import time

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from . import db
from .config import INTERNAL_TOKEN, JWT_SECRET, SEED_PASSWORD

ROLES = ("auxiliar", "analista", "coordinador", "admin")
# Grupos candidatos de Flowable que puede ver cada rol
GRUPOS = {"auxiliar": ["auxiliar"], "analista": ["analista"], "coordinador": ["coordinador"],
          "admin": ["auxiliar", "analista", "coordinador"]}


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def check_pw(pw: str, h: str) -> bool:
    return bcrypt.checkpw(pw.encode(), h.encode())


def crear_token(u: dict) -> str:
    return jwt.encode({"sub": str(u["id"]), "rol": u["rol"], "exp": int(time.time()) + 8 * 3600}, JWT_SECRET, "HS256")


def seed_usuarios():
    """Usuarios de demostración (uno por rol) si la tabla está vacía."""
    if db.q1("SELECT 1 FROM usuario LIMIT 1"):
        return
    for nombre, correo, rol in [("Auxiliar RR.HH.", "auxiliar@empresa.test", "auxiliar"),
                                ("Analista de Selección", "analista@empresa.test", "analista"),
                                ("Coordinador de Selección", "coordinador@empresa.test", "coordinador"),
                                ("Administrador", "admin@empresa.test", "admin")]:
        db.ex("INSERT INTO usuario(nombre,correo,password_hash,rol) VALUES (%s,%s,%s,%s)",
              (nombre, correo, hash_pw(SEED_PASSWORD), rol))


def usuario_actual(request: Request) -> dict:
    tok = request.cookies.get("token") or request.headers.get("Authorization", "").removeprefix("Bearer ")
    try:
        data = jwt.decode(tok, JWT_SECRET, ["HS256"])
    except Exception:
        raise HTTPException(401, "No autenticado")
    u = db.q1("SELECT id,nombre,correo,rol FROM usuario WHERE id=%s", (int(data["sub"]),))
    if not u:
        raise HTTPException(401, "Usuario no existe")
    return u


def requiere(*roles):
    """Dependencia: exige sesión y uno de los roles (admin siempre pasa)."""
    def dep(u: dict = Depends(usuario_actual)):
        if u["rol"] != "admin" and u["rol"] not in roles:
            raise HTTPException(403, "No tienes permiso para esta acción")
        return u
    return dep


def interno(request: Request):
    if request.headers.get("X-Internal-Token") != INTERNAL_TOKEN:
        raise HTTPException(403, "Token interno inválido")
