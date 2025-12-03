import streamlit as st
import time
from datetime import datetime

# --- SETUP & STATE ---
# We initialiseren de waarden in de sessie zodat we ze kunnen wissen na opslaan
keys = ['omzet_0', 'omzet_6', 'omzet_12', 'omzet_21', 'bc', 'cash', 'payq', 'omschrijving']
for key in keys:
    if key not in st.session_state:
        st.session_state[key] = None # Start leeg

if 'last_save' not in st.session_state:
    st.session_state.last_save = ""

def clear_inputs():
    """Maak alle velden weer leeg voor de volgende dag"""
    for key in keys:
        st.session_state[key] = None
    st.session_state.omschrijving = ""

# --- PAGINA CONFIG ---
st.set_page_config(page_title="Kassa Live", page_icon="⚡", layout="centered")

st.title("⚡ Dagontvangsten")
# Toon een bevestiging als er net is opgeslagen
if st.session_state.last_save:
    st.success(st.session_state.last_save)
    st.session_state.last_save = "" # Reset melding

# --- DATUM & INFO ---
c1, c2 = st.columns([1, 2])
with c1:
    datum = st.date_input("Datum", datetime.now())
with c2:
    # We gebruiken de session_state direct in de value voor reset-mogelijkheid
    omschrijving = st.text_input("Omschrijving", key="omschrijving")

st.markdown("---")

# --- DE LIVE INPUTS ---
col_links, col_rechts = st.columns(2)

with col_links:
    st.subheader("1. Omzet (Ticket)")
    st.caption("Vul in van laag naar hoog:")
    
    # VOLGORDE AANGEPAST: 0 -> 6 -> 12 -> 21
    omzet_0  = st.number_input("Totaal 0% (Vrijgesteld)", min_value=0.0, step=0.01, format="%.2f", key="omzet_0", placeholder="0.00")
    omzet_6  = st.number_input("Totaal 6%",  min_value=0.0, step=0.01, format="%.2f", key="omzet_6",  placeholder="0.00")
    omzet_12 = st.number_input("Totaal 12%", min_value=0.0, step=0.01, format="%.2f", key="omzet_12", placeholder="0.00")
    omzet_21 = st.number_input("Totaal 21%", min_value=0.0, step=0.01, format="%.2f", key="omzet_21", placeholder="0.00")

with col_rechts:
    st.subheader("2. Betalingen (Lade)")
    st.caption("Hoe is er betaald?")
    
    bc = st.number_input("Bancontact", min_value=0.0, step=0.01, format="%.2f", key="bc", placeholder="0.00")
    cash = st.number_input("Cash", min_value=0.0, step=0.01, format="%.2f", key="cash", placeholder="0.00")
    payq = st.number_input("Payconiq", min_value=0.0, step=0.01, format="%.2f", key="payq", placeholder="0.00")

# --- LIVE BEREKENING ---
# Zet None om naar 0.0 voor de wiskunde
v_0  = omzet_0  if omzet_0  else 0.0
v_6  = omzet_6  if omzet_6  else 0.0
v_12 = omzet_12 if omzet_12 else 0.0
v_21 = omzet_21 if omzet_21 else 0.0

v_bc = bc if bc else 0.0
v_cash = cash if cash else 0.0
v_payq = payq if payq else 0.0

totaal_omzet = v_0 + v_6 + v_12 + v_21
totaal_betaald = v_bc + v_cash + v_payq
verschil = round(totaal_omzet - totaal_betaald, 2)

st.markdown("---")

# --- DE STATUS BALK & KNOP LOGICA ---

# Container voor de totalen
c_tot1, c_tot2, c_status = st.columns([1, 1, 2])
with c_tot1:
    st.metric("Totaal Ticket", f"€ {totaal_omzet:.2f}")
with c_tot2:
    st.metric("Totaal Geld", f"€ {totaal_betaald:.2f}")

with c_status:
    # LOGICA: Knop is alleen actief als er iets is ingevuld EN verschil is 0
    is_valid = (totaal_omzet > 0) and (verschil == 0)
    
    if is_valid:
        # GROEN SCENARIO
        st.success("✅ Saldo klopt perfect!")
        # Knop is actief (type='primary' maakt hem opvallend)
        knop_klik = st.button("💾 Opslaan & Volgende", type="primary", use_container_width=True)
    else:
        # ROOD / GRIJS SCENARIO
        if totaal_omzet == 0:
            st.info("💡 Vul gegevens in...")
        else:
            st.error(f"❌ Verschil: € {verschil:.2f}")
        
        # Knop is disabled (grijs)
        st.button("⛔ Saldo niet nul", disabled=True, use_container_width=True)

# --- OPSLAAN ACTIE ---
if is_valid and knop_klik:
    # Hier komt de code om naar Google Sheets te schrijven
    # save_to_gsheets(...)
    
    # Feedback voor de gebruiker
    st.session_state.last_save = "🎉 Opgeslagen! Klaar voor de volgende dag."
    
    # Velden wissen en herladen
    clear_inputs()
    st.rerun()
