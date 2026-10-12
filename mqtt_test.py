import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "wildshield/alert"

client = mqtt.Client()

client.connect(BROKER, PORT, 60)

message = "ELEPHANT|96|HIGH"

result = client.publish(TOPIC, message)

result.wait_for_publish()

print("Message sent:")
print(message)

client.disconnect()
