"""Portal web: formulario del candidato y bandejas del personal de RR.HH."""
import csv
import io
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import auth, db, flowable, servicios
from . import plantillas as pl
from .auth import requiere, usuario_actual
from .config import EMPRESA_NOMBRE, UPLOADS_DIR, URL_PUBLICA
from .workers_backend import evaluar_postulacion
from common.experiencia import anios_experiencia

log = logging.getLogger("portal")
router = APIRouter()
T = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
T.env.filters["fecha"] = lambda v: v.strftime("%d/%m/%Y %H:%M") if v else "—"
T.env.globals["css_v"] = int((Path(__file__).parent / "static" / "style.css").stat().st_mtime)
T.env.globals["empresa"] = EMPRESA_NOMBRE
T.env.filters["fecha_corta"] = lambda v: v.strftime("%d/%m/%Y") if v else "—"
T.env.filters["lineas"] = lambda t: [x.strip() for x in str(t or "").splitlines() if x.strip()]
T.env.filters["pct"] = lambda v: f"{float(v) * 100:.0f}%" if v is not None else "—"
ESTADOS = ["Recibida", "En extracción", "En validación", "Aprobada", "Rechazada", "Registrada",
           "En entrevista", "Descartada", "Error", "Duplicada"]


def render(request, nombre, usuario=None, **ctx):
    return T.TemplateResponse(request, nombre, {"u": usuario, "estados": ESTADOS, **ctx})


# ---------- público: candidato ----------

VAC_COLS = "id,codigo,titulo,descripcion,requisitos,area,ubicacion,modalidad,contrato,salario,responsabilidades,ofrecemos,creada_en"
MENSAJE_ESTADO = {
    "Recibida": ("Recibimos tu postulación", "Ya está en nuestro sistema y pronto será revisada."),
    "En extracción": ("Estamos leyendo tu hoja de vida", "Revisamos automáticamente tus datos."),
    "En validación": ("Tu perfil está en revisión", "Una persona del equipo de selección lo está revisando."),
    "Aprobada": ("Tu perfil avanzó", "Pasaste la revisión inicial."),
    "Registrada": ("Tu perfil avanzó", "Quedaste registrado en nuestro sistema de talento."),
    "En entrevista": ("Avanzaste a la etapa de entrevistas", "Te contactaremos para acordar el horario."),
    "Rechazada": ("Tu perfil no continúa en este proceso", "Gracias por tu interés. Puedes postularte a otras vacantes."),
    "Descartada": ("Tu perfil no continúa en este proceso", "Gracias por tu interés. Puedes postularte a otras vacantes."),
    "Error": ("Tu postulación está en revisión manual", "Nuestro equipo la está atendiendo; no necesitas hacer nada."),
    "Duplicada": ("Ya teníamos tu postulación", "Detectamos una postulación anterior a la misma vacante."),
}


def _activas(q: str = "", modalidad: str = "", area: str = ""):
    sql, par = f"SELECT {VAC_COLS} FROM vacante WHERE estado='activa'", []
    if q:
        sql += " AND (titulo ILIKE %s OR descripcion ILIKE %s OR coalesce(area,'') ILIKE %s)"
        par += [f"%{q}%"] * 3
    if modalidad:
        sql += " AND modalidad=%s"
        par.append(modalidad)
    if area:
        sql += " AND area=%s"
        par.append(area)
    return db.q(sql + " ORDER BY creada_en DESC, id DESC", par)


@router.get("/", response_class=HTMLResponse)
def inicio(request: Request, q: str = "", modalidad: str = "", area: str = ""):
    opciones = db.q("SELECT DISTINCT modalidad, area FROM vacante WHERE estado='activa'")
    return render(request, "empleos.html", vacantes=_activas(q.strip(), modalidad, area), q=q, modalidad=modalidad, area=area,
                  modalidades=sorted({o["modalidad"] for o in opciones if o["modalidad"]}),
                  areas=sorted({o["area"] for o in opciones if o["area"]}), empresa=EMPRESA_NOMBRE)


