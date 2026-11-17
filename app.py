"""EnerControl - Iteración #1: autenticación, usuarios, negocios, equipos y sensores IoT.

Ejecutar con:  streamlit run app.py
"""
import html
import logging
import time
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from core import db
from core.constants import (
    ESTADO_SENSOR_ICON, ESTADOS_GENERALES, ESTADOS_SENSOR, ROL_LABELS, ROLES,
    TIPOS_EQUIPO, TIPOS_NEGOCIO, TIPOS_SENSOR,
)
from core.permissions import PermissionDenied, has_permission, matriz_efectiva
from core.validators import ValidationError
from services import auth, dashboard, demo, equipos, negocios, sensores, usuarios

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("enercontrol.app")

VERDE = "#16a34a"

CSS = """
<style>
.block-container{padding-top:1.5rem;max-width:1200px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#111827,#1f2937)}
[data-testid="stSidebar"] *{color:#e5e7eb}
[data-testid="stSidebar"] .stButton>button{background:#16a34a;color:#fff;border:0;width:100%}
.ec-logo{font-size:1.7rem;font-weight:800;letter-spacing:-.5px}
.ec-logo span{color:#22c55e}
.ec-card{background:#fff;border:1px solid #e5e7eb;border-left:5px solid #16a34a;border-radius:12px;
  padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:12px}
.ec-card .t{font-size:.75rem;text-transform:uppercase;color:#6b7280;font-weight:600}
.ec-card .v{font-size:1.8rem;font-weight:800;color:#111827;line-height:1.2}
.ec-card .h{font-size:.78rem;color:#6b7280}
.ec-header{background:linear-gradient(90deg,#14532d,#16a34a);border-radius:14px;padding:18px 22px;margin-bottom:18px}
.ec-header h2{margin:0;color:#fff;font-size:1.5rem}
.ec-header p{margin:4px 0 0;color:#dcfce7}
.ec-pending{border:2px dashed #9ca3af;border-radius:12px;padding:16px;background:#f3f4f6}
.stButton>button,.stFormSubmitButton>button{border-radius:8px;font-weight:600}
@media (max-width:768px){
  .block-container{padding:1rem .75rem}
  .ec-card .v{font-size:1.4rem}
  .ec-logo{font-size:1.4rem}
  .ec-header{padding:14px}
}
</style>
"""


# ----------------------------------------------------------------------------
# Utilidades de interfaz
# ----------------------------------------------------------------------------
def flash(kind: str, msg: str) -> None:
    st.session_state.setdefault("_flash", []).append((kind, msg))


def show_flash() -> None:
    for kind, msg in st.session_state.pop("_flash", []):
        {"success": st.success, "error": st.error, "warning": st.warning, "info": st.info}[kind](msg)
        if kind == "success":
            st.toast(msg, icon="✅")


def run_action(fn, ok_msg: str | None = None) -> bool:
    """Ejecuta una operación mostrando errores de validación, permisos o BD de forma segura."""
    try:
        fn()
    except ValidationError as exc:
        for m in exc.errors:
            st.error(m)
        return False
    except PermissionDenied as exc:
        st.error(f"⛔ {exc}")
        return False
    except SQLAlchemyError as exc:
        log.error("Error de base de datos: %s", exc)
        st.error("No se pudo completar la operación por un error de base de datos. Inténtalo nuevamente.")
        return False
    except Exception as exc:  # noqa: BLE001
        log.exception("Error inesperado: %s", exc)
        st.error("Ocurrió un error inesperado. Inténtalo nuevamente.")
        return False
    if ok_msg:
        flash("success", ok_msg)
    return True


def load(fn, *args):
    """Carga datos (DataFrame) manejando errores; devuelve None si falla."""
    try:
        return fn(*args)
    except PermissionDenied as exc:
        st.error(f"⛔ {exc}")
    except SQLAlchemyError as exc:
        log.error("Error al consultar: %s", exc)
        st.error("No se pudo consultar la información. Verifica la conexión con la base de datos.")
    return None


def header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="ec-header"><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def card(title: str, value, hint: str = "") -> None:
    st.markdown(
        f'<div class="ec-card"><div class="t">{html.escape(title)}</div>'
        f'<div class="v">{html.escape(str(value))}</div><div class="h">{html.escape(hint)}</div></div>',
        unsafe_allow_html=True,
    )


def build_tabs(user: dict, spec: list) -> dict:
    """spec: [(clave, título, permiso)]. Solo crea las pestañas permitidas."""
    allowed = [(k, t) for k, t, p in spec if has_permission(user["rol"], p)]
    tabs = st.tabs([t for _, t in allowed])
    return {k: tab for (k, _), tab in zip(allowed, tabs)}


def pick_row(label: str, df: pd.DataFrame, key: str, fmt):
    if df is None or df.empty:
        st.info("No hay registros disponibles.")
        return None
    lookup = {int(r["id"]): r for r in df.to_dict("records")}
    sel = st.selectbox(label, list(lookup.keys()), format_func=lambda i: fmt(lookup[int(i)]), key=key)
    return lookup[int(sel)]


