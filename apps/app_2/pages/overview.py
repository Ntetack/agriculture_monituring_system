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


# ── Plotly global style ──────────────────────────────────────
PLOTLY_TEMPLATE = "plotly_white"

def style_fig(fig):

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        font=dict(
            family="Arial",
            size=14
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        title=dict(x=0)
    )

    fig.update_xaxes(
        showgrid=False,
        linecolor="lightgray"
    )

    fig.update_yaxes(
        gridcolor="rgba(200,200,200,0.25)",
        zeroline=False
    )

    return fig


# ── Page config ──────────────────────────────────────────────
st.set_page_config(page_title="IoTAM", layout="wide")
st.markdown("<h1 style='color: green;'>Overview</h1>", unsafe_allow_html=True)


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

crops_sql = "SELECT cropId, cropName FROM Crops" + (" WHERE cropId IN (SELECT cropId FROM CropCycles WHERE fieldId=?)" if field_id else "")
crops = q(crops_sql, (field_id,) if field_id else ())
crop_options = {"All Crops": None} | dict(zip(crops["cropName"], crops["cropId"]))
selected_crop = st.sidebar.selectbox("Crop", list(crop_options.keys()))
crop_id = crop_options[selected_crop]

st.sidebar.divider()

alert_types = q("SELECT DISTINCT severity FROM Alerts")
alert_type_options = {"All Types": None} | dict(zip(alert_types["severity"], alert_types["severity"]))
selected_alert_type = st.sidebar.selectbox("Severity of Alerts", list(alert_type_options.keys()))
alert_type_filter = alert_type_options[selected_alert_type]

st.sidebar.divider()

st.sidebar.markdown("Date range (sensor readings)")
date_from = st.sidebar.date_input("From", value=date(2026, 1, 28))
date_to   = st.sidebar.date_input("To",   value=date(2026, 2, 27))


# ── KPIs ─────────────────────────────────────────────────────
st.subheader("Key Metrics")

k6, k1, k2, k3, k4, k5 = st.columns(6)

farms_n = q("SELECT COUNT(farmId) AS n FROM Farms").iloc[0]["n"]
k6.metric("Farms", farms_n)

active_fields = q("SELECT COUNT(fieldId) AS n FROM CropCycles WHERE status='Growing'").iloc[0]["n"]
k1.metric("Active Fields", active_fields)

avg_moist = q("""
SELECT ROUND(AVG(value),2) as v
FROM sensorReadings
WHERE metricType = 'soil_moisture'
""").iloc[0]["v"]

k2.metric("Avg Soil Moisture", f"{avg_moist}")

water_today = q("""
SELECT COALESCE(SUM(waterVolume_m3), 0) AS v
FROM irrigationEvents
WHERE DATE(irrigStartTime) = DATE('now')
""").iloc[0]["v"]

k3.metric("Water Used Today", f"{water_today} m³")

active_alerts = q("SELECT COUNT(*) AS n FROM Alerts WHERE resolved=0").iloc[0]["n"]
k4.metric("Active Alerts", active_alerts)

active_devices = q("SELECT COUNT(*) AS n FROM IotDevices WHERE deviceStatus='Active'").iloc[0]["n"]
k5.metric("Active Devices", active_devices)

st.divider()


# ── Sensor trends ─────────────────────────────────────────────
st.subheader("Sensor Trends")

col1, col2, col3 = st.columns(3)

field_clause = ""
field_params = []

if field_id:
    field_clause = "AND d.fieldId = ?"
    field_params = [field_id]


# ── Moisture data
moisture_df = q(f"""
SELECT date(sr.timestamp) AS day,
       ROUND(AVG(sr.value),2) AS avg_moisture
FROM SensorReadings sr
JOIN IotDevices d ON sr.deviceId = d.deviceId
WHERE sr.metricType='soil_moisture'
AND date(sr.timestamp) BETWEEN ? AND ?
{field_clause}
GROUP BY day
ORDER BY day
""", [str(date_from), str(date_to)] + field_params)


# ── Temperature data
temp_df = q(f"""
SELECT date(sr.timestamp) AS day,
       ROUND(AVG(sr.value),2) AS avg_temp
FROM SensorReadings sr
JOIN IotDevices d ON sr.deviceId = d.deviceId
WHERE sr.metricType='temperature'
AND date(sr.timestamp) BETWEEN ? AND ?
{field_clause}
GROUP BY day
ORDER BY day
""", [str(date_from), str(date_to)] + field_params)


# ── Soil Moisture Area Chart
with col1:

    if not moisture_df.empty:

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=moisture_df["day"],
            y=moisture_df["avg_moisture"],
            mode="lines+markers",
            line=dict(color="#2E8B57", width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(46,139,87,0.25)",
            name="Moisture"
        ))

        fig.add_hline(y=20, line_dash="dot", line_color="orange")
        fig.add_hline(y=40, line_dash="dot", line_color="orange")

        fig = style_fig(fig)

        fig.update_layout(title="Avg Soil Moisture (%)")

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No moisture data for selected range/field.")


# ── Temperature Area Chart
with col2:

    if not temp_df.empty:

        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            x=temp_df["day"],
            y=temp_df["avg_temp"],
            mode="lines+markers",
            line=dict(color="#E5533D", width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(229,83,61,0.25)",
            name="Temperature"
        ))

        fig2 = style_fig(fig2)

        fig2.update_layout(title="Avg Temperature (°C)")

        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.info("No temperature data for selected range/field.")


# ── Irrigation data
irrig_clause = "WHERE date(irrigStartTime) BETWEEN ? AND ?" + (" AND fieldId=?" if field_id else "")
irrig_params = [str(date_from), str(date_to)] + ([field_id] if field_id else [])

irrig_df = q(f"""
SELECT date(irrigStartTime) AS day,
       COUNT(*) AS events,
       ROUND(SUM(waterVolume_m3),1) AS total_m3
FROM IrrigationEvents
{irrig_clause}
GROUP BY day
ORDER BY day
""", irrig_params)


# ── Irrigation chart
with col3:

    if not irrig_df.empty:

        fig3 = px.bar(
            irrig_df,
            x="day",
            y="total_m3",
            title="Irrigation Volume (m³ / day)",
            hover_data=["events"],
            color="total_m3",
            color_continuous_scale="Blues"
        )

        fig3.update_layout(coloraxis_showscale=False)

        fig3 = style_fig(fig3)

        st.plotly_chart(fig3, use_container_width=True)

    else:
        st.info("No irrigation events in selected range.")