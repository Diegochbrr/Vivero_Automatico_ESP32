"""
Agente Inteligente Ollama para el Vivero Autónomo (Versión Cliente API REST).
A diferencia de agente_ollama.py (que se conecta directo a PostgreSQL), este módulo
consume exclusivamente los endpoints HTTP de la API REST (FastAPI) mediante peticiones HTTP.
"""

import os
import json
import ollama
from typing import Optional, Dict, Any, List

# Cargar variables de entorno si python-dotenv está disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
# URL base de la API REST del Vivero (local o remota en Render)
VIVERO_API_URL = os.getenv("VIVERO_API_URL", "http://localhost:8000/api/v1").rstrip("/")
API_KEY = os.getenv("API_KEY", "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d")

# Configuración del modelo Ollama
MODELO_OLLAMA = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b-instruct")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

cliente_ollama = ollama.Client(host=OLLAMA_HOST)


# =============================================================================
# CLIENTE HTTP RESILIENTE (soporta 'requests' o módulo estándar 'urllib')
# =============================================================================
def _hacer_peticion_api(metodo: str, ruta: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Any:
    """
    Ejecuta una petición HTTP a la API REST del vivero con el encabezado de autenticación X-API-Key.
    Compatible tanto con la librería 'requests' como con 'urllib' nativa de Python.
    """
    url_completa = f"{VIVERO_API_URL}{ruta}"
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        import requests
        resp = requests.request(
            method=metodo,
            url=url_completa,
            params=params,
            json=body,
            headers=headers,
            timeout=6
        )
        if resp.status_code in (200, 201):
            return resp.json()
        elif resp.status_code == 404:
            return None
        else:
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except ImportError:
        # Fallback a urllib nativo de la biblioteca estándar
        import urllib.request
        import urllib.parse
        import urllib.error

        query_str = f"?{urllib.parse.urlencode(params)}" if params else ""
        req = urllib.request.Request(f"{url_completa}{query_str}", headers=headers, method=metodo)
        data_bytes = json.dumps(body).encode("utf-8") if body else None

        try:
            with urllib.request.urlopen(req, data=data_bytes, timeout=6) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": f"Error de red hacia la API: {str(e)}"}
    except Exception as e:
        return {"error": f"Error conectando a la API ({url_completa}): {str(e)}"}


# -----------------------------------------------------------------------------
# FUNCIONES DE CONSULTA A LA API REST
# -----------------------------------------------------------------------------
def consultar_sectores_y_encargados() -> str:
    """
    Consulta a la API REST la lista de sectores, encargados y cultivos.
    Endpoint: GET /sectores
    """
    data = _hacer_peticion_api("GET", "/sectores")
    if isinstance(data, dict) and "error" in data:
        return f"Error consultando API: {data['error']}"
    return json.dumps(data or [], default=str)


def consultar_humedad_actual(id_sector: Optional[int] = None) -> str:
    """
    Consulta la última lectura de humedad y los umbrales configurados para uno o todos los sectores.
    Endpoints: GET /sectores, GET /mediciones/sector/{id_sector}, GET /umbrales/{id_sector}
    """
    try:
        sectores = _hacer_peticion_api("GET", "/sectores")
        if not isinstance(sectores, list):
            return "No se pudieron obtener los sectores de la API."

        resultado = []
        for sec in sectores:
            s_id = sec.get("id_sector")
            if id_sector and s_id != id_sector:
                continue

            # Obtener última medición del sector
            mediciones = _hacer_peticion_api("GET", f"/mediciones/sector/{s_id}", params={"limit": 1})
            ultima_medicion = mediciones[0] if (isinstance(mediciones, list) and len(mediciones) > 0) else {}

            # Obtener umbral de riego del sector
            umbral = _hacer_peticion_api("GET", f"/umbrales/{s_id}") or {}

            resultado.append({
                "id_sector": s_id,
                "nombre_sector": sec.get("nombre_sector"),
                "tipo_cultivo": sec.get("tipo_cultivo"),
                "humedad_porcentaje": ultima_medicion.get("humedad_porcentaje"),
                "fecha_hora": ultima_medicion.get("fecha_hora"),
                "humedad_min_on": umbral.get("humedad_min_on", 45),
                "humedad_max_off": umbral.get("humedad_max_off", 75)
            })

        return json.dumps(resultado, default=str)
    except Exception as e:
        return f"Error al consultar humedad vía API: {str(e)}"


def consultar_ultimos_riegos(limite: int = 3) -> str:
    """
    Consulta el historial de eventos de riego registrados.
    Endpoint: GET /riego/eventos
    """
    data = _hacer_peticion_api("GET", "/riego/eventos", params={"limit": limite})
    if isinstance(data, dict) and "error" in data:
        return f"Error consultando API: {data['error']}"
    return json.dumps(data or [], default=str)


def consultar_alertas_y_tanques() -> str:
    """
    Consulta las alertas recientes de nivel de agua y bombas bloqueadas.
    Endpoint: GET /alertas
    """
    data = _hacer_peticion_api("GET", "/alertas", params={"limit": 5})
    if isinstance(data, dict) and "error" in data:
        return f"Error consultando API: {data['error']}"
    return json.dumps(data or [], default=str)


def consultar_estado_dispositivos() -> str:
    """
    Consulta el estado de conexión y último ping (heartbeat) de los nodos ESP32.
    Endpoint: GET /sistema/dispositivos
    """
    data = _hacer_peticion_api("GET", "/sistema/dispositivos")
    if isinstance(data, dict) and "error" in data:
        return f"Error consultando API: {data['error']}"
    return json.dumps(data or [], default=str)


def forzar_riego_sector(id_sector: int, duracion_seg: int = 30) -> str:
    """
    Envía una orden a la API REST para forzar el riego en un sector específico.
    Endpoint: POST /comandos/forzar-riego/{id_sector}
    """
    data = _hacer_peticion_api("POST", f"/comandos/forzar-riego/{id_sector}", params={"duracion_seg": duracion_seg})
    return json.dumps(data or {}, default=str)


# Mapeo de herramientas disponibles
HERRAMIENTAS_DISPONIBLES = {
    "consultar_humedad_actual": consultar_humedad_actual,
    "consultar_ultimos_riegos": consultar_ultimos_riegos,
    "consultar_alertas_y_tanques": consultar_alertas_y_tanques,
    "consultar_sectores_y_encargados": consultar_sectores_y_encargados,
    "consultar_estado_dispositivos": consultar_estado_dispositivos,
    "forzar_riego_sector": forzar_riego_sector,
}

SYSTEM_PROMPT = """
Eres el Asistente Virtual Inteligente del Vivero Automatizado "SmartVivero IoT" (Grupo 3).
Obtienes la información en tiempo real a través de la API REST del sistema.
Responde en español de forma amigable para WhatsApp. Usa negritas y emojis (🌱, 💧, ✅, ⚠️).
INTEGRANTES: Diego Charry (Admin S1: Orquídeas), Angel Villalobos (Agrónomo S2: Tomates), Adelfo Freyle (Operador S3: Semilleros), Juan Quintero (IoT S4), Juan Figueroa (S5).
HARDWARE: ESP32 DevKit V1, sensor humedad capacitivo (GPIO34), sensor boya agua (GPIO18), bomba (GPIO2).

REGLAS DE RESPUESTA:
- Sé conciso y ve directo al grano para WhatsApp.
- Concluye siempre tus oraciones completamente.
- Para preguntas sobre humedad de un sector, responde directamente con el valor actual reportado y su rango óptimo.
"""

def _obtener_info_sector(sec: dict) -> dict:
    """Helper concurrente para obtener medicion y umbral de un sector."""
    s_id = sec.get("id_sector")
    mediciones = _hacer_peticion_api("GET", f"/mediciones/sector/{s_id}", params={"limit": 1})
    umbral = _hacer_peticion_api("GET", f"/umbrales/{s_id}") or {}
    hum_act = 0.0
    fecha_h = None
    if isinstance(mediciones, list) and len(mediciones) > 0:
        hum_act = mediciones[0].get("humedad_porcentaje", 0.0)
        fecha_h = mediciones[0].get("fecha_hora")

    return {
        "id_sector": s_id,
        "nombre_sector": sec.get("nombre_sector"),
        "tipo_cultivo": sec.get("tipo_cultivo"),
        "humedad_porcentaje": hum_act,
        "fecha_hora": fecha_h,
        "humedad_min_on": umbral.get("humedad_min_on", 45),
        "humedad_max_off": umbral.get("humedad_max_off", 75)
    }

def obtener_contexto_vivo_api() -> str:
    """
    Extrae el estado actual del vivero consultando los endpoints de la API REST
    en paralelo para alimentar al modelo Ollama con contexto fresco de forma ultrarrápida.
    """
    from concurrent.futures import ThreadPoolExecutor
    try:
        # 1. Obtener Sectores
        sectores = _hacer_peticion_api("GET", "/sectores") or []
        if isinstance(sectores, dict) and "error" in sectores:
            return f"[Nota: No fue posible conectar con la API del vivero en {VIVERO_API_URL}: {sectores['error']}]"

        lineas = ["=== DATOS EN TIEMPO REAL DEL VIVERO (VÍA API REST) ==="]

        # 2. Consultar todos los sectores en paralelo
        with ThreadPoolExecutor(max_workers=8) as executor:
            detalles_sectores = list(executor.map(_obtener_info_sector, sectores))

        for sec in detalles_sectores:
            lineas.append(
                f"- Sector {sec['id_sector']} ({sec['nombre_sector']} - Cultivo: {sec['tipo_cultivo']}): "
                f"Humedad actual = {sec['humedad_porcentaje']}%. (Rango óptimo: {sec['humedad_min_on']}% a {sec['humedad_max_off']}%)"
            )

        # 3. Último riego
        riegos = _hacer_peticion_api("GET", "/riego/eventos", params={"limit": 1})
        if isinstance(riegos, list) and len(riegos) > 0:
            r = riegos[0]
            lineas.append(
                f"- Último riego: Sector {r.get('id_sector')}, duración: {r.get('duracion_segundos')}s, "
                f"volumen: {r.get('volumen_litros_estimado')}L, fecha: {r.get('fecha_inicio')}"
            )
        else:
            lineas.append("- Último riego: No hay riegos recientes.")

        # 4. Alertas de agua
        alertas = _hacer_peticion_api("GET", "/alertas", params={"limit": 1})
        if isinstance(alertas, list) and len(alertas) > 0:
            a = alertas[0]
            lineas.append(
                f"- Estado de agua: Nivel {a.get('nivel_detectado')} en Sector {a.get('id_sector')}. "
                f"Bomba bloqueada: {a.get('bomba_bloqueada')}."
            )
        else:
            lineas.append("- Estado de agua: Normal (tanque con agua, bomba operativa).")

        return "\n".join(lineas)
    except Exception as e:
        return f"[Nota: Error consultando la API en vivo: {e}]"


# -----------------------------------------------------------------------------
# MEMORIA CONVERSACIONAL POR USUARIO
# -----------------------------------------------------------------------------
_historial_conversaciones: dict = {}

def procesar_con_ollama(mensaje_usuario: str, user_id: str = "default") -> str:
    """
    Envía la pregunta a Ollama manteniendo memoria conversacional por usuario
    e inyectando el estado vivo recuperado a través de las llamadas a la API REST.
    """
    try:
        # Obtener los datos frescos de la API en cada mensaje
        datos_vivos_api = obtener_contexto_vivo_api()
        prompt_completo = f"{SYSTEM_PROMPT}\n\n{datos_vivos_api}"

        # Inicializar o actualizar el historial del usuario
        if user_id not in _historial_conversaciones:
            _historial_conversaciones[user_id] = [
                {"role": "system", "content": prompt_completo}
            ]
        else:
            # Actualizar siempre el system prompt con los datos más frescos de la API
            _historial_conversaciones[user_id][0] = {"role": "system", "content": prompt_completo}

        historial = _historial_conversaciones[user_id]

        # Mantener los últimos 8 turnos de conversación
        if len(historial) > 10:
            historial = [historial[0]] + historial[-8:]
            _historial_conversaciones[user_id] = historial

        # Agregar mensaje del usuario
        historial.append({"role": "user", "content": mensaje_usuario})

        # Ejecutar chat con Ollama
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
        print(f"[Error Ollama API Agent]: {e}")
        return f"Hola, tuve un inconveniente conectando con el sistema del vivero: {str(e)}"


# -----------------------------------------------------------------------------
# PRUEBA RÁPIDA EN CONSOLA (CLI)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"--- Probando Agente Ollama con API REST ({VIVERO_API_URL}) ---")
    print("\n[1] Consultando contexto en vivo desde la API...")
    contexto = obtener_contexto_vivo_api()
    print(contexto)

    pregunta_demo = "¿Cómo está la humedad en el vivero y qué cultivo hay en el sector 1?"
    print(f"\n[2] Enviando pregunta de prueba: '{pregunta_demo}'")
    try:
        respuesta = procesar_con_ollama(pregunta_demo)
        print(f"\n[Respuesta Ollama]:\n{respuesta}")
    except Exception as err:
        print(f"Nota: Ollama no respondió (asegúrate de tener 'ollama serve' ejecutándose): {err}")
