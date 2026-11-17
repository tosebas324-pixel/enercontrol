"""CRUD de usuarios."""
from sqlalchemy.exc import IntegrityError

from core.constants import ADMIN
from core.db import execute, fetch_one, insert, run_query
from core.permissions import require
from core.security import hash_password
from core.validators import ValidationError, password_errors, validate_password, validate_usuario


def listar(actor):
    require(actor, "usuarios:ver")
    return run_query(
        "SELECT id, nombre_completo, correo, usuario, rol, estado, creado_en FROM usuarios ORDER BY id"
    )


def _duplicados(correo: str, usuario: str, excluir: int = 0) -> list:
    errs = []
    if fetch_one("SELECT id FROM usuarios WHERE correo = :c AND id <> :i", {"c": correo, "i": excluir}):
        errs.append("Ya existe un usuario con ese correo electrónico.")
    if fetch_one("SELECT id FROM usuarios WHERE usuario = :u AND id <> :i", {"u": usuario, "i": excluir}):
        errs.append("Ya existe un usuario con ese nombre de usuario.")
    return errs


def _es_ultimo_admin(uid: int) -> bool:
    row = fetch_one("SELECT rol, estado FROM usuarios WHERE id = :i", {"i": uid})
    if not row or row["rol"] != ADMIN or row["estado"] != "activo":
        return False
    otros = fetch_one(
        "SELECT COUNT(*) AS n FROM usuarios WHERE rol = :r AND estado = 'activo' AND id <> :i",
        {"r": ADMIN, "i": uid},
    )
    return int(otros["n"]) == 0


def _obtener(uid: int) -> dict:
    row = fetch_one("SELECT * FROM usuarios WHERE id = :i", {"i": uid})
    if not row:
        raise ValidationError("El usuario no existe.")
    return row


def crear(actor, data: dict, password: str, confirmacion: str) -> int:
    require(actor, "usuarios:crear")
    limpio = validate_usuario(data)
    validate_password(password)
    errs = _duplicados(limpio["correo"], limpio["usuario"])
    if password != confirmacion:
        errs.append("Las contraseñas no coinciden.")
    if errs:
        raise ValidationError(errs)
    try:
        return insert(
            """INSERT INTO usuarios (nombre_completo, correo, usuario, password_hash, rol, estado)
               VALUES (:nombre_completo, :correo, :usuario, :ph, :rol, :estado)""",
            {**limpio, "ph": hash_password(password)},
        )
    except IntegrityError:
        raise ValidationError("Usuario o correo duplicado.")


def actualizar(actor, uid: int, data: dict, nueva_password: str = "") -> None:
    require(actor, "usuarios:editar")
    _obtener(uid)
    limpio = validate_usuario(data)
    errs = _duplicados(limpio["correo"], limpio["usuario"], excluir=uid)
    if nueva_password:
        errs += password_errors(nueva_password)
    if uid == actor["id"] and (limpio["rol"] != ADMIN or limpio["estado"] != "activo"):
        errs.append("No puedes quitarte el rol de administrador ni desactivar tu propio usuario.")
    elif (limpio["rol"] != ADMIN or limpio["estado"] != "activo") and _es_ultimo_admin(uid):
        errs.append("Debe existir al menos un administrador activo.")
    if errs:
        raise ValidationError(errs)
    params = {**limpio, "i": uid}
    sql = """UPDATE usuarios SET nombre_completo=:nombre_completo, correo=:correo, usuario=:usuario,
             rol=:rol, estado=:estado"""
    if nueva_password:
        sql += ", password_hash=:ph"
        params["ph"] = hash_password(nueva_password)
    try:
        execute(sql + " WHERE id=:i", params)
    except IntegrityError:
        raise ValidationError("Usuario o correo duplicado.")


def cambiar_estado(actor, uid: int, estado: str) -> None:
    require(actor, "usuarios:desactivar")
    _obtener(uid)
    if estado == "inactivo":
        if uid == actor["id"]:
            raise ValidationError("No puedes desactivar tu propio usuario.")
        if _es_ultimo_admin(uid):
            raise ValidationError("Debe existir al menos un administrador activo.")
    execute("UPDATE usuarios SET estado = :e WHERE id = :i", {"e": estado, "i": uid})


def eliminar(actor, uid: int) -> None:
    require(actor, "usuarios:eliminar")
    _obtener(uid)
    if uid == actor["id"]:
        raise ValidationError("No puedes eliminar tu propio usuario.")
    if _es_ultimo_admin(uid):
        raise ValidationError("Debe existir al menos un administrador activo.")
    execute("DELETE FROM usuarios WHERE id = :i", {"i": uid})
