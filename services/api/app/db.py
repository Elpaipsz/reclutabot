import json
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from .config import DATABASE_URL

pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, kwargs={"row_factory": dict_row}, open=False)


MIGRACIONES = [
    "ALTER TABLE vacante ADD COLUMN IF NOT EXISTS area TEXT, ADD COLUMN IF NOT EXISTS ubicacion TEXT, "
    "ADD COLUMN IF NOT EXISTS modalidad TEXT, ADD COLUMN IF NOT EXISTS contrato TEXT, ADD COLUMN IF NOT EXISTS salario TEXT, "
    "ADD COLUMN IF NOT EXISTS responsabilidades TEXT, ADD COLUMN IF NOT EXISTS ofrecemos TEXT",
]


def init():
    pool.open(wait=True, timeout=30)
    with pool.connection() as c:          # migraciones idempotentes: una base ya creada recibe las columnas nuevas
        for m in MIGRACIONES:
            c.execute(m)


def J(v):
    """Envuelve un valor Python para columnas JSONB."""
    return Jsonb(v, dumps=lambda o: json.dumps(o, ensure_ascii=False, default=str))


def q(sql, params=None):
    with pool.connection() as c:
        return c.execute(sql, params or ()).fetchall()


def q1(sql, params=None):
    rows = q(sql, params)
    return rows[0] if rows else None


def ex(sql, params=None):
    """Ejecuta y devuelve la primera fila (útil con RETURNING)."""
    with pool.connection() as c:
        cur = c.execute(sql, params or ())
        return cur.fetchone() if cur.description else None


@contextmanager
def tx():
    with pool.connection() as c:
        yield c