def idx(options: list, value) -> int:
    return options.index(value) if value in options else 0


def to_date(value) -> date:
    try:
        d = pd.to_datetime(value)
        if pd.isna(d):
            return date.today()
        return d.date()
    except Exception:  # noqa: BLE001
        return date.today()


def filtrar_texto(df: pd.DataFrame, texto: str) -> pd.DataFrame:
    if not texto:
        return df
    mask = df.astype(str).apply(lambda col: col.str.contains(texto, case=False, na=False, regex=False)).any(axis=1)
    return df[mask]


# ----------------------------------------------------------------------------
# Pantallas previas al ingreso
# ----------------------------------------------------------------------------
def view_db_error(msg: str) -> None:
    st.markdown('<div class="ec-logo">⚡ Ener<span>Control</span></div>', unsafe_allow_html=True)
    st.error("No fue posible conectar con la base de datos MySQL.")
    st.caption(f"Detalle técnico: {msg}")
    st.markdown("Configura las credenciales en `.streamlit/secrets.toml` (local) o en **Settings → Secrets** (Streamlit Cloud):")
    st.code(
        '[mysql]\nhost = "..."\nport = 3306\nuser = "..."\npassword = "..."\ndatabase = "enercontrol"',
        language="toml",
    )


def view_setup() -> None:
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        st.markdown('<div class="ec-logo">⚡ Ener<span>Control</span></div>', unsafe_allow_html=True)
        st.subheader("Configuración inicial")
        st.info("No existen usuarios. Crea la cuenta del primer **Administrador**.")
        show_flash()
        with st.form("setup"):
            nombre = st.text_input("Nombre completo")
            correo = st.text_input("Correo electrónico")
            usuario = st.text_input("Nombre de usuario")
            p1 = st.text_input("Contraseña (mín. 8, letras y números)", type="password")
            p2 = st.text_input("Confirmar contraseña", type="password")
            ok = st.form_submit_button("Crear administrador")
        if ok:
            if p1 != p2:
                st.error("Las contraseñas no coinciden.")
            elif run_action(
                lambda: auth.crear_primer_admin(
                    {"nombre_completo": nombre, "correo": correo, "usuario": usuario}, p1),
                "Administrador creado. Ya puedes iniciar sesión.",
            ):
                st.rerun()


def do_login(usuario: str, password: str) -> None:
    ahora = time.time()
    bloqueo = st.session_state.get("lock_until", 0)
    if ahora < bloqueo:
        st.error(f"Demasiados intentos fallidos. Espera {int(bloqueo - ahora)} segundos.")
        return
    try:
        user, msg = auth.autenticar(usuario, password)
    except SQLAlchemyError as exc:
        log.error("Error en login: %s", exc)
        st.error("No se pudo validar el acceso por un error de base de datos.")
        return
    if user is None:
        st.session_state["fails"] = st.session_state.get("fails", 0) + 1
        if st.session_state["fails"] >= 5:
            st.session_state["lock_until"] = ahora + 60
            st.session_state["fails"] = 0
        st.error(f"❌ {msg}")
        return
    st.session_state["uid"] = user["id"]
    st.session_state["fails"] = 0
    flash("success", f"Inicio de sesión exitoso. Bienvenido/a, {user['nombre_completo']}.")
    st.rerun()


