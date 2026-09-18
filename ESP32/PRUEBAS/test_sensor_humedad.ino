/**
 * ============================================================================
 * Proyecto    : SmartVivero IoT - Sistema de Riego y Climatización Automatizado
 * Archivo     : test_sensor_humedad.ino
 * Módulo      : Calibración y Diagnóstico de Sensor Capacitivo de Humedad de Suelo
 * Plataforma  : ESP-WROOM-32 (NodeMCU-32S / ESP32 DevKit v1)
 * Entorno     : Arduino IDE / PlatformIO
 * Versión     : 1.2.0
 * ============================================================================
 * 
 * DESCRIPCIÓN:
 * Banco de pruebas unitario para caracterización analógica, validación y
 * calibración en dos puntos (aire seco vs. saturación de agua) del sensor
 * de humedad capacitivo. Despliega lecturas en tiempo real a través del 
 * monitor serial y en pantalla LCD 1602 (I2C).
 *
 * BIBLIOTECAS REQUERIDAS:
 *  - "LiquidCrystal I2C" de Frank de Brabander (Gestor de librerías de Arduino)
 *  - "Wire" (Nativa del core ESP32)
 *  - "gravity_soil_moisture_sensor.h" (Librería local / DFRobot)
 *
 * ----------------------------------------------------------------------------
 * ESQUEMA DE CONEXIONES DE HARDWARE (PINOUT):
 * ----------------------------------------------------------------------------
 * 1. SENSOR DE HUMEDAD CAPACITIVO (v1.2 / Gravity DFRobot):
 *    - VCC  ---> Pin 3.3V del ESP32 (o VIN 5V según versión del módulo)
 *    - GND  ---> Pin GND del ESP32
 *    - AOUT ---> GPIO 34 (ADC1 Canal 6 - Solo entrada analógica, sin pull-up)
 *
 * 2. PANTALLA LCD 1602 CON MÓDULO I2C (PCF8574):
 *    - VCC  ---> Pin VIN (5V) para contraste y retroiluminación óptimos
 *    - GND  ---> Pin GND del ESP32
 *    - SDA  ---> GPIO 22 (Línea de datos I2C)
 *    - SCL  ---> GPIO 21 (Línea de reloj I2C)
 * ----------------------------------------------------------------------------
 *
 * PROCEDIMIENTO OPERATIVO ESTÁNDAR (SOP) DE CALIBRACIÓN:
 * 1. Conecte el ESP32 a la PC y abra el Monitor Serial a 115200 baudios.
 * 2. FASE AIRE (SECO - 0% HR):
 *    - Deje el sensor en el aire, completamente seco y limpio.
 *    - Observe el valor "ADC Crudo" estabilizado (rango típico: 3000 - 3800).
 *    - Anote este número como 'VALOR_ADC_AIRE'.
 * 3. FASE AGUA (SATURADO - 100% HR):
 *    - Sumerja la sonda en un vaso con agua SOLO hasta la línea blanca serigrafiada.
 *    - PRECAUCIÓN: Nunca sumerja los componentes electrónicos superiores ni cables.
 *    - Observe el valor "ADC Crudo" estabilizado (rango típico: 1200 - 1800).
 *    - Anote este número como 'VALOR_ADC_AGUA'.
 * 4. APLICACIÓN AL SISTEMA PRINCIPAL:
 *    - Transfiera ambos valores a las constantes de 'SmartVivero_REAL.ino':
 *        const int VALOR_ADC_AIRE = <valor_en_aire>;
 *        const int VALOR_ADC_AGUA = <valor_en_agua>;
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "gravity_soil_moisture_sensor.h"

// ─── 1. ASIGNACIÓN DE PINES Y PARÁMETROS DE HARDWARE ────────────────────────
#define PIN_SENSOR_HUMEDAD      34      // ADC1_CH6 (GPIO 34) - Entrada analógica dedicada
#define PIN_I2C_SDA             22      // GPIO 22 - Línea SDA del bus I2C
#define PIN_I2C_SCL             21      // GPIO 21 - Línea SCL del bus I2C
#define SERIAL_BAUD_RATE        115200  // Velocidad de transmisión UART (Serial Monitor)

// ─── 2. PARÁMETROS DE PANTALLA LCD I2C ──────────────────────────────────────
#define LCD_DIRECCION_I2C       0x27    // Dirección I2C base (0x27 habitual, o 0x3F)
#define LCD_COLUMNAS            16      // Cantidad de caracteres por fila
#define LCD_FILAS               2       // Cantidad de filas de texto

// ─── 3. PARÁMETROS DE MUESTREO Y ADQUISICIÓN DE DATOS ───────────────────────
#define SENSOR_MUESTRAS         20      // Número de muestras para filtrado y promediado
#define SENSOR_DELAY_MS         5       // Intervalo entre sub-muestras analógicas (ms)
#define INTERVALO_MUESTREO_MS   500UL   // Periodo del ciclo de muestreo y refresco (ms)

// ─── 4. CONSTANTES DE CALIBRACIÓN DE REFERENCIA ─────────────────────────────
// Valores de referencia iniciales basados en SmartVivero_REAL.ino.
// Actualice estos valores luego de realizar la prueba de calibración en dos puntos.
const int CAL_ADC_AIRE          = 3200; // Lectura en seco / aire (0% Humedad)
const int CAL_ADC_AGUA          = 1400; // Lectura sumergido en agua (100% Humedad)

// ─── 5. INSTANCIACIÓN DE DRIVERS Y VARIABLES GLOBALES ───────────────────────
GravitySoilMoistureSensor sensorHumedad;
LiquidCrystal_I2C lcd(LCD_DIRECCION_I2C, LCD_COLUMNAS, LCD_FILAS);

bool lcdDisponible              = false;
unsigned long tiempoUltimaLectura = 0;

// ─── 6. PROTOTIPOS DE FUNCIONES ─────────────────────────────────────────────
void  inicializarHardwareADC();
bool  inicializarDisplayLCD();
void  actualizarDisplayLCD(int rawAdc, float voltaje, float humedadPct);
void  imprimirTelemetriaSerial(uint16_t valorLibreria, int rawAdc, float voltaje, float humedadPct);
float calcularHumedadPorcentaje(int rawAdc);

// ════════════════════════════════════════════════════════════════════════════
// CONFIGURACIÓN INICIAL (SETUP)
// ════════════════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    delay(500);

    // 1. Configuración de hardware del conversor analógico
    inicializarHardwareADC();

    // 2. Encabezado de diagnóstico en consola serial
    Serial.println("\r\n============================================================");
    Serial.println("  SmartVivero IoT - BANCO DE PRUEBAS Y CALIBRACION ANALOGICA");
    Serial.println("============================================================");
    Serial.println("  Controlador : ESP-WROOM-32");
    Serial.println("  Sensor Pin  : GPIO 34 (ADC1_CH6, 12 bits, 0-3.3V)");
    Serial.printf ("  Bus I2C     : SDA=GPIO %d | SCL=GPIO %d | Dir=0x%02X\n", 
                   PIN_I2C_SDA, PIN_I2C_SCL, LCD_DIRECCION_I2C);
    Serial.println("------------------------------------------------------------");

    // 3. Inicialización del display LCD I2C
    lcdDisponible = inicializarDisplayLCD();
    if (lcdDisponible) {
        Serial.println("  [OK] Pantalla LCD 1602 detectada e inicializada correctamente.");
    }

    // 4. Inicialización del controlador del sensor de humedad
    if (sensorHumedad.Setup(PIN_SENSOR_HUMEDAD)) {
        Serial.println("  [OK] Sensor capacitivo enlazado correctamente con la libreria.");
    } else {
        Serial.println("  [INFO] Sensor conectado al pin analógico GPIO 34.");
    }

    // 5. Instrucciones de calibración para el operador
    Serial.println("------------------------------------------------------------");
    Serial.println("  INSTRUCCIONES DE CALIBRACION:");
    Serial.println("  1. FASE AIRE: Suspenda el sensor en aire seco.");
    Serial.println("     -> Anote el 'ADC Crudo' estabilizado como VALOR_ADC_AIRE.");
    Serial.println("  2. FASE AGUA: Sumerja la sonda hasta la linea blanca en agua.");
    Serial.println("     -> Anote el 'ADC Crudo' estabilizado como VALOR_ADC_AGUA.");
    Serial.println("  3. Traslade ambos valores al firmware de produccion (SmartVivero_REAL.ino).");
    Serial.println("============================================================\n");
    Serial.println("Timestamp(ms) | Val.Libreria | ADC Crudo | Voltaje(V) | Humedad(%)");
    Serial.println("--------------+--------------+-----------+------------+-----------");
}

// ════════════════════════════════════════════════════════════════════════════
// BUCLE PRINCIPAL (LOOP NO BLOQUEANTE)
// ════════════════════════════════════════════════════════════════════════════
void loop() {
    unsigned long tiempoActual = millis();

    // Muestreo cíclico temporizado mediante millis()
    if (tiempoActual - tiempoUltimaLectura >= INTERVALO_MUESTREO_MS) {
        tiempoUltimaLectura = tiempoActual;

        // 1. Adquisición analógica con promediado de muestras (librería Gravity)
        uint16_t valorLibreria = sensorHumedad.Read(SENSOR_MUESTRAS, SENSOR_DELAY_MS);

        // 2. Reconstrucción del valor ADC crudo (0 - 4095)
        int rawAdc = 4095 - valorLibreria;
        if (rawAdc < 0)    rawAdc = 0;
        if (rawAdc > 4095) rawAdc = 4095;

        // 3. Conversión a voltaje equivalente (escala 0.0V a 3.3V)
        float voltaje = rawAdc * (3.3f / 4095.0f);

        // 4. Estimación de humedad porcentual con umbrales de referencia
        float humedadPorcentaje = calcularHumedadPorcentaje(rawAdc);

        // 5. Salida de telemetría a monitor serial
        imprimirTelemetriaSerial(valorLibreria, rawAdc, voltaje, humedadPorcentaje);

        // 6. Actualización en tiempo real del display LCD
        actualizarDisplayLCD(rawAdc, voltaje, humedadPorcentaje);
    }
}

// ════════════════════════════════════════════════════════════════════════════
// SUBRUTINAS DE INICIALIZACIÓN Y CONFIGURACIÓN
// ════════════════════════════════════════════════════════════════════════════

/**
 * @brief Configura la resolución y el factor de atenuación del ADC del ESP32.
 */
