**1. Actores del sistema**

El sistema contempla cuatro actores principales, correspondientes a los participantes del proceso de reclutamiento.

**1.1. Candidato**

Es la persona interesada en participar en un proceso de selección para una vacante laboral.

**Responsabilidades:**

- Consultar las vacantes disponibles.

- Completar el formulario de postulación.

- Adjuntar su hoja de vida.

- Proporcionar información de contacto.

- Autorizar el tratamiento de sus datos personales.

El candidato también podrá enviar su postulación mediante el correo electrónico destinado a la recepción de hojas de vida.

**1.2. Auxiliar de Recursos Humanos**

Es el responsable del apoyo operativo y administrativo del proceso de reclutamiento.

En el proceso automatizado, su participación se concentra en la supervisión de postulaciones, gestión de vacantes y atención de incidencias, en lugar de realizar manualmente todas las actividades repetitivas.

**Responsabilidades:**

- Registrar y gestionar las vacantes disponibles.

- Supervisar la recepción de postulaciones.

- Consultar las postulaciones registradas.

- Identificar y gestionar incidencias documentales.

- Verificar los resultados del registro automático.

- Consultar los estados e historiales de las postulaciones.

**1.3. Analista de selección**

Es el responsable de revisar la información de los candidatos y evaluar su cumplimiento de los requisitos establecidos para cada vacante.

La Inteligencia Artificial facilita su trabajo mediante la extracción automática de información, pero no reemplaza su criterio profesional.

**Responsabilidades:**

- Revisar la información extraída por la IA.

- Comparar los datos con la hoja de vida original.

- Corregir posibles errores de extracción.

- Verificar formación académica, experiencia y habilidades.

- Determinar si el candidato cumple los requisitos mínimos.

- Registrar los resultados de la evaluación.

**1.4. Coordinador de selección**

Es el responsable de revisar los perfiles que superaron la evaluación inicial y decidir cuáles continúan hacia la etapa de entrevistas.

**Responsabilidades:**

- Consultar los candidatos preseleccionados.

- Revisar los perfiles y resultados de validación.

- Evaluar la conveniencia de continuar con cada candidato.

- Aprobar o rechazar la continuidad hacia entrevistas.

- Consultar el estado y los indicadores generales del proceso.

**2. Historias de usuario**

**Módulo 1. Gestión de vacantes y postulaciones**

**HU-01. Gestión de vacantes Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero crear y gestionar vacantes laborales con sus respectivos requisitos para que los candidatos puedan postularse a ofertas disponibles.

**Criterios de aceptación:**

1.  El sistema permite registrar vacantes con título, descripción y requisitos mínimos.

2.  Cada vacante puede encontrarse en estado activa o cerrada.

3.  Únicamente las vacantes activas admiten postulaciones.

4.  El auxiliar puede consultar y actualizar la información de las vacantes.

5.  Los datos se almacenan permanentemente en la base de datos.

**Tareas técnicas:**

- HU01-T01. Diseñar la tabla de vacantes en PostgreSQL.

- HU01-T02. Desarrollar los endpoints CRUD utilizando FastAPI.

- HU01-T03. Implementar formularios de creación y edición.

- HU01-T04. Implementar la gestión de estados de las vacantes.

- HU01-T05. Realizar pruebas funcionales.

**HU-02. Postulación mediante formulario web Actor:** Candidato  
**Prioridad:** Alta **Historia de usuario:** Como candidato, quiero postularme a una vacante mediante un formulario web y adjuntar mi hoja de vida para participar en el proceso de selección.

**Criterios de aceptación:**

1.  El sistema presenta las vacantes activas.

2.  El candidato puede ingresar nombre, correo electrónico y teléfono.

3.  Se permite adjuntar una hoja de vida en formato PDF.

4.  Se validan los campos obligatorios y las características del documento.

5.  El formulario presenta la autorización correspondiente para el tratamiento de datos personales.

6.  El candidato recibe una confirmación de recepción.

**Tareas técnicas:**

- HU02-T01. Diseñar la interfaz de postulación.

- HU02-T02. Crear el endpoint de recepción de postulaciones.

- HU02-T03. Implementar la carga segura de documentos PDF.

- HU02-T04. Validar los datos suministrados.

- HU02-T05. Registrar la postulación y su autorización.

- HU02-T06. Realizar pruebas de recepción.

