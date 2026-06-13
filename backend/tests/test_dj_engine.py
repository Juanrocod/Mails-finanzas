import pytest
from app.services.dj_engine import evaluate_dj_rules
from app.models.audit import DJTemplate


def make_template(db, nombre, reglas, prioridad=1, activo=True):
    t = DJTemplate(
        nombre=nombre,
        texto=f"Texto DJ para {nombre}",
        reglas=reglas,
        prioridad=prioridad,
        activo=activo,
    )
    db.add(t)
    db.flush()
    return t


def test_no_templates_returns_none(db):
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is None


def test_matches_instrumento(db):
    make_template(db, "DJ-AL30", {"instrumento": "AL30"})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is not None
    assert result.nombre == "DJ-AL30"


def test_no_match_different_instrumento(db):
    make_template(db, "DJ-GD30", {"instrumento": "GD30"})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is None


def test_matches_tipo(db):
    make_template(db, "DJ-COMPRA", {"tipo": "COMPRA"})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is not None


def test_no_match_wrong_tipo(db):
    make_template(db, "DJ-VENTA-ONLY", {"tipo": "VENTA"})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is None


def test_matches_moneda(db):
    make_template(db, "DJ-USD", {"moneda": "USD"})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is not None


def test_no_match_wrong_moneda(db):
    make_template(db, "DJ-ARS", {"moneda": "ARS"})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is None


def test_monto_minimo_reached(db):
    # monto = 1000 * 70.50 = 70500
    make_template(db, "DJ-MONTO", {"monto_minimo": 50000})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is not None


def test_monto_minimo_not_reached(db):
    # monto = 1 * 1.0 = 1.0 < 100000
    make_template(db, "DJ-BIGMONTO", {"monto_minimo": 100000})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1, 1.0, db)
    assert result is None


def test_empty_reglas_matches_everything(db):
    make_template(db, "DJ-UNIVERSAL", {})
    result = evaluate_dj_rules("CUALQUIER", "COMPRA", "USD", 1, 1.0, db)
    assert result is not None


def test_inactive_template_not_matched(db):
    make_template(db, "DJ-INACTIVO", {}, activo=False)
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is None


def test_priority_order_highest_wins(db):
    make_template(db, "DJ-LOW", {}, prioridad=1)
    make_template(db, "DJ-HIGH", {}, prioridad=10)
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result.nombre == "DJ-HIGH"


def test_combined_rules_all_must_match(db):
    make_template(db, "DJ-COMBO", {"instrumento": "AL30", "tipo": "VENTA"})
    # Order is COMPRA, not VENTA -> should not match
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is None


def test_instrumento_partial_match(db):
    # Rule says "AL" -- order has "AL30" -- should match (contains)
    make_template(db, "DJ-AL-FAMILY", {"instrumento": "AL"})
    result = evaluate_dj_rules("AL30", "COMPRA", "USD", 1000, 70.50, db)
    assert result is not None
