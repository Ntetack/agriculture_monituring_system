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
st.title("IoT Agricultural Monitoring")

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

# ── KPIs ─────────────────────────────────────────────────────


# ── Sensor trends ─────────────────────────────────────────────

# ── Irrigation & Anomalies ────────────────────────────────────
col3, col4 = st.columns(2)

yield_df = q("""
    SELECT c.cropName,
           COUNT(cc.cycleId) AS seasons,
           ROUND(SUM(cc.yieldTons),2) AS total_yield,
           ROUND(SUM(f.area_ha),2) AS total_area,
           ROUND(SUM(cc.yieldTons)/SUM(f.area_ha),3) AS yield_per_ha
    FROM CropCycles cc
    JOIN Crops c ON cc.cropId=c.cropId
    JOIN Fields f ON cc.fieldId=f.fieldId
    WHERE cc.status='Completed' AND cc.yieldTons IS NOT NULL
    GROUP BY c.cropName
    ORDER BY yield_per_ha DESC
""")

irrig_clause = "WHERE date(irrigStartTime) BETWEEN ? AND ?" + (" AND fieldId=?" if field_id else "")
irrig_params = [str(date_from), str(date_to)] + ([field_id] if field_id else [])

irrig_df = q(f"""
    SELECT date(irrigStartTime) AS day,
           COUNT(*) AS events,
           ROUND(SUM(waterVolume_m3),1) AS total_m3
    FROM IrrigationEvents
    {irrig_clause}
    GROUP BY day ORDER BY day
""", irrig_params)

with col3:
    if not irrig_df.empty:
        fig3 = px.bar(irrig_df, x="day", y="total_m3",
                      title="Irrigation Volume (m³ / day)",
                      labels={"day": "", "total_m3": "m³"},
                      hover_data=["events"])
        
        fig3.update_layout(
        margin=dict(l=0, r=40, t=40, b=0),
        yaxis_title=None,
        xaxis_title=None,
        showlegend=False,       
        plot_bgcolor="rgba(0,0,0,0)", 
    )

        fig3.update_xaxes(visible=False) # Enlève la numérotation et la grille de l'axe X

        st.plotly_chart(fig3, use_container_width=True)

        
    else:
        st.info("No irrigation events in selected range.")

anomaly_df = q(f"""
    SELECT f.name AS field,
           SUM(sr.anomalyFlag) AS anomalies,
           COUNT(sr.readingId) AS total,
           ROUND(100.0*SUM(sr.anomalyFlag)/COUNT(sr.readingId),2) AS rate_pct
    FROM SensorReadings sr
    JOIN IotDevices d ON sr.deviceId=d.deviceId
    JOIN Fields f ON d.fieldId=f.fieldId
    WHERE date(sr.timestamp) BETWEEN ? AND ?
    {"AND f.fieldId=?" if field_id else ""}
    GROUP BY f.fieldId
    ORDER BY anomalies DESC
""", [str(date_from), str(date_to)] + ([field_id] if field_id else []))

with col4:
    if not yield_df.empty:
        fig5 = px.bar(
            yield_df,
            x="cropName",
            y="yield_per_ha",
            color="cropName",  #  une couleur par crop
            title="Avg Yield per Hectare (completed cycles)",
            labels={"cropName": "Crop", "yield_per_ha": "t/ha"},
            text="yield_per_ha"
        )

        fig5.update_layout(
        margin=dict(l=0, r=40, t=40, b=0),
        yaxis_title=None,
        xaxis_title=None,
        showlegend=False,       
        plot_bgcolor="rgba(0,0,0,0)", 
    )

        #fig5.update_xaxes(visible=False) # Enlève la numérotation et la grille de l'axe X


        st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ── Yield Analysis ────────────────────────────────────────────
st.subheader("Yield Analysis")
col5, col6 = st.columns(2)



with col5:
    if not anomaly_df.empty:
        fig4 = px.bar(anomaly_df, x="anomalies", y="field", orientation="h",
                      title="Sensor Anomalies by Field",
                      labels={"anomalies": "Anomaly Count", "field": ""},
                      color="anomalies",
                      hover_data=["rate_pct"])
        st.plotly_chart(fig4, use_container_width=True)
        fig4.update_layout(
        margin=dict(l=0, r=40, t=40, b=0),
        yaxis_title=None,
        xaxis_title=None,
        showlegend=False,       
        plot_bgcolor="rgba(0,0,0,0)", 
    )

        fig4.update_xaxes(visible=False) # Enlève la numérotation et la grille de l'axe X

    else:
        st.info("No anomaly data.")

with col6:
    st.markdown("**Alerts analysis**")

    alerts_df = q("""
        SELECT alertType, COUNT(*) AS total
        FROM Alerts
        GROUP BY alertType
        ORDER BY total DESC
    """)

    if not alerts_df.empty:

        fig = px.pie(
            alerts_df,
            names="alertType",
            values="total",   # correction ici
            title="Alert Types Distribution (%)",
            hole=0.4,
            #template="seaborn",
            color_discrete_sequence=px.colors.sequential.Blues
        )

        fig.update_traces(textinfo="percent+label")
        fig.update_layout(
        margin=dict(l=0, r=40, t=40, b=0),
        yaxis_title=None,
        xaxis_title=None,
        showlegend=False,       
        plot_bgcolor="rgba(0,0,0,0)", 
    )

        fig.update_xaxes(visible=False) # Enlève la numérotation et la grille de l'axe X


        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No alert data available.")

st.divider()
