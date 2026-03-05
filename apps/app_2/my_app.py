import streamlit as st
import pandas as pd
import os

# --- Page configuration ---
st.set_page_config(page_title="Motorcycles Data", layout="wide", initial_sidebar_state="expanded")

# --- Charger le CSS depuis template1_style.css ---
css_file = "styles/template1_style.css"  # chemin vers ton fichier CSS
with open(css_file) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Titre principal (style appliqué via CSS h1) ---
st.markdown("<h1>MY DATA APP</h1>", unsafe_allow_html=True)

# --- Description ---
st.markdown("""
This app allows you to download scraped data on motorcycles from expat-dakar.
* **Python libraries:** pandas, streamlit
* **Data source:** [Expat-Dakar](https://www.expat-dakar.com/).
""")

# --- Sidebar menu ---
st.sidebar.title("Menu")
csv_files = [
    ("Motorcycles data 1", "data/motos_scooters1.csv"),
    ("Motorcycles data 2", "data/motos_scooters2.csv"),
    ("Motorcycles data 3", "data/motos_scooters3.csv"),
    ("Motorcycles data 4", "data/motos_scooters4.csv"),
    ("Motorcycles data 5", "data/motos_scooters5.csv")
]

menu_selection = st.sidebar.radio("Choose a dataset:", [name for name, _ in csv_files])

# --- Afficher le DataFrame sélectionné ---
for name, path in csv_files:
    if menu_selection == name:
        df = pd.read_csv(path)
        st.subheader(f"{name} ({df.shape[0]} rows x {df.shape[1]} columns)")
        st.dataframe(df)
        # --- Bouton de téléchargement ---
        st.sidebar.download_button(
            label=f"Download {name}",
            data=open(path, "rb").read(),
            file_name=os.path.basename(path),
            mime="text/csv"
        )
        break
