import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ

DEFAULT_PLANTILLA = (
    "MINUTA DE OPERACIÓN\n"
    "Fecha y hora: {fecha_operacion}\n\n"
    "Cliente: {cliente_nombre}\n"
    "Cuenta Comitente: {cuenta_comitente}\n"
    "Cuenta Cotapartista: {cuenta_cotapartista}\n\n"
    "DETALLE DE LA OPERACIÓN\n"
    "Instrumento: {instrumento}\n"
    "Tipo: {tipo}\n"
    "Cantidad: {cantidad}\n"
    "Precio: {precio} {moneda}\n"
    "Condición de Liquidación: {liquidacion}\n\n"
    "Quedo a su disposición ante cualquier consulta.\n"
    "Saludos cordiales."
)


@dataclass
class ConfigDJData:
    activa: bool = False
    incluir_texto_en_minuta: bool = False
    texto_alerta: str = ""
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


def load_config_dj(db: Session) -> ConfigDJData:
    row = db.get(ConfigDJ, 1)
    if not row:
        return ConfigDJData()
    return ConfigDJData(
        activa=row.activa,
        incluir_texto_en_minuta=row.incluir_texto_en_minuta,
        texto_alerta=row.texto_alerta,
        reglas=json.loads(row.reglas),
        logica=row.logica,
    )


def save_config_dj(db: Session, data: ConfigDJData) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(ConfigDJ, 1)
    if row:
        row.activa = data.activa
        row.incluir_texto_en_minuta = data.incluir_texto_en_minuta
        row.texto_alerta = data.texto_alerta
        row.reglas = json.dumps(data.reglas)
        row.logica = data.logica
        row.actualizado_en = now
    else:
        db.add(ConfigDJ(
            id=1,
            activa=data.activa,
            incluir_texto_en_minuta=data.incluir_texto_en_minuta,
            texto_alerta=data.texto_alerta,
            reglas=json.dumps(data.reglas),
            logica=data.logica,
            actualizado_en=now,
        ))
    db.commit()
