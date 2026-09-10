"""
============================================================================
SmartVivero - Test y Calibración de Hardware Físico en MicroPython
============================================================================
Pines configurados:
- Pantalla LCD 16x2 I2C: SDA = GPIO 22, SCL = GPIO 21 (Dirección: 0x27)
- Sensor Humedad v1.2: AOUT -> GPIO 34 (ADC1)
- Módulo Relé: IN -> GPIO 18
============================================================================
"""

import time
from machine import Pin, ADC, I2C
from machine_i2c_lcd import I2cLcd, DEFAULT_I2C_ADDR

# 1. Configuración de Pines
PIN_SENSOR_HUMEDAD = 34
PIN_RELE           = 18

# La mayoría de relés son activos en BAJO (0V).
# Si tu relé se activa al revés, cambia esta variable a False.
RELE_ACTIVE_LOW = True

# 2. Inicializar Relé (Inicia apagado por seguridad)
rele = Pin(PIN_RELE, Pin.OUT)

def fijar_bomba(activar):
    if RELE_ACTIVE_LOW:
        rele.value(0 if activar else 1)
    else:
        rele.value(1 if activar else 0)

fijar_bomba(False)

# 3. Inicializar Sensor ADC (12 bits: 0 a 4095, rango hasta 3.3V)
adc_humedad = ADC(Pin(PIN_SENSOR_HUMEDAD))
adc_humedad.atten(ADC.ATTN_11DB)

# 4. Inicializar LCD I2C en SDA=22, SCL=21
i2c = I2C(0, scl=Pin(21), sda=Pin(22), freq=400000)
lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)

lcd.clear()
lcd.putstr("TEST HARDWARE\nSmartVivero")
time.sleep(2)
lcd.clear()

print("--- INICIANDO TEST DE CALIBRACION MICROPYTHON ---")
print("Observa el valor ADC Raw en la consola y en el LCD.")
print("1. Deja el sensor al aire (Seco) y anota el valor.")
print("2. Sumerge la punta en agua y anota el valor.\n")

contador_rele = 0

while True:
    # Sobremuestreo (promedio de 15 lecturas para eliminar ruido)
    suma = 0
    for _ in range(15):
        suma += adc_humedad.read()
        time.sleep_ms(10)
    raw_adc = suma // 15

    # Cálculo de voltaje real aproximado (0.00V a 3.30V)
    voltaje = (raw_adc / 4095) * 3.3

    print("ADC Raw: {:<4} | Voltaje: {:.2f} V".format(raw_adc, voltaje))

    # Actualizar pantalla LCD
    lcd.move_to(0, 0)
    lcd.putstr("ADC:{:<5} P:{}".format(raw_adc, PIN_SENSOR_HUMEDAD))

    lcd.move_to(0, 1)
    lcd.putstr("Voltaje: {:.2f}V ".format(voltaje))

    time.sleep_ms(400)

