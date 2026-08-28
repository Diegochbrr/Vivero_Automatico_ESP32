# Hardware y Firmware ESP32 — SmartVivero

## Microcontrolador y Entorno
- **Modelo:** ESP32 DevKit V1 (30 pines)
- **Lenguaje de Programación:** MicroPython
- **Simulador:** Wokwi Simulator (`ESP32/diagram.json` y `ESP32/main.py`)
- **Librerías I2C:** `ESP32/lcd_api.py` y `ESP32/machine_i2c_lcd.py`

## Pinout y Componentes Conectados

| Pin GPIO | Componente Conectado | Tipo de Entrada/Salida | Función en el Sistema |
| :--- | :--- | :---: | :--- |
| **GPIO 34** | Sensor de Humedad Capacitivo (Potenciómetro en Wokwi) | Entrada Analógica (ADC) | Lee el nivel de humedad del suelo en valores crudos de 0 a 4095. |
| **GPIO 18** | Switch de Nivel de Agua (Slide Switch) | Entrada Digital (PULL_UP) | Detecta si el depósito de agua tiene reserva (`HIGH` = Agua OK, `LOW` = Vacío). |
| **GPIO 19** | Botón de Riego Manual | Entrada Digital (PULL_UP) | Permite activar la electrobomba físicamente en campo (`LOW` = Presionado). |
| **GPIO 2**  | Módulo Relé de la Bomba de Agua (LED Verde) | Salida Digital | Activa (`1`) o desactiva (`0`) el paso de corriente a la electrobomba. |
| **GPIO 4**  | Diodo LED de Alerta Crítica (Rojo) | Salida Digital | Se ilumina (`1`) en caso de emergencia por reservorio vacío. |
| **GPIO 21** | Línea SDA del LCD I2C | Canal de Datos I2C | Envío de datos para la pantalla LCD 16x2 (Dirección: `0x27`). |
| **GPIO 22** | Línea SCL del LCD I2C | Canal de Reloj I2C | Señal de reloj sincronizada a 400 kHz. |

## Sensor de Humedad del Suelo
- **Tipo:** Sensor capacitivo de suelo (inmune a corrosión por contacto directo).
- **Resolución ADC:** 12 bits (0 a 4095 unidades).
- **Atenuación configurada:** `ADC.ATTN_11DB` (permite medir voltajes de 0.0V hasta 3.3V).
- **Técnica de lectura (Sobremuestreo Antirruido):**  
  El microcontrolador realiza 10 lecturas consecutivas con intervalos de 5 ms entre cada muestra y calcula el promedio aritmético:
  $$\text{ADC}_{\text{promedio}} = \frac{1}{10} \sum_{i=1}^{10} \text{ADC}_i$$
- **Conversión a Porcentaje:**
  $$\text{Porcentaje Humedad} = \left( \frac{\text{ADC}_{\text{promedio}}}{4095.0} \right) \times 100.0$$

## Lógica de Control del Riego (Firmware en MicroPython)

El ESP32 ejecuta un bucle infinito estructurado con las siguientes reglas de prioridad:

### Regla 1 — Prioridad Máxima: Seguridad por Nivel de Agua
Si el switch de flotador (`GPIO18`) reporta nivel bajo (`0` / `LOW`):
1. Se desactiva inmediatamente la bomba (`GPIO2 = 0`).
2. Se activa el LED rojo de advertencia (`GPIO4 = 1`).
3. El LCD 16x2 muestra:
   - Línea 1: `Hum: XX.X% [S{sector}]`
   - Línea 2: `ALERTA: Sin Agua`
4. Se despacha de inmediato una alerta HTTP POST a la API con `nivel_detectado = "CRITICO_VACIO"` y `bomba_bloqueada = true`.

### Regla 2 — Comandos Remotos desde la Nube
Si el backend entrega una orden de forzar riego (`duracion_segundos > 0`) para el sector activo y hay agua en el reservorio:
1. La bomba se activa (`GPIO2 = 1`) durante el tiempo establecido.
2. Se envía un `DELETE /api/v1/comandos/forzar-riego/{id_sector}` para confirmar que el comando fue procesado (ACK).

