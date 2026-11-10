"""Prueba de carga (RNF-03, RNF-04): envía N postulaciones con P en paralelo y mide el tiempo de ciclo automático.

El tiempo de ciclo automático es el que va desde la recepción hasta que la postulación queda lista para
una persona (tarea de validación) o ya registrada por el robot; no cuenta la espera humana (RNF-03).

Uso: python scripts/carga.py [N=20] [paralelo=5]
"""
import concurrent.futures as cf
import json
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).parent.parent
BASE = "http://localhost:8000"
LISTAS = {"En validación", "Registrada", "Error", "Rechazada", "Duplicada", "En entrevista", "Descartada"}


def una(args):
    i, pdf = args
    c = httpx.Client(base_url=BASE, follow_redirects=True, timeout=120)
    contenido = pdf.read_bytes() + f"\n%%carga-{time.time_ns()}\n".encode()
    t0 = time.time()
    r = c.post("/postular", data={"vacante_id": 2, "nombre": f"Carga {i}", "correo": f"carga.{int(t0)}.{i}@prueba.com",
                                  "telefono": "3000000000", "acepta": "1"}, files={"cv": (pdf.name, contenido, "application/pdf")})
    numero = re.search(r"POST-\d{4}-\d{6}", r.text).group(0)
    admin = httpx.Client(base_url=BASE, follow_redirects=True, timeout=60)
    admin.post("/login", data={"correo": "admin@empresa.test", "password": "demo1234"})
    while time.time() - t0 < 600:
        h = BeautifulSoup(admin.get("/app/postulaciones", params={"q": numero}).text, "html.parser")
        badges = h.select("tr td span.badge")
        badge = badges[-1] if badges else None   # la última etiqueta de la fila es el estado
        estado = badge.get_text(strip=True) if badge else "?"
        if estado in LISTAS:
            return numero, estado, time.time() - t0
        time.sleep(2)
    return numero, "TIMEOUT", time.time() - t0


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    par = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    pdfs = [p for p in sorted((RAIZ / "datos_prueba").glob("*.pdf")) if "escaneado" not in p.name]
    trabajos = [(i, pdfs[i % len(pdfs)]) for i in range(n)]
    t0 = time.time()
    with cf.ThreadPoolExecutor(par) as ex:
        res = list(ex.map(una, trabajos))
    total = time.time() - t0
    tiempos = sorted(r[2] for r in res)
    por_estado = {}
    for _, e, _ in res:
        por_estado[e] = por_estado.get(e, 0) + 1
    print(f"{n} postulaciones, {par} en paralelo, duración total {total:.0f}s ({total / n:.1f}s por postulación)")
    print("Estados:", por_estado)
    print(f"Tiempo de ciclo automático: promedio {sum(tiempos) / n:.0f}s · mediana {tiempos[n // 2]:.0f}s · "
          f"p90 {tiempos[int(n * 0.9) - 1]:.0f}s · máx {tiempos[-1]:.0f}s   (meta RNF-03: ≤ 300s)")
    print("Sin estado final:", sum(1 for r in res if r[1] == "TIMEOUT"), "(meta RNF-06: 0)")


if __name__ == "__main__":
    main()
