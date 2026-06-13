from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit import DJTemplate


def evaluate_dj_rules(
    instrumento: str,
    tipo: str,
    moneda: str,
    cantidad: float,
    precio: float,
    db: Session,
) -> Optional[DJTemplate]:
    """
    Evaluate which DJTemplate (if any) applies to the given order.

    Returns the highest-priority active template whose rules all match,
    or None if no template matches.
    """
    templates = (
        db.query(DJTemplate)
        .filter(DJTemplate.activo == True)
        .order_by(DJTemplate.prioridad.desc())
        .all()
    )
    monto = cantidad * precio
    for template in templates:
        if _matches(template.reglas, instrumento, tipo, moneda, monto):
            return template
    return None


def _matches(reglas: dict, instrumento: str, tipo: str, moneda: str, monto: float) -> bool:
    """Return True if all rules in reglas match the given order fields."""
    if "instrumento" in reglas:
        if reglas["instrumento"].upper() not in instrumento.upper():
            return False
    if "tipo" in reglas:
        if reglas["tipo"].upper() != tipo.upper():
            return False
    if "moneda" in reglas:
        if reglas["moneda"].upper() != moneda.upper():
            return False
    if "monto_minimo" in reglas:
        if monto < float(reglas["monto_minimo"]):
            return False
    return True
