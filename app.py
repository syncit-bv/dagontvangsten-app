import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATIE ---
st.set_page_config(page_title="Kassa Op Maat", page_icon="⚙️", layout="centered")

# CSS: Schone look
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    [data-testid="stDataFrameResizable"] { border: 1px solid #ddd; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'reset_count' not in st.session_state:
    st.session_state.reset_count = 0

def reset_app():
    st.session_state.reset_count += 1
    st.session_state.omschrijving = ""

# ==========================================
# ⚙️ DE INSTELLINGEN (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Instellingen")
    st.info("Vink aan wat van toepassing is voor jouw zaak.")
    
    st.subheader("Welke BTW tarieven?")
    use_0  = st.checkbox("0% (Vrijgesteld)", value=True)
    use_6  = st.checkbox("6% (Voeding/Kranten)", value=True)
    use_12 = st.checkbox("12% (Horeca)", value=False) # Standaard uit
    use_21 = st.checkbox("21% (Algemeen)", value=True)
    
    st.divider()
    
    st.subheader("Welke Betaalopties?")
    use_bc   = st.checkbox("Bancontact", value=True)
    use_cash = st.checkbox("Cash", value=True)
    use_payq = st.checkbox("Payconiq", value=True)
    use_vouc = st.checkbox("Cadeaubonnen", value=False) # Extra optie

# ==========================================
# 📅 DE APPLICATIE (HOOFDSCHERM)
# ==========================================

st.subheader("📅 Dagontvangst")

c1, c2 = st.columns([1, 2])
with c1:
    datum = st.date_input("Datum", datetime.now(), label_visibility="collapsed")
with c2:
    omschrijving = st.text_input("Omschrijving", placeholder="Notitie...", label_visibility="collapsed", key="omschrijving")

st.divider()

# --- DATAFRAME BOUWEN OP BASIS VAN INSTELLINGEN ---
data_items = []

# 1. OMZET REGELS (Dynamisch toegevoegd)
if use_0:  data_items.append({"Label": "🎫 0% (Vrijgesteld)", "Bedrag": 0.00, "Type": "Omzet"})
if use_6:  data_items.append({"Label": "🎫 6% (Voeding)",     "Bedrag": 0.00, "Type": "Omzet"})
if use_12: data_items.append({"Label": "🎫 12% (Horeca)",     "Bedrag": 0.00, "Type": "Omzet"})
if use_21: data_items.append({"Label": "🎫 21% (Algemeen)",   "Bedrag": 0.00, "Type": "Omzet"})

# 2. DE SCHEIDINGSLIJN
data_items.append({"Label": "⬇️ --- LADE INHOUD --- ⬇️", "Bedrag": None, "Type": "Separator"})

# 3. GELD REGELS (Dynamisch toegevoegd)
if use_bc:   data_items.append({"Label": "💳 Bancontact",   "Bedrag": 0.00, "Type": "Geld"})
if use_cash: data_items.append({"Label": "💶 Cash",         "Bedrag": 0.00, "Type": "Geld"})
if use_payq: data_items.append({"Label": "📱 Payconiq",     "Bedrag": 0.00, "Type": "Geld"})
if use_vouc: data_items.append({"Label": "🎁 Bonnen",       "Bedrag": 0.00, "Type": "Geld"})

# Maak dataframe
df_start = pd.DataFrame(data_items)

# --- DE INPUT TABEL ---
st.caption("Gebruik **ENTER** om door de actieve velden te springen.")

edited_df = st.data_editor(
    df_start,
    column_config={
        "Label": st.column_config.TextColumn("Omschrijving", disabled=True),
        "Bedrag": st.column_config.NumberColumn(
            "Waarde (€)", 
            min_value=0, 
            format="%.2f"
        ),
        "Type": None # Verberg technisch veld
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    height=(len(data_items) * 35) + 38, # Hoogte past zich automatisch aan!
    key=f"editor_dynamic_{st.session_state.reset_count}"
)

# --- BEREKENINGEN ---
regels = edited_df[edited_df["Type"] != "Separator"].copy()
regels["Bedrag"] = regels["Bedrag"].fillna(0.0)

som_omzet = regels[regels["Type"] == "Omzet"]["Bedrag"].sum()
som_geld = regels[regels["Type"] == "Geld"]["Bedrag"].sum()

verschil = round(som_omzet - som_geld, 2)

# --- STATUS & KNOP ---
st.divider()

c_info, c_knop = st.columns([1, 1])

with c_info:
    if som_omzet == 0:
        st.info("👆 Begin met invullen...")
    elif verschil == 0:
        st.markdown(f"### ✅ :green[OK: € {som_omzet:.2f}]")
    else:
        st.markdown(f"### ❌ :red[Verschil: € {verschil:.2f}]")
        st.caption(f"Ticket: € {som_omzet:.2f} | Lade: € {som_geld:.2f}")

with c_knop:
    is_valid = (som_omzet > 0) and (verschil == 0)
    
    if st.button(
        "💾 Opslaan & Volgende", 
        type="primary" if is_valid else "secondary", 
        disabled=not is_valid, 
        use_container_width=True
    ):
        # SIMULATIE OPSLAAN
        with st.spinner("Bezig met opslaan..."):
            time.sleep(0.5)
            # Hier zou je de actieve velden uitlezen en opslaan
        
        st.toast("Opgeslagen!", icon="✅")
        time.sleep(1)
        reset_app()
        st.rerun()
