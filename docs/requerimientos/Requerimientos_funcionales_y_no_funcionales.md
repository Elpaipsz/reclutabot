# Requerimientos funcionales y no funcionales — Automatización de reclutamiento

Oct 29, 2026 · @Santiago Mafla Jaramillo

## 1. Requerimientos funcionales

Son 32 requerimientos repartidos en 8 módulos. Los 23 marcados Must son el mínimo para demostrar el flujo completo con IA, RPA y Flowable integrados. Prioridad MoSCoW: Must = obligatorio para la demo, Should = importante, Could = si alcanza el tiempo.

### 1.1 Recepción de postulaciones

| ID    | Requerimiento                                                                                                                                                                           | Prioridad | Componente         |
|-------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|--------------------|
| RF-01 | El sistema debe ofrecer un formulario web donde el candidato elige la vacante, ingresa nombre, correo y teléfono, acepta la política de tratamiento de datos y adjunta su hoja de vida. | Must      | Backend + interfaz |
| RF-02 | El sistema debe leer cada 5 minutos un buzón de correo dedicado y crear una postulación por cada correo con hoja de vida adjunta, tomando la vacante del asunto.                        | Should    | Backend (IMAP)     |
| RF-03 | El sistema debe aceptar archivos PDF y DOCX de hasta 5 MB y rechazar los demás formatos con un mensaje claro.                                                                           | Must      | Backend            |
| RF-04 | El sistema debe guardar el archivo original, asignar un número único de postulación y registrar fecha, hora y canal de llegada.                                                         | Must      | Backend + BD       |
| RF-05 | El sistema debe detectar postulaciones duplicadas (mismo correo o documento a la misma vacante en los últimos 30 días) y marcarlas sin abrir un nuevo proceso.                          | Should    | Backend + BD       |
| RF-06 | El sistema debe iniciar automáticamente una instancia del proceso de reclutamiento en Flowable por cada postulación válida.                                                             | Must      | Backend + Flowable |

### 1.2 Extracción con IA

| ID    | Requerimiento                                                                                                                                                                        | Prioridad | Componente           |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|----------------------|
| RF-07 | El sistema debe convertir la hoja de vida a texto (incluido OCR si el PDF es escaneado) antes de enviarla a la IA.                                                                   | Must      | Servicio IA          |
| RF-08 | La IA debe extraer en formato JSON: datos personales, formación (título, institución, año), experiencia (cargo, empresa, fechas, funciones), habilidades, idiomas y certificaciones. | Must      | Servicio IA (Gemini) |
| RF-09 | El sistema debe calcular los años totales de experiencia a partir de las fechas extraídas.                                                                                           | Must      | Servicio IA          |
| RF-10 | La IA debe asignar un nivel de confianza (0 a 1) a cada campo extraído.                                                                                                              | Must      | Servicio IA          |
| RF-11 | El sistema debe validar el JSON contra un esquema y reintentar la extracción hasta 2 veces si viene incompleto o mal formado.                                                        | Must      | Servicio IA          |
| RF-12 | La IA debe generar un resumen del perfil de máximo 100 palabras para el analista.                                                                                                    | Should    | Servicio IA          |

### 1.3 Validación automática de requisitos

| ID    | Requerimiento                                                                                                                                            | Prioridad | Componente                   |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------------------------------|
| RF-13 | El sistema debe comparar los datos extraídos con los requisitos de la vacante (formación mínima, años de experiencia, habilidades obligatorias, idioma). | Must      | Backend (reglas)             |
| RF-14 | El sistema debe calcular un puntaje de ajuste de 0 a 100 con pesos configurables por criterio.                                                           | Must      | Backend                      |
| RF-15 | El sistema debe clasificar la postulación como Cumple, Revisar o No cumple según el puntaje y los requisitos obligatorios.                               | Must      | Backend + Flowable (gateway) |

### 1.4 Validación humana (tareas en Flowable)