def view_login() -> None:
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        st.markdown('<div class="ec-logo">⚡ Ener<span>Control</span></div>', unsafe_allow_html=True)
        st.caption("Monitoreo y análisis del consumo eléctrico para tu negocio")
        show_flash()
        t_login, t_rec = st.tabs(["🔑 Iniciar sesión", "📧 Recuperar contraseña"])
        with t_login:
            with st.form("login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                ok = st.form_submit_button("Ingresar")
            if ok:
                do_login(u, p)
        with t_rec:
            if not _smtp_ok():
                st.info("La recuperación por correo no está disponible: el servicio SMTP no está configurado.")
            else:
                with st.form("rec1"):
                    correo = st.text_input("Correo registrado")
                    enviar = st.form_submit_button("Enviar código")
                if enviar:
                    try:
                        st.success(auth.solicitar_recuperacion(correo))
                    except ValidationError as exc:
                        for m in exc.errors:
                            st.error(m)
                    except SQLAlchemyError:
                        st.error("Error de base de datos. Inténtalo nuevamente.")
                with st.form("rec2"):
                    c2 = st.text_input("Correo")
                    codigo = st.text_input("Código de 6 dígitos")
                    n1 = st.text_input("Nueva contraseña", type="password")
                    n2 = st.text_input("Confirmar nueva contraseña", type="password")
                    cambiar = st.form_submit_button("Cambiar contraseña")
                if cambiar:
                    if n1 != n2:
                        st.error("Las contraseñas no coinciden.")
                    elif run_action(lambda: auth.confirmar_recuperacion(c2, codigo, n1)):
                        st.success("Contraseña actualizada. Ya puedes iniciar sesión.")


def _smtp_ok() -> bool:
    from core import mailer

    return mailer.is_configured()


# ----------------------------------------------------------------------------
# Panel principal
# ----------------------------------------------------------------------------
def page_dashboard(user: dict) -> None:
    header("Panel general", "Resumen del inventario y estado de los dispositivos")
    show_flash()
    data = load(dashboard.resumen, user)
    if data is None:
        return
    c = data["conteos"]
    cols = st.columns(4)
    with cols[0]:
        card("Negocios", c["negocios"], "Registrados")
    with cols[1]:
        card("Equipos", c["equipos"], "Registrados")
    with cols[2]:
        card("Sensores", c["sensores"], f"{c['sensores_activos']} activos")
    with cols[3]:
        card("Sin conexión", c["sensores_sin_conexion"], "Sensores a revisar")
    cols = st.columns(2)
    with cols[0]:
        card("Potencia nominal instalada", f"{c['potencia_w'] / 1000:,.2f} kW", "Equipos activos (no es consumo medido)")
    with cols[1]:
        if c["usuarios_activos"] is not None:
            card("Usuarios activos", c["usuarios_activos"], "Con acceso al sistema")
        else:
            card("Tu rol", ROL_LABELS[user["rol"]], "Permisos según la matriz del sistema")

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Sensores por estado")
        est = data["sensores_por_estado"]
        if est.empty:
            st.info("Aún no hay sensores registrados.")
        else:
            est["estado"] = est["estado"].map(lambda e: ESTADO_SENSOR_ICON.get(e, e))
            fig = px.pie(est, names="estado", values="cantidad", hole=0.5,
                         color_discrete_sequence=["#16a34a", "#9ca3af", "#dc2626"])
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig)
    with g2:
        st.subheader("Potencia nominal por negocio (kW)")
        pot = data["potencia_por_negocio"]
        if pot.empty:
            st.info("Aún no hay negocios registrados.")
        else:
            fig = px.bar(pot, x="negocio", y="kw", color_discrete_sequence=[VERDE])
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None, yaxis_title="kW")
            st.plotly_chart(fig)

    if has_permission(user["rol"], "demo:cargar"):
        with st.expander("🧪 Datos de demostración"):
            st.caption("Crea un negocio, equipos y sensores simulados identificados con el prefijo [DEMO].")
            if st.button("Cargar datos de demostración"):
                try:
                    msg = demo.cargar(user)
                    flash("success", msg)
                    st.rerun()
                except (ValidationError, PermissionDenied) as exc:
                    st.error(str(exc))
                except SQLAlchemyError as exc:
                    log.error("Demo: %s", exc)
                    st.error("No se pudieron cargar los datos de demostración.")


