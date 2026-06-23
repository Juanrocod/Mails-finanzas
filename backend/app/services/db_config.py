import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ
from app.models.config_filtros import ConfigFiltros

DEFAULT_PLANTILLA = (
    "MINUTA DE OPERACIÓN Nº {id_orden}\n"
    "Fecha de operación: {fecha_operacion}\n"
    "Fecha de liquidación: {fecha_liquidacion}\n"
    "\n"
    "Estimado/a {cliente_nombre},\n"
    "\n"
    "Por medio de la presente le informamos que se ha procesado la siguiente "
    "operación en su cuenta:\n"
    "\n"
    "  Operación:          {operacion}\n"
    "  Instrumento:        {instrumento}\n"
    "  Cantidad:           {cantidad}\n"
    "  Precio unitario:    {precio}\n"
    "  Monto total:        {monto}\n"
    "  Moneda:             {moneda}\n"
    "  Estado:             {estado}\n"
    "\n"
    "  Cuenta comitente:   {cuenta_comitente}\n"
    "  Cuenta cotapartista:{cuenta_cotapartista}\n"
    "\n"
    "Ante cualquier consulta o aclaración, no dude en comunicarse con nosotros.\n"
    "\n"
    "Atentamente,\n"
    "{asesor}"
)


@dataclass
class ConfigDJData:
    id: int | None = None
    nombre: str = "DJ General"
    activa: bool = False
    incluir_texto_en_minuta: bool = False
    texto_alerta: str = ""
    reglas: list = field(default_factory=list)
    logica: str = "OR"
    activar_si_requiere_conformidad: bool = True


@dataclass
class ConfigFiltrosData:
    reglas: list = field(default_factory=list)
    logica: str = "OR"


def load_plantilla(db: Session) -> str:
    row = db.get(Plantilla, 1)
    return row.texto if row else DEFAULT_PLANTILLA


def save_plantilla(db: Session, texto: str) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(Plantilla, 1)
    if row:
        row.texto = texto
        row.actualizado_en = now
    else:
        db.add(Plantilla(id=1, texto=texto, actualizado_en=now))
    db.commit()


def _row_to_data(row: ConfigDJ) -> ConfigDJData:
    return ConfigDJData(
        id=row.id,
        nombre=row.nombre,
        activa=row.activa,
        incluir_texto_en_minuta=row.incluir_texto_en_minuta,
        texto_alerta=row.texto_alerta,
        reglas=json.loads(row.reglas),
        logica=row.logica,
        activar_si_requiere_conformidad=row.activar_si_requiere_conformidad,
    )


def load_all_config_dj(db: Session) -> list[ConfigDJData]:
    rows = db.query(ConfigDJ).order_by(ConfigDJ.id).all()
    return [_row_to_data(row) for row in rows]


def create_config_dj(db: Session, data: ConfigDJData) -> ConfigDJData:
    now = datetime.now(timezone.utc)
    row = ConfigDJ(
        nombre=data.nombre,
        activa=data.activa,
        incluir_texto_en_minuta=data.incluir_texto_en_minuta,
        texto_alerta=data.texto_alerta,
        reglas=json.dumps(data.reglas),
        logica=data.logica,
        activar_si_requiere_conformidad=data.activar_si_requiere_conformidad,
        actualizado_en=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    data.id = row.id
    return data


def update_config_dj(db: Session, dj_id: int, data: ConfigDJData) -> ConfigDJData | None:
    row = db.get(ConfigDJ, dj_id)
    if not row:
        return None
    now = datetime.now(timezone.utc)
    row.nombre = data.nombre
    row.activa = data.activa
    row.incluir_texto_en_minuta = data.incluir_texto_en_minuta
    row.texto_alerta = data.texto_alerta
    row.reglas = json.dumps(data.reglas)
    row.logica = data.logica
    row.activar_si_requiere_conformidad = data.activar_si_requiere_conformidad
    row.actualizado_en = now
    db.commit()
    data.id = dj_id
    return data


def delete_config_dj(db: Session, dj_id: int) -> bool:
    row = db.get(ConfigDJ, dj_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True



def load_config_filtros(db: Session) -> ConfigFiltrosData:
    row = db.get(ConfigFiltros, 1)
    if not row:
        return ConfigFiltrosData()
    return ConfigFiltrosData(
        reglas=json.loads(row.reglas),
        logica=row.logica,
    )


def save_config_filtros(db: Session, data: ConfigFiltrosData) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(ConfigFiltros, 1)
    if row:
        row.reglas = json.dumps(data.reglas)
        row.logica = data.logica
        row.actualizado_en = now
    else:
        db.add(ConfigFiltros(
            id=1,
            reglas=json.dumps(data.reglas),
            logica=data.logica,
            actualizado_en=now,
        ))
    db.commit()