**HU-03. Recepción automática de postulaciones por correo electrónico Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que las hojas de vida recibidas por correo electrónico sean procesadas automáticamente para evitar su descarga y registro manual.

**Criterios de aceptación:**

1.  El sistema consulta la cuenta de correo destinada a recibir postulaciones.

2.  Se identifican mensajes nuevos con documentos adjuntos.

3.  Se identifica la vacante mediante un código o asunto previamente establecido.

4.  El documento y los datos del remitente se almacenan.

5.  No se procesa dos veces el mismo correo.

6.  Los mensajes que presentan errores quedan registrados como incidencias.

**Tareas técnicas:**

- HU03-T01. Configurar la conexión al servicio de correo.

- HU03-T02. Implementar el servicio de detección de mensajes nuevos.

- HU03-T03. Descargar y validar los archivos adjuntos.

- HU03-T04. Convertir los datos recibidos al formato estándar de postulación.

- HU03-T05. Implementar controles contra duplicados.

- HU03-T06. Realizar pruebas de integración.

**HU-04. Validación inicial de documentos Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que el sistema valide automáticamente los documentos recibidos para identificar las postulaciones que pueden continuar y aquellas que requieren atención.

**Criterios de aceptación:**

1.  El sistema verifica que la vacante exista y se encuentre activa.

2.  El documento debe cumplir con el formato y tamaño establecidos.

3.  Se comprueba que el archivo pueda abrirse y procesarse.

4.  Los documentos inválidos no continúan hacia la extracción mediante IA.

5.  El motivo de la incidencia queda registrado.

6.  El auxiliar puede consultar las incidencias documentales.

**Tareas técnicas:**

- HU04-T01. Implementar el servicio de validación documental.

- HU04-T02. Configurar las reglas de negocio.

- HU04-T03. Registrar los resultados de validación.

- HU04-T04. Integrar la decisión con la compuerta BPMN correspondiente.

- HU04-T05. Crear la consulta de incidencias.

- HU04-T06. Realizar pruebas de validación.

**Módulo 2. Inteligencia Artificial**

**HU-05. Extracción automática de información de hojas de vida Actor:** Analista de selección  
**Prioridad:** Alta **Historia de usuario:** Como analista de selección, quiero que la Inteligencia Artificial extraiga automáticamente la información relevante de las hojas de vida para reducir el tiempo dedicado a su lectura y transcripción.

**Criterios de aceptación:**

1.  El sistema procesa documentos PDF compatibles.

2.  La IA extrae información personal, formación académica, experiencia y habilidades.

3.  Los resultados se presentan en una estructura JSON definida.

4.  Los datos no identificados se señalan como faltantes.

5.  Se conserva el documento original.

6.  La IA no decide si un candidato cumple los requisitos ni si continúa a entrevistas.

**Tareas técnicas:**

- HU05-T01. Implementar extracción de texto desde PDF.

- HU05-T02. Configurar la integración con Gemini API.

- HU05-T03. Diseñar el prompt de extracción.

- HU05-T04. Definir el esquema de información estructurada.

- HU05-T05. Crear el servicio de extracción de datos.

- HU05-T06. Validar la respuesta de la IA.

- HU05-T07. Probar diferentes formatos de hojas de vida.

**HU-06. Validación humana de información extraída Actor:** Analista de selección  
**Prioridad:** Alta **Historia de usuario:** Como analista de selección, quiero revisar y corregir los datos extraídos por la Inteligencia Artificial para garantizar que coincidan con la información real de la hoja de vida.

**Criterios de aceptación:**

1.  El sistema muestra la hoja de vida original.

2.  Se presentan los datos obtenidos por la IA.

3.  El analista puede corregir información incorrecta.

4.  Se permite aprobar la información validada.

5.  Las correcciones quedan registradas.

6.  El sistema conserva la identidad del responsable de la validación.

**Tareas técnicas:**

- HU06-T01. Diseñar la interfaz de validación.

- HU06-T02. Implementar visualización del PDF original.

- HU06-T03. Crear campos editables para los datos extraídos.

- HU06-T04. Guardar las correcciones.

- HU06-T05. Integrar la aprobación con Flowable.

- HU06-T06. Realizar pruebas de validación.

**Módulo 3. Orquestación mediante BPMS**

