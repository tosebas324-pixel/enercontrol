"""CRUD, asociación y estado de sensores IoT.

Preparado para Iteración #2: los dispositivos reales (ESP32 vía HTTP/HTTPS o MQTT)
actualizarán `estado` y `ultima_conexion` y enviarán lecturas; hoy se simulan.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from core.db import execute, fetch_one, insert, run_query
from core.permissions import require
from core.validators import ValidationError, validate_sensor


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def listar(actor):
    require(actor, "sensores:ver")
    df = run_query(
        """SELECT s.id, s.codigo, s.tipo, s.fecha_instalacion, s.equipo_id, e.nombre AS equipo,
                  n.nombre AS negocio, s.estado, s.simulado, s.ultima_conexion
           FROM sensores s
           LEFT JOIN equipos e ON e.id = s.equipo_id
           LEFT JOIN negocios n ON n.id = e.negocio_id
           ORDER BY s.id"""
    )
    df["simulado"] = df["simulado"].astype(bool)
    return df


def _validar_equipo(equipo_id):
    if equipo_id is None:
        return
    if not fetch_one("SELECT id FROM equipos WHERE id = :i", {"i": equipo_id}):
        raise ValidationError("El equipo seleccionado no existe.")


def _codigo_existe(codigo: str, excluir: int = 0) -> bool:
    return fetch_one("SELECT id FROM sensores WHERE codigo = :c AND id <> :i", {"c": codigo, "i": excluir}) is not None


def _obtener(sid: int) -> dict:
    row = fetch_one("SELECT * FROM sensores WHERE id = :i", {"i": sid})
    if not row:
        raise ValidationError("El sensor no existe.")
    return row


def crear(actor, data: dict) -> int:
    require(actor, "sensores:crear")
    limpio = validate_sensor(data)
    _validar_equipo(limpio["equipo_id"])
    if _codigo_existe(limpio["codigo"]):
        raise ValidationError("Ya existe un sensor con ese código.")
    try:
        return insert(
            """INSERT INTO sensores (codigo, tipo, fecha_instalacion, equipo_id, estado, simulado)
               VALUES (:codigo, :tipo, :fecha_instalacion, :equipo_id, :estado, :simulado)""",
            limpio,
        )
    except IntegrityError:
        raise ValidationError("Ya existe un sensor con ese código.")


def actualizar(actor, sid: int, data: dict) -> None:
    require(actor, "sensores:editar")
    _obtener(sid)
    limpio = validate_sensor(data)
    _validar_equipo(limpio["equipo_id"])
    if _codigo_existe(limpio["codigo"], sid):
        raise ValidationError("Ya existe otro sensor con ese código.")
    execute(
        """UPDATE sensores SET codigo=:codigo, tipo=:tipo, fecha_instalacion=:fecha_instalacion,
           equipo_id=:equipo_id, estado=:estado, simulado=:simulado WHERE id=:i""",
        {**limpio, "i": sid},
    )


def eliminar(actor, sid: int) -> None:
    require(actor, "sensores:eliminar")
    _obtener(sid)
    execute("DELETE FROM sensores WHERE id = :i", {"i": sid})


def asociar(actor, sid: int, equipo_id: int) -> None:
    require(actor, "sensores:asociar")
    _obtener(sid)
    if equipo_id is None:
        raise ValidationError("Selecciona un equipo.")
    _validar_equipo(equipo_id)
    execute("UPDATE sensores SET equipo_id = :e WHERE id = :i", {"e": equipo_id, "i": sid})


def desvincular(actor, sid: int) -> None:
    require(actor, "sensores:desvincular")
    sensor = _obtener(sid)
    if sensor["equipo_id"] is None:
        raise ValidationError("El sensor ya está sin equipo asociado.")
    execute("UPDATE sensores SET equipo_id = NULL WHERE id = :i", {"i": sid})


ACCIONES_SIMULACION = {
    "conectar": "Simular conexión / latido (activo)",
    "caida": "Simular pérdida de conexión",
    "desactivar": "Desactivar sensor",
}


def simular(actor, sid: int, accion: str) -> None:
    """Solo para sensores marcados como simulados (pruebas sin hardware)."""
    require(actor, "sensores:simular")
    sensor = _obtener(sid)
    if not sensor["simulado"]:
        raise ValidationError("Solo se pueden simular sensores marcados como 'simulado'.")
    if accion == "conectar":
        execute("UPDATE sensores SET estado='activo', ultima_conexion=:t WHERE id=:i", {"t": _now(), "i": sid})
    elif accion == "caida":
        execute("UPDATE sensores SET estado='sin_conexion' WHERE id=:i", {"i": sid})
    elif accion == "desactivar":
        execute("UPDATE sensores SET estado='inactivo' WHERE id=:i", {"i": sid})
    else:
        raise ValidationError("Acción de simulación inválida.")


def refrescar_conexiones(actor, minutos: int = 10) -> int:
    """Marca 'sin_conexion' los sensores activos sin latido reciente. Devuelve cuántos cambió."""
    require(actor, "sensores:supervisar")
    if minutos < 1:
        raise ValidationError("El tiempo límite debe ser de al menos 1 minuto.")
    limite = _now() - timedelta(minutes=int(minutos))
    return execute(
        """UPDATE sensores SET estado='sin_conexion'
           WHERE estado='activo' AND ultima_conexion IS NOT NULL AND ultima_conexion < :l""",
        {"l": limite},
    )
