import cv2
import time
import av
import pandas as pd
import streamlit as st
import paho.mqtt.client as mqtt

from ultralytics import YOLO
from streamlit_webrtc import (
    webrtc_streamer,
    VideoProcessorBase,
    WebRtcMode
)

from database import save_event, get_events


st.set_page_config(
    page_title="WildShield",
    page_icon="W",
    layout="wide"
)


st.title("WildShield")
st.write("AI-Based Wildlife Intrusion Detection System")


MQTT_BROKER = "172.20.10.8"
MQTT_PORT = 1883
MQTT_TOPIC = "wildshield/alert"


high_risk = [
    "AmurTiger",
    "AmurLeopard",
    "BlackBear",
    "WildBoar"
]

medium_risk = [
    "RoeDeer",
    "SikaDeer",
    "MuskDeer",
    "Sable",
    "Badger",
    "YellowThroatedMarten",
    "RaccoonDog",
    "RedFox",
    "Weasel",
    "LeopardCat"
]

low_risk = [
    "Cow",
    "Dog",
    "Hare"
]


mqtt_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)


try:

    mqtt_client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        60
    )

    mqtt_client.loop_start()

    mqtt_status = True

except Exception:

    mqtt_status = False


class WildlifeVideoProcessor(VideoProcessorBase):

    def __init__(self):

        self.model = YOLO("best.pt")

        self.last_saved = {}

        self.cooldown = 10

    def recv(self, frame):

        img = frame.to_ndarray(
            format="bgr24"
        )

        results = self.model(
            img,
            verbose=False
        )

        for result in results:

            for box in result.boxes:

                class_id = int(box.cls[0])

                confidence = float(
                    box.conf[0]
                )

                if confidence < 0.50:
                    continue

                animal = self.model.names[class_id]


                if animal in high_risk:

                    risk = "HIGH"

                    action = (
                        "Activate Alarm + "
                        "Notify Farmer"
                    )

                elif animal in medium_risk:

                    risk = "MEDIUM"

                    action = "Notify Farmer"

                elif animal in low_risk:

                    risk = "LOW"

                    action = "No Action"

                else:

                    risk = "LOW"

                    action = "No Action"


                print("Animal :", animal)

                print(
                    "Confidence :",
                    f"{confidence * 100:.0f}%"
                )

                print("Risk :", risk)

                print("Action :", action)

                print()


                current_time = time.time()


                if (
                    animal not in self.last_saved
                    or
                    current_time
                    - self.last_saved[animal]
                    >= self.cooldown
                ):

                    save_event(
                        animal,
                        risk,
                        confidence
                    )

                    self.last_saved[animal] = (
                        current_time
                    )


                    message = (
                        f"{animal.upper()}|"
                        f"{confidence * 100:.0f}|"
                        f"{risk}"
                    )


                    if mqtt_status:

                        result = mqtt_client.publish(
                            MQTT_TOPIC,
                            message,
                            qos=1
                        )

                        print(
                            "MQTT SENT:",
                            message
                        )

                        print(
                            "MQTT RESULT:",
                            result.rc
                        )


                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )


                label = (
                    f"{animal} "
                    f"{confidence * 100:.0f}% "
                    f"| {risk}"
                )


                cv2.rectangle(
                    img,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    img,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )


        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )


if mqtt_status:

    st.success(
        "MQTT Broker Connected"
    )

else:

    st.error(
        "MQTT Broker Not Connected"
    )


st.subheader("Live Camera")


webrtc_streamer(
    key="wildshield-camera",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=WildlifeVideoProcessor,
    media_stream_constraints={
        "video": True,
        "audio": False
    },
    async_processing=True
)


st.subheader("Latest Detection")


events = get_events()


if len(events) > 0:

    animal, event_time, risk, confidence = events[0]


    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            "Animal",
            animal
        )


    with col2:

        st.metric(
            "Confidence",
            f"{confidence * 100:.0f}%"
        )


    with col3:

        st.metric(
            "Risk",
            risk
        )


    with col4:

        if risk == "HIGH":

            st.error(
                "ACTIVATE ALARM"
            )

        elif risk == "MEDIUM":

            st.warning(
                "NOTIFY FARMER"
            )

        else:

            st.info(
                "NO ACTION"
            )


    st.write(
        "Time :",
        event_time
    )


    if risk == "HIGH":

        st.error(
            "Action: Activate Alarm + Notify Farmer"
        )

    elif risk == "MEDIUM":

        st.warning(
            "Action: Notify Farmer"
        )

    else:

        st.info(
            "Action: No Action"
        )

else:

    st.info(
        "No detections yet."
    )


st.subheader("Detection History")


events = get_events()


if len(events) > 0:

    df = pd.DataFrame(
        events,
        columns=[
            "Animal",
            "Time",
            "Risk",
            "Confidence"
        ]
    )


    df["Confidence"] = (
        df["Confidence"] * 100
    ).round(0).astype(str) + "%"


    st.dataframe(
        df,
        use_container_width=True
    )

else:

    st.info(
        "No detection history available."
    )


st.subheader("Charts")


events = get_events()


if len(events) > 0:

    chart_df = pd.DataFrame(
        events,
        columns=[
            "Animal",
            "Time",
            "Risk",
            "Confidence"
        ]
    )


    col1, col2 = st.columns(2)


    with col1:

        st.write(
            "Animals Detected"
        )


        animal_counts = (
            chart_df["Animal"]
            .value_counts()
        )


        st.bar_chart(
            animal_counts
        )


    with col2:

        st.write(
            "Risk Distribution"
        )


        risk_counts = (
            chart_df["Risk"]
            .value_counts()
        )


        st.bar_chart(
            risk_counts
        )

else:

    st.info(
        "Charts will appear after detections."
    )


if st.button("Refresh Dashboard"):

    st.rerun()
