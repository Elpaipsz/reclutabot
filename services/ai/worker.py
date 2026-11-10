"""Worker de IA: atiende el tópico 'extraer-cv' de Flowable."""
import logging
import os

import httpx

from common.confianza import hay_baja_confianza
from common.flowable_worker import run_worker
import extractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ia")

API = os.getenv("API_URL", "http://api:8000")
H = {"X-Internal-Token": os.getenv("INTERNAL_TOKEN", "")}
UPLOADS = os.getenv("UPLOADS_DIR", "/data/uploads")
UMBRAL_CONFIANZA = float(os.getenv("UMBRAL_CONFIANZA", "0.8"))  # RF-16
# Precio estimado por millón de tokens (USD) para registrar el costo por CV (RNF-21)
PRECIO_IN, PRECIO_OUT = float(os.getenv("PRECIO_IN", "0.30")), float(os.getenv("PRECIO_OUT", "2.50"))


def api(method, path, **kw):
    r = httpx.request(method, f"{API}{path}", headers=H, timeout=30, **kw)
    r.raise_for_status()
    return r.json()


def extraer_cv(v: dict) -> dict:
    pid = int(v["postulacionId"])
    api("POST", f"/internal/postulaciones/{pid}/estado", json={"estado": "En extracción", "actor": "ia"})
    try:
        post = api("GET", f"/internal/postulaciones/{pid}")
        res = extractor.extraer(os.path.join(UPLOADS, post["archivo_path"]))
        t = res["tokens"]
        costo = (t["entrada"] * PRECIO_IN + t["salida"] * PRECIO_OUT) / 1e6
        api("POST", f"/internal/postulaciones/{pid}/extraccion", json={
            "datos": res["datos"], "confianza": res["confianza"], "resumen": res["resumen"],
            "anios_experiencia": res["anios_experiencia"], "costo_usd": round(costo, 5),
            "detalle": {"modelo": res["modelo"], "tokens": t}})
        baja = hay_baja_confianza(res["datos"], res["confianza"], UMBRAL_CONFIANZA)
        return {"extraccionOk": True, "bajaConfianza": baja}
    except Exception as e:
        log.exception("extracción falló para postulación %s", pid)
        api("POST", f"/internal/postulaciones/{pid}/incidencia", json={"origen": "ia", "detalle": str(e)[:500]})
        return {"extraccionOk": False, "bajaConfianza": False}


if __name__ == "__main__":
    run_worker("extraer-cv", extraer_cv)
