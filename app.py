import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- SETUP ---
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

def clear_form():
    # We maken alle invoervelden leeg (None)
    keys_to_clear = ['omzet_21', 'omzet_12', 'omzet_6', 'omzet_0', 'bc', 'cash', 'payq']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key] # Deletes the specific key from session state
    st.session_state.omschrijving = ""

# --- PAGINA CONFIG ---
st.set_page_config(page_title="Kassa Uitgebreid", page_icon="🧾", layout="centered")

st.title("🧾 Dagontvangsten")
st.caption("Neem de totalen over van het Z-ticket (Inclusief BTW)")

# --- INPUT FORMULIER ---
with st.form(key='dagontvangsten_form', clear_on_submit=False):
    
    # DATUM & OMSCHRIJVING
    c_date, c_desc = st.columns([1, 2])
    with c_date:
        datum = st.date_input("Datum", datetime.now())
    with c_desc:
        omschrijving = st.text_input("Omschrijving / Notitie", key="omschrijving")
    
    st.markdown("---")
    
    # DE KOLOMMEN: LINKS (OMZET) vs RECHTS (GELD)
    col_links, col_rechts = st.columns(2)

    with col_links:
        st.subheader("1. Omzet (Ticket)")
        st.caption("Vul in wat van toepassing is:")
        
        # We bieden de 4 gangbare tarieven aan. Wat leeg is, blijft leeg.
        omzet_21 = st.number_input("Totaal 21%", min_value=0.0, step=0.01, format="%.2f", value=None, key="omzet_21", placeholder="0.00")
        omzet_12 = st.number_input("Totaal 12%", min_value=0.0, step=0.01, format="%.2f", value=None, key="omzet_12", placeholder="0.00")
        omzet_6  = st.number_input("Totaal 6%",  min_value=0.0, step=0.01, format="%.2f", value=None, key="omzet_6",  placeholder="0.00")
        omzet_0  = st.number_input("Totaal 0% (Vrijgesteld)", min_value=0.0, step=0.01, format="%.2f", value=None, key="omzet_0",  placeholder="0.00")

    with col_rechts:
        st.subheader("2. Betalingen (Lade)")
        st.caption("Hoe is het totaalbedrag betaald?")
        
        bc = st.number_input("Bancontact", min_value=0.0, step=0.01, format="%.2f", value=None, key="bc", placeholder="0.00")
        cash = st.number_input("Cash", min_value=0.0, step=0.01, format="%.2f", value=None, key="cash", placeholder="0.00")
        payq = st.number_input("Payconiq", min_value=0.0, step=0.01, format="%.2f", value=None, key="payq", placeholder="0.00")
        
        # Ruimte opvullen zodat de totalen mooi uitlijnen
        st.write("") 

    st.markdown("---")
    
    # Submit knop
    submit_knop = st.form_submit_button("💾 Controleer & Opslaan", type="primary", use_container_width=True)

# --- BEREKENING & VALIDATIE (NA DE KLIK) ---
if submit_knop:
    # 1. Zet alles om naar getallen (None wordt 0.0)
    v_21 = omzet_21 if omzet_21 else 0.0
    v_12 = omzet_12 if omzet_12 else 0.0
    v_6  = omzet_6  if omzet_6  else 0.0
    v_0  = omzet_0  if omzet_0  else 0.0
    
    v_bc = bc if bc else 0.0
    v_cash = cash if cash else 0.0
    v_payq = payq if payq else 0.0

    # 2. Totalen
    totaal_omzet = v_21 + v_12 + v_6 + v_0
    totaal_betaald = v_bc + v_cash + v_payq
    verschil = round(totaal_omzet - totaal_betaald, 2)

    # 3. Visuele Feedback
    c_res1, c_res2 = st.columns(2)
    with c_res1:
        st.metric("Totaal Ticket", f"€ {totaal_omzet:.2f}")
    with c_res2:
        st.metric("Totaal Geld", f"€ {totaal_betaald:.2f}")

    # 4. Validatie Check
    if totaal_omzet > 0:
        if verschil == 0:
            st.success("✅ SALDO KLOPT! De gegevens zijn opgeslagen.")
            
            # --- HIER STRAKS DE OPSLAG CODE NAAR GOOGLE SHEETS ---
            # We slaan nu in één keer 4 kolommen op (Omzet_21, Omzet_12, etc.)
            
            time.sleep(1.5)
            # Reset
            for key in ['omzet_21', 'omzet_12', 'omzet_6', 'omzet_0', 'bc', 'cash', 'payq', 'omschrijving']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
        else:
            st.error(f"⚠️ VERSCHIL: € {verschil:.2f}")
            st.warning("Kijk na of je een typfout hebt gemaakt bij de betalingen of de omzet.")
    else:
        st.warning("Vul minstens één omzetbedrag in.")
