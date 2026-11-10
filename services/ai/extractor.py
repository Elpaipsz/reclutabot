"""Extracción de datos de hojas de vida con Gemini."""
import base64
import json
import logging
import os
import re
import threading
import time
from datetime import date
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from common.experiencia import anios_experiencia  # noqa: E402

log = logging.getLogger("extractor")

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODELOS = [m.strip() for m in os.getenv(
    "GEMINI_MODELS", os.getenv("GEMINI_MODEL", "gemini-3.5-flash") + ",gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-3.7-flash,gemini-3.8-flash,gemma-4-26b-a4b-it"
).split(",") if m.strip()]
PROMPT = (Path(__file__).parent / "prompts" / "extraccion.txt").read_text(encoding="utf-8")
MAX_REINTENTOS_ESQUEMA = 2   # RF-11
TIMEOUT = 40                 # RNF-07 (por modelo; hay cadena de respaldo)
_LIMITE = threading.Semaphore(int(os.getenv("GEMINI_CONCURRENCIA", "3")))  # llamadas simultáneas


class Personales(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None
    documento: Optional[str] = None
    ubicacion: Optional[str] = None

    @field_validator("telefono", "documento", mode="before")
    @classmethod
    def _a_texto(cls, v):
        return None if v is None else str(v)


class Formacion(BaseModel):
    titulo: str
    institucion: Optional[str] = None
    anio: Optional[int] = None
    nivel: str = "Otro"


class Experiencia(BaseModel):
    cargo: str
    empresa: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    funciones: Optional[str] = None


class Idioma(BaseModel):
    idioma: str
    nivel: Optional[str] = None


class CV(BaseModel):
    datos_personales: Personales
    formacion: list[Formacion] = []
    experiencia: list[Experiencia] = []
    habilidades: list[str] = []
    idiomas: list[Idioma] = []
    certificaciones: list[str] = []
    resumen: str = ""
    relleno_palabras_clave: bool = False
    confianza: dict[str, float] = Field(default_factory=dict)


# ---------- texto desde archivo ----------

def texto_pdf(path: Path) -> str:
    from pypdf import PdfReader
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages).strip()
    except Exception as e:
        log.warning("pypdf falló: %s", e)
        return ""


def texto_docx(path: Path) -> str:
    import docx
    d = docx.Document(str(path))
    partes = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            partes.append(" | ".join(c.text for c in row.cells))
    return "\n".join(partes).strip()


# ---------- Gemini ----------

_AGOTADOS: dict[str, float] = {}   # modelo -> instante hasta el que se omite (cuota diaria agotada)
_lock = threading.Lock()


def _llamar_gemini(partes: list[dict]) -> tuple[str, dict, str]:
    """Llama a Gemini con cadena de modelos de respaldo y reintentos (RNF-07).

    Si un modelo agota su cuota diaria se omite durante 6 h; si está saturado (5xx/timeout) se
    pasa al siguiente. Devuelve (texto, usage, modelo_usado)."""
    ultimo = None
    for ronda in range(3):                         # rondas completas con espera exponencial
        usados = 0
        for modelo in MODELOS:
            with _lock:
                if _AGOTADOS.get(modelo, 0) > time.time():
                    continue
            usados += 1
            # Gemma no admite modo JSON: se omite y se confía en el parser tolerante
            gen = {"temperature": 0.1} if modelo.startswith("gemma") else {"responseMimeType": "application/json", "temperature": 0.1}
            body = {"contents": [{"parts": partes}], "generationConfig": gen}
            try:
                with _LIMITE:
                    r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                                   headers={"x-goog-api-key": API_KEY}, json=body, timeout=TIMEOUT)
                if r.status_code == 429:
                    if "PerDay" in r.text:
                        with _lock:
                            _AGOTADOS[modelo] = time.time() + 6 * 3600
                        log.warning("modelo %s sin cuota diaria; se usa el siguiente", modelo)
                    raise RuntimeError(f"{modelo}: HTTP 429")
                if r.status_code >= 500:
                    raise RuntimeError(f"{modelo}: HTTP {r.status_code}")
                r.raise_for_status()
                data = r.json()
                txt = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"] if not p.get("thought"))
                return txt, data.get("usageMetadata", {}), modelo
            except Exception as e:
                ultimo = e
                log.warning("Gemini falló con %s: %s", modelo, e)
                with _lock:   # pausa breve para no volver a tropezar con un modelo saturado o lento
                    _AGOTADOS[modelo] = max(_AGOTADOS.get(modelo, 0), time.time() + 90)
        if usados == 0:
            # todos en pausa: si alguno se libera pronto (fallo transitorio) se espera; si es cuota diaria, se rinde
            with _lock:
                libre_en = min((_AGOTADOS[m] - time.time() for m in MODELOS if m in _AGOTADOS), default=0)
            if 0 < libre_en <= 45:
                time.sleep(libre_en + 0.5)
                continue
            break
        time.sleep((3, 10, 20)[ronda])
    raise RuntimeError(f"Gemini no disponible en ningún modelo: {ultimo}")


def _json(txt: str) -> dict:
    txt = txt.strip()
    txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
    if not txt.startswith("{"):
        i, j = txt.find("{"), txt.rfind("}")
        if i >= 0 and j > i:
            txt = txt[i:j + 1]
    return json.loads(txt)


def extraer(path: str | Path) -> dict:
    """Devuelve {datos, confianza, resumen, anios_experiencia, tokens, modelo}."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".docx":
        texto = texto_docx(path)
        partes = [{"text": PROMPT + "\n\nTEXTO DE LA HOJA DE VIDA:\n" + texto}]
    elif ext == ".pdf":
        texto = texto_pdf(path)
        if len(texto) >= 200:
            partes = [{"text": PROMPT + "\n\nTEXTO DE LA HOJA DE VIDA:\n" + texto}]
        else:  # PDF escaneado: Gemini hace OCR leyendo el PDF directamente (RF-07)
            log.info("PDF con poco texto (%d car.), se envía como imagen a Gemini", len(texto))
            b64 = base64.b64encode(path.read_bytes()).decode()
            partes = [{"text": PROMPT}, {"inline_data": {"mime_type": "application/pdf", "data": b64}}]
    else:
        raise ValueError(f"Formato no soportado: {ext}")

    tokens = {"entrada": 0, "salida": 0}
    error = None
    for intento in range(1 + MAX_REINTENTOS_ESQUEMA):
        extra = [] if error is None else [{"text": f"\nTu respuesta anterior fue inválida ({error}). Corrígela y devuelve solo el JSON."}]
        txt, usage, modelo = _llamar_gemini(partes + extra)
        tokens["entrada"] += usage.get("promptTokenCount", 0)
        tokens["salida"] += usage.get("candidatesTokenCount", 0)
        try:
            cv = CV.model_validate(_json(txt))
            break
        except (json.JSONDecodeError, ValidationError) as e:
            error = str(e)[:300]
            log.warning("Esquema inválido (intento %d): %s", intento + 1, error)
    else:
        raise RuntimeError(f"La IA no devolvió un JSON válido tras reintentos: {error}")

    datos = cv.model_dump()
    resumen = datos.pop("resumen")
    confianza = datos.pop("confianza")
    return {"datos": datos, "confianza": confianza, "resumen": resumen,
            "anios_experiencia": anios_experiencia(cv.experiencia), "tokens": tokens, "modelo": modelo}
