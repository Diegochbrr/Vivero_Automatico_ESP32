"""
API REST con Arquitectura POO en Python para el Sistema de Riego Autónomo
Conexión directa y optimizada (Connection Pooling) a PostgreSQL en Neon Cloud
Incluye generador de telemetría IoT en segundo plano para operar sin depender de Wokwi externo.
"""

import os
import sys
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

if sys.stdout and hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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


# --- DTOs SECTORES Y ENCARGADOS ---
class SectorResponse(BaseModel):
    id_sector: int
    nombre_sector: str
    encargado_nombre: str
    encargado_correo: str
    encargado_rol: str
    tipo_cultivo: str
    descripcion: Optional[str] = ""

class SectorUpdate(BaseModel):
    nombre_sector: str = Field(..., example="Invernadero 1 (Principal)")
    encargado_nombre: str = Field(..., example="Diego Charry")
    encargado_correo: str = Field(..., example="diego.charry@vivero.com")
    encargado_rol: str = Field(..., example="Administrador General")
    tipo_cultivo: str = Field(..., example="Orquídeas y Suculentas")
    descripcion: Optional[str] = Field(default="", example="Zona de cultivo automatizado")


# --- DTOs USUARIOS Y ROLES ---
class RolResponse(BaseModel):
    id_rol: int
    nombre_rol: str
    descripcion: Optional[str] = None

class UsuarioCreate(BaseModel):
    nombre: str = Field(..., example="Diego Charry")
    correo: str = Field(..., example="diego.charry@vivero.com")
    contrasena: str = Field(..., example="admin123")
    rol: Optional[str] = Field(default="OPERADOR", example="ADMINISTRADOR")
    id_rol: Optional[int] = Field(default=None, example=1)

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, example="Diego Charry")
    correo: Optional[str] = Field(default=None, example="diego.charry@vivero.com")
    contrasena: Optional[str] = Field(default=None, example="nueva_contrasena123")
    rol: Optional[str] = Field(default=None, example="ADMINISTRADOR")
    id_rol: Optional[int] = Field(default=None, example=1)
    activo: Optional[bool] = Field(default=None, example=True)

class UsuarioResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    rol: str
    id_rol: Optional[int] = None
    activo: bool
    creado_en: Optional[Any] = None

class LoginRequest(BaseModel):
    correo: str
    contrasena: str


