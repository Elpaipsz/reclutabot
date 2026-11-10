"""Pruebas del plazo de escalación en horas hábiles (RF-19)."""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))

from app.horario import duracion_iso, fin_plazo_habil  # noqa: E402

TZ = timezone(timedelta(hours=-5))


def d(y, m, dia, h=0, mi=0):
    return datetime(y, m, dia, h, mi, tzinfo=TZ)


def test_lunes_10am_24h_habiles_termina_miercoles_2pm():
    # lunes 10-18 = 8 h, martes 10 h (18 acumuladas), miércoles 8:00-14:00 = 6 h
    assert fin_plazo_habil(d(2026, 11, 2, 10), 24) == d(2026, 11, 4, 14)


def test_viernes_tarde_salta_el_fin_de_semana():
    # viernes 16:00: quedan 2 h, el lunes 10 h, el martes 10 h, el miércoles 2 h
    assert fin_plazo_habil(d(2026, 11, 6, 16), 24) == d(2026, 11, 11, 10)


def test_sabado_cuenta_desde_el_lunes_a_las_8():
    assert fin_plazo_habil(d(2026, 11, 7, 12), 2) == d(2026, 11, 9, 10)


def test_fuera_de_horario_nocturno_espera_a_la_manana():
    assert fin_plazo_habil(d(2026, 11, 3, 21), 1) == d(2026, 11, 4, 9)


def test_festivo_no_cuenta():
    assert fin_plazo_habil(d(2026, 11, 2, 17), 2, festivos={date(2026, 11, 3)}) == d(2026, 11, 4, 9)


def test_duracion_iso_es_valida_y_mayor_que_la_corrida():
    iso = duracion_iso(d(2026, 11, 6, 16), 24)
    assert iso.startswith("PT") and iso.endswith("M")
    horas = int(iso[2:iso.index("H")])
    assert horas > 24
