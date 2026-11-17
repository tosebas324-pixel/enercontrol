# ⚡ EnerControl — Iteración #1

Aplicación web (EnergyTech) para monitorear el consumo eléctrico de pequeños y medianos negocios.
Esta primera iteración incluye: **autenticación, usuarios, negocios, equipos y sensores IoT** (con simulación).

**Stack:** Python · Streamlit · MySQL · SQLAlchemy/PyMySQL · Pandas · Plotly · bcrypt.

## Estructura
```
app.py                 Interfaz y navegación
core/                  config, db, security, permissions, validators, mailer, constants
services/              auth, usuarios, negocios, equipos, sensores, dashboard, demo
database/schema.sql    Esquema MySQL (la app lo aplica automáticamente)
tests/                 Pruebas funcionales (pytest)
.streamlit/            config.toml y secrets.toml.example
```

## Ejecución local
1. Crea la base de datos: `CREATE DATABASE enercontrol CHARACTER SET utf8mb4;`
2. `pip install -r requirements.txt`
3. Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completa tus credenciales
   (o usa variables de entorno `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`).
4. `streamlit run app.py`
5. En el primer ingreso la app pide crear la cuenta del **primer administrador** (no hay credenciales por defecto).

Pruebas: `pytest -q`

## Roles y permisos
Centralizados en `core/permissions.py` y verificados en cada operación de `services/`
(no solo ocultando la interfaz). Decisiones donde la especificación no era explícita:
- Técnico IoT y Analista **consultan** negocios y equipos (solo lectura); el Analista consulta sensores.
- El Administrador puede gestionar sensores igual que el Técnico IoT.
- Solo el Administrador gestiona usuarios y carga datos de demostración.

Se puede ajustar editando `DEFAULT_PERMISSIONS` o con la sección `[permissions]` en los secretos.
La pantalla **Permisos** (solo Administrador) muestra la matriz efectiva.

## Recuperación de contraseña
Opcional: requiere la sección `[smtp]` en los secretos. Envía un código de 6 dígitos (15 min, 5 intentos, guardado como hash).

## Datos de demostración
El Administrador puede cargarlos desde el Panel; se identifican con el prefijo **[DEMO]** y los sensores son simulados.

## Publicar en GitHub y Streamlit Community Cloud
1. `git init && git add . && git commit -m "EnerControl Iteración 1"` y súbelo a un repositorio de GitHub
   (verifica que `.streamlit/secrets.toml` NO se suba).
2. Necesitas un MySQL **accesible desde Internet** (Streamlit Cloud no puede ver tu localhost). Opciones con capa
   gratuita: TiDB Cloud, Aiven, entre otras. Si exige SSL, define `ssl_ca`.
3. En https://share.streamlit.io → **New app** → elige repositorio, rama y `app.py`.
4. **Advanced settings → Secrets**: pega el contenido de `secrets.toml.example` con tus credenciales reales.
5. Deploy. Al abrir la app por primera vez se crean las tablas y se solicita el primer administrador.

## Pendiente (preparado, no implementado)
- **Iteración #2:** lecturas (HTTP/HTTPS o MQTT con ESP32), kWh, costos, dashboard energético, reportes PDF/Excel.
- **Iteración #3:** patrones, umbrales, alertas y notificaciones por correo.
