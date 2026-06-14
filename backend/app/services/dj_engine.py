from typing import Optional


def get_dj_texto(activa: bool, texto_alerta: str) -> Optional[str]:
    return texto_alerta if activa else None
