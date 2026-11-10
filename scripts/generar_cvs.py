"""Genera hojas de vida sintéticas (PDF en 3 layouts, uno escaneado, y DOCX) con su verdad terreno.

Uso: python scripts/generar_cvs.py [cantidad] [carpeta_salida]
Dependencias locales: reportlab pillow python-docx
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import docx

random.seed(7)
NOMBRES = ["Camila", "Juan", "Valentina", "Santiago", "Laura", "Andrés", "Daniela", "Sebastián", "María", "Felipe",
           "Isabella", "Mateo", "Sofía", "Nicolás", "Paula", "Daniel"]
APELLIDOS = ["Gómez", "Rodríguez", "Martínez", "López", "Hernández", "García", "Ramírez", "Torres", "Díaz", "Vargas",
             "Castro", "Ortiz", "Rojas", "Moreno", "Jiménez", "Álvarez"]
CIUDADES = ["Medellín", "Bogotá", "Cali", "Barranquilla", "Bucaramanga", "Pereira"]
CARGOS = ["Desarrollador Backend", "Desarrollador Full Stack", "Analista de Datos", "Ingeniero de Software",
          "Analista de Sistemas", "Desarrollador Python", "Ingeniero DevOps"]
EMPRESAS = ["Bancolombia", "Rappi", "Globant", "Mercado Libre", "Sofka", "Endava", "Grupo Éxito", "Bancamía",
            "Pragma", "Nubank", "TCS", "Accenture"]
HAB = ["Python", "FastAPI", "Django", "SQL", "PostgreSQL", "Docker", "Git", "JavaScript", "React", "AWS",
       "Linux", "Power BI", "Excel", "Scrum", "Java", "Kubernetes"]
TITULOS = {"Técnico": "Técnico en Sistemas", "Tecnólogo": "Tecnólogo en Desarrollo de Software",
           "Profesional": "Ingeniería de Sistemas", "Especialización": "Especialización en Analítica de Datos",
           "Maestría": "Maestría en Ingeniería"}
UNIS = ["Universidad de Antioquia", "Universidad Nacional", "EAFIT", "SENA", "Universidad del Valle", "UPB"]
IDIOMAS = [("Inglés", n) for n in ["A2", "B1", "B2", "C1"]]


def mes(y, m):
    return f"{y}-{m:02d}"


def crear_candidato(i):
    nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
    nivel = random.choices(list(TITULOS), weights=[1, 2, 6, 2, 1])[0]
    anio_grado = random.randint(2012, 2024)
    exp, y = [], random.randint(2013, 2021)
    for _ in range(random.randint(0, 3)):
        dur = random.randint(1, 3)
        ini_m, fin_m = random.randint(1, 12), random.randint(1, 12)
        fin = y + dur
        if fin > 2026:
            break
        exp.append({"cargo": random.choice(CARGOS), "empresa": random.choice(EMPRESAS),
                    "fecha_inicio": mes(y, ini_m), "fecha_fin": mes(fin, fin_m),
                    "funciones": "Desarrollo y mantenimiento de servicios, trabajo con equipos ágiles."})
        y = fin + 1
    if exp and random.random() < 0.3:
        exp[-1]["fecha_fin"] = "actual"
    nombre_ascii = nombre.lower().replace(" ", ".").translate(str.maketrans("áéíóúñ", "aeioun"))
    return {
        "datos_personales": {"nombre": nombre, "correo": f"{nombre_ascii}{i}@correo.com",
                             "telefono": f"3{random.randint(0, 2)}{random.randint(10000000, 99999999)}",
                             "documento": str(random.randint(1000000000, 1199999999)),
                             "ubicacion": random.choice(CIUDADES)},
        "formacion": [{"titulo": TITULOS[nivel], "institucion": random.choice(UNIS), "anio": anio_grado, "nivel": nivel}],
        "experiencia": exp,
        "habilidades": random.sample(HAB, random.randint(3, 8)),
        "idiomas": [{"idioma": a, "nivel": b} for a, b in [random.choice(IDIOMAS)]] if random.random() < 0.8 else [],
        "certificaciones": random.sample(["AWS Cloud Practitioner", "Scrum Master", "Azure Fundamentals"], random.randint(0, 2)),
    }


def lineas(c):
    p = c["datos_personales"]
    L = [("h1", p["nombre"]), ("p", f"Correo: {p['correo']}   Tel: {p['telefono']}"),
         ("p", f"Documento: {p['documento']}   Ciudad: {p['ubicacion']}"), ("h2", "Formación académica")]
    for f in c["formacion"]:
        L.append(("p", f"{f['titulo']} - {f['institucion']} ({f['anio']})"))
    L.append(("h2", "Experiencia laboral"))
    for e in c["experiencia"] or []:
        fin = "Actualidad" if e["fecha_fin"] == "actual" else e["fecha_fin"]
        L.append(("p", f"<b>{e['cargo']}</b> - {e['empresa']} ({e['fecha_inicio']} a {fin})"))
        L.append(("p", e["funciones"]))
    if not c["experiencia"]:
        L.append(("p", "Sin experiencia laboral formal."))
    L += [("h2", "Habilidades"), ("p", ", ".join(c["habilidades"]))]
    if c["idiomas"]:
        L += [("h2", "Idiomas"), ("p", ", ".join(f"{i['idioma']} {i['nivel']}" for i in c["idiomas"]))]
    if c["certificaciones"]:
        L += [("h2", "Certificaciones"), ("p", ", ".join(c["certificaciones"]))]
    return L


def pdf_simple(c, path):
    st = getSampleStyleSheet()
    estilos = {"h1": st["Title"], "h2": st["Heading2"], "p": st["BodyText"]}
    SimpleDocTemplate(str(path), pagesize=A4).build([Paragraph(t, estilos[k]) for k, t in lineas(c)])


def pdf_dos_columnas(c, path):
    st = getSampleStyleSheet()
    L = lineas(c)
    izq = [Paragraph(t, st["Heading3"] if k != "p" else st["BodyText"]) for k, t in L[:4] + L[-4:]]
    der = [Paragraph(t, st["Heading3"] if k != "p" else st["BodyText"]) for k, t in L[4:-4]]
    t = Table([[izq, der]], colWidths=[170, 330])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    SimpleDocTemplate(str(path), pagesize=A4).build([Paragraph(c["datos_personales"]["nombre"], st["Title"]), Spacer(1, 8), t])


def pdf_escaneado(c, path):
    """PDF solo imagen (sin capa de texto) para forzar el OCR vía Gemini."""
    img = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(img)
    try:
        f1, f2 = ImageFont.truetype("arial.ttf", 34), ImageFont.truetype("arial.ttf", 26)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    y = 80
    for k, t in lineas(c):
        t = t.replace("<b>", "").replace("</b>", "")
        d.text((80, y), t, fill=(30, 30, 30), font=f1 if k in ("h1", "h2") else f2)
        y += 60 if k in ("h1", "h2") else 42
    img = img.rotate(0.6, fillcolor="white")
    img.save(path, "PDF", resolution=150)


def cv_docx(c, path):
    d = docx.Document()
    for k, t in lineas(c):
        t = t.replace("<b>", "").replace("</b>", "")
        d.add_heading(t, 1 if k == "h1" else 2) if k != "p" else d.add_paragraph(t)
    d.save(str(path))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent.parent / "datos_prueba"
    out.mkdir(parents=True, exist_ok=True)
    formatos = [("simple", pdf_simple, "pdf"), ("columnas", pdf_dos_columnas, "pdf"),
                ("escaneado", pdf_escaneado, "pdf"), ("docx", cv_docx, "docx")]
    for i in range(1, n + 1):
        c = crear_candidato(i)
        nombre, fn, ext = formatos[(i - 1) % len(formatos)] if i > 4 else formatos[(i - 1) % 4]
        base = out / f"cv_{i:03d}_{nombre}"
        fn(c, base.with_suffix("." + ext))
        base.with_suffix(".json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{n} hojas de vida generadas en {out}")


if __name__ == "__main__":
    main()
