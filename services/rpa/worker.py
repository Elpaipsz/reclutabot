"""Robot RPA: registra candidatos aprobados en el sistema de RR.HH. con Playwright (tópico 'registrar-rpa')."""
import logging
import os
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

from common.flowable_worker import run_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rpa")

API = os.getenv("API_URL", "http://api:8000")
H = {"X-Internal-Token": os.getenv("INTERNAL_TOKEN", "")}
RRHH = os.getenv("RRHH_URL", "http://rrhh:9000")
RRHH_USER, RRHH_PASS = os.getenv("RRHH_USER", "robot"), os.getenv("RRHH_PASSWORD", "robot123")
UPLOADS = Path(os.getenv("UPLOADS_DIR", "/data/uploads"))
HEADLESS = os.getenv("RPA_HEADLESS", "true").lower() != "false"
SLOW_MO = int(os.getenv("RPA_SLOW_MO", "0"))        # ms entre acciones (útil para demos visibles)
INTENTOS = 3                                          # RF-22
TIMEOUT_MS = 20_000                                   # RNF-02/RNF-07


def api(method, path, **kw):
    r = httpx.request(method, f"{API}{path}", headers=H, timeout=30, **kw)
    r.raise_for_status()
    return r.json()


def registrar(payload: dict, captura: Path) -> str:
    """Una pasada completa en el navegador. Devuelve el ID asignado por RR.HH."""
    d, c = payload["datos"], payload["candidato"]
    personales = d.get("datos_personales", {})
    nombre = personales.get("nombre") or c["nombre"]
    correo = personales.get("correo") or c["correo"]
    documento = (personales.get("documento") or "").strip()
    telefono = personales.get("telefono") or c["telefono"] or ""
    formacion = (d.get("formacion") or [{}])[0]
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        page = navegador.new_page()
        page.set_default_timeout(TIMEOUT_MS)
        try:
            page.goto(f"{RRHH}/login")
            page.fill("#usuario", RRHH_USER)
            page.fill("#password", RRHH_PASS)
            page.click("#entrar")
            page.wait_for_url("**/candidatos")

            # RF-23: buscar antes de crear (documento; si no hay, correo)
            page.goto(f"{RRHH}/candidatos")
            page.fill("#q", documento or correo)
            page.click("#buscar")
            page.wait_for_load_state()
            existente = page.locator("tr.fila .rh-id")
            if existente.count() > 0:
                rid = existente.first.inner_text().strip()
                log.info("candidato ya existía en RR.HH.: %s (no se duplica)", rid)
                return rid

            page.goto(f"{RRHH}/candidatos/nuevo")
            page.fill("#nombre", nombre)
            page.fill("#documento", documento)
            page.fill("#correo", correo)
            page.fill("#telefono", str(telefono))
            page.fill("#vacante", payload["vacante"]["codigo"])
            page.fill("#anios", str(payload["anios_experiencia"]))
            page.fill("#formacion", formacion.get("titulo") or "")
            page.fill("#habilidades", ", ".join(d.get("habilidades", [])))
            page.fill("#resumen", f"Puntaje {payload['puntaje']} · postulación {payload['postulacion']['numero']}")
            adjunto = UPLOADS / payload["postulacion"]["archivo_path"]
            if adjunto.exists():
                page.set_input_files("#archivo", str(adjunto))
            page.click("#guardar")
            page.wait_for_selector("#id-asignado")           # RF-21: capturar el ID
            return page.inner_text("#id-asignado").strip()
        except Exception:
            try:
                captura.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(captura), full_page=True)
            except Exception:
                pass
            raise
        finally:
            navegador.close()


def registrar_rpa(v: dict) -> dict:
    pid = int(v["postulacionId"])
    payload = api("GET", f"/internal/postulaciones/{pid}/payload")
    if payload["postulacion"]["rrhh_id"]:                      # idempotencia ante reintentos de Flowable
        return {"rpaOk": True}
    captura = UPLOADS / "capturas" / f"{payload['postulacion']['numero']}-{int(time.time())}.png"
    ultimo = None
    for intento in range(1, INTENTOS + 1):
        try:
            rid = registrar(payload, captura)
            api("POST", f"/internal/postulaciones/{pid}/rrhh-id", json={"rrhh_id": rid})
            log.info("postulación %s registrada como %s (intento %d)", pid, rid, intento)
            return {"rpaOk": True}
        except Exception as e:
            ultimo = e
            log.warning("intento %d/%d falló: %s", intento, INTENTOS, str(e)[:200])
            time.sleep(2 ** intento)
    api("POST", f"/internal/postulaciones/{pid}/incidencia", json={
        "origen": "rpa", "detalle": f"El robot falló tras {INTENTOS} intentos: {str(ultimo)[:300]}",
        "captura_path": captura.name if captura.exists() else None})
    return {"rpaOk": False}


if __name__ == "__main__":
    run_worker("registrar-rpa", registrar_rpa, lock="PT10M")
