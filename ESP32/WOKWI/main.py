import time
import network
import machine
import urequests
import ujson
from machine import Pin, ADC, I2C
from machine_i2c_lcd import I2cLcd, DEFAULT_I2C_ADDR

PIN_SENSOR_HUMEDAD = 34
PIN_NIVEL_AGUA     = 18
PIN_BOTON_MANUAL   = 19
PIN_RELE_BOMBA      = 2
PIN_LED_ALERTA      = 4

ssid = "Wokwi-GUEST"
password = ""

API_BASE           = "https://vivero-automatico-esp32.onrender.com/api/v1"
api_mediciones_url = API_BASE + "/mediciones"
api_alertas_url    = API_BASE + "/alertas"
api_comandos_url   = API_BASE + "/comandos/1"          # polling: umbral + forzar riego
api_ack_riego_url  = API_BASE + "/comandos/forzar-riego/1"  # DELETE para confirmar
api_key            = "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d"
ID_SECTOR          = 1

# Umbrales con valores por defecto (se sobreescriben al conectar a la API)
HUM_MIN_ON  = 35.0   # encender bomba si humedad < este valor
HUM_MAX_OFF = 70.0   # apagar bomba si humedad >= este valor
TIEMPO_MAX_RIEGO_SEG = 180

# Configurar pines
adc_humedad = ADC(Pin(PIN_SENSOR_HUMEDAD))
adc_humedad.atten(ADC.ATTN_11DB)  # Para leer hasta 3.3V (0-4095)

pin_nivel_agua   = Pin(PIN_NIVEL_AGUA, Pin.IN, Pin.PULL_UP)
pin_boton_manual = Pin(PIN_BOTON_MANUAL, Pin.IN, Pin.PULL_UP)
rele_bomba       = Pin(PIN_RELE_BOMBA, Pin.OUT)
led_alerta       = Pin(PIN_LED_ALERTA, Pin.OUT)

rele_bomba.value(0)
led_alerta.value(0)

# Inicializar I2C para LCD (en ESP32: SCL=22, SDA=21 por defecto)
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)

lcd.putstr("Iniciando Riego")

print("Conectando a WiFi", end="")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected():
    time.sleep(0.4)
    print(".", end="")
print("\n[WiFi] Conectado exitosamente!")
print("IP:", wlan.ifconfig()[0])

lcd.clear()

ultimo_envio   = time.ticks_ms()
intervalo_envio = 5000  # ms entre envíos a la API

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": api_key
}


