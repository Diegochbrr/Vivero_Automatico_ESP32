"""
API REST con Arquitectura POO en Python para el Sistema de Riego Autónomo
Conexión directa y optimizada (Connection Pooling) a PostgreSQL en Neon Cloud
Incluye generador de telemetría IoT en segundo plano para operar sin depender de Wokwi externo.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status, Security, Depends
from fastapi.security.api_key import APIKeyHeader
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import uvicorn

# Cargar variables del entorno desde el archivo .env
load_dotenv()

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD (API KEY)
# =============================================================================
API_KEY = os.environ.get("API_KEY", "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d")
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=True)

def get_api_key(api_key_header: str = Security(api_key_header_scheme)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acceso Denegado. API Key inválida o faltante.",
    )

# =============================================================================
# MODELOS PYDANTIC (DTOs)
# =============================================================================

class LecturaHumedadCreate(BaseModel):
    id_sensor: str = Field(..., example="SEN-CAP-S01")
    id_sector: int = Field(..., example=1)
    humedad_porcentaje: float = Field(..., ge=0.0, le=100.0, example=42.5)
    valor_adc_crudo: int = Field(..., ge=0, le=4095, example=2450)

class EventoRiegoCreate(BaseModel):
    id_actuador: str = Field(..., example="REL-BOM-01")
    id_sector: int = Field(..., example=1)
    duracion_segundos: int = Field(..., gt=0, example=180)
    volumen_litros_estimado: float = Field(..., ge=0.0, example=15.0)
    motivo: Optional[str] = Field(default="AUTOMATICO_UMBRAL")

class AlertaNivelAguaCreate(BaseModel):
    id_sector: int = Field(..., example=1)
    nivel_detectado: str = Field(..., example="CRITICO_VACIO")
    bomba_bloqueada: bool = Field(default=True)
    observacion: Optional[str] = Field(default="Interlock de seguridad activado por switch")

class UmbralUpdate(BaseModel):
    humedad_min_on: float = Field(..., ge=0.0, le=100.0, example=45.0)
    humedad_max_off: float = Field(..., ge=0.0, le=100.0, example=75.0)
    tiempo_max_riego_seg: int = Field(..., gt=0, example=180)
    id_usuario_modifica: int = Field(..., example=1)


# Estado en memoria de comandos pendientes por sector (no requiere tabla extra en BD)
# { id_sector: {"forzar_riego": bool, "duracion_seg": int} }
_comandos_pendientes: Dict[int, Dict[str, Any]] = {}


# =============================================================================
# CAPA DE PERSISTENCIA Y REPOSITORIO (POO CON CONNECTION POOLING)
# =============================================================================

class DatabaseManager:
    """Clase gestora con Connection Pooling persistente para Neon PostgreSQL."""
    def __init__(self, connection_url: Optional[str] = None):
        if connection_url:
            self.connection_url = connection_url
        elif os.getenv("DATABASE_URL"):
            self.connection_url = os.getenv("DATABASE_URL")
        elif os.getenv("NEON_DATABASE_URL"):
            self.connection_url = os.getenv("NEON_DATABASE_URL")
        else:
            user = os.getenv("DB_USER", "neondb_owner")
            password = os.getenv("DB_PASSWORD", "")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            dbname = os.getenv("DB_NAME", "neondb")
            self.connection_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"

        self.pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.connection_url,
            cursor_factory=RealDictCursor
        )

    @contextmanager
    def get_connection(self):
        """Context manager que presta una conexión del pool y la devuelve al terminar."""
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error en base de datos Neon PostgreSQL: {str(e)}"
            )
        finally:
            if conn:
                self.pool.putconn(conn)


class ViveroRepository:
    """Repositorio con operaciones CRUD sobre las entidades del Vivero."""
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    # --- LECTURAS HUMEDAD ---
    def insert_lectura(self, lectura: LecturaHumedadCreate) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO lecturas_humedad (id_sensor, id_sector, humedad_porcentaje, valor_adc_crudo)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id_lectura, id_sensor, id_sector, humedad_porcentaje, valor_adc_crudo, fecha_hora;
                """
                cur.execute(query, (lectura.id_sensor, lectura.id_sector, lectura.humedad_porcentaje, lectura.valor_adc_crudo))
                result = cur.fetchone()
                conn.commit()
                return dict(result)

    def get_lecturas_by_sector(self, id_sector: int, limit: int = 50) -> List[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT * FROM lecturas_humedad 
                    WHERE id_sector = %s 
                    ORDER BY fecha_hora DESC 
                    LIMIT %s;
                """
                cur.execute(query, (id_sector, limit))
                return [dict(row) for row in cur.fetchall()]

    def delete_lectura(self, id_lectura: int) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM lecturas_humedad WHERE id_lectura = %s RETURNING *;",
                    (id_lectura,)
                )
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail=f"Medición con id {id_lectura} no encontrada")
                conn.commit()
                return dict(result)

    # --- EVENTOS DE RIEGO ---
    def insert_evento_riego(self, evento: EventoRiegoCreate) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO eventos_riego (id_actuador, id_sector, fecha_inicio, fecha_fin, duracion_segundos, volumen_litros_estimado, motivo)
                    VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + (%s ||' seconds')::INTERVAL, %s, %s, %s)
                    RETURNING *;
                """
                cur.execute(query, (evento.id_actuador, evento.id_sector, evento.duracion_segundos, evento.duracion_segundos, evento.volumen_litros_estimado, evento.motivo))
                result = cur.fetchone()
                conn.commit()
                return dict(result)

    def get_eventos_riego(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM eventos_riego ORDER BY fecha_inicio DESC LIMIT %s;", (limit,))
                return [dict(row) for row in cur.fetchall()]

    def delete_evento_riego(self, id_evento: int) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM eventos_riego WHERE id_evento = %s RETURNING *;",
                    (id_evento,)
                )
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail=f"Evento de riego con id {id_evento} no encontrado")
                conn.commit()
                return dict(result)

    # --- ALERTAS NIVEL DE AGUA ---
    def insert_alerta(self, alerta: AlertaNivelAguaCreate) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO alertas_nivel_agua (id_sector, nivel_detectado, bomba_bloqueada, observacion)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *;
                """
                cur.execute(query, (alerta.id_sector, alerta.nivel_detectado, alerta.bomba_bloqueada, alerta.observacion))
                result = cur.fetchone()
                conn.commit()
                return dict(result)

    def get_alertas_recientes(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM alertas_nivel_agua ORDER BY fecha_hora DESC LIMIT %s;", (limit,))
                return [dict(row) for row in cur.fetchall()]

    def delete_alerta(self, id_alerta: int) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM alertas_nivel_agua WHERE id_alerta = %s RETURNING *;",
                    (id_alerta,)
                )
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail=f"Alerta con id {id_alerta} no encontrada")
                conn.commit()
                return dict(result)

    # --- CONFIGURACIÓN & UMBRALES ---
    def get_umbral_by_sector(self, id_sector: int) -> Optional[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM umbrales_configuracion WHERE id_sector = %s;", (id_sector,))
                result = cur.fetchone()
                return dict(result) if result else None

    def update_umbral(self, id_sector: int, umbral: UmbralUpdate) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    UPDATE umbrales_configuracion
                    SET humedad_min_on = %s, humedad_max_off = %s, tiempo_max_riego_seg = %s, id_usuario_modifica = %s, actualizado_en = CURRENT_TIMESTAMP
                    WHERE id_sector = %s
                    RETURNING *;
                """
                cur.execute(query, (umbral.humedad_min_on, umbral.humedad_max_off, umbral.tiempo_max_riego_seg, umbral.id_usuario_modifica, id_sector))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail=f"No se encontró umbral para el sector {id_sector}")
                conn.commit()
                return dict(result)

    # --- COMANDOS ESP32 (en memoria, patrón polling) ---
    def get_config_esp32(self, id_sector: int) -> Dict[str, Any]:
        """Devuelve al ESP32 su configuración activa + si hay un comando de riego forzado pendiente."""
        umbral = self.get_umbral_by_sector(id_sector)
        if not umbral:
            raise HTTPException(status_code=404, detail=f"No existe configuración para el sector {id_sector}")
        cmd = _comandos_pendientes.get(id_sector, {})
        return {
            "humedad_min_on": float(umbral["humedad_min_on"]),
            "humedad_max_off": float(umbral["humedad_max_off"]),
            "tiempo_max_riego_seg": int(umbral["tiempo_max_riego_seg"]),
            "forzar_riego": cmd.get("forzar_riego", False),
            "duracion_forzado_seg": cmd.get("duracion_seg", 30),
        }

    def set_forzar_riego(self, id_sector: int, duracion_seg: int) -> Dict[str, Any]:
        """Registra un comando de riego forzado pendiente para que el ESP32 lo consuma."""
        _comandos_pendientes[id_sector] = {"forzar_riego": True, "duracion_seg": duracion_seg}
        return {"mensaje": f"Comando forzar riego registrado para sector {id_sector}", "duracion_seg": duracion_seg}

    def clear_forzar_riego(self, id_sector: int) -> Dict[str, Any]:
        """El ESP32 llama a este endpoint para confirmar que ejecutó el riego forzado y limpia el flag."""
        _comandos_pendientes.pop(id_sector, None)
        return {"mensaje": f"Comando de riego forzado limpiado para sector {id_sector}"}


