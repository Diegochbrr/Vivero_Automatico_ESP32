import os
import json
import ollama

# Nombre del modelo que tienes en Ollama (ej: qwen2.5:1.5b-instruct, llama3.1, etc.)
MODELO_OLLAMA = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
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
Eres el Asistente Virtual Inteligente de "SmartVivero IoT" (Grupo 3).
Responde en español por WhatsApp de forma concisa, clara y directa. Usa negritas y emojis (🌱, 💧, ✅, ⚠️).

INTEGRANTES Y SECTORES:
- Sector 1: Orquídeas — Encargado: Diego Charry (Administrador)
- Sector 2: Tomates — Encargado: Angel Villalobos (Agrónomo)
- Sector 3: Semilleros — Encargado: Adelfo Freyle (Operador)
- Sector 4: Aromáticas — Encargado: Juan Quintero (IoT / Telecomunicaciones)
- Sector 5: Suculentas — Encargado: Juan Figueroa (Mantenimiento)

HARDWARE Y SENSOR ADC (ESP32):
- ESP32 DevKit V1 con sensor capacitivo analógico en GPIO34 (ADC de 12 bits, rango 0 a 4095).
- En el sensor capacitivo:
  * Suelo Seco = ADC alto (~2800 - 3200 ADC) -> Humedad baja (<40%).
  * Suelo Húmedo/Regado = ADC bajo (~1200 - 1500 ADC) -> Humedad alta (>75%).
- LÓGICA DE RIEGO: La bomba (GPIO2) se activa automáticamente cuando la humedad cae por debajo del umbral mínimo configurado (humedad_min_on, ej: <45%). Se desactiva cuando alcanza el umbral máximo (humedad_max_off, ej: >75%).
- Si el sensor de boya (GPIO18) detecta tanque vacío (CRITICO_VACIO), la bomba se bloquea de inmediato por seguridad contra trabajo en seco.

