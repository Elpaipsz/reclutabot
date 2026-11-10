# Trazabilidad: requisitos → implementación → evidencia

Estado: ✅ implementado y verificado · 🟡 implementado parcialmente · ⬜ no implementado.
"Evidencia" indica la prueba o el lugar donde se puede comprobar.

## Resultados medidos

| Métrica | Meta (requisito) | Resultado | Cómo se midió |
|---|---|---|---|
| Precisión de extracción de la IA | ≥ 90 % (RNF-05) | **99,6 %** (239/240 campos, 20 hojas de 4 formatos, incluidas escaneadas) | `scripts/evaluar_extraccion.py 20` contra verdad terreno |
| Tiempo de extracción p90 | ≤ 30 s (RNF-01) | **8,5 s** (2 casos aislados de ~110 s por modelos saturados; se corrigió con pausa de modelos) | idem |
| Tiempo de ciclo automático | ≤ 5 min (RNF-03) | **43 s** promedio (recepción → tarea humana o registro) | `scripts/carga.py 20 5` |
| Capacidad | 50 en un día, ≥ 5 en paralelo (RNF-04) | 20 postulaciones con 5 en paralelo en **173 s** (≈ 8,7 s c/u; 50 ≈ 7 min) | idem |
| Postulaciones sin estado final | 0 (RNF-06) | **0** | idem y escenarios e2e |
| Pruebas unitarias | parser y reglas (RNF-20) | **29 pasan** (experiencia, reglas, plantillas, confianza y horario hábil) | `pytest tests` |
| Pruebas punta a punta | aprobado, rechazado, falla del bot (RNF-20) | **9 escenarios** (los 3 pedidos + correo, duplicado, avisos y permisos, plantillas, histórico y escalación) | `scripts/e2e.py todos` y `scripts/e2e.py escalacion` |

## Requerimientos funcionales

| ID | Estado | Dónde / evidencia |
|---|---|---|
| RF-01 formulario con Habeas Data | ✅ | `templates/empleo.html`, `portal.postular`; e2e escenario 1 |
| RF-02 correo cada 5 min | ✅ | `correo.py` (IMAP; intervalo configurable, 30 s en demo); e2e escenario 4 |
| RF-03 PDF/DOCX ≤ 5 MB | ✅ | `servicios._validar_archivo` (extensión, tamaño y firma del archivo) |
| RF-04 archivo, número único, fecha y canal | ✅ | `servicios.crear_postulacion` (`POST-AAAA-nnnnnn`) |
| RF-05 duplicados 30 días | ✅ | por correo o hash del archivo; e2e escenario 5 |
| RF-06 inicia proceso en Flowable | ✅ | `flowable.iniciar` |
| RF-07 texto + OCR | ✅ | `pypdf`/`python-docx`; PDF escaneado se envía a Gemini (OCR) |
| RF-08 JSON estructurado | ✅ | `extractor.py` (esquema Pydantic) |
| RF-09 años de experiencia | ✅ | `common/experiencia.py` (fusiona periodos solapados; 5 pruebas unitarias) |
| RF-10 confianza por campo | ✅ | por **campo** en datos personales (nombre, correo, teléfono, documento, ubicación) y por bloque en formación, experiencia, habilidades e idiomas; los campos dudosos se resaltan en la tarea (`common/confianza.py`, 5 pruebas unitarias) |
| RF-11 validar esquema y reintentar ×2 | ✅ | `extractor.extraer` |
| RF-12 resumen ≤ 100 palabras | ✅ | `extraccion.resumen` |
| RF-13 comparar con requisitos | ✅ | `rules.evaluar` (8 pruebas unitarias) |
| RF-14 puntaje 0–100 con pesos | ✅ | pesos por vacante en BD |
| RF-15 Cumple / Revisar / No cumple | ✅ | `rules.evaluar` + compuerta BPMN `g_auto` |
| RF-16 tarea si Revisar o confianza < 0,8 | ✅ | compuerta `g_auto`; e2e escenarios 1–2 |
| RF-17 PDF junto a datos, resaltando baja confianza | ✅ | `templates/tarea.html` (bloques amarillos) |
| RF-18 aprobar/rechazar/pedir info, observación obligatoria | ✅ | validación en portal y restricción `CHECK` en la BD; e2e escenario 2 |
| RF-19 escalar a las 24 h | ✅ | temporizador en el BPMN (`b_escalar`); a las 24 h (configurable con `ESCALACION_ISO`) la tarea pasa también a la bandeja del coordinador y se le avisa; e2e escenario 10. Cuenta horas **hábiles** (`ESCALACION_MODO=habiles`, `app/horario.py`, probado en `tests/test_horario.py`); el plazo se traduce a una duración corrida porque Flowable no trae calendario laboral |
| RF-20 el bot registra con archivo adjunto | ✅ | `services/rpa/worker.py`; e2e escenario 1 |
| RF-21 captura y guarda el ID | ✅ | `postulacion.rrhh_id` |
| RF-22 reintenta ×3, luego tarea manual con captura | ✅ | e2e escenario 3 |
| RF-23 buscar antes de crear | ✅ | el bot busca por documento (o correo) |
| RF-24 BPMN TO-BE ejecutable por REST | ✅ | `services/api/app/bpmn/` (generado por `scripts/gen_bpmn.py`) |
| RF-25 estados definidos | ✅ | 10 estados (los 9 pedidos + `Duplicada`) |
| RF-26 tarea del líder para entrevista | ✅ | tarea `u_entrevista` |
| RF-27 correo de confirmación | ✅ | `servicios.notificar` |
| RF-28 resultado final al candidato, plantilla editable | ✅ | pantalla *Plantillas* (administrador); e2e escenario 8; el renderizado impide acceder a atributos internos |
| RF-29 avisar a RR.HH. de tareas pendientes / falla del bot | ✅ | `avisos.py`: correo por cada tarea nueva (también la de registro manual tras una falla del bot); e2e escenario 7 |
| RF-30 administrar vacantes, requisitos y pesos | ✅ | pantalla *Vacantes* |
| RF-31 tablero | ✅ | `/app` (estados, ciclo, intervención humana, costo de IA) |
| RF-32 exportar CSV | ✅ | `/app/postulaciones.csv` |

