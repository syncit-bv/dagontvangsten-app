import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- SETUP ---
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

def clear_form():
    st.session_state.datum = datetime.now()
    st.session_state.bedrag_incl_input = 0.00 # Reset de input
    st.session_state.bc = 0.00
    st.session_state.cash = 0.00
    st.session_state.payq = 0.00
    st.session_state.omschrijving = ""

# --- PAGINA ---
st.set_page_config(page_title="Kassa Demo", page_icon="💶", layout="centered")

st.title("💶 Dagontvangsten")
st.caption("Demo versie: Input op basis van ticket inclusief BTW")

# --- INVOER BOVENAAN ---
col_date, col_cat = st.columns([1, 2])
with col_date:
    datum = st.date_input("Datum", key="datum")
with col_cat:
    categorie = st.selectbox(
        "Categorie", 
        ["Verkoop 21%", "Verkoop 6%", "Verkoop 12%", "Diensten", "Anders"],
        key="categorie"
    )

omschrijving = st.text_input("Omschrijving", key="omschrijving")

st.markdown("---")

# --- DE BALANS ---
col_links, col_rechts = st.columns(2)

with col_links:
    st.subheader("1. Omzet (Ticket)")
    st.caption("Vul het totaalbedrag van het Z-ticket in.")
    
    # AANPASSING: Input is nu INCLUSIEF BTW
    bedrag_incl_input = st.number_input(
        "Totaalbedrag (Incl. BTW)", 
        min_value=0.0, 
        step=0.01, 
        format="%.2f", 
        key="bedrag_incl_input"
    )
    
    # BTW Selectie & Terugrekenen
    def_btw = 3 # 21%
    if "6%" in categorie: def_btw = 1
    elif "12%" in categorie: def_btw = 2
    
    btw_pct = st.selectbox("BTW Tarief in ticket", [0, 6, 12, 21], index=def_btw)
    
    # De wiskunde: Bedrag / 1.21 = Excl
    if bedrag_incl_input > 0:
        factor = 1 + (btw_pct / 100)
        bedrag_excl_calc = bedrag_incl_input / factor
        bedrag_btw_calc = bedrag_incl_input - bedrag_excl_calc
        
        # Toon de berekening lichtgrijs ter info
        st.info(f"Excl: € {bedrag_excl_calc:.2f} | BTW: € {bedrag_btw_calc:.2f}")
    else:
        bedrag_excl_calc = 0
        bedrag_btw_calc = 0
    
    # Grote metric voor de vergelijking
    st.metric("Te verantwoorden", f"€ {bedrag_incl_input:.2f}")

with col_rechts:
    st.subheader("2. Ontvangen (Geld)")
    st.caption("Hoe is dit bedrag betaald?")
    
    bc = st.number_input("Bancontact", min_value=0.0, step=0.01, format="%.2f", key="bc")
    cash = st.number_input("Cash", min_value=0.0, step=0.01, format="%.2f", key="cash")
    payq = st.number_input("Payconiq", min_value=0.0, step=0.01, format="%.2f", key="payq")
    
    totaal_ontvangen = bc + cash + payq
    
    # Lege ruimte voor uitlijning
    if bedrag_incl_input > 0: st.write("") 
    
    st.metric("Totaal Geteld", f"€ {totaal_ontvangen:.2f}")

# --- VALIDATIE ---
st.markdown("---")
verschil = round(bedrag_incl_input - totaal_ontvangen, 2)

if bedrag_incl_input > 0:
    if verschil == 0:
        st.success("✅ SALDO KLOPT PERFECT")
        if st.button("💾 Opslaan (Demo)", type="primary", use_container_width=True):
            st.toast("Opgeslagen!", icon='🎉')
            time.sleep(1)
            clear_form()
            st.rerun()
    else:
        st.error(f"⚠️ VERSCHIL: € {verschil:.2f}")
        st.caption("Het totaal links (Ticket) moet gelijk zijn aan het totaal rechts (Betalingen).")
        st.button("Corrigeer saldo om op te slaan", disabled=True, use_container_width=True)
else:
    st.info("💡 Vul links een bedrag in om te starten.")
