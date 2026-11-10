"""Pruebas unitarias de plantillas de correo (RF-28) y de la regla de confianza baja (RF-10, RF-16)."""
import sys
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "services" / "api"))
sys.path.insert(0, str(RAIZ / "services"))

from app import plantillas  # noqa: E402
from common.confianza import hay_baja_confianza  # noqa: E402


# ---------- plantillas ----------

def test_render_sustituye_marcadores():
    assert plantillas.render("Hola {nombre}, tu número es {numero}", {"nombre": "Ana", "numero": "POST-1"}) == "Hola Ana, tu número es POST-1"


def test_render_deja_intactos_los_marcadores_desconocidos():
    assert plantillas.render("Hola {nombre} {otro}", {"nombre": "Ana"}) == "Hola Ana {otro}"


def test_render_no_permite_acceder_a_atributos():
    """Una plantilla editable no debe poder filtrar objetos internos (a diferencia de str.format)."""
    assert plantillas.render("{nombre.__class__}", {"nombre": "Ana"}) == "{nombre.__class__}"


def test_todas_las_plantillas_tienen_etiqueta_y_se_renderizan():
    ctx = {"nombre": "Ana", "numero": "POST-1", "vacante": "Analista", "enlace": "http://x", "tarea": "Validar", "tiempo": "24 horas"}
    assert set(plantillas.DEFECTO) == set(plantillas.ETIQUETAS)
    for clave, (asunto, cuerpo) in plantillas.DEFECTO.items():
        for texto in (asunto, cuerpo):
            assert "{" not in plantillas.render(texto, ctx), clave


def test_avisos_al_personal_no_incluyen_datos_del_candidato():
    """HU-16: el aviso no expone información personal innecesaria."""
    for clave in ("tarea_pendiente", "tarea_escalada"):
        asunto, cuerpo = plantillas.DEFECTO[clave]
        assert "{nombre}" not in asunto + cuerpo


# ---------- confianza ----------

DATOS = {"datos_personales": {"nombre": "Ana", "correo": "a@b.co", "telefono": None, "documento": "123", "ubicacion": "Cali"}}


def test_confianza_alta_no_requiere_revision():
    assert not hay_baja_confianza(DATOS, {"nombre": 0.95, "correo": 0.9, "formacion": 0.9, "experiencia": 0.85})


def test_un_campo_personal_dudoso_activa_la_revision():
    assert hay_baja_confianza(DATOS, {"nombre": 0.95, "documento": 0.6})


def test_un_bloque_dudoso_activa_la_revision():
    assert hay_baja_confianza(DATOS, {"nombre": 0.95, "experiencia": 0.7})


def test_dato_personal_ausente_no_cuenta_aunque_su_confianza_sea_baja():
    assert not hay_baja_confianza(DATOS, {"nombre": 0.95, "telefono": 0.1})   # telefono es null: simplemente no aparece


def test_umbral_configurable_y_valores_invalidos_se_ignoran():
    assert hay_baja_confianza(DATOS, {"nombre": 0.85}, umbral=0.9)
    assert not hay_baja_confianza(DATOS, {"nombre": "n/a", "correo": None})