def _pagina_empleo(request, codigo, error=None, status=200):
    v = db.q1(f"SELECT {VAC_COLS}, estado FROM vacante WHERE codigo=%s", (codigo.upper(),))
    if not v:
        raise HTTPException(404, "No encontramos esa vacante")
    return T.TemplateResponse(request, "empleo.html", {"u": None, "v": v, "error": error, "empresa": EMPRESA_NOMBRE,
                                                       "url": f"{URL_PUBLICA}/empleos/{v['codigo']}"}, status_code=status)


@router.get("/empleos/{codigo}", response_class=HTMLResponse)
def empleo(request: Request, codigo: str):
    return _pagina_empleo(request, codigo)


@router.get("/estado", response_class=HTMLResponse)
def estado_form(request: Request):
    return render(request, "estado.html", resultado=None, error=None)


@router.post("/estado", response_class=HTMLResponse)
def estado_consulta(request: Request, numero: str = Form(...), correo: str = Form(...)):
    p = db.q1("""SELECT p.numero, p.estado, p.recibida_en, v.titulo FROM postulacion p JOIN candidato c ON c.id=p.candidato_id
                 JOIN vacante v ON v.id=p.vacante_id WHERE p.numero=%s AND lower(c.correo)=lower(%s)""",
              (numero.strip().upper(), correo.strip()))
    if not p:   # mismo mensaje exista o no el número: no revela qué postulaciones existen
        return render(request, "estado.html", resultado=None, error="No encontramos una postulación con esos datos.")
    titulo, detalle = MENSAJE_ESTADO.get(p["estado"], ("En proceso", ""))
    return render(request, "estado.html", resultado={**p, "titulo_estado": titulo, "detalle": detalle}, error=None)


@router.post("/postular", response_class=HTMLResponse)
async def postular(request: Request, vacante_id: int = Form(...), nombre: str = Form(...), correo: str = Form(...),
                   telefono: str = Form(""), acepta: str | None = Form(None), cv: UploadFile = File(...)):
    try:
        r = servicios.crear_postulacion(vacante_id=vacante_id, nombre=nombre, correo=correo, telefono=telefono,
                                        acepta_datos=bool(acepta), archivo_nombre=cv.filename or "cv",
                                        contenido=await cv.read(), canal="formulario")
    except servicios.ErrorNegocio as e:
        v = db.q1("SELECT codigo FROM vacante WHERE id=%s", (vacante_id,))
        return _pagina_empleo(request, v["codigo"], error=str(e), status=400)
    return render(request, "confirmacion.html", r=r)


# ---------- sesión ----------

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return render(request, "login.html", error=None)


@router.post("/login", response_class=HTMLResponse)
def login(request: Request, correo: str = Form(...), password: str = Form(...)):
    u = db.q1("SELECT * FROM usuario WHERE lower(correo)=%s", (correo.strip().lower(),))
    if not u or not auth.check_pw(password, u["password_hash"]):
        return render(request, "login.html", error="Correo o contraseña incorrectos")
    resp = RedirectResponse("/app", status_code=303)
    resp.set_cookie("token", auth.crear_token(u), httponly=True, samesite="lax", max_age=8 * 3600)
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("token")
    return resp


# ---------- tablero ----------