**HU-07. Seguimiento automático del proceso de postulación Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que cada postulación recibida quede registrada y gestionada mediante un proceso automatizado para conocer su estado sin realizar un seguimiento manual de cada actividad.

**Criterios de aceptación:**

1.  Cada postulación genera una instancia de proceso en Flowable.

2.  Cada instancia posee un identificador único.

3.  El proceso se encuentra relacionado con la vacante correspondiente.

4.  Flowable controla las actividades según el BPMN TO-BE.

5.  El auxiliar puede consultar el estado de cada postulación.

**Tareas técnicas:**

- HU07-T01. Instalar y configurar Flowable.

- HU07-T02. Desplegar el BPMN TO-BE ejecutable.

- HU07-T03. Integrar FastAPI con Flowable.

- HU07-T04. Implementar el inicio automático de instancias.

- HU07-T05. Almacenar los identificadores del proceso.

- HU07-T06. Probar el inicio y seguimiento de postulaciones.

**HU-08. Automatización de actividades del reclutamiento Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que el sistema coordine automáticamente la extracción de información, las validaciones humanas y el registro de candidatos para reducir las tareas operativas y mantener organizado el proceso.

**Criterios de aceptación:**

1.  Flowable activa el componente de IA cuando corresponde.

2.  Los resultados se relacionan con la postulación correcta.

3.  El analista recibe una tarea para revisar la información.

4.  Las decisiones humanas determinan la continuación del proceso.

5.  El registro mediante RPA se ejecuta únicamente cuando corresponde.

6.  Cada actividad actualiza el estado de la postulación.

**Tareas técnicas:**

- HU08-T01. Configurar tareas de servicio en el BPMN.

- HU08-T02. Implementar los servicios de integración.

- HU08-T03. Definir las variables del proceso.

- HU08-T04. Integrar Flowable con IA y RPA.

- HU08-T05. Configurar las transiciones entre actividades.

- HU08-T06. Realizar pruebas de integración de extremo a extremo.

**HU-09. Evaluación de requisitos y decisión de continuidad Actores:** Analista de selección y coordinador de selección  
**Prioridad:** Alta **Historia de usuario:** Como analista de selección, quiero evaluar el cumplimiento de requisitos de cada candidato para identificar los perfiles que pueden ser revisados por el coordinador de selección.

Como coordinador de selección, quiero revisar los perfiles preseleccionados y registrar mi decisión para determinar cuáles continúan hacia entrevistas.

**Criterios de aceptación:**

1.  El analista recibe las postulaciones pendientes de evaluación.

2.  Puede revisar la información validada y los requisitos de la vacante.

3.  Puede registrar si el candidato cumple o no los requisitos mínimos.

4.  Las postulaciones que cumplen llegan a la bandeja del coordinador.

5.  El coordinador puede aprobar o rechazar la continuidad hacia entrevistas.

6.  El sistema registra las decisiones, fechas y responsables.

7.  Flowable dirige las instancias por las rutas correspondientes.

**Tareas técnicas:**

- HU09-T01. Configurar las tareas humanas en Flowable.

- HU09-T02. Crear la bandeja de evaluación del analista.

- HU09-T03. Desarrollar el formulario de cumplimiento de requisitos.

- HU09-T04. Crear la bandeja de revisión del coordinador.

- HU09-T05. Implementar el registro de decisiones.

- HU09-T06. Configurar las compuertas exclusivas del BPMN.

- HU09-T07. Probar las rutas de aprobación y cierre.

**Módulo 4. Automatización mediante RPA**

**HU-10. Registro automático de candidatos Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que un robot registre automáticamente los datos validados de los candidatos en el sistema administrativo para evitar la digitación manual y reducir posibles errores de transcripción.

**Criterios de aceptación:**

1.  El RPA recibe únicamente información previamente validada y autorizada para el registro.

2.  El robot accede a la aplicación web de Recursos Humanos simulada.

3.  Completa automáticamente los campos del formulario.

4.  Guarda la información y verifica el resultado.

5.  Comunica a Flowable si el registro fue exitoso.

6.  No genera registros duplicados.

**Tareas técnicas:**

- HU10-T01. Desarrollar el sistema web simulado de Recursos Humanos.

- HU10-T02. Implementar el robot con Python y Playwright.

- HU10-T03. Configurar el acceso del robot.

- HU10-T04. Crear el servicio de activación del RPA.

- HU10-T05. Implementar la validación de registros existentes.

