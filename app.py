import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- SETUP (Geen database nodig voor deze demo) ---
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

def clear_form():
    st.session_state.datum = datetime.now()
    st.session_state.bedrag_excl = 0.00
    st.session_state.bc = 0.00
    st.session_state.cash = 0.00
    st.session_state.payq = 0.00
    st.session_state.omschrijving = ""

# --- PAGINA ---
st.set_page_config(page_title="Kassa Demo", page_icon="💶", layout="centered")

st.title("💶 Dagontvangsten")
st.info("Dit is een live demo van de interface.")

# --- INVOER ---
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

col_links, col_rechts = st.columns(2)

with col_links:
    st.subheader("1. Omzet (Ticket)")
    bedrag_excl = st.number_input("Bedrag Excl. BTW", min_value=0.0, step=0.01, format="%.2f", key="bedrag_excl")
    
    # BTW logica
    def_btw = 3 # 21%
    if "6%" in categorie: def_btw = 1
    elif "12%" in categorie: def_btw = 2
    
    btw_pct = st.selectbox("BTW %", [0, 6, 12, 21], index=def_btw)
    bedrag_incl = bedrag_excl * (1 + (btw_pct/100))
    
    st.metric("Totaal Omzet", f"€ {bedrag_incl:.2f}")

with col_rechts:
    st.subheader("2. Ontvangen (Geld)")
    bc = st.number_input("Bancontact", min_value=0.0, step=0.01, format="%.2f", key="bc")
    cash = st.number_input("Cash", min_value=0.0, step=0.01, format="%.2f", key="cash")
    payq = st.number_input("Payconiq", min_value=0.0, step=0.01, format="%.2f", key="payq")
    
    totaal = bc + cash + payq
    st.metric("Totaal Ontvangen", f"€ {totaal:.2f}")

# --- VALIDATIE ---
st.markdown("---")
verschil = round(bedrag_incl - totaal, 2)

if bedrag_incl > 0:
    if verschil == 0:
        st.success("✅ SALDO KLOPT")
        if st.button("💾 Opslaan (Demo)", type="primary", use_container_width=True):
            st.toast("Opgeslagen! (In demo mode wordt niets bewaard)", icon='🎉')
            time.sleep(1)
            clear_form()
            st.rerun()
    else:
        st.error(f"⚠️ Verschil: € {verschil:.2f}")
        st.button("Corrigeer saldo", disabled=True, use_container_width=True)
