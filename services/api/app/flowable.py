"""Cliente REST de Flowable (despliegue, instancias y tareas humanas)."""
import logging
import time
from pathlib import Path

import httpx

from .config import FLOWABLE_AUTH, FLOWABLE_URL

log = logging.getLogger("flowable")
PROCESS_KEY = "reclutamiento"
BPMN = Path(__file__).parent / "bpmn" / "reclutamiento.bpmn20.xml"


def _c():
    return httpx.Client(base_url=f"{FLOWABLE_URL}/service", auth=FLOWABLE_AUTH, timeout=30)


def _tipo(v):
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "double"
    return "string"


def desplegar(reintentos=30):
    """Despliega el BPMN (el filtro de duplicados evita versiones repetidas)."""
    for i in range(reintentos):
        try:
            with _c() as c:
                r = c.post("/repository/deployments", params={"enableDuplicateFiltering": "true"},
                           files={"file": (BPMN.name, BPMN.read_bytes(), "application/xml")})
                r.raise_for_status()
                log.info("BPMN desplegado: %s", r.json().get("id"))
                return
        except Exception as e:
            log.warning("Flowable no listo (%s), reintento %d", e, i + 1)
            time.sleep(4)
    raise RuntimeError("No se pudo desplegar el BPMN en Flowable")


def iniciar(postulacion_id: int, variables: dict) -> str:
    vs = [{"name": "postulacionId", "value": postulacion_id, "type": "integer"}]
    vs += [{"name": k, "value": v, "type": _tipo(v)} for k, v in variables.items()]
    with _c() as c:
        r = c.post("/runtime/process-instances", json={
            "processDefinitionKey": PROCESS_KEY, "businessKey": str(postulacion_id), "variables": vs})
        r.raise_for_status()
        return r.json()["id"]


def tareas(grupos: list[str]) -> list[dict]:
    """Tareas abiertas para los grupos dados, con el id de postulación."""
    out = []
    with _c() as c:
        for g in grupos:
            r = c.get("/runtime/tasks", params={"candidateGroup": g, "includeProcessVariables": "true", "size": 200})
            r.raise_for_status()
            for t in r.json()["data"]:
                v = {x["name"]: x["value"] for x in t.get("variables", [])}
                out.append({"id": t["id"], "nombre": t["name"], "definicion": t["taskDefinitionKey"],
                            "grupo": g, "asignada": t.get("assignee"), "creada": t["createTime"],
                            "postulacion_id": v.get("postulacionId")})
    return sorted(out, key=lambda t: t["creada"])


def tarea(task_id: str) -> dict:
    with _c() as c:
        r = c.get(f"/runtime/tasks/{task_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        t = r.json()
        # el recurso individual no incluye variables del proceso: se piden aparte
        rv = c.get(f"/runtime/process-instances/{t['processInstanceId']}/variables")
        rv.raise_for_status()
        t["vars"] = {x["name"]: x["value"] for x in rv.json()}
        return t


def tarea_de_proceso(proceso_id: str, definicion: str) -> str | None:
    with _c() as c:
        r = c.get("/runtime/tasks", params={"processInstanceId": proceso_id, "taskDefinitionKey": definicion})
        r.raise_for_status()
        d = r.json()["data"]
        return d[0]["id"] if d else None


def agregar_grupo(task_id: str, grupo: str):
    """Hace visible una tarea a otro grupo (escalación)."""
    with _c() as c:
        r = c.post(f"/runtime/tasks/{task_id}/identitylinks", json={"group": grupo, "type": "candidate"})
        if r.status_code not in (201, 409):
            r.raise_for_status()


def completar(task_id: str, usuario: str, variables: dict):
    with _c() as c:
        r = c.post(f"/runtime/tasks/{task_id}", json={"action": "claim", "assignee": usuario})
        if r.status_code not in (200, 409):   # 409: ya reclamada
            r.raise_for_status()
        vs = [{"name": k, "value": v, "type": _tipo(v)} for k, v in variables.items()]
        r = c.post(f"/runtime/tasks/{task_id}", json={"action": "complete", "variables": vs})
        r.raise_for_status()


def historial(proceso_id: str) -> list[dict]:
    with _c() as c:
        r = c.get("/history/historic-activity-instances",
                  params={"processInstanceId": proceso_id, "size": 200, "sort": "startTime", "order": "asc"})
        r.raise_for_status()
        return [{"actividad": a.get("activityName") or a["activityId"], "tipo": a["activityType"],
                 "inicio": a["startTime"], "fin": a.get("endTime"), "asignado": a.get("assignee")}
                for a in r.json()["data"] if a["activityType"] in ("userTask", "serviceTask", "startEvent", "endEvent")]
