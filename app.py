import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATIE ---
st.set_page_config(page_title="Kassa Pro", page_icon="💶", layout="wide") 
# Layout 'wide' geeft meer ademruimte voor de split-view

# CSS: Maak de headers wat strakker en de metrics groter
st.markdown("""
    <style>
    .stMetric { background-color: #f9f9f9; padding: 15px; border-radius: 5px; border: 1px solid #eee; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'reset_id' not in st.session_state:
    st.session_state.reset_id = 0

def reset_app():
    st.session_state.reset_id += 1
    st.session_state.omschrijving = ""

# --- HEADER ---
c1, c2, c3 = st.columns([1, 2, 2])
with c1:
    st.title("💶 Kassa")
with c2:
    datum = st.date_input("Datum", datetime.now(), label_visibility="collapsed")
with c3:
    omschrijving = st.text_input("Omschrijving", placeholder="Notitie...", label_visibility="collapsed", key="omschrijving")

st.divider()

# --- INPUT SECTIE (LINKS VS RECHTS) ---
col_L, col_M, col_R = st.columns([4, 1, 4]) 
# De middelste kolom (1) is voor witruimte/scheiding

# --- LINKS: HET TICKET (OMZET) ---
with col_L:
    st.subheader("1. Het Ticket (Omzet)")
    st.caption("Vul de totalen per BTW-tarief in.")
    
    # Startdata vastleggen
    df_links = pd.DataFrame([
        {"Categorie": "0% (Vrijgesteld)", "Bedrag": 0.00},
        {"Categorie": "6% (Voeding)",     "Bedrag": 0.00},
        {"Categorie": "12% (Horeca)",     "Bedrag": 0.00},
        {"Categorie": "21% (Algemeen)",   "Bedrag": 0.00},
    ])

    # De Linker Editor
    edited_links = st.data_editor(
        df_links,
        column_config={
            "Categorie": st.column_config.TextColumn("Tarief", disabled=True),
            "Bedrag": st.column_config.NumberColumn(
                "Bedrag (€)", 
                min_value=0, 
                format="%.2f", 
                required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key=f"grid_links_{st.session_state.reset_id}"
    )

    # Subtotaal Links (Visueel hulpmiddel)
    som_links = edited_links["Bedrag"].sum()


# --- RECHTS: DE LADE (GELD) ---
with col_R:
    st.subheader("2. De Lade (Ontvangst)")
    st.caption("Vul de getelde bedragen in.")
    
    # Startdata vastleggen
    df_rechts = pd.DataFrame([
        {"Methode": "Bancontact", "Bedrag": 0.00},
        {"Methode": "Cash",       "Bedrag": 0.00},
        {"Methode": "Payconiq",   "Bedrag": 0.00},
    ])

    # De Rechter Editor
    edited_rechts = st.data_editor(
        df_rechts,
        column_config={
            "Methode": st.column_config.TextColumn("Betaalwijze", disabled=True),
            "Bedrag": st.column_config.NumberColumn(
                "Bedrag (€)", 
                min_value=0, 
                format="%.2f", 
                required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key=f"grid_rechts_{st.session_state.reset_id}"
    )
    
    # Subtotaal Rechts
    som_rechts = edited_rechts["Bedrag"].sum()


# --- DE VALIDATIE BALK (ONDERAAN) ---
st.divider()

verschil = round(som_links - som_rechts, 2)
is_valid = (som_links > 0) and (verschil == 0)

# We gebruiken metrics voor een duidelijk dashboard-gevoel
m1, m2, m3 = st.columns(3)

with m1:
    st.metric(label="Totaal Ticket", value=f"€ {som_links:.2f}")

with m2:
    color_diff = "normal"
    if som_links > 0:
        if verschil == 0: color_diff = "off" # Grijs/Neutraal als het klopt
        else: color_diff = "inverse" # Rood als het fout is
    
    st.metric(
        label="Verschil", 
        value=f"€ {verschil:.2f}", 
        delta="Klopt niet!" if verschil != 0 and som_links > 0 else "Ok",
        delta_color=color_diff
    )

with m3:
    st.metric(label="Totaal Lade", value=f"€ {som_rechts:.2f}")

# --- DE ACTIE KNOP ---
# De knop staat gecentreerd onder de totalen
st.write("") # Witruimte
c_btn_pad, c_btn_main, c_btn_pad2 = st.columns([1, 2, 1])

with c_btn_main:
    if is_valid:
        # GROENE KNOP
        st.success("✅ De kassa klopt! Je kunt opslaan.")
        if st.button("💾 Opslaan & Dag Sluiten", type="primary", use_container_width=True):
            
            # --- SAVE DATA ---
            # Hier haal je de data op:
            # - edited_links (voor BTW uitsplitsing)
            # - edited_rechts (voor geld uitsplitsing)
            
            with st.spinner("Opslaan naar administratie..."):
                time.sleep(1) # Fake save
                
            st.toast("Succesvol opgeslagen!", icon="🎉")
            time.sleep(1)
            reset_app()
            st.rerun()
            
    elif som_links == 0:
        # GRIJZE KNOP (Nog niks ingevuld)
        st.info("Vul eerst de omzet in aan de linkerkant.")
        st.button("Wacht op invoer...", disabled=True, use_container_width=True)
        
    else:
        # RODE KNOP (Fout)
        st.error(f"⚠️ Er is een kasverschil van € {verschil:.2f}")
        st.button("⛔ Corrigeer het verschil", disabled=True, use_container_width=True)
