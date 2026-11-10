"""Pruebas de punta a punta (RNF-20) contra el sistema levantado con docker compose.

Simula a candidatos y a las personas (analista, auxiliar, coordinador) usando el portal como lo haría un navegador.
Escenarios:  aprobado | rechazado | falla_bot | correo | duplicado | todos

Uso: python scripts/e2e.py [escenario]
"""
import json
import re
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "services" / "api"))
sys.path.insert(0, str(RAIZ / "services"))
from app import rules  # noqa: E402

BASE, RRHH = "http://127.0.0.1:8000", "http://127.0.0.1:9000"
PASS = "demo1234"
VAC = {"VAC-001": 1, "VAC-002": 2, "VAC-003": 3}
VACANTES = {  # mismos requisitos que la siembra de la API (para elegir CV de prueba)
    "VAC-001": {"anios_experiencia": 2, "formacion_minima": "Profesional", "habilidades_obligatorias": ["Python", "SQL"],
                "habilidades_deseables": ["FastAPI", "Docker", "PostgreSQL"], "idiomas": [{"idioma": "Inglés", "nivel": "B1"}]},
    "VAC-002": {"anios_experiencia": 1, "formacion_minima": "Tecnólogo", "habilidades_obligatorias": ["SQL"],
                "habilidades_deseables": ["Power BI", "Excel", "Python"], "idiomas": []},
    "VAC-003": {"anios_experiencia": 3, "formacion_minima": "Profesional", "habilidades_obligatorias": ["Docker", "Linux"],
                "habilidades_deseables": ["Kubernetes", "AWS", "Git"], "idiomas": [{"idioma": "Inglés", "nivel": "B2"}]},
}
resultados = []


def ok(nombre, cond, detalle=""):
    resultados.append((nombre, bool(cond)))
    print(f"  {'✔' if cond else '✘'} {nombre} {detalle}")
    return cond


def sesion(rol):
    c = httpx.Client(base_url=BASE, follow_redirects=True, timeout=60)
    r = c.post("/login", data={"correo": f"{rol}@empresa.test", "password": PASS})
    assert "token" in c.cookies, f"login falló para {rol}"
    return c


def documentos_en_rrhh():
    """Documentos ya registrados en el sistema RR.HH. (para elegir candidatos nuevos)."""
    c = httpx.Client(base_url=RRHH, follow_redirects=True)
    c.post("/login", data={"usuario": "robot", "password": "robot123"})
    return set(re.findall(r'class="doc">(\d+)<', c.get("/candidatos").text))


def elegir_cv(vacante, clase, excluir=(), nuevo_en_rrhh=False):
    """Elige un CV de datos_prueba cuya evaluación (sobre la verdad terreno) caiga en la clase pedida."""
    from math import floor
    sys.path.insert(0, str(RAIZ / "services"))
    from common.experiencia import anios_experiencia
    ya = documentos_en_rrhh() if nuevo_en_rrhh else set()
    for js in sorted((RAIZ / "datos_prueba").glob("*.json")):
        pdf = next((p for p in js.parent.glob(js.stem + ".*") if p.suffix in (".pdf", ".docx")), None)
        if pdf in excluir or pdf is None or pdf.suffix != ".pdf" or "escaneado" in pdf.name:
            continue
        d = json.loads(js.read_text(encoding="utf-8"))
        if d["datos_personales"]["documento"] in ya:
            continue
        r = rules.evaluar(d, anios_experiencia(d["experiencia"]), VACANTES[vacante])
        if r["clasificacion"] == clase:
            return pdf, d
    raise RuntimeError(f"No hay CV de clase {clase} para {vacante}")


def unico(pdf):
    """Bytes del PDF con un comentario final único (el PDF sigue siendo válido, pero el hash cambia)."""
    return pdf.read_bytes() + f"\n%%unico-{time.time_ns()}\n".encode()


def postular(vacante, pdf, nombre, correo, contenido=None):
    c = httpx.Client(base_url=BASE, follow_redirects=True, timeout=60)
    r = c.post("/postular", data={"vacante_id": VAC[vacante], "nombre": nombre, "correo": correo, "telefono": "3001234567", "acepta": "1"},
               files={"cv": (pdf.name, contenido or unico(pdf), "application/pdf")})
    m = re.search(r"POST-\d{4}-\d{6}", r.text)
    assert m, f"sin número de postulación: {BeautifulSoup(r.text, 'html.parser').get_text()[:200]}"
    return m.group(0)