# =============================================================================
# CONTROLADOR Y APLICACIÓN FASTAPI
# =============================================================================

db_manager = DatabaseManager()
repository = ViveroRepository(db_manager)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="API Sistema de Riego Autónomo para Vivero",
    description="Servicios CRUD RESTful en Python (POO) integrados con Neon PostgreSQL",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint Raíz y Diagnóstico
@app.get("/", tags=["Salud y Diagnóstico"])
def root():
    return {
        "status": "online",
        "proyecto": "SmartVivero API",
        "docs_url": "/docs",
        "timestamp": datetime.utcnow()
    }

# Endpoint de Salud
@app.get("/health", tags=["Salud y Diagnóstico"])
def health_check():
    return {"status": "online", "database": "Neon Serverless PostgreSQL", "timestamp": datetime.utcnow()}

# Endpoints de Lecturas (Usados por ESP32 y Desktop App)
@app.post("/api/v1/mediciones", status_code=status.HTTP_201_CREATED, tags=["Telemetría ESP32"], dependencies=[Depends(get_api_key)])
def registrar_medicion(lectura: LecturaHumedadCreate):
    return repository.insert_lectura(lectura)

@app.get("/api/v1/mediciones/sector/{id_sector}", tags=["Telemetría ESP32"], dependencies=[Depends(get_api_key)])
def consultar_mediciones_sector(id_sector: int, limit: int = 50):
    return repository.get_lecturas_by_sector(id_sector, limit)

