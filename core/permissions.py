"""Matriz de permisos centralizada. Se verifica en cada operación de los servicios.

Decisiones adoptadas donde la especificación no es explícita (ajustables vía
[permissions] en secrets o editando DEFAULT_PERMISSIONS):
- Técnico IoT y Analista pueden CONSULTAR negocios y equipos (necesario para asociar
  sensores y para analizar), pero no modificarlos.
- Analista puede consultar sensores (solo lectura).
- El Administrador puede hacer todo lo que hace el Técnico IoT sobre sensores.
- Solo el Administrador gestiona usuarios, carga datos de demostración y ve la matriz.
"""
from core.constants import ADMIN, ANALISTA, ROLES, TECNICO


class PermissionDenied(Exception):
    pass


_TODOS = {ADMIN, TECNICO, ANALISTA}
_ADM = {ADMIN}
_ADM_TEC = {ADMIN, TECNICO}

DEFAULT_PERMISSIONS = {
    "dashboard:ver": _TODOS,
    "usuarios:ver": _ADM, "usuarios:crear": _ADM, "usuarios:editar": _ADM,
    "usuarios:desactivar": _ADM, "usuarios:eliminar": _ADM,
    "negocios:ver": _TODOS, "negocios:crear": _ADM, "negocios:editar": _ADM, "negocios:eliminar": _ADM,
    "equipos:ver": _TODOS, "equipos:crear": _ADM, "equipos:editar": _ADM, "equipos:eliminar": _ADM,
    "sensores:ver": _TODOS, "sensores:crear": _ADM_TEC, "sensores:editar": _ADM_TEC,
    "sensores:eliminar": _ADM_TEC, "sensores:asociar": _ADM_TEC, "sensores:desvincular": _ADM_TEC,
    "sensores:simular": _ADM_TEC, "sensores:supervisar": _ADM_TEC,
    "demo:cargar": _ADM,
    "permisos:ver": _ADM,
    "iteracion2:ver": _TODOS,
    "iteracion3:ver": {ADMIN, ANALISTA},
}


def _overrides() -> dict:
    try:
        import streamlit as st

        if "permissions" in st.secrets:
            return {k: set(v) for k, v in dict(st.secrets["permissions"]).items()}
    except Exception:  # noqa: BLE001
        pass
    return {}


def matriz_efectiva() -> dict:
    matriz = {k: set(v) for k, v in DEFAULT_PERMISSIONS.items()}
    for perm, roles in _overrides().items():
        if perm in matriz:
            matriz[perm] = {r for r in roles if r in ROLES}
    return matriz


def has_permission(rol: str, permiso: str) -> bool:
    return rol in matriz_efectiva().get(permiso, set())


def require(actor: dict | None, permiso: str) -> None:
    if not actor or not has_permission(actor.get("rol"), permiso):
        raise PermissionDenied(f"No tienes permiso para realizar esta operación ({permiso}).")
