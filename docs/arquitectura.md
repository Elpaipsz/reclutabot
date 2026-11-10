# Arquitectura del sistema

## 1. Vista de componentes

Imagen: `docs/diagramas/arquitectura.png` (fuente `arquitectura.mmd`). El flujo del proceso está en `docs/diagramas/flujo.png`.

```mermaid
flowchart LR
  subgraph PERSONAS["Personas"]
    CAN["Candidato<br/>(navegador)"]
    PER["Personal de selección<br/>auxiliar · analista · coordinador · admin"]
    EXT["LinkedIn, Indeed u otros portales<br/>(solo enlazan a la oferta)"]
  end

  CORREO[["Buzón de correo<br/>IMAP"]]

  subgraph API["Contenedor api · FastAPI"]
    direction TB
    PUB["Portal público<br/>cargos abiertos · oferta · postular · consultar estado"]
    INT["Portal interno<br/>tareas · vacantes · postulaciones · plantillas · histórico · tablero"]
    NEG["Servicios de negocio<br/>reglas · estados · duplicados · plazos hábiles"]
    LEC["Lector IMAP"]
    AVI["Avisos al personal"]
    WB["Workers backend<br/>reglas · estados · correos"]
    APII["API interna<br/>token X-Internal-Token"]
  end

  FL[("Flowable 7<br/>motor BPMN 2.0")]
  IA["Servicio IA<br/>worker Python"]
  RPA["Robot RPA<br/>Playwright"]
  RRHH["App RR.HH. simulada<br/>login + expedientes"]
  GEM[["Gemini API"]]
  SMTP[["SMTP<br/>GreenMail en pruebas"]]
  DB[("PostgreSQL<br/>esquemas reclutamiento y flowable")]
  FS[("Volumen uploads<br/>hojas de vida y capturas")]
  HTTPS["Caddy<br/>HTTPS local"]

  CAN --> HTTPS --> PUB
  PER --> HTTPS --> INT
  EXT -. enlace a /empleos .-> PUB
  CORREO --> LEC
  PUB --> NEG
  INT --> NEG
  LEC --> NEG
  NEG -->|inicia proceso| FL
  FL <-->|external tasks REST| WB
  FL <-->|external tasks REST| IA
  FL <-->|external tasks REST| RPA
  AVI -->|consulta tareas nuevas| FL
  IA --> GEM
  IA --> APII
  RPA --> APII
  RPA --> RRHH
  NEG --> DB
  APII --> DB
  WB --> DB
  FL --> DB
  NEG --> FS
  WB --> SMTP
  AVI --> SMTP
  NEG --> SMTP
```

**Decisión central: *external workers* de Flowable.** El BPMN no llama a los servicios: publica trabajo en un tópico
(`extraer-cv`, `registrar-rpa`…) y cada worker lo toma por REST (`/external-job-api/acquire/jobs`), lo ejecuta y lo completa
con variables. Beneficios: los servicios se despliegan y escalan por separado (RNF-17), el paralelismo es natural (RNF-04),
no hay acoplamiento síncrono y una caída de un componente no pierde trabajo (el bloqueo del trabajo expira y otro worker lo retoma).

## 2. Proceso orquestado (BPMN TO-BE ejecutable)

El BPMN se genera con `scripts/gen_bpmn.py` y se despliega solo al arrancar la API
(`services/api/app/bpmn/reclutamiento.bpmn20.xml`). Los datos pesados viven en PostgreSQL; el proceso solo lleva
`postulacionId` y las banderas de decisión.

```mermaid
flowchart TD
  S((Postulación recibida)) --> EX[IA: extraer datos]
  EX --> G1{¿ok?}
  G1 -- falla --> E1[Estado Error] --> UI[/Tarea auxiliar:<br/>atender incidencia/]
  UI -- reintentar --> EX
  UI -- cerrar --> FI((Cerrada por incidencia))
  G1 -- ok --> EV[Evaluar requisitos]
  EV --> G2{¿Cumple y<br/>confianza alta?}
  G2 -- no --> V[/Tarea analista:<br/>validar hoja de vida/]
  V --> G3{decisión}
  G3 -- pedir info --> NI[Correo al candidato] --> V
  G3 -- rechazar --> RE[Estado Rechazada] --> NN[Notificar: no continúa] --> FN((No continúa))
  G3 -- aprobar --> AP
  G2 -- sí --> AP[Estado Aprobada]
  AP --> RPA[RPA: registrar en RR.HH.]
  RPA --> G4{¿registrado?}
  G4 -- falla x3 --> E2[Estado Error] --> UM[/Tarea auxiliar:<br/>registro manual/]
  UM -- reintentar --> RPA
  UM -- registrado --> RG
  UM -- cerrar --> FI
  G4 -- ok --> RG[Estado Registrada]
  RG --> UC[/Tarea coordinador:<br/>¿continúa a entrevista?/]
  UC -- no --> DS[Estado Descartada] --> NN
  UC -- sí --> EN[Estado En entrevista] --> NE[Notificar: avanza a entrevista] --> FE((Pasa a entrevistas))
```

