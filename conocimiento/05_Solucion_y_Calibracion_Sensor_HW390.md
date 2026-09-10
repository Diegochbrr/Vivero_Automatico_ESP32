# Solución y Calibración del Sensor de Humedad HW-390 (SmartVivero)

Este documento contiene la guía paso a paso para revivir, conectar y calibrar el sensor capacitivo **HW-390 V2.0.0** con la resistencia de 10 kΩ, dejando el sistema listo para la entrega final.

---

## 1. Diagnóstico del Problema de Fábrica

* **Modelo:** *Capacitive Soil Moisture Sensor V2.0.0 (HW-390 / 2024)*.
* **Síntoma detectado:** El sensor marca un valor estático de `~3648` (`2.94 V`) al aire y `~3660` (`2.95 V`) en agua. No reacciona a la humedad.
* **Causa técnica:** Error de fabricación común en el diseño de la PCB: la resistencia interna de descarga **R4** (1 MΩ) tiene la vía de conexión a tierra (**GND**) cortada. El condensador de salida de señal se carga al voltaje máximo y nunca se puede descargar.

---

## 2. La Solución: Resistencia Externa de 10 kΩ (Pull-Down)

Colocando una resistencia externa entre el pin de señal analógica (**AOUT**) y tierra (**GND**), se restaura el camino de descarga y el sensor empieza a variar su voltaje normalmente según el nivel de humedad.

### Identificación de la Resistencia de 10 kΩ (Colores):
* **Resistencia de 4 bandas:** **Marrón – Negro – Naranja – Dorado**
* **Resistencia de 5 bandas:** **Marrón – Negro – Negro – Rojo – Marrón**

---

## 3. Diagrama de Conexión Física

```text
       [ Sensor HW-390 ]
             VCC  ----------------------------------------> 3.3V o VIN (5V) del ESP32
             GND  ----------------+-----------------------> GND del ESP32
                                  |
                            [Resistencia]
                              [ 10 kΩ ]
                                  |
             AUOT ----------------+-----------------------> GPIO 34 del ESP32
```

### Pines detallados:
1. **VCC del sensor:** Al pin **3.3V** (o al pin **VIN / 5V**) del ESP32.
2. **GND del sensor:** Al pin **GND** del ESP32.
3. **AUOT del sensor:** Al pin **GPIO 34** del ESP32.
4. **Resistencia de 10 kΩ:**
   * Una patita conectada a la misma línea de **AUOT (GPIO 34)**.
   * La otra patita conectada a la misma línea de **GND**.

> [!WARNING]
> **Límite de agua:** Sumerge la pala en agua o tierra **únicamente hasta la línea blanca** serigrafiada. Nunca mojes la zona superior donde están los chips y el conector blanco.

---

## 4. Paso a Paso de Prueba con `test_hardware.py`

1. Abre Thonny con el ESP32 conectado.
2. Abre y ejecuta el script [ESP32/REAL/test_hardware.py](file:///c:/Users/Elitebook222/Documents/GitHub/Vivero_Automatico_ESP32/ESP32/REAL/test_hardware.py).
3. **Paso A (Medición en Seco):** Con la pala al aire, anota el valor de `ADC Raw` que sale en consola y LCD:
   * *Anotar:* `VALOR_ADC_AIRE = _______`
4. **Paso B (Medición en Agua):** Sumerge la pala en un vaso con agua hasta la línea blanca:
   * *Anotar:* `VALOR_ADC_AGUA = _______` (debería caer notablemente respecto al aire).

---

## 5. Actualizar la Calibración en `main.py`

Con los dos valores obtenidos, abre [ESP32/REAL/main.py](file:///c:/Users/Elitebook222/Documents/GitHub/Vivero_Automatico_ESP32/ESP32/REAL/main.py) y colócalos en las líneas 44 y 45:

```python
# 3. CALIBRACIÓN DEL SENSOR CAPACITIVO v2.0
VALOR_ADC_AIRE = 3200  # <-- Sustituir con tu lectura al aire
VALOR_ADC_AGUA = 1400  # <-- Sustituir con tu lectura en agua
```

El firmware calculará automáticamente el porcentaje con la fórmula matemática:
$$\text{Porcentaje Humedad} = \left( \frac{\text{VALOR\_ADC\_AIRE} - \text{Lectura Raw}}{\text{VALOR\_ADC\_AIRE} - \text{VALOR\_ADC\_AGUA}} \right) \times 100$$

* Si Humedad $< 35.0\%$ $\rightarrow$ Bomba se **ENCIENDE**.
* Si Humedad $\ge 70.0\%$ $\rightarrow$ Bomba se **APAGA**.

---

## 6. Plan B de Respaldo Inmediato (Sensor Táctil Pin 32)

Si por cualquier motivo no tienes la resistencia o la placa no responde, el **sensor táctil capacitivo integrado del ESP32** ya fue probado y funciona al 100%:

* **Conexión:** Un solo cable jumper desde el pin **GPIO 32** directo a la tierra/agua (puedes ponerle un clip o clavo en la punta como sonda).
* **Calibración verificada:**
  * Aire: `650` (0% Humedad).
  * Húmedo: `200` (100% Humedad).
* **Lectura blindada en MicroPython:**
  ```python
  from machine import TouchPad, Pin
  touch = TouchPad(Pin(32))
  try:
      val = touch.read()
  except ValueError:
      val = 200 # Saturación máxima por agua
  ```

---

## 7. Checklist de Entrega del Proyecto (Jueves por la Noche)

- [ ] Sensor de humedad calibrado (en seco bomba riega, en mojado bomba para).
- [ ] Módulo Relé conectado en **GPIO 18** (`VIN`, `GND`, `IN`).
- [ ] Bomba sumergible conectada a `NO` y `COM` del relé.
- [ ] Pantalla LCD 16x2 en **GPIO 22** (SDA) y **GPIO 21** (SCL).
- [ ] Wi-Fi configurado con la red del lugar en [ESP32/REAL/main.py](file:///c:/Users/Elitebook222/Documents/GitHub/Vivero_Automatico_ESP32/ESP32/REAL/main.py):
  ```python
  WIFI_SSID     = "TU_RED"
  WIFI_PASSWORD = "TU_PASSWORD"
  ```
- [ ] API en Render recibiendo telemetría en `POST /api/v1/mediciones`.
- [ ] App de escritorio ejecutándose con `python main.py` mostrando gráficos y sectores.