def consultar_config_y_comandos():
    """
    1. Consulta GET /api/v1/sistema/sector-activo para saber qué sector está operando la app.
    2. Consulta GET /api/v1/comandos/{ID_SECTOR} para leer umbrales y si hay forzado de riego.
    """
    global HUM_MIN_ON, HUM_MAX_OFF, TIEMPO_MAX_RIEGO_SEG, ID_SECTOR
    
    # 1. Sincronizar Sector Activo
    try:
        r_sec = urequests.get(API_BASE + "/sistema/sector-activo", headers=HEADERS, timeout=4)
        if r_sec.status_code == 200:
            d_sec = ujson.loads(r_sec.text)
            nuevo_sec = int(d_sec.get("sector_activo", ID_SECTOR))
            if nuevo_sec != ID_SECTOR:
                ID_SECTOR = nuevo_sec
                print("🔄 [Sector] ESP32 sincronizado a Sector {}".format(ID_SECTOR))
            r_sec.close()
        else:
            r_sec.close()
    except Exception as e:
        print("⚠️ Error consultando sector activo:", e)

    # 2. Consultar Umbrales y Comandos del sector activo
    try:
        url_cmd = "{}/comandos/{}".format(API_BASE, ID_SECTOR)
        r = urequests.get(url_cmd, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            data = ujson.loads(r.text)
            r.close()
            HUM_MIN_ON           = float(data.get("humedad_min_on",  HUM_MIN_ON))
            HUM_MAX_OFF          = float(data.get("humedad_max_off", HUM_MAX_OFF))
            TIEMPO_MAX_RIEGO_SEG = int(data.get("tiempo_max_riego_seg", TIEMPO_MAX_RIEGO_SEG))
            print("[Sector {}] Min={:.1f}% Max={:.1f}% Forzar={}".format(
                ID_SECTOR, HUM_MIN_ON, HUM_MAX_OFF, data.get("forzar_riego", False)))
            return data
        else:
            r.close()
    except Exception as e:
        print("⚠️ Error consultando config/comandos:", e)
    return None


def confirmar_riego_forzado():
    """DELETE /api/v1/comandos/forzar-riego/{ID_SECTOR} — limpia el flag en la API."""
    try:
        url_ack = "{}/comandos/forzar-riego/{}".format(API_BASE, ID_SECTOR)
        r = urequests.request("DELETE", url_ack, headers=HEADERS, timeout=5)
        print("[ACK] Riego forzado sector {} confirmado: {}".format(ID_SECTOR, r.status_code))
        r.close()
    except Exception as e:
        print("⚠️ Error confirmando riego forzado:", e)


def enviar_datos_api(humedad, adc_crudo, nivel_agua_ok):
    if not wlan.isconnected():
        print("WiFi desconectado")
        return

    # 1. Telemetría de humedad
    payload = {
        "id_sensor": "SEN-CAP-S01",
        "id_sector": ID_SECTOR,
        "humedad_porcentaje": round(humedad, 2),
        "valor_adc_crudo": adc_crudo
    }
    try:
        response = urequests.post(api_mediciones_url, headers=HEADERS, json=payload, timeout=5)
        print("HTTP Mediciones:", response.status_code)
        response.close()
    except Exception as e:
        print("Error HTTP Mediciones:", e)

    # 2. Alerta crítica de falta de agua
    if not nivel_agua_ok:
        alerta_payload = {
            "id_sector": ID_SECTOR,
            "nivel_detectado": "CRITICO_VACIO",
            "bomba_bloqueada": True,
            "observacion": "Alerta de nivel de agua detectada por ESP32"
        }
        try:
            res_alerta = urequests.post(api_alertas_url, headers=HEADERS, json=alerta_payload, timeout=5)
            print("HTTP Alerta Nivel:", res_alerta.status_code)
            res_alerta.close()
        except Exception as e:
            print("Error HTTP Alerta:", e)


# ── Loop principal ────────────────────────────────────────────────────────────
while True:
    # Lectura analógica con sobremuestreo (promedio de 10 lecturas)
    suma_adc = 0
    for _ in range(10):
        suma_adc += adc_humedad.read()
        time.sleep_ms(5)

    raw_adc             = suma_adc // 10
    porcentaje_humedad  = (raw_adc / 4095.0) * 100.0

    # Estados de entrada
    nivel_agua_ok = (pin_nivel_agua.value() == 1)
    boton_manual  = (pin_boton_manual.value() == 0)

    activar_bomba = False
    alerta_nivel  = False

    if time.ticks_diff(time.ticks_ms(), ultimo_envio) >= intervalo_envio:
        ultimo_envio = time.ticks_ms()

        # ── Consultar configuración y comandos pendientes ─────────────────────
        config = consultar_config_y_comandos() if wlan.isconnected() else None

        forzar = False
        duracion_forzado = 30
        if config:
            forzar           = bool(config.get("forzar_riego", False))
            duracion_forzado = int(config.get("duracion_forzado_seg", 30))

        # ── Lógica de control ─────────────────────────────────────────────────
        if not nivel_agua_ok:
            alerta_nivel  = True
            activar_bomba = False
        else:
            # Riego si humedad baja el umbral mínimo, o botón físico, o comando forzado
            if porcentaje_humedad < HUM_MIN_ON or boton_manual or forzar:
                activar_bomba = True

        # ── Si hay riego forzado, regar la duración indicada y confirmar ──────
        if forzar and nivel_agua_ok:
            print("[Forzar] Regando {}s por comando de la app".format(duracion_forzado))
            rele_bomba.value(1)
            lcd.move_to(0, 1)
            lcd.putstr("Forzado: REGANDO")
            time.sleep(duracion_forzado)
            rele_bomba.value(0)
            confirmar_riego_forzado()  # limpia el flag en la API
            activar_bomba = False      # reset para no doble-activar

        # ── Envío de telemetría ───────────────────────────────────────────────
        enviar_datos_api(porcentaje_humedad, raw_adc, nivel_agua_ok)

    # ── Lógica de control continua (entre envíos) ─────────────────────────────
    if not nivel_agua_ok:
        alerta_nivel  = True
        activar_bomba = False
    elif porcentaje_humedad < HUM_MIN_ON or boton_manual:
        activar_bomba = True
    elif porcentaje_humedad >= HUM_MAX_OFF:
        activar_bomba = False  # cortar riego si supera el máximo

    # Actualización de actuadores
    rele_bomba.value(1 if activar_bomba else 0)
    led_alerta.value(1 if alerta_nivel else 0)

    # Interfaz LCD
    lcd.move_to(0, 0)
    lcd.putstr("S{} Hum:{:>5.1f}%  ".format(ID_SECTOR, porcentaje_humedad))

    lcd.move_to(0, 1)
    if alerta_nivel:
        lcd.putstr("ALERTA: Sin Agua")
    elif activar_bomba:
        lcd.putstr("Bomba: REGANDO  ")
    else:
        lcd.putstr("Bomba: APAGADA  ")

    time.sleep(0.2)