def info(admin, numero):
    r = admin.get("/app/postulaciones", params={"q": numero})
    s = BeautifulSoup(r.text, "html.parser")
    a = s.find("a", href=re.compile(r"/app/postulaciones/\d+$"))
    pid = int(a["href"].rsplit("/", 1)[1])
    d = BeautifulSoup(admin.get(f"/app/postulaciones/{pid}").text, "html.parser")
    estado = d.find("span", class_=re.compile("^badge"))
    return pid, estado.get_text(strip=True), d


def esperar(admin, numero, estados, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        pid, est, _ = info(admin, numero)
        if est in estados:
            return est
        time.sleep(3)
    return info(admin, numero)[1]


def tareas_de(cli, pid_numero=None):
    s = BeautifulSoup(cli.get("/app/tareas").text, "html.parser")
    out = []
    for tr in s.find_all("tr"):
        a = tr.find("a", href=re.compile(r"/app/tareas/"))
        if a and (pid_numero is None or pid_numero in tr.get_text()):
            out.append((a["href"], tr.find("b").get_text(strip=True)))
    return out


def esperar_tarea(cli, numero, nombre, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        for href, n in tareas_de(cli, numero):
            if nombre in n:
                return href
        time.sleep(3)
    return None


def enviar_form(cli, href, extra):
    """Envía el formulario de la tarea como lo haría un navegador (valores actuales + decisión)."""
    s = BeautifulSoup(cli.get(href).text, "html.parser")
    form = s.find("form", action=re.compile("/app/tareas/"))
    data = []
    for i in form.find_all(["input", "textarea", "select"]):
        n = i.get("name")
        if not n or i.get("type") in ("radio", "checkbox"):
            continue
        if i.name == "select":
            sel = i.find("option", selected=True) or i.find("option")
            data.append((n, sel.get_text(strip=True)))
        elif i.name == "textarea":
            data.append((n, i.get_text()))
        else:
            data.append((n, i.get("value", "")))
    data = [(k, v) for k, v in data if k not in extra] + list(extra.items())
    agrupado = {}
    for k, v in data:
        agrupado.setdefault(k, []).append(v)
    return cli.post(href, data=agrupado)


def correo_candidato(n):
    return f"e2e.{int(time.time())}.{n}@prueba.com"


def llegar_a_registro(admin, analista, numero):
    """Avanza hasta Registrada, aprobando la validación humana si hace falta."""
    t0 = time.time()
    validada = False
    while time.time() - t0 < 240:
        _, est, _ = info(admin, numero)
        if est in ("Registrada", "Error", "Rechazada", "En entrevista", "Descartada"):
            return est, validada
        h = next((h for h, n in tareas_de(analista, numero) if "Validar" in n), None)
        if h and not validada:
            enviar_form(analista, h, {"decision": "aprobar", "observacion": "Datos verificados contra el original"})
            validada = True
        time.sleep(3)
    return info(admin, numero)[1], validada


# ------------------------------------------------------------ escenarios

def escenario_aprobado():
    print("\n== Escenario 1: candidato aprobado → registro RPA → pasa a entrevistas")
    admin, analista, coord = sesion("admin"), sesion("analista"), sesion("coordinador")
    pdf, gt = elegir_cv("VAC-002", "Cumple", nuevo_en_rrhh=True)
    numero = postular("VAC-002", pdf, gt["datos_personales"]["nombre"], correo_candidato(1))
    ok("postulación recibida con número", numero.startswith("POST-"), numero)
    est, validada = llegar_a_registro(admin, analista, numero)
    ok("el robot registró al candidato (estado Registrada)", est == "Registrada", f"[{est}, validación humana={validada}]")
    pid, _, d = info(admin, numero)
    ok("se guardó el ID de RR.HH.", re.search(r"RH-\d{6}", d.get_text()) is not None)
    h = esperar_tarea(coord, numero, "entrevista")
    ok("el coordinador recibió la tarea de decisión", h is not None)
    if h:
        enviar_form(coord, h, {"decision": "continuar", "observacion": "Perfil sólido"})
        ok("el candidato pasa a entrevista", esperar(admin, numero, ["En entrevista"], 60) == "En entrevista")
        for _ in range(10):   # el aviso al candidato sale unos segundos después del cambio de estado
            _, _, d = info(admin, numero)
            if "entrevista" in d.get_text() and "enviado" in d.get_text():
                break
            time.sleep(3)
        ok("se avisó al candidato que avanza a entrevista", "enviado" in d.get_text())


def escenario_rechazado():
    print("\n== Escenario 2: candidato rechazado por el analista")
    admin, analista = sesion("admin"), sesion("analista")
    pdf, gt = elegir_cv("VAC-003", "No cumple")
    numero = postular("VAC-003", pdf, gt["datos_personales"]["nombre"], correo_candidato(2))
    h = esperar_tarea(analista, numero, "Validar")
    ok("la postulación que no cumple llega a validación humana (nunca se descarta sola)", h is not None)
    if h:
        r = enviar_form(analista, h, {"decision": "rechazar", "observacion": ""})
        ok("rechazar sin observación es bloqueado", "obligatoria" in r.text or "observaci" in r.url.query.decode().lower() if hasattr(r.url, "query") else True)
        h2 = next((h for h, n in tareas_de(analista, numero) if "Validar" in n), h)
        enviar_form(analista, h2, {"decision": "rechazar", "observacion": "No cumple experiencia ni habilidades obligatorias"})
        ok("estado final Rechazada", esperar(admin, numero, ["Rechazada"], 90) == "Rechazada")
        for _ in range(10):   # el correo sale unos segundos después del cambio de estado
            _, _, d = info(admin, numero)
            if "no_continua" in d.get_text() and "enviado" in d.get_text():
                break
            time.sleep(3)
        ok("se notificó al candidato", "no_continua" in d.get_text() and "enviado" in d.get_text())


def escenario_falla_bot():
    print("\n== Escenario 3: falla del bot RPA → tarea de registro manual → reintento")
    admin, analista, aux = sesion("admin"), sesion("analista"), sesion("auxiliar")
    httpx.post(f"{RRHH}/api/falla/9")                      # los próximos 9 registros fallan
    pdf, gt = elegir_cv("VAC-002", "Cumple", nuevo_en_rrhh=True)
    numero = postular("VAC-002", pdf, "Prueba Falla Bot", correo_candidato(3))
    t0, h = time.time(), None
    while time.time() - t0 < 300 and not h:
        for hh, n in tareas_de(analista, numero):
            if "Validar" in n:
                enviar_form(analista, hh, {"decision": "aprobar", "observacion": "ok"})
        h = next((hh for hh, n in tareas_de(aux, numero) if "manualmente" in n), None)
        time.sleep(3)
    ok("tras 3 intentos fallidos se creó la tarea de registro manual", h is not None)
    _, est, d = info(admin, numero)
    ok("la postulación quedó en estado Error (no se perdió)", est == "Error", f"[{est}]")
    ok("la incidencia guardó captura de pantalla", "Ver captura" in d.get_text())
    httpx.post(f"{RRHH}/api/falla/0")                      # el sistema RR.HH. se recupera
    if h:
        enviar_form(aux, h, {"decision": "reintentar", "observacion": "RR.HH. ya está disponible"})
        ok("el reintento registra al candidato", esperar(admin, numero, ["Registrada"], 120) == "Registrada")


def escenario_correo():
    print("\n== Escenario 4: postulación recibida por correo (IMAP)")
    admin = sesion("admin")
    pdf, gt = elegir_cv("VAC-002", "Cumple")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = f'"Carlos Correo" <carlos.{int(time.time())}@prueba.com>', "postulaciones@empresa.test", "Postulación VAC-002"
    msg.set_content("Adjunto mi hoja de vida.")
    msg.add_attachment(unico(pdf), maintype="application", subtype="pdf", filename=pdf.name)
    with smtplib.SMTP("localhost", 3025) as s:
        s.send_message(msg)
    t0, hallada = time.time(), None
    while time.time() - t0 < 90 and not hallada:
        s = BeautifulSoup(admin.get("/app/postulaciones", params={"q": "carlos."}).text, "html.parser")
        hallada = s.find("a", href=re.compile(r"/app/postulaciones/\d+$"))
        time.sleep(3)
    ok("el correo se convirtió en postulación", hallada is not None)
    if hallada:
        ok("canal registrado como 'correo'", "correo" in hallada.find_parent("tr").get_text())


def escenario_duplicado():
    print("\n== Escenario 5: postulación duplicada")
    admin = sesion("admin")
    pdf, gt = elegir_cv("VAC-002", "Cumple")
    mail = correo_candidato(5)
    datos = unico(pdf)
    n1 = postular("VAC-002", pdf, "Duplicado Uno", mail, datos)
    n2 = postular("VAC-002", pdf, "Duplicado Uno", mail, datos)
    _, est, _ = info(admin, n2)
    ok("la segunda postulación se marca Duplicada sin abrir proceso", est == "Duplicada", f"[{n1} / {n2}]")


def leer_buzon(correo, contiene, timeout=90):
    """Devuelve el texto del primer correo del buzón (GreenMail/IMAP) cuyo asunto contiene `contiene`."""
    import imaplib
    from email import message_from_bytes
    from email.header import decode_header, make_header
    t0 = time.time()
    while time.time() - t0 < timeout:
        M = imaplib.IMAP4("localhost", 3143)
        M.login(correo, "x")
        M.select("INBOX")
        _, data = M.search(None, "ALL")
        for num in data[0].split():
            _, raw = M.fetch(num, "(RFC822)")
            m = message_from_bytes(raw[0][1])
            asunto = str(make_header(decode_header(m["Subject"] or "")))
            cuerpo_txt = (m.get_payload(decode=True) or b"").decode("utf-8", "ignore")
            if contiene.lower() in (asunto + " " + cuerpo_txt).lower():
                cuerpo = m.get_payload(decode=True).decode("utf-8", "ignore")
                M.logout()
                return asunto + "\n" + cuerpo
        M.logout()
        time.sleep(3)
    return None


def cv_para_validacion(vacante="VAC-003"):
    """Un CV que NO sea 'Cumple' para esa vacante, para que genere tarea humana."""
    return elegir_cv(vacante, "No cumple")


def escenario_avisos_y_permisos():
    print("\n== Escenario 7: avisos de tareas al personal (sin datos del candidato) y permisos por rol")
    admin, analista, aux, coord = sesion("admin"), sesion("analista"), sesion("auxiliar"), sesion("coordinador")
    pdf, gt = cv_para_validacion()
    nombre = gt["datos_personales"]["nombre"]
    numero = postular("VAC-003", pdf, nombre, correo_candidato(7))
    h = esperar_tarea(analista, numero, "Validar")
    ok("se creó la tarea de validación para el analista", h is not None)
    aviso = leer_buzon("analista@empresa.test", numero, timeout=90)
    ok("el analista recibió un correo de aviso de tarea pendiente", aviso is not None and "tarea pendiente" in aviso.lower())
    ok("el aviso no expone el nombre del candidato", aviso is not None and nombre.split()[0] not in aviso)
    r = aux.get(h)
    ok("el auxiliar no puede abrir una tarea del analista (403)", r.status_code == 403, f"[{r.status_code}]")
    r2 = aux.post(h, data={"decision": "aprobar"})
    ok("el auxiliar tampoco puede completarla", r2.status_code == 403, f"[{r2.status_code}]")
    anon = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)
    ok("sin sesión no se accede a las tareas", anon.get("/app/tareas", headers={"accept": "text/html"}).status_code in (303, 401))
    ok("el archivo de la hoja de vida no es público", anon.get("/app/postulaciones/1/archivo").status_code in (303, 401))
    enviar_form(analista, h, {"decision": "rechazar", "observacion": "Prueba de permisos: no cumple"})


def escenario_plantillas():
    print("\n== Escenario 8: plantillas de correo editables")
    admin, analista = sesion("admin"), sesion("analista")
    marca = f"PLANTILLA-EDITADA-{int(time.time())}"
    admin.post("/app/plantillas", data={"clave": "confirmacion", "asunto": marca + " {numero}",
                                          "cuerpo": "Hola {nombre}, mensaje editado desde pantalla. {numero} {nombre.__class__}"})
    ok("el analista no puede editar plantillas (403)", analista.post("/app/plantillas", data={"clave": "confirmacion", "asunto": "x", "cuerpo": "x"}).status_code == 403)
    pdf, gt = cv_para_validacion()
    correo = correo_candidato(8)
    numero = postular("VAC-003", pdf, "Candidato Plantilla", correo)
    msg = leer_buzon(correo, marca)
    ok("el candidato recibe el correo con el asunto editado", msg is not None)
    ok("el marcador {numero} se reemplaza y no se puede acceder a atributos", msg is not None and numero in msg and "{nombre.__class__}" in msg)
    admin.post("/app/plantillas", data={"clave": "confirmacion", "asunto": "", "cuerpo": "", "restaurar": "1"})
    pdf2, gt2 = cv_para_validacion()
    correo2 = correo_candidato(88)
    n2 = postular("VAC-003", elegir_cv("VAC-003", "No cumple", excluir=[pdf])[0], "Candidato Restaurada", correo2)
    ok("al restaurar vuelve el texto original", leer_buzon(correo2, "Recibimos tu postulación") is not None)
    h = esperar_tarea(analista, n2, "Validar", 90)
    if h:
        enviar_form(analista, h, {"decision": "rechazar", "observacion": "Prueba: cierre"})
    h = esperar_tarea(analista, numero, "Validar", 90)
    if h:
        enviar_form(analista, h, {"decision": "rechazar", "observacion": "Prueba: cierre"})


def escenario_historico():
    print("\n== Escenario 9: vacantes cerradas, histórico y bloqueo de nuevas postulaciones")
    aux, admin = sesion("auxiliar"), sesion("admin")
    codigo = f"CER-{int(time.time()) % 1000:03d}"
    aux.post("/app/vacantes", data={"codigo": codigo, "titulo": "Vacante de prueba cerrada", "estado": "cerrada",
                                      "requisitos": "{}", "pesos": "{}"})
    pag = aux.get("/app/historico").text
    ok("la vacante cerrada aparece en el histórico", codigo in pag)
    c = httpx.Client(base_url=BASE, follow_redirects=True, timeout=30)
    home = c.get("/").text
    ok("una vacante cerrada no se ofrece a los candidatos", codigo not in home)
    cerrada = int(re.search(r"/app/postulaciones\?vacante=(\d+)", pag).group(1)) if "vacante=" in pag else None
    pdf, _ = cv_para_validacion()
    vid = [int(x) for x in re.findall(r'name="vid" value="(\d+)"', aux.get("/app/vacantes").text)][-1]
    r = c.post("/postular", data={"vacante_id": vid, "nombre": "Prueba", "correo": "x@y.co", "acepta": "1"},
               files={"cv": (pdf.name, unico(pdf), "application/pdf")})
    ok("el sistema rechaza postulaciones a una vacante cerrada", "cerrada" in r.text.lower())
    ok("el CSV exporta las postulaciones", "numero,candidato" in aux.get("/app/postulaciones.csv").text)


def escenario_escalacion():
    print("\n== Escenario 10: escalación de una validación sin atender (requiere ESCALACION_ISO corto, p. ej. PT1M)")
    admin, analista, coord = sesion("admin"), sesion("analista"), sesion("coordinador")
    pdf, gt = cv_para_validacion()
    numero = postular("VAC-003", pdf, gt["datos_personales"]["nombre"], correo_candidato(10))
    h = esperar_tarea(analista, numero, "Validar")
    ok("la tarea nace en la bandeja del analista", h is not None)
    ok("al inicio el coordinador NO la ve", not tareas_de(coord, numero))
    hc = esperar_tarea(coord, numero, "Validar", timeout=240)
    ok("tras el tiempo sin atender se escala a la bandeja del coordinador", hc is not None)
    aviso = leer_buzon("coordinador@empresa.test", numero, timeout=90)   # busca por número: el buzón guarda avisos de pruebas anteriores
    ok("el coordinador recibe un aviso de tarea escalada", aviso is not None and "escalada" in aviso.lower())
    if hc:
        enviar_form(coord, hc, {"decision": "rechazar", "observacion": "Escalada atendida por el coordinador"})
        ok("el coordinador puede resolver la tarea escalada", esperar(admin, numero, ["Rechazada"], 90) == "Rechazada")


def escenario_empleos():
    print("\n== Escenario 11: la empresa publica una vacante → el candidato la ve, se postula y consulta su estado")
    aux, coord = sesion("auxiliar"), sesion("coordinador")
    codigo = f"WEB-{int(time.time()) % 10000:04d}"
    r = aux.post("/app/vacantes/guardar", data={
        "codigo": codigo, "titulo": "Analista de Pruebas Web", "estado": "activa", "anios": "1", "formacion": "Tecnólogo",
        "obligatorias": "SQL, Excel", "deseables": "Power BI", "idiomas": "Inglés B1", "p_experiencia": "40", "p_formacion": "20",
        "p_habilidades": "30", "p_idioma": "10", "area": "Analítica", "ubicacion": "Bogotá", "modalidad": "Remoto",
        "contrato": "Término indefinido", "salario": "$4.000.000", "descripcion": "Oferta creada desde el formulario amigable.",
        "responsabilidades": "Probar flujos\nReportar hallazgos", "ofrecemos": "Trabajo remoto"})
    ok("la empresa crea la vacante con el formulario (sin JSON)", codigo in r.text and "guardada" in r.text)
    c = httpx.Client(base_url=BASE, follow_redirects=True, timeout=60)
    ok("la vacante aparece en la página pública de empleos", codigo in c.get("/").text)
    ok("el buscador y los filtros la encuentran", codigo in c.get("/", params={"q": "Pruebas Web", "modalidad": "Remoto"}).text
       and codigo not in c.get("/", params={"q": "zzzz-no-existe"}).text)
    det = c.get(f"/empleos/{codigo}").text
    ok("la página de la oferta muestra requisitos y datos estructurados para Google",
       "Power BI" in det and "Inglés" in det and "JobPosting" in det and "Probar flujos" in det)
    ok("un cargo del personal no coordinador no puede crear vacantes", coord.get("/app/vacantes/nueva").status_code == 403)
    vid = [int(x) for x in re.findall(r'name="vid" value="(\d+)"', aux.get("/app/vacantes").text)][-1]
    pdf, gt = cv_para_validacion()
    correo = f"web{int(time.time())}@correo.com"
    r = c.post("/postular", data={"vacante_id": vid, "nombre": gt["datos_personales"]["nombre"], "correo": correo,
                                  "telefono": "3001112233", "acepta": "1"},
               files={"cv": (pdf.name, unico(pdf), "application/pdf")})
    m = re.search(r"POST-\d{4}-\d{6}", r.text)
    ok("el candidato se postula desde la página de la oferta", m is not None)
    numero = m.group(0) if m else ""
    ok("consulta el estado con número y correo", "Recibimos" in c.post("/estado", data={"numero": numero, "correo": correo}).text
       or "estamos" in c.post("/estado", data={"numero": numero, "correo": correo}).text.lower()
       or "perfil" in c.post("/estado", data={"numero": numero, "correo": correo}).text.lower())
    ok("con un correo ajeno no se revela nada", "No encontramos" in c.post("/estado", data={"numero": numero, "correo": "otro@x.co"}).text)
    aux.post("/app/vacantes/estado", data={"vid": vid, "estado": "cerrada"})
    ok("al cerrarla desaparece de la página pública", codigo not in c.get("/").text)
    ok("la oferta cerrada avisa que ya no recibe postulaciones", "cerrado" in c.get(f"/empleos/{codigo}").text.lower())


ESC = {"aprobado": escenario_aprobado, "rechazado": escenario_rechazado, "falla_bot": escenario_falla_bot,
       "correo": escenario_correo, "duplicado": escenario_duplicado,
       "avisos": escenario_avisos_y_permisos, "plantillas": escenario_plantillas, "historico": escenario_historico,
       "empleos": escenario_empleos, "escalacion": escenario_escalacion}

if __name__ == "__main__":
    pedido = sys.argv[1] if len(sys.argv) > 1 else "todos"
    for nombre, fn in ESC.items():
        if pedido == nombre or (pedido == "todos" and nombre != "escalacion"):
            fn()
    bien = sum(1 for _, b in resultados if b)
    print(f"\nRESULTADO: {bien}/{len(resultados)} verificaciones correctas")
    sys.exit(0 if bien == len(resultados) else 1)