@router.get("/app", response_class=HTMLResponse)
def tablero(request: Request, vacante: int | None = None, u: dict = Depends(usuario_actual)):
    filtro, p = ("WHERE vacante_id=%s", (vacante,)) if vacante else ("", ())
    por_estado = {r["estado"]: r["n"] for r in db.q(f"SELECT estado, count(*) n FROM postulacion {filtro} GROUP BY estado", p)}
    total = sum(por_estado.values())
    ciclo = db.q1(f"""SELECT avg(extract(epoch FROM (actualizada_en - recibida_en)))/60 AS min FROM postulacion
                      WHERE estado IN ('Registrada','En entrevista','Descartada','Rechazada') {'AND vacante_id=%s' if vacante else ''}""", p)
    # tasa de intervención humana = postulaciones que pasaron por validación humana
    hum = db.q1(f"""SELECT count(DISTINCT e.postulacion_id) n FROM evento e JOIN postulacion x ON x.id=e.postulacion_id
                    WHERE e.accion='tarea_completada' AND e.detalle->>'tarea'='u_validar' {'AND x.vacante_id=%s' if vacante else ''}""", p)
    costo = db.q1(f"""SELECT coalesce(sum(costo_usd),0) c FROM extraccion e JOIN postulacion x ON x.id=e.postulacion_id
                      {'WHERE x.vacante_id=%s' if vacante else ''}""", p)
    vac = db.q("SELECT id,codigo,titulo FROM vacante ORDER BY id")
    return render(request, "tablero.html", u, por_estado=por_estado, total=total, vacantes=vac, vacante=vacante,
                  ciclo=ciclo["min"], intervencion=(100 * hum["n"] / total) if total else 0, costo=costo["c"],
                  pendientes=len(flowable.tareas(auth.GRUPOS[u["rol"]])))


# ---------- postulaciones ----------

def _lista(estado=None, vacante=None, q=None):
    w, p = [], []
    if estado:
        w.append("p.estado=%s"); p.append(estado)
    if vacante:
        w.append("p.vacante_id=%s"); p.append(vacante)
    if q:
        w.append("(c.nombre ILIKE %s OR c.correo ILIKE %s OR p.numero ILIKE %s)"); p += [f"%{q}%"] * 3
    return db.q(f"""SELECT p.id,p.numero,p.estado,p.clasificacion,p.puntaje,p.canal,p.recibida_en,p.rrhh_id,
                           c.nombre,c.correo,v.titulo,v.codigo FROM postulacion p
                    JOIN candidato c ON c.id=p.candidato_id JOIN vacante v ON v.id=p.vacante_id
                    {'WHERE ' + ' AND '.join(w) if w else ''} ORDER BY p.id DESC LIMIT 500""", p)


@router.get("/app/postulaciones", response_class=HTMLResponse)
def postulaciones(request: Request, estado: str | None = None, vacante: int | None = None, q: str | None = None,
                  u: dict = Depends(usuario_actual)):
    return render(request, "postulaciones.html", u, filas=_lista(estado, vacante, q), estado=estado, vacante=vacante, q=q,
                  vacantes=db.q("SELECT id,codigo,titulo FROM vacante ORDER BY id"))


@router.get("/app/postulaciones.csv")
def exportar(vacante: int | None = None, u: dict = Depends(requiere("auxiliar", "coordinador"))):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["numero", "candidato", "correo", "vacante", "puntaje", "clasificacion", "estado", "canal", "recibida"])
    for f in _lista(vacante=vacante):
        w.writerow([f["numero"], f["nombre"], f["correo"], f["codigo"], f["puntaje"], f["clasificacion"], f["estado"],
                    f["canal"], f["recibida_en"]])
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=postulaciones.csv"})


@router.get("/app/postulaciones/{pid}", response_class=HTMLResponse)
def detalle(request: Request, pid: int, u: dict = Depends(usuario_actual)):
    p = db.q1("""SELECT p.*, c.nombre,c.correo,c.telefono, v.titulo,v.codigo FROM postulacion p
                 JOIN candidato c ON c.id=p.candidato_id JOIN vacante v ON v.id=p.vacante_id WHERE p.id=%s""", (pid,))
    if not p:
        raise HTTPException(404, "Postulación no encontrada")
    try:
        hist = flowable.historial(p["proceso_id"]) if p["proceso_id"] else []
    except Exception:
        hist = []
    return render(request, "postulacion.html", u, p=p, ext=servicios.datos_vigentes(pid), hist=hist,
                  eventos=db.q("SELECT * FROM evento WHERE postulacion_id=%s ORDER BY id", (pid,)),
                  incidencias=db.q("SELECT * FROM incidencia WHERE postulacion_id=%s ORDER BY id", (pid,)),
                  decisiones=db.q("SELECT d.*, u.nombre AS usuario FROM decision d LEFT JOIN usuario u ON u.id=d.usuario_id WHERE postulacion_id=%s ORDER BY d.id", (pid,)),
                  notifs=db.q("SELECT * FROM notificacion WHERE postulacion_id=%s ORDER BY id", (pid,)))


