from datetime import datetime
from typing import Optional


DEFAULT_PLANTILLA = (
    "MINUTA DE OPERACIÓN\n"
    "Fecha y hora: {fecha_operacion}\n"
    "Fecha liquidación: {fecha_liquidacion}\n\n"
    "Cliente: {cliente_nombre}\n"
    "Cuenta Comitente: {cuenta_comitente}\n"
    "Cuenta Cotapartista: {cuenta_cotapartista}\n\n"
    "DETALLE DE LA OPERACIÓN\n"
    "Operación: {operacion}\n"
    "Instrumento: {instrumento}\n"
    "Moneda: {moneda}\n"
    "Cantidad: {cantidad}\n"
    "Precio: {precio}\n"
    "Monto: {monto}\n"
    "Estado: {estado}\n\n"
    "Asesor: {asesor}\n\n"
    "Quedo a su disposición ante cualquier consulta.\n"
    "Saludos cordiales."
)

_CAMPOS_NUMERICOS = {
    "cantidad", "precio", "monto", "cantidad_operada", "precio_operado"
}


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _fmt_num(val: float) -> str:
    """Formatea un número para la Minuta. -1 → 'N/A'."""
    if val == -1:
        return "N/A"
    if val == int(val):
        return f"{int(val):,}".replace(",", ".")
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_minuta_text(
    plantilla: str,
    datos: dict,
    dj_texto: Optional[str] = None,
) -> str:
    fecha_op = datos.get("fecha_operacion")
    fecha_str = (
        fecha_op.strftime("%d/%m/%Y %H:%M")
        if isinstance(fecha_op, datetime)
        else str(fecha_op or "")
    )

    subs = _SafeDict()
    for key, val in datos.items():
        if key == "fecha_operacion":
            subs[key] = fecha_str
        elif key in _CAMPOS_NUMERICOS and isinstance(val, (int, float)):
            subs[key] = _fmt_num(float(val))
        else:
            subs[key] = str(val) if val is not None else ""

    texto = plantilla.format_map(subs)
    if dj_texto:
        texto += f"\n\n---\nDECLARACIÓN JURADA\n\n{dj_texto}"
    return texto
