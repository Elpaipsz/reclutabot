"""Mide la precisión de la extracción (RNF-05) contra la verdad terreno de datos_prueba/.

Uso: python scripts/evaluar_extraccion.py [n] [--desde K]
Lee GEMINI_API_KEY y GEMINI_MODEL del .env."""
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).parent.parent
for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in linea and not linea.startswith("#"):
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
sys.path.insert(0, str(RAIZ / "services" / "ai")); sys.path.insert(0, str(RAIZ / "services"))
import json
import extractor  # noqa: E402


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def comparar(esp, obt):
    """Devuelve lista de (campo, correcto)."""
    r = []
    ep, op = esp["datos_personales"], obt["datos"]["datos_personales"]
    for k in ("nombre", "correo", "telefono", "documento", "ubicacion"):
        r.append((f"personales.{k}", norm(ep[k]) == norm(op.get(k))))
    f_e, f_o = esp["formacion"][0], (obt["datos"]["formacion"] or [{}])[0]
    r.append(("formacion.titulo", norm(f_e["titulo"]) == norm(f_o.get("titulo"))))
    r.append(("formacion.nivel", norm(f_e["nivel"]) == norm(f_o.get("nivel"))))
    r.append(("formacion.anio", f_e["anio"] == f_o.get("anio")))
    r.append(("exp.cantidad", len(esp["experiencia"]) == len(obt["datos"]["experiencia"])))
    from extractor import anios_experiencia
    r.append(("exp.anios", abs(anios_experiencia(esp["experiencia"]) - obt["anios_experiencia"]) <= 0.2))
    h_e, h_o = {norm(x) for x in esp["habilidades"]}, {norm(x) for x in obt["datos"]["habilidades"]}
    r.append(("habilidades", h_e <= h_o))
    i_e = {(norm(x["idioma"]), norm(x["nivel"])) for x in esp["idiomas"]}
    i_o = {(norm(x["idioma"]), norm(x["nivel"])) for x in obt["datos"]["idiomas"]}
    r.append(("idiomas", i_e == i_o))
    return r


def una(pdf):
    esp = json.loads(pdf.with_suffix(".json").read_text(encoding="utf-8"))
    t = time.time()
    try:
        obt = extractor.extraer(pdf)
    except Exception as e:
        return pdf.name, None, str(e), time.time() - t
    return pdf.name, comparar(esp, obt), obt, time.time() - t


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8
    archivos = sorted(p for p in (RAIZ / "datos_prueba").iterdir() if p.suffix in (".pdf", ".docx"))[:n]
    tot = ok = 0
    por_campo, tiempos, tokens = {}, [], 0
    with ThreadPoolExecutor(4) as ex:
        for nombre, res, obt, seg in ex.map(una, archivos):
            if res is None:
                print(f"{nombre}: ERROR {obt}")
                continue
            c = sum(b for _, b in res)
            tot += len(res); ok += c
            tiempos.append(seg); tokens += obt["tokens"]["entrada"] + obt["tokens"]["salida"]
            fallos = [k for k, b in res if not b]
            print(f"{nombre}: {c}/{len(res)} {seg:.1f}s  fallos={fallos}")
            for k, b in res:
                a, t = por_campo.get(k, (0, 0)); por_campo[k] = (a + b, t + 1)
    print(f"\nPRECISIÓN GLOBAL: {ok}/{tot} = {100 * ok / max(tot, 1):.1f}%   (meta RNF-05: >=90%)")
    tiempos.sort()
    if tiempos:
        print(f"Tiempo p90: {tiempos[int(len(tiempos) * 0.9) - 1]:.1f}s (meta RNF-01: <=30s)  tokens totales: {tokens}")
    for k, (a, t) in sorted(por_campo.items(), key=lambda x: x[1][0] / x[1][1]):
        print(f"  {k}: {a}/{t}")


if __name__ == "__main__":
    main()
