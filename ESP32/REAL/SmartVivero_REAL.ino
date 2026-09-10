/*
 ============================================================================
  SmartVivero IoT - Firmware Unificado Físico ESP32 (Arduino C++)
 ============================================================================
  Integra en un solo microcontrolador:
  1. Control por Voz / App con Google Home & Alexa (SinricPro en tiempo real).
  2. Riego automático inteligente por umbral de humedad de suelo.
  3. Lectura de sensor capacitivo con librería oficial (Gravity DFRobot).
  4. Despliegue de datos en Pantalla LCD 16x2 I2C (PCF8574).
  5. Comunicación y telemetría periódica con la API Cloud (PostgreSQL Neon).

  Hardware Conectado:
  - ESP32 DevKit V1 (30 pines)
  - Pantalla LCD 16x2 I2C: SDA = GPIO 22, SCL = GPIO 21 (Dir: 0x27)
  - Sensor Humedad Capacitivo v1.2: AOUT -> GPIO 34 (ADC1), VCC -> 3.3V
  - Módulo Relé 5V: IN -> GPIO 18 (Controlado en Alta Impedancia Hi-Z)
  - Bomba de Agua Sumergible 5V

  Librerías instaladas:
  - "SinricPro" y "WebSockets"
  - "LiquidCrystal I2C" de Frank de Brabander
  - "ArduinoJson" de Benoit Blanchon
  - "Gravity Soil Moisture Sensor" de Mihai Dinculescu (DFRobot)
 ============================================================================
*/

#ifdef ENABLE_DEBUG
   #define DEBUG_ESP_PORT Serial
   #define NODEBUG_WEBSOCKETS
   #define NDEBUG
#endif 

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <LiquidCrystal_I2C.h>
#include <gravity_soil_moisture_sensor.h>
#include "SinricPro.h"
#include "SinricProSwitch.h"

// ─── 1. CREDENCIALES WI-FI ────────────────────────────────────────────────
const char* WIFI_SSID     = "iPhone";
const char* WIFI_PASSWORD = "Diego123";

// ─── 2. CREDENCIALES SINRICPRO (GOOGLE HOME) ──────────────────────────────
#define APP_KEY           "087703d1-88c1-4f45-a7c9-8d3624596c24"
#define APP_SECRET        "39d2a459-a77e-4c42-bee8-df86ea20f0fa-c43024d7-0fe9-4637-8684-ae3d9e6992bc"
#define SWITCH_ID_1       "6aa2184ab3889c3a11adc017"

// ─── 3. CREDENCIALES API REST BACKEND ─────────────────────────────────────
const char* API_BASE = "https://vivero-automatico-esp32.onrender.com/api/v1";
const char* API_KEY  = "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d";

// ─── 4. DEFINICIÓN DE PINES ───────────────────────────────────────────────
#define PIN_SENSOR_HUMEDAD  34    // ADC1_CH6 – Sensor capacitivo
#define PIN_RELE_BOMBA      18    // Relé de la bomba (GPIO 18)
#define BAUD_RATE           115200

// ─── 5. CALIBRACIÓN DEL SENSOR CAPACITIVO ─────────────────────────────────
const int VALOR_ADC_AIRE = 3200;  // Lectura en seco / aire  (0%  Humedad)
const int VALOR_ADC_AGUA = 1400;  // Lectura en vaso de agua (100% Humedad)

// ─── 6. PARÁMETROS DEL SISTEMA ────────────────────────────────────────────
int   ID_SECTOR            = 1;
float HUM_MIN_ON           = 35.0f;  // Enciende si humedad < este %
float HUM_MAX_OFF          = 70.0f;  // Apaga si humedad >= este %
int   TIEMPO_MAX_RIEGO_SEG = 180;

// ─── 7. ESTADOS GLOBALES DE CONTROL ───────────────────────────────────────
bool bomba_activa         = false;
bool riego_por_google     = false;
unsigned long bloqueo_auto_hasta = 0;  // Pausa temporal tras apagar por voz

float humedadActual       = 50.0f;
int   rawAdcActual        = 2300;

// Temporizadores no bloqueantes
const unsigned long INTERVALO_ENVIO_MS  = 5000UL;  // Cada 5 seg telemetría
const unsigned long INTERVALO_SENSOR_MS = 1000UL;  // Cada 1 seg lectura LCD
unsigned long ultimoEnvioApi            = 0;
unsigned long ultimoCicloSensor         = 0;

// ─── 8. OBJETOS DE HARDWARE ───────────────────────────────────────────────
LiquidCrystal_I2C lcd(0x27, 16, 2);
GravitySoilMoistureSensor sensorHumedad;

// ─── PROTOTIPOS DE FUNCIONES ──────────────────────────────────────────────
void  setupWiFi();
void  setupSinricPro();
void  fijarBomba(bool activar);
float leerHumedad(int &rawOut);
void  actualizarLcd();
void  procesarRiegoAutomatico();
void  consultarConfigYComandos();
void  enviarTelemetriaApi(float humedad, int rawAdc);

