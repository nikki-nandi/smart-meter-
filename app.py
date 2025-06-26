import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import smtplib
import pydeck as pdk
from datetime import datetime
from email.message import EmailMessage
from tensorflow.keras.models import load_model
import joblib

# Suppress log clutter
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# CONFIG
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
EMAIL_ALERTS = True
ALERT_EMAIL = "nikithnandi2004@gmail.com"
EMAIL_SENDER = "nikithnandi08@gmail.com"
EMAIL_PASSWORD = "sshz jpyi pibg jxev"

# Streamlit setup
st.set_page_config(page_title="🔌 Smart Meter Dashboard", layout="wide")
st.title("🔌 Real-Time Smart Meter Monitoring & Anomaly Detection")

# Sidebar
refresh_rate = st.sidebar.slider("🔁 Refresh interval (sec)", 1, 10, 5)
data_choice = st.sidebar.radio("🧪 Data Source", ["Real", "Simulated"])
st.sidebar.header("🚨 Live Alerts")
alert_box = st.sidebar.empty()

# Data Load
DATA_PATH = "preprocessed_data.csv" if data_choice == "Real" else "data/simulated_data.csv"
if not os.path.exists(DATA_PATH):
    st.warning("⚠️ Missing data file!")
    st.stop()
df = pd.read_csv(DATA_PATH, parse_dates=["RealtimeClockDateandTime"], dayfirst=True)

# Functions
def detect_row_anomalies(row):
    reasons = []
    if row['Voltage'] < 180 or row['Voltage'] > 250:
        reasons.append("Voltage anomaly")
    if row['SystemPowerFactor'] < 0.5:
        reasons.append("Low power factor")
    if row['ActivePower_kW'] < 0:
        reasons.append("Negative active power")
    if row['Frequency'] < 48.5 or row['Frequency'] > 51.5:
        reasons.append("Frequency anomaly")
    if row['BlockEnergykWh'] == 0:
        reasons.append("Zero energy consumption")
    return reasons

def send_email_alert(anomalies):
    if not anomalies or not EMAIL_ALERTS:
        return
    msg = EmailMessage()
    msg["Subject"] = "⚠️ Smart Meter Anomaly Alert"
    msg["From"] = EMAIL_SENDER
    msg["To"] = ALERT_EMAIL
    msg.set_content("Anomalies Detected:\n\n" + "\n".join(anomalies))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        st.error(f"❌ Email failed: {e}")

# Real-time Loop
log_file = os.path.join(LOG_DIR, f"{datetime.today().strftime('%Y-%m-%d')}_log.txt")
anomaly_log = []
placeholder = st.empty()
i = 0

while i < len(df):
    with placeholder.container():
        row = df.iloc[i]
        st.subheader(f"Meter ID: `{row['METERSNO']}` | Time: {row['RealtimeClockDateandTime']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🔋 Voltage", f"{row['Voltage']:.2f}")
        col2.metric("⚡ Current", f"{row['NormalPhaseCurrent']:.2f}")
        col3.metric("📊 Power Factor", f"{row['SystemPowerFactor']:.2f}")
        col4.metric("🌐 Frequency", f"{row['Frequency']:.2f}")

        st.markdown("### 📈 Energy Usage")
        st.line_chart(df.iloc[:i+1][['BlockEnergykWh', 'CumulativeEnergykWh']])

        st.markdown("### 🗺️ Location")
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=row['Latitude'],
                longitude=row['Longitude'],
                zoom=12,
                pitch=50,
            ),
            layers=[
                pdk.Layer(
                    'ScatterplotLayer',
                    data=df.iloc[i:i+1],
                    get_position='[Longitude, Latitude]',
                    get_color='[200, 30, 0, 160]',
                    get_radius=500,
                ),
            ],
        ))

        anomalies = detect_row_anomalies(row)
        timestamp = row['RealtimeClockDateandTime']
        alert_lines = [f"[{timestamp}] - {reason}" for reason in anomalies]

        if anomalies:
            alert_box.error("\n".join(alert_lines))
            anomaly_log.extend(alert_lines)
            with open(log_file, "a") as log:
                log.write("\n".join(alert_lines) + "\n")
            send_email_alert(alert_lines)
        else:
            alert_box.success("✅ No anomalies detected")

    i += 1
    time.sleep(refresh_rate)

# Wrap Up
st.success("✅ Monitoring Completed")
if anomaly_log:
    st.subheader("📋 Final Anomaly Summary")
    st.code("\n".join(anomaly_log))

# Log Viewer
st.markdown("---")
st.subheader("📂 View Past Logs")
if os.path.exists(LOG_DIR):
    logs = sorted(os.listdir(LOG_DIR), reverse=True)
    selected_log = st.selectbox("📄 Select log file", logs)
    if selected_log:
        with open(os.path.join(LOG_DIR, selected_log)) as f:
            st.code(f.read(), language="text")
else:
    st.info("No logs found.")
