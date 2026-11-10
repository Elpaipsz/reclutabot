import logging
import threading
from contextlib import asynccontextmanager

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from . import auth, avisos, correo, db, flowable, internas, portal, workers_backend
from .config import DATABASE_URL, FLOWABLE_AUTH, FLOWABLE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

VACANTES_DEMO = [
    ("VAC-001", "Desarrollador Backend Python", "Desarrollo de servicios con FastAPI y PostgreSQL.",
     {"anios_experiencia": 2, "formacion_minima": "Profesional", "habilidades_obligatorias": ["Python", "SQL"],
      "habilidades_deseables": ["FastAPI", "Docker", "PostgreSQL"], "idiomas": [{"idioma": "Inglés", "nivel": "B1"}]}),
    ("VAC-002", "Analista de Datos", "Análisis y visualización de datos para el área comercial.",
     {"anios_experiencia": 1, "formacion_minima": "Tecnólogo", "habilidades_obligatorias": ["SQL"],
      "habilidades_deseables": ["Power BI", "Excel", "Python"], "idiomas": []}),
    ("VAC-003", "Ingeniero DevOps", "Automatización de infraestructura y despliegues.",
     {"anios_experiencia": 3, "formacion_minima": "Profesional", "habilidades_obligatorias": ["Docker", "Linux"],
      "habilidades_deseables": ["Kubernetes", "AWS", "Git"], "idiomas": [{"idioma": "Inglés", "nivel": "B2"}]}),
]


OFERTA_DEMO = {   # código: (área, ubicación, modalidad, contrato, responsabilidades, qué ofrecemos)
    "VAC-001": ("Tecnología", "Bogotá", "Híbrido", "Término indefinido",
                "Diseñar y mantener servicios REST con FastAPI\nModelar y consultar bases de datos PostgreSQL\nEscribir pruebas automáticas y documentar",
                "Salario competitivo y bonos por desempeño\nTrabajo híbrido (3 días en oficina)\nPlan de formación y certificaciones"),
    "VAC-002": ("Analítica", "Medellín", "Remoto", "Término indefinido",
                "Construir tableros e informes para el área comercial\nLimpiar y analizar datos con SQL y Python\nPresentar hallazgos a las áreas de negocio",
                "Trabajo 100 % remoto\nHorario flexible\nAcceso a cursos de analítica de datos"),
    "VAC-003": ("Infraestructura", "Cali", "Presencial", "Término fijo",
                "Automatizar despliegues con contenedores\nAdministrar servidores Linux y monitoreo\nMejorar la seguridad y la disponibilidad",
                "Salario por encima del mercado\nCertificaciones cloud pagadas\nEquipo de alto nivel técnico"),
}


def _arranque_flowable():
    flowable.desplegar()
    workers_backend.iniciar_todos()


@asynccontextmanager
async def lifespan(app):
    db.init()
    auth.seed_usuarios()
    if not db.q1("SELECT 1 FROM vacante LIMIT 1"):
        for c, t, d, r in VACANTES_DEMO:
            db.ex("INSERT INTO vacante(codigo,titulo,descripcion,requisitos) VALUES (%s,%s,%s,%s)", (c, t, d, db.J(r)))
    for codigo, (area, ubic, modal, contrato, resp, ofrece) in OFERTA_DEMO.items():   # datos públicos de las vacantes de ejemplo
        db.ex("""UPDATE vacante SET area=%s,ubicacion=%s,modalidad=%s,contrato=%s,responsabilidades=%s,ofrecemos=%s
                 WHERE codigo=%s AND area IS NULL""", (area, ubic, modal, contrato, resp, ofrece, codigo))
    threading.Thread(target=_arranque_flowable, daemon=True, name="arranque-flowable").start()
    correo.iniciar()
    avisos.iniciar()
    yield


app = FastAPI(title="Reclutamiento automatizado - API", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.include_router(internas.router)
app.include_router(portal.router)


@app.exception_handler(HTTPException)
async def http_error(request, exc: HTTPException):
    if exc.status_code == 401 and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/login", status_code=303)
    if "text/html" in request.headers.get("accept", ""):
        return portal.T.TemplateResponse(request, "error.html", {"u": None, "codigo": exc.status_code, "detalle": exc.detail},
                                         status_code=exc.status_code)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/health")
def health():
    """Verifica conexión a PostgreSQL y a Flowable."""
    estado = {}
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        estado["postgres"] = "ok"
    except Exception as e:
        estado["postgres"] = f"error: {e}"
    try:
        r = httpx.get(f"{FLOWABLE_URL}/service/repository/deployments", auth=FLOWABLE_AUTH, timeout=3)
        estado["flowable"] = "ok" if r.status_code == 200 else f"http {r.status_code}"
    except Exception as e:
        estado["flowable"] = f"error: {e}"
    return estado