// ══════════════════════════════════════════════════════════════════════════
// CALLBACK GOOGLE HOME / SINRICPRO
// ══════════════════════════════════════════════════════════════════════════
bool onPowerState1(const String &deviceId, bool &state) {
    Serial.printf("\r\n[Google Home]: Orden de voz recibida -> Bomba %s\r\n", state ? "ENCENDIDA" : "APAGADA");

    if (state) {
        // Encendido manual forzado por voz
        riego_por_google = true;
        bloqueo_auto_hasta = 0;
        fijarBomba(true);
    } else {
        // Apagado forzado por voz (tiene prioridad total)
        riego_por_google = false;
        fijarBomba(false);
        // Pausa de 60 segundos antes de que el modo automático pueda volver a actuar
        bloqueo_auto_hasta = millis() + 60000UL;
        Serial.println("[Google Home]: Modo automatico pausado por 60s tras apagado manual.");
    }

    actualizarLcd();
    return true; // Petición procesada correctamente
}

// ══════════════════════════════════════════════════════════════════════════
// SETUP PRINCIPAL
// ══════════════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(BAUD_RATE);
    delay(500);
    Serial.println("\r\n=================================================");
    Serial.println("  SmartVivero IoT - Firmware Físico + Google Home");
    Serial.println("=================================================");

    // 1. Inicializar pantalla LCD I2C en pines SDA=22, SCL=21
    Wire.begin(22, 21);
    delay(100);
    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("VIVERO AUTO");
    lcd.setCursor(0, 1);
    lcd.print("Iniciando...");

    // 2. Inicializar relé en modo seguro (apagado mediante Hi-Z)
    fijarBomba(false);

    // 3. Configurar ADC de 12 bits para el sensor de humedad
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);
    sensorHumedad.Setup(PIN_SENSOR_HUMEDAD);

    // 4. Conectar a red Wi-Fi
    setupWiFi();

    // 5. Configurar e iniciar cliente SinricPro para Google Home
    setupSinricPro();

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("SISTEMA LISTO");
    lcd.setCursor(0, 1);
    lcd.print("Google Home: OK");
    delay(1500);
    lcd.clear();
}

// ══════════════════════════════════════════════════════════════════════════
// LOOP PRINCIPAL (COMPLETAMENTE NO BLOQUEANTE)
// ══════════════════════════════════════════════════════════════════════════
void loop() {
    // Escucha permanente de comandos de Google Home en tiempo real
    SinricPro.handle();

    unsigned long ahora = millis();

    // Ciclo 1: Lectura de sensor y actualización de pantalla (cada 1 seg)
    if (ahora - ultimoCicloSensor >= INTERVALO_SENSOR_MS) {
        ultimoCicloSensor = ahora;
        
        int raw = 0;
        humedadActual = leerHumedad(raw);
        rawAdcActual = raw;

        procesarRiegoAutomatico();
        actualizarLcd();
    }

    // Ciclo 2: Telemetría y sincronización con API REST (cada 5 seg)
    if (ahora - ultimoEnvioApi >= INTERVALO_ENVIO_MS) {
        ultimoEnvioApi = ahora;

        consultarConfigYComandos();
        enviarTelemetriaApi(humedadActual, rawAdcActual);
    }
}

// ══════════════════════════════════════════════════════════════════════════
// CONTROL SEGURO DE LA BOMBA (ALTA IMPEDANCIA Hi-Z)
// ══════════════════════════════════════════════════════════════════════════
void fijarBomba(bool activar) {
    bomba_activa = activar;
    if (activar) {
        pinMode(PIN_RELE_BOMBA, OUTPUT);
        digitalWrite(PIN_RELE_BOMBA, LOW);   // Activa relé (conduce a GND)
    } else {
        pinMode(PIN_RELE_BOMBA, INPUT);      // Desconecta pin (flotante / apaga 100%)
    }
}

// ══════════════════════════════════════════════════════════════════════════
// LÓGICA DE RIEGO AUTOMÁTICO COORDINA CON GOOGLE HOME
// ══════════════════════════════════════════════════════════════════════════
void procesarRiegoAutomatico() {
    // Si la bomba fue encendida por voz desde Google Home, se respeta la orden manual
    if (riego_por_google) {
        return;
    }

    // Si el usuario apagó por voz recientemente, respetar la pausa de seguridad
    if (millis() < bloqueo_auto_hasta) {
        return;
    }

    // Modo Automático por umbrales de humedad de suelo
    if (humedadActual < HUM_MIN_ON && !bomba_activa) {
        Serial.printf("[AutoRiego] Humedad baja (%.1f%% < %.1f%%) -> Encendiendo Bomba\n", humedadActual, HUM_MIN_ON);
        fijarBomba(true);

        // Notificar el estado a la app de Google Home
        SinricProSwitch& mySwitch = SinricPro[SWITCH_ID_1];
        mySwitch.sendPowerStateEvent(true);
    } 
    else if (humedadActual >= HUM_MAX_OFF && bomba_activa) {
        Serial.printf("[AutoRiego] Humedad optima alcanzada (%.1f%% >= %.1f%%) -> Apagando Bomba\n", humedadActual, HUM_MAX_OFF);
        fijarBomba(false);

        // Notificar el estado a la app de Google Home
        SinricProSwitch& mySwitch = SinricPro[SWITCH_ID_1];
        mySwitch.sendPowerStateEvent(false);
    }
}

