import sqlite3
import streamlit as st
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns
import pandas as pd
import database
DB = "agri_monitor.db"

database.create_table()
#database.insert_data()

# load css
css_file = Path(__file__).parent / "styles" / "template1_style.css"
with open(css_file) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)



def get_connection():
    return sqlite3.connect(DB, check_same_thread=False)


def q(sql):
    return pd.read_sql_query(sql, get_connection())


# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
st.markdown("### Welcome to AgroSense", unsafe_allow_html=True)
st.markdown(
    "A secure IoT-based platform to monitor agricultural fields, "
    "track sensor data, manage irrigation and optimize crop cycles in real time.",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# QUICK KPIs
# ------------------------------------------------------------------
st.markdown("### Platform at a glance")

total_farms    = q("SELECT COUNT(*) AS n FROM Farms").iloc[0]["n"]
total_fields   = q("SELECT COUNT(*) AS n FROM Fields").iloc[0]["n"]
active_devices = q("SELECT COUNT(*) AS n FROM IotDevices WHERE deviceStatus='Active'").iloc[0]["n"]
open_alerts    = q("SELECT COUNT(*) AS n FROM Alerts WHERE resolved=0").iloc[0]["n"]
growing_cycles = q("SELECT COUNT(*) AS n FROM CropCycles WHERE status='Growing'").iloc[0]["n"]
total_readings = q("SELECT COUNT(*) AS n FROM SensorReadings").iloc[0]["n"]

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Farms",          total_farms)
k2.metric("Fields",         total_fields)
k3.metric("Active Devices", active_devices)
k4.metric("Open Alerts",    open_alerts)
k5.metric("Growing Cycles", growing_cycles)
k6.metric("Total Readings", f"{total_readings:,}")

st.markdown("")

# ------------------------------------------------------------------
# WHAT THIS APP DOES
# ------------------------------------------------------------------
st.markdown("### What this app does")
st.markdown(
    """
    This platform allows you to:

    👉 **Monitor sensor data** (soil moisture, temperature, pH, humidity) from IoT devices deployed across all fields  
    👉 **Track irrigation events** and compare automated vs manual water usage over time  
    👉 **Analyse crop cycles** — yields per hectare, growth stages, harvest performance  
    👉 **Manage alerts** — view, filter and resolve anomalies detected by the sensor network  
    👉 **Explore weather data** collected at each farm to correlate with field conditions  
    👉 **Query the database** directly with the built-in data explorer  
    """
)

st.markdown("")

# ------------------------------------------------------------------
# HOW TO USE
# ------------------------------------------------------------------
st.markdown("### How to use the app")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("#### Sensor Dashboard")
    st.markdown(
        """
        - Select a farm and field
        - Choose a date range
        - View moisture, temperature and pH trends
        """
    )

with col2:
    st.markdown("#### Irrigation")
    st.markdown(
        """
        - Track daily water volumes
        - Compare automated vs manual events
        - Identify over- or under-irrigation
        """
    )

with col3:
    st.markdown("#### Crop Analytics")
    st.markdown(
        """
        - Compare yield per hectare by crop
        - View active and completed cycles
        - Monitor expected harvest dates
        """
    )

with col4:
    st.markdown("#### Alerts")
    st.markdown(
        """
        - Filter by severity and field
        - Resolve or escalate open alerts
        - Track alert history over time
        """
    )

st.markdown("")

# ------------------------------------------------------------------
# OVERVIEW CHARTS  (matplotlib / seaborn)
# ------------------------------------------------------------------
st.markdown("### Overview")

# --- data ---
moisture_df = q("""
    SELECT date(sr.timestamp) AS day, ROUND(AVG(sr.value), 2) AS avg_val
    FROM SensorReadings sr
    JOIN IotDevices d ON sr.deviceId = d.deviceId
    WHERE sr.metricType = 'soil_moisture'
    GROUP BY day ORDER BY day
""")

alerts_df = q("""
    SELECT alertType, COUNT(*) AS total
    FROM Alerts
    GROUP BY alertType
    ORDER BY total DESC
""")

yield_df = q("""
    SELECT c.cropName,
           ROUND(SUM(cc.yieldTons) / SUM(f.area_ha), 2) AS yield_per_ha
    FROM CropCycles cc
    JOIN Crops c  ON cc.cropId  = c.cropId
    JOIN Fields f ON cc.fieldId = f.fieldId
    WHERE cc.status = 'Completed' AND cc.yieldTons IS NOT NULL
    GROUP BY c.cropName
    ORDER BY yield_per_ha DESC
""")

irrig_df = q("""
    SELECT date(irrigStartTime) AS day,
           ROUND(SUM(waterVolume_m3), 1) AS volume
    FROM IrrigationEvents
    GROUP BY day ORDER BY day
""")

sns.set_theme(style="darkgrid")
ACCENT  = "#3ddc84"
ACCENT2 = "#4db8ff"
WARN    = "#f5a623"
BG      = "#111a14"
SURFACE = "#162019"
TEXT    = "#e8f0ea"

fig, axes = plt.subplots(2, 2, figsize=(14, 8))
fig.patch.set_facecolor(BG)
for ax in axes.flat:
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1f3025")

# 1 — soil moisture trend
ax1 = axes[0, 0]
if not moisture_df.empty:
    ax1.plot(moisture_df["day"], moisture_df["avg_val"],
             color=ACCENT, linewidth=1.8, alpha=0.9)
    ax1.fill_between(moisture_df["day"], moisture_df["avg_val"],
                     alpha=0.15, color=ACCENT)
    ax1.axhline(20, color=WARN, linewidth=0.8, linestyle="--", alpha=0.7, label="Min threshold")
    ax1.axhline(40, color=WARN, linewidth=0.8, linestyle="--", alpha=0.7, label="Max threshold")
    step = max(1, len(moisture_df) // 6)
    ax1.set_xticks(moisture_df["day"].iloc[::step])
    ax1.set_xticklabels(moisture_df["day"].iloc[::step], rotation=30, ha="right", fontsize=7)
    ax1.legend(fontsize=7, facecolor=SURFACE, labelcolor=TEXT, framealpha=0.6)
ax1.set_title("Avg Soil Moisture — all fields", fontsize=10, fontweight="bold")
ax1.set_ylabel("%", fontsize=8)

# 2 — alert types bar
ax2 = axes[0, 1]
if not alerts_df.empty:
    colors_bar = [ACCENT, ACCENT2, WARN, "#ff4d4d", "#a78bfa",
                  "#34d399", "#fb923c", "#e879f9"][:len(alerts_df)]
    bars = ax2.barh(alerts_df["alertType"], alerts_df["total"],
                    color=colors_bar, edgecolor="none", height=0.6)
    for bar, val in zip(bars, alerts_df["total"]):
        ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                 str(val), va="center", color=TEXT, fontsize=8)
    ax2.set_xlim(0, alerts_df["total"].max() * 1.25)
ax2.set_title("Alerts by Type", fontsize=10, fontweight="bold")
ax2.set_xlabel("Count", fontsize=8)

# 3 — yield per hectare
ax3 = axes[1, 0]
if not yield_df.empty:
    palette = sns.color_palette("Greens_d", len(yield_df))
    bars3 = ax3.bar(yield_df["cropName"], yield_df["yield_per_ha"],
                    color=palette, edgecolor="none")
    for bar, val in zip(bars3, yield_df["yield_per_ha"]):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f"{val}", ha="center", color=TEXT, fontsize=8)
ax3.set_title("Yield per Hectare by Crop (completed cycles)", fontsize=10, fontweight="bold")
ax3.set_ylabel("t / ha", fontsize=8)
ax3.set_xticklabels(yield_df["cropName"], rotation=20, ha="right", fontsize=8)

# 4 — irrigation volume over time
ax4 = axes[1, 1]
if not irrig_df.empty:
    ax4.bar(irrig_df["day"], irrig_df["volume"],
            color=ACCENT2, alpha=0.8, edgecolor="none", width=0.6)
    step4 = max(1, len(irrig_df) // 8)
    ax4.set_xticks(irrig_df["day"].iloc[::step4])
    ax4.set_xticklabels(irrig_df["day"].iloc[::step4], rotation=30, ha="right", fontsize=7)
ax4.set_title("Daily Irrigation Volume — all fields", fontsize=10, fontweight="bold")
ax4.set_ylabel("m³", fontsize=8)

plt.tight_layout(pad=2.0)
st.pyplot(fig)
plt.close()

# ------------------------------------------------------------------
# HOW TO START
# ------------------------------------------------------------------
st.markdown("")
st.markdown("### How to start?")
st.markdown(
    "👉 Use the menu on the left to navigate between the different modules."
)
