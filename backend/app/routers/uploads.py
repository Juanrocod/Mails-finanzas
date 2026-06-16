import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.session import UploadMVPResponse, RowErrorSchema, MinutaSchema
from app.services.dj_engine import evaluar_reglas, resolver_dj_texto
from app.services.filtros_engine import evaluar_filtros
from app.services.excel_parser import parse_excel_file
from app.services.minuta_generator import generate_minuta_text
from app.services import session_store, db_config
from app.services.session_store import MinutaSession

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


@router.post("/excel", response_model=UploadMVPResponse, status_code=status.HTTP_201_CREATED)
def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Se esperaba .xlsx o .xls, se recibió: '{ext}'",
        )

    file_bytes = file.file.read()

    try:
        parse_result = parse_excel_file(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user_id = str(current_user.id)
    config_dj = db_config.load_config_dj(db)
    config_filtros = db_config.load_config_filtros(db)
    plantilla = db_config.load_plantilla(db)
    now = datetime.now(timezone.utc)

    minutas: list[MinutaSession] = []
    filtradas_count = 0

    for parsed in parse_result.ordenes:
        datos = {
            "cliente_nombre": parsed.cliente_nombre,
            "cuenta_comitente": parsed.cuenta_comitente,
            "cuenta_cotapartista": parsed.cuenta_cotapartista,
            "id_orden": parsed.id_orden,
            "fecha_operacion": parsed.fecha_operacion,
            "fecha_liquidacion": parsed.fecha_liquidacion,
            "operacion": parsed.operacion,
            "instrumento": parsed.instrumento,
            "moneda": parsed.moneda,
            "cantidad": parsed.cantidad,
            "precio": parsed.precio,
            "monto": parsed.monto,
            "estado": parsed.estado,
            "cantidad_operada": parsed.cantidad_operada,
            "precio_operado": parsed.precio_operado,
            "operador": parsed.operador,
            "origen": parsed.origen,
            "asesor": parsed.asesor,
            "requiere_conformidad": parsed.requiere_conformidad,
        }

        excluida = evaluar_filtros(config_filtros, datos)
        estado_minuta = "FILTRADA" if excluida else "BORRADOR"
        if excluida:
            filtradas_count += 1

        dj_aplica = evaluar_reglas(config_dj, datos)
        dj_texto = resolver_dj_texto(config_dj, datos) if dj_aplica else None
        texto = generate_minuta_text(plantilla, datos, dj_texto=dj_texto)

        minutas.append(MinutaSession(
            id=str(uuid.uuid4()),
            cliente_nombre=parsed.cliente_nombre,
            cuenta_comitente=parsed.cuenta_comitente,
            cuenta_cotapartista=parsed.cuenta_cotapartista,
            id_orden=parsed.id_orden,
            fecha_operacion=parsed.fecha_operacion,
            fecha_liquidacion=parsed.fecha_liquidacion,
            operacion=parsed.operacion,
            instrumento=parsed.instrumento,
            moneda=parsed.moneda,
            cantidad=parsed.cantidad,
            precio=parsed.precio,
            monto=parsed.monto,
            estado_orden=parsed.estado,
            cantidad_operada=parsed.cantidad_operada,
            precio_operado=parsed.precio_operado,
            operador=parsed.operador,
            origen=parsed.origen,
            asesor=parsed.asesor,
            requiere_conformidad=parsed.requiere_conformidad,
            dj_aplicada=dj_aplica,
            dj_texto=dj_texto,
            estado=estado_minuta,
            texto_minuta=texto,
            texto_editado=False,
            creado_en=now,
        ))

    session_store.clear_borradores_y_filtradas(user_id)
    session_store.add_minutas(user_id, minutas)

    borradores = [m for m in minutas if m.estado == "BORRADOR"]

    return UploadMVPResponse(
        nombre_archivo=filename,
        total_ordenes=len(parse_result.ordenes) + len(parse_result.errors),
        ordenes_validas=len(parse_result.ordenes),
        ordenes_con_error=len(parse_result.errors),
        ordenes_filtradas=filtradas_count,
        errors=[RowErrorSchema(fila=e.fila, mensaje=e.mensaje) for e in parse_result.errors],
        minutas=[MinutaSchema(**m.__dict__) for m in borradores],
    )