- HU10-T06. Integrar los resultados con Flowable.

- HU10-T07. Realizar pruebas funcionales.

**Módulo 5. Consulta y administración**

**HU-11. Consulta del estado de postulaciones Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero consultar el estado de las postulaciones para conocer qué actividades se han completado y cuáles están pendientes.

**Criterios de aceptación:**

1.  El sistema presenta un listado de postulaciones.

2.  Cada registro muestra candidato, vacante, fecha y estado.

3.  Se puede consultar el detalle de una postulación.

4.  Los estados se actualizan conforme avanza el proceso.

5.  La consulta respeta los permisos establecidos.

**Tareas técnicas:**

- HU11-T01. Crear endpoints para consultar postulaciones.

- HU11-T02. Diseñar el listado de postulaciones.

- HU11-T03. Implementar la vista de detalle.

- HU11-T04. Integrar la consulta con Flowable.

- HU11-T05. Desarrollar filtros por estado y vacante.

- HU11-T06. Realizar pruebas funcionales.

**HU-12. Control de acceso según responsabilidades Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Media **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que el sistema controle el acceso a las funcionalidades según las responsabilidades de cada participante para proteger la información de los candidatos.

**Criterios de aceptación:**

1.  Los usuarios internos deben autenticarse.

2.  El sistema diferencia los permisos del auxiliar, analista y coordinador.

3.  Cada usuario accede únicamente a las funciones que le corresponden.

4.  Las hojas de vida y los datos personales están protegidos.

5.  Las contraseñas se almacenan mediante mecanismos seguros.

6.  Las acciones de validación y decisión quedan asociadas al usuario correspondiente.

**Tareas técnicas:**

- HU12-T01. Implementar autenticación para usuarios internos.

- HU12-T02. Configurar los perfiles de auxiliar, analista y coordinador.

- HU12-T03. Implementar autorización por roles.

- HU12-T04. Proteger endpoints, documentos e interfaces.

- HU12-T05. Aplicar almacenamiento seguro de contraseñas.

- HU12-T06. Realizar pruebas de acceso.

**HU-13. Consulta de trazabilidad de postulaciones Actor:** Coordinador de selección  
**Prioridad:** Media

**Historia de usuario:** Como coordinador de selección, quiero consultar el historial de actividades de cada postulación para conocer las evaluaciones realizadas, las decisiones registradas y el avance del proceso.

**Criterios de aceptación:**

1.  Se registran los cambios de estado relevantes.

2.  Los eventos incluyen actividad, fecha y responsable.

3.  Se conservan los resultados de las evaluaciones.

4.  Los errores de automatización quedan documentados.

5.  El coordinador puede consultar el historial de una postulación.

**Tareas técnicas:**

- HU13-T01. Diseñar la estructura de auditoría.

- HU13-T02. Implementar el registro de eventos.

- HU13-T03. Relacionar los eventos con las instancias BPMN.

- HU13-T04. Crear una interfaz de consulta histórica.

- HU13-T05. Realizar pruebas de trazabilidad.

**HU-14. Detección de postulaciones duplicadas Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Media **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que el sistema detecte postulaciones duplicadas para evitar registrar varias veces a un mismo candidato en una misma vacante.

**Criterios de aceptación:**

1.  Se verifica si existe una postulación previa para la vacante.

2.  La detección utiliza reglas de identificación definidas.

3.  Las postulaciones duplicadas no generan registros adicionales automáticos.

4.  Se conserva una referencia a la postulación original.

5.  Se registra el evento para su posterior revisión.

**Tareas técnicas:**

- HU14-T01. Definir las reglas de detección de duplicados.

- HU14-T02. Implementar consultas de verificación.

- HU14-T03. Configurar restricciones de idempotencia.

- HU14-T04. Integrar controles con la recepción de postulaciones.

- HU14-T05. Integrar verificaciones con el RPA.

- HU14-T06. Realizar pruebas de duplicación.

**Módulo 6. Confiabilidad, operación y mejoras**

**HU-15. Manejo de errores en el proceso automatizado Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Alta **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero que el sistema detecte y registre los errores de las automatizaciones para identificar postulaciones que necesitan intervención humana y evitar la pérdida de información.

**Criterios de aceptación:**

1.  Se detectan errores de IA, BPMS, conexión y RPA.

2.  Los errores se registran con información para su diagnóstico.