### Regla 3 — Riego Manual Físico
Si el botón pulsador en `GPIO19` se mantiene presionado (`LOW`) y hay agua:
1. La bomba se enciende (`GPIO2 = 1`).
2. El LCD muestra `Bomba: REGANDO (M)`.

### Regla 4 — Riego Automático por Umbral de Humedad
Si la humedad del suelo cae por debajo del umbral mínimo configurado (por defecto `< 35.0%`) y el reservorio contiene agua:
1. La electrobomba se enciende automáticamente (`GPIO2 = 1`).
2. El LCD muestra:
   - Línea 1: `Hum: XX.X% [S{sector}]`
   - Línea 2: `Bomba: REGANDO`

### Regla 5 — Estado de Reposo
Si la humedad está en rango óptimo ($\ge 35.0\%$), no hay comandos ni pulsación manual:
1. La bomba permanece apagada (`GPIO2 = 0`).
2. El LED rojo permanece apagado (`GPIO4 = 0`).
3. El LCD muestra:
   - Línea 1: `Hum: XX.X% [S{sector}]`
   - Línea 2: `Bomba: APAGADA`

## Pantalla LCD 16x2 (I2C)
- **Controlador:** HD44780 con expansor PCF8574 en dirección `0x27`.
- **Frecuencia I2C:** 400 kHz.
- **Distribución de pantalla:**
  - Línea 1: Porcentaje de humedad en tiempo real e identificador de sector activo (ej: `Hum:  42.3% [S1]`).
  - Línea 2: Estado del actuador (`Bomba: REGANDO`, `Bomba: APAGADA` o `ALERTA: Sin Agua`).

## Conectividad WiFi y Comunicación con la Nube
- **Red Wi-Fi en Wokwi:** `Wokwi-GUEST` (sin contraseña).
- **Librería HTTP:** `urequests` en MicroPython.
- **Frecuencia de ciclo de telemetría:** Cada 5000 ms (5 segundos), gestionada con `time.ticks_ms()` para evitar pausas bloqueantes.
- **Autenticación:** Cabecera HTTP `X-API-Key: sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d`.
- **Sincronización Dinámica de Sector:** En cada ciclo, el ESP32 consulta `GET /api/v1/sistema/sector-activo` para sincronizar su variable `id_sector` con el sector seleccionado por los operadores en la aplicación de escritorio.

## Payloads Enviados por el ESP32 a la API

### Telemetría Periódica (`POST /api/v1/mediciones`)
```json
{
  "id_sensor": "SEN-CAP-S01",
  "id_sector": 1,
  "humedad_porcentaje": 42.35,
  "valor_adc_crudo": 1734
}
```

### Alerta de Reservorio Vacío (`POST /api/v1/alertas`)
```json
{
  "id_sector": 1,
  "nivel_detectado": "CRITICO_VACIO",
  "bomba_bloqueada": true,
  "observacion": "Alerta de nivel de agua detectada por ESP32"
}
```

## Tabla de Referencia: Relación ADC → Humedad del Suelo

| Rango ADC | Humedad (%) | Diagnóstico del Suelo | Estado de la Bomba |
| :---: | :---: | :--- | :---: |
| **0 – 400** | 0.0% – 9.8% | Suelo extremadamente seco / Árido | **ENCENDIDA** |
| **401 – 1432** | 9.8% – 34.9% | Suelo seco (bajo el umbral de 35%) | **ENCENDIDA** |
| **1433 – 2800** | 35.0% – 68.4% | Humedad óptima de cultivo | **APAGADA** |
| **2801 – 3600** | 68.5% – 87.9% | Suelo muy húmedo | **APAGADA** |
| **3601 – 4095** | 88.0% – 100.0% | Suelo saturado / Encharcado | **APAGADA** |
