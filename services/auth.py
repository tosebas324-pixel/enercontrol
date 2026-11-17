"""Autenticación, primer administrador y recuperación de contraseña."""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from core import mailer
from core.constants import ADMIN
from core.db import count_users, execute, fetch_one, insert
from core.security import hash_password, verify_password
from core.validators import EMAIL_RE, ValidationError, clean, validate_password, validate_usuario

log = logging.getLogger("enercontrol.auth")
_dummy_hash = None
MAX_INTENTOS_CODIGO = 5
VIGENCIA_CODIGO_MIN = 15


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def autenticar(usuario: str, password: str):
    """Devuelve (usuario|None, mensaje)."""
    global _dummy_hash
    usuario = clean(usuario)
    if not usuario or not password:
        return None, "Ingresa usuario y contraseña."
    row = fetch_one("SELECT * FROM usuarios WHERE usuario = :u", {"u": usuario})
    if row is None:
        if _dummy_hash is None:
            _dummy_hash = hash_password("contrasena-ficticia-1")
        verify_password(password, _dummy_hash)  # iguala tiempos de respuesta
        return None, "Usuario o contraseña incorrectos."
    if not verify_password(password, row["password_hash"]):
        return None, "Usuario o contraseña incorrectos."
    if row["estado"] != "activo":
        return None, "Tu usuario está inactivo. Contacta al administrador."
    return _publico(row), "Inicio de sesión exitoso."


def _publico(row: dict) -> dict:
    return {k: row[k] for k in ("id", "nombre_completo", "correo", "usuario", "rol", "estado")}


def obtener_usuario_activo(uid: int):
    """Revalida la sesión contra la BD en cada ejecución."""
    row = fetch_one("SELECT * FROM usuarios WHERE id = :i AND estado = 'activo'", {"i": uid})
    return _publico(row) if row else None


def crear_primer_admin(data: dict, password: str) -> None:
    if count_users() > 0:
        raise ValidationError("Ya existe al menos un usuario; el registro inicial está deshabilitado.")
    data = {**data, "rol": ADMIN, "estado": "activo"}
    limpio = validate_usuario(data)
    validate_password(password)
    insert(
        """INSERT INTO usuarios (nombre_completo, correo, usuario, password_hash, rol, estado)
           VALUES (:nombre_completo, :correo, :usuario, :ph, :rol, :estado)""",
        {**limpio, "ph": hash_password(password)},
    )


def solicitar_recuperacion(correo: str) -> str:
    """Envía un código por correo. Respuesta genérica para no revelar si el correo existe."""
    if not mailer.is_configured():
        raise ValidationError("El envío de correo (SMTP) no está configurado. Contacta al administrador.")
    correo = clean(correo).lower()
    if not EMAIL_RE.match(correo):
        raise ValidationError("Ingresa un correo electrónico válido.")
    generico = "Si el correo está registrado, recibirás un código de verificación (válido 15 minutos)."
    user = fetch_one("SELECT id, nombre_completo FROM usuarios WHERE correo = :c AND estado = 'activo'", {"c": correo})
    if not user:
        return generico
    codigo = f"{secrets.randbelow(10**6):06d}"
    execute("UPDATE recuperaciones SET usado = 1 WHERE usuario_id = :i AND usado = 0", {"i": user["id"]})
    insert(
        "INSERT INTO recuperaciones (usuario_id, codigo_hash, expira_en) VALUES (:i, :h, :e)",
        {"i": user["id"], "h": hash_password(codigo), "e": _now() + timedelta(minutes=VIGENCIA_CODIGO_MIN)},
    )
    try:
        mailer.send_email(
            correo,
            "EnerControl - Código de recuperación de contraseña",
            f"Hola {user['nombre_completo']},\n\nTu código de verificación es: {codigo}\n"
            f"Vence en {VIGENCIA_CODIGO_MIN} minutos. Si no lo solicitaste, ignora este mensaje.",
        )
    except Exception as exc:  # noqa: BLE001
        log.error("No se pudo enviar el correo de recuperación: %s", exc)
    return generico


def confirmar_recuperacion(correo: str, codigo: str, nueva: str) -> None:
    validate_password(nueva)
    err = ValidationError("Código inválido o vencido.")
    user = fetch_one("SELECT id FROM usuarios WHERE correo = :c AND estado = 'activo'", {"c": clean(correo).lower()})
    if not user:
        raise err
    rec = fetch_one(
        """SELECT id, codigo_hash, intentos FROM recuperaciones
           WHERE usuario_id = :i AND usado = 0 AND expira_en > :ahora
           ORDER BY id DESC LIMIT 1""",
        {"i": user["id"], "ahora": _now()},
    )
    if not rec or rec["intentos"] >= MAX_INTENTOS_CODIGO:
        raise err
    if not verify_password(clean(codigo), rec["codigo_hash"]):
        execute("UPDATE recuperaciones SET intentos = intentos + 1 WHERE id = :i", {"i": rec["id"]})
        raise err
    execute("UPDATE usuarios SET password_hash = :h WHERE id = :i", {"h": hash_password(nueva), "i": user["id"]})
    execute("UPDATE recuperaciones SET usado = 1 WHERE id = :i", {"i": rec["id"]})
