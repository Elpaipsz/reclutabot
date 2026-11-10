"""Motor de reglas: compara datos extraídos con los requisitos de la vacante (RF-13, RF-14, RF-15)."""
import re
import unicodedata

NIVELES = {"bachiller": 1, "tecnico": 2, "tecnologo": 3, "profesional": 4, "especializacion": 5,
           "maestria": 6, "doctorado": 7, "otro": 0}
CEFR = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}
PESOS_DEFECTO = {"experiencia": 0.35, "formacion": 0.25, "habilidades": 0.30, "idioma": 0.10}
OBLIGATORIOS_DEFECTO = ["experiencia", "formacion", "habilidades"]
UMBRAL_CUMPLE, UMBRAL_NO_CUMPLE = 70, 40


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9+#.]+", " ", s).strip()


def rango_nivel(n) -> int:
    return NIVELES.get(norm(n), 0)


def _tiene(skills_norm: list[str], req: str) -> bool:
    r = norm(req)
    return any(r == s or r in s or s in r for s in skills_norm if s)


def _cefr(nivel) -> int:
    m = re.search(r"\b([abc][12])\b", norm(nivel))
    return CEFR.get(m.group(1), 0) if m else 0


def evaluar(datos: dict, anios: float, requisitos: dict, pesos: dict | None = None) -> dict:
    """Devuelve {puntaje 0-100, clasificacion, criterios{...}}."""
    pesos = {**PESOS_DEFECTO, **(pesos or {})}
    obligatorios = requisitos.get("obligatorios", OBLIGATORIOS_DEFECTO)
    crit = {}

    # experiencia
    req = float(requisitos.get("anios_experiencia") or 0)
    crit["experiencia"] = {"puntos": 1.0 if req <= 0 else min(anios / req, 1.0), "cumple": anios >= req,
                           "detalle": f"{anios} años (requerido {req})"}

    # formación
    req_n = requisitos.get("formacion_minima")
    mejor = max((rango_nivel(f.get("nivel")) for f in datos.get("formacion", [])), default=0)
    rr = rango_nivel(req_n)
    crit["formacion"] = {"puntos": 1.0 if rr == 0 else min(mejor / rr, 1.0), "cumple": mejor >= rr,
                         "detalle": f"nivel {mejor} (requerido: {req_n or 'ninguno'})"}

    # habilidades
    skills = [norm(s) for s in datos.get("habilidades", [])]
    oblig = requisitos.get("habilidades_obligatorias", [])
    deseables = requisitos.get("habilidades_deseables", [])
    todas = oblig + deseables
    faltan = [h for h in oblig if not _tiene(skills, h)]
    ok_t = [h for h in todas if _tiene(skills, h)]
    crit["habilidades"] = {"puntos": 1.0 if not todas else len(ok_t) / len(todas), "cumple": not faltan,
                           "detalle": f"faltan obligatorias: {faltan}" if faltan else "obligatorias cubiertas"}

    # idiomas
    reqs_i = requisitos.get("idiomas", [])
    pts, cumple_i = [], True
    for ri in reqs_i:
        cand = [i for i in datos.get("idiomas", []) if norm(i.get("idioma")) == norm(ri.get("idioma"))]
        if not cand:
            pts.append(0.0); cumple_i = False
        elif _cefr(cand[0].get("nivel")) >= _cefr(ri.get("nivel")):
            pts.append(1.0)
        else:
            pts.append(0.5); cumple_i = False
    crit["idioma"] = {"puntos": sum(pts) / len(pts) if pts else 1.0, "cumple": cumple_i,
                      "detalle": "sin requisito" if not reqs_i else f"{len(reqs_i)} idioma(s) requerido(s)"}

    total_w = sum(pesos.values()) or 1
    puntaje = round(100 * sum(pesos[k] * crit[k]["puntos"] for k in crit) / total_w, 1)
    incumple = [k for k in obligatorios if k in crit and not crit[k]["cumple"]]
    if not incumple and puntaje >= UMBRAL_CUMPLE:
        clasif = "Cumple"
    elif puntaje < UMBRAL_NO_CUMPLE or (incumple and puntaje < 55):
        clasif = "No cumple"
    else:
        clasif = "Revisar"
    return {"puntaje": puntaje, "clasificacion": clasif, "criterios": crit, "incumple": incumple}
