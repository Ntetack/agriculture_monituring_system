import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

DB = "agri_monitor.db"

def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def q(sql, params=()):
    return pd.read_sql_query(sql, get_conn(), params=params)

# ── Page config ──────────────────────────────────────────────
st.set_page_config(page_title="IoTAM", layout="wide")
st.markdown("<h1 style='color: green;'>Raw Sensor Readings Explorer</h1>", unsafe_allow_html=True)

# ── Sidebar filters ──────────────────────────────────────────
farms = q("SELECT farmId, name FROM Farms")
farm_options = {"All Farms": None} | dict(zip(farms["name"], farms["farmId"]))
selected_farm = st.sidebar.selectbox("Farm", list(farm_options.keys()))
farm_id = farm_options[selected_farm]

fields_sql = "SELECT fieldId, name FROM Fields" + (" WHERE farmId=?" if farm_id else "")
fields = q(fields_sql, (farm_id,) if farm_id else ())
field_options = {"All Fields": None} | dict(zip(fields["name"], fields["fieldId"]))
selected_field = st.sidebar.selectbox("Field", list(field_options.keys()))
field_id = field_options[selected_field]

st.sidebar.divider()
st.sidebar.markdown("**Date range (sensor readings)**")
date_from = st.sidebar.date_input("From", value=date(2026, 1, 28))
date_to   = st.sidebar.date_input("To",   value=date(2026, 2, 27))


metric_type = st.selectbox(
    "Sensor Metric",
    ["soil_moisture", "temperature", "soil_ph", "humidity"]
)

raw_df = q(f"""
    SELECT sr.readingId, f.name AS field, d.deviceType, d.deviceSerialNumber,
           sr.metricType, sr.value, sr.unit, sr.timestamp, sr.anomalyFlag
    FROM SensorReadings sr
    JOIN IotDevices d ON sr.deviceId=d.deviceId
    JOIN Fields f ON d.fieldId=f.fieldId
    WHERE sr.metricType=?
      AND date(sr.timestamp) BETWEEN ? AND ?
        {"AND f.farmId=?" if farm_id else ""}
      {"AND f.fieldId=?" if field_id else ""}
    ORDER BY sr.timestamp DESC
    LIMIT 500
""", [metric_type, str(date_from), str(date_to)] + ([farm_id] if farm_id else []) + ([field_id] if field_id else []))

# KPI
if not raw_df.empty:

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Total Readings", len(raw_df))
    c2.metric("Average", round(raw_df["value"].mean(), 2))
    c3.metric("Min", round(raw_df["value"].min(), 2))
    c4.metric("Max", round(raw_df["value"].max(), 2))
    c5.metric("Anomalies", int(raw_df["anomalyFlag"].sum()))


st.markdown("")
st.markdown("")

st.dataframe(raw_df, use_container_width=True, hide_index=True)
st.caption(f"{len(raw_df)} rows shown (max 500)")