@router.get("/app/postulaciones/{pid}/archivo")
def archivo(pid: int, u: dict = Depends(usuario_actual)):
    p = db.q1("SELECT archivo_path FROM postulacion WHERE id=%s", (pid,))
    if not p or not p["archivo_path"]:
        raise HTTPException(404, "Archivo no disponible")
    ruta = Path(UPLOADS_DIR) / p["archivo_path"]
    if not ruta.exists():
        raise HTTPException(404, "Archivo eliminado")
    tipo = "application/pdf" if ruta.suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(ruta, media_type=tipo, headers={"Content-Disposition": f'inline; filename="{ruta.name}"'})


@router.post("/app/postulaciones/{pid}/eliminar-datos")
def eliminar_datos(pid: int, u: dict = Depends(requiere("admin"))):
    """RNF-10: eliminación de datos personales a solicitud del titular (anonimiza y borra el archivo)."""
    p = db.q1("SELECT archivo_path, candidato_id FROM postulacion WHERE id=%s", (pid,))
    if not p:
        raise HTTPException(404)
    if p["archivo_path"]:
        (Path(UPLOADS_DIR) / p["archivo_path"]).unlink(missing_ok=True)
    db.ex("UPDATE candidato SET nombre='[ELIMINADO]', correo='eliminado-%s@anonimo.local', telefono=NULL, documento=NULL WHERE id=%s",
          (p["candidato_id"], p["candidato_id"]))
    db.ex("DELETE FROM extraccion WHERE postulacion_id IN (SELECT id FROM postulacion WHERE candidato_id=%s)", (p["candidato_id"],))
    db.ex("UPDATE postulacion SET archivo_path='' WHERE candidato_id=%s", (p["candidato_id"],))
    servicios.evento(pid, u["correo"], "datos_eliminados", "ok")
    return RedirectResponse(f"/app/postulaciones/{pid}", status_code=303)


# ---------- tareas humanas ----------

@router.get("/app/tareas", response_class=HTMLResponse)
def tareas(request: Request, u: dict = Depends(usuario_actual)):
    ts = flowable.tareas(auth.GRUPOS[u["rol"]])
    ids = [t["postulacion_id"] for t in ts if t["postulacion_id"]]
    info = {r["id"]: r for r in db.q("""SELECT p.id,p.numero,p.puntaje,p.clasificacion,c.nombre,v.titulo FROM postulacion p
        JOIN candidato c ON c.id=p.candidato_id JOIN vacante v ON v.id=p.vacante_id WHERE p.id = ANY(%s)""", (ids,))}
    return render(request, "tareas.html", u, tareas=ts, info=info)


def _bloques_form(ext):
    """Estructura editable (datos validados si existen, si no extraídos)."""
    return (ext["datos_validados"] or ext["datos"]) if ext else {}


ROL_DE_TAREA = {"u_validar": {"analista", "coordinador"},   # el coordinador la recibe al escalarse (RF-19)
                "u_incidencia": {"auxiliar"}, "u_registro_manual": {"auxiliar"},
                "u_entrevista": {"coordinador"}}


def _exigir_rol_tarea(u: dict, t: dict):
    """Cada tarea solo la ve y la completa el rol responsable (el administrador puede todas)."""
    if u["rol"] != "admin" and u["rol"] not in ROL_DE_TAREA.get(t["taskDefinitionKey"], set()):
        raise HTTPException(403, "No tienes permiso para esta tarea")