## Requerimientos no funcionales

| ID | Estado | Evidencia |
|---|---|---|
| RNF-01 a RNF-05 rendimiento, capacidad, calidad IA | ✅ | tabla de resultados |
| RNF-06 nada se pierde | ✅ | toda falla → `Error` + incidencia + tarea manual (e2e escenario 3) |
| RNF-07 tolerancia a fallas de Gemini y RR.HH. | ✅ | reintentos con espera creciente, tiempo límite por llamada y cadena de modelos de respaldo; bot con 3 intentos |
| RNF-08 acceso por rol | ✅ | login con JWT y roles; cada tarea solo la abre su rol (403 en otro caso); sin sesión no hay acceso; e2e escenario 7. Nota: la API REST de Flowable usa credenciales básicas y está pensada solo para la red interna |
| RNF-09 credenciales fuera del código | ✅ | `.env` (ignorado por git) y `.env.example` |
| RNF-10 Habeas Data | ✅ | casilla obligatoria; el administrador elimina datos personales a solicitud (anonimiza y borra archivo) |
| RNF-11 HTTPS y archivos no públicos | ✅ | HTTPS en `https://localhost:8443` (proxy Caddy con certificado interno: el navegador muestra una advertencia en local); archivos solo tras autenticación |
| RNF-12 trazabilidad | ✅ | tabla `evento` + historial de Flowable en el detalle de cada postulación |
| RNF-13 la IA no decide sola | ✅ | todo rechazo exige tarea humana y observación (restricción en BD); la decisión de continuidad la toma una persona |
| RNF-14 usabilidad | 🟡 | interfaz en español y de pocos pasos; **no se midieron** los tiempos con usuarios reales (postularse ≤ 3 min, validar ≤ 2 min): pendiente de cronometrar en el ensayo del video |
| RNF-15 un solo comando, reinicio automático | ✅ | `docker compose up -d --build`, `restart: unless-stopped` |
| RNF-16 todo en contenedores | ✅ | 7 servicios en `docker-compose.yml` |
| RNF-17 modular y documentado | ✅ | servicios separados, README, `/docs` (OpenAPI) |
| RNF-18 cambios sin tocar código | ✅ | requisitos y pesos en BD; prompts en `services/ai/prompts/` |
| RNF-19 estándares | ✅ | REST + JSON, BPMN 2.0 |
| RNF-20 pruebas | ✅ | 23 unitarias + 10 e2e |
| RNF-21 costo | ✅ | costo estimado por hoja de vida en `extraccion.costo_usd` y en el tablero |

## Historias de usuario

Las 18 historias están cubiertas. HU-01 a HU-11, HU-13, HU-14, HU-15 e HU-17: ✅ (vacantes, formulario, correo, validación documental,
extracción, validación humana, instancia por postulación, orquestación, decisión, RPA, consulta, trazabilidad,
duplicados, errores, tablero).
HU-12 (control de acceso): ✅ roles, autenticación, contraseñas cifradas con bcrypt, HTTPS.
HU-16 (notificaciones al analista): ✅ correo por tarea nueva, sin datos del candidato, con registro del envío en la tabla `notificacion`.
HU-18 (histórico de vacantes cerradas): ✅ pantalla *Histórico* con resultados finales por vacante y bloqueo de nuevas postulaciones.
