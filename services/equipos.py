"""CRUD de equipos eléctricos."""
from sqlalchemy.exc import IntegrityError

from core.db import execute, fetch_one, insert, run_query
from core.permissions import require
from core.validators import ValidationError, validate_equipo


def listar(actor):
    require(actor, "equipos:ver")
    df = run_query(
        """SELECT e.id, e.nombre, e.tipo, e.ubicacion, e.potencia_w, e.negocio_id, n.nombre AS negocio, e.estado,
                  (SELECT COUNT(*) FROM sensores s WHERE s.equipo_id = e.id) AS sensores
           FROM equipos e JOIN negocios n ON n.id = e.negocio_id ORDER BY e.id"""
    )
    df["potencia_w"] = df["potencia_w"].astype(float)
    return df


def _validar_relaciones(limpio: dict, excluir: int = 0) -> None:
    if not fetch_one("SELECT id FROM negocios WHERE id = :i", {"i": limpio["negocio_id"]}):
        raise ValidationError("El negocio seleccionado no existe.")
    if fetch_one(
        "SELECT id FROM equipos WHERE negocio_id = :n AND nombre = :nom AND id <> :i",
        {"n": limpio["negocio_id"], "nom": limpio["nombre"], "i": excluir},
    ):
        raise ValidationError("Ya existe un equipo con ese nombre en el negocio seleccionado.")


def crear(actor, data: dict) -> int:
    require(actor, "equipos:crear")
    limpio = validate_equipo(data)
    _validar_relaciones(limpio)
    try:
        return insert(
            """INSERT INTO equipos (nombre, tipo, ubicacion, potencia_w, negocio_id, estado)
               VALUES (:nombre, :tipo, :ubicacion, :potencia_w, :negocio_id, :estado)""",
            limpio,
        )
    except IntegrityError:
        raise ValidationError("No se pudo registrar el equipo (dato duplicado o negocio inválido).")


def actualizar(actor, eid: int, data: dict) -> None:
    require(actor, "equipos:editar")
    if not fetch_one("SELECT id FROM equipos WHERE id = :i", {"i": eid}):
        raise ValidationError("El equipo no existe.")
    limpio = validate_equipo(data)
    _validar_relaciones(limpio, eid)
    execute(
        """UPDATE equipos SET nombre=:nombre, tipo=:tipo, ubicacion=:ubicacion, potencia_w=:potencia_w,
           negocio_id=:negocio_id, estado=:estado WHERE id=:i""",
        {**limpio, "i": eid},
    )


def eliminar(actor, eid: int) -> None:
    """Los sensores del equipo quedan sin vincular (ON DELETE SET NULL)."""
    require(actor, "equipos:eliminar")
    if not fetch_one("SELECT id FROM equipos WHERE id = :i", {"i": eid}):
        raise ValidationError("El equipo no existe.")
    execute("DELETE FROM equipos WHERE id = :i", {"i": eid})
