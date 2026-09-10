/*
 ============================================================================
  SmartVivero - Firmware Definitivo Físico en Arduino (C++)
 ============================================================================
  Hardware Conectado:
  - ESP32 DevKit V1
  - Pantalla LCD 16x2 I2C (PCF8574): SDA = GPIO 21, SCL = GPIO 22 (Dir: 0x27)
  - Sensor Humedad Capacitivo v1.2:  AOUT -> GPIO 34 (ADC1), VCC -> 3.3V
  - Módulo Relé 1 Canal:             IN   -> GPIO 18, COM -> 5V, NO -> Bomba (+)
  - Mini Bomba Sumergible 5V

  Librerías requeridas (instalar en Arduino IDE -> Sketch -> Manage Libraries):
  - "LiquidCrystal I2C"            de Frank de Brabander
  - "ArduinoJson"                  de Benoit Blanchon
  - "Gravity Soil Moisture Sensor" de Mihai Dinculescu (DFRobot)
 ============================================================================
*/

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <LiquidCrystal_I2C.h>
#include "gravity_soil_moisture_sensor.h"

// ─── 1. CREDENCIALES WI-FI Y API CLOUD ────────────────────────────────────
const char* WIFI_SSID     = "iPhone";
const char* WIFI_PASSWORD = "Diego123";

const char* API_BASE = "https://vivero-automatico-esp32.onrender.com/api/v1";
const char* API_KEY  = "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d";

// ─── 2. DEFINICIÓN DE PINES ───────────────────────────────────────────────
#define PIN_SENSOR_HUMEDAD  34    // ADC1 – Sensor capacitivo
#define PIN_RELE_BOMBA      18    // Relé de la bomba

// La mayoría de relés son activos en nivel BAJO (LOW / 0V).
// Si tu relé se activa al revés, pon false.
#define RELE_ACTIVE_LOW     true

// ─── 3. CALIBRACIÓN DEL SENSOR CAPACITIVO v1.2 ────────────────────────────
// Ajusta estos valores con lo que mediste en tu sensor:
const int VALOR_ADC_AIRE = 3200;  // Sensor en seco / aire  (0%  Humedad)
const int VALOR_ADC_AGUA = 1400;  // Sensor en vaso de agua (100% Humedad)

// ─── 4. PARÁMETROS DEL SISTEMA ────────────────────────────────────────────
int   ID_SECTOR            = 1;
float HUM_MIN_ON           = 35.0f;  // Enciende bomba si humedad < este %
float HUM_MAX_OFF          = 70.0f;  // Apaga bomba si humedad >= este %
int   TIEMPO_MAX_RIEGO_SEG = 180;
bool  bomba_activa         = false;

// ─── 5. INTERVALO DE ENVÍO A LA API ───────────────────────────────────────
const unsigned long INTERVALO_ENVIO_MS = 5000UL;   // cada 5 segundos

// ─── 6. OBJETOS DE HARDWARE (LIBRERÍAS) ──────────────────────────────────
// La dirección se detecta automáticamente en setup() (0x27 o 0x3F son comunes)
LiquidCrystal_I2C lcd(0x27, 16, 2);  // se reinicializa si se detecta 0x3F
GravitySoilMoistureSensor sensorHumedad;

// ─── PROTOTIPOS ────────────────────────────────────────────────────────────
bool  conectarWifi();
void  fijarBomba(bool activar);
float leerHumedad(int &rawOut);
void  consultarConfigYComandos();
void  enviarTelemetriaApi(float humedad, int rawAdc);