# ----------------------------------------------------------------------------
# Usuarios
# ----------------------------------------------------------------------------
def page_usuarios(user: dict) -> None:
    header("Gestión de usuarios", "Registro, roles y estado de las cuentas")
    show_flash()
    tabs = build_tabs(user, [
        ("lista", "📋 Listado", "usuarios:ver"), ("crear", "➕ Registrar", "usuarios:crear"),
        ("editar", "✏️ Editar", "usuarios:editar"), ("estado", "🗑️ Desactivar / Eliminar", "usuarios:desactivar"),
    ])
    df = load(usuarios.listar, user)
    if df is None:
        return
    fmt = lambda r: f"{r['nombre_completo']} (@{r['usuario']}) - {r['estado']}"  # noqa: E731

    if "lista" in tabs:
        with tabs["lista"]:
            f1, f2 = st.columns([2, 1])
            texto = f1.text_input("Buscar", key="u_buscar")
            estado = f2.selectbox("Estado", ["todos"] + ESTADOS_GENERALES, key="u_estado")
            vista = filtrar_texto(df, texto)
            if estado != "todos":
                vista = vista[vista["estado"] == estado]
            vista = vista.assign(rol=vista["rol"].map(ROL_LABELS))
            st.dataframe(vista.rename(columns={
                "id": "ID", "nombre_completo": "Nombre", "correo": "Correo", "usuario": "Usuario",
                "rol": "Rol", "estado": "Estado", "creado_en": "Creado"}), hide_index=True)
            st.caption(f"{len(vista)} usuario(s)")

    if "crear" in tabs:
        with tabs["crear"]:
            with st.form("u_crear", clear_on_submit=False):
                a, b = st.columns(2)
                nombre = a.text_input("Nombre completo *")
                correo = b.text_input("Correo electrónico *")
                usuario = a.text_input("Nombre de usuario *")
                rol = b.selectbox("Rol *", ROLES, format_func=ROL_LABELS.get)
                p1 = a.text_input("Contraseña *", type="password", help="Mínimo 8 caracteres, letras y números")
                p2 = b.text_input("Confirmar contraseña *", type="password")
                estado = st.selectbox("Estado", ESTADOS_GENERALES)
                ok = st.form_submit_button("Registrar usuario")
            if ok and run_action(
                lambda: usuarios.crear(user, {"nombre_completo": nombre, "correo": correo, "usuario": usuario,
                                              "rol": rol, "estado": estado}, p1, p2),
                "Usuario registrado correctamente.",
            ):
                st.rerun()

    if "editar" in tabs:
        with tabs["editar"]:
            row = pick_row("Selecciona el usuario", df, "u_edit_sel", fmt)
            if row:
                k = row["id"]
                with st.form(f"u_edit_{k}"):
                    a, b = st.columns(2)
                    nombre = a.text_input("Nombre completo *", row["nombre_completo"], key=f"ue_n{k}")
                    correo = b.text_input("Correo electrónico *", row["correo"], key=f"ue_c{k}")
                    usuario = a.text_input("Nombre de usuario *", row["usuario"], key=f"ue_u{k}")
                    rol = b.selectbox("Rol *", ROLES, idx(ROLES, row["rol"]), format_func=ROL_LABELS.get, key=f"ue_r{k}")
                    estado = a.selectbox("Estado", ESTADOS_GENERALES, idx(ESTADOS_GENERALES, row["estado"]), key=f"ue_e{k}")
                    nueva = b.text_input("Nueva contraseña (opcional)", type="password", key=f"ue_p{k}")
                    ok = st.form_submit_button("Guardar cambios")
                if ok and run_action(
                    lambda: usuarios.actualizar(user, int(k), {"nombre_completo": nombre, "correo": correo,
                                                               "usuario": usuario, "rol": rol, "estado": estado}, nueva),
                    "Usuario actualizado correctamente.",
                ):
                    st.rerun()

    if "estado" in tabs:
        with tabs["estado"]:
            row = pick_row("Selecciona el usuario", df, "u_del_sel", fmt)
            if row:
                k = int(row["id"])
                st.warning("Desactivar impide el acceso pero conserva el registro. Eliminar es permanente.")
                c1, c2 = st.columns(2)
                nuevo = "activo" if row["estado"] == "inactivo" else "inactivo"
                if c1.button("Reactivar usuario" if nuevo == "activo" else "Desactivar usuario", key=f"u_toggle{k}"):
                    if run_action(lambda: usuarios.cambiar_estado(user, k, nuevo), f"Usuario {nuevo} correctamente."):
                        st.rerun()
                if has_permission(user["rol"], "usuarios:eliminar"):
                    conf = c2.checkbox("Confirmo que deseo eliminarlo", key=f"u_conf{k}")
                    if c2.button("Eliminar definitivamente", key=f"u_del{k}", disabled=not conf):
                        if run_action(lambda: usuarios.eliminar(user, k), "Usuario eliminado correctamente."):
                            st.rerun()


# ----------------------------------------------------------------------------
# Negocios
# ----------------------------------------------------------------------------
def _form_negocio(prefix: str, row: dict | None = None) -> dict:
    row = row or {}
    a, b = st.columns(2)
    tipos = TIPOS_NEGOCIO if row.get("tipo") in (None, *TIPOS_NEGOCIO) else TIPOS_NEGOCIO + [row["tipo"]]
    return {
        "nombre": a.text_input("Nombre del negocio *", row.get("nombre", ""), key=f"{prefix}n"),
        "tipo": b.selectbox("Tipo de establecimiento *", tipos, idx(tipos, row.get("tipo")), key=f"{prefix}t"),
        "direccion": a.text_input("Dirección *", row.get("direccion", ""), key=f"{prefix}d"),
        "tarifa_kwh": b.number_input("Tarifa de energía por kWh *", min_value=0.0, step=10.0, format="%.2f",
                                     value=float(row.get("tarifa_kwh", 0.0)), key=f"{prefix}f",
                                     help="Se usará para calcular el costo estimado (Iteración #2)"),
        "responsable": a.text_input("Responsable *", row.get("responsable", ""), key=f"{prefix}r"),
        "estado": b.selectbox("Estado", ESTADOS_GENERALES, idx(ESTADOS_GENERALES, row.get("estado")), key=f"{prefix}e"),
    }


