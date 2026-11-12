#include <Wire.h>
#include <WiFiS3.h>
#include "SparkFun_SHTC3.h"
#include "secrets.h"

const char WIFI_SSID[] = SECURE_SSID;
const char WIFI_PASSWORD[] = SECURE_PASSWD;
const char DEVICE_ID[] = SECURE_DEVICE_NAME;

IPAddress SERVER_IP(10, 42, 0, 1);
const uint16_t SERVER_PORT = 5000;

WiFiClient tcpClient;
SHTC3 mySHTC3;

WiFiClient tcp;
unsigned long lastWiFiAttempt = 0;
unsigned long lastServerAttempt = 0;

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

  Wire1.begin();

  if (mySHTC3.begin(Wire1) != SHTC3_Status_Nominal) {
    Serial.println("SHTC3 initialization failed.");
  } else {
    Serial.println("SHTC3 initialized.");
  }

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Wi-Fi module not detected.");
    while (true) {
      delay(1000);
    }
  }

  startWiFiConnection();
}

void loop() {
  if (mySHTC3.update() != SHTC3_Status_Nominal) {
    Serial.println("SHTC3 read failed.");
    delay(1000);
    return;
  }

  float temperature = mySHTC3.toDegC();
  float humidity = mySHTC3.toPercent();

  String json = "{\"Device\":\"";
  json += DEVICE_ID;
  json += "\",\"Outlet temp 2\":";
  json += String(temperature, 1);
  json += ",\"Humidity 2\":";
  json += String(humidity, 1);
  json += "}\n";

  if (keepNetworkConnections()) {
    tcpClient.print(json);
  }

  delay(1000);
}
