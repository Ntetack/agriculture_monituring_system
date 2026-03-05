import sqlite3
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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
st.markdown("<h1 style='color: green;'>Crop Monitoring</h1>", unsafe_allow_html=True)

# ── Sidebar filters ──────────────────────────────────────────
farms = q("SELECT farmId, name FROM Farms")
farm_options = {"All Farms": None} | dict(zip(farms["name"], farms["farmId"]))
selected_farm = st.sidebar.selectbox("Farm", list(farm_options.keys()))
farm_id = farm_options[selected_farm]

#st.markdown("**All Crop Cycles**")



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
st.sidebar.markdown("**Date range (sensor readings)**")
date_from = st.sidebar.date_input("From", value=date(2026, 1, 28))
date_to   = st.sidebar.date_input("To",   value=date(2026, 2, 27))

cycles_df = q(f"""
    SELECT cc.cycleId,
           f.name AS field,
           c.cropName AS crop,
           cc.plantingDate,
           cc.expectedHarvestDate,
           cc.actualHarvestDate,
           cc.yieldTons,
           cc.status
    FROM CropCycles cc
    JOIN Fields f ON cc.fieldId = f.fieldId
    JOIN Crops c ON cc.cropId = c.cropId
    WHERE date(cc.plantingDate) BETWEEN ? AND ?
        {"AND f.farmId=?" if farm_id else ""}
        {"AND f.fieldId=?" if field_id else ""}
        {"AND c.cropId=?" if crop_id else ""}
    ORDER BY cc.plantingDate DESC
""",
[str(date_from), str(date_to)]
+ ([farm_id] if farm_id else [])
+ ([field_id] if field_id else [])
+ ([crop_id] if crop_id else [])
)

if not cycles_df.empty:

    k4, k1, k2, k3 = st.columns(4)

    total_cycles = len(cycles_df)
    active_cycles = (cycles_df["status"] == "Growing").sum()
    completed_cycles = (cycles_df["status"] == "Completed").sum()
    total_crops = cycles_df["crop"].nunique()
    cycles_df["plantingDate"] = pd.to_datetime(cycles_df["plantingDate"])
    cycles_df["expectedHarvestDate"] = pd.to_datetime(cycles_df["expectedHarvestDate"])
    mean_cycle = (cycles_df["expectedHarvestDate"] - cycles_df["plantingDate"]).dt.days.mean()

    total_yield = cycles_df["yieldTons"].sum()
    avg_yield = cycles_df["yieldTons"].mean()

    #k1.metric("Total Cycles", total_cycles)
    k1.metric("Active Cycles", int(active_cycles))
    k2.metric("Avg Cycle Duration (days)", round(mean_cycle, 1))
    k4.metric("Total Crops", total_crops, delta_color="inverse")
    k3.metric("Avg Yield (t)", round(avg_yield, 2))

st.divider()
st.dataframe(cycles_df, use_container_width=True, hide_index=True)
