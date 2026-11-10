"""Sistema de RR.HH. simulado: la aplicación web "legada" donde el robot (RPA) registra candidatos.

Tiene login, buscador, formulario de alta y un panel para inyectar fallas (demostración de RF-22).
"""
import html
import os
import sqlite3
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

DB = os.getenv("RRHH_DB", "/data/rrhh.db")
FILES = Path(os.getenv("RRHH_FILES", "/data/rrhh_files"))
USER, PASSWORD = os.getenv("RRHH_USER", "robot"), os.getenv("RRHH_PASSWORD", "robot123")
SESIONES: set[str] = set()
FALLAS = {"restantes": 0}   # cuántos registros fallarán a propósito

app = FastAPI(title="Sistema RR.HH. (simulado)")
Path(DB).parent.mkdir(parents=True, exist_ok=True)
FILES.mkdir(parents=True, exist_ok=True)


def con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS candidato(id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, documento TEXT,
                 correo TEXT, telefono TEXT, vacante TEXT, anios REAL, formacion TEXT, habilidades TEXT, resumen TEXT,
                 archivo TEXT, creado TEXT DEFAULT CURRENT_TIMESTAMP)""")
    return c


def e(v):
    return html.escape(str(v if v is not None else ""))


def pagina(titulo, cuerpo, nav=True):
    menu = ('<nav><a href="/candidatos">Candidatos</a><a href="/candidatos/nuevo">Nuevo candidato</a>'
            '<a href="/admin">Administración</a><a href="/logout">Salir</a></nav>') if nav else ""
    return HTMLResponse(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{e(titulo)}</title>
<style>body{{font-family:Arial,sans-serif;margin:0;background:#eef1f5}}header{{background:#0b3d6b;color:#fff;padding:14px 24px;font-size:18px}}
nav{{background:#124f8a;padding:8px 24px}}nav a{{color:#fff;margin-right:18px;text-decoration:none}}main{{padding:24px;max-width:900px}}
input,select,textarea{{padding:7px;margin:3px 0 10px;width:100%;box-sizing:border-box}}table{{border-collapse:collapse;width:100%;background:#fff}}
td,th{{border:1px solid #cdd3dc;padding:7px;text-align:left}}button{{background:#0b3d6b;color:#fff;border:0;padding:9px 18px;cursor:pointer}}
.ok{{background:#d4edda;padding:12px;border:1px solid #9bd0a8}}</style></head><body>
<header>SAP-RH Legacy · Sistema de Recursos Humanos</header>{menu}<main><h2>{e(titulo)}</h2>{cuerpo}</main></body></html>""")


def autenticado(request: Request) -> bool:
    return request.cookies.get("rrhh_sid") in SESIONES


@app.get("/login", response_class=HTMLResponse)
def login_form(error: str = ""):
    return pagina("Iniciar sesión", f"""<p style="color:#b00">{e(error)}</p><form method="post" action="/login" style="max-width:320px">
<label>Usuario</label><input name="usuario" id="usuario"><label>Contraseña</label><input name="password" id="password" type="password">
<button id="entrar">Entrar</button></form>""", nav=False)


@app.post("/login")
def login(usuario: str = Form(...), password: str = Form(...)):
    if usuario != USER or password != PASSWORD:
        return RedirectResponse("/login?error=Credenciales+inválidas", status_code=303)
    sid = uuid.uuid4().hex
    SESIONES.add(sid)
    r = RedirectResponse("/candidatos", status_code=303)
    r.set_cookie("rrhh_sid", sid, httponly=True)
    return r


@app.get("/logout")
def logout():
    r = RedirectResponse("/login", status_code=303)
    r.delete_cookie("rrhh_sid")
    return r


@app.get("/candidatos", response_class=HTMLResponse)
def listar(request: Request, q: str = ""):
    if not autenticado(request):
        return RedirectResponse("/login", status_code=303)
    filas = con().execute("SELECT * FROM candidato WHERE documento LIKE ? OR correo LIKE ? OR nombre LIKE ? ORDER BY id DESC LIMIT 200",
                          (f"%{q}%",) * 3).fetchall() if q else con().execute("SELECT * FROM candidato ORDER BY id DESC LIMIT 200").fetchall()
    tr = "".join(f'<tr class="fila"><td class="rh-id">RH-{r["id"]:06d}</td><td>{e(r["nombre"])}</td><td class="doc">{e(r["documento"])}</td>'
                 f'<td>{e(r["correo"])}</td><td>{e(r["vacante"])}</td></tr>' for r in filas)
    return pagina("Candidatos", f"""<form method="get"><input name="q" id="q" value="{e(q)}" placeholder="Buscar por documento, correo o nombre" style="width:70%">
<button id="buscar">Buscar</button></form><table><tr><th>ID</th><th>Nombre</th><th>Documento</th><th>Correo</th><th>Vacante</th></tr>{tr or '<tr><td colspan=5>Sin resultados</td></tr>'}</table>""")