3.  Los procesos pueden realizar reintentos controlados.

4.  Se evita la duplicación de registros durante los reintentos.

5.  Las incidencias que no se resuelven automáticamente quedan pendientes de intervención humana.

6.  Se conserva la información de las postulaciones afectadas.

**Tareas técnicas:**

- HU15-T01. Implementar manejo de excepciones.

- HU15-T02. Configurar tiempos de espera y reintentos.

- HU15-T03. Definir las rutas de error en Flowable.

- HU15-T04. Implementar controles de idempotencia.

- HU15-T05. Crear una bandeja de incidencias para el auxiliar.

- HU15-T06. Simular y probar fallos de integración.

**HU-16. Notificaciones de tareas pendientes Actor:** Analista de selección  
**Prioridad:** Media **Historia de usuario:** Como analista de selección, quiero recibir notificaciones cuando tenga nuevas postulaciones pendientes de revisión para atender oportunamente las actividades asignadas.

**Criterios de aceptación:**

1.  El sistema genera una notificación cuando se asigna una tarea.

2.  La notificación identifica la postulación correspondiente.

3.  No se expone información personal innecesaria.

4.  Se registra el resultado del envío.

5.  Las notificaciones no modifican las decisiones ni los estados del proceso.

**Tareas técnicas:**

- HU16-T01. Configurar el servicio de notificaciones.

- HU16-T02. Diseñar las plantillas de mensajes.

- HU16-T03. Integrar eventos de asignación desde Flowable.

- HU16-T04. Implementar el historial de notificaciones.

- HU16-T05. Probar el envío y manejo de errores.

**HU-17. Panel de indicadores de reclutamiento Actor:** Coordinador de selección  
**Prioridad:** Baja **Historia de usuario:** Como coordinador de selección, quiero consultar indicadores del proceso de reclutamiento para conocer el volumen de postulaciones y evaluar su desempeño operativo.

**Criterios de aceptación:**

1.  El sistema muestra el número de postulaciones recibidas.

2.  Se visualizan postulaciones agrupadas por estado.

3.  Se presentan los tiempos promedio de procesamiento.

4.  Se pueden filtrar los indicadores por vacante.

5.  Los cálculos corresponden a la información almacenada.

**Tareas técnicas:**

- HU17-T01. Definir los indicadores operativos.

- HU17-T02. Desarrollar las consultas de métricas.

- HU17-T03. Crear los endpoints de indicadores.

- HU17-T04. Diseñar el panel visual.

- HU17-T05. Implementar filtros.

- HU17-T06. Validar los resultados.

**HU-18. Consulta histórica de vacantes y postulaciones Actor:** Auxiliar de Recursos Humanos  
**Prioridad:** Baja **Historia de usuario:** Como auxiliar de Recursos Humanos, quiero consultar las vacantes cerradas y sus postulaciones para mantener organizado el historial de los procesos de reclutamiento.

**Criterios de aceptación:**

1.  El sistema permite consultar vacantes cerradas.

2.  Se presentan las postulaciones asociadas a cada vacante.

3.  Se pueden consultar los estados finales registrados.

4.  Una vacante cerrada no recibe nuevas postulaciones.

5.  La información se consulta conforme a los permisos y políticas de conservación establecidos.

**Tareas técnicas:**

- HU18-T01. Implementar filtros de vacantes cerradas.

- HU18-T02. Crear la interfaz de consulta histórica.

- HU18-T03. Integrar el historial de postulaciones.

- HU18-T04. Aplicar las restricciones de acceso.

- HU18-T05. Realizar pruebas funcionales.

**3. Priorización de las historias de usuario**

Las historias de usuario se clasifican según su importancia para desarrollar el prototipo y cumplir los objetivos del proceso automatizado.

| **Prioridad** | **Historias de usuario**                                                           |
|---------------|------------------------------------------------------------------------------------|
| Alta          | HU-01, HU-02, HU-03, HU-04, HU-05, HU-06, HU-07, HU-08, HU-09, HU-10, HU-11, HU-15 |
| Media         | HU-12, HU-13, HU-14, HU-16                                                         |
| Baja          | HU-17, HU-18                                                                       |

Los controles básicos de acceso, prevención de duplicados y recuperación de errores deberán implementarse desde las primeras etapas, aunque algunas de sus historias se clasifiquen con prioridad media.
