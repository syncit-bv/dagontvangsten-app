import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- SETUP ---
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

def clear_form():
    # We resetten de datum niet, dat is irritant voor de gebruiker.
    # We resetten alleen de cijfers.
    st.session_state.bedrag_incl_input = None 
    st.session_state.bc = None
    st.session_state.cash = None
    st.session_state.payq = None
    st.session_state.omschrijving = ""

# --- PAGINA CONFIG ---
st.set_page_config(page_title="Kassa Demo", page_icon="⚡", layout="centered")

st.title("⚡ Snelle Invoer")
st.caption("Gebruik TAB om te navigeren. Druk op ENTER om op te slaan.")

# --- INPUT FORMULIER ---
# Door 'clear_on_submit=False' te gebruiken houden we controle over wat we wissen
with st.form(key='dagontvangsten_form', clear_on_submit=False):
    
    # 1. BOVENSTUK
    c1, c2 = st.columns([1, 2])
    with c1:
        datum = st.date_input("Datum", key="datum")
    with c2:
        categorie = st.selectbox(
            "Categorie", 
            ["Verkoop 21%", "Verkoop 6%", "Verkoop 12%", "Diensten", "Anders"],
            key="categorie"
        )
    
    omschrijving = st.text_input("Omschrijving", key="omschrijving")
    
    st.markdown("---")
    
    # 2. DE CIJFERS (Links vs Rechts)
    col_links, col_rechts = st.columns(2)

    with col_links:
        st.subheader("Ticket (Omzet)")
        # value=None zorgt dat het vakje leeg is. Geen 0.00 om weg te halen!
        bedrag_incl_input = st.number_input(
            "Totaal Incl. BTW", 
            min_value=0.0, 
            step=0.01, 
            format="%.2f", 
            value=None,  # HIER ZIT DE TRUC VOOR SNELHEID
            key="bedrag_incl_input",
            placeholder="0.00" 
        )
        
        # BTW visueel maken (Berekening gebeurt pas na submit of bij rerun)
        def_btw = 3 
        if "6%" in categorie: def_btw = 1
        elif "12%" in categorie: def_btw = 2
        btw_pct = st.selectbox("BTW %", [0, 6, 12, 21], index=def_btw)

    with col_rechts:
        st.subheader("Betalingen (Geld)")
        # Ook hier starten we leeg
        bc = st.number_input("Bancontact", min_value=0.0, step=0.01, format="%.2f", value=None, key="bc", placeholder="0.00")
        cash = st.number_input("Cash", min_value=0.0, step=0.01, format="%.2f", value=None, key="cash", placeholder="0.00")
        payq = st.number_input("Payconiq", min_value=0.0, step=0.01, format="%.2f", value=None, key="payq", placeholder="0.00")

    st.markdown("---")
    
    # De Submit knop binnen het formulier
    # In veel browsers triggert 'Enter' in het laatste veld deze knop
    submit_knop = st.form_submit_button("Verwerk Invoer", type="primary", use_container_width=True)

# --- VERWERKING (BUITEN HET FORMULIER) ---
if submit_knop:
    # 1. Zet 'None' om naar 0.0 voor de berekening
    val_omzet = bedrag_incl_input if bedrag_incl_input is not None else 0.0
    val_bc = bc if bc is not None else 0.0
    val_cash = cash if cash is not None else 0.0
    val_payq = payq if payq is not None else 0.0
    
    val_totaal_ontvangen = val_bc + val_cash + val_payq
    verschil = round(val_omzet - val_totaal_ontvangen, 2)

    # 2. Validatie
    if val_omzet > 0:
        if verschil == 0:
            st.success("✅ OPGESLAGEN! Saldo klopt.")
            # Hier zou je save_to_google_sheets() aanroepen
            
            time.sleep(1) # Korte pauze voor feedback
            clear_form() # Maak velden leeg
            st.rerun()   # Ververs pagina voor nieuwe invoer
        else:
            st.error(f"⚠️ FOUT: Verschil van € {verschil:.2f}")
            st.warning(f"Omzet: € {val_omzet} | Geteld: € {val_totaal_ontvangen}")
    else:
        st.warning("Vul minstens een omzetbedrag in.")
