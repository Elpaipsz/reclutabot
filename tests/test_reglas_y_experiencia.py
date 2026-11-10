"""Pruebas unitarias del motor de reglas y del cálculo de experiencia (RNF-20)."""
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "services" / "api"))
sys.path.insert(0, str(RAIZ / "services"))

from app import rules  # noqa: E402
from common.experiencia import anios_experiencia  # noqa: E402

HOY = date(2026, 11, 1)
REQ = {"anios_experiencia": 2, "formacion_minima": "Profesional", "habilidades_obligatorias": ["Python", "SQL"],
       "habilidades_deseables": ["Docker"], "idiomas": [{"idioma": "Inglés", "nivel": "B1"}]}


def cv(nivel="Profesional", skills=("Python", "SQL", "Docker"), idiomas=(("Inglés", "B2"),)):
    return {"formacion": [{"titulo": "X", "nivel": nivel}], "habilidades": list(skills),
            "idiomas": [{"idioma": i, "nivel": n} for i, n in idiomas]}


# ---------- experiencia ----------

def test_experiencia_simple():
    assert anios_experiencia([{"fecha_inicio": "2020-01", "fecha_fin": "2021-12"}], HOY) == 2.0


def test_experiencia_actual_usa_fecha_de_hoy():
    assert anios_experiencia([{"fecha_inicio": "2026-05", "fecha_fin": "actual"}], HOY) == 0.6   # may–nov = 7 meses


def test_experiencia_fusiona_periodos_solapados():
    exp = [{"fecha_inicio": "2020-01", "fecha_fin": "2021-12"}, {"fecha_inicio": "2021-01", "fecha_fin": "2022-12"}]
    assert anios_experiencia(exp, HOY) == 3.0     # 36 meses, no 48


def test_experiencia_ignora_fechas_invalidas_o_vacias():
    exp = [{"fecha_inicio": None, "fecha_fin": "2021-01"}, {"fecha_inicio": "2022-05", "fecha_fin": "2021-01"}, {}]
    assert anios_experiencia(exp, HOY) == 0.0


def test_experiencia_solo_anio():
    assert anios_experiencia([{"fecha_inicio": "2019", "fecha_fin": "2020"}], HOY) == 2.0   # 2019 y 2020 completos


# ---------- reglas ----------

def test_cumple_todo():
    r = rules.evaluar(cv(), 3.0, REQ)
    assert r["clasificacion"] == "Cumple" and r["puntaje"] == 100.0 and not r["incumple"]


def test_no_cumple_si_falta_todo():
    r = rules.evaluar(cv("Bachiller", ["Excel"], []), 0.0, REQ)
    assert r["clasificacion"] == "No cumple" and r["puntaje"] < 40
    assert set(r["incumple"]) == {"experiencia", "formacion", "habilidades"}


def test_revisar_cuando_falta_un_obligatorio_pero_puntaje_medio():
    r = rules.evaluar(cv(skills=["Python", "Docker"]), 3.0, REQ)      # falta SQL (obligatoria)
    assert r["clasificacion"] == "Revisar" and r["incumple"] == ["habilidades"]


def test_habilidades_ignoran_tildes_y_mayusculas():
    r = rules.evaluar(cv(skills=["PYTHON", "sql", "docker"]), 3.0, REQ)
    assert r["criterios"]["habilidades"]["cumple"]


def test_idioma_nivel_inferior_da_puntaje_parcial_y_no_cumple_criterio():
    r = rules.evaluar(cv(idiomas=[("Inglés", "A2")]), 3.0, REQ)
    assert r["criterios"]["idioma"]["puntos"] == 0.5 and not r["criterios"]["idioma"]["cumple"]


def test_pesos_configurables_cambian_el_puntaje():
    base = rules.evaluar(cv(skills=["Python", "SQL"]), 1.0, REQ)
    solo_exp = rules.evaluar(cv(skills=["Python", "SQL"]), 1.0, REQ,
                             {"experiencia": 1, "formacion": 0, "habilidades": 0, "idioma": 0})
    assert solo_exp["puntaje"] == 50.0 and base["puntaje"] != solo_exp["puntaje"]


def test_vacante_sin_requisitos_cumple():
    assert rules.evaluar(cv("Otro", [], []), 0.0, {})["clasificacion"] == "Cumple"


def test_la_clasificacion_nunca_depende_solo_de_ia_hay_obligatorios_personalizables():
    r = rules.evaluar(cv(skills=["Excel"]), 3.0, {**REQ, "obligatorios": ["experiencia"]})
    assert r["incumple"] == []        # habilidades dejó de ser obligatoria en esta vacante
