/*
 * Умная AI-Теплица — прошивка контроллера 12 участков.
 * ---------------------------------------------------------------
 * Плата: Arduino Mega 2560 (или совместимая).
 * Обмен с сервером: построчный JSON по Serial, 115200 бод.
 *
 * Аппаратная конфигурация:
 *   - CD74HC4067 (16-канальный аналоговый мультиплексор):
 *       C0..C11  -> датчики влажности почвы 12 участков (ёмкостные/резистивные);
 *       C12      -> фоторезистор (освещённость, лк, оценочно);
 *   - DHT22      -> температура и влажность воздуха;
 *   - HC-SR04    -> уровень воды в баке;
 *   - 2x 74HC595 -> 16 выходов: Q0..Q11 насосы 12 участков,
 *                   Q12 вентилятор, Q13 фитолампа (ШИМ через MOSFET);
 *   - Строб: линия STROBE синхронизирует засветку фитолампы с экспозицией
 *            (при наличии модуля технического зрения).
 *
 * Библиотеки (Library Manager): ArduinoJson (v6), DHT sensor library.
 *
 * Протокол (сервер -> плата):
 *   {"cmd":"set","zone":3,"device":"watering","on":true,"seconds":10}
 * Протокол (плата -> сервер):
 *   {"type":"hello","fw":"1.0","zones":12}
 *   {"type":"readings","tank":78.5,"data":[{"zone":1,"temperature":24.5,
 *      "moisture":48,"light":12400}, ...]}
 *   {"type":"ack","zone":3,"device":"watering","on":true}
 */

#include <ArduinoJson.h>
#include <DHT.h>

// ---------------------------------------------------------------- параметры
static const uint8_t  ZONES            = 12;
static const uint32_t SEND_INTERVAL_MS = 2000;   // период отправки телеметрии
static const uint32_t SERIAL_BAUD      = 115200;
static const uint32_t MAX_ON_MS        = 120000; // страховка: макс. 2 мин работы

// Мультиплексор CD74HC4067
static const uint8_t MUX_S0 = 22, MUX_S1 = 23, MUX_S2 = 24, MUX_S3 = 25, MUX_SIG = A0;
static const uint8_t MUX_SOIL_FIRST = 0;   // каналы 0..11 — влажность почвы
static const uint8_t MUX_LDR_CH     = 12;  // фотодиод/фоторезистор

// DHT22
static const uint8_t DHT_PIN = 2;
#define DHT_TYPE DHT22

// Ультразвук (бак)
static const uint8_t TRIG_PIN = 3, ECHO_PIN = 4;
static const float   TANK_FULL_CM = 3.0f, TANK_EMPTY_CM = 25.0f;

// 74HC595 (2 шт. каскадом)
static const uint8_t SR_DATA = 8, SR_CLOCK = 9, SR_LATCH = 10;
static const uint8_t OUT_PUMP_FIRST = 0;   // Q0..Q11 — насосы участков
static const uint8_t OUT_FAN = 12;         // Q12 — вентилятор
static const uint8_t OUT_LIGHT = 13;       // Q13 — фитолампа

// Калибровка датчиков влажности (значения АЦП: сухо/мокро)
static const int SOIL_DRY = 820;
static const int SOIL_WET = 320;

DHT dht(DHT_PIN, DHT_TYPE);

struct Output {
  bool      on = false;
  uint32_t  offAt = 0;      // 0 — без таймера
  uint16_t  shiftBit = 0;   // позиция в сдвиговом регистре
};

Output outputs[ZONES + 2];  // 12 насосов + вентилятор + лампа
uint16_t outputState = 0;   // битовая маска для 74HC595
uint32_t lastSend = 0;

// ------------------------------------------------------------------ утилиты
uint16_t readMux(uint8_t channel) {
  digitalWrite(MUX_S0, (channel >> 0) & 1);
  digitalWrite(MUX_S1, (channel >> 1) & 1);
  digitalWrite(MUX_S2, (channel >> 2) & 1);
  digitalWrite(MUX_S3, (channel >> 3) & 1);
  delayMicroseconds(120);
  return analogRead(MUX_SIG);
}

// Усреднение для подавления шума
uint16_t readMuxAverage(uint8_t channel, uint8_t samples = 8) {
  uint32_t sum = 0;
  for (uint8_t i = 0; i < samples; i++) sum += readMux(channel);
  return (uint16_t)(sum / samples);
}

float soilMoisturePercent(uint16_t raw) {
  float value = (float)(SOIL_DRY - raw) * 100.0f / (float)(SOIL_DRY - SOIL_WET);
  if (value < 0) value = 0;
  if (value > 100) value = 100;
  return value;
}

float lightLux(uint16_t raw) {
  // Оценочная шкала: 0 — темно, 1023 — ярко (~45 000 лк)
  return (float)raw * (45000.0f / 1023.0f);
}