| ID    | Requerimiento                                                                                                                                         | Prioridad | Componente            |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|-----------------------|
| RF-16 | Flowable debe crear una tarea de validación para el grupo de RR. HH. cuando la postulación queda en Revisar o tiene campos con confianza menor a 0,8. | Must      | Flowable              |
| RF-17 | La tarea debe mostrar la hoja de vida original junto a los datos extraídos, resaltando los de baja confianza, y permitir corregirlos.                 | Must      | Flowable (formulario) |
| RF-18 | El analista debe poder aprobar, rechazar o pedir información al candidato, dejando una observación obligatoria si rechaza.                            | Must      | Flowable              |
| RF-19 | Flowable debe escalar la tarea al líder de selección si no se atiende en 24 horas hábiles.                                                            | Should    | Flowable (timer)      |

### 1.5 Registro por RPA

| ID    | Requerimiento                                                                                                                                              | Prioridad | Componente       |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------------------|
| RF-20 | El bot debe iniciar sesión en el sistema de RR. HH. y registrar al candidato aprobado con sus datos validados y el archivo adjunto.                        | Must      | RPA (Playwright) |
| RF-21 | El bot debe capturar el ID que asigna el sistema de RR. HH. y devolverlo al backend para guardarlo en la postulación.                                      | Must      | RPA + Backend    |
| RF-22 | El bot debe reintentar hasta 3 veces ante fallas y, si persisten, Flowable debe crear una tarea de registro manual con el error y una captura de pantalla. | Must      | RPA + Flowable   |
| RF-23 | El bot no debe registrar dos veces al mismo candidato: antes de crear, debe buscarlo por documento.                                                        | Should    | RPA              |

### 1.6 Orquestación y estados

| ID    | Requerimiento                                                                                                                                                 | Prioridad | Componente    |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|---------------|
| RF-24 | Flowable debe ejecutar el BPMN TO-BE completo, llamando a los servicios de IA, reglas y RPA mediante tareas de servicio (REST).                               | Must      | Flowable      |
| RF-25 | Cada postulación debe pasar por estados definidos: Recibida, En extracción, En validación, Aprobada, Rechazada, Registrada, En entrevista, Descartada, Error. | Must      | Flowable + BD |
| RF-26 | El líder de selección debe tener una tarea para decidir si el candidato registrado pasa a entrevista.                                                         | Must      | Flowable      |

### 1.7 Notificaciones

| ID    | Requerimiento                                                                                                          | Prioridad | Componente         |
|-------|------------------------------------------------------------------------------------------------------------------------|-----------|--------------------|
| RF-27 | El sistema debe enviar al candidato un correo de confirmación de recibido con su número de postulación.                | Must      | Backend (SMTP)     |
| RF-28 | El sistema debe informar al candidato el resultado final (pasa a entrevista o no continúa) con una plantilla editable. | Should    | Backend + Flowable |
| RF-29 | El sistema debe avisar a RR. HH. por correo cuando tiene tareas pendientes o cuando falla el bot.                      | Could     | Flowable           |

### 1.8 Administración y reportes

| ID    | Requerimiento                                                                                                            | Prioridad | Componente         |
|-------|--------------------------------------------------------------------------------------------------------------------------|-----------|--------------------|
| RF-30 | El administrador debe poder crear y editar vacantes con sus requisitos y pesos de puntaje.                               | Must      | Backend + interfaz |
| RF-31 | El sistema debe mostrar un tablero con postulaciones por estado, tiempo promedio de ciclo y tasa de intervención humana. | Should    | Backend + interfaz |
| RF-32 | El sistema debe exportar a CSV el listado de postulaciones de una vacante con su puntaje y estado.                       | Could     | Backend            |

## 2. Requerimientos no funcionales

Cada requerimiento trae una métrica para poder probarlo en la demo. Las metas de tiempo salen de la simulación en BIMP (68 % menos de tiempo de ciclo).