@router.get("/app/tareas/{task_id}", response_class=HTMLResponse)
def tarea(request: Request, task_id: str, u: dict = Depends(usuario_actual)):
    t = flowable.tarea(task_id)
    if not t:
        raise HTTPException(404, "La tarea no existe o ya fue completada")
    _exigir_rol_tarea(u, t)
    pid = int(t["vars"]["postulacionId"])
    p = db.q1("""SELECT p.*, c.nombre,c.correo,c.telefono, v.titulo,v.requisitos FROM postulacion p
                 JOIN candidato c ON c.id=p.candidato_id JOIN vacante v ON v.id=p.vacante_id WHERE p.id=%s""", (pid,))
    ext = servicios.datos_vigentes(pid)
    return render(request, "tarea.html", u, t=t, p=p, ext=ext, datos=_bloques_form(ext),
                  incidencias=db.q("SELECT * FROM incidencia WHERE postulacion_id=%s ORDER BY id DESC LIMIT 5", (pid,)),
                  umbral=0.8, error=request.query_params.get("error"))


def _lista_form(form, prefijo, campos):
    cols = [form.getlist(f"{prefijo}_{c}") for c in campos]
    filas = []
    for vals in zip(*cols):
        if any(v.strip() for v in vals):
            filas.append({c: v.strip() or None for c, v in zip(campos, vals)})
    return filas


@router.post("/app/tareas/{task_id}")
async def completar_tarea(request: Request, task_id: str, u: dict = Depends(usuario_actual)):
    t = flowable.tarea(task_id)
    if not t:
        raise HTTPException(404, "La tarea no existe o ya fue completada")
    _exigir_rol_tarea(u, t)
    pid = int(t["vars"]["postulacionId"])
    form = await request.form()
    decision, obs = form.get("decision", ""), (form.get("observacion") or "").strip()
    clave = t["taskDefinitionKey"]
    validas = {"u_validar": ("aprobar", "rechazar", "pedir_info"), "u_incidencia": ("reintentar", "cerrar"),
               "u_registro_manual": ("registrado", "reintentar", "cerrar"), "u_entrevista": ("continuar", "descartar")}
    if decision not in validas.get(clave, ()):
        return RedirectResponse(f"/app/tareas/{task_id}?error=Selecciona+una+decisión", status_code=303)
    if decision in ("rechazar", "descartar") and not obs:          # RF-18 / RNF-13
        return RedirectResponse(f"/app/tareas/{task_id}?error=La+observación+es+obligatoria+al+rechazar+o+descartar", status_code=303)

    if clave == "u_validar" and decision != "pedir_info":
        datos = {
            "datos_personales": {k: (form.get(f"p_{k}") or "").strip() or None
                                 for k in ("nombre", "correo", "telefono", "documento", "ubicacion")},
            "formacion": _lista_form(form, "f", ["titulo", "institucion", "anio", "nivel"]),
            "experiencia": _lista_form(form, "e", ["cargo", "empresa", "fecha_inicio", "fecha_fin", "funciones"]),
            "habilidades": [h.strip() for h in (form.get("habilidades") or "").split(",") if h.strip()],
            "idiomas": [{"idioma": (l.rsplit(" ", 1)[0] if " " in l else l).strip(), "nivel": l.rsplit(" ", 1)[1] if " " in l else None}
                        for l in (form.get("idiomas") or "").splitlines() if l.strip()],
            "certificaciones": [c.strip() for c in (form.get("certificaciones") or "").split(",") if c.strip()],
        }
        for f in datos["formacion"]:
            f["anio"] = int(f["anio"]) if f["anio"] and str(f["anio"]).isdigit() else None
        original = servicios.datos_vigentes(pid)
        cambios = [k for k in datos if datos[k] != original["datos"].get(k)] if original else []
        db.ex("""UPDATE extraccion SET datos_validados=%s, anios_experiencia=%s, validado_por=%s, validado_en=now()
                 WHERE id=%s""", (db.J(datos), anios_experiencia(datos["experiencia"]), u["id"], original["id"]))
        servicios.evento(pid, u["correo"], "datos_corregidos", "ok", {"bloques_modificados": cambios})
        evaluar_postulacion(pid)                                   # recalcula con los datos corregidos

    if clave in ("u_validar", "u_entrevista"):
        db.ex("INSERT INTO decision(postulacion_id,tipo,resultado,observacion,usuario_id) VALUES (%s,%s,%s,%s,%s)",
              (pid, {"u_validar": "validacion", "u_entrevista": "continuidad"}[clave],
               decision, obs or None, u["id"]))
    if clave == "u_registro_manual" and decision == "registrado":
        rid = (form.get("rrhh_id") or "").strip()
        if not rid:
            return RedirectResponse(f"/app/tareas/{task_id}?error=Indica+el+ID+asignado+en+RR.HH.", status_code=303)
        db.ex("UPDATE postulacion SET rrhh_id=%s WHERE id=%s", (rid, pid))
    servicios.evento(pid, u["correo"], "tarea_completada", decision, {"tarea": clave, "observacion": obs or None})
    flowable.completar(task_id, u["correo"], {"decision": decision})
    return RedirectResponse("/app/tareas", status_code=303)


