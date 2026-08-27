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

api_mediciones_url = "https://vivero-automatico-esp32.onrender.com/api/v1/mediciones"
api_alertas_url = "https://vivero-automatico-esp32.onrender.com/api/v1/alertas"
api_key = "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d"

# Configurar pines
adc_humedad = ADC(Pin(PIN_SENSOR_HUMEDAD))
adc_humedad.atten(ADC.ATTN_11DB) # Para leer hasta 3.3V (0-4095)

pin_nivel_agua = Pin(PIN_NIVEL_AGUA, Pin.IN, Pin.PULL_UP)
pin_boton_manual = Pin(PIN_BOTON_MANUAL, Pin.IN, Pin.PULL_UP)
rele_bomba = Pin(PIN_RELE_BOMBA, Pin.OUT)
led_alerta = Pin(PIN_LED_ALERTA, Pin.OUT)

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

ultimo_envio = time.ticks_ms()
intervalo_envio = 5000

def enviar_datos_api(humedad, adc_crudo, nivel_agua_ok):
    if wlan.isconnected():
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        
        # 1. Enviar telemetría de humedad a la nube (Render)
        payload = {
            "id_sensor": "SEN-CAP-S01",
            "id_sector": 1,
            "humedad_porcentaje": round(humedad, 2),
            "valor_adc_crudo": adc_crudo
        }
        
        try:
            # En MicroPython usamos urequests
            # timeout para evitar que se congele si Render está dormido
            response = urequests.post(api_mediciones_url, headers=headers, json=payload, timeout=5)
            print("📡 HTTP Mediciones:", response.status_code)
            response.close()
        except Exception as e:
            print("❌ Error HTTP Mediciones:", e)

        # 2. Enviar alerta crítica de falta de agua
        if not nivel_agua_ok:
            alerta_payload = {
                "id_sector": 1,
                "nivel_detectado": "CRITICO_VACIO",
                "bomba_bloqueada": True,
                "observacion": "Alerta de nivel de agua detectada por ESP32"
            }
            try:
                res_alerta = urequests.post(api_alertas_url, headers=headers, json=alerta_payload, timeout=5)
                print("🚨 HTTP Alerta Nivel:", res_alerta.status_code)
                res_alerta.close()
            except Exception as e:
                print("❌ Error HTTP Alerta Nivel:", e)
    else:
        print("⚠️ WiFi desconectado")

while True:
    # Lectura analógica con sobremuestreo (promedio de 10 lecturas) para evitar saltos o datos incorrectos
    suma_adc = 0
    for _ in range(10):
        suma_adc += adc_humedad.read()
        time.sleep_ms(5)
    
    raw_adc = suma_adc // 10
    porcentaje_humedad = (raw_adc / 4095.0) * 100.0

    # Estados de entrada
    nivel_agua_ok = (pin_nivel_agua.value() == 1)
    boton_manual = (pin_boton_manual.value() == 0)

    activar_bomba = False
    alerta_nivel = False

    # Lógica de control
    if not nivel_agua_ok:
        alerta_nivel = True
        activar_bomba = False
    else:
        if porcentaje_humedad < 35.0 or boton_manual:
            activar_bomba = True

    # Actualización de actuadores
    rele_bomba.value(1 if activar_bomba else 0)
    led_alerta.value(1 if alerta_nivel else 0)

    # Interfaz LCD
    lcd.move_to(0, 0)
    lcd.putstr("Hum: {:>5.1f}%   ".format(porcentaje_humedad))

    lcd.move_to(0, 1)
    if alerta_nivel:
        lcd.putstr("ALERTA: Sin Agua")
    elif activar_bomba:
        lcd.putstr("Bomba: REGANDO  ")
    else:
        lcd.putstr("Bomba: APAGADA  ")

    # Envío a la API cada 5 segundos
    # ticks_diff maneja correctamente el overflow de milisegundos
    if time.ticks_diff(time.ticks_ms(), ultimo_envio) >= intervalo_envio:
        ultimo_envio = time.ticks_ms()
        enviar_datos_api(porcentaje_humedad, raw_adc, nivel_agua_ok)

    time.sleep(0.2)