@app.get("/candidatos/nuevo", response_class=HTMLResponse)
def nuevo(request: Request):
    if not autenticado(request):
        return RedirectResponse("/login", status_code=303)
    return pagina("Registrar candidato", """<form method="post" action="/candidatos" enctype="multipart/form-data">
<label>Nombre completo</label><input name="nombre" id="nombre" required>
<label>Documento de identidad</label><input name="documento" id="documento">
<label>Correo</label><input name="correo" id="correo" required>
<label>Teléfono</label><input name="telefono" id="telefono">
<label>Vacante (código)</label><input name="vacante" id="vacante">
<label>Años de experiencia</label><input name="anios" id="anios" type="number" step="0.1">
<label>Formación principal</label><input name="formacion" id="formacion">
<label>Habilidades</label><textarea name="habilidades" id="habilidades"></textarea>
<label>Resumen del perfil</label><textarea name="resumen" id="resumen"></textarea>
<label>Hoja de vida (adjunto)</label><input type="file" name="archivo" id="archivo">
<button id="guardar">Guardar candidato</button></form>""")


@app.post("/candidatos")
async def crear(request: Request, nombre: str = Form(...), documento: str = Form(""), correo: str = Form(...),
                telefono: str = Form(""), vacante: str = Form(""), anios: str = Form("0"), formacion: str = Form(""),
                habilidades: str = Form(""), resumen: str = Form(""), archivo: UploadFile = File(None)):
    if not autenticado(request):
        return RedirectResponse("/login", status_code=303)
    if FALLAS["restantes"] > 0:
        FALLAS["restantes"] -= 1
        return HTMLResponse("<h1>500 - Error interno del servidor de RR.HH.</h1><p>Servicio no disponible, intente más tarde.</p>", status_code=500)
    ruta = ""
    if archivo and archivo.filename:
        ruta = f"{uuid.uuid4().hex}_{Path(archivo.filename).name}"
        (FILES / ruta).write_bytes(await archivo.read())
    c = con()
    cur = c.execute("INSERT INTO candidato(nombre,documento,correo,telefono,vacante,anios,formacion,habilidades,resumen,archivo) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (nombre, documento, correo, telefono, vacante, float(anios or 0), formacion, habilidades, resumen, ruta))
    c.commit()
    return RedirectResponse(f"/candidatos/{cur.lastrowid}", status_code=303)


@app.get("/candidatos/{cid}", response_class=HTMLResponse)
def ver(request: Request, cid: int):
    if not autenticado(request):
        return RedirectResponse("/login", status_code=303)
    r = con().execute("SELECT * FROM candidato WHERE id=?", (cid,)).fetchone()
    if not r:
        return pagina("No encontrado", "<p>El candidato no existe.</p>")
    return pagina("Candidato registrado", f"""<div class="ok">Registro guardado. ID asignado: <b id="id-asignado">RH-{r['id']:06d}</b></div>
<p><b>{e(r['nombre'])}</b> · {e(r['documento'])} · {e(r['correo'])}</p><p>Vacante: {e(r['vacante'])} · {r['anios']} años · {e(r['formacion'])}</p>
<p>Habilidades: {e(r['habilidades'])}</p><p>Adjunto: {e(r['archivo'])}</p>""")


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    if not autenticado(request):
        return RedirectResponse("/login", status_code=303)
    return pagina("Administración (demo)", f"""<p>Simulador de fallas: los próximos <b>{FALLAS['restantes']}</b> registros fallarán con error 500.</p>
<form method="post" action="/admin/falla"><input name="n" type="number" value="3" style="width:90px"> <button>Provocar fallas</button></form>
<form method="post" action="/admin/falla"><input type="hidden" name="n" value="0"><button>Restablecer</button></form>
<p><b>{con().execute('SELECT count(*) FROM candidato').fetchone()[0]}</b> candidatos registrados.</p>""")


@app.post("/admin/falla")
def falla(request: Request, n: int = Form(0)):
    FALLAS["restantes"] = max(n, 0)
    return RedirectResponse("/admin", status_code=303)


@app.post("/api/falla/{n}")
def falla_api(n: int):
    """Atajo para los scripts de prueba (sin sesión)."""
    FALLAS["restantes"] = max(n, 0)
    return {"fallas_restantes": FALLAS["restantes"]}


@app.get("/health")
def health():
    return {"ok": True}
