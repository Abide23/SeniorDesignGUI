#include <SensirionCore.h>
#include <SensirionI2CSen5x.h>

SensirionI2CSen5x sen5x;

// --- ANALOG VELOCITY CONFIGURATION ---
const int VELOCITY_PIN = A0;
const float VELOCITY_SLOPE = 2.8;     // Change this: (Change in Velocity / Change in Voltage)
const float VELOCITY_INTERCEPT = -0.4; // Change this: Velocity when voltage is 0V
// -------------------------------------

// Measurement Variables
float pm1p0;
float pm2p5;
float pm4p0;
float pm10p0;
float sen5xHumidity;
float ambientTemperature;
float vocIndex;
float noxIndex;

void setup() {
  Serial.begin(115200);
  delay(250);

  Wire1.begin();
  sen5x.begin(Wire1);

  sen5x.deviceReset();
  sen5x.startMeasurement();
}

void loop() {
  // 1. Read SEN5x Sensor
  sen5x.readMeasuredValues(pm1p0, pm2p5, pm4p0, pm10p0, sen5xHumidity, 
                           ambientTemperature, vocIndex, noxIndex);

  // 2. Read and Map Analog Velocity
  int rawAnalog = analogRead(VELOCITY_PIN);
  float voltage = rawAnalog * (5.0 / 1023.0); // Convert 0-1023 to 0-5V
  float velocity = (VELOCITY_SLOPE * voltage) + VELOCITY_INTERCEPT; // Linear Mapping

  // 3. Send JSON Data
  Serial.print("{");
  
  // Inlet Temp
  Serial.print("\"Inlet temp\":");
  if (isnan(ambientTemperature)) Serial.print("0.0"); else Serial.print(ambientTemperature);
  Serial.print(",");

  // Humidity
  Serial.print("\"Humidity\":");
  if (isnan(sen5xHumidity)) Serial.print("0.0"); else Serial.print(sen5xHumidity);
  Serial.print(",");

  // NEW: Measured Velocity
  Serial.print("\"Measured Velocity\":");
  Serial.print(velocity);
  Serial.print(",");

  // PM 1.0 (Last item - no trailing comma)
  Serial.print("\"PM 1.0\":");
  if (isnan(pm1p0)) Serial.print("0.0"); else Serial.print(pm1p0);
  
  Serial.println("}");

  delay(1000);
}
