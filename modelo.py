import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class ModeloRiego:
    def __init__(self):
        self.api_url = "https://vivero-automatico-esp32.onrender.com/api/v1"
        self.api_key = os.environ.get("API_KEY", "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d")

    def obtener_historial(self):
        """Recupera todos los registros históricos de mediciones desde la API."""
        try:
            response = requests.get(
                f"{self.api_url}/mediciones/sector/1?limit=50", 
                headers={"X-API-Key": self.api_key},
                timeout=3
            )
            if response.status_code == 200:
                datos = response.json()
                # Formato esperado por el controlador/vista para la tabla:
                # ["ID", "Fecha/Hora", "Ubicación", "Humedad", "Valor ADC", "Sensor"]
                filas = []
                for d in datos:
                    filas.append((
                        d.get("id_lectura", ""),
                        str(d.get("fecha_hora", "")).replace("T", " "),
                        "Invernadero 1", 
                        d.get("humedad_porcentaje", 0),
                        d.get("valor_adc_crudo", 0),
                        d.get("id_sensor", "")
                    ))
                return filas
        except Exception as e:
            print(f"Error conectando a la API (Historial): {e}")
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

    def actualizar_umbral(self, id_sector: int, hum_min: float, hum_max: float, tiempo_seg: int) -> bool:
        """Actualiza el umbral de riego para un sector vía PUT a la API. Retorna True si fue exitoso."""
        try:
            payload = {
                "humedad_min_on": hum_min,
                "humedad_max_off": hum_max,
                "tiempo_max_riego_seg": tiempo_seg,
                "id_usuario_modifica": 1
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
                    filas.append((
                        str(d.get("fecha_hora", "")).replace("T", " "),
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