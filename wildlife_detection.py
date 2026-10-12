import cv2
import time

from ultralytics import YOLO
from database import save_event

model = YOLO("best.pt")
cap = cv2.VideoCapture(0)

high_risk = [
    "WildBoar", "AmurTiger", "AmurLeopard", "BlackBear"
]

medium_risk = [
    "RoeDeer", "SikaDeer", "MuskDeer", "Sable",
    "Badger", "YellowThroatedMarten", "RaccoonDog",
    "RedFox", "Weasel", "LeopardCat"
]

low_risk = ["Cow", "Dog", "Hare"]

# Only accept classes in our trained wildlife dataset
valid_animals = set(high_risk + medium_risk + low_risk)

last_saved = {}
cooldown = 10
confidence_threshold = 0.60

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to capture frame")
        break

    results = model.predict(
        source=frame,
        conf=confidence_threshold,
        verbose=False
    )

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            animal = model.names[class_id]

            # Ignore classes outside our expected wildlife labels
            if animal not in valid_animals:
                continue

            if animal in high_risk:
                risk = "HIGH"
                action = "Activate Alarm + Notify Farmer"

            elif animal in medium_risk:
                risk = "MEDIUM"
                action = "Notify Farmer"

            else:
                risk = "LOW"
                action = "No Action"

            print("Animal:", animal)
            print("Confidence:", f"{confidence * 100:.0f}%")
            print("Risk:", risk)
            print("Action:", action)
            print()

            current_time = time.time()

            if (
                animal not in last_saved
                or current_time - last_saved[animal] >= cooldown
            ):
                save_event(animal, risk, confidence)
                last_saved[animal] = current_time

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            label = f"{animal} {confidence * 100:.0f}%"

            cv2.rectangle(
                frame, (x1, y1), (x2, y2), (0, 255, 0), 2
            )

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    cv2.imshow("Wildlife Intrusion Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
