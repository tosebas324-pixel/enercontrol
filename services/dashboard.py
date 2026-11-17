"""Indicadores generales del sistema (Iteración #1: inventario, no consumo)."""
from core.db import fetch_one, run_query
from core.permissions import has_permission, require


def resumen(actor) -> dict:
    require(actor, "dashboard:ver")
    c = fetch_one(
        """SELECT
             (SELECT COUNT(*) FROM usuarios WHERE estado='activo') AS usuarios_activos,
             (SELECT COUNT(*) FROM negocios) AS negocios,
             (SELECT COUNT(*) FROM equipos) AS equipos,
             (SELECT COUNT(*) FROM sensores) AS sensores,
             (SELECT COUNT(*) FROM sensores WHERE estado='activo') AS sensores_activos,
             (SELECT COUNT(*) FROM sensores WHERE estado='sin_conexion') AS sensores_sin_conexion,
             (SELECT COALESCE(SUM(potencia_w),0) FROM equipos WHERE estado='activo') AS potencia_w"""
    )
    c = {k: float(v) if k == "potencia_w" else int(v) for k, v in c.items()}
    if not has_permission(actor["rol"], "usuarios:ver"):
        c["usuarios_activos"] = None
    estados = run_query("SELECT estado, COUNT(*) AS cantidad FROM sensores GROUP BY estado")
    potencia = run_query(
        """SELECT n.nombre AS negocio, COALESCE(SUM(e.potencia_w),0)/1000 AS kw
           FROM negocios n LEFT JOIN equipos e ON e.negocio_id = n.id AND e.estado='activo'
           GROUP BY n.id, n.nombre ORDER BY kw DESC LIMIT 15"""
    )
    potencia["kw"] = potencia["kw"].astype(float)
    return {"conteos": c, "sensores_por_estado": estados, "potencia_por_negocio": potencia}
