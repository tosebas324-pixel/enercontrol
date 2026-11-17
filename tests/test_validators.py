"""Pruebas funcionales de validaciones y permisos (sin base de datos).
Ejecutar:  pytest -q
"""
from datetime import date, timedelta

import pytest

from core.constants import ADMIN, ANALISTA, TECNICO
from core.permissions import DEFAULT_PERMISSIONS
from core.validators import (ValidationError, password_errors, validate_equipo, validate_negocio,
                             validate_sensor, validate_usuario)


def test_usuario_valido():
    r = validate_usuario({"nombre_completo": "Ana Pérez", "correo": "ANA@mail.com", "usuario": "ana.p",
                          "rol": ADMIN, "estado": "activo"})
    assert r["correo"] == "ana@mail.com"


def test_usuario_invalido():
    with pytest.raises(ValidationError) as e:
        validate_usuario({"nombre_completo": "", "correo": "x", "usuario": "a", "rol": "X"})
    assert len(e.value.errors) >= 4


def test_password_policy():
    assert password_errors("abc12345") == []
    assert password_errors("corta1")
    assert password_errors("sololetras")


def test_negocio_tarifa_positiva():
    base = {"nombre": "Café Uno", "tipo": "Cafetería", "direccion": "Calle 1 # 2-3", "responsable": "Luis Gómez"}
    assert validate_negocio({**base, "tarifa_kwh": 700})["tarifa_kwh"] == 700
    with pytest.raises(ValidationError):
        validate_negocio({**base, "tarifa_kwh": 0})


def test_equipo_requiere_negocio_y_potencia():
    with pytest.raises(ValidationError):
        validate_equipo({"nombre": "Nevera", "tipo": "Refrigeración", "ubicacion": "Cocina", "potencia_w": 0})


def test_sensor_fecha_futura_rechazada():
    with pytest.raises(ValidationError):
        validate_sensor({"codigo": "esp-001", "tipo": "Corriente (CT)",
                         "fecha_instalacion": date.today() + timedelta(days=1)})
    ok = validate_sensor({"codigo": "esp-001", "tipo": "Corriente (CT)", "fecha_instalacion": date.today()})
    assert ok["codigo"] == "ESP-001"


def test_matriz_permisos():
    assert ADMIN in DEFAULT_PERMISSIONS["usuarios:crear"]
    assert TECNICO not in DEFAULT_PERMISSIONS["usuarios:crear"]
    assert TECNICO in DEFAULT_PERMISSIONS["sensores:asociar"]
    assert ANALISTA not in DEFAULT_PERMISSIONS["sensores:asociar"]
