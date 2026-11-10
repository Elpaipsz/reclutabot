"""Regla de confianza baja (RF-10, RF-16), compartida por el servicio de IA y el backend."""

CAMPOS_PERSONALES = ("nombre", "correo", "telefono", "documento", "ubicacion")


def hay_baja_confianza(datos: dict, confianza: dict, umbral: float = 0.8) -> bool:
    """True si algún campo o bloque extraído tiene confianza menor al umbral.

    La confianza se informa por campo en los datos personales y por bloque en las listas. Un dato personal
    que no aparece en la hoja de vida (null) no cuenta: que falte no significa que la IA dude de lo que leyó."""
    personales = (datos or {}).get("datos_personales", {}) or {}
    for clave, valor in (confianza or {}).items():
        if clave in CAMPOS_PERSONALES and not personales.get(clave):
            continue
        try:
            if float(valor) < umbral:
                return True
        except (TypeError, ValueError):
            continue
    return False
