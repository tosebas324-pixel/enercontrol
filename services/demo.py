"""Datos de demostración, claramente identificados con el prefijo [DEMO]."""
from datetime import date

from core.constants import PREFIJO_DEMO
from core.db import fetch_one, insert
from core.permissions import require

NEGOCIO = f"{PREFIJO_DEMO} Cafetería Aurora"
EQUIPOS = [
    ("Nevera exhibidora", "Refrigeración", "Salón principal", 350),
    ("Cafetera industrial", "Cocina", "Barra", 1800),
    ("Iluminación LED salón", "Iluminación", "Salón principal", 240),
]


def cargar(actor) -> str:
    require(actor, "demo:cargar")
    if fetch_one("SELECT id FROM negocios WHERE nombre = :n", {"n": NEGOCIO}):
        return "Los datos de demostración ya estaban cargados."
    nid = insert(
        """INSERT INTO negocios (nombre, tipo, direccion, tarifa_kwh, responsable, estado)
           VALUES (:n, 'Cafetería', 'Dirección de demostración 123', 750.00, 'Responsable Demo', 'activo')""",
        {"n": NEGOCIO},
    )
    for i, (nombre, tipo, ubic, pot) in enumerate(EQUIPOS, start=1):
        eid = insert(
            """INSERT INTO equipos (nombre, tipo, ubicacion, potencia_w, negocio_id, estado)
               VALUES (:n, :t, :u, :p, :neg, 'activo')""",
            {"n": f"{PREFIJO_DEMO} {nombre}", "t": tipo, "u": ubic, "p": pot, "neg": nid},
        )
        insert(
            """INSERT INTO sensores (codigo, tipo, fecha_instalacion, equipo_id, estado, simulado)
               VALUES (:c, 'Potencia/Energía', :f, :e, 'inactivo', 1)""",
            {"c": f"DEMO-SIM-{i:03d}", "f": date.today(), "e": eid},
        )
    return "Datos de demostración cargados (negocio, 3 equipos y 3 sensores simulados)."
