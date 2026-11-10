# Adaptaciones de terceros

Solo se adaptaron **ideas y criterios de redacción de prompts** de repos con licencia permisiva (MIT / Apache-2.0).
No se copió código. De repos AGPL, CPAL o sin licencia no se tomó nada textual.

| Qué se adaptó | Nuestro archivo | Repo origen | Archivo origen | Licencia |
|---|---|---|---|---|
| Reglas para extraer rangos de fechas (separadores, «actual/presente», solo año) | `services/ai/prompts/extraccion.txt` | interviewstreet/hiring-agent | `prompts/templates/work.jinja` | MIT |
| Cláusula de equidad (no inferir a partir de nombre, institución, ubicación) | `services/ai/prompts/extraccion.txt` | interviewstreet/hiring-agent | `roles/software_engineering_intern/criteria.jinja` | MIT |

Las ideas tomadas de Jonmaa/AI-Interview-Coach e IliaLarchenko/Interviewer solo se usaron en el prototipo de entrevista con IA, que se retiró del proyecto; sus prompts ya no forman parte del código.

## Solo ideas (sin adaptar texto ni código)

- **AryaXDG/RecruitAI** (sin archivo de licencia → todos los derechos reservados): la idea de una bandera de «relleno de palabras clave»
  se implementó con redacción y esquema propios (`relleno_palabras_clave`, aviso en la tarea de validación).
- **espetro/dits** (CPAL-1.0) y **reqcore** (AGPL-3.0; el repo no estaba accesible): no se tomó nada.

Apache-2.0 exige conservar el aviso de licencia si se copia código; como solo se tomaron ideas de redacción reescritas, no se incluye texto original.

## Tipografías incluidas en el portal (`services/api/app/static/fonts/`)

| Fuente | Uso | Origen | Licencia |
|---|---|---|---|
| Bricolage Grotesque (Regular, Bold) | Títulos | The Bricolage Grotesque Project Authors, github.com/ateliertriay/bricolage | SIL OFL 1.1 (`BricolageGrotesque-OFL.txt`) |
| Instrument Sans (Regular, Bold) | Texto e interfaz | The Instrument Sans Project Authors | SIL OFL 1.1 (`InstrumentSans-OFL.txt`) |

Se tomaron de la carpeta `canvas-design/canvas-fonts` del repositorio ComposioHQ/awesome-claude-skills y se empaquetaron para que el portal no dependa de internet.
La licencia OFL permite incluirlas en el proyecto siempre que se conserve su texto, y está junto a cada archivo.

## Criterios de diseño y redacción de la interfaz

Los textos de las pantallas públicas siguen la skill `no-ai-slop` (petergyang/no-ai-slop, MIT) y la dirección visual sigue `frontend-design` (anthropics/claude-plugins-official, Apache-2.0).
Solo se aplicaron como criterios editoriales y de diseño; no se copió código ni texto de ellas.