@app.delete("/api/v1/mediciones/{id_lectura}", tags=["Telemetría ESP32"], dependencies=[Depends(get_api_key)])
def eliminar_medicion(id_lectura: int):
    return repository.delete_lectura(id_lectura)

# Endpoints de Riego
@app.post("/api/v1/riego/evento", status_code=status.HTTP_201_CREATED, tags=["Control de Riego"], dependencies=[Depends(get_api_key)])
def registrar_evento_riego(evento: EventoRiegoCreate):
    return repository.insert_evento_riego(evento)

@app.get("/api/v1/riego/eventos", tags=["Control de Riego"], dependencies=[Depends(get_api_key)])
def listar_eventos_riego(limit: int = 20):
    return repository.get_eventos_riego(limit)

@app.delete("/api/v1/riego/evento/{id_evento}", tags=["Control de Riego"], dependencies=[Depends(get_api_key)])
def eliminar_evento_riego(id_evento: int):
    return repository.delete_evento_riego(id_evento)

# Endpoints de Alertas de Nivel de Agua
@app.post("/api/v1/alertas", status_code=status.HTTP_201_CREATED, tags=["Alertas & Seguridad"], dependencies=[Depends(get_api_key)])
def registrar_alerta(alerta: AlertaNivelAguaCreate):
    return repository.insert_alerta(alerta)

@app.get("/api/v1/alertas", tags=["Alertas & Seguridad"], dependencies=[Depends(get_api_key)])
def listar_alertas(limit: int = 20):
    return repository.get_alertas_recientes(limit)

@app.delete("/api/v1/alertas/{id_alerta}", tags=["Alertas & Seguridad"], dependencies=[Depends(get_api_key)])
def eliminar_alerta(id_alerta: int):
    return repository.delete_alerta(id_alerta)

# Endpoints de Umbrales de Riego
@app.get("/api/v1/umbrales/{id_sector}", tags=["Configuración"], dependencies=[Depends(get_api_key)])
def consultar_umbral(id_sector: int):
    umbral = repository.get_umbral_by_sector(id_sector)
    if not umbral:
        raise HTTPException(status_code=404, detail="Umbral no encontrado para el sector especificado")
    return umbral

@app.put("/api/v1/umbrales/{id_sector}", tags=["Configuración"], dependencies=[Depends(get_api_key)])
def actualizar_umbral(id_sector: int, umbral: UmbralUpdate):
    return repository.update_umbral(id_sector, umbral)


# =============================================================================
# ENDPOINTS DE COMANDOS PARA EL ESP32 (POLLING PATTERN)
# =============================================================================

@app.get("/api/v1/comandos/{id_sector}",
         tags=["Comandos ESP32"],
         summary="Polling de configuración y comandos pendientes",
         description="El ESP32 llama a este endpoint cada ciclo para obtener su umbral activo y si hay riego forzado pendiente.")
def polling_comandos(id_sector: int, api_key: str = Depends(get_api_key)):
    return repository.get_config_esp32(id_sector)


@app.post("/api/v1/comandos/forzar-riego/{id_sector}",
          status_code=status.HTTP_200_OK,
          tags=["Comandos ESP32"],
          summary="Forzar riego desde la app de escritorio",
          dependencies=[Depends(get_api_key)])
def forzar_riego(id_sector: int, duracion_seg: int = 30):
    return repository.set_forzar_riego(id_sector, duracion_seg)


@app.delete("/api/v1/comandos/forzar-riego/{id_sector}",
            tags=["Comandos ESP32"],
            summary="Confirmar ejecución de riego forzado (llamado por el ESP32)",
            dependencies=[Depends(get_api_key)])
def confirmar_riego_forzado(id_sector: int):
    return repository.clear_forzar_riego(id_sector)


if __name__ == "__main__":
    uvicorn.run("main_api_vivero:app", host="0.0.0.0", port=8000, reload=True)