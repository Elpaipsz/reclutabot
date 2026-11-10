# Guion de demostración (≈ 10 minutos)

Preparación (antes de presentar): `docker compose up -d --build`, esperar `/health` en ok, abrir en pestañas:
portal (`:8000`), RR.HH. simulado (`:9000/candidatos`, login `robot`/`robot123`), y tener 3 hojas de vida de `datos_prueba/`
(`python scripts/generar_cvs.py 50`). Iniciar sesión en ventanas distintas como **analista**, **auxiliar** y **coordinador**
(contraseña `demo1234`). Si usarás mucho la IA, revisa la cuota de Gemini (ver README).

## 1. El problema y la idea (1 min)
Antes: RR.HH. recibía hojas de vida por correo, las leía, transcribía a mano y registraba. Ahora: un flujo orquestado por Flowable.

## 2. Un candidato se postula (1 min)
- Portal (`/`): elegir **VAC-002**, subir `cv_001_simple.pdf`, aceptar Habeas Data → aparece el **número de postulación**.
- Mostrar que también llega por correo: enviar un correo a `postulaciones@empresa.test` con asunto `Postulación VAC-002`
  (o ejecutar `python scripts/e2e.py correo`).

## 3. La IA extrae y las reglas puntúan (2 min)
- Login analista → **Mis tareas** → abrir *Validar hoja de vida*.
- PDF original a la izquierda, datos extraídos a la derecha; **bloques amarillos = baja confianza de la IA**. Corregir un dato.
- Explicar: la IA no decide; el puntaje sale de reglas explicables y pesos configurables (pantalla *Vacantes*).
- Aprobar.

## 4. El robot registra (2 min)
- Mostrar `http://localhost:9000/candidatos`: el candidato aparece con su **ID RH-…** sin que nadie digitara nada.
- Abrir la postulación en el portal → **Trazabilidad**: cada paso (IA, regla, humano, bot) con fecha y actor.

## 5. Una falla y su recuperación (2 min)
- En `:9000/admin` pulsar **Provocar fallas (3)**; postular otra hoja de vida y aprobarla.
- El robot reintenta 3 veces → la postulación pasa a **Error**, hay una **incidencia con captura de pantalla** y una **tarea manual** para el auxiliar.
- Restablecer fallas → como auxiliar elegir **Reintentar** → queda registrada. *«Ninguna postulación se pierde.»*

## 6. Paso a entrevistas (1 min)
- Login coordinador → tarea *Decidir continuidad* → **Continúa**.
- La postulación queda en *En entrevista* y el candidato recibe el aviso por correo (en la demo local el buzón es GreenMail; ver *Correos al candidato* en la postulación).
- El proceso termina aquí: la entrevista se hace fuera del sistema.

## 7. Extras opcionales (1 min cada uno)
- **Avisos:** al crearse una tarea, el personal recibe un correo sin datos del candidato (se ve en `notificacion` o con `scripts/e2e.py avisos`).
- **Plantillas:** admin → *Plantillas* → editar el asunto de «Confirmación» y postular de nuevo.
- **Escalación:** con `ESCALACION_MODO=corridas` y `ESCALACION_ISO=PT1M` una validación sin atender aparece sola en la bandeja del coordinador.
- **Histórico:** auxiliar → *Vacantes* → cerrar una → *Histórico*; el formulario deja de ofrecerla.
- **HTTPS:** `https://localhost:8443`.

## 8. Cierre con números (30 s)
Tablero (`/app`): postulaciones por estado, minutos de ciclo, tasa de intervención humana, costo de IA.
Citar la simulación BIMP (−68 % tiempo de ciclo, −58 % costo) y los resultados de `docs/trazabilidad.md`.
