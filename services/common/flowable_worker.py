"""Cliente mínimo de external workers de Flowable (REST)."""
import logging
import os
import threading
import time
import uuid
from typing import Callable

import httpx

log = logging.getLogger("worker")
logging.getLogger("httpx").setLevel(logging.WARNING)

BASE = os.getenv("FLOWABLE_URL", "http://flowable:8080/flowable-rest")
AUTH = (os.getenv("FLOWABLE_USER", "rest-admin"), os.getenv("FLOWABLE_PASSWORD", "test"))


def _typed(name, value):
    if isinstance(value, bool):
        t = "boolean"
    elif isinstance(value, int):
        t = "integer"
    elif isinstance(value, float):
        t = "double"
    elif isinstance(value, (dict, list)):
        t = "json"
    else:
        t = "string"
    return {"name": name, "value": value, "type": t}


def job_vars(job: dict) -> dict:
    d = {v["name"]: v.get("value") for v in job.get("variables", [])}
    d["_procesoId"] = job.get("processInstanceId")
    return d


def run_worker(topic: str, handler: Callable[[dict], dict], lock="PT5M", poll=2.0, worker_id=None):
    """Bucle bloqueante: toma trabajos del tópico y los completa con las variables devueltas.

    handler(vars) -> dict de variables de salida. Si lanza excepción, el trabajo se
    marca fallido (sin reintentos: los reintentos y la ruta de error los decide el handler/BPMN)."""
    wid = worker_id or f"{topic}-{uuid.uuid4().hex[:6]}"
    client = httpx.Client(base_url=f"{BASE}/external-job-api", auth=AUTH, timeout=120)
    log.info("worker %s escuchando tópico %s", wid, topic)
    while True:
        try:
            r = client.post("/acquire/jobs", json={
                "topic": topic, "lockDuration": lock, "numberOfTasks": 5, "workerId": wid})
            r.raise_for_status()
            jobs = r.json()
        except Exception as e:  # Flowable aún no disponible, etc.
            log.warning("acquire falló: %s", e)
            time.sleep(5)
            continue
        if not jobs:
            time.sleep(poll)
            continue
        for job in jobs:
            threading.Thread(target=_process, args=(client, wid, job, handler), daemon=True).start()


def _process(client, wid, job, handler):
    jid = job["id"]
    try:
        out = handler(job_vars(job)) or {}
        body = {"workerId": wid, "variables": [_typed(k, v) for k, v in out.items()]}
        client.post(f"/acquire/jobs/{jid}/complete", json=body).raise_for_status()
    except Exception as e:
        log.exception("job %s falló", jid)
        try:
            client.post(f"/acquire/jobs/{jid}/fail", json={
                "workerId": wid, "errorMessage": str(e)[:200], "errorDetails": repr(e)[:2000],
                "retries": 0}).raise_for_status()
        except Exception:
            log.exception("no se pudo marcar fallo del job %s", jid)