# ---------- vacantes ----------

NIVELES_FORMACION = ["Bachiller", "Técnico", "Tecnólogo", "Profesional", "Especialización", "Maestría", "Doctorado"]
CAMPOS_OFERTA = ("area", "ubicacion", "modalidad", "contrato", "salario", "responsabilidades", "ofrecemos")


def _items(txt: str) -> list[str]:
    return [x.strip() for x in re.split(r"[,\n]", txt or "") if x.strip()]


@router.get("/app/vacantes", response_class=HTMLResponse)
def vacantes(request: Request, u: dict = Depends(usuario_actual)):
    vs = db.q("""SELECT v.*, (SELECT count(*) FROM postulacion p WHERE p.vacante_id=v.id) AS n FROM vacante v ORDER BY v.id""")
    return render(request, "vacantes.html", u, vacantes=vs, url_publica=URL_PUBLICA, error=request.query_params.get("error"),
                  ok=request.query_params.get("ok"))


@router.get("/app/vacantes/nueva", response_class=HTMLResponse)
def vacante_nueva(request: Request, u: dict = Depends(requiere("auxiliar"))):
    from .rules import PESOS_DEFECTO
    return render(request, "vacante_form.html", u, v=None, req={}, pesos=PESOS_DEFECTO, niveles=NIVELES_FORMACION)


@router.get("/app/vacantes/{vid}/editar", response_class=HTMLResponse)
def vacante_editar(request: Request, vid: int, u: dict = Depends(requiere("auxiliar"))):
    v = db.q1("SELECT * FROM vacante WHERE id=%s", (vid,))
    if not v:
        raise HTTPException(404, "Vacante no encontrada")
    return render(request, "vacante_form.html", u, v=v, req=v["requisitos"] or {}, pesos=v["pesos"], niveles=NIVELES_FORMACION)