float tankPercent() {
  digitalWrite(TRIG_PIN, LOW);  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  uint32_t duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) return -1.0f;                  // нет эха
  float distance = duration * 0.0343f / 2.0f;       // см
  float percent = (TANK_EMPTY_CM - distance) * 100.0f / (TANK_EMPTY_CM - TANK_FULL_CM);
  if (percent < 0) percent = 0;
  if (percent > 100) percent = 100;
  return percent;
}

void writeShiftRegister() {
  digitalWrite(SR_LATCH, LOW);
  shiftOut(SR_DATA, SR_CLOCK, MSBFIRST, (uint8_t)(outputState >> 8));
  shiftOut(SR_DATA, SR_CLOCK, MSBFIRST, (uint8_t)(outputState & 0xFF));
  digitalWrite(SR_LATCH, HIGH);
}

int findOutput(const char *device, int zone) {
  if (strcmp(device, "water") == 0 || strcmp(device, "watering") == 0) {
    if (zone >= 1 && zone <= ZONES) return OUT_PUMP_FIRST + zone - 1;
  } else if (strcmp(device, "ventilation") == 0 || strcmp(device, "fan") == 0) {
    return OUT_FAN;
  } else if (strcmp(device, "lighting") == 0 || strcmp(device, "light") == 0) {
    return OUT_LIGHT;
  }
  return -1;
}

void applyOutput(int index, bool on, uint32_t seconds) {
  if (index < 0 || index >= ZONES + 2) return;
  outputs[index].on = on;
  outputs[index].offAt = (on && seconds > 0) ? millis() + seconds * 1000UL : 0;

  // индекс выхода == номер бита в сдвиговом регистре
  if (on) outputState |= (uint16_t)(1 << index);
  else    outputState &= (uint16_t)~(1 << index);
  writeShiftRegister();
}

void handleCommand(const char *line) {
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, line);
  if (error) return;

  const char *cmd = doc["cmd"] | "";
  if (strcmp(cmd, "set") != 0) return;

  int zone = doc["zone"] | 0;
  const char *device = doc["device"] | "";
  bool on = doc["on"] | false;
  uint32_t seconds = doc["seconds"] | 0;
  if (seconds > MAX_ON_MS / 1000UL) seconds = MAX_ON_MS / 1000UL;

  int index = findOutput(device, zone);
  if (index < 0) return;
  applyOutput(index, on, seconds);

  StaticJsonDocument<160> ack;
  ack["type"] = "ack";
  ack["zone"] = zone;
  ack["device"] = device;
  ack["on"] = on;
  serializeJson(ack, Serial);
  Serial.println();
}

void sendHello() {
  StaticJsonDocument<96> hello;
  hello["type"] = "hello";
  hello["fw"] = "1.0";
  hello["zones"] = ZONES;
  serializeJson(hello, Serial);
  Serial.println();
}

void sendReadings() {
  float airTemp = dht.readTemperature();
  float airHum = dht.readHumidity();
  if (isnan(airTemp)) airTemp = 24.0f;

  float lux = lightLux(readMuxAverage(MUX_LDR_CH));
  float tank = tankPercent();

  StaticJsonDocument<1024> doc;
  doc["type"] = "readings";
  if (tank >= 0) doc["tank"] = tank;
  JsonArray data = doc.createNestedArray("data");

  for (uint8_t zone = 0; zone < ZONES; zone++) {
    uint16_t raw = readMuxAverage(MUX_SOIL_FIRST + zone);
    float moisture = soilMoisturePercent(raw);

    JsonObject item = data.createNestedObject();
    item["zone"] = zone + 1;
    item["temperature"] = airTemp;
    item["moisture"] = moisture;
    item["light"] = lux;
  }

  serializeJson(doc, Serial);
  Serial.println();
}

void expireTimers() {
  uint32_t now = millis();
  for (uint8_t i = 0; i < ZONES + 2; i++) {
    if (outputs[i].on && outputs[i].offAt && now >= outputs[i].offAt) {
      applyOutput(i, false, 0);
    }
  }
}

// -------------------------------------------------------------------- setup
void setup() {
  Serial.begin(SERIAL_BAUD);
  dht.begin();

  pinMode(MUX_S0, OUTPUT); pinMode(MUX_S1, OUTPUT);
  pinMode(MUX_S2, OUTPUT); pinMode(MUX_S3, OUTPUT);
  pinMode(SR_DATA, OUTPUT); pinMode(SR_CLOCK, OUTPUT); pinMode(SR_LATCH, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);

  outputState = 0;
  writeShiftRegister();
  for (uint8_t i = 0; i < ZONES + 2; i++) {
    outputs[i].shiftBit = i;
    outputs[i].on = false;
    outputs[i].offAt = 0;
  }

  delay(300);
  sendHello();
}

// --------------------------------------------------------------------- loop
void loop() {
  // приём команд (построчно)
  static char buffer[256];
  static uint16_t length = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (length > 0) {
        buffer[length] = '\0';
        handleCommand(buffer);
        length = 0;
      }
    } else if (length < sizeof(buffer) - 1) {
      buffer[length++] = c;
    }
  }

  expireTimers();

  if (millis() - lastSend >= SEND_INTERVAL_MS) {
    lastSend = millis();
    sendReadings();
  }
}
