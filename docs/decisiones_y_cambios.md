# Decisiones de implementación y diferencias con los documentos iniciales

Este documento explica en qué se aparta el prototipo de la propuesta inicial, del modelo TO-BE y de los documentos de
requerimientos e historias de usuario (`docs/requerimientos/`). Donde esos documentos y el código no coinciden, lo que
describe este archivo es lo implementado.

## 1. Decisiones técnicas

| Propuesta inicial | Lo implementado | Por qué |
|---|---|---|
| n8n como posible automatizador | No se usa. El correo lo lee un servicio propio por IMAP | Menos piezas: todo el flujo queda en Flowable y los servicios |
| Flowable llama por REST a cada servicio | **External workers** de Flowable: cada servicio pide su trabajo por tópico | Servicios desacoplados, con reintentos y paralelismo nativos |
| Un solo modelo de Gemini | Cadena de modelos de respaldo (Gemini y Gemma) | La capa gratuita permite unas 20 peticiones por día y modelo |
| Interfaz de tareas de Flowable | Portal propio (FastAPI + Jinja2) | Permite mostrar el PDF junto a los datos editables y resaltar los de baja confianza |
| 6 contenedores | 8 contenedores (se suman GreenMail para el correo de pruebas y Caddy para HTTPS) | Recepción por correo (RF-02) y cifrado en tránsito (RNF-11) |
| Entrevista asistida por IA (prototipo) | **Retirada.** El proceso termina en «Pasa a entrevistas», igual que el BPMN TO-BE | Fuera del alcance del modelo; se priorizó el flujo de recepción a registro |

## 2. Diferencias con el modelo TO-BE

El BPMN ejecutado (`services/api/app/bpmn/reclutamiento.bpmn20.xml`, generado con `scripts/gen_bpmn.py`) conserva las
tareas, decisiones, carriles y finales del TO-BE (`docs/modelado_procesos/TO-BE/`). Hay dos variaciones declaradas:

1. **Aprobación automática:** una hoja de vida clasificada como `Cumple` y con confianza alta en todos los campos pasa al
   registro sin validación del analista. En el modelo, toda hoja válida pasa por el analista. Cualquier otra combinación
   (`Revisar`, `No cumple` o confianza baja) sí va a validación humana, y ningún candidato se descarta sin una persona.
2. **«Revisar perfil preseleccionado»** se integró en la tarea de validación del analista en lugar de ser una tarea aparte.

Además se agregaron elementos que el modelo no tenía: detección de duplicados, incidencias con reintentos del robot y
tarea de registro manual, escalación al coordinador a las 24 horas hábiles, avisos por correo al candidato y al personal,
página pública de empleos y gestión de vacantes.

## 3. Ajustes a los requerimientos y a las historias de usuario

- **Roles:** cuatro roles en el sistema: auxiliar, analista, coordinador y administrador.
- **Estados:** diez estados: Recibida, En extracción, En validación, Aprobada, Rechazada, Registrada, En entrevista,
  Descartada, Error y Duplicada (se agregó `Duplicada`, RF-05).
- **RF-10 (confianza):** se informa por campo en los datos personales y por bloque en formación, experiencia,
  habilidades e idiomas.
- **RF-19 (escalación):** cuenta 24 horas hábiles (lunes a viernes, 8:00 a 18:00, hora de Colombia, festivos
  configurables). Como Flowable solo admite duraciones corridas, el plazo hábil se convierte a duración real al iniciar
  cada proceso (`services/api/app/horario.py`). También puede contarse en horas corridas (`ESCALACION_MODO=corridas`).
- **HU-09 (decisión del coordinador):** incluye la rama de escalación y el aviso al candidato cuando avanza a entrevista.
- **HU-10 (RPA):** el robot busca primero al candidato por documento o correo y, si ya existe, no lo duplica.
- **HU-01 y HU-02:** la empresa crea vacantes con un formulario guiado (requisitos y pesos del puntaje) y cada vacante
  publicada tiene su página pública con formulario de postulación.
- **Diagrama de clases:** el actualizado está en `docs/clases.md` y `docs/diagramas/clases.png`.

## 4. Lo que no se hizo o no se midió

- **Usabilidad (RNF-14):** los tiempos de uso (postularse en 3 minutos o menos, validar en 2 minutos o menos) no se midieron con usuarios reales.
- **Correo real:** en local los correos van al buzón de pruebas GreenMail. Para enviar de verdad hay que configurar `SMTP_*` e `IMAP_*`.
- **Hojas de vida reales:** las pruebas usan 200 hojas de vida sintéticas (`datos_prueba/`).
- **LinkedIn:** no hay integración directa porque su API de postulaciones es solo para socios. La oferta se publica allí
  con «postularse en el sitio de la empresa», apuntando a la página pública del sistema.