// ══════════════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(115200);
    delay(500);

    // ── Inicializar I2C: SDA=22, SCL=21 (igual que el código de prueba) ──────
    Wire.begin(22, 21);   // SDA=GPIO 22, SCL=GPIO 21
    delay(100);

    // Inicializar LCD (dirección 0x27 confirmada)
    lcd = LiquidCrystal_I2C(0x27, 16, 2);
    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("VIVERO AUTO");
    lcd.setCursor(0, 1);
    lcd.print("Conectando WiFi");

    // Inicializar relé (apagado desde el inicio)
    pinMode(PIN_RELE_BOMBA, OUTPUT);
    fijarBomba(false);

    // Configurar ADC de 12 bits para el sensor (0-4095)
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);   // Rango 0-3.3 V

    // Inicializar sensor capacitivo con la librería
    sensorHumedad.Setup(PIN_SENSOR_HUMEDAD);

    // Conectar Wi-Fi
    bool conectado = conectarWifi();

    lcd.clear();
    if (conectado) {
        String ip = WiFi.localIP().toString();
        Serial.println("[WiFi] Conectado! IP: " + ip);
        lcd.setCursor(0, 0);
        lcd.print("WiFi Conectado!");
        lcd.setCursor(0, 1);
        lcd.print(ip.substring(0, 16));
    } else {
        Serial.println("[WiFi] No conectado. Modo Offline local.");
        lcd.setCursor(0, 0);
        lcd.print("Modo Offline");
        lcd.setCursor(0, 1);
        lcd.print("Sin conexion");
    }
    delay(2000);
    lcd.clear();
}

// ══════════════════════════════════════════════════════════════════════════
unsigned long ultimoEnvioApi = 0;

void loop() {
    int   rawAdc;
    float humedad = leerHumedad(rawAdc);

    // Logica de riego automatico
    if (humedad < HUM_MIN_ON) {
        fijarBomba(true);
    } else if (humedad >= HUM_MAX_OFF) {
        fijarBomba(false);
    }

    // Actualizar pantalla LCD
    char fila0[17];
    snprintf(fila0, sizeof(fila0), "S%d Hum:%5.1f%%  ", ID_SECTOR, humedad);
    lcd.setCursor(0, 0);
    lcd.print(fila0);

    lcd.setCursor(0, 1);
    if (bomba_activa) {
        lcd.print("Bomba: REGANDO  ");
    } else {
        lcd.print("Bomba: APAGADA  ");
    }

    // Ciclo de comunicacion periodica con la nube (cada 5 seg)
    unsigned long ahora = millis();
    if (ahora - ultimoEnvioApi >= INTERVALO_ENVIO_MS) {
        ultimoEnvioApi = ahora;
        consultarConfigYComandos();
        enviarTelemetriaApi(humedad, rawAdc);
    }

    delay(200);
}

// ══════════════════════════════════════════════════════════════════════════
// FUNCIONES
// ══════════════════════════════════════════════════════════════════════════

bool conectarWifi() {
    if (WiFi.status() == WL_CONNECTED) return true;

    Serial.println("Inicializando WiFi...");
    WiFi.disconnect(true);
    delay(200);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    Serial.print("Conectando a WiFi: ");
    Serial.print(WIFI_SSID);

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 25) {
        delay(400);
        Serial.print(".");
        intentos++;
    }
    Serial.println();
    return (WiFi.status() == WL_CONNECTED);
}

void fijarBomba(bool activar) {
    bomba_activa = activar;
    // Control seguro mediante alta impedancia (Hi-Z) para módulo relé de 5V
    if (activar) {
        pinMode(PIN_RELE_BOMBA, OUTPUT);
        digitalWrite(PIN_RELE_BOMBA, LOW);
    } else {
        pinMode(PIN_RELE_BOMBA, INPUT);
    }
}

float leerHumedad(int &rawOut) {
    // Lectura mediante la librería oficial GravitySoilMoistureSensor
    uint16_t valorLib = sensorHumedad.Read(15, 5);

    // Recuperamos el valor ADC crudo equivalente (para telemetría y calibración)
    int raw = 4095 - valorLib;
    if (raw < 0) raw = 0;
    if (raw > 4095) raw = 4095;
    rawOut = raw;

    // Mapeo inverso calibrado
    float porcentaje = ((float)(VALOR_ADC_AIRE - raw) /
                        (float)(VALOR_ADC_AIRE - VALOR_ADC_AGUA)) * 100.0f;

    if (porcentaje < 0.0f)   porcentaje = 0.0f;
    if (porcentaje > 100.0f) porcentaje = 100.0f;

    return porcentaje;
}

