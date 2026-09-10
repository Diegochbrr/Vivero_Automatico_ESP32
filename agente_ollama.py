import os
import json
import ollama

# Nombre del modelo que tienes en Ollama (ej: qwen2.5:1.5b-instruct, llama3.1, etc.)
MODELO_OLLAMA = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b-instruct")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

cliente_ollama = ollama.Client(host=OLLAMA_HOST)

# -----------------------------------------------------------------------------
# FUNCIONES DE CONSULTA A TU BASE DE DATOS (POSTGRESQL / NEON)
# -----------------------------------------------------------------------------
def consultar_humedad_actual(id_sector: int = None) -> str:
    """
    Consulta la última lectura de humedad en los sectores del vivero.
    Úsala cuando pregunten por humedad, estado de las plantas o sensores.
    """
    from main_api_vivero import db_manager
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                if id_sector:
                    cur.execute("""
                        SELECT s.nombre_sector, s.tipo_cultivo, l.humedad_porcentaje, 
                               l.fecha_hora, u.humedad_min_on, u.humedad_max_off
                        FROM sectores s
                        LEFT JOIN LATERAL (
                            SELECT humedad_porcentaje, fecha_hora 
                            FROM lecturas_humedad 
                            WHERE id_sector = s.id_sector 
                            ORDER BY fecha_hora DESC LIMIT 1
                        ) l ON true
                        LEFT JOIN umbrales_configuracion u ON u.id_sector = s.id_sector
                        WHERE s.id_sector = %s;
                    """, (id_sector,))
                else:
                    cur.execute("""
                        SELECT s.id_sector, s.nombre_sector, s.tipo_cultivo, 
                               l.humedad_porcentaje, l.fecha_hora,
                               u.humedad_min_on, u.humedad_max_off
                        FROM sectores s
                        LEFT JOIN LATERAL (
                            SELECT humedad_porcentaje, fecha_hora 
                            FROM lecturas_humedad 
                            WHERE id_sector = s.id_sector 
                            ORDER BY fecha_hora DESC LIMIT 1
                        ) l ON true
                        LEFT JOIN umbrales_configuracion u ON u.id_sector = s.id_sector
                        ORDER BY s.id_sector ASC;
                    """)
                datos = cur.fetchall()
                return json.dumps(datos, default=str)
    except Exception as e:
        return f"Error en BD: {str(e)}"


def consultar_ultimos_riegos(limite: int = 3) -> str:
    """
    Consulta el historial de riegos realizados, duración y litros de agua usados.
    Úsala cuando pregunten cuándo regaron, cuánta agua se usó o sobre la bomba.
    """
    from main_api_vivero import db_manager
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.nombre_sector, r.duracion_segundos, 
                           r.volumen_litros_estimado, r.motivo, r.fecha_inicio
                    FROM eventos_riego r
                    JOIN sectores s ON r.id_sector = s.id_sector
                    ORDER BY r.fecha_inicio DESC LIMIT %s;
                """, (limite,))
                datos = cur.fetchall()
                return json.dumps(datos, default=str)
    except Exception as e:
        return f"Error en BD: {str(e)}"


def consultar_alertas_y_tanques() -> str:
    """
    Consulta si hay tanques vacíos, bombas bloqueadas o alertas críticas activas.
    """
    from main_api_vivero import db_manager
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.nombre_sector, a.nivel_detectado, a.bomba_bloqueada, 
                           a.observacion, a.fecha_hora
                    FROM alertas_nivel_agua a
                    JOIN sectores s ON a.id_sector = s.id_sector
                    ORDER BY a.fecha_hora DESC LIMIT 5;
                """)
                datos = cur.fetchall()
                return json.dumps(datos, default=str)
    except Exception as e:
        return f"Error en BD: {str(e)}"


def consultar_sectores_y_encargados() -> str:
    """
    Consulta los nombres de sectores, tipos de cultivo y datos del personal encargado.
    """
    from main_api_vivero import db_manager
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id_sector, nombre_sector, encargado_nombre, 
                           encargado_correo, encargado_rol, tipo_cultivo
                    FROM sectores;
                """)
                datos = cur.fetchall()
                return json.dumps(datos, default=str)
    except Exception as e:
        return f"Error en BD: {str(e)}"


# Mapeo de herramientas
HERRAMIENTAS_DISPONIBLES = {
    "consultar_humedad_actual": consultar_humedad_actual,
    "consultar_ultimos_riegos": consultar_ultimos_riegos,
    "consultar_alertas_y_tanques": consultar_alertas_y_tanques,
    "consultar_sectores_y_encargados": consultar_sectores_y_encargados,
}

SYSTEM_PROMPT = """
Eres el Asistente Virtual Inteligente del Vivero Automatizado "SmartVivero IoT" (Grupo 3).
Responde en español por WhatsApp. Usa negritas y emojis (🌱, 💧, ✅, ⚠️).
INTEGRANTES: Diego Charry (Admin S1: Orquídeas), Angel Villalobos (Agrónomo S2: Tomates), Adelfo Freyle (Operador S3: Semilleros), Juan Quintero (IoT S4), Juan Figueroa (S5).
HARDWARE: ESP32 DevKit V1, sensor humedad capacitivo (GPIO34), sensor boya agua (GPIO18), bomba (GPIO2).

