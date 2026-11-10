"""Workers de Flowable que viven en el backend: reglas, estados y notificaciones."""
import logging
import sys
import threading

from . import db, flowable, rules, servicios
from .config import UMBRAL_CONFIANZA

sys.path.insert(0, "/app")  # common/ se copia junto a la app en la imagen
from common.confianza import hay_baja_confianza  # noqa: E402
from common.flowable_worker import run_worker  # noqa: E402

log = logging.getLogger("workers")

ESTADOS = {
    "estado-validacion": "En validación", "estado-aprobada": "Aprobada", "estado-rechazada": "Rechazada",
    "estado-registrada": "Registrada", "estado-entrevista": "En entrevista", "estado-descartada": "Descartada",
    "estado-error": "Error",
}


def evaluar_postulacion(pid: int) -> dict:
    """Evalúa con los datos vigentes (validados si existen) y guarda el resultado."""
    e = servicios.datos_vigentes(pid)
    v = db.q1("SELECT v.requisitos, v.pesos FROM vacante v JOIN postulacion p ON p.vacante_id=v.id WHERE p.id=%s", (pid,))
    datos = e["datos_validados"] or e["datos"]
    res = rules.evaluar(datos, float(e["anios_experiencia"] or 0), v["requisitos"], v["pesos"])
    db.ex("UPDATE postulacion SET puntaje=%s, clasificacion=%s, actualizada_en=now() WHERE id=%s",
          (res["puntaje"], res["clasificacion"], pid))
    servicios.evento(pid, "sistema", "evaluacion", res["clasificacion"], {"puntaje": res["puntaje"], "criterios": res["criterios"]})
    return res


def _evaluar(v):
    pid = int(v["postulacionId"])
    res = evaluar_postulacion(pid)
    # RF-16: confianza baja se recalcula por si cambió el umbral
    e = servicios.datos_vigentes(pid)
    baja = hay_baja_confianza(e["datos"], e["confianza"], UMBRAL_CONFIANZA)
    return {"clasificacion": res["clasificacion"], "puntaje": res["puntaje"], "bajaConfianza": baja}


def _estado(estado):
    def h(v):
        servicios.set_estado(int(v["postulacionId"]), estado, "flowable")
        return {}
    return h


def _notif(plantilla):
    def h(v):
        servicios.notificar(int(v["postulacionId"]), plantilla)
        return {}
    return h


def _escalar(v):
    """RF-19: si nadie atendió la validación a tiempo, la tarea pasa también a la bandeja del coordinador."""
    pid = int(v["postulacionId"])
    tid = flowable.tarea_de_proceso(v["_procesoId"], "u_validar")
    if tid:
        flowable.agregar_grupo(tid, "coordinador")
        servicios.evento(pid, "flowable", "tarea_escalada", "coordinador", {"tras": servicios.ESCALACION_TEXTO})
    return {}


def iniciar_todos():
    tareas = {"evaluar-requisitos": _evaluar, "escalar-validacion": _escalar,
              "notificar-pedir-info": _notif("pedir_info"),
              "notificar-no-continua": _notif("no_continua"),
              "notificar-entrevista": _notif("entrevista")}
    tareas.update({t: _estado(s) for t, s in ESTADOS.items()})
    for topic, fn in tareas.items():
        threading.Thread(target=run_worker, args=(topic, fn), kwargs={"poll": 1.5}, daemon=True,
                         name=f"worker-{topic}").start()
