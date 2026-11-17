"""Constantes de dominio (sin dependencias externas, fáciles de probar)."""

ADMIN = "ADMINISTRADOR"
TECNICO = "TECNICO_IOT"
ANALISTA = "ANALISTA_ENERGETICO"

ROLES = [ADMIN, TECNICO, ANALISTA]
ROL_LABELS = {
    ADMIN: "Administrador",
    TECNICO: "Técnico IoT",
    ANALISTA: "Analista energético",
}

ESTADOS_GENERALES = ["activo", "inactivo"]
ESTADOS_SENSOR = ["activo", "inactivo", "sin_conexion"]
ESTADO_SENSOR_ICON = {"activo": "🟢 Activo", "inactivo": "⚪ Inactivo", "sin_conexion": "🔴 Sin conexión"}

TIPOS_NEGOCIO = ["Restaurante", "Cafetería", "Peluquería", "Tienda", "Taller", "Oficina", "Otro"]
TIPOS_EQUIPO = ["Refrigeración", "Iluminación", "Climatización", "Cocina", "Cómputo", "Maquinaria", "Otro"]
TIPOS_SENSOR = ["Corriente (CT)", "Voltaje", "Potencia/Energía", "Temperatura", "Multifunción"]

PREFIJO_DEMO = "[DEMO]"
