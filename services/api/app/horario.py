"""Cálculo de plazos en horas hábiles (RF-19).

Flowable solo entiende duraciones corridas (PT24H). Para respetar un horario laboral, calculamos
cuánto tiempo corrido hay que esperar hasta que se cumplan N horas hábiles y se lo pasamos al
temporizador como una duración ISO-8601 normal.
"""
from datetime import date, datetime, timedelta, timezone


def _inicio_ventana(t: datetime, ini: int, fin: int, dias: set[int], festivos: set[date]) -> datetime:
    """Primer instante >= t que cae dentro del horario laboral."""
    while True:
        habil = t.weekday() in dias and t.date() not in festivos
        if habil and t.hour < ini:
            return t.replace(hour=ini, minute=0, second=0, microsecond=0)
        if habil and t.hour < fin:
            return t
        t = (t + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def fin_plazo_habil(inicio: datetime, horas: float, ini: int = 8, fin: int = 18,
                    dias: set[int] | None = None, festivos: set[date] | None = None) -> datetime:
    """Momento en que se cumplen `horas` hábiles contadas desde `inicio` (lunes a viernes, 8:00 a 18:00 por defecto)."""
    dias = dias if dias is not None else {0, 1, 2, 3, 4}
    festivos = festivos or set()
    restante = timedelta(hours=horas)
    t = inicio
    while True:
        t = _inicio_ventana(t, ini, fin, dias, festivos)
        cierre = t.replace(hour=fin, minute=0, second=0, microsecond=0)
        if cierre - t >= restante:
            return t + restante
        restante -= cierre - t
        t = cierre


def duracion_iso(inicio: datetime, horas: float, **kw) -> str:
    """Duración corrida ISO-8601 (PTnHnM) equivalente a `horas` hábiles desde `inicio`."""
    total = int((fin_plazo_habil(inicio, horas, **kw) - inicio).total_seconds() // 60) + 1
    return f"PT{total // 60}H{total % 60}M"


def ahora_local(offset_horas: float) -> datetime:
    return datetime.now(timezone(timedelta(hours=offset_horas)))