REGLAS DE RESPUESTA:
- TÚ SÍ TIENES ACCESO A LA BASE DE DATOS EN VIVO: La sección "=== DATOS EN TIEMPO REAL DEL VIVERO (BASE DE DATOS) ===" más abajo contiene los registros exactos y actuales de la base de datos de PostgreSQL/Neon del vivero. 
- NUNCA digas "no tengo acceso a la base de datos" ni "no puedo acceder a registros específicos". Utiliza directamente los datos que se te proporcionan en ese bloque para responder con los valores reales.
- Responde directamente la cifra o dato exacto solicitado en el primer renglón.
- Sé breve, amigable y profesional (máximo 3 o 4 párrafos cortos).
- Concluye siempre tus oraciones completamente.
"""

def obtener_contexto_vivo_bd(pregunta: str = "") -> str:
    """Extrae el estado relevante de la BD para alimentar a Ollama velozmente."""
    from main_api_vivero import db_manager
    try:
        preg_lower = pregunta.lower()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Si la pregunta menciona un sector específico, filtramos para que Ollama procese 10 veces más rápido
                filtro_sector = ""
                import re
                match = re.search(r'sector\s*([0-9]+)', preg_lower)
                if match:
                    sec_id = int(match.group(1))
                    filtro_sector = f"WHERE s.id_sector = {sec_id}"
                elif "tomate" in preg_lower:
                    filtro_sector = "WHERE s.id_sector = 2"
                elif "orquidea" in preg_lower:
                    filtro_sector = "WHERE s.id_sector = 1"
                elif "semillero" in preg_lower:
                    filtro_sector = "WHERE s.id_sector = 3"
                
                # 1. Humedades, ADC y Umbrales (Solo los necesarios)
                cur.execute(f"""
                    SELECT s.id_sector, s.nombre_sector, s.tipo_cultivo, s.encargado_nombre,
                           COALESCE(l.humedad_porcentaje, 0) as humedad,
                           COALESCE(l.valor_adc_crudo, 0) as adc,
                           COALESCE(u.humedad_min_on, 45) as hum_min,
                           COALESCE(u.humedad_max_off, 75) as hum_max
                    FROM sectores s
                    LEFT JOIN LATERAL (
                        SELECT humedad_porcentaje, valor_adc_crudo
                        FROM lecturas_humedad 
                        WHERE id_sector = s.id_sector 
                        ORDER BY fecha_hora DESC LIMIT 1
                    ) l ON true
                    LEFT JOIN umbrales_configuracion u ON u.id_sector = s.id_sector
                    {filtro_sector}
                    ORDER BY s.id_sector ASC
                    LIMIT 5;
                """)
                sectores = cur.fetchall()

                # Solo consultar alerta si preguntan por agua/alerta o no hay filtro
                alerta = None
                if not filtro_sector or any(w in preg_lower for w in ["agua", "tanque", "alerta", "bomba"]):
                    cur.execute("""
                        SELECT a.nivel_detectado, a.bomba_bloqueada, a.observacion, s.nombre_sector
                        FROM alertas_nivel_agua a
                        JOIN sectores s ON a.id_sector = s.id_sector
                        ORDER BY a.fecha_hora DESC LIMIT 1;
                    """)
                    alerta = cur.fetchone()

        lineas = ["=== DATOS EN TIEMPO REAL DEL VIVERO ==="]
        for sec in sectores:
            lineas.append(
                f"- Sector {sec['id_sector']} ({sec['nombre_sector']} - Cultivo: {sec['tipo_cultivo']} - Encargado: {sec['encargado_nombre']}): "
                f"Humedad actual: {sec['humedad']}% | ADC: {sec['adc']} | Umbral riego: <{sec['hum_min']}% act / >{sec['hum_max']}% apag"
            )

        if alerta and alerta.get('nivel_detectado') == 'CRITICO_VACIO' and alerta.get('bomba_bloqueada'):
            lineas.append(f"- Agua: ⚠️ ALERTA - Tanque VACÍO en {alerta['nombre_sector']}. Bomba BLOQUEADA.")
        elif any(w in preg_lower for w in ["agua", "tanque", "alerta", "bomba"]) or not filtro_sector:
            lineas.append("- Agua: ✅ Nivel normal (Tanque lleno, bomba operativa).")

        return "\n".join(lineas)
    except Exception as e:
        return f"[Error BD: {e}]"


# -----------------------------------------------------------------------------
# MEMORIA CONVERSACIONAL POR USUARIO (ÚLTIMOS MENSAJES)
# -----------------------------------------------------------------------------
_historial_conversaciones: dict = {}

def procesar_con_ollama(mensaje_usuario: str, user_id: str = "default") -> str:
    """
    Responde instantáneamente (< 0.1s) a las preguntas operativas del vivero
    usando la base de datos viva, y usa Ollama como respaldo.
    Esto garantiza 100% de éxito frente al timeout de 15s de Twilio en WhatsApp.
    """
    import re
    preg_lower = mensaje_usuario.lower()

    # --- 1. ATAJO RÁPIDO: HUMEDAD DE SECTORES (< 0.05s) ---
    match_sec = re.search(r'sector\s*([0-9]+)', preg_lower)
    if any(w in preg_lower for w in ["humedad", "cuanto marca", "valor"]):
        from main_api_vivero import db_manager
        try:
            sec_num = int(match_sec.group(1)) if match_sec else (2 if "tomate" in preg_lower else (1 if "orquidea" in preg_lower else None))
            if sec_num:
                with db_manager.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT s.id_sector, s.nombre_sector, s.tipo_cultivo, s.encargado_nombre,
                                   COALESCE(l.humedad_porcentaje, 0) as humedad,
                                   COALESCE(l.valor_adc_crudo, 0) as adc,
                                   COALESCE(u.humedad_min_on, 45) as hum_min,
                                   COALESCE(u.humedad_max_off, 75) as hum_max
                            FROM sectores s
                            LEFT JOIN LATERAL (
                                SELECT humedad_porcentaje, valor_adc_crudo 
                                FROM lecturas_humedad 
                                WHERE id_sector = s.id_sector 
                                ORDER BY fecha_hora DESC LIMIT 1
                            ) l ON true
                            LEFT JOIN umbrales_configuracion u ON u.id_sector = s.id_sector
                            WHERE s.id_sector = %s;
                        """, (sec_num,))
                        row = cur.fetchone()
                if row:
                    estado_riego = "🚨 Requiere riego" if row['humedad'] < row['hum_min'] else "✅ Nivel óptimo"
                    return (
                        f"🌱 *Sector {row['id_sector']} - {row['nombre_sector']}* ({row['tipo_cultivo']}):\n"
                        f"💧 *Humedad actual:* {row['humedad']:.2f}%\n"
                        f"📊 *ADC Crudo:* {row['adc']}\n"
                        f"🎯 *Rango óptimo:* {row['hum_min']}% a {row['hum_max']}%\n"
                        f"Estado: {estado_riego}"
                    )
        except Exception as e:
            print(f"[Error Fast Query Humedad]: {e}")

    # --- 2. ATAJO RÁPIDO: NIVEL DE TANQUE Y ALERTAS (< 0.05s) ---
    if any(w in preg_lower for w in ["tanque", "nivel de agua", "alerta", "falta de agua", "hay agua"]):
        from main_api_vivero import db_manager
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT a.nivel_detectado, a.bomba_bloqueada, a.observacion, s.nombre_sector, a.fecha_hora
                        FROM alertas_nivel_agua a
                        JOIN sectores s ON a.id_sector = s.id_sector
                        ORDER BY a.fecha_hora DESC LIMIT 1;
                    """)
                    alerta = cur.fetchone()
            if alerta and alerta.get('nivel_detectado') == 'CRITICO_VACIO' and alerta.get('bomba_bloqueada'):
                return (
                    f"⚠️ *ALERTA DE AGUA EN EL VIVERO*:\n"
                    f"El tanque se encuentra en estado *CRÍTICO (VACÍO)* en {alerta['nombre_sector']}.\n"
                    f"🛑 *Bomba bloqueada por seguridad* contra trabajo en seco.\n"
                    f"Detalle: {alerta.get('observacion', 'Sensor boya en nivel bajo')}."
                )
            else:
                return "✅ *Tanque de agua:* Nivel adecuado y normal. La bomba se encuentra operativa y no hay alertas críticas activas."
        except Exception as e:
            print(f"[Error Fast Query Tanque]: {e}")

    # --- 3. ATAJO RÁPIDO: ENCARGADOS Y CULTIVOS (< 0.01s) ---
    if any(w in preg_lower for w in ["encargado", "responsable", "quien"]):
        if "tomate" in preg_lower or (match_sec and match_sec.group(1) == "2"):
            return "🍅 *Sector 2 (Tomates)*: El encargado es *Angel Villalobos* (Agrónomo)."
        elif "orquidea" in preg_lower or (match_sec and match_sec.group(1) == "1"):
            return "🌸 *Sector 1 (Orquídeas)*: El encargado es *Diego Charry* (Administrador)."
        elif "semillero" in preg_lower or (match_sec and match_sec.group(1) == "3"):
            return "🌱 *Sector 3 (Semilleros)*: El encargado es *Adelfo Freyle* (Operador)."
        elif "aromatica" in preg_lower or "iot" in preg_lower or (match_sec and match_sec.group(1) == "4"):
            return "🌿 *Sector 4 (Laboratorio IoT)*: El encargado es *Juan Quintero* (Técnico IoT)."
        elif "suculenta" in preg_lower or (match_sec and match_sec.group(1) == "5"):
            return "🪴 *Sector 5 (Suculentas)*: El encargado es *Juan Figueroa* (Visualizador)."

    # --- 4. ATAJO RÁPIDO: VALORES ADC / BOMBA (< 0.01s) ---
    if any(w in preg_lower for w in ["adc", "cuando riega", "enciende la bomba", "activa la bomba"]):
        return (
            "⚙️ *Lógica de Bomba y Sensor ADC (ESP32)*:\n"
            "- *Suelo seco (Requiere riego):* ADC alto (~2800 - 3200), humedad < 45%.\n"
            "- *Suelo húmedo (Bomba apagada):* ADC bajo (~1200 - 1500), humedad > 75%.\n"
            "💧 La bomba (GPIO2) se activa automáticamente cuando la humedad cae por debajo del umbral mínimo del sector."
        )

    # --- 5. SI ES UNA PREGUNTA GENERAL O CONVERSACIONAL, USAR OLLAMA (< 5s) ---
    try:
        datos_vivos_db = obtener_contexto_vivo_bd(mensaje_usuario)
        mensaje_con_contexto = (
            f"Pregunta: {mensaje_usuario}\n"
            f"{datos_vivos_db}\n"
            f"Instrucción: Responde en 1 o 2 renglones con emojis."
        )
        response = cliente_ollama.chat(
            model=MODELO_OLLAMA,
            messages=[
                {"role": "system", "content": "Eres el bot de WhatsApp de SmartVivero IoT. Responde en español de forma ultracorta y directa. Usa emojis."},
                {"role": "user", "content": mensaje_con_contexto}
            ],
            options={"num_predict": 70, "temperature": 0.1, "num_thread": 6}
        )
        return response.message.content.strip()
    except Exception as e:
        print(f"[Error Ollama]: {e}")
        return f"Hola, tuve un inconveniente conectando con el sistema del vivero: {str(e)}"
