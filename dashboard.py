
import cv2
import av
import time
import uuid
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


MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "wildshield/alert"


@st.cache_resource
def create_mqtt_client():

    state = {
        "connected": False,
        "error": ""
    }

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="wildshield-" + uuid.uuid4().hex[:12]
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            state["connected"] = False
            state["error"] = str(reason_code)
        else:
            state["connected"] = True
            state["error"] = ""

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        state["connected"] = False
        if reason_code.is_failure:
            state["error"] = str(reason_code)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )
        client.loop_start()

    except Exception as e:
        state["error"] = str(e)

    return client, state


mqtt_client, mqtt_state = create_mqtt_client()


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


class WildlifeVideoProcessor(VideoProcessorBase):

    def __init__(self):
        self.model = YOLO("best.pt")
        self.last_saved = {}
        self.cooldown = 10

    def recv(self, frame):

        img = frame.to_ndarray(format="bgr24")

        results = self.model(img, verbose=False)

        for result in results:
            for box in result.boxes:

                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                if confidence < 0.50:
                    continue

                animal = self.model.names[class_id]

                if animal in high_risk:
                    risk = "HIGH"
                    action = "Activate Alarm + Notify Farmer"

                elif animal in medium_risk:
                    risk = "MEDIUM"
                    action = "Notify Farmer"

                else:
                    risk = "LOW"
                    action = "No Action"

                current_time = time.time()

                if (
                    animal not in self.last_saved
                    or current_time - self.last_saved[animal] >= self.cooldown
                ):

                    try:
                        save_event(animal, risk, confidence)
                    except Exception as e:
                        print("Database error:", e)

                    self.last_saved[animal] = current_time

                    message = (
                        f"{animal.upper()}|"
                        f"{confidence * 100:.0f}|"
                        f"{risk}"
                    )

                    if mqtt_state["connected"]:
                        try:
                            info = mqtt_client.publish(
                                MQTT_TOPIC,
                                message,
                                qos=0
                            )

                            print(
                                "MQTT PUBLISH:",
                                message,
                                "RESULT:",
                                info.rc
                            )

                        except Exception as e:
                            print("MQTT publish error:", e)

                    else:
                        print("MQTT not connected:", message)

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                label = (
                    f"{animal} "
                    f"{confidence * 100:.0f}% | {risk}"
                )

                color = (
                    (0, 0, 255) if risk == "HIGH"
                    else (0, 165, 255) if risk == "MEDIUM"
                    else (0, 255, 0)
                )

                cv2.rectangle(
                    img,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2
                )

                cv2.putText(
                    img,
                    label,
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )


if mqtt_state["connected"]:
    st.success("MQTT Broker Connected")
elif mqtt_state["error"]:
    st.error("MQTT Connection Failed: " + mqtt_state["error"])
else:
    st.info("Connecting to MQTT broker...")


st.caption("MQTT Topic: " + MQTT_TOPIC)


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
        st.metric("Animal", animal)

    with col2:
        st.metric("Confidence", f"{confidence * 100:.0f}%")

    with col3:
        st.metric("Risk", risk)

    with col4:
        if risk == "HIGH":
            st.error("ACTIVATE ALARM")
        elif risk == "MEDIUM":
            st.warning("NOTIFY FARMER")
        else:
            st.info("NO ACTION")

    st.write("Time:", event_time)

    if risk == "HIGH":
        st.error("Action: Activate Alarm + Notify Farmer")
    elif risk == "MEDIUM":
        st.warning("Action: Notify Farmer")
    else:
        st.info("Action: No Action")

else:
    st.info("No detections yet.")


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
    st.info("No detection history available.")


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
        st.write("Animals Detected")
        st.bar_chart(chart_df["Animal"].value_counts())

    with col2:
        st.write("Risk Distribution")
        st.bar_chart(chart_df["Risk"].value_counts())

else:
    st.info("Charts will appear after detections.")


if st.button("Refresh Dashboard"):
    st.rerun()