// ══════════════════════════════════════════════════════════════════════════
// PANTALLA LCD 16x2
// ══════════════════════════════════════════════════════════════════════════
void actualizarLcd() {
    // Fila 0: Sector y porcentaje de humedad
    char fila0[17];
    snprintf(fila0, sizeof(fila0), "S%d Hum:%5.1f%%  ", ID_SECTOR, humedadActual);
    lcd.setCursor(0, 0);
    lcd.print(fila0);

    // Fila 1: Estado del actuador
    lcd.setCursor(0, 1);
    if (riego_por_google) {
        lcd.print("Bomba: GOOGLE ON");
    } else if (bomba_activa) {
        lcd.print("Bomba: REGANDO  ");
    } else if (millis() < bloqueo_auto_hasta) {
        lcd.print("Bomba: PAUSA VOZ");
    } else {
        lcd.print("Bomba: APAGADA  ");
    }
}

// ══════════════════════════════════════════════════════════════════════════
// LECTURA DEL SENSOR CAPACITIVO CON LIBRERÍA DFRobot
// ══════════════════════════════════════════════════════════════════════════
float leerHumedad(int &rawOut) {
    uint16_t valorLib = sensorHumedad.Read(15, 5);

    int raw = 4095 - valorLib;
    if (raw < 0) raw = 0;
    if (raw > 4095) raw = 4095;
    rawOut = raw;

    float porcentaje = ((float)(VALOR_ADC_AIRE - raw) /
                        (float)(VALOR_ADC_AIRE - VALOR_ADC_AGUA)) * 100.0f;

    if (porcentaje < 0.0f)   porcentaje = 0.0f;
    if (porcentaje > 100.0f) porcentaje = 100.0f;

    return porcentaje;
}

// ══════════════════════════════════════════════════════════════════════════
// CONEXIÓN WI-FI
// ══════════════════════════════════════════════════════════════════════════
void setupWiFi() {
    Serial.printf("\r\n[WiFi]: Conectando a %s", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 30) {
        delay(300);
        Serial.print(".");
        intentos++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\r\n[WiFi]: Conectado con exito! IP: %s\r\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\r\n[WiFi]: No se pudo conectar de inmediato. Reintentando en segundo plano...");
    }
}

// ══════════════════════════════════════════════════════════════════════════
// INICIALIZACIÓN SINRICPRO (GOOGLE HOME)
// ══════════════════════════════════════════════════════════════════════════
void setupSinricPro() {
    SinricProSwitch& mySwitch1 = SinricPro[SWITCH_ID_1];
    mySwitch1.onPowerState(onPowerState1);

    SinricPro.onConnected([](){ 
        Serial.println("[SinricPro]: Conectado a la nube de Google Home!"); 
    }); 
    SinricPro.onDisconnected([](){ 
        Serial.println("[SinricPro]: Desconectado de SinricPro"); 
    });

    SinricPro.begin(APP_KEY, APP_SECRET);
    SinricPro.restoreDeviceStates(true);
}

// ══════════════════════════════════════════════════════════════════════════
// COMUNICACIÓN CON LA API REST EN LA NUBE
// ══════════════════════════════════════════════════════════════════════════
void consultarConfigYComandos() {
    if (WiFi.status() != WL_CONNECTED) return;

    HTTPClient http;

    // 1. Sincronizar sector activo actual
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
                Serial.printf("[Sector] Sincronizado con app de escritorio -> Sector %d\n", ID_SECTOR);
            }
        }
    }
    http.end();

    // 2. Consultar umbrales y comandos de forzado web
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
                Serial.printf("[API Web]: Comando de forzado remoto recibido (%ds)!\n", duracion);

                fijarBomba(true);
                actualizarLcd();

                // ACK inmediato a la API
                http.end();
                String urlAck = String(API_BASE) + "/comandos/forzar-riego/" + String(ID_SECTOR);
                http.begin(urlAck);
                http.addHeader("X-API-Key", API_KEY);
                http.sendRequest("DELETE");
            }
        }
    }
    http.end();
}

void enviarTelemetriaApi(float humedad, int rawAdc) {
    if (WiFi.status() != WL_CONNECTED) return;

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
    if (httpCode > 0) {
        Serial.printf("[API] Telemetria enviada: Humedad %.1f%% | ADC %d | HTTP %d\n", humedad, rawAdc, httpCode);
    }
    http.end();
}
