import os

DATABASE_URL = os.environ["DATABASE_URL"]
FLOWABLE_URL = os.environ["FLOWABLE_URL"]
FLOWABLE_AUTH = (os.getenv("FLOWABLE_USER", "rest-admin"), os.getenv("FLOWABLE_PASSWORD", "test"))
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "dev-internal")
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "/data/uploads")
SEED_PASSWORD = os.getenv("SEED_PASSWORD", "demo1234")

MAX_BYTES = 5 * 1024 * 1024          # RF-03
EXTENSIONES = {".pdf", ".docx"}       # RF-03
DIAS_DUPLICADO = 30                   # RF-05
UMBRAL_CONFIANZA = float(os.getenv("UMBRAL_CONFIANZA", "0.8"))

SMTP_HOST = os.getenv("SMTP_HOST", "greenmail")
SMTP_PORT = int(os.getenv("SMTP_PORT", "3025"))
SMTP_FROM = os.getenv("SMTP_FROM", "reclutamiento@empresa.test")
IMAP_HOST = os.getenv("IMAP_HOST", "greenmail")
IMAP_PORT = int(os.getenv("IMAP_PORT", "3143"))
IMAP_SSL = os.getenv("IMAP_SSL", "false").lower() == "true"
IMAP_USER = os.getenv("IMAP_USER", "postulaciones@empresa.test")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "demo1234")
IMAP_INTERVALO = int(os.getenv("IMAP_INTERVALO", "30"))   # segundos (RF-02 pide 300 en producción)

PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:8000")
# Tiempo sin atender una validación antes de escalarla al coordinador (RF-19). Duración ISO-8601: PT24H, PT30M...
ESCALACION_ISO = os.getenv("ESCALACION_ISO", "PT24H")
# Modo "corridas" usa ESCALACION_ISO tal cual. Modo "habiles" cuenta ESCALACION_HORAS dentro del horario laboral.
ESCALACION_MODO = os.getenv("ESCALACION_MODO", "corridas")
ESCALACION_HORAS = float(os.getenv("ESCALACION_HORAS", "24"))
HORARIO_INICIO = int(os.getenv("HORARIO_INICIO", "8"))          # hora local de apertura
HORARIO_FIN = int(os.getenv("HORARIO_FIN", "18"))               # hora local de cierre
HORARIO_UTC = float(os.getenv("HORARIO_UTC", "-5"))             # Colombia: UTC-5, sin horario de verano
FESTIVOS = [x.strip() for x in os.getenv("FESTIVOS", "").split(",") if x.strip()]   # AAAA-MM-DD separados por coma
AVISOS_INTERVALO = int(os.getenv("AVISOS_INTERVALO", "20"))   # segundos entre revisiones de tareas nuevas

EMPRESA_NOMBRE = os.getenv("EMPRESA_NOMBRE", "Empresa S.A.")
URL_PUBLICA = os.getenv("URL_PUBLICA", "http://localhost:8000")
