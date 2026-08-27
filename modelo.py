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