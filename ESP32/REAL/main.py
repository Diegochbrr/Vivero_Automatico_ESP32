"""
============================================================================
SmartVivero - Firmware Definitivo Físico en MicroPython
============================================================================
Hardware Conectado:
- ESP32 DevKit V1
- Pantalla LCD 16x2 I2C: SDA = GPIO 22, SCL = GPIO 21 (Dir: 0x27)
- Sensor Humedad Capacitivo v1.2: AOUT -> GPIO 34 (ADC1), VCC -> 3.3V
- Módulo Relé 1 Canal: IN -> GPIO 18, COM -> 5V, NO -> Bomba (+)
- Mini Bomba Sumergible 5V
============================================================================
"""

import time
import network
import machine
import urequests
import ujson
from machine import Pin, ADC, I2C
from machine_i2c_lcd import I2cLcd, DEFAULT_I2C_ADDR

# 1. CREDENCIALES WI-FI Y API CLOUD
WIFI_SSID     = "TU_NOMBRE_DE_WIFI"       # <-- Coloca tu red Wi-Fi
WIFI_PASSWORD = "TU_CONTRASENA_WIFI"   # <-- Coloca tu contraseña

API_BASE = "https://vivero-automatico-esp32.onrender.com/api/v1"
API_KEY  = "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d"

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# 2. DEFINICIÓN DE PINES
PIN_SENSOR_HUMEDAD = 34
PIN_RELE_BOMBA      = 18

# La mayoría de relés son activos en nivel BAJO (LOW / 0V).
# Si tu relé se activa al revés, cámbialo a False.
RELE_ACTIVE_LOW = True

# 3. CALIBRACIÓN DEL SENSOR CAPACITIVO v1.2
# Ajusta estos valores con lo que anotaste en test_hardware.py:
VALOR_ADC_AIRE = 3200  # Sensor en seco / aire (0% Humedad)
VALOR_ADC_AGUA = 1400  # Sensor en vaso de agua (100% Humedad)

# 4. PARÁMETROS DEL SISTEMA
ID_SECTOR            = 1
HUM_MIN_ON           = 35.0   # Enciende la bomba si humedad < 35%
HUM_MAX_OFF          = 70.0   # Apaga la bomba si humedad >= 70%
TIEMPO_MAX_RIEGO_SEG = 180
bomba_activa         = False

# 5. CONFIGURAR HARDWARE
rele = Pin(PIN_RELE_BOMBA, Pin.OUT)

def fijar_bomba(activar):
    global bomba_activa
    bomba_activa = activar
    if RELE_ACTIVE_LOW:
        rele.value(0 if activar else 1)
    else:
        rele.value(1 if activar else 0)

fijar_bomba(False) # Inicia con la bomba apagada

adc_humedad = ADC(Pin(PIN_SENSOR_HUMEDAD))
adc_humedad.atten(ADC.ATTN_11DB) # 0 a 3.3V

# Inicializar bus I2C y LCD
i2c = I2C(0, scl=Pin(21), sda=Pin(22), freq=400000)
lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)

lcd.clear()
lcd.putstr("VIVERO AUTO\nConectando WiFi")

# 6. CONEXIÓN WI-FI ROBUSTA
wlan = network.WLAN(network.STA_IF)

def conectar_wifi():
    if wlan.isconnected():
        return True
    
    # Reiniciar la interfaz para limpiar estados previos colgados
    print("Inicializando WiFi...")
    wlan.active(False)
    time.sleep(0.2)
    wlan.active(True)
    time.sleep(0.3)
    
    print("Conectando a WiFi:", WIFI_SSID)
    try:
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    except OSError as e:
        print("Aviso WiFi:", e)
        
    intentos = 0
    while not wlan.isconnected() and intentos < 25:
        time.sleep(0.4)
        print(".", end="")
        intentos += 1
        
    return wlan.isconnected()

conectado = conectar_wifi()

lcd.clear()
if conectado:
    ip = wlan.ifconfig()[0]
    print("\n[WiFi] Conectado! IP:", ip)
    lcd.putstr("WiFi Conectado!\nIP: " + ip[:12])
else:
    print("\n[WiFi] No conectado. Operando en modo Offline local.")
    lcd.putstr("Modo Offline\nSin conexion")
time.sleep(2)
lcd.clear()


def leer_humedad():
    """Lee el sensor con sobremuestreo y calcula el porcentaje calibrado."""
    suma = 0
    for _ in range(15):
        suma += adc_humedad.read()
        time.sleep_ms(5)
    raw = suma // 15
    
    # Mapeo inverso calibrado:
    porcentaje = ((VALOR_ADC_AIRE - raw) / (VALOR_ADC_AIRE - VALOR_ADC_AGUA)) * 100.0
    if porcentaje < 0.0:
        porcentaje = 0.0
    elif porcentaje > 100.0:
        porcentaje = 100.0
        
    return porcentaje, raw


def consultar_config_y_comandos():
    """Sincroniza el sector activo y comprueba si hay orden de forzar riego."""
    global ID_SECTOR, HUM_MIN_ON, HUM_MAX_OFF, TIEMPO_MAX_RIEGO_SEG
    if not wlan.isconnected():
        return

    # Sincronizar Sector Activo
    try:
        r_sec = urequests.get(API_BASE + "/sistema/sector-activo", headers=HEADERS)
        if r_sec.status_code == 200:
            d_sec = ujson.loads(r_sec.text)
            nuevo_sec = int(d_sec.get("sector_activo", ID_SECTOR))
            if nuevo_sec != ID_SECTOR:
                ID_SECTOR = nuevo_sec
                print("🔄 [Sector] Sincronizado a Sector {}".format(ID_SECTOR))
        r_sec.close()
    except Exception as e:
        print("⚠️ Error sector:", e)

    # Consultar umbrales y forzado de riego
    try:
        url_cmd = "{}/comandos/{}".format(API_BASE, ID_SECTOR)
        r = urequests.get(url_cmd, headers=HEADERS)
        if r.status_code == 200:
            data = ujson.loads(r.text)
            r.close()
            HUM_MIN_ON  = float(data.get("humedad_min_on", HUM_MIN_ON))
            HUM_MAX_OFF = float(data.get("humedad_max_off", HUM_MAX_OFF))
            
            # Si hay comando de forzar riego desde la app de escritorio
            if data.get("forzar_riego", False):
                duracion = int(data.get("duracion_forzado_seg", 15))
                print("[Comando] Riego forzado recibido! Regando por {}s".format(duracion))
                lcd.move_to(0, 1)
                lcd.putstr("Forzado: REGANDO")
                fijar_bomba(True)
                time.sleep(duracion)
                fijar_bomba(False)
                
                # Confirmar (ACK) borrando el flag en la API
                try:
                    url_ack = "{}/comandos/forzar-riego/{}".format(API_BASE, ID_SECTOR)
                    ack = urequests.request("DELETE", url_ack, headers=HEADERS)
                    print("[ACK] Confirmado DELETE:", ack.status_code)
                    ack.close()
                except Exception as ex:
                    print("Error ACK:", ex)
        else:
            r.close()
    except Exception as e:
        print("⚠️ Error comandos:", e)


def enviar_telemetria_api(humedad, raw_adc):
    """Envía la medición de humedad al backend en Render."""
    if not wlan.isconnected():
        return

    payload = {
        "id_sensor": "SEN-CAP-S01",
        "id_sector": ID_SECTOR,
        "humedad_porcentaje": round(humedad, 2),
        "valor_adc_crudo": raw_adc
    }
    try:
        res = urequests.post(API_BASE + "/mediciones", headers=HEADERS, json=payload)
        print("[API] Medicion enviada:", res.status_code)
        res.close()
    except Exception as e:
        print("Error enviando telemetria:", e)


# BUCLE PRINCIPAL
ultimo_envio_api = time.ticks_ms()
INTERVALO_ENVIO_MS = 5000

while True:
    humedad, raw_adc = leer_humedad()

    # Lógica de riego automático
    if humedad < HUM_MIN_ON:
        fijar_bomba(True)
    elif humedad >= HUM_MAX_OFF:
        fijar_bomba(False)

    # Actualizar pantalla LCD
    lcd.move_to(0, 0)
    lcd.putstr("S{} Hum:{:>5.1f}%  ".format(ID_SECTOR, humedad))

    lcd.move_to(0, 1)
    if bomba_activa:
        lcd.putstr("Bomba: REGANDO  ")
    else:
        lcd.putstr("Bomba: APAGADA  ")

    # Ciclo de comunicación periódica con la nube (cada 5 seg)
    if time.ticks_diff(time.ticks_ms(), ultimo_envio_api) >= INTERVALO_ENVIO_MS:
        ultimo_envio_api = time.ticks_ms()
        consultar_config_y_comandos()
        enviar_telemetria_api(humedad, raw_adc)

    time.sleep_ms(200)
