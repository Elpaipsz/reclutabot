"""Genera docs/presentacion/presentacion.html: un solo archivo con imágenes y tipografías incrustadas."""
import base64, re
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent.parent
FUENTES = RAIZ / "services" / "api" / "app" / "static" / "fonts"


def b64(p: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


s = (AQUI / "plantilla.html").read_text(encoding="utf-8")
for clave, f in {"BRICOLAGE_REGULAR": "BricolageGrotesque-Regular.ttf", "BRICOLAGE_BOLD": "BricolageGrotesque-Bold.ttf",
                 "INSTRUMENT_REGULAR": "InstrumentSans-Regular.ttf", "INSTRUMENT_BOLD": "InstrumentSans-Bold.ttf"}.items():
    s = s.replace(f"%%FONT_{clave}%%", b64(FUENTES / f, "font/ttf"))
for img in re.findall(r"%%IMG_(\w+)%%", s):
    s = s.replace(f"%%IMG_{img}%%", b64(AQUI / "img" / f"{img}.png", "image/png"))

# flujo de caja acumulado del caso de negocio (meses 0 a 12)
acum = [-2696000, -6740000, -6090668, -5441335, -4792003, -4142671, -3493339, -2844006, -2194674, -1545342, -896009, -246677, 402655]
pts = [(60 + 680 * k / 12, 60 - v * 240 / 6740000) for k, v in enumerate(acum)]
s = s.replace("%%CASHFLOW%%", " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)).replace("%%CF_END_Y%%", f"{pts[-1][1]:.1f}")
assert "%%" not in s
(AQUI / "presentacion.html").write_text(s, encoding="utf-8")
print("presentacion.html", round(len(s) / 1e6, 2), "MB")
