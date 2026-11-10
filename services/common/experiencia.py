"""Cálculo de años de experiencia (compartido entre IA y backend)."""
import re
from datetime import date


def _ym(s: str | None, hoy: date, fin: bool = False) -> tuple[int, int] | None:
    if not s:
        return None
    if s.strip().lower() in ("actual", "presente", "current", "present"):
        return hoy.year, hoy.month
    m = re.match(r"(\d{4})(?:-(\d{1,2}))?", s.strip())
    if not m:
        return None
    # un año suelto como inicio es enero; como fin es diciembre
    return int(m.group(1)), int(m.group(2) or (12 if fin else 1))


def anios_experiencia(experiencia: list[dict], hoy: date | None = None) -> float:
    """Meses totales fusionando periodos solapados (RF-09), en años con un decimal."""
    hoy = hoy or date.today()
    tramos = []
    for e in experiencia:
        e = e if isinstance(e, dict) else e.model_dump()
        ini, fin = _ym(e.get("fecha_inicio"), hoy), _ym(e.get("fecha_fin"), hoy, fin=True)
        if ini and fin:
            a, b = ini[0] * 12 + ini[1], fin[0] * 12 + fin[1]
            if b >= a:
                tramos.append((a, b + 1))  # inclusivo
    tramos.sort()
    total, cur = 0, None
    for a, b in tramos:
        if cur is None:
            cur = [a, b]
        elif a <= cur[1]:
            cur[1] = max(cur[1], b)
        else:
            total += cur[1] - cur[0]
            cur = [a, b]
    if cur:
        total += cur[1] - cur[0]
    return round(total / 12, 1)