@router.post("/app/vacantes/guardar")
def vacante_guardar(vid: int | None = Form(None), codigo: str = Form(...), titulo: str = Form(...),
                    descripcion: str = Form(""), estado: str = Form("activa"), anios: float = Form(0),
                    formacion: str = Form(""), obligatorias: str = Form(""), deseables: str = Form(""), idiomas: str = Form(""),
                    p_experiencia: float = Form(35), p_formacion: float = Form(25), p_habilidades: float = Form(30),
                    p_idioma: float = Form(10), area: str = Form(""), ubicacion: str = Form(""), modalidad: str = Form(""),
                    contrato: str = Form(""), salario: str = Form(""), responsabilidades: str = Form(""),
                    ofrecemos: str = Form(""), u: dict = Depends(requiere("auxiliar"))):
    codigo = re.sub(r"[^A-Z0-9-]", "", codigo.strip().upper())
    total = p_experiencia + p_formacion + p_habilidades + p_idioma
    err = None
    if not codigo or not titulo.strip():
        err = "El código y el título son obligatorios."
    elif estado not in ("activa", "cerrada"):
        err = "Estado inválido."
    elif total <= 0 or min(p_experiencia, p_formacion, p_habilidades, p_idioma) < 0:
        err = "Los pesos del puntaje deben ser positivos."
    if err:
        return RedirectResponse(f"/app/vacantes?error={err.replace(' ', '+')}", status_code=303)
    req = {"anios_experiencia": anios, "formacion_minima": formacion or None,
           "habilidades_obligatorias": _items(obligatorias), "habilidades_deseables": _items(deseables),
           "idiomas": [{"idioma": i.split()[0], "nivel": " ".join(i.split()[1:]) or None} for i in _items(idiomas)]}
    pesos = {k: round(v / total, 4) for k, v in (("experiencia", p_experiencia), ("formacion", p_formacion),
                                                  ("habilidades", p_habilidades), ("idioma", p_idioma))}
    oferta = dict(zip(CAMPOS_OFERTA, (area, ubicacion, modalidad, contrato, salario, responsabilidades, ofrecemos)))
    try:
        if vid:
            db.ex("""UPDATE vacante SET codigo=%s,titulo=%s,descripcion=%s,estado=%s,requisitos=%s,pesos=%s,
                     area=%s,ubicacion=%s,modalidad=%s,contrato=%s,salario=%s,responsabilidades=%s,ofrecemos=%s WHERE id=%s""",
                  (codigo, titulo.strip(), descripcion, estado, db.J(req), db.J(pesos), *oferta.values(), vid))
        else:
            db.ex("""INSERT INTO vacante(codigo,titulo,descripcion,estado,requisitos,pesos,area,ubicacion,modalidad,contrato,salario,
                     responsabilidades,ofrecemos) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (codigo, titulo.strip(), descripcion, estado, db.J(req), db.J(pesos), *oferta.values()))
    except Exception as e:   # código repetido (UNIQUE)
        log.warning("vacante no guardada: %s", e)
        return RedirectResponse("/app/vacantes?error=No+se+pudo+guardar:+el+código+ya+existe", status_code=303)
    servicios.evento(None, u["correo"], "vacante_guardada", codigo, {"estado": estado})
    return RedirectResponse(f"/app/vacantes?ok=Vacante+{codigo}+guardada", status_code=303)


@router.post("/app/vacantes/estado")
def vacante_estado(vid: int = Form(...), estado: str = Form(...), u: dict = Depends(requiere("auxiliar"))):
    if estado not in ("activa", "cerrada"):
        raise HTTPException(400, "Estado inválido")
    db.ex("UPDATE vacante SET estado=%s WHERE id=%s", (estado, vid))
    return RedirectResponse("/app/vacantes?ok=Estado+actualizado", status_code=303)


@router.post("/app/vacantes")
def guardar_vacante(vid: int | None = Form(None), codigo: str = Form(...), titulo: str = Form(...),
                    descripcion: str = Form(""), estado: str = Form("activa"), requisitos: str = Form("{}"),
                    pesos: str = Form("{}"), u: dict = Depends(requiere("auxiliar"))):
    """Edición avanzada con JSON (se conserva por compatibilidad y para las pruebas automáticas)."""
    try:
        req, pes = json.loads(requisitos or "{}"), json.loads(pesos or "{}")
    except json.JSONDecodeError:
        return RedirectResponse("/app/vacantes?error=Requisitos+o+pesos+no+son+JSON+válido", status_code=303)
    if estado not in ("activa", "cerrada"):
        raise HTTPException(400, "Estado inválido")
    pes = pes or {"experiencia": 0.35, "formacion": 0.25, "habilidades": 0.30, "idioma": 0.10}
    if vid:
        db.ex("UPDATE vacante SET codigo=%s,titulo=%s,descripcion=%s,estado=%s,requisitos=%s,pesos=%s WHERE id=%s",
              (codigo.strip().upper(), titulo, descripcion, estado, db.J(req), db.J(pes), vid))
    else:
        db.ex("INSERT INTO vacante(codigo,titulo,descripcion,estado,requisitos,pesos) VALUES (%s,%s,%s,%s,%s,%s)",
              (codigo.strip().upper(), titulo, descripcion, estado, db.J(req), db.J(pes)))
    return RedirectResponse("/app/vacantes", status_code=303)


# ---------- incidencias ----------

@router.get("/app/incidencias", response_class=HTMLResponse)
def incidencias(request: Request, u: dict = Depends(requiere("auxiliar", "coordinador"))):
    return render(request, "incidencias.html", u, filas=db.q("""
        SELECT i.*, p.numero FROM incidencia i LEFT JOIN postulacion p ON p.id=i.postulacion_id ORDER BY i.id DESC LIMIT 200"""))


@router.get("/app/capturas/{nombre}")
def captura(nombre: str, u: dict = Depends(usuario_actual)):
    ruta = (Path(UPLOADS_DIR) / "capturas" / Path(nombre).name)
    if not ruta.exists():
        raise HTTPException(404)
    return FileResponse(ruta, media_type="image/png")


# ---------- plantillas de correo editables (RF-28) ----------

@router.get("/app/plantillas", response_class=HTMLResponse)
def ver_plantillas(request: Request, u: dict = Depends(requiere("admin"))):
    editadas = {r["clave"]: r for r in db.q("SELECT * FROM plantilla")}
    lista = []
    for clave, (asunto, cuerpo) in pl.DEFECTO.items():
        e = editadas.get(clave)
        lista.append({"clave": clave, "etiqueta": pl.ETIQUETAS[clave], "personalizada": bool(e),
                      "asunto": e["asunto"] if e else asunto, "cuerpo": e["cuerpo"] if e else cuerpo})
    return render(request, "plantillas.html", u, plantillas=lista, ok=request.query_params.get("ok"))


@router.post("/app/plantillas")
def guardar_plantilla(clave: str = Form(...), asunto: str = Form(""), cuerpo: str = Form(""), restaurar: str | None = Form(None),
                      u: dict = Depends(requiere("admin"))):
    if clave not in pl.DEFECTO:
        raise HTTPException(400, "Plantilla desconocida")
    if restaurar:
        db.ex("DELETE FROM plantilla WHERE clave=%s", (clave,))
    else:
        if not asunto.strip() or not cuerpo.strip():
            raise HTTPException(400, "El asunto y el mensaje no pueden estar vacíos")
        db.ex("""INSERT INTO plantilla(clave,asunto,cuerpo) VALUES (%s,%s,%s)
                 ON CONFLICT (clave) DO UPDATE SET asunto=EXCLUDED.asunto, cuerpo=EXCLUDED.cuerpo, actualizada_en=now()""",
              (clave, asunto.strip(), cuerpo.strip()))
    return RedirectResponse("/app/plantillas?ok=1", status_code=303)


# ---------- histórico de vacantes cerradas (HU-18) ----------

@router.get("/app/historico", response_class=HTMLResponse)
def historico(request: Request, u: dict = Depends(requiere("auxiliar", "coordinador"))):
    vs = db.q("SELECT * FROM vacante WHERE estado='cerrada' ORDER BY id DESC")
    for v in vs:
        filas = db.q("SELECT estado, count(*) AS n FROM postulacion WHERE vacante_id=%s GROUP BY estado ORDER BY n DESC", (v["id"],))
        v["estados"] = {f["estado"]: f["n"] for f in filas}
        v["total"] = sum(v["estados"].values())
    return render(request, "historico.html", u, vacantes=vs)
