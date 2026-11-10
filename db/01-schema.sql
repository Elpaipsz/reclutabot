-- Esquema de la aplicación (la BD "flowable" la gestiona Flowable).
\connect reclutamiento

CREATE TABLE usuario (
  id            SERIAL PRIMARY KEY,
  nombre        TEXT NOT NULL,
  correo        TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  rol           TEXT NOT NULL CHECK (rol IN ('auxiliar','analista','coordinador','admin'))
);

CREATE TABLE vacante (
  id             SERIAL PRIMARY KEY,
  codigo         TEXT NOT NULL UNIQUE,            -- se usa en el asunto del correo
  titulo         TEXT NOT NULL,
  descripcion    TEXT,
  estado         TEXT NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa','cerrada')),
  -- requisitos y pesos configurables sin tocar código (RNF-18)
  requisitos     JSONB NOT NULL DEFAULT '{}',     -- {"anios_experiencia":2,"formacion":"Profesional","habilidades":["python"],"idiomas":["Inglés B2"]}
  pesos          JSONB NOT NULL DEFAULT '{"experiencia":0.35,"formacion":0.25,"habilidades":0.30,"idioma":0.10}',
  -- datos públicos de la oferta (página de empleo)
  area TEXT, ubicacion TEXT, modalidad TEXT, contrato TEXT, salario TEXT, responsabilidades TEXT, ofrecemos TEXT,
  creada_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE candidato (
  id        SERIAL PRIMARY KEY,
  nombre    TEXT NOT NULL,
  correo    TEXT NOT NULL,
  telefono  TEXT,
  documento TEXT,
  acepta_datos BOOLEAN NOT NULL DEFAULT FALSE,
  acepta_en    TIMESTAMPTZ
);
CREATE INDEX ON candidato (lower(correo));

CREATE TABLE postulacion (
  id               SERIAL PRIMARY KEY,
  numero           TEXT NOT NULL UNIQUE,          -- "POST-2026-000123"
  vacante_id       INT NOT NULL REFERENCES vacante(id),
  candidato_id     INT NOT NULL REFERENCES candidato(id),
  canal            TEXT NOT NULL CHECK (canal IN ('formulario','correo')),
  estado           TEXT NOT NULL DEFAULT 'Recibida' CHECK (estado IN
                     ('Recibida','En extracción','En validación','Aprobada','Rechazada',
                      'Registrada','En entrevista','Descartada','Error','Duplicada')),
  clasificacion    TEXT CHECK (clasificacion IN ('Cumple','Revisar','No cumple')),
  puntaje          NUMERIC(5,2),
  archivo_path     TEXT NOT NULL,
  archivo_hash     TEXT NOT NULL,                 -- idempotencia / duplicados
  proceso_id       TEXT,                          -- instancia en Flowable
  rrhh_id          TEXT,                          -- ID devuelto por el sistema RR.HH. (RPA)
  duplicada_de     INT REFERENCES postulacion(id),
  recibida_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
  actualizada_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON postulacion (estado);
CREATE INDEX ON postulacion (vacante_id, candidato_id);

CREATE TABLE extraccion (
  id              SERIAL PRIMARY KEY,
  postulacion_id  INT NOT NULL REFERENCES postulacion(id),
  datos           JSONB NOT NULL,                 -- JSON extraído por la IA
  confianza       JSONB NOT NULL DEFAULT '{}',    -- {"campo": 0.0-1.0}
  resumen         TEXT,
  anios_experiencia NUMERIC(4,1),
  datos_validados JSONB,                          -- tras corrección humana
  validado_por    INT REFERENCES usuario(id),
  validado_en     TIMESTAMPTZ,
  costo_usd       NUMERIC(10,5),
  creada_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE decision (
  id             SERIAL PRIMARY KEY,
  postulacion_id INT NOT NULL REFERENCES postulacion(id),
  tipo           TEXT NOT NULL CHECK (tipo IN ('validacion','continuidad')),
  resultado      TEXT NOT NULL,                   -- aprobar / rechazar / pedir_info / continuar / descartar
  observacion    TEXT,
  usuario_id     INT REFERENCES usuario(id),
  creada_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (resultado NOT IN ('rechazar','descartar') OR observacion IS NOT NULL)  -- RF-18 / RNF-13
);

CREATE TABLE incidencia (
  id             SERIAL PRIMARY KEY,
  postulacion_id INT REFERENCES postulacion(id),
  origen         TEXT NOT NULL CHECK (origen IN ('documento','ia','rpa','flowable','correo')),
  detalle        TEXT NOT NULL,
  captura_path   TEXT,
  resuelta       BOOLEAN NOT NULL DEFAULT FALSE,
  creada_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bitácora de auditoría (HU-13, RNF-12)
CREATE TABLE evento (
  id             BIGSERIAL PRIMARY KEY,
  postulacion_id INT REFERENCES postulacion(id),
  actor          TEXT NOT NULL,                   -- usuario, 'ia', 'rpa', 'sistema'
  accion         TEXT NOT NULL,
  resultado      TEXT,
  detalle        JSONB,
  creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON evento (postulacion_id, creado_en);

CREATE TABLE notificacion (
  id             SERIAL PRIMARY KEY,
  postulacion_id INT REFERENCES postulacion(id),
  destinatario   TEXT NOT NULL,
  plantilla      TEXT NOT NULL,
  enviada        BOOLEAN NOT NULL,
  error          TEXT,
  creada_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Plantillas de correo editables desde pantalla (RF-28); si no hay fila se usa el texto por defecto
CREATE TABLE plantilla (
  clave          TEXT PRIMARY KEY,
  asunto         TEXT NOT NULL,
  cuerpo         TEXT NOT NULL,
  actualizada_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Avisos de tarea ya enviados al personal (uno por tarea y grupo): evita repetirlos (RF-29, HU-16)
CREATE TABLE tarea_notificada (
  clave     TEXT PRIMARY KEY,
  creada_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
