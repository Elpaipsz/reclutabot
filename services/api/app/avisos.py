"""Avisos por correo al personal cuando Flowable les asigna una tarea (RF-29, HU-16).

Revisa periódicamente las tareas abiertas de cada grupo y envía un correo por cada tarea nueva (una sola vez por
tarea y grupo; una tarea escalada vuelve a avisar al grupo que la recibe). Los avisos no cambian estados ni decisiones
y no incluyen datos personales del candidato.
"""
import logging
import threading
import time

from . import db, flowable, servicios
from .config import AVISOS_INTERVALO, PORTAL_URL

log = logging.getLogger("avisos")
ROL_DEL_GRUPO = {"auxiliar": "auxiliar", "analista": "analista", "coordinador": "coordinador"}


def revisar():
    for grupo in ROL_DEL_GRUPO:
        try:
            tareas = flowable.tareas([grupo])
        except Exception as e:
            log.warning("no se pudieron leer las tareas de %s: %s", grupo, e)
            continue
        for t in tareas:
            nuevo = db.ex("INSERT INTO tarea_notificada(clave) VALUES (%s) ON CONFLICT DO NOTHING RETURNING clave",
                          (f"{t['id']}:{grupo}",))
            if not nuevo:
                continue
            numero = ""
            if t["postulacion_id"]:
                p = db.q1("SELECT numero FROM postulacion WHERE id=%s", (int(t["postulacion_id"]),))
                numero = p["numero"] if p else ""
            escalada = grupo == "coordinador" and t["definicion"] == "u_validar"
            destinos = [u["correo"] for u in db.q("SELECT correo FROM usuario WHERE rol=%s", (grupo,))]
            servicios.avisar_personal(destinos, "tarea_escalada" if escalada else "tarea_pendiente",
                                      {"tarea": t["nombre"], "numero": numero, "enlace": f"{PORTAL_URL}/app/tareas/{t['id']}",
                                       "tiempo": servicios.ESCALACION_TEXTO}, t["postulacion_id"])


def bucle():
    time.sleep(15)   # deja arrancar a Flowable
    while True:
        try:
            revisar()
        except Exception:
            log.exception("error revisando tareas pendientes")
        time.sleep(AVISOS_INTERVALO)


def iniciar():
    threading.Thread(target=bucle, daemon=True, name="avisos").start()
