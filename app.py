import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATIE ---
st.set_page_config(page_title="Kassa Flow", page_icon="⚡", layout="centered")

# CSS: Zorgt dat de tabel clean oogt zonder index-nummers
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    [data-testid="stDataFrameResizable"] { border: 1px solid #ddd; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE ---
if 'reset_count' not in st.session_state:
    st.session_state.reset_count = 0

def reset_app():
    st.session_state.reset_count += 1
    st.session_state.omschrijving = ""

# --- HEADER ---
c1, c2 = st.columns([1, 2])
with c1:
    datum = st.date_input("Datum", datetime.now(), label_visibility="collapsed")
with c2:
    omschrijving = st.text_input("Omschrijving", placeholder="Korte notitie...", label_visibility="collapsed", key="omschrijving")

st.divider()

# --- DE DATA STRUCTUUR ---
# We gebruiken één lijst voor de flow. 
# TRUC: We voegen een 'Separator' rij toe die puur visueel is.

if 'df_flow' not in st.session_state:
    # Dit is alleen definitie, de echte startwaarden staan hieronder
    pass

# We bouwen de dataframe telkens opnieuw op voor de reset
# De kolom 'Is_Separator' gebruiken we om regels te blokkeren of te kleuren (indien mogelijk)
# of puur voor onze eigen logica.
data_items = [
    # DEEL 1: OMZET
    {"Label": "🎫 0% (Vrijgesteld)", "Bedrag": 0.00, "Type": "Omzet"},
    {"Label": "🎫 6% (Voeding)",     "Bedrag": 0.00, "Type": "Omzet"},
    {"Label": "🎫 12% (Horeca)",     "Bedrag": 0.00, "Type": "Omzet"},
    {"Label": "🎫 21% (Algemeen)",   "Bedrag": 0.00, "Type": "Omzet"},
    
    # DE VISUELE PAUZE (Enter drukken om door te gaan)
    {"Label": "⬇️ --- LADE INHOUD --- ⬇️", "Bedrag": None, "Type": "Separator"},
    
    # DEEL 2: GELD
    {"Label": "💶 Bancontact",       "Bedrag": 0.00, "Type": "Geld"},
    {"Label": "💶 Cash",             "Bedrag": 0.00, "Type": "Geld"},
    {"Label": "💶 Payconiq",         "Bedrag": 0.00, "Type": "Geld"},
]

df_start = pd.DataFrame(data_items)

# --- DE SNELE EDITOR ---
st.info("⚡ **Snelheid:** Typ bedrag ➔ ENTER ➔ Volgende.")

edited_df = st.data_editor(
    df_start,
    column_config={
        "Label": st.column_config.TextColumn("Omschrijving", disabled=True),
        "Bedrag": st.column_config.NumberColumn(
            "Waarde (€)", 
            min_value=0, 
            format="%.2f"
        ),
        "Type": None # Verberg deze technische kolom
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    height=320, # Precies hoog genoeg voor alle regels
    key=f"editor_flow_{st.session_state.reset_count}"
)

# --- BEREKENINGEN ---
# We filteren de separator eruit voor de sommen
regels = edited_df[edited_df["Type"] != "Separator"].copy()
regels["Bedrag"] = regels["Bedrag"].fillna(0.0) # Zorg dat lege velden 0 zijn

som_omzet = regels[regels["Type"] == "Omzet"]["Bedrag"].sum()
som_geld = regels[regels["Type"] == "Geld"]["Bedrag"].sum()

verschil = round(som_omzet - som_geld, 2)

# --- STATUS & KNOP ---
st.divider()

c_info, c_knop = st.columns([1, 1])

with c_info:
    if som_omzet == 0:
        st.caption("Nog geen invoer.")
    elif verschil == 0:
        st.markdown(f"### ✅ :green[OK: € {som_omzet:.2f}]")
    else:
        st.markdown(f"### ❌ :red[Verschil: € {verschil:.2f}]")
        st.caption(f"Ticket: {som_omzet} | Lade: {som_geld}")

with c_knop:
    is_valid = (som_omzet > 0) and (verschil == 0)
    
    if st.button(
        "💾 Opslaan & Volgende", 
        type="primary" if is_valid else "secondary", 
        disabled=not is_valid, 
        use_container_width=True
    ):
        with st.spinner("Opslaan..."):
            time.sleep(0.5)
            # Hier save code...
        
        st.toast("Opgeslagen!", icon="✅")
        time.sleep(1)
        reset_app()
        st.rerun()
