"""Lógica de negocio: recepción de postulaciones, estados, auditoría y notificaciones."""
import hashlib
import logging
import re
import smtplib
import uuid
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path

from . import db, flowable, horario, plantillas
from .config import (DIAS_DUPLICADO, ESCALACION_HORAS, ESCALACION_ISO, ESCALACION_MODO, FESTIVOS, HORARIO_FIN, HORARIO_INICIO, HORARIO_UTC, EXTENSIONES, MAX_BYTES, PORTAL_URL, SMTP_FROM, SMTP_HOST, SMTP_PORT, UPLOADS_DIR)

log = logging.getLogger("servicios")


class ErrorNegocio(Exception):
    """Error de validación con mensaje claro para el usuario (RF-03)."""


# ---------- auditoría ----------

def evento(postulacion_id, actor, accion, resultado=None, detalle=None):
    db.ex("INSERT INTO evento(postulacion_id,actor,accion,resultado,detalle) VALUES (%s,%s,%s,%s,%s)",
          (postulacion_id, actor, accion, resultado, db.J(detalle) if detalle is not None else None))


def set_estado(pid: int, estado: str, actor="sistema", detalle=None):
    db.ex("UPDATE postulacion SET estado=%s, actualizada_en=now() WHERE id=%s", (estado, pid))
    evento(pid, actor, "cambio_estado", estado, detalle)


def incidencia(pid, origen, detalle, captura=None):
    db.ex("INSERT INTO incidencia(postulacion_id,origen,detalle,captura_path) VALUES (%s,%s,%s,%s)",
          (pid, origen, detalle, captura))
    evento(pid, origen, "incidencia", "error", {"detalle": detalle[:300]})


# ---------- notificaciones ----------

def _texto_duracion(iso: str) -> str:
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", iso or "")
    if not m or not any(m.groups()):
        return iso
    d, h, mi = (int(x) if x else 0 for x in m.groups())
    partes = [f"{n} {u}{'s' if n != 1 else ''}" for n, u in ((d, "día"), (h, "hora"), (mi, "minuto")) if n]
    return " y ".join(partes)


def plazo_escalacion() -> str:
    """Duración ISO que se le da al temporizador de escalación de una validación nueva."""
    if ESCALACION_MODO != "habiles":
        return ESCALACION_ISO
    return horario.duracion_iso(
        horario.ahora_local(HORARIO_UTC), ESCALACION_HORAS, ini=HORARIO_INICIO, fin=HORARIO_FIN,
        festivos={date.fromisoformat(f) for f in FESTIVOS})


ESCALACION_TEXTO = (f"{ESCALACION_HORAS:g} horas hábiles ({HORARIO_INICIO}:00 a {HORARIO_FIN}:00, lunes a viernes)"
                    if ESCALACION_MODO == "habiles" else _texto_duracion(ESCALACION_ISO))


def plantilla_vigente(clave: str) -> tuple[str, str]:
    """Asunto y mensaje: la versión editada en pantalla si existe; si no, la de respaldo."""
    r = db.q1("SELECT asunto, cuerpo FROM plantilla WHERE clave=%s", (clave,))
    return (r["asunto"], r["cuerpo"]) if r else plantillas.DEFECTO[clave]


def enviar_correo(destino: str, asunto: str, cuerpo: str) -> str | None:
    """Envía por SMTP. Devuelve None si salió bien o el mensaje de error."""
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = SMTP_FROM, destino, asunto
    msg.set_content(cuerpo)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.send_message(msg)
        return None
    except Exception as e:
        log.warning("correo no enviado a %s: %s", destino, e)
        return str(e)[:300]


def notificar(pid: int, plantilla: str, extra: dict | None = None):
    """Correo al candidato de una postulación (RF-27, RF-28)."""
    p = db.q1("""SELECT p.numero, c.nombre, c.correo, v.titulo AS vacante FROM postulacion p
                 JOIN candidato c ON c.id=p.candidato_id JOIN vacante v ON v.id=p.vacante_id WHERE p.id=%s""", (pid,))
    asunto, cuerpo = plantilla_vigente(plantilla)
    ctx = {**p, **(extra or {})}
    error = enviar_correo(p["correo"], plantillas.render(asunto, ctx), plantillas.render(cuerpo, ctx))
    db.ex("INSERT INTO notificacion(postulacion_id,destinatario,plantilla,enviada,error) VALUES (%s,%s,%s,%s,%s)",
          (pid, p["correo"], plantilla, error is None, error))
    evento(pid, "sistema", "notificacion", "enviada" if error is None else "error", {"plantilla": plantilla})


def avisar_personal(destinos: list[str], plantilla: str, ctx: dict, pid=None):
    """Aviso interno a personas de RR.HH. (RF-29, HU-16). No incluye datos del candidato."""
    asunto, cuerpo = plantilla_vigente(plantilla)
    for d in destinos:
        error = enviar_correo(d, plantillas.render(asunto, ctx), plantillas.render(cuerpo, ctx))
        db.ex("INSERT INTO notificacion(postulacion_id,destinatario,plantilla,enviada,error) VALUES (%s,%s,%s,%s,%s)",
              (int(pid) if pid else None, d, plantilla, error is None, error))
    if pid:
        evento(int(pid), "sistema", "aviso_personal", plantilla, {"destinatarios": len(destinos)})