void inicializarHardwareADC() {
    // 12 bits de resolución: rango numérico de 0 a 4095
    analogReadResolution(12);

    // Atenuación de 11 dB: rango de lectura de tensión entre 0 y ~3.3V
    analogSetAttenuation(ADC_11db);
}

/**
 * @brief Inicializa el bus I2C y comprueba la presencia de la pantalla LCD.
 * @return true si el display respondió positivamente al handshake I2C.
 */
bool inicializarDisplayLCD() {
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setClock(100000); // 100 kHz estándar: máxima inmunidad frente a transitorios
    delay(100);

    // Sondeo de confirmación en la dirección I2C configurada
    Wire.beginTransmission(LCD_DIRECCION_I2C);
    byte error = Wire.endTransmission();

    if (error == 0) {
        lcd.init();
        lcd.backlight();
        lcd.clear();

        // Pantalla de bienvenida (Splash Screen)
        lcd.setCursor(0, 0);
        lcd.print(" SMART VIVERO   ");
        lcd.setCursor(0, 1);
        lcd.print(" CALIBRADOR v1.2");
        delay(1500);

        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Iniciando test..");
        lcd.setCursor(0, 1);
        lcd.print("Sensor GPIO 34  ");
        delay(800);
        lcd.clear();

        return true;
    }

    // Diagnóstico en caso de fallo de comunicación I2C
    Serial.printf("  [ALERTA] No se detecto respuesta I2C en direccion 0x%02X (Error: %d).\n", 
                  LCD_DIRECCION_I2C, error);
    Serial.println("           Verifique conexiones SDA (GPIO 22), SCL (GPIO 21), VCC (5V)");
    Serial.println("           o intente cambiando LCD_DIRECCION_I2C a 0x3F.");
    return false;
}

