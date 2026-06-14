# backend/app/routers/uploads.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.session import UploadMVPResponse, RowErrorSchema, MinutaSchema
from app.services.dj_engine import get_dj_texto
from app.services.excel_parser import parse_excel_file
from app.services.minuta_generator import generate_minuta_text
from app.services import session_store
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
    config = session_store.get_config_dj(user_id)
    dj_texto = get_dj_texto(config.activa, config.texto_alerta)
    now = datetime.now(timezone.utc)

    minutas: list[MinutaSession] = []
    for parsed in parse_result.ordenes:
        texto = generate_minuta_text(
            cliente_nombre=parsed.cliente_nombre,
            cuenta_comitente=parsed.cuenta_comitente,
            cuenta_cotapartista=parsed.cuenta_cotapartista,
            instrumento=parsed.instrumento,
            tipo=parsed.tipo,
            cantidad=parsed.cantidad,
            precio=parsed.precio,
            moneda=parsed.moneda,
            liquidacion=parsed.liquidacion,
            fecha_operacion=parsed.fecha_operacion,
            dj_texto=dj_texto,
        )
        minutas.append(MinutaSession(
            id=str(uuid.uuid4()),
            cliente_nombre=parsed.cliente_nombre,
            cliente_email=parsed.cliente_email,
            cuenta_comitente=parsed.cuenta_comitente,
            cuenta_cotapartista=parsed.cuenta_cotapartista,
            instrumento=parsed.instrumento,
            tipo=parsed.tipo,
            cantidad=parsed.cantidad,
            precio=parsed.precio,
            moneda=parsed.moneda,
            liquidacion=parsed.liquidacion,
            fecha_operacion=parsed.fecha_operacion,
            dj_aplicada=config.activa,
            dj_texto=dj_texto,
            estado="BORRADOR",
            texto_minuta=texto,
            texto_editado=False,
            creado_en=now,
        ))

    session_store.add_minutas(user_id, minutas)

    return UploadMVPResponse(
        nombre_archivo=filename,
        total_ordenes=len(parse_result.ordenes) + len(parse_result.errors),
        ordenes_validas=len(parse_result.ordenes),
        ordenes_con_error=len(parse_result.errors),
        errors=[RowErrorSchema(fila=e.fila, mensaje=e.mensaje) for e in parse_result.errors],
        minutas=[MinutaSchema(**m.__dict__) for m in minutas],
    )