REGLAS DE RESPUESTA:
- Sé conciso y ve al grano para WhatsApp. Si listas sectores, hazlo de forma breve o resumida.
- Concluye siempre tus oraciones completamente.
- Para preguntas sobre humedad de un sector, responde directamente con el valor actual reportado.
"""

def obtener_contexto_vivo_bd() -> str:
    """Extrae el estado actual completo de la BD para alimentar a Ollama."""
    from main_api_vivero import db_manager
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Humedades
                cur.execute("""
                    SELECT s.id_sector, s.nombre_sector, s.tipo_cultivo,
                           COALESCE(l.humedad_porcentaje, 0) as humedad,
                           COALESCE(u.humedad_min_on, 45) as hum_min,
                           COALESCE(u.humedad_max_off, 75) as hum_max
                    FROM sectores s
                    LEFT JOIN LATERAL (
                        SELECT humedad_porcentaje 
                        FROM lecturas_humedad 
                        WHERE id_sector = s.id_sector 
                        ORDER BY fecha_hora DESC LIMIT 1
                    ) l ON true
                    LEFT JOIN umbrales_configuracion u ON u.id_sector = s.id_sector
                    ORDER BY s.id_sector ASC;
                """)
                sectores = cur.fetchall()

                # 2. Último riego
                cur.execute("""
                    SELECT r.duracion_segundos, r.volumen_litros_estimado, r.fecha_inicio, s.nombre_sector
                    FROM eventos_riego r
                    JOIN sectores s ON r.id_sector = s.id_sector
                    ORDER BY r.fecha_inicio DESC LIMIT 1;
                """)
                ultimo_riego = cur.fetchone()

                # 3. Alertas
                cur.execute("""
                    SELECT a.nivel_detectado, a.bomba_bloqueada, s.nombre_sector
                    FROM alertas_nivel_agua a
                    JOIN sectores s ON a.id_sector = s.id_sector
                    ORDER BY a.fecha_hora DESC LIMIT 1;
                """)
                alerta = cur.fetchone()

        lineas = ["=== DATOS EN TIEMPO REAL DEL VIVERO (BASE DE DATOS) ==="]
        for sec in sectores:
            lineas.append(f"- Sector {sec['id_sector']} ({sec['nombre_sector']} - Cultivo: {sec['tipo_cultivo']}): Humedad actual = {sec['humedad']}%. (Rango óptimo: {sec['hum_min']}% a {sec['hum_max']}%)")
        
        if ultimo_riego:
            lineas.append(f"- Último riego: {ultimo_riego['nombre_sector']}, duración: {ultimo_riego['duracion_segundos']}s, volumen: {ultimo_riego['volumen_litros_estimado']}L, fecha: {ultimo_riego['fecha_inicio']}")
        else:
            lineas.append("- Último riego: No hay riegos recientes.")

        if alerta:
            lineas.append(f"- Estado de agua: Nivel {alerta['nivel_detectado']} en {alerta['nombre_sector']}. Bomba bloqueada: {alerta['bomba_bloqueada']}.")
        else:
            lineas.append("- Estado de agua: Normal (tanque lleno, bomba operativa).")

        return "\n".join(lineas)
    except Exception as e:
        return f"[Nota: Error consultando BD en vivo: {e}]"


# -----------------------------------------------------------------------------
# MEMORIA CONVERSACIONAL POR USUARIO (ÚLTIMOS MENSAJES)
# -----------------------------------------------------------------------------
_historial_conversaciones: dict = {}

def procesar_con_ollama(mensaje_usuario: str, user_id: str = "default") -> str:
    """
    Envía la pregunta a Ollama manteniendo memoria conversacional por usuario
    e inyectando el estado vivo de la base de datos para respuestas instantáneas.
    """
    try:
        # Obtener los datos frescos de la BD en cada mensaje
        datos_vivos_db = obtener_contexto_vivo_bd()
        prompt_completo = f"{SYSTEM_PROMPT}\n\n{datos_vivos_db}"

        # Inicializar o actualizar el historial del usuario
        if user_id not in _historial_conversaciones:
            _historial_conversaciones[user_id] = [
                {"role": "system", "content": prompt_completo}
            ]
        else:
            # Actualizar siempre el system prompt con los datos más frescos de la BD
            _historial_conversaciones[user_id][0] = {"role": "system", "content": prompt_completo}

        historial = _historial_conversaciones[user_id]

        # Mantener los últimos 8 turnos de conversación
        if len(historial) > 10:
            historial = [historial[0]] + historial[-8:]
            _historial_conversaciones[user_id] = historial

        # Agregar mensaje del usuario
        historial.append({"role": "user", "content": mensaje_usuario})

        # Ejecutar chat con Ollama de forma rápida
        response = cliente_ollama.chat(
            model=MODELO_OLLAMA,
            messages=historial,
            options={
                "num_predict": 220,
                "temperature": 0.2
            }
        )

        texto_respuesta = response.message.content

        # Guardar respuesta en memoria
        historial.append({"role": "assistant", "content": texto_respuesta})
        return texto_respuesta

    except Exception as e:
        print(f"[Error Ollama]: {e}")
        return f"Hola, tuve un inconveniente conectando con el sistema del vivero: {str(e)}"