def page_negocios(user: dict) -> None:
    header("Gestión de negocios", "Establecimientos monitoreados y su tarifa eléctrica")
    show_flash()
    tabs = build_tabs(user, [
        ("lista", "📋 Listado", "negocios:ver"), ("crear", "➕ Registrar", "negocios:crear"),
        ("editar", "✏️ Editar", "negocios:editar"), ("eliminar", "🗑️ Eliminar", "negocios:eliminar"),
    ])
    df = load(negocios.listar, user)
    if df is None:
        return
    fmt = lambda r: f"{r['nombre']} ({r['tipo']})"  # noqa: E731

    if "lista" in tabs:
        with tabs["lista"]:
            f1, f2 = st.columns([2, 1])
            texto = f1.text_input("Buscar", key="n_buscar")
            estado = f2.selectbox("Estado", ["todos"] + ESTADOS_GENERALES, key="n_estado")
            vista = filtrar_texto(df, texto)
            if estado != "todos":
                vista = vista[vista["estado"] == estado]
            st.dataframe(vista.rename(columns={
                "id": "ID", "nombre": "Nombre", "tipo": "Tipo", "direccion": "Dirección",
                "tarifa_kwh": "Tarifa/kWh", "responsable": "Responsable", "estado": "Estado", "equipos": "Equipos"}),
                hide_index=True)
            st.caption(f"{len(vista)} negocio(s)")

    if "crear" in tabs:
        with tabs["crear"]:
            with st.form("n_crear", clear_on_submit=True):
                datos = _form_negocio("nc_")
                ok = st.form_submit_button("Registrar negocio")
            if ok and run_action(lambda: negocios.crear(user, datos), "Negocio registrado correctamente."):
                st.rerun()

    if "editar" in tabs:
        with tabs["editar"]:
            row = pick_row("Selecciona el negocio", df, "n_edit_sel", fmt)
            if row:
                with st.form(f"n_edit_{row['id']}"):
                    datos = _form_negocio(f"ne{row['id']}_", row)
                    ok = st.form_submit_button("Guardar cambios")
                if ok and run_action(lambda: negocios.actualizar(user, int(row["id"]), datos),
                                     "Negocio actualizado correctamente."):
                    st.rerun()

    if "eliminar" in tabs:
        with tabs["eliminar"]:
            row = pick_row("Selecciona el negocio", df, "n_del_sel", fmt)
            if row:
                st.warning("La eliminación es permanente y solo es posible si el negocio no tiene equipos.")
                conf = st.checkbox("Confirmo que deseo eliminarlo", key=f"n_conf{row['id']}")
                if st.button("Eliminar negocio", disabled=not conf, key=f"n_del{row['id']}"):
                    if run_action(lambda: negocios.eliminar(user, int(row["id"])), "Negocio eliminado correctamente."):
                        st.rerun()


# ----------------------------------------------------------------------------
# Equipos
# ----------------------------------------------------------------------------
def _form_equipo(prefix: str, df_neg: pd.DataFrame, row: dict | None = None) -> dict:
    row = row or {}
    a, b = st.columns(2)
    ids = [int(i) for i in df_neg["id"]]
    nombres = dict(zip(ids, df_neg["nombre"]))
    tipos = TIPOS_EQUIPO if row.get("tipo") in (None, *TIPOS_EQUIPO) else TIPOS_EQUIPO + [row["tipo"]]
    actual = int(row["negocio_id"]) if row.get("negocio_id") is not None else ids[0]
    return {
        "nombre": a.text_input("Nombre del equipo *", row.get("nombre", ""), key=f"{prefix}n"),
        "tipo": b.selectbox("Tipo de equipo *", tipos, idx(tipos, row.get("tipo")), key=f"{prefix}t"),
        "ubicacion": a.text_input("Ubicación *", row.get("ubicacion", ""), key=f"{prefix}u"),
        "potencia_w": b.number_input("Potencia nominal (W) *", min_value=0.0, step=10.0, format="%.2f",
                                     value=float(row.get("potencia_w", 0.0)), key=f"{prefix}p"),
        "negocio_id": a.selectbox("Negocio asociado *", ids, idx(ids, actual), format_func=nombres.get, key=f"{prefix}b"),
        "estado": b.selectbox("Estado", ESTADOS_GENERALES, idx(ESTADOS_GENERALES, row.get("estado")), key=f"{prefix}e"),
    }


