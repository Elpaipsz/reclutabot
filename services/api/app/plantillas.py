"""Plantillas de correo: valores por defecto y renderizado seguro (sin dependencias, fácil de probar).

Los textos pueden editarse desde la pantalla *Plantillas* (se guardan en la tabla `plantilla`); estos son los de respaldo.
"""
import re

DEFECTO = {
    "confirmacion": ("Recibimos tu postulación {numero}",
                     "Hola {nombre},\n\nRecibimos tu hoja de vida para la vacante «{vacante}». "
                     "Tu número de postulación es {numero}.\n\nTe contactaremos cuando avance el proceso.\n\nEquipo de Selección"),
    "pedir_info": ("Necesitamos información adicional - {numero}",
                   "Hola {nombre},\n\nPara continuar con tu postulación {numero} a «{vacante}» necesitamos que nos "
                   "envíes información adicional o una versión legible de tu hoja de vida. Responde a este correo.\n\nEquipo de Selección"),
    "entrevista": ("¡Avanzas a entrevista! - {numero}",
                   "Hola {nombre},\n\nTu perfil avanzó a la etapa de entrevistas para «{vacante}». "
                   "Pronto nos pondremos en contacto para acordar el horario.\n\nEquipo de Selección"),
    "no_continua": ("Resultado de tu postulación {numero}",
                    "Hola {nombre},\n\nGracias por postularte a «{vacante}». En esta ocasión tu proceso no continúa. "
                    "Conservaremos tu información conforme a nuestra política de tratamiento de datos.\n\nEquipo de Selección"),
    # avisos internos (sin datos personales del candidato: solo el número de postulación)
    "tarea_pendiente": ("Nueva tarea pendiente: {tarea}",
                        "Hola,\n\nTienes una tarea pendiente en el proceso de selección: «{tarea}» (postulación {numero}).\n"
                        "Ingresa para atenderla: {enlace}\n\nPor privacidad, este aviso no incluye datos del candidato."),
    "tarea_escalada": ("Tarea escalada a tu bandeja: {tarea}",
                       "Hola,\n\nLa tarea «{tarea}» (postulación {numero}) lleva más de {tiempo} sin atenderse y se escaló a tu bandeja.\n"
                       "Ingresa para resolverla o reasignarla: {enlace}"),
}

ETIQUETAS = {
    "confirmacion": "Confirmación de recepción (al candidato)",
    "pedir_info": "Solicitud de información adicional (al candidato)",
    "entrevista": "Aviso de paso a entrevista (al candidato)",
    "no_continua": "Resultado: no continúa (al candidato)",
    "tarea_pendiente": "Aviso de tarea pendiente (al personal)",
    "tarea_escalada": "Aviso de tarea escalada (al coordinador)",
}

_MARCADOR = re.compile(r"\{(\w+)\}")


def render(texto: str, ctx: dict) -> str:
    """Sustituye {clave} por su valor; las claves desconocidas se dejan intactas.

    No usa str.format a propósito: una plantilla editable por un usuario no debe poder acceder a atributos ({x.__class__})."""
    return _MARCADOR.sub(lambda m: str(ctx.get(m.group(1), m.group(0))), texto)
