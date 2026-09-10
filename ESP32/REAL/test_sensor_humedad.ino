/*
 ============================================================================
  SmartVivero - Test de Sensor de Humedad Capacitivo con Librería
 ============================================================================
  Propósito: Verificar que el sensor funciona usando la librería obligatoria
  "Gravity Soil Moisture Sensor" (DFRobot) y obtener los valores de
  calibración reales (ADC al aire seco y ADC en agua).

  Librería requerida:
  - "Gravity Soil Moisture Sensor" (instalada en Arduino/libraries)

  Conexión:
  - AOUT del sensor  -> GPIO 34 (ADC1)
  - VCC del sensor   -> 3.3V (o VIN 5V)
  - GND del sensor   -> GND

  Instrucciones:
  1. Sube este sketch al ESP32 desde el Arduino IDE.
  2. Abre el Serial Monitor a 115200 baudios.
  3. Con el sensor al AIRE -> anota el valor "ADC Crudo" (ej: ~3700)
  4. Mete el sensor en un VASO CON AGUA (hasta la línea blanca) -> anota "ADC Crudo"
  5. Copia esos valores en SmartVivero_REAL.ino:
       const int VALOR_ADC_AIRE = <valor al aire>;
       const int VALOR_ADC_AGUA = <valor en agua>;
 ============================================================================
*/

#include <Arduino.h>
#include "gravity_soil_moisture_sensor.h"

#define PIN_SENSOR    34      // GPIO 34 = ADC1_CH6
#define NUM_MUESTRAS  20      // Sobremuestreo gestionado por la librería

GravitySoilMoistureSensor sensorHumedad;

void setup() {
    Serial.begin(115200);
    delay(500);

    // Configurar ADC en ESP32: 12 bits (0-4095), rango 0-3.3V
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);

    Serial.println("=================================================");
    Serial.println("  SmartVivero - Test Sensor con LIBRERIA");
    Serial.println("=================================================");
    Serial.println("  Libreria: Gravity Soil Moisture Sensor (DFRobot)");
    Serial.println("  GPIO 34 | 12 bits (0-4095) | 0-3.3V");
    Serial.println("-------------------------------------------------");

    if (sensorHumedad.Setup(PIN_SENSOR)) {
        Serial.println("  [OK] Sensor inicializado correctamente con la libreria.");
    } else {
        Serial.println("  [INFO] Sensor conectado al pin GPIO 34.");
    }

    Serial.println("-------------------------------------------------");
    Serial.println("  PASO 1: Deja el sensor en el AIRE (seco)");
    Serial.println("          Anota el valor 'ADC Crudo' -> VALOR_ADC_AIRE");
    Serial.println("  PASO 2: Mete el sensor en un VASO CON AGUA");
    Serial.println("          (Sumergir solo hasta la linea blanca serigrafiada)");
    Serial.println("          Anota el valor 'ADC Crudo' -> VALOR_ADC_AGUA");
    Serial.println("=================================================\n");
}

void loop() {
    // Lectura a traves de la funcion de la libreria GravitySoilMoistureSensor
    uint16_t valorLibreria = sensorHumedad.Read(NUM_MUESTRAS, 5);

    // El valor de la libreria representa humedad creciente (4095 - raw).
    // Obtenemos el ADC crudo para la calibracion:
    int raw = 4095 - valorLibreria;
    if (raw < 0) raw = 0;
    if (raw > 4095) raw = 4095;

    // Voltaje aproximado (referencia 3.3V, 12 bits)
    float voltaje = raw * (3.3f / 4095.0f);

    // Porcentaje de humedad referencial de la libreria (0 a 100%)
    float pct_libreria = (valorLibreria / 4095.0f) * 100.0f;

    Serial.printf("Libreria: %4d  |  ADC Crudo: %4d  |  Voltaje: %.3fV  |  Humedad: %5.1f%%\n",
                  valorLibreria, raw, voltaje, pct_libreria);

    delay(500);
}