// ════════════════════════════════════════════════════════════════════════════
// SUBRUTINAS DE PROCESAMIENTO Y VISUALIZACIÓN
// ════════════════════════════════════════════════════════════════════════════

/**
 * @brief Realiza la interpolación lineal inversa para obtener el porcentaje de humedad.
 * @param rawAdc Valor de lectura analógica entre 0 y 4095.
 * @return Porcentaje de humedad acotado entre 0.0% y 100.0%.
 */
float calcularHumedadPorcentaje(int rawAdc) {
    if (CAL_ADC_AIRE == CAL_ADC_AGUA) return 0.0f; // Previene indeterminación por división por cero

    float porcentaje = ((float)(CAL_ADC_AIRE - rawAdc) / 
                        (float)(CAL_ADC_AIRE - CAL_ADC_AGUA)) * 100.0f;

    // Saturación de límites para garantizar coherencia en la telemetría
    if (porcentaje < 0.0f)   porcentaje = 0.0f;
    if (porcentaje > 100.0f) porcentaje = 100.0f;

    return porcentaje;
}

/**
 * @brief Actualiza las 2 líneas del display LCD 1602 sin parpadeos.
 * @param rawAdc Valor ADC crudo del sensor (0-4095).
 * @param voltaje Voltaje medido en voltios.
 * @param humedadPct Porcentaje de humedad calculado.
 */
void actualizarDisplayLCD(int rawAdc, float voltaje, float humedadPct) {
    if (!lcdDisponible) return;

    // Verificación de integridad del bus I2C (mecanismo de auto-recuperación ante ruido)
    Wire.beginTransmission(LCD_DIRECCION_I2C);
    if (Wire.endTransmission() != 0) {
        Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
        Wire.setClock(100000);
        lcd.init();
        lcd.backlight();
    }

    char bufferLinea0[17];
    char bufferLinea1[17];

    // Fila 0: ADC Crudo y Tensión (Ejemplo: "ADC:3210   2.58V")
    snprintf(bufferLinea0, sizeof(bufferLinea0), "ADC:%4d  %4.2fV", rawAdc, voltaje);

    // Fila 1: Humedad calculada (Ejemplo: "Humedad:   48.5% ")
    snprintf(bufferLinea1, sizeof(bufferLinea1), "Humedad: %5.1f%% ", humedadPct);

    lcd.setCursor(0, 0);
    lcd.print(bufferLinea0);
    lcd.setCursor(0, 1);
    lcd.print(bufferLinea1);
}

/**
 * @brief Imprime en el monitor serial los datos formateados en tabla de telemetría.
 */
void imprimirTelemetriaSerial(uint16_t valorLibreria, int rawAdc, float voltaje, float humedadPct) {
    Serial.printf("  %10lu  |     %4d     |   %4d    |   %5.3fV   |  %5.1f%%\n",
                  millis(), valorLibreria, rawAdc, voltaje, humedadPct);
}
