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
st.markdown("<h1 style='color: green;'>Alert Monitoring</h1>", unsafe_allow_html=True)

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
st.sidebar.markdown("Severity Alerts")
alert_types = q("SELECT DISTINCT severity FROM Alerts")
alert_type_options = {"All Types": None} | dict(zip(alert_types["severity"], alert_types["severity"]))
selected_alert_type = st.sidebar.selectbox("Severity", list(alert_type_options.keys()))
alert_type_filter = alert_type_options[selected_alert_type]

st.sidebar.divider()
st.sidebar.markdown("Date range (sensor readings)")
date_from = st.sidebar.date_input("From", value=date(2026, 1, 28))
date_to   = st.sidebar.date_input("To",   value=date(2026, 2, 27))

# ── Alerts Overview ─────────────────────────────────────────
st.subheader("Alerts Overview")

k1, k2, k3, k4, k5 = st.columns(5)

kpi_df = q(f"""
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN a.resolved=0 THEN 1 ELSE 0 END) AS active,
    SUM(CASE WHEN a.resolved=1 THEN 1 ELSE 0 END) AS resolved,
    SUM(CASE WHEN a.severity='Critical' THEN 1 ELSE 0 END) AS critical
FROM Alerts a
JOIN Fields f ON a.fieldId=f.fieldId
WHERE date(a.createdAt) BETWEEN ? AND ?
    {"AND f.farmId=?" if farm_id else ""}
    {"AND f.fieldId=?" if field_id else ""}
    {"AND a.severity=?" if alert_type_filter else ""}
""",
[str(date_from), str(date_to)]
+ ([farm_id] if farm_id else [])
+ ([field_id] if field_id else [])
+ ([alert_type_filter] if alert_type_filter else [])
)

total_alerts = int(kpi_df["total"][0])
active_alerts = int(kpi_df["active"][0])
resolved_alerts = int(kpi_df["resolved"][0])
critical_alerts = int(kpi_df["critical"][0])

k1.metric("Total Alerts", total_alerts)
k2.metric("Active Alerts", active_alerts)
k3.metric("Resolved Alerts", resolved_alerts)
k4.metric("Critical Alerts", critical_alerts)

severity_df = q("""
    SELECT severity, COUNT(*) AS total
    FROM Alerts
    WHERE resolved=0
    GROUP BY severity
    
    ORDER BY total DESC
""")

if not severity_df.empty:
    fig = px.bar(
        severity_df,
        x="total",
        y="severity",
        text="total",  # Affiche la valeur numérique
        title="Active Alerts by Severity",
        orientation="h",
        height=160,
        color="severity",
        color_discrete_map={
            "Critical": "#D8340B",
            "High": "#E98C13",
            "Medium": "#DAC720",
            "Low": "#74DA20"
        }
    )
    
    fig.update_traces(
        textposition="outside", # Place le chiffre juste après la barre
        cliponaxis=False        # Évite que le texte soit coupé
    )

    fig.update_layout(
        margin=dict(l=0, r=40, t=40, b=0),
        yaxis_title=None,
        xaxis_title=None,
        showlegend=False,       
        plot_bgcolor="rgba(0,0,0,0)", 
    )

    fig.update_xaxes(visible=False) # Enlève la numérotation et la grille de l'axe X


    k5.plotly_chart(fig, use_container_width=True)


# ── Alerts ────────────────────────────────────────────────────
st.subheader("Alerts History")
alerts_clause = ""
alerts_params = []
if field_id:
    alerts_clause = "WHERE a.fieldId=?"
    alerts_params = [field_id]

alerts_df = q(f"""
SELECT a.alertId,
       f.name AS field,
       a.alertType,
       a.severity,
       a.message,
       a.createdAt,
       CASE WHEN a.resolved=1 THEN 'Resolved' ELSE 'Open' END AS status
FROM Alerts a
JOIN Fields f ON a.fieldId=f.fieldId
WHERE date(a.createdAt) BETWEEN ? AND ?
    {"AND f.farmId=?" if farm_id else ""}
    {"AND f.fieldId=?" if field_id else ""}
    {"AND a.severity=?" if alert_type_filter else ""}
ORDER BY a.createdAt DESC
""",
[str(date_from), str(date_to)]
+ ([farm_id] if farm_id else [])
+ ([field_id] if field_id else [])
+ ([alert_type_filter] if alert_type_filter else [])
)

col_filter1, col_filter2 = st.columns([1, 4])
show_open_only = col_filter1.checkbox("Open only", value=False)
if show_open_only:
    alerts_df = alerts_df[alerts_df["status"] == "Open"]

st.dataframe(
    alerts_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "severity": st.column_config.TextColumn("Severity"),
        "status": st.column_config.TextColumn("Status"),
    }
)

st.divider()