def page_equipos(user: dict) -> None:
    header("Gestión de equipos eléctricos", "Inventario de equipos por negocio")
    show_flash()
    tabs = build_tabs(user, [
        ("lista", "📋 Listado", "equipos:ver"), ("crear", "➕ Registrar", "equipos:crear"),
        ("editar", "✏️ Editar", "equipos:editar"), ("eliminar", "🗑️ Eliminar", "equipos:eliminar"),
    ])
    df = load(equipos.listar, user)
    df_neg = load(negocios.listar, user)
    if df is None or df_neg is None:
        return
    fmt = lambda r: f"{r['nombre']} - {r['negocio']}"  # noqa: E731

    if "lista" in tabs:
        with tabs["lista"]:
            f1, f2 = st.columns([2, 1])
            texto = f1.text_input("Buscar", key="e_buscar")
            opciones = ["todos"] + sorted(df["negocio"].unique().tolist())
            neg = f2.selectbox("Negocio", opciones, key="e_neg")
            vista = filtrar_texto(df.drop(columns=["negocio_id"]), texto)
            if neg != "todos":
                vista = vista[vista["negocio"] == neg]
            st.dataframe(vista.rename(columns={
                "id": "ID", "nombre": "Equipo", "tipo": "Tipo", "ubicacion": "Ubicación", "potencia_w": "Potencia (W)",
                "negocio": "Negocio", "estado": "Estado", "sensores": "Sensores"}), hide_index=True)
            st.caption(f"{len(vista)} equipo(s)")

    needs_neg = "crear" in tabs or "editar" in tabs
    if needs_neg and df_neg.empty:
        for key in ("crear", "editar"):
            if key in tabs:
                with tabs[key]:
                    st.warning("Primero debes registrar al menos un negocio.")
    else:
        if "crear" in tabs:
            with tabs["crear"]:
                with st.form("e_crear", clear_on_submit=True):
                    datos = _form_equipo("ec_", df_neg)
                    ok = st.form_submit_button("Registrar equipo")
                if ok and run_action(lambda: equipos.crear(user, datos), "Equipo registrado correctamente."):
                    st.rerun()
        if "editar" in tabs:
            with tabs["editar"]:
                row = pick_row("Selecciona el equipo", df, "e_edit_sel", fmt)
                if row:
                    with st.form(f"e_edit_{row['id']}"):
                        datos = _form_equipo(f"ee{row['id']}_", df_neg, row)
                        ok = st.form_submit_button("Guardar cambios")
                    if ok and run_action(lambda: equipos.actualizar(user, int(row["id"]), datos),
                                         "Equipo actualizado correctamente."):
                        st.rerun()

    if "eliminar" in tabs:
        with tabs["eliminar"]:
            row = pick_row("Selecciona el equipo", df, "e_del_sel", fmt)
            if row:
                st.warning(f"Eliminación permanente. Sus {int(row['sensores'])} sensor(es) quedarán sin equipo asociado.")
                conf = st.checkbox("Confirmo que deseo eliminarlo", key=f"e_conf{row['id']}")
                if st.button("Eliminar equipo", disabled=not conf, key=f"e_del{row['id']}"):
                    if run_action(lambda: equipos.eliminar(user, int(row["id"])), "Equipo eliminado correctamente."):
                        st.rerun()


# ----------------------------------------------------------------------------
# Sensores
# ----------------------------------------------------------------------------
def _form_sensor(prefix: str, df_eq: pd.DataFrame, row: dict | None = None) -> dict:
    row = row or {}
    a, b = st.columns(2)
    ids = [None] + [int(i) for i in df_eq["id"]]
    etiquetas = {None: "— Sin equipo —"}
    etiquetas.update({int(r["id"]): f"{r['nombre']} · {r['negocio']}" for r in df_eq.to_dict("records")})
    actual = int(row["equipo_id"]) if row.get("equipo_id") is not None and not pd.isna(row.get("equipo_id")) else None
    tipos = TIPOS_SENSOR if row.get("tipo") in (None, *TIPOS_SENSOR) else TIPOS_SENSOR + [row["tipo"]]
    hoy = date.today()
    fecha_min = date(2000, 1, 1)
    fecha_val = min(max(to_date(row.get("fecha_instalacion")), fecha_min), hoy)
    return {
        "codigo": a.text_input("Código del sensor *", row.get("codigo", ""), key=f"{prefix}c"),
        "tipo": b.selectbox("Tipo de sensor *", tipos, idx(tipos, row.get("tipo")), key=f"{prefix}t"),
         "fecha_instalacion": a.date_input("Fecha de instalación *", fecha_val,
                               min_value=fecha_min, max_value=hoy, key=f"{prefix}f"),
        "equipo_id": b.selectbox("Equipo asociado", ids, idx(ids, actual), format_func=etiquetas.get, key=f"{prefix}q"),
        "estado": a.selectbox("Estado", ESTADOS_SENSOR, idx(ESTADOS_SENSOR, row.get("estado", "inactivo")),
                              format_func=lambda e: ESTADO_SENSOR_ICON[e], key=f"{prefix}e"),
        "simulado": b.checkbox("Sensor simulado (pruebas sin hardware)", bool(row.get("simulado", False)), key=f"{prefix}s"),
    }


