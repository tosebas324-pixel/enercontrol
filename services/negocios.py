"""CRUD de negocios."""
from sqlalchemy.exc import IntegrityError

from core.db import execute, fetch_one, insert, run_query
from core.permissions import require
from core.validators import ValidationError, validate_negocio


def listar(actor):
    require(actor, "negocios:ver")
    df = run_query(
        """SELECT n.id, n.nombre, n.tipo, n.direccion, n.tarifa_kwh, n.responsable, n.estado,
                  (SELECT COUNT(*) FROM equipos e WHERE e.negocio_id = n.id) AS equipos
           FROM negocios n ORDER BY n.id"""
    )
    df["tarifa_kwh"] = df["tarifa_kwh"].astype(float)
    return df


def _existe_nombre(nombre: str, excluir: int = 0) -> bool:
    return fetch_one("SELECT id FROM negocios WHERE nombre = :n AND id <> :i", {"n": nombre, "i": excluir}) is not None


def crear(actor, data: dict) -> int:
    require(actor, "negocios:crear")
    limpio = validate_negocio(data)
    if _existe_nombre(limpio["nombre"]):
        raise ValidationError("Ya existe un negocio con ese nombre.")
    try:
        return insert(
            """INSERT INTO negocios (nombre, tipo, direccion, tarifa_kwh, responsable, estado)
               VALUES (:nombre, :tipo, :direccion, :tarifa_kwh, :responsable, :estado)""",
            limpio,
        )
    except IntegrityError:
        raise ValidationError("Ya existe un negocio con ese nombre.")


def actualizar(actor, nid: int, data: dict) -> None:
    require(actor, "negocios:editar")
    if not fetch_one("SELECT id FROM negocios WHERE id = :i", {"i": nid}):
        raise ValidationError("El negocio no existe.")
    limpio = validate_negocio(data)
    if _existe_nombre(limpio["nombre"], nid):
        raise ValidationError("Ya existe otro negocio con ese nombre.")
    execute(
        """UPDATE negocios SET nombre=:nombre, tipo=:tipo, direccion=:direccion, tarifa_kwh=:tarifa_kwh,
           responsable=:responsable, estado=:estado WHERE id=:i""",
        {**limpio, "i": nid},
    )


def eliminar(actor, nid: int) -> None:
    require(actor, "negocios:eliminar")
    row = fetch_one("SELECT COUNT(*) AS n FROM equipos WHERE negocio_id = :i", {"i": nid})
    if int(row["n"]) > 0:
        raise ValidationError(
            f"El negocio tiene {row['n']} equipo(s) asociado(s). Elimina o reasigna los equipos primero, "
            "o cambia el estado del negocio a inactivo."
        )
    try:
        execute("DELETE FROM negocios WHERE id = :i", {"i": nid})
    except IntegrityError:
        raise ValidationError("No se puede eliminar: el negocio tiene registros relacionados.")
