"""Lector del buzón de postulaciones por IMAP (RF-02, HU-03)."""
import email
import imaplib
import logging
import re
import threading
import time
from email.header import decode_header, make_header
from email.utils import parseaddr

from . import db, servicios
from .config import IMAP_HOST, IMAP_INTERVALO, IMAP_PASSWORD, IMAP_PORT, IMAP_SSL, IMAP_USER

log = logging.getLogger("correo")
CODIGO = re.compile(r"\b([A-Z]{2,6}-\d{2,5})\b")


def _texto(h):
    return str(make_header(decode_header(h or "")))


def procesar_mensaje(msg) -> str:
    """Convierte un correo en postulación. Devuelve un resumen del resultado."""
    asunto = _texto(msg["Subject"])
    nombre, remitente = parseaddr(_texto(msg["From"]))
    nombre = nombre or remitente.split("@")[0]
    m = CODIGO.search(asunto)
    if not m:
        servicios.incidencia(None, "correo", f"Correo de {remitente} sin código de vacante en el asunto: «{asunto}»")
        return "sin código de vacante"
    v = db.q1("SELECT id FROM vacante WHERE codigo=%s", (m.group(1),))
    if not v:
        servicios.incidencia(None, "correo", f"Código de vacante desconocido «{m.group(1)}» (de {remitente})")
        return "vacante desconocida"
    adjunto = None
    for parte in msg.walk():
        fn = parte.get_filename()
        if fn and fn.lower().endswith((".pdf", ".docx")):
            adjunto = (_texto(fn), parte.get_payload(decode=True))
            break
    if not adjunto:
        servicios.incidencia(None, "correo", f"Correo de {remitente} sin hoja de vida adjunta (PDF/DOCX)")
        return "sin adjunto"
    try:
        r = servicios.crear_postulacion(vacante_id=v["id"], nombre=nombre, correo=remitente, telefono="",
                                        acepta_datos=True, archivo_nombre=adjunto[0], contenido=adjunto[1], canal="correo")
        return f"{r['numero']}{' (duplicada)' if r['duplicada'] else ''}"
    except servicios.ErrorNegocio as e:
        servicios.incidencia(None, "correo", f"Correo de {remitente} rechazado: {e}")
        return f"rechazado: {e}"


def revisar_buzon():
    """Lee mensajes NO LEÍDOS; al procesarlos quedan marcados (no se procesa dos veces)."""
    M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) if IMAP_SSL else imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
    try:
        M.login(IMAP_USER, IMAP_PASSWORD)
        M.select("INBOX")
        _, data = M.search(None, "UNSEEN")
        for num in data[0].split():
            _, raw = M.fetch(num, "(BODY.PEEK[])")
            msg = email.message_from_bytes(raw[0][1])
            mid = msg["Message-ID"] or f"{msg['From']}|{msg['Date']}|{msg['Subject']}"
            if db.q1("SELECT 1 FROM evento WHERE accion='correo_procesado' AND resultado=%s", (mid,)):
                M.store(num, "+FLAGS", "\\Seen")
                continue
            try:
                res = procesar_mensaje(msg)
            except Exception as e:
                log.exception("error procesando correo")
                servicios.incidencia(None, "correo", f"Error inesperado procesando correo: {e}")
                res = "error"
            db.ex("INSERT INTO evento(actor,accion,resultado,detalle) VALUES ('correo','correo_procesado',%s,%s)",
                  (mid, db.J({"resultado": res})))
            M.store(num, "+FLAGS", "\\Seen")
            log.info("correo procesado: %s", res)
    finally:
        try:
            M.logout()
        except Exception:
            pass


def bucle():
    while True:
        try:
            revisar_buzon()
        except Exception as e:
            log.warning("buzón no disponible: %s", e)
        time.sleep(IMAP_INTERVALO)


def iniciar():
    threading.Thread(target=bucle, daemon=True, name="imap").start()