def page_sensores(user: dict) -> None:
    header("Gestión de sensores IoT", "Registro, asociación y supervisión de dispositivos")
    show_flash()
    tabs = build_tabs(user, [
        ("lista", "📋 Listado", "sensores:ver"), ("crear", "➕ Registrar", "sensores:crear"),
        ("editar", "✏️ Editar", "sensores:editar"), ("asociar", "🔗 Asociar / Desvincular", "sensores:asociar"),
        ("estado", "📶 Estado y simulación", "sensores:ver"), ("eliminar", "🗑️ Eliminar", "sensores:eliminar"),
    ])
    df = load(sensores.listar, user)
    df_eq = load(equipos.listar, user)
    if df is None or df_eq is None:
        return
    fmt = lambda r: f"{r['codigo']} · {ESTADO_SENSOR_ICON.get(r['estado'], r['estado'])}"  # noqa: E731
    vista_cols = {"id": "ID", "codigo": "Código", "tipo": "Tipo", "fecha_instalacion": "Instalación",
                  "equipo": "Equipo", "negocio": "Negocio", "estado": "Estado", "simulado": "Simulado",
                  "ultima_conexion": "Última conexión (UTC)"}

    def tabla(d: pd.DataFrame) -> pd.DataFrame:
        d = d.drop(columns=["equipo_id"]).copy()
        d["estado"] = d["estado"].map(lambda e: ESTADO_SENSOR_ICON.get(e, e))
        d["equipo"] = d["equipo"].fillna("— Sin equipo —")
        d["negocio"] = d["negocio"].fillna("—")
        return d.rename(columns=vista_cols)

    if "lista" in tabs:
        with tabs["lista"]:
            f1, f2 = st.columns([2, 1])
            texto = f1.text_input("Buscar", key="s_buscar")
            estado = f2.selectbox("Estado", ["todos"] + ESTADOS_SENSOR, key="s_estado")
            vista = filtrar_texto(df, texto)
            if estado != "todos":
                vista = vista[vista["estado"] == estado]
            st.dataframe(tabla(vista), hide_index=True)
            st.caption(f"{len(vista)} sensor(es)")

    if "crear" in tabs:
        with tabs["crear"]:
            with st.form("s_crear", clear_on_submit=True):
                datos = _form_sensor("sc_", df_eq)
                ok = st.form_submit_button("Registrar sensor")
            if ok and run_action(lambda: sensores.crear(user, datos), "Sensor registrado correctamente."):
                st.rerun()

    if "editar" in tabs:
        with tabs["editar"]:
            row = pick_row("Selecciona el sensor", df, "s_edit_sel", fmt)
            if row:
                with st.form(f"s_edit_{row['id']}"):
                    datos = _form_sensor(f"se{row['id']}_", df_eq, row)
                    ok = st.form_submit_button("Guardar cambios")
                if ok and run_action(lambda: sensores.actualizar(user, int(row["id"]), datos),
                                     "Sensor actualizado correctamente."):
                    st.rerun()

    if "asociar" in tabs:
        with tabs["asociar"]:
            row = pick_row("Selecciona el sensor", df, "s_aso_sel", fmt)
            if row:
                actual = row["equipo"] if isinstance(row["equipo"], str) else "ninguno"
                st.info(f"Equipo actual: **{actual}**")
                if df_eq.empty:
                    st.warning("No hay equipos registrados para asociar.")
                else:
                    ids = [int(i) for i in df_eq["id"]]
                    nombres = {int(r["id"]): f"{r['nombre']} · {r['negocio']}" for r in df_eq.to_dict("records")}
                    destino = st.selectbox("Equipo destino", ids, format_func=nombres.get, key=f"s_dest{row['id']}")
                    c1, c2 = st.columns(2)
                    if c1.button("Asociar al equipo", key=f"s_aso{row['id']}"):
                        if run_action(lambda: sensores.asociar(user, int(row["id"]), int(destino)),
                                      "Sensor asociado correctamente."):
                            st.rerun()
                    if has_permission(user["rol"], "sensores:desvincular"):
                        if c2.button("Desvincular", key=f"s_des{row['id']}"):
                            if run_action(lambda: sensores.desvincular(user, int(row["id"])),
                                          "Sensor desvinculado correctamente."):
                                st.rerun()

    if "estado" in tabs:
        with tabs["estado"]:
            cols = st.columns(3)
            for col, est in zip(cols, ESTADOS_SENSOR):
                with col:
                    card(ESTADO_SENSOR_ICON[est], int((df["estado"] == est).sum()), "sensores")
            st.dataframe(tabla(df), hide_index=True)
            if has_permission(user["rol"], "sensores:supervisar"):
                st.markdown("**Supervisión de conexión**")
                minutos = st.number_input("Marcar 'sin conexión' si no hay latido en (minutos)", 1, 1440, 10, key="s_min")
                if st.button("Verificar conexiones ahora"):
                    try:
                        n = sensores.refrescar_conexiones(user, int(minutos))
                        flash("success" if n else "info", f"{n} sensor(es) marcados como sin conexión." if n
                              else "Todos los sensores activos reportaron recientemente.")
                        st.rerun()
                    except (ValidationError, PermissionDenied) as exc:
                        st.error(str(exc))
                    except SQLAlchemyError:
                        st.error("Error de base de datos al verificar conexiones.")
            if has_permission(user["rol"], "sensores:simular"):
                st.markdown("**Simulación de sensores** (solo los marcados como simulados)")
                simulados = df[df["simulado"]]
                row = pick_row("Sensor simulado", simulados, "s_sim_sel", fmt)
                if row:
                    accion = st.selectbox("Acción", list(sensores.ACCIONES_SIMULACION),
                                          format_func=sensores.ACCIONES_SIMULACION.get, key="s_sim_acc")
                    if st.button("Ejecutar simulación"):
                        if run_action(lambda: sensores.simular(user, int(row["id"]), accion), "Simulación ejecutada."):
                            st.rerun()
            st.caption("🔌 Próximamente: recepción de datos de dispositivos ESP32 por HTTP/HTTPS o MQTT (Iteración #2).")

    if "eliminar" in tabs:
        with tabs["eliminar"]:
            row = pick_row("Selecciona el sensor", df, "s_del_sel", fmt)
            if row:
                st.warning("La eliminación es permanente.")
                conf = st.checkbox("Confirmo que deseo eliminarlo", key=f"s_conf{row['id']}")
                if st.button("Eliminar sensor", disabled=not conf, key=f"s_del{row['id']}"):
                    if run_action(lambda: sensores.eliminar(user, int(row["id"])), "Sensor eliminado correctamente."):
                        st.rerun()


