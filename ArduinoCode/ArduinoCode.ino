#include <Wire.h>
#include <WiFiS3.h>
#include <SensirionCore.h>
#include <SensirionI2CSen5x.h>
#include <math.h>
#include "secrets.h" // Secret file that contains wifi information

SensirionI2CSen5x sen5x;

const char WIFI_SSID[] = SECURE_SSID; // Place Wi-Fi SSID here (placeholder)
const char WIFI_PASSWORD[] = SECURE_PASSWD; // Password here (placeholder) 
const char DEVICE_ID[] = SECURE_DEVICE_NAME;

//10.42.0.1
IPAddress SERVER_IP(10, 42, 0, 1);
const uint16_t SERVER_PORT = 5000;

WiFiClient tcpClient;

// Analog velocity sensor
const int VELOCITY_PIN = A0;
const float VELOCITY_SLOPE = 2.8;
const float VELOCITY_INTERCEPT = -0.4;

unsigned long lastWiFiAttempt = 0;
unsigned long lastServerAttempt = 0;

String numberOrZero(float value, int decimals) {
  if (isnan(value)) {
    return "0.0";
  }
  return String(value, decimals);
}

void startWiFiConnection() {
  Serial.print("Connecting to hotspot: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWiFiAttempt = millis();
}

bool keepNetworkConnections() {
  if (WiFi.status() != WL_CONNECTED) {
    tcpClient.stop();

    // Retry Wi-Fi every 10 seconds.
    if (millis() - lastWiFiAttempt >= 10000) {
      startWiFiConnection();
    }
    return false;
  }

  if (!tcpClient.connected()) {
    tcpClient.stop();

    // Retry the computer's TCP server every 3 seconds.
    if (millis() - lastServerAttempt >= 3000) {
      lastServerAttempt = millis();

      Serial.print("Connecting to computer at ");
      Serial.print(SERVER_IP);
      Serial.print(":");
      Serial.println(SERVER_PORT);

      if (tcpClient.connect(SERVER_IP, SERVER_PORT)) {
        Serial.println("Connected to computer.");
      } else {
        Serial.println("TCP connection failed; will retry.");
      }
    }
  }

  return tcpClient.connected();
}

void setup() {
  Serial.begin(115200);

  // Use Wire1 when the SEN5x is connected through the UNO R4 WiFi Qwiic port.
  Wire1.begin();
  sen5x.begin(Wire1);

  uint16_t error = sen5x.deviceReset();
  if (error) {
    Serial.println("SEN5x reset failed.");
  }
  delay(100);

  error = sen5x.startMeasurement();
  if (error) {
    Serial.println("SEN5x measurement start failed.");
  }

  // Read A0 at 14-bit resolution: 0–16383.
  analogReadResolution(14);

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Wi-Fi module not detected.");
    while (true) {
      delay(1000);
    }
  }

  startWiFiConnection();
}

void loop() {
  BLE_UNUSED: // No BLE is used in this Wi-Fi version.

  float pm1p0 = NAN;
  float pm2p5 = NAN;
  float pm4p0 = NAN;
  float pm10p0 = NAN;
  float sen5xHumidity = NAN;
  float ambientTemperature = NAN;
  float vocIndex = NAN;
  float noxIndex = NAN;

  uint16_t error = sen5x.readMeasuredValues(
    pm1p0,
    pm2p5,
    pm4p0,
    pm10p0,
    sen5xHumidity,
    ambientTemperature,
    vocIndex,
    noxIndex
  );

  if (error) {
    Serial.println("SEN5x read failed.");
  }

  int rawAnalog = analogRead(VELOCITY_PIN);
  float voltage = rawAnalog * (5.0f / 16383.0f);
  float velocity =
    (VELOCITY_SLOPE * voltage) + VELOCITY_INTERCEPT;

  String json = "{\"Device\":\"";
  json += DEVICE_ID;
  json += "\",\"Inlet temp\":";
  json += numberOrZero(ambientTemperature, 1);
  json += ",\"Humidity\":";
  json += numberOrZero(sen5xHumidity, 1);
  json += ",\"Measured Velocity\":";
  json += String(velocity, 2);
  json += ",\"PM 1.0\":";
  json += numberOrZero(pm1p0, 1);
  json += "}\n";

  if (keepNetworkConnections()) {
    tcpClient.print(json);
  }

  delay(1000);
}
