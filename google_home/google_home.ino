/*
 * SmartVivero - Control de Bomba con Google Home / SinricPro
 * 
 * Hardware:
 * - ESP32 DevKit V1
 * - Módulo Relé en GPIO 18 (Bomba de agua)
 * 
 * Librerías necesarias (instaladas en Arduino IDE):
 * - SinricPro
 * - WebSockets
 * - ArduinoJson
 */

#ifdef ENABLE_DEBUG
   #define DEBUG_ESP_PORT Serial
   #define NODEBUG_WEBSOCKETS
   #define NDEBUG
#endif 

#include <Arduino.h>
#if defined(ESP8266)
  #include <ESP8266WiFi.h>
#elif defined(ESP32) || defined(ARDUINO_ARCH_RP2040)
  #include <WiFi.h>
#endif

#include "SinricPro.h"
#include "SinricProSwitch.h"

// ─── CREDENCIALES WI-FI ───────────────────────────────────────────────────
#define WIFI_SSID         "iPhone"
#define WIFI_PASS         "Diego123"

// ─── CREDENCIALES SINRICPRO (GOOGLE HOME) ─────────────────────────────────
#define APP_KEY           "087703d1-88c1-4f45-a7c9-8d3624596c24"
#define APP_SECRET        "39d2a459-a77e-4c42-bee8-df86ea20f0fa-c43024d7-0fe9-4637-8684-ae3d9e6992bc"
#define SWITCH_ID_1       "6aa2184ab3889c3a11adc017"

// ─── CONFIGURACIÓN DE PINES ───────────────────────────────────────────────
#define RELAYPIN_1        18
#define BAUD_RATE         115200

// Control seguro del relé de 5V desde ESP32 (3.3V) usando Alta Impedancia (Hi-Z):
// - ENCENDER: Pin en OUTPUT y nivel LOW (conecta a GND, activa el optoacoplador).
// - APAGAR:   Pin en INPUT (flotante / circuito abierto, equivale exactamente a desconectar el cable IN).
void fijarRele(bool encender) {
  if (encender) {
    pinMode(RELAYPIN_1, OUTPUT);
    digitalWrite(RELAYPIN_1, LOW);
  } else {
    pinMode(RELAYPIN_1, INPUT);
  }
}

// Callback cuando Google Home o la app enciende/apaga el dispositivo
bool onPowerState1(const String &deviceId, bool &state) {
  Serial.printf("[Google Home]: Dispositivo (Bomba) cambio a: %s\r\n", state ? "ENCENDIDO" : "APAGADO");
  fijarRele(state);
  return true; // Solicitud procesada correctamente
}

// Conexión Wi-Fi
void setupWiFi() {
  Serial.printf("\r\n[WiFi]: Conectando a %s", WIFI_SSID);

  #if defined(ESP8266)
    WiFi.setSleepMode(WIFI_NONE_SLEEP); 
    WiFi.setAutoReconnect(true);
  #elif defined(ESP32)
    WiFi.setSleep(false); 
    WiFi.setAutoReconnect(true);
  #endif

  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    Serial.printf(".");
    delay(250);
  }

  Serial.printf("\r\n[WiFi]: Conectado con exito! IP asignada: %s\r\n", WiFi.localIP().toString().c_str());
}

// Configuración SinricPro
void setupSinricPro() {
  // Iniciar con la bomba apagada por seguridad (modo flotante = cable desconectado)
  fijarRele(false);

  // Vincular Switch y callback
  SinricProSwitch& mySwitch1 = SinricPro[SWITCH_ID_1];
  mySwitch1.onPowerState(onPowerState1);

  // Callbacks de conexión
  SinricPro.onConnected([](){ 
    Serial.printf("[SinricPro]: Conectado al servidor SinricPro! (Listo para recibir comandos de Google Home)\r\n"); 
  }); 
  SinricPro.onDisconnected([](){ 
    Serial.printf("[SinricPro]: Desconectado de SinricPro\r\n"); 
  });

  SinricPro.begin(APP_KEY, APP_SECRET);
}

void setup() {
  Serial.begin(BAUD_RATE);
  Serial.printf("\r\n\r\n=========================================\r\n");
  Serial.printf("  SmartVivero - Google Home / SinricPro  \r\n");
  Serial.printf("=========================================\r\n");
  setupWiFi();
  setupSinricPro();
}

void loop() {
  SinricPro.handle();
}