## 3. Secuencia de una postulación (camino feliz con validación humana)

```mermaid
sequenceDiagram
  actor Cand as Candidato
  participant API as API FastAPI
  participant FL as Flowable
  participant IA as Worker IA
  participant GM as Gemini
  actor An as Analista
  participant RPA as Robot RPA
  participant RH as App RR.HH.

  Cand->>API: POST /postular (CV + datos)
  API->>API: validar, guardar, detectar duplicado
  API-->>Cand: número POST-… (+ correo de confirmación)
  API->>FL: iniciar proceso (postulacionId)
  FL-->>IA: trabajo extraer-cv
  IA->>GM: texto del CV (o PDF si es escaneado) + prompt
  GM-->>IA: JSON (reintenta si no valida el esquema)
  IA->>API: guardar extracción + confianza
  FL-->>API: trabajo evaluar-requisitos (reglas → puntaje)
  FL->>An: tarea "Validar hoja de vida"
  An->>API: corrige datos y aprueba
  FL-->>RPA: trabajo registrar-rpa
  RPA->>RH: login → buscar documento → crear → capturar ID
  RPA->>API: guardar ID de RR.HH.
  FL->>FL: sigue hacia la decisión del coordinador
```

## 4. Despliegue

Un solo `docker compose up -d --build` levanta ocho contenedores:

| Servicio | Imagen / build | Puerto | Responsabilidad |
|---|---|---|---|
| `postgres` | postgres:16 | — | Esquema `reclutamiento` (app) y `flowable` (motor) |
| `flowable` | flowable/flowable-rest:7.1.0 | 8081 | Motor BPMN, tareas humanas, external workers |
| `api` | `services/api` | 8000 | Portal, reglas, notificaciones, IMAP, API interna, despliegue del BPMN |
| `https` | caddy:2 | 8443 | HTTPS local (proxy inverso hacia `api`) |
| `ia` | `services/ai` | — | Worker: `extraer-cv` |
| `rpa` | `services/rpa` (Playwright) | — | Worker: `registrar-rpa` |
| `rrhh` | `services/rrhh` | 9000 | Sistema de RR.HH. simulado (web con login) |
| `greenmail` | greenmail/standalone | 3025 / 3143 | SMTP e IMAP de pruebas |

Los volúmenes `pgdata`, `uploads` (hojas de vida y capturas) y `rrhhdata` conservan los datos entre reinicios; los servicios
tienen `restart: unless-stopped` (RNF-15).

## 5. Decisiones de diseño relevantes

| Tema | Decisión | Por qué |
|---|---|---|
| Orquestación | Flowable con external workers | Desacopla componentes, reintentos y paralelismo nativos |
| IA | Gemini con salida JSON + validación Pydantic + reintentos; cadena de modelos de respaldo | La capa gratuita tiene cuota diaria por modelo (descubierto en pruebas) |
| IA vs. decisión | La IA solo extrae y sugiere; reglas deterministas puntúan; personas deciden | RNF-13, explicabilidad y riesgo legal |
| Experiencia | Se calcula en código fusionando periodos solapados | Los LLM suman mal fechas |
| Robot | Busca antes de crear; idempotente ante reintentos de Flowable | RF-23, evitar duplicados |
| Fallas | Toda falla → estado `Error` + incidencia (+ captura) + tarea humana | RNF-06: ninguna postulación se pierde |
| Seguridad | JWT en cookie httpOnly, roles por tarea, bcrypt, token interno entre servicios, HTTPS (Caddy), secretos en `.env` | RNF-08/09/11 |
| Escalación | Temporizador de frontera no interruptor en la tarea de validación; la duración la calcula `app/horario.py` (horas hábiles) o viene de `ESCALACION_ISO` (modo corridas) | RF-19 |
| Avisos al personal | Hilo que detecta tareas nuevas en Flowable y envía un correo por tarea y grupo (deduplicado en BD) | RF-29, HU-16 |
| Datos personales | Casilla Habeas Data obligatoria, archivos no públicos, borrado por solicitud (admin) | RNF-10/11 |
| Configurabilidad | Requisitos y pesos en BD; prompts en archivos | RNF-18 |
