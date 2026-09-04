import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class ModeloRiego:
    def __init__(self):
        self.api_url = "https://vivero-automatico-esp32.onrender.com/api/v1"
        self.api_key = os.environ.get("API_KEY", "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d")

    def obtener_historial(self, id_sector: int = 1):
        """Recupera todos los registros históricos de mediciones desde la API para el sector indicado."""
        try:
            response = requests.get(
                f"{self.api_url}/mediciones/sector/{id_sector}?limit=50", 
                headers={"X-API-Key": self.api_key},
                timeout=3
            )
            if response.status_code == 200:
                datos = response.json()
                # Formato esperado por el controlador/vista para la tabla:
                # ["ID", "Fecha/Hora", "Ubicación", "Humedad", "Valor ADC", "Sensor"]
                filas = []
                for d in datos:
                    fh_raw = str(d.get("fecha_hora", "")).replace("T", " ")
                    fh_limpia = fh_raw.split('.')[0].split('+')[0].strip()
                    filas.append((
                        d.get("id_lectura", ""),
                        fh_limpia,
                        f"Invernadero {id_sector}", 
                        f"{float(d.get('humedad_porcentaje', 0)):.1f}%",
                        d.get("valor_adc_crudo", 0),
                        d.get("id_sensor", "")
                    ))
                return filas
        except Exception as e:
            print(f"Error conectando a la API (Historial Sector {id_sector}): {e}")
        return []

    def obtener_umbral(self, id_sector: int):
        """Obtiene el umbral de configuración para un sector desde la API."""
        try:
            response = requests.get(
                f"{self.api_url}/umbrales/{id_sector}",
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error obteniendo umbral del sector {id_sector}: {e}")
        return None

    def actualizar_umbral(self, id_sector: int, hum_min: float, hum_max: float, tiempo_seg: int, id_usuario: int = 1) -> bool:
        """Actualiza el umbral de riego para un sector vía PUT a la API. Retorna True si fue exitoso."""
        try:
            payload = {
                "humedad_min_on": hum_min,
                "humedad_max_off": hum_max,
                "tiempo_max_riego_seg": tiempo_seg,
                "id_usuario_modifica": id_usuario
            }
            response = requests.put(
                f"{self.api_url}/umbrales/{id_sector}",
                json=payload,
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error actualizando umbral del sector {id_sector}: {e}")
        return False

    def obtener_alertas_con_id(self):
        """Recupera alertas en formato crudo (dict) incluyendo id_alerta, para poder eliminarlas."""
        try:
            response = requests.get(
                f"{self.api_url}/alertas?limit=20",
                headers={"X-API-Key": self.api_key},
                timeout=3
            )
            if response.status_code == 200:
                return response.json()  # Lista de dicts con id_alerta incluido
        except Exception as e:
            print(f"Error conectando a la API (Alertas con ID): {e}")
        return []

    def obtener_alertas(self):
        """Recupera las alertas registradas desde la API."""
        try:
            response = requests.get(
                f"{self.api_url}/alertas?limit=20", 
                headers={"X-API-Key": self.api_key},
                timeout=3
            )
            if response.status_code == 200:
                datos = response.json()
                # Formato tabla alertas: ["Hora", "Tipo", "Sensor", "Valor", "Estado"]
                filas = []
                for d in datos:
                    fh_raw = str(d.get("fecha_hora", "")).replace("T", " ")
                    fh_limpia = fh_raw.split('.')[0].split('+')[0].strip()
                    filas.append((
                        fh_limpia,
                        "CRÍTICO",
                        "Sensor Flotador",
                        d.get("nivel_detectado", ""),
                        "Bomba Bloqueada" if d.get("bomba_bloqueada") else "Activa"
                    ))
                return filas
        except Exception as e:
            print(f"Error conectando a la API (Alertas): {e}")
        return []

    def obtener_ultimo_dato(self):
        """Recupera el último dato de humedad para las gráficas y tarjetas."""
        historial = self.obtener_historial()
        if historial and len(historial) > 0:
            ultimo = historial[0]
            return {
                "fecha_hora": ultimo[1],
                "ubicacion": ultimo[2],
                "humedad": ultimo[3],
                "adc": ultimo[4],
                "sensor": ultimo[5]
            }
        return {
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ubicacion": "Desconectado",
            "humedad": 0.0,
            "adc": 0,
            "sensor": "N/A"
        }

    def eliminar_medicion(self, id_lectura: int) -> bool:
        """Elimina una medición de humedad por su ID. Retorna True si se eliminó correctamente."""
        try:
            response = requests.delete(
                f"{self.api_url}/mediciones/{id_lectura}",
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error eliminando medición {id_lectura}: {e}")
            return False

    def eliminar_evento_riego(self, id_evento: int) -> bool:
        """Elimina un evento de riego por su ID. Retorna True si se eliminó correctamente."""
        try:
            response = requests.delete(
                f"{self.api_url}/riego/evento/{id_evento}",
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error eliminando evento de riego {id_evento}: {e}")
            return False

    def eliminar_alerta(self, id_alerta: int) -> bool:
        """Elimina una alerta de nivel de agua por su ID. Retorna True si se eliminó correctamente."""
        try:
            response = requests.delete(
                f"{self.api_url}/alertas/{id_alerta}",
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error eliminando alerta {id_alerta}: {e}")
            return False

    def forzar_riego(self, id_sector: int = 1, duracion_seg: int = 30) -> bool:
        """Envía un comando de riego forzado a la API para que el ESP32 lo consuma. Retorna True si fue exitoso."""
        try:
            response = requests.post(
                f"{self.api_url}/comandos/forzar-riego/{id_sector}?duracion_seg={duracion_seg}",
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error enviando comando forzar riego sector {id_sector}: {e}")
            return False

    # =========================================================================
    # SECTORES Y ENCARGADOS
    # =========================================================================

    def obtener_sectores(self):
        """Obtiene la lista de sectores con sus encargados."""
        try:
            res = requests.get(f"{self.api_url}/sectores", headers={"X-API-Key": self.api_key}, timeout=4)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Error obteniendo sectores: {e}")
        # Valores por defecto de contingencia con los 5 integrantes
        return [
            {
                "id_sector": 1,
                "nombre_sector": "Invernadero 1 (Principal)",
                "encargado_nombre": "Diego Charry",
                "encargado_correo": "diego.charry@vivero.com",
                "encargado_rol": "Administrador General",
                "tipo_cultivo": "Orquídeas y Suculentas",
                "descripcion": "Sector de telemetría IoT ESP32 automatizado"
            },
            {
                "id_sector": 2,
                "nombre_sector": "Invernadero 2 (Cultivo Agrónomo)",
                "encargado_nombre": "Angel Villalobos",
                "encargado_correo": "angel.villalobos@vivero.com",
                "encargado_rol": "Ingeniero Agrónomo",
                "tipo_cultivo": "Hortalizas y Tomates",
                "descripcion": "Monitoreo de suelo y fertilización"
            },
            {
                "id_sector": 3,
                "nombre_sector": "Invernadero 3 (Riego Automatizado)",
                "encargado_nombre": "Adelfo Freyle",
                "encargado_correo": "adelfo.freyle@vivero.com",
                "encargado_rol": "Operador de Riego",
                "tipo_cultivo": "Semilleros y Flores",
                "descripcion": "Área de aspersión y control de humedad"
            },
            {
                "id_sector": 4,
                "nombre_sector": "Invernadero 4 (Laboratorio IoT)",
                "encargado_nombre": "Juan Quintero",
                "encargado_correo": "juan.quintero@vivero.com",
                "encargado_rol": "Técnico en Sistemas IoT",
                "tipo_cultivo": "Cultivo Experimental",
                "descripcion": "Banco de pruebas de sensores y actuadores ESP32"
            },
            {
                "id_sector": 5,
                "nombre_sector": "Invernadero 5 (Supervisión)",
                "encargado_nombre": "Juan Figueroa",
                "encargado_correo": "juan.figueroa@vivero.com",
                "encargado_rol": "Monitor y Visualizador",
                "tipo_cultivo": "Plantas Ornamentales",
                "descripcion": "Supervisión y control de calidad"
            }
        ]

    def fijar_sector_activo(self, id_sector: int) -> bool:
        """Notifica a la API qué sector está activo para que el ESP32 en Wokwi se sincronice."""
        try:
            res = requests.put(
                f"{self.api_url}/sistema/sector-activo/{id_sector}",
                headers={"X-API-Key": self.api_key},
                timeout=3
            )
            return res.status_code == 200
        except Exception as e:
            print(f"Error fijando sector activo: {e}")
            return False

    def actualizar_sector(self, id_sector: int, nombre_sector: str, encargado_nombre: str, encargado_correo: str, encargado_rol: str, tipo_cultivo: str, descripcion: str = "") -> bool:
        """Actualiza la información del sector y su encargado."""
        try:
            payload = {
                "nombre_sector": nombre_sector,
                "encargado_nombre": encargado_nombre,
                "encargado_correo": encargado_correo,
                "encargado_rol": encargado_rol,
                "tipo_cultivo": tipo_cultivo,
                "descripcion": descripcion
            }
            res = requests.put(
                f"{self.api_url}/sectores/{id_sector}",
                json=payload,
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            return res.status_code == 200
        except Exception as e:
            print(f"Error actualizando sector {id_sector}: {e}")
            return False

    # =========================================================================
    # GESTIÓN DE USUARIOS Y ROLES
    # =========================================================================

    def obtener_usuarios(self):
        """Obtiene la lista de usuarios del sistema."""
        try:
            res = requests.get(f"{self.api_url}/usuarios", headers={"X-API-Key": self.api_key}, timeout=4)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Error obteniendo usuarios: {e}")
        return []

    def obtener_roles(self):
        """Obtiene la lista de roles/ocupaciones registrados en la base de datos."""
        try:
            res = requests.get(f"{self.api_url}/roles", headers={"X-API-Key": self.api_key}, timeout=4)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Error obteniendo roles: {e}")
        return []

    def crear_usuario(self, nombre: str, correo: str, contrasena: str, rol: str) -> bool:
        """Crea un nuevo usuario en la API."""
        try:
            payload = {
                "nombre": nombre,
                "correo": correo,
                "contrasena": contrasena,
                "rol": rol
            }
            res = requests.post(f"{self.api_url}/usuarios", json=payload, headers={"X-API-Key": self.api_key}, timeout=5)
            return res.status_code in [200, 201]
        except Exception as e:
            print(f"Error creando usuario: {e}")
            return False

    def actualizar_usuario(self, id_usuario: int, nombre: str = None, correo: str = None, contrasena: str = None, rol: str = None, activo: bool = True) -> bool:
        """Actualiza un usuario existente (contraseña y correo opcionales)."""
        try:
            payload = {}
            if nombre is not None: payload["nombre"] = nombre
            if correo is not None: payload["correo"] = correo
            if contrasena is not None and contrasena.strip(): payload["contrasena"] = contrasena.strip()
            if rol is not None: payload["rol"] = rol
            payload["activo"] = activo

            res = requests.put(f"{self.api_url}/usuarios/{id_usuario}", json=payload, headers={"X-API-Key": self.api_key}, timeout=5)
            return res.status_code == 200
        except Exception as e:
            print(f"Error actualizando usuario {id_usuario}: {e}")
            return False

    def eliminar_usuario(self, id_usuario: int) -> bool:
        """Elimina un usuario por su ID."""
        try:
            res = requests.delete(f"{self.api_url}/usuarios/{id_usuario}", headers={"X-API-Key": self.api_key}, timeout=5)
            return res.status_code == 200
        except Exception as e:
            print(f"Error eliminando usuario {id_usuario}: {e}")
            return False

    def autenticar_usuario(self, correo: str, contrasena: str):
        """Autentica a un usuario por correo y contraseña."""
        try:
            payload = {"correo": correo, "contrasena": contrasena}
            res = requests.post(f"{self.api_url}/auth/login", json=payload, timeout=5)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Error autenticando: {e}")
        return None