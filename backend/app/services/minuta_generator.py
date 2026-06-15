from datetime import datetime
from typing import Optional


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


class _SafeDict(dict):
    """Deja {variable} sin reemplazar si la clave no existe."""
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def generate_minuta_text(
    plantilla: str,
    cliente_nombre: str,
    cuenta_comitente: str,
    cuenta_cotapartista: str,
    instrumento: str,
    tipo: str,
    cantidad: float,
    precio: float,
    moneda: str,
    liquidacion: str,
    fecha_operacion: datetime,
    dj_texto: Optional[str] = None,
) -> str:
    cantidad_str = f"{cantidad:,.0f}".replace(",", ".")
    precio_str = (
        f"{precio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    subs = _SafeDict(
        cliente_nombre=cliente_nombre,
        cuenta_comitente=cuenta_comitente,
        cuenta_cotapartista=cuenta_cotapartista,
        instrumento=instrumento,
        tipo=tipo,
        cantidad=cantidad_str,
        precio=precio_str,
        moneda=moneda,
        liquidacion=liquidacion,
        fecha_operacion=fecha_operacion.strftime("%d/%m/%Y %H:%M"),
    )
    texto = plantilla.format_map(subs)
    if dj_texto:
        texto += f"\n\n---\nDECLARACIÓN JURADA\n\n{dj_texto}"
    return texto
