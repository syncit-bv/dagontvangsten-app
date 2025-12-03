import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATIE ---
st.set_page_config(page_title="Kassa Unified", page_icon="⚡", layout="centered")

# CSS: Iets meer ruimte tussen de rijen voor leesbaarheid
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE ---
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

def reset_app():
    st.session_state.reset_counter += 1
    st.session_state.omschrijving = ""

# --- HEADER ---
st.subheader("📅 Dagontvangst")
c1, c2 = st.columns([1, 2])
with c1:
    datum = st.date_input("Datum", datetime.now(), label_visibility="collapsed")
with c2:
    omschrijving = st.text_input("Omschrijving", placeholder="Notitie...", label_visibility="collapsed", key="omschrijving")

st.divider()

# --- DE GECOMBINEERDE DATA ---
# We maken één lijst. Dit zorgt dat 'Enter' gewoon doorloopt naar beneden.
# We voegen een verborgen kolom 'Type' toe om straks te weten wat Omzet is en wat Geld is.

if 'df_unified' not in st.session_state:
    data = [
        # OMZET DEEL
        {"Type": "Omzet", "Omschrijving": "TICKET: 0% (BTW Vrijgesteld)", "Bedrag": 0.00},
        {"Type": "Omzet", "Omschrijving": "TICKET: 6% (BTW 6%)",     "Bedrag": 0.00},
        {"Type": "Omzet", "Omschrijving": "TICKET: 12% (BTW 12%)",     "Bedrag": 0.00},
        {"Type": "Omzet", "Omschrijving": "TICKET: 21% (BTW 21%)",   "Bedrag": 0.00},
        # BETAAL DEEL
        {"Type": "Geld",  "Omschrijving": "LADE: Bancontact",         "Bedrag": 0.00},
        {"Type": "Geld",  "Omschrijving": "LADE: Cash",               "Bedrag": 0.00},
        {"Type": "Geld",  "Omschrijving": "LADE: Payconiq",           "Bedrag": 0.00},
    ]
    # We slaan dit op in een DataFrame
    # Let op: We genereren het elke keer opnieuw in de editor op basis van de startwaarden
    # om de reset makkelijk te maken, maar hier definiëren we de structuur.
    pass 

# --- DE INPUT GRID (UNIFIED) ---
# We bouwen het dataframe hier 'live' op zodat de reset werkt via de key
df_start = pd.DataFrame([
    {"Type": "Omzet", "Groep": "1. OMZET (Ticket)", "Categorie": "0% (Vrijgesteld)", "Bedrag": 0.00},
    {"Type": "Omzet", "Groep": "1. OMZET (Ticket)", "Categorie": "6% (Voeding)",     "Bedrag": 0.00},
    {"Type": "Omzet", "Groep": "1. OMZET (Ticket)", "Categorie": "12% (Horeca)",     "Bedrag": 0.00},
    {"Type": "Omzet", "Groep": "1. OMZET (Ticket)", "Categorie": "21% (Algemeen)",   "Bedrag": 0.00},
    {"Type": "Geld",  "Groep": "2. BETALING (Lade)", "Categorie": "Bancontact",       "Bedrag": 0.00},
    {"Type": "Geld",  "Groep": "2. BETALING (Lade)", "Categorie": "Cash",             "Bedrag": 0.00},
    {"Type": "Geld",  "Groep": "2. BETALING (Lade)", "Categorie": "Payconiq",         "Bedrag": 0.00},
])

st.info("👇 Eén lijst voor snelheid: Gebruik **ENTER** om direct naar het volgende vakje te springen.")

edited_df = st.data_editor(
    df_start,
    column_config={
        "Type": None, # Verberg deze technische kolom
        "Groep": st.column_config.TextColumn("Sectie", disabled=True), # Alleen lezen
        "Categorie": st.column_config.TextColumn("Omschrijving", disabled=True),
        "Bedrag": st.column_config.NumberColumn("Bedrag (€)", min_value=0, format="%.2f", required=True)
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    height=280, # Hoogte vastzetten zodat er geen scrollbalk komt
    key=f"editor_unified_{st.session_state.reset_counter}"
)

# --- BEREKENINGEN ---
# We splitsen de dataframe weer op basis van de verborgen 'Type' kolom
som_omzet = edited_df[edited_df["Type"] == "Omzet"]["Bedrag"].sum()
som_geld = edited_df[edited_df["Type"] == "Geld"]["Bedrag"].sum()

verschil = round(som_omzet - som_geld, 2)

# --- STATUS BALK ---
st.divider()

col_totaal, col_knop = st.columns([1, 1])

with col_totaal:
    st.caption("Live Balans")
    if verschil == 0 and som_omzet > 0:
        st.markdown(f"### ✅ :green[€ {som_omzet:.2f}]")
    elif verschil != 0:
        st.markdown(f"### ❌ :red[Verschil: € {verschil:.2f}]")
        st.caption(f"Ticket: € {som_omzet:.2f} | Lade: € {som_geld:.2f}")
    else:
        st.markdown("### € 0.00")

with col_knop:
    # Validatie
    is_valid = (som_omzet > 0) and (verschil == 0)
    
    label = "✅ Opslaan & Sluiten" if is_valid else "⛔ Saldo moet 0 zijn"
    type_btn = "primary" if is_valid else "secondary"
    
    if st.button(label, type=type_btn, disabled=not is_valid, use_container_width=True):
        
        # --- EXPORT VOORBEREIDING ---
        # Nu moeten we de waarden er weer uitvissen voor de database
        # We zetten de Categorie als index om makkelijk te zoeken
        final_data = edited_df.set_index("Categorie")["Bedrag"]
        
        # Voorbeeld hoe je data nu uitleest:
        # omzet_21 = final_data["21% (Algemeen)"]
        # cash = final_data["Cash"]
        
        with st.spinner("Opslaan..."):
            time.sleep(0.8)
            # save_to_google_sheets(...)
            
        st.toast("Succesvol opgeslagen!", icon="🎉")
        time.sleep(1)
        reset_app()
        st.rerun()
