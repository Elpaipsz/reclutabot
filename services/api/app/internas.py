"""API interna usada por los workers (IA, RPA). Protegida con X-Internal-Token."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import secrets

from . import db, servicios
from .config import PORTAL_URL
from .auth import interno

router = APIRouter(prefix="/internal", dependencies=[Depends(interno)], include_in_schema=False)


class Estado(BaseModel):
    estado: str
    actor: str = "sistema"


class Extraccion(BaseModel):
    datos: dict
    confianza: dict
    resumen: str = ""
    anios_experiencia: float = 0
    costo_usd: float = 0
    detalle: dict = {}


class Incidencia(BaseModel):
    origen: str
    detalle: str
    captura_path: str | None = None


class RrhhId(BaseModel):
    rrhh_id: str


def _post(pid):
    p = db.q1("SELECT * FROM postulacion WHERE id=%s", (pid,))
    if not p:
        raise HTTPException(404, "Postulación no existe")
    return p


@router.get("/postulaciones/{pid}")
def obtener(pid: int):
    return _post(pid)


@router.post("/postulaciones/{pid}/estado")
def estado(pid: int, b: Estado):
    _post(pid)
    servicios.set_estado(pid, b.estado, b.actor)
    return {"ok": True}


@router.post("/postulaciones/{pid}/extraccion")
def extraccion(pid: int, b: Extraccion):
    _post(pid)
    db.ex("""INSERT INTO extraccion(postulacion_id,datos,confianza,resumen,anios_experiencia,costo_usd)
             VALUES (%s,%s,%s,%s,%s,%s)""",
          (pid, db.J(b.datos), db.J(b.confianza), b.resumen, b.anios_experiencia, b.costo_usd))
    servicios.evento(pid, "ia", "extraccion", "ok", {**b.detalle, "costo_usd": b.costo_usd})
    return {"ok": True}


@router.post("/postulaciones/{pid}/incidencia")
def incidencia(pid: int, b: Incidencia):
    _post(pid)
    servicios.incidencia(pid, b.origen, b.detalle, b.captura_path)
    return {"ok": True}


@router.get("/postulaciones/{pid}/payload")
def payload(pid: int):
    """Datos validados + candidato + archivo, para que el RPA registre al candidato."""
    p = _post(pid)
    e = servicios.datos_vigentes(pid)
    c = db.q1("SELECT * FROM candidato WHERE id=%s", (p["candidato_id"],))
    v = db.q1("SELECT codigo,titulo,descripcion,requisitos FROM vacante WHERE id=%s", (p["vacante_id"],))
    datos = (e["datos_validados"] or e["datos"]) if e else {}
    return {"postulacion": {"id": pid, "numero": p["numero"], "rrhh_id": p["rrhh_id"], "archivo_path": p["archivo_path"]},
            "candidato": {"nombre": c["nombre"], "correo": c["correo"], "telefono": c["telefono"]},
            "vacante": v, "datos": datos, "anios_experiencia": float(e["anios_experiencia"] or 0) if e else 0,
            "puntaje": float(p["puntaje"] or 0), "resumen": (e["resumen"] if e else "")}


@router.post("/postulaciones/{pid}/rrhh-id")
def rrhh_id(pid: int, b: RrhhId):
    _post(pid)
    db.ex("UPDATE postulacion SET rrhh_id=%s, actualizada_en=now() WHERE id=%s", (b.rrhh_id, pid))
    servicios.evento(pid, "rpa", "registro_rrhh", "ok", {"rrhh_id": b.rrhh_id})
    return {"ok": True}