# ----------------------------------------------------------------------------
# Módulos pendientes y permisos
# ----------------------------------------------------------------------------
def page_pendiente(titulo: str, subtitulo: str, items: list) -> None:
    header(titulo, subtitulo)
    st.markdown(
        '<div class="ec-pending"><b>🚧 PENDIENTE — no implementado en la Iteración #1.</b><br>'
        "La arquitectura (tablas, servicios y permisos) está preparada para incorporarlo.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("\n".join(f"- {i}" for i in items))


def page_permisos(user: dict) -> None:
    header("Matriz de permisos", "Permisos efectivos por rol (se verifican en cada operación)")
    show_flash()
    matriz = matriz_efectiva()
    filas = [{"Permiso": perm, **{ROL_LABELS[r]: ("✅" if r in roles else "—") for r in ROLES}}
             for perm, roles in sorted(matriz.items())]
    st.dataframe(pd.DataFrame(filas), hide_index=True)
    st.caption("Para ajustarla: edita DEFAULT_PERMISSIONS en core/permissions.py o define la sección "
               "[permissions] en los secretos (ver secrets.toml.example).")


# ----------------------------------------------------------------------------
# Navegación y arranque
# ----------------------------------------------------------------------------
NAV = [
    ("🏠 Panel", "dashboard:ver", page_dashboard),
    ("👥 Usuarios", "usuarios:ver", page_usuarios),
    ("🏢 Negocios", "negocios:ver", page_negocios),
    ("🔌 Equipos", "equipos:ver", page_equipos),
    ("📡 Sensores IoT", "sensores:ver", page_sensores),
    ("📊 Consumo (Iter. 2 · pendiente)", "iteracion2:ver", lambda u: page_pendiente(
        "Consumo y reportes", "Iteración #2",
        ["Recepción de lecturas de consumo desde sensores", "Almacenamiento de datos eléctricos",
         "Cálculo de consumo en kWh y costos estimados", "Dashboard energético, históricos y comparaciones",
         "Reportes en PDF y Excel"])),
    ("🚨 Alertas (Iter. 3 · pendiente)", "iteracion3:ver", lambda u: page_pendiente(
        "Patrones y alertas", "Iteración #3",
        ["Detección de patrones de consumo", "Configuración de umbrales", "Detección de consumos anormales",
         "Generación e historial de alertas", "Notificaciones por correo"])),
    ("🔐 Permisos", "permisos:ver", page_permisos),
]


def current_user():
    uid = st.session_state.get("uid")
    if not uid:
        return None
    user = auth.obtener_usuario_activo(uid)
    if user is None:
        st.session_state.pop("uid", None)
    return user


def view_app(user: dict) -> None:
    opciones = [(label, fn) for label, perm, fn in NAV if has_permission(user["rol"], perm)]
    with st.sidebar:
        st.markdown('<div class="ec-logo">⚡ Ener<span>Control</span></div>', unsafe_allow_html=True)
        st.markdown(
            f"**{html.escape(user['nombre_completo'])}**<br><small>{ROL_LABELS[user['rol']]}</small>",
            unsafe_allow_html=True,
        )
        st.divider()
        etiqueta = st.radio("Navegación", [o[0] for o in opciones], label_visibility="collapsed")
        st.divider()
        if st.button("Cerrar sesión"):
            st.session_state.clear()
            flash("info", "Sesión cerrada correctamente.")
            st.rerun()
    dict(opciones)[etiqueta](user)


@st.cache_resource(show_spinner="Preparando base de datos...")
def ensure_schema() -> bool:
    db.init_schema()
    return True


def main() -> None:
    st.set_page_config(page_title="EnerControl", page_icon="⚡", layout="wide", initial_sidebar_state="auto")
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        ensure_schema()
        user = current_user()
        if user is None:
            if db.count_users() == 0:
                view_setup()
            else:
                view_login()
        else:
            view_app(user)
    except (SQLAlchemyError, RuntimeError) as exc:
        log.error("Fallo de base de datos: %s", exc)
        view_db_error(str(exc))


main()