# ---------- recepción ----------

def _validar_archivo(nombre: str, contenido: bytes) -> str:
    ext = Path(nombre).suffix.lower()
    if ext not in EXTENSIONES:
        raise ErrorNegocio("Formato no permitido: solo se aceptan archivos PDF o DOCX.")
    if not contenido:
        raise ErrorNegocio("El archivo está vacío.")
    if len(contenido) > MAX_BYTES:
        raise ErrorNegocio("El archivo supera el tamaño máximo de 5 MB.")
    if ext == ".pdf" and not contenido.startswith(b"%PDF"):
        raise ErrorNegocio("El archivo no es un PDF válido.")
    if ext == ".docx" and not contenido.startswith(b"PK"):
        raise ErrorNegocio("El archivo no es un DOCX válido.")
    return ext


def crear_postulacion(*, vacante_id: int, nombre: str, correo: str, telefono: str, acepta_datos: bool,
                      archivo_nombre: str, contenido: bytes, canal: str) -> dict:
    """Valida, almacena, detecta duplicados e inicia el proceso en Flowable (RF-01…RF-06)."""
    nombre, correo, telefono = nombre.strip(), correo.strip().lower(), (telefono or "").strip()
    if not nombre or "@" not in correo:
        raise ErrorNegocio("Nombre y correo válidos son obligatorios.")
    if not acepta_datos:
        raise ErrorNegocio("Debes aceptar la política de tratamiento de datos personales.")
    v = db.q1("SELECT * FROM vacante WHERE id=%s", (vacante_id,))
    if not v:
        raise ErrorNegocio("La vacante no existe.")
    if v["estado"] != "activa":
        raise ErrorNegocio("La vacante está cerrada y no admite postulaciones.")
    ext = _validar_archivo(archivo_nombre, contenido)
    h = hashlib.sha256(contenido).hexdigest()

    dup = db.q1("""SELECT p.id FROM postulacion p JOIN candidato c ON c.id=p.candidato_id
                   WHERE p.vacante_id=%s AND p.estado<>'Duplicada'
                     AND p.recibida_en > now() - make_interval(days => %s)
                     AND (lower(c.correo)=%s OR p.archivo_hash=%s) ORDER BY p.id LIMIT 1""",
                (vacante_id, DIAS_DUPLICADO, correo, h))

    cand = db.q1("SELECT id FROM candidato WHERE lower(correo)=%s ORDER BY id DESC LIMIT 1", (correo,))
    if cand:
        db.ex("UPDATE candidato SET nombre=%s, telefono=%s WHERE id=%s", (nombre, telefono, cand["id"]))
        cid = cand["id"]
    else:
        cid = db.ex("INSERT INTO candidato(nombre,correo,telefono,acepta_datos,acepta_en) VALUES (%s,%s,%s,TRUE,now()) RETURNING id",
                    (nombre, correo, telefono))["id"]

    rel = f"{datetime.now():%Y%m}/{uuid.uuid4().hex}{ext}"
    destino = Path(UPLOADS_DIR) / rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)

    p = db.ex("""INSERT INTO postulacion(numero,vacante_id,candidato_id,canal,estado,archivo_path,archivo_hash,duplicada_de)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
              (f"TMP-{uuid.uuid4().hex[:8]}", vacante_id, cid, canal, "Duplicada" if dup else "Recibida", rel, h,
               dup["id"] if dup else None))
    pid = p["id"]
    numero = f"POST-{datetime.now():%Y}-{pid:06d}"
    db.ex("UPDATE postulacion SET numero=%s WHERE id=%s", (numero, pid))
    evento(pid, "candidato", "recibida", canal, {"archivo": archivo_nombre, "bytes": len(contenido)})

    if dup:
        evento(pid, "sistema", "duplicada", "sin proceso", {"original": dup["id"]})
        return {"id": pid, "numero": numero, "duplicada": True, "original": dup["id"]}

    notificar(pid, "confirmacion")                                    # RF-27
    try:
        proceso = flowable.iniciar(pid, {"vacanteId": vacante_id, "bajaConfianza": False, "escalaTras": plazo_escalacion()})  # RF-06
        db.ex("UPDATE postulacion SET proceso_id=%s WHERE id=%s", (proceso, pid))
        evento(pid, "sistema", "proceso_iniciado", "ok", {"proceso": proceso})
    except Exception as e:                                            # RNF-06: nada se pierde
        log.exception("no se pudo iniciar el proceso")
        set_estado(pid, "Error", "sistema")
        incidencia(pid, "flowable", f"No se pudo iniciar el proceso en Flowable: {e}")
    return {"id": pid, "numero": numero, "duplicada": False}


# ---------- datos para la tarea humana ----------

def datos_vigentes(pid: int) -> dict | None:
    e = db.q1("SELECT * FROM extraccion WHERE postulacion_id=%s ORDER BY id DESC LIMIT 1", (pid,))
    return e