void consultarConfigYComandos() {
    if (WiFi.status() != WL_CONNECTED) {
        if (!conectarWifi()) return;
    }

    HTTPClient http;

    // 1. Sincronizar Sector Activo
    String urlSec = String(API_BASE) + "/sistema/sector-activo";
    http.begin(urlSec);
    http.addHeader("X-API-Key", API_KEY);
    int codeSec = http.GET();
    if (codeSec == 200) {
        String body = http.getString();
        JsonDocument docSec;
        if (deserializeJson(docSec, body) == DeserializationError::Ok) {
            int nuevoSec = docSec["sector_activo"] | ID_SECTOR;
            if (nuevoSec != ID_SECTOR) {
                ID_SECTOR = nuevoSec;
                Serial.printf("[Sector] Sincronizado a Sector %d\n", ID_SECTOR);
            }
        }
    }
    http.end();

    // 2. Consultar umbrales y comandos del sector activo
    String urlCmd = String(API_BASE) + "/comandos/" + String(ID_SECTOR);
    http.begin(urlCmd);
    http.addHeader("X-API-Key", API_KEY);
    int codeCmd = http.GET();

    if (codeCmd == 200) {
        String bodyCmd = http.getString();
        JsonDocument docCmd;
        if (deserializeJson(docCmd, bodyCmd) == DeserializationError::Ok) {
            HUM_MIN_ON           = docCmd["humedad_min_on"]       | HUM_MIN_ON;
            HUM_MAX_OFF          = docCmd["humedad_max_off"]      | HUM_MAX_OFF;
            TIEMPO_MAX_RIEGO_SEG = docCmd["tiempo_max_riego_seg"] | TIEMPO_MAX_RIEGO_SEG;

            bool forzar = docCmd["forzar_riego"] | false;
            if (forzar) {
                int duracion = docCmd["duracion_forzado_seg"] | 15;
                Serial.printf("[Comando] Riego forzado! Regando por %ds\n", duracion);

                lcd.setCursor(0, 1);
                lcd.print("Forzado: REGANDO");

                fijarBomba(true);
                delay((unsigned long)duracion * 1000UL);
                fijarBomba(false);

                // ACK: DELETE /api/v1/comandos/forzar-riego/{ID_SECTOR}
                http.end();
                String urlAck = String(API_BASE) + "/comandos/forzar-riego/" + String(ID_SECTOR);
                http.begin(urlAck);
                http.addHeader("X-API-Key", API_KEY);
                int codeAck = http.sendRequest("DELETE");
                Serial.printf("[ACK] DELETE confirmado: %d\n", codeAck);
            }
        }
    } else {
        Serial.printf("[API] Error comandos: HTTP %d\n", codeCmd);
    }
    http.end();
}

void enviarTelemetriaApi(float humedad, int rawAdc) {
    if (WiFi.status() != WL_CONNECTED) {
        if (!conectarWifi()) return;
    }

    JsonDocument payload;
    payload["id_sensor"]          = "SEN-CAP-S01";
    payload["id_sector"]          = ID_SECTOR;
    payload["humedad_porcentaje"] = round(humedad * 100.0f) / 100.0f;
    payload["valor_adc_crudo"]    = rawAdc;

    String jsonStr;
    serializeJson(payload, jsonStr);

    HTTPClient http;
    String url = String(API_BASE) + "/mediciones";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", API_KEY);

    int httpCode = http.POST(jsonStr);
    Serial.printf("[API] Medicion enviada: HTTP %d\n", httpCode);
    http.end();
}
