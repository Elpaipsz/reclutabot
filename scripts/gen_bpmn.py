"""Genera el BPMN ejecutable (TO-BE) para Flowable: services/api/app/bpmn/reclutamiento.bpmn20.xml

Las tareas de servicio usan 'external-worker': Flowable publica el trabajo en un tópico y los
workers (IA, RPA, backend) lo toman por REST, lo ejecutan y lo completan.
"""
from pathlib import Path

SALIDA = Path(__file__).parent.parent / "services" / "api" / "app" / "bpmn" / "reclutamiento.bpmn20.xml"

# (id, nombre, tópico)
SERVICIOS = [
    ("t_extraer", "Extraer datos con IA", "extraer-cv"),
    ("t_evaluar", "Evaluar requisitos", "evaluar-requisitos"),
    ("t_registrar", "Registrar candidato (RPA)", "registrar-rpa"),
    ("t_est_validacion", "Estado: En validación", "estado-validacion"),
    ("t_est_aprobada", "Estado: Aprobada", "estado-aprobada"),
    ("t_est_rechazada", "Estado: Rechazada", "estado-rechazada"),
    ("t_est_registrada", "Estado: Registrada", "estado-registrada"),
    ("t_est_entrevista", "Estado: En entrevista", "estado-entrevista"),
    ("t_est_descartada", "Estado: Descartada", "estado-descartada"),
    ("t_est_descartada_inc", "Estado: Descartada (incidencia cerrada)", "estado-descartada"),
    ("t_est_error_ia", "Estado: Error (IA)", "estado-error"),
    ("t_est_error_rpa", "Estado: Error (RPA)", "estado-error"),
    ("t_escalar", "Escalar validación al coordinador", "escalar-validacion"),
    ("t_notif_info", "Pedir información al candidato", "notificar-pedir-info"),
    ("t_notif_nocontinua", "Notificar: no continúa", "notificar-no-continua"),
    ("t_notif_entrevista", "Notificar: avanza a entrevista", "notificar-entrevista"),
]
# (id, nombre, grupo)
USUARIO = [
    ("u_incidencia", "Atender incidencia de extracción", "auxiliar"),
    ("u_validar", "Validar hoja de vida", "analista"),
    ("u_registro_manual", "Registrar candidato manualmente", "auxiliar"),
    ("u_entrevista", "Decidir continuidad a entrevista", "coordinador"),
]
EXCLUSIVAS = {  # id: flujo por defecto
    "g_ext": "f_ext_ok", "g_inc": "f_inc_cerrar", "g_auto": "f_auto_no", "g_val": "f_val_info",
    "g_rpa": "f_rpa_error", "g_man": "f_man_cerrar", "g_ent": "f_ent_no",
}
# (id, origen, destino, condición | None)
FLUJOS = [
    ("f0", "inicio", "t_extraer", None),
    ("f1", "t_extraer", "g_ext", None),
    ("f_ext_err", "g_ext", "t_est_error_ia", "${extraccionOk == false}"),
    ("f_ext_ok", "g_ext", "t_evaluar", None),
    ("f2", "t_est_error_ia", "u_incidencia", None),
    ("f3", "u_incidencia", "g_inc", None),
    ("f_inc_reint", "g_inc", "t_extraer", "${decision == 'reintentar'}"),
    ("f_inc_cerrar", "g_inc", "t_est_descartada_inc", None),
    ("f4", "t_est_descartada_inc", "fin_incidencia", None),
    ("f_esc1", "b_escalar", "t_escalar", None),
    ("f_esc2", "t_escalar", "fin_escalada", None),
    ("f5", "t_evaluar", "g_auto", None),
    ("f_auto_si", "g_auto", "t_est_aprobada", "${clasificacion == 'Cumple' && bajaConfianza == false}"),
    ("f_auto_no", "g_auto", "t_est_validacion", None),
    ("f6", "t_est_validacion", "u_validar", None),
    ("f7", "u_validar", "g_val", None),
    ("f_val_ok", "g_val", "t_est_aprobada", "${decision == 'aprobar'}"),
    ("f_val_no", "g_val", "t_est_rechazada", "${decision == 'rechazar'}"),
    ("f_val_info", "g_val", "t_notif_info", None),
    ("f8", "t_notif_info", "u_validar", None),
    ("f9", "t_est_rechazada", "t_notif_nocontinua", None),
    ("f10", "t_est_aprobada", "t_registrar", None),
    ("f11", "t_registrar", "g_rpa", None),
    ("f_rpa_ok", "g_rpa", "t_est_registrada", "${rpaOk == true}"),
    ("f_rpa_error", "g_rpa", "t_est_error_rpa", None),
    ("f12", "t_est_error_rpa", "u_registro_manual", None),
    ("f13", "u_registro_manual", "g_man", None),
    ("f_man_ok", "g_man", "t_est_registrada", "${decision == 'registrado'}"),
    ("f_man_reint", "g_man", "t_registrar", "${decision == 'reintentar'}"),
    ("f_man_cerrar", "g_man", "t_est_descartada_inc", None),
    ("f14", "t_est_registrada", "u_entrevista", None),
    ("f15", "u_entrevista", "g_ent", None),
    ("f_ent_si", "g_ent", "t_est_entrevista", "${decision == 'continuar'}"),
    ("f_ent_no", "g_ent", "t_est_descartada", None),
    ("f16", "t_est_entrevista", "t_notif_entrevista", None),
    ("f17", "t_notif_entrevista", "fin_entrevista", None),
    ("f18", "t_est_descartada", "t_notif_nocontinua", None),
    ("f19", "t_notif_nocontinua", "fin_no_continua", None),
]


def generar():
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:flowable="http://flowable.org/bpmn" '
         'targetNamespace="http://reclutamiento/to-be">',
         '  <process id="reclutamiento" name="Reclutamiento automatizado (TO-BE)" isExecutable="true">',
         '    <startEvent id="inicio" name="Postulación recibida"/>']
    for i, n, t in SERVICIOS:
        L.append(f'    <serviceTask id="{i}" name="{n}" flowable:type="external-worker" flowable:topic="{t}"/>')
    for i, n, g in USUARIO:
        L.append(f'    <userTask id="{i}" name="{n}" flowable:candidateGroups="{g}"/>')
    for g, d in EXCLUSIVAS.items():
        L.append(f'    <exclusiveGateway id="{g}" default="{d}"/>')
    L.append('    <boundaryEvent id="b_escalar" name="Sin atender a tiempo" attachedToRef="u_validar" cancelActivity="false">'
             '<timerEventDefinition><timeDuration>${escalaTras}</timeDuration></timerEventDefinition></boundaryEvent>')
    for e, n in [("fin_escalada", "Tarea escalada"), ("fin_incidencia", "Cerrada por incidencia"), ("fin_entrevista", "Pasa a entrevistas"),
                 ("fin_no_continua", "No continúa")]:
        L.append(f'    <endEvent id="{e}" name="{n}"/>')
    for i, o, d, c in FLUJOS:
        if c:
            L.append(f'    <sequenceFlow id="{i}" sourceRef="{o}" targetRef="{d}">'
                     f'<conditionExpression xsi:type="tFormalExpression"><![CDATA[{c}]]></conditionExpression></sequenceFlow>')
        else:
            L.append(f'    <sequenceFlow id="{i}" sourceRef="{o}" targetRef="{d}"/>')
    L += ["  </process>", "</definitions>"]
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(L), encoding="utf-8")
    print("BPMN escrito en", SALIDA)


if __name__ == "__main__":
    generar()
