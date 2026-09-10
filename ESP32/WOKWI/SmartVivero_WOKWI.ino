/*
 ============================================================================
  SmartVivero - Firmware Wokwi/Simulacion en Arduino (C++)
 ============================================================================
  Circuito simulado en Wokwi:
  - ESP32 DevKit V1
  - LCD 16x2 I2C:         SDA = GPIO 21,  SCL = GPIO 22
  - Potenciómetro (ADC):  SIG -> GPIO 34  (simula sensor de humedad)
  - Switch deslizante:    salida -> GPIO 18 (simula nivel de agua, PULL_UP)
  - Botón manual:         salida -> GPIO 19 (PULL_UP, activo en LOW)
  - LED verde bomba:      GPIO 2
  - LED rojo alerta:      GPIO 4

  Librerías requeridas:
  - "LiquidCrystal I2C"  de Frank de Brabander
  - "ArduinoJson"        de Benoit Blanchon
 ============================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <LiquidCrystal_I2C.h>

// ─── 1. CREDENCIALES Y API ─────────────────────────────────────────────────
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// Cambia por tu URL de ngrok o por la URL de Render directamente:
const char* API_BASE = "https://vivero-automatico-esp32.onrender.com/api/v1";
const char* API_KEY  = "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d";

// ─── 2. PINES ──────────────────────────────────────────────────────────────
#define PIN_SENSOR_HUMEDAD  34    // ADC – Potenciometro en Wokwi
#define PIN_NIVEL_AGUA      18    // Switch (nivel agua OK = HIGH con PULL_UP)
#define PIN_BOTON_MANUAL    19    // Boton (activo en LOW con PULL_UP)
#define PIN_RELE_BOMBA       2    // LED verde (simula bomba)
#define PIN_LED_ALERTA       4    // LED rojo  (simula alerta)

// ─── 3. PARÁMETROS DEL SISTEMA ────────────────────────────────────────────
int   ID_SECTOR            = 4;
float HUM_MIN_ON           = 35.0f;
float HUM_MAX_OFF          = 70.0f;
int   TIEMPO_MAX_RIEGO_SEG = 180;

const unsigned long INTERVALO_ENVIO_MS = 5000UL;

// ─── 4. LCD ────────────────────────────────────────────────────────────────
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ─── Estado ────────────────────────────────────────────────────────────────
bool  alertaEnviadaPrevia = false;

// ─── PROTOTIPOS ────────────────────────────────────────────────────────────
bool  conectarWifi();
float leerHumedad(int &rawOut);
void  consultarConfigYComandos(bool &forzar, int &duracionForzado);
void  confirmarRiegoForzado();
void  enviarDatosApi(float humedad, int rawAdc, bool nivelAguaOk);

// ══════════════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(115200);

    // Pines de salida
    pinMode(PIN_RELE_BOMBA,  OUTPUT);
    pinMode(PIN_LED_ALERTA,  OUTPUT);
    digitalWrite(PIN_RELE_BOMBA,  LOW);
    digitalWrite(PIN_LED_ALERTA,  LOW);

    // Pines de entrada
    pinMode(PIN_NIVEL_AGUA,   INPUT_PULLUP);
    pinMode(PIN_BOTON_MANUAL, INPUT_PULLUP);

    // ADC 12 bits
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);

    // LCD
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("Iniciando Riego");

    // Wi-Fi
    Serial.print("Conectando a WiFi");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(400);
        Serial.print(".");
    }
    Serial.println();
    Serial.println("[WiFi] Conectado exitosamente!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());

    lcd.clear();
}

// ══════════════════════════════════════════════════════════════════════════
unsigned long ultimoEnvio    = 0;
bool          activarBomba   = false;
bool          alertaNivel    = false;

void loop() {
    // Lectura analogica con sobremuestreo (10 lecturas)
    long sumaAdc = 0;
    for (int i = 0; i < 10; i++) {
        sumaAdc += analogRead(PIN_SENSOR_HUMEDAD);
        delay(5);
    }
    int   rawAdc            = (int)(sumaAdc / 10);
    float porcentajeHumedad = (rawAdc / 4095.0f) * 100.0f;

    // Entradas digitales
    bool nivelAguaOk = (digitalRead(PIN_NIVEL_AGUA)   == HIGH);
    bool botonManual = (digitalRead(PIN_BOTON_MANUAL)  == LOW);

    activarBomba = false;
    alertaNivel  = false;

    // ── Ciclo periódico de comunicación con la API ─────────────────────────
    unsigned long ahora = millis();
    if (ahora - ultimoEnvio >= INTERVALO_ENVIO_MS) {
        ultimoEnvio = ahora;

        bool forzar          = false;
        int  duracionForzado = 30;

        if (WiFi.status() == WL_CONNECTED) {
            consultarConfigYComandos(forzar, duracionForzado);
        }

        // Logica de control
        if (!nivelAguaOk) {
            alertaNivel  = true;
            activarBomba = false;
        } else {
            if (porcentajeHumedad < HUM_MIN_ON || botonManual || forzar) {
                activarBomba = true;
            }
        }

        // Ejecutar riego forzado con ACK
        if (forzar && nivelAguaOk) {
            Serial.printf("[Forzar] Regando %ds por comando de la app\n", duracionForzado);
            lcd.setCursor(0, 1);
            lcd.print("Forzado: REGANDO");
            digitalWrite(PIN_RELE_BOMBA, HIGH);
            delay((unsigned long)duracionForzado * 1000UL);
            digitalWrite(PIN_RELE_BOMBA, LOW);
            confirmarRiegoForzado();
            activarBomba = false;
        }

        // Enviar telemetria
        enviarDatosApi(porcentajeHumedad, rawAdc, nivelAguaOk);
    }

    // ── Lógica continua entre envíos ──────────────────────────────────────
    if (!nivelAguaOk) {
        alertaNivel  = true;
        activarBomba = false;
    } else if (porcentajeHumedad < HUM_MIN_ON || botonManual) {
        activarBomba = true;
    } else if (porcentajeHumedad >= HUM_MAX_OFF) {
        activarBomba = false;
    }

    // Actuadores
    digitalWrite(PIN_RELE_BOMBA, activarBomba ? HIGH : LOW);
    digitalWrite(PIN_LED_ALERTA, alertaNivel  ? HIGH : LOW);

    // Interfaz LCD
    char fila0[17];
    snprintf(fila0, sizeof(fila0), "S%d Hum:%5.1f%%  ", ID_SECTOR, porcentajeHumedad);
    lcd.setCursor(0, 0);
    lcd.print(fila0);

    lcd.setCursor(0, 1);
    if (alertaNivel) {
        lcd.print("ALERTA: Sin Agua");
    } else if (activarBomba) {
        lcd.print("Bomba: REGANDO  ");
    } else {
        lcd.print("Bomba: APAGADA  ");
    }

    delay(200);
}

// ══════════════════════════════════════════════════════════════════════════
// FUNCIONES
// ══════════════════════════════════════════════════════════════════════════

bool conectarWifi() {
    if (WiFi.status() == WL_CONNECTED) return true;
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 20) {
        delay(500);
        intentos++;
    }
    return (WiFi.status() == WL_CONNECTED);
}

void consultarConfigYComandos(bool &forzar, int &duracionForzado) {
    HTTPClient http;

    // GET /api/v1/comandos/{ID_SECTOR}
    String urlCmd = String(API_BASE) + "/comandos/" + String(ID_SECTOR);
    http.begin(urlCmd);
    http.addHeader("X-API-Key", API_KEY);
    int code = http.GET();

    if (code == 200) {
        String body = http.getString();
        JsonDocument doc;
        if (deserializeJson(doc, body) == DeserializationError::Ok) {
            HUM_MIN_ON           = doc["humedad_min_on"]       | HUM_MIN_ON;
            HUM_MAX_OFF          = doc["humedad_max_off"]      | HUM_MAX_OFF;
            TIEMPO_MAX_RIEGO_SEG = doc["tiempo_max_riego_seg"] | TIEMPO_MAX_RIEGO_SEG;
            forzar               = doc["forzar_riego"]         | false;
            duracionForzado      = doc["duracion_forzado_seg"] | 30;

            Serial.printf("[Sector %d] Min=%.1f%% Max=%.1f%% Forzar=%s\n",
                ID_SECTOR, HUM_MIN_ON, HUM_MAX_OFF, forzar ? "SI" : "NO");
        }
    } else {
        Serial.printf("[API] Error consultando comandos: HTTP %d\n", code);
    }
    http.end();
}

void confirmarRiegoForzado() {
    HTTPClient http;
    String urlAck = String(API_BASE) + "/comandos/forzar-riego/" + String(ID_SECTOR);
    http.begin(urlAck);
    http.addHeader("X-API-Key", API_KEY);
    int code = http.sendRequest("DELETE");
    Serial.printf("[ACK] Riego forzado sector %d confirmado: HTTP %d\n", ID_SECTOR, code);
    http.end();
}

void enviarDatosApi(float humedad, int rawAdc, bool nivelAguaOk) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi desconectado");
        return;
    }

    HTTPClient http;

    // 1. Telemetría de humedad
    JsonDocument payload;
    char idSensor[16];
    snprintf(idSensor, sizeof(idSensor), "SEN-CAP-S%02d", ID_SECTOR);
    payload["id_sensor"]          = idSensor;
    payload["id_sector"]          = ID_SECTOR;
    payload["humedad_porcentaje"] = round(humedad * 100.0f) / 100.0f;
    payload["valor_adc_crudo"]    = rawAdc;

    String jsonStr;
    serializeJson(payload, jsonStr);

    http.begin(String(API_BASE) + "/mediciones");
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", API_KEY);
    int httpCode = http.POST(jsonStr);
    Serial.printf("HTTP Mediciones S%d: %d\n", ID_SECTOR, httpCode);
    http.end();

    // 2. Alerta crítica de falta de agua (solo si cambia estado)
    if (!nivelAguaOk && !alertaEnviadaPrevia) {
        JsonDocument alerta;
        char obs[80];
        snprintf(obs, sizeof(obs), "Alerta nivel agua detectada por ESP32 en Sector %d", ID_SECTOR);
        alerta["id_sector"]       = ID_SECTOR;
        alerta["nivel_detectado"] = "CRITICO_VACIO";
        alerta["bomba_bloqueada"] = true;
        alerta["observacion"]     = obs;

        String alertaStr;
        serializeJson(alerta, alertaStr);

        http.begin(String(API_BASE) + "/alertas");
        http.addHeader("Content-Type", "application/json");
        http.addHeader("X-API-Key", API_KEY);
        int codeAlerta = http.POST(alertaStr);
        Serial.printf("HTTP Alerta Nivel: %d\n", codeAlerta);
        http.end();
        alertaEnviadaPrevia = true;
    } else if (nivelAguaOk) {
        alertaEnviadaPrevia = false;
    }
}
