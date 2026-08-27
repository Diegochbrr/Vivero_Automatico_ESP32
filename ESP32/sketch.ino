#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <WiFi.h>
#include <HTTPClient.h>

#define PIN_SENSOR_HUMEDAD 34
#define PIN_NIVEL_AGUA     18
#define PIN_BOTON_MANUAL   19
#define PIN_RELE_BOMBA      2
#define PIN_LED_ALERTA      4

const char* ssid = "Wokwi-GUEST";
const char* password = "";

// URLs en la nube (Render)
const char* api_mediciones_url = "https://vivero-automatico-esp32.onrender.com/api/v1/mediciones"; 
const char* api_alertas_url = "https://vivero-automatico-esp32.onrender.com/api/v1/alertas"; 
const char* api_key = "sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d";

LiquidCrystal_I2C lcd(0x27, 16, 2);

unsigned long ultimoEnvio = 0;
const long intervaloEnvio = 5000;

void setup() {
  Serial.begin(115200);

  pinMode(PIN_NIVEL_AGUA, INPUT_PULLUP);
  pinMode(PIN_BOTON_MANUAL, INPUT_PULLUP);
  pinMode(PIN_RELE_BOMBA, OUTPUT);
  pinMode(PIN_LED_ALERTA, OUTPUT);

  digitalWrite(PIN_RELE_BOMBA, LOW);
  digitalWrite(PIN_LED_ALERTA, LOW);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Iniciando Riego");

  Serial.print("Conectando a WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Conectado exitosamente!");
  
  lcd.clear();
}

void loop() {
  // Lectura analógica escalada (0 - 4095 -> 0.0% - 100.0%)
  int rawADC = analogRead(PIN_SENSOR_HUMEDAD);
  float porcentajeHumedad = (rawADC / 4095.0) * 100.0;

  // Estados de entrada
  bool nivelAguaOk = (digitalRead(PIN_NIVEL_AGUA) == HIGH);
  bool botonManual = (digitalRead(PIN_BOTON_MANUAL) == LOW);

  bool activarBomba = false;
  bool alertaNivel = false;

  // Lógica de control
  if (!nivelAguaOk) {
    alertaNivel = true;
    activarBomba = false;
  } else {
    if (porcentajeHumedad < 35.0 || botonManual) {
      activarBomba = true;
    }
  }

  // Actualización de actuadores
  digitalWrite(PIN_RELE_BOMBA, activarBomba ? HIGH : LOW);
  digitalWrite(PIN_LED_ALERTA, alertaNivel ? HIGH : LOW);

  // Interfaz LCD
  lcd.setCursor(0, 0);
  lcd.print("Hum: ");
  lcd.print(porcentajeHumedad, 1);
  lcd.print("%   ");

  lcd.setCursor(0, 1);
  if (alertaNivel) {
    lcd.print("ALERTA: Sin Agua");
  } else if (activarBomba) {
    lcd.print("Bomba: REGANDO  ");
  } else {
    lcd.print("Bomba: APAGADA  ");
  }

  // Envío a la API cada 5 segundos
  if (millis() - ultimoEnvio >= intervaloEnvio) {
    ultimoEnvio = millis();
    enviarDatosAPI(porcentajeHumedad, rawADC, nivelAguaOk);
  }

  delay(200);
}

void enviarDatosAPI(float humedad, int adcCrudo, bool nivelAguaOk) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    // 1. Enviar telemetría de humedad a la nube (Render)
    if (http.begin(api_mediciones_url)) {
      http.addHeader("Content-Type", "application/json");
      http.addHeader("X-API-Key", api_key);
      
      String payload = "{";
      payload += "\"id_sensor\": \"SEN-CAP-S01\",";
      payload += "\"id_sector\": 1,";
      payload += "\"humedad_porcentaje\": " + String(humedad, 2) + ",";
      payload += "\"valor_adc_crudo\": " + String(adcCrudo);
      payload += "}";

      int httpResponseCode = http.POST(payload);
      Serial.print("📡 HTTP Mediciones: ");
      Serial.println(httpResponseCode);
      http.end();
    } else {
      Serial.println("❌ Error al inicializar conexión HTTP");
    }

    // 2. Enviar alerta crítica de falta de agua
    if (!nivelAguaOk) {
      HTTPClient httpAlerta;
      if (httpAlerta.begin(api_alertas_url)) {
        httpAlerta.addHeader("Content-Type", "application/json");
        httpAlerta.addHeader("X-API-Key", api_key);
        
        String alertaPayload = "{";
        alertaPayload += "\"id_sector\": 1,";
        alertaPayload += "\"nivel_detectado\": \"CRITICO_VACIO\",";
        alertaPayload += "\"bomba_bloqueada\": true,";
        alertaPayload += "\"observacion\": \"Alerta de nivel de agua detectada por ESP32\"";
        alertaPayload += "}";

        int alertaCode = httpAlerta.POST(alertaPayload);
        Serial.print("🚨 HTTP Alerta Nivel: ");
        Serial.println(alertaCode);
        httpAlerta.end();
      }
    }
  } else {
    Serial.println("⚠️ WiFi desconectado");
  }
}