| ID     | Categoría           | Requerimiento                                                                                                  | Métrica / criterio de verificación                                                                                            | Prioridad |
|--------|---------------------|----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|-----------|
| RNF-01 | Rendimiento         | La extracción con IA de una hoja de vida debe ser rápida.                                                      | ≤ 30 s por hoja de vida de hasta 3 páginas (percentil 90)                                                                     | Must      |
| RNF-02 | Rendimiento         | El registro por RPA de un candidato debe ser rápido.                                                           | ≤ 60 s por candidato                                                                                                          | Must      |
| RNF-03 | Rendimiento         | El tiempo de ciclo automático (recepción hasta tarea humana o registro) debe reducirse frente al AS-IS.        | ≤ 5 min sin contar la espera de la tarea humana                                                                               | Must      |
| RNF-04 | Capacidad           | El sistema debe procesar el volumen simulado sin degradarse.                                                   | 50 postulaciones en un día, con al menos 5 procesadas en paralelo                                                             | Must      |
| RNF-05 | Calidad de la IA    | La extracción debe ser precisa.                                                                                | ≥ 90 % de campos correctos sobre un set de prueba de 20 hojas de vida etiquetadas a mano                                      | Must      |
| RNF-06 | Confiabilidad       | Ninguna postulación se pierde: toda falla queda en estado Error con tarea manual.                              | 0 postulaciones sin estado final en las pruebas de punta a punta                                                              | Must      |
| RNF-07 | Confiabilidad       | Las llamadas a Gemini y al sistema de RR. HH. deben tolerar fallas temporales.                                 | Reintentos con espera exponencial (3 intentos) y tiempo límite de 60 s                                                        | Must      |
| RNF-08 | Seguridad           | Solo usuarios autenticados acceden a tareas y datos, según su rol (candidato, analista, líder, administrador). | Login en Flowable y API con token (JWT); prueba de acceso denegado por rol                                                    | Must      |
| RNF-09 | Seguridad           | Las credenciales (API key de Gemini, usuario del bot, base de datos) no van en el código.                      | Variables de entorno o archivo .env fuera del repositorio                                                                     | Must      |
| RNF-10 | Protección de datos | El tratamiento de datos personales debe cumplir la Ley 1581 de 2012 (Habeas Data).                             | Aceptación explícita de la política en el formulario; opción de eliminar datos a solicitud                                    | Must      |
| RNF-11 | Protección de datos | La información viaja y se guarda protegida.                                                                    | HTTPS en la API; archivos de hojas de vida no accesibles públicamente                                                         | Should    |
| RNF-12 | Trazabilidad        | Cada paso (IA, regla, decisión humana, bot) queda registrado.                                                  | Bitácora con fecha, actor, acción y resultado por postulación; historial de Flowable consultable                              | Must      |
| RNF-13 | Explicabilidad      | La IA apoya pero no decide sola: ningún candidato se descarta sin revisión humana.                             | 100 % de rechazos con tarea humana y observación                                                                              | Must      |
| RNF-14 | Usabilidad          | El formulario del candidato y la tarea del analista deben ser fáciles de usar.                                 | Postularse en ≤ 3 min; validar una hoja de vida en ≤ 2 min; interfaz en español                                               | Should    |
| RNF-15 | Disponibilidad      | El prototipo debe estar disponible durante la demo y las pruebas.                                              | Arranque completo con un solo comando y servicios con reinicio automático                                                     | Should    |
| RNF-16 | Portabilidad        | Todo corre localmente en contenedores.                                                                         | docker compose up levanta Flowable, FastAPI, PostgreSQL, servicio IA, bot RPA y la app de RR. HH. simulada                    | Must      |
| RNF-17 | Mantenibilidad      | El código es modular y documentado.                                                                            | Servicios separados (IA, reglas, RPA); README de instalación; APIs documentadas con OpenAPI (Swagger de FastAPI)              | Must      |
| RNF-18 | Mantenibilidad      | El cambio de vacantes, requisitos o prompts no exige tocar código.                                             | Requisitos y pesos en BD; prompt de Gemini en un archivo de configuración                                                     | Should    |
| RNF-19 | Interoperabilidad   | La comunicación entre componentes usa estándares.                                                              | REST + JSON entre Flowable, FastAPI e IA; BPMN 2.0 en Flowable                                                                | Must      |
| RNF-20 | Calidad / pruebas   | Los componentes críticos tienen pruebas.                                                                       | Pruebas unitarias del parser y las reglas (pytest) y al menos 3 pruebas de punta a punta: aprobado, rechazado y falla del bot | Must      |
| RNF-21 | Costo               | El costo de operación debe ser coherente con el caso de negocio.                                               | Uso del nivel gratuito o de bajo costo de Gemini; costo por hoja de vida registrado en la bitácora                            | Could     |
