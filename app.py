import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATIE ---
st.set_page_config(page_title="Snelle Kassa Invoer", page_icon="⚡", layout="centered")

# --- CSS HACK VOOR SCHONE LOOK ---
# Dit verwijdert onnodige witruimte bovenaan zodat de app direct begint
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
# We gebruiken een teller om de tabellen te 'resetten' na opslaan
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

def reset_app():
    st.session_state.reset_counter += 1
    st.session_state.omschrijving = ""

# --- DATUM & OMSCHRIJVING ---
st.subheader("📅 Dagontvangst Registreren")

c1, c2 = st.columns([1, 2])
with c1:
    datum = st.date_input("Datum", datetime.now(), label_visibility="collapsed")
with c2:
    omschrijving = st.text_input("Omschrijving", placeholder="Bijv. Dagtotaal winkel", label_visibility="collapsed", key="omschrijving")

st.divider()

# --- DE DATA GRID ---
col_links, col_rechts = st.columns(2)

# Unieke keys zorgen dat de tabellen leeg gemaakt kunnen worden
key_omzet = f"grid_omzet_{st.session_state.reset_counter}"
key_geld = f"grid_geld_{st.session_state.reset_counter}"

with col_links:
    st.markdown("**1. TICKET (Omzet)**")
    
    # Startdata: Van 0% naar 21%
    df_omzet_start = pd.DataFrame({
        "Tarief": ["0% (Vrijgesteld)", "6% (Voeding)", "12% (Horeca)", "21% (Algemeen)"],
        "Bedrag": [0.00, 0.00, 0.00, 0.00]
    })

    edited_omzet = st.data_editor(
        df_omzet_start,
        column_config={
            "Tarief": st.column_config.TextColumn("Categorie", disabled=True),
            "Bedrag": st.column_config.NumberColumn("Bedrag (€)", min_value=0, format="%.2f", required=True)
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed", # Geen regels toevoegen
        key=key_omzet
    )

with col_rechts:
    st.markdown("**2. LADE (Geld)**")
    
    df_geld_start = pd.DataFrame({
        "Methode": ["Bancontact", "Cash", "Payconiq"],
        "Ontvangen": [0.00, 0.00, 0.00]
    })

    edited_geld = st.data_editor(
        df_geld_start,
        column_config={
            "Methode": st.column_config.TextColumn("Betaalwijze", disabled=True),
            "Ontvangen": st.column_config.NumberColumn("Bedrag (€)", min_value=0, format="%.2f", required=True)
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key=key_geld
    )

# --- LIVE BEREKENING ---
totaal_omzet = edited_omzet["Bedrag"].sum()
totaal_geld = edited_geld["Ontvangen"].sum()
verschil = round(totaal_omzet - totaal_geld, 2)

# --- VALIDATIE BALK ---
st.divider()

# Container voor de status
status_container = st.container()

with status_container:
    c_res1, c_res2, c_actie = st.columns([1, 1, 2])
    
    with c_res1:
        st.metric("Totaal Ticket", f"€ {totaal_omzet:.2f}")
    with c_res2:
        st.metric("Totaal Geld", f"€ {totaal_geld:.2f}")
    
    with c_actie:
        # Validatie Logica
        if totaal_omzet == 0 and totaal_geld == 0:
             st.info("👆 Vul de gegevens hierboven in.")
             knop_text = "Nog geen gegevens"
             knop_type = "secondary"
             is_active = False
             
        elif verschil == 0:
            st.success("✅ Saldo klopt perfect!")
            knop_text = "💾 Opslaan & Dag Sluiten"
            knop_type = "primary" # Maakt de knop rood/opvallend in Streamlit thema
            is_active = True
            
        else:
            st.error(f"⚠️ Verschil: € {verschil:.2f}")
            knop_text = "⛔ Corrigeer saldo"
            knop_type = "secondary"
            is_active = False

        # De Knop
        if st.button(knop_text, type=knop_type, disabled=not is_active, use_container_width=True):
            
            # --- HIER KOMT DE SAVE LOGICA ---
            # Nu simuleren we het even:
            with st.spinner("Bezig met opslaan naar Database..."):
                time.sleep(1) # Fake save tijd
                
                # Hier halen we de data uit de grid voor de export later
                # export_data = {
                #    "datum": datum,
                #    "omzet_21": edited_omzet.iloc[3]['Bedrag'],
                #    "cash": edited_geld.iloc[1]['Ontvangen'],
                #    ...
                # }
                
            st.toast("Succesvol opgeslagen!", icon="🎉")
            time.sleep(1)
            reset_app()
            st.rerun()
