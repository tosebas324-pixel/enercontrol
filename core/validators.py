"""Validaciones de entrada (funciones puras, sin acceso a BD)."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from core.constants import ESTADOS_GENERALES, ESTADOS_SENSOR, ROLES


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(self.errors))


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
USER_RE = re.compile(r"^[A-Za-z0-9_.-]{4,40}$")
CODIGO_RE = re.compile(r"^[A-Za-z0-9_-]{3,40}$")


def clean(value) -> str:
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def password_errors(password: str) -> list:
    errs = []
    if not password or len(password) < 8:
        errs.append("La contraseña debe tener al menos 8 caracteres.")
    elif len(password.encode("utf-8")) > 72:
        errs.append("La contraseña no puede superar 72 bytes.")
    if password and not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        errs.append("La contraseña debe combinar letras y números.")
    return errs


def validate_password(password: str) -> None:
    errs = password_errors(password)
    if errs:
        raise ValidationError(errs)


def _decimal(value, label, errs, maximo=1_000_000):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errs.append(f"{label} debe ser un número.")
        return None
    if not d.is_finite() or d <= 0:
        errs.append(f"{label} debe ser mayor que cero.")
        return None
    if d > maximo:
        errs.append(f"{label} no puede superar {maximo:,}.")
        return None
    return d.quantize(Decimal("0.01"))


def validate_usuario(data: dict) -> dict:
    e = []
    nombre = clean(data.get("nombre_completo"))
    correo = clean(data.get("correo")).lower()
    usuario = clean(data.get("usuario"))
    rol = data.get("rol")
    estado = data.get("estado", "activo")
    if not 3 <= len(nombre) <= 120:
        e.append("El nombre completo es obligatorio (3 a 120 caracteres).")
    if not EMAIL_RE.match(correo) or len(correo) > 150:
        e.append("Ingresa un correo electrónico válido.")
    if not USER_RE.match(usuario):
        e.append("El usuario debe tener 4 a 40 caracteres (letras, números, punto, guion o guion bajo).")
    if rol not in ROLES:
        e.append("Selecciona un rol válido.")
    if estado not in ESTADOS_GENERALES:
        e.append("Estado de usuario inválido.")
    if e:
        raise ValidationError(e)
    return {"nombre_completo": nombre, "correo": correo, "usuario": usuario, "rol": rol, "estado": estado}


def validate_negocio(data: dict) -> dict:
    e = []
    nombre, tipo = clean(data.get("nombre")), clean(data.get("tipo"))
    direccion, resp = clean(data.get("direccion")), clean(data.get("responsable"))
    estado = data.get("estado", "activo")
    if not 3 <= len(nombre) <= 120:
        e.append("El nombre del negocio es obligatorio (3 a 120 caracteres).")
    if not tipo:
        e.append("El tipo de establecimiento es obligatorio.")
    if not 5 <= len(direccion) <= 200:
        e.append("La dirección es obligatoria (5 a 200 caracteres).")
    if not 3 <= len(resp) <= 120:
        e.append("El responsable es obligatorio (3 a 120 caracteres).")
    tarifa = _decimal(data.get("tarifa_kwh"), "La tarifa por kWh", e)
    if estado not in ESTADOS_GENERALES:
        e.append("Estado inválido.")
    if e:
        raise ValidationError(e)
    return {"nombre": nombre, "tipo": tipo, "direccion": direccion, "tarifa_kwh": tarifa,
            "responsable": resp, "estado": estado}


def validate_equipo(data: dict) -> dict:
    e = []
    nombre, tipo, ubic = clean(data.get("nombre")), clean(data.get("tipo")), clean(data.get("ubicacion"))
    estado = data.get("estado", "activo")
    if not 2 <= len(nombre) <= 120:
        e.append("El nombre del equipo es obligatorio (2 a 120 caracteres).")
    if not tipo:
        e.append("El tipo de equipo es obligatorio.")
    if not 2 <= len(ubic) <= 120:
        e.append("La ubicación es obligatoria (2 a 120 caracteres).")
    potencia = _decimal(data.get("potencia_w"), "La potencia nominal (W)", e)
    if not data.get("negocio_id"):
        e.append("Debes asociar el equipo a un negocio.")
    if estado not in ESTADOS_GENERALES:
        e.append("Estado inválido.")
    if e:
        raise ValidationError(e)
    return {"nombre": nombre, "tipo": tipo, "ubicacion": ubic, "potencia_w": potencia,
            "negocio_id": int(data["negocio_id"]), "estado": estado}


def validate_sensor(data: dict) -> dict:
    e = []
    codigo = clean(data.get("codigo")).upper()
    tipo = clean(data.get("tipo"))
    fecha = data.get("fecha_instalacion")
    estado = data.get("estado", "inactivo")
    if not CODIGO_RE.match(codigo):
        e.append("El código debe tener 3 a 40 caracteres (letras, números, guion o guion bajo).")
    if not tipo:
        e.append("El tipo de sensor es obligatorio.")
    if not isinstance(fecha, date):
        e.append("La fecha de instalación es obligatoria.")
    elif fecha > date.today():
        e.append("La fecha de instalación no puede ser futura.")
    if estado not in ESTADOS_SENSOR:
        e.append("Estado de sensor inválido.")
    if e:
        raise ValidationError(e)
    equipo_id = data.get("equipo_id")
    return {"codigo": codigo, "tipo": tipo, "fecha_instalacion": fecha, "estado": estado,
            "equipo_id": int(equipo_id) if equipo_id else None, "simulado": 1 if data.get("simulado") else 0}
