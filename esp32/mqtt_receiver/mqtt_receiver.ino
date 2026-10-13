
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

const char* ssid = "Galaxy A15 5G";
const char* password = "prarthana";

const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic = "wildshield/alert";

#define RED_LED 15
#define YELLOW_LED 4
#define GREEN_LED 5
#define BUZZER 27

WiFiClient espClient;
PubSubClient client(espClient);

LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup_wifi() {
  Serial.println("Connecting to WiFi...");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";

  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("MQTT message received: ");
  Serial.println(message);

  int first = message.indexOf('|');
  int second = message.indexOf('|', first + 1);

  if (first == -1 || second == -1) {
    Serial.println("Invalid message format");
    return;
  }

  String animal = message.substring(0, first);
  String confidence = message.substring(first + 1, second);
  String risk = message.substring(second + 1);

  animal.trim();
  confidence.trim();
  risk.trim();

  digitalWrite(RED_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER, LOW);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(animal.substring(0, 16));

  lcd.setCursor(0, 1);
  lcd.print(risk);
  lcd.print(" RISK");

  Serial.print("Animal: ");
  Serial.println(animal);
  Serial.print("Confidence: ");
  Serial.println(confidence);
  Serial.print("Risk: ");
  Serial.println(risk);

  if (risk == "HIGH") {
    digitalWrite(RED_LED, HIGH);
    digitalWrite(BUZZER, HIGH);
    Serial.println("HIGH RISK: Alarm activated");
    delay(5000);
    digitalWrite(RED_LED, LOW);
    digitalWrite(BUZZER, LOW);

  } else if (risk == "MEDIUM") {
    digitalWrite(YELLOW_LED, HIGH);
    Serial.println("MEDIUM RISK");
    delay(5000);
    digitalWrite(YELLOW_LED, LOW);

  } else if (risk == "LOW") {
    digitalWrite(GREEN_LED, HIGH);
    Serial.println("LOW RISK");
    delay(5000);
    digitalWrite(GREEN_LED, LOW);

  } else {
    Serial.println("Unknown risk level");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to HiveMQ Public Broker...");

    String clientId = "WildShieldESP32-";
    clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");

      if (client.subscribe(mqtt_topic)) {
        Serial.print("Subscribed to: ");
        Serial.println(mqtt_topic);
      } else {
        Serial.println("Subscription failed");
      }

    } else {
      Serial.print("Connection failed, state = ");
      Serial.println(client.state());
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(RED_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  digitalWrite(RED_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER, LOW);

  Wire.begin(21, 22);

  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SYSTEM READY");

  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setKeepAlive(60);
  client.setBufferSize(256);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setup_wifi();
  }

  if (!client.connected()) {
    reconnect();
  }

  client.loop();
}
