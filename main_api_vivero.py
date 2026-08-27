"""
API REST con Arquitectura POO en Python para el Sistema de Riego Autónomo
Conexión directa y optimizada (Connection Pooling) a PostgreSQL en Neon Cloud
Incluye generador de telemetría IoT en segundo plano para operar sin depender de Wokwi externo.
"""

import os
import threading
import time
import random
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import uvicorn

# Cargar variables del entorno desde el archivo .env
load_dotenv()

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
@app.post("/api/v1/mediciones", status_code=status.HTTP_201_CREATED, tags=["Telemetría ESP32"])
def registrar_medicion(lectura: LecturaHumedadCreate):
    return repository.insert_lectura(lectura)

@app.get("/api/v1/mediciones/sector/{id_sector}", tags=["Telemetría ESP32"])
def consultar_mediciones_sector(id_sector: int, limit: int = 50):
    return repository.get_lecturas_by_sector(id_sector, limit)

# Endpoints de Riego
@app.post("/api/v1/riego/evento", status_code=status.HTTP_201_CREATED, tags=["Control de Riego"])
def registrar_evento_riego(evento: EventoRiegoCreate):
    return repository.insert_evento_riego(evento)

@app.get("/api/v1/riego/eventos", tags=["Control de Riego"])
def listar_eventos_riego(limit: int = 20):
    return repository.get_eventos_riego(limit)

# Endpoints de Alertas de Nivel de Agua
@app.post("/api/v1/alertas", status_code=status.HTTP_201_CREATED, tags=["Alertas & Seguridad"])
def registrar_alerta(alerta: AlertaNivelAguaCreate):
    return repository.insert_alerta(alerta)

@app.get("/api/v1/alertas", tags=["Alertas & Seguridad"])
def listar_alertas(limit: int = 20):
    return repository.get_alertas_recientes(limit)

# Endpoints de Umbrales de Riego
@app.get("/api/v1/umbrales/{id_sector}", tags=["Configuración"])
def consultar_umbral(id_sector: int):
    umbral = repository.get_umbral_by_sector(id_sector)
    if not umbral:
        raise HTTPException(status_code=404, detail="Umbral no encontrado para el sector especificado")
    return umbral

@app.put("/api/v1/umbrales/{id_sector}", tags=["Configuración"])
def actualizar_umbral(id_sector: int, umbral: UmbralUpdate):
    return repository.update_umbral(id_sector, umbral)


# =============================================================================
# EMULADOR DE TELEMETRÍA IOT (INTEGRADO EN SEGUNDO PLANO)
# =============================================================================

def iniciar_emulador_esp32():
    """Genera lecturas continuas realistas de sensores que se insertan en Neon DB."""
    time.sleep(1.5)
    print("\n🌿 [IoT ESP32 Activo] Emulador de telemetría iniciado en segundo plano.")
    print("📡 Transmitiendo lecturas dinámicas a Neon PostgreSQL cada 4 segundos...\n")

    humedad_actual = 52.0
    regando = False
    contador_ciclos = 0

    while True:
        try:
            # Simulación del comportamiento físico del suelo
            if regando:
                humedad_actual += random.uniform(3.5, 6.0)
                if humedad_actual >= 74.0:
                    regando = False
                    repository.insert_evento_riego(EventoRiegoCreate(
                        id_actuador="REL-BOM-01",
                        id_sector=1,
                        duracion_segundos=18,
                        volumen_litros_estimado=2.8,
                        motivo="AUTOMATICO_UMBRAL"
                    ))
                    print("💧 [IoT ESP32] Riego terminado. Nivel óptimo alcanzado (74%).")
            else:
                humedad_actual -= random.uniform(0.7, 1.6)
                if humedad_actual <= 32.0:
                    regando = True
                    print("⚡ [IoT ESP32] Humedad baja detectada (<=32%). Electrobomba encendida.")

            humedad_actual = max(12.0, min(92.0, humedad_actual))
            adc_crudo = int((humedad_actual / 100.0) * 4095)

            # Insertar registro en la base de datos Neon
            lectura = LecturaHumedadCreate(
                id_sensor="SEN-CAP-S01",
                id_sector=1,
                humedad_porcentaje=round(humedad_actual, 1),
                valor_adc_crudo=adc_crudo
            )
            repository.insert_lectura(lectura)
            print(f"📊 [ESP32 Telemetría] Humedad: {lectura.humedad_porcentaje}% | ADC: {adc_crudo} -> Guardado en Neon")

            # Registrar alerta periódica para probar el sistema de alertas
            contador_ciclos += 1
            if contador_ciclos == 25:
                alerta = AlertaNivelAguaCreate(
                    id_sector=1,
                    nivel_detectado="CRITICO_VACIO",
                    bomba_bloqueada=True,
                    observacion="Sensor Flotador: Nivel bajo en tanque principal"
                )
                repository.insert_alerta(alerta)
                print("🚨 [Alerta IoT] Alerta de tanque vacío registrada.")
                contador_ciclos = 0

        except Exception as e:
            print(f"Aviso en telemetría IoT: {e}")

        time.sleep(4)


@app.on_event("startup")
def on_startup():
    # Iniciar emulador de telemetría en hilo daemon al arrancar la API
    hilo = threading.Thread(target=iniciar_emulador_esp32, daemon=True)
    hilo.start()


if __name__ == "__main__":
    uvicorn.run("main_api_vivero:app", host="0.0.0.0", port=8000, reload=True)