# Estado en memoria de comandos pendientes por sector (no requiere tabla extra en BD)
# { id_sector: {"forzar_riego": bool, "duracion_seg": int} }
_comandos_pendientes: Dict[int, Dict[str, Any]] = {}
_sector_activo_sistema: int = 1


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
        self.init_db()

    def init_db(self):
        """Inicializa las tablas necesarias e inserta datos semilla si no existen."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Tabla Roles (Normalización 3NF)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS roles (
                            id_rol SERIAL PRIMARY KEY,
                            nombre_rol VARCHAR(50) UNIQUE NOT NULL,
                            descripcion TEXT
                        );
                    """)
                    roles_iniciales = [
                        ('ADMINISTRADOR', 'Acceso total al sistema, configuración y gestión de personal'),
                        ('AGRONOMO', 'Supervisión de cultivos y calibración de umbrales agronómicos'),
                        ('OPERADOR', 'Operación de riego y supervisión en campo'),
                        ('TECNICO_IOT', 'Mantenimiento de nodos sensores y actuadores ESP32'),
                        ('VISUALIZADOR', 'Monitoreo en tiempo real y solo lectura'),
                    ]
                    for nom_r, desc_r in roles_iniciales:
                        cur.execute("""
                            INSERT INTO roles (nombre_rol, descripcion)
                            VALUES (%s, %s)
                            ON CONFLICT (nombre_rol) DO UPDATE SET descripcion = EXCLUDED.descripcion;
                        """, (nom_r, desc_r))

                    # 2. Tabla Usuarios con Llave Foránea id_rol
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS usuarios (
                            id_usuario SERIAL PRIMARY KEY,
                            nombre VARCHAR(100) NOT NULL,
                            correo VARCHAR(150) UNIQUE NOT NULL,
                            contrasena_hash VARCHAR(255) NOT NULL,
                            rol VARCHAR(50) DEFAULT 'OPERADOR',
                            id_rol INT REFERENCES roles(id_rol),
                            activo BOOLEAN DEFAULT TRUE,
                            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_schema = 'public' AND table_name = 'usuarios' AND column_name = 'id_rol'
                            ) THEN
                                ALTER TABLE usuarios ADD COLUMN id_rol INT REFERENCES roles(id_rol);
                            END IF;
                        END $$;
                    """)

                    # 3. Tabla Sectores y Encargados
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS sectores (
                            id_sector INT PRIMARY KEY,
                            nombre_sector VARCHAR(100) NOT NULL,
                            encargado_nombre VARCHAR(100) NOT NULL,
                            encargado_correo VARCHAR(150) NOT NULL,
                            encargado_rol VARCHAR(50) NOT NULL,
                            tipo_cultivo VARCHAR(100) NOT NULL,
                            descripcion TEXT DEFAULT ''
                        );
                    """)

                    # 4. Semilla/Sincronización de los 5 Usuarios del Grupo 3
                    usuarios_iniciales = [
                        ('Diego Charry', 'diego.charry@vivero.com', 'admin123', 'ADMINISTRADOR', 1),
                        ('Angel Villalobos', 'angel.villalobos@vivero.com', 'admin123', 'AGRONOMO', 2),
                        ('Adelfo Freyle', 'adelfo.freyle@vivero.com', 'admin123', 'OPERADOR', 3),
                        ('Juan Quintero', 'juan.quintero@vivero.com', 'admin123', 'TECNICO_IOT', 4),
                        ('Juan Figueroa', 'juan.figueroa@vivero.com', 'admin123', 'VISUALIZADOR', 5),
                    ]
                    for nom, cor, pas, rol, id_r in usuarios_iniciales:
                        cur.execute("SELECT id_usuario FROM usuarios WHERE correo = %s;", (cor,))
                        if cur.fetchone():
                            cur.execute("""
                                UPDATE usuarios SET nombre = %s, contrasena_hash = %s, rol = %s, id_rol = %s, activo = TRUE
                                WHERE correo = %s;
                            """, (nom, pas, rol, id_r, cor))
                        else:
                            cur.execute("""
                                INSERT INTO usuarios (nombre, correo, contrasena_hash, rol, id_rol, activo)
                                VALUES (%s, %s, %s, %s, %s, TRUE);
                            """, (nom, cor, pas, rol, id_r))

                    # 4. Semilla/Sincronización de Sectores asignados al equipo
                    sectores_iniciales = [
                        (1, 'Invernadero 1 (Principal)', 'Diego Charry', 'diego.charry@vivero.com', 'Administrador General', 'Orquídeas y Suculentas', 'Sector de telemetría IoT ESP32 automatizado'),
                        (2, 'Invernadero 2 (Cultivo Agrónomo)', 'Angel Villalobos', 'angel.villalobos@vivero.com', 'Ingeniero Agrónomo', 'Hortalizas y Tomates', 'Monitoreo de suelo y fertilización'),
                        (3, 'Invernadero 3 (Riego Automatizado)', 'Adelfo Freyle', 'adelfo.freyle@vivero.com', 'Operador de Riego', 'Semilleros y Flores', 'Área de aspersión y control de humedad'),
                        (4, 'Invernadero 4 (Laboratorio IoT)', 'Juan Quintero', 'juan.quintero@vivero.com', 'Técnico en Sistemas IoT', 'Cultivo Experimental', 'Banco de pruebas de sensores y actuadores ESP32'),
                        (5, 'Invernadero 5 (Supervisión)', 'Juan Figueroa', 'juan.figueroa@vivero.com', 'Monitor y Visualizador', 'Plantas Ornamentales', 'Supervisión y control de calidad'),
                    ]
                    for id_s, nom_s, enc_n, enc_c, enc_r, cul, des in sectores_iniciales:
                        cur.execute("SELECT id_sector FROM sectores WHERE id_sector = %s;", (id_s,))
                        if cur.fetchone():
                            cur.execute("""
                                UPDATE sectores SET nombre_sector = %s, encargado_nombre = %s, encargado_correo = %s, encargado_rol = %s, tipo_cultivo = %s, descripcion = %s
                                WHERE id_sector = %s;
                            """, (nom_s, enc_n, enc_c, enc_r, cul, des, id_s))
                        else:
                            cur.execute("""
                                INSERT INTO sectores (id_sector, nombre_sector, encargado_nombre, encargado_correo, encargado_rol, tipo_cultivo, descripcion)
                                VALUES (%s, %s, %s, %s, %s, %s, %s);
                            """, (id_s, nom_s, enc_n, enc_c, enc_r, cul, des))

                    # 5. Asegurar umbrales para sectores 1 a 5
                    umbrales_iniciales = [
                        (1, 35.0, 70.0, 180),
                        (2, 40.0, 75.0, 150),
                        (3, 45.0, 80.0, 200),
                        (4, 30.0, 65.0, 120),
                        (5, 38.0, 72.0, 160),
                    ]
                    for id_s, h_min, h_max, t_max in umbrales_iniciales:
                        cur.execute("SELECT id_sector FROM umbrales_configuracion WHERE id_sector = %s;", (id_s,))
                        if not cur.fetchone():
                            cur.execute("""
                                INSERT INTO umbrales_configuracion (id_sector, humedad_min_on, humedad_max_off, tiempo_max_riego_seg, id_usuario_modifica)
                                VALUES (%s, %s, %s, %s, 1);
                            """, (id_s, h_min, h_max, t_max))

                    conn.commit()
                    print("[OK] Tablas, roles, sectores y cuentas de usuarios inicializadas correctamente.")
        except Exception as e:
            print(f"[WARN] Advertencia en init_db: {e}")

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

    # --- GESTIÓN DE SECTORES ---
    def get_sectores(self) -> List[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sectores ORDER BY id_sector ASC;")
                return [dict(row) for row in cur.fetchall()]

    def get_sector_by_id(self, id_sector: int) -> Optional[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sectores WHERE id_sector = %s;", (id_sector,))
                res = cur.fetchone()
                return dict(res) if res else None

    def update_sector(self, id_sector: int, sector: SectorUpdate) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sectores (id_sector, nombre_sector, encargado_nombre, encargado_correo, encargado_rol, tipo_cultivo, descripcion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id_sector) DO UPDATE SET
                        nombre_sector = EXCLUDED.nombre_sector,
                        encargado_nombre = EXCLUDED.encargado_nombre,
                        encargado_correo = EXCLUDED.encargado_correo,
                        encargado_rol = EXCLUDED.encargado_rol,
                        tipo_cultivo = EXCLUDED.tipo_cultivo,
                        descripcion = EXCLUDED.descripcion
                    RETURNING *;
                """, (id_sector, sector.nombre_sector, sector.encargado_nombre, sector.encargado_correo, sector.encargado_rol, sector.tipo_cultivo, sector.descripcion))
                res = cur.fetchone()
                conn.commit()
                return dict(res)

    # --- ROLES ---
    def get_roles(self) -> List[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id_rol, nombre_rol, descripcion FROM roles ORDER BY id_rol ASC;")
                return [dict(row) for row in cur.fetchall()]

    # --- GESTIÓN DE USUARIOS ---
    def get_usuarios(self) -> List[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT u.id_usuario, u.nombre, u.correo, COALESCE(r.nombre_rol, u.rol) AS rol, u.id_rol, u.activo, u.creado_en
                    FROM usuarios u
                    LEFT JOIN roles r ON u.id_rol = r.id_rol
                    ORDER BY u.id_usuario ASC;
                """)
                return [dict(row) for row in cur.fetchall()]

    def create_usuario(self, user: UsuarioCreate) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id_usuario FROM usuarios WHERE correo = %s;", (user.correo,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="El correo ya se encuentra registrado.")
                
                # Resolver id_rol y nombre_rol
                id_rol = user.id_rol
                nombre_rol = (user.rol or "OPERADOR").strip().upper()
                if id_rol:
                    cur.execute("SELECT nombre_rol FROM roles WHERE id_rol = %s;", (id_rol,))
                    row_r = cur.fetchone()
                    if row_r:
                        nombre_rol = row_r["nombre_rol"]
                else:
                    cur.execute("SELECT id_rol FROM roles WHERE nombre_rol = %s;", (nombre_rol,))
                    row_r = cur.fetchone()
                    if row_r:
                        id_rol = row_r["id_rol"]
                    else:
                        id_rol = 3  # OPERADOR por defecto

                cur.execute("""
                    INSERT INTO usuarios (nombre, correo, contrasena_hash, rol, id_rol, activo)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    RETURNING id_usuario, nombre, correo, rol, id_rol, activo, creado_en;
                """, (user.nombre, user.correo, user.contrasena, nombre_rol, id_rol))
                res = cur.fetchone()
                conn.commit()
                return dict(res)

    def update_usuario(self, id_usuario: int, user: UsuarioUpdate) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Obtener usuario existente
                cur.execute("SELECT * FROM usuarios WHERE id_usuario = %s;", (id_usuario,))
                current = cur.fetchone()
                if not current:
                    raise HTTPException(status_code=404, detail="Usuario no encontrado.")

                # 2. Reemplazar solo los campos provistos (contraseña y correo opcionales)
                nuevo_nombre = user.nombre.strip() if (user.nombre and user.nombre.strip()) else current["nombre"]
                nuevo_correo = user.correo.strip() if (user.correo and user.correo.strip()) else current["correo"]
                nueva_pass   = user.contrasena.strip() if (user.contrasena and user.contrasena.strip()) else current["contrasena_hash"]
                nuevo_activo = user.activo if user.activo is not None else current["activo"]

                # Resolver id_rol y nombre_rol
                nuevo_id_rol = user.id_rol if user.id_rol is not None else current.get("id_rol")
                if user.rol and user.rol.strip():
                    nuevo_rol = user.rol.strip().upper()
                    cur.execute("SELECT id_rol FROM roles WHERE nombre_rol = %s;", (nuevo_rol,))
                    row_r = cur.fetchone()
                    if row_r:
                        nuevo_id_rol = row_r["id_rol"]
                elif nuevo_id_rol:
                    cur.execute("SELECT nombre_rol FROM roles WHERE id_rol = %s;", (nuevo_id_rol,))
                    row_r = cur.fetchone()
                    nuevo_rol = row_r["nombre_rol"] if row_r else current["rol"]
                else:
                    nuevo_rol = current["rol"]

                cur.execute("""
                    UPDATE usuarios
                    SET nombre = %s, correo = %s, contrasena_hash = %s, rol = %s, id_rol = %s, activo = %s
                    WHERE id_usuario = %s
                    RETURNING id_usuario, nombre, correo, rol, id_rol, activo, creado_en;
                """, (nuevo_nombre, nuevo_correo, nueva_pass, nuevo_rol, nuevo_id_rol, nuevo_activo, id_usuario))
                res = cur.fetchone()
                conn.commit()
                return dict(res)

    def delete_usuario(self, id_usuario: int) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM usuarios WHERE id_usuario = %s RETURNING id_usuario, nombre, correo;", (id_usuario,))
                res = cur.fetchone()
                if not res:
                    raise HTTPException(status_code=404, detail="Usuario no encontrado.")
                conn.commit()
                return dict(res)

    def authenticate_user(self, correo: str, contrasena: str) -> Dict[str, Any]:
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT u.id_usuario, u.nombre, u.correo, u.contrasena_hash, COALESCE(r.nombre_rol, u.rol) AS rol, u.id_rol, u.activo
                    FROM usuarios u
                    LEFT JOIN roles r ON u.id_rol = r.id_rol
                    WHERE u.correo = %s;
                """, (correo,))
                user = cur.fetchone()
                if not user or user["contrasena_hash"] != contrasena:
                    raise HTTPException(status_code=401, detail="Credenciales incorrectas.")
                if not user["activo"]:
                    raise HTTPException(status_code=403, detail="Cuenta de usuario desactivada.")
                return {
                    "id_usuario": user["id_usuario"],
                    "nombre": user["nombre"],
                    "correo": user["correo"],
                    "rol": user["rol"],
                    "id_rol": user["id_rol"]
                }


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

# Endpoint Raíz y Diagnóstico (Soporta GET y HEAD para Render health checks)
@app.api_route("/", methods=["GET", "HEAD"], tags=["Salud y Diagnóstico"])
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


@app.get("/api/v1/sistema/sector-activo",
         tags=["Comandos ESP32"],
         summary="Consultar sector activo actual",
         description="El ESP32 llama a este endpoint para saber qué sector está activo en la app de escritorio.")
def consultar_sector_activo_sistema():
    return {"sector_activo": _sector_activo_sistema}


@app.put("/api/v1/sistema/sector-activo/{id_sector}",
         tags=["Comandos ESP32"],
         summary="Fijar sector activo del sistema",
         dependencies=[Depends(get_api_key)])
def fijar_sector_activo_sistema(id_sector: int):
    global _sector_activo_sistema
    _sector_activo_sistema = id_sector
    return {"mensaje": f"Sector activo del sistema actualizado a {id_sector}", "sector_activo": id_sector}


# =============================================================================
# ENDPOINTS DE SECTORES Y ENCARGADOS
# =============================================================================

@app.get("/api/v1/sectores", tags=["Sectores & Encargados"], dependencies=[Depends(get_api_key)])
def listar_sectores():
    return repository.get_sectores()

@app.get("/api/v1/sectores/{id_sector}", tags=["Sectores & Encargados"], dependencies=[Depends(get_api_key)])
def obtener_sector(id_sector: int):
    sec = repository.get_sector_by_id(id_sector)
    if not sec:
        raise HTTPException(status_code=404, detail="Sector no encontrado")
    return sec

@app.put("/api/v1/sectores/{id_sector}", tags=["Sectores & Encargados"], dependencies=[Depends(get_api_key)])
def actualizar_sector(id_sector: int, sector: SectorUpdate):
    return repository.update_sector(id_sector, sector)


# =============================================================================
# ENDPOINTS DE GESTIÓN DE USUARIOS Y ROLES
# =============================================================================

@app.get("/api/v1/roles", tags=["Usuarios & Roles"], dependencies=[Depends(get_api_key)])
def listar_roles():
    return repository.get_roles()

@app.get("/api/v1/usuarios", tags=["Usuarios & Roles"], dependencies=[Depends(get_api_key)])
def listar_usuarios():
    return repository.get_usuarios()

@app.post("/api/v1/usuarios", status_code=status.HTTP_201_CREATED, tags=["Usuarios & Roles"], dependencies=[Depends(get_api_key)])
def registrar_usuario(user: UsuarioCreate):
    return repository.create_usuario(user)

@app.put("/api/v1/usuarios/{id_usuario}", tags=["Usuarios & Roles"], dependencies=[Depends(get_api_key)])
def actualizar_usuario(id_usuario: int, user: UsuarioUpdate):
    return repository.update_usuario(id_usuario, user)

@app.delete("/api/v1/usuarios/{id_usuario}", tags=["Usuarios & Roles"], dependencies=[Depends(get_api_key)])
def eliminar_usuario(id_usuario: int):
    return repository.delete_usuario(id_usuario)

@app.post("/api/v1/auth/login", tags=["Usuarios & Roles"])
def iniciar_sesion(credenciales: LoginRequest):
    return repository.authenticate_user(credenciales.correo, credenciales.contrasena)


if __name__ == "__main__":
    uvicorn.run("main_api_vivero:app", host="0.0.0.0", port=8000, reload=True)