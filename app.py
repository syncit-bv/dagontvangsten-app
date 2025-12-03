import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os

# --- CONFIGURATIE ---
DATA_FILE = "kassa_historiek.csv"
st.set_page_config(page_title="Kassa Op Maat", page_icon="💾", layout="centered")

# CSS: Styling
st.markdown("""
    <style>
    .block-container { padding-top: 4rem; padding-bottom: 2rem; }
    [data-testid="stDataFrameResizable"] { border: 1px solid #ddd; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTIES VOOR OPSLAG ---

def load_database():
    """Laad het bestaande bestand of maak een nieuw aan."""
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        # Definieer de kolommen die we altijd willen hebben
        cols = [
            "Datum", "Omschrijving", "Totaal_Omzet", "Totaal_Geld", "Verschil",
            "Omzet_0", "Omzet_6", "Omzet_12", "Omzet_21",
            "Geld_Bancontact", "Geld_Cash", "Geld_Payconiq", "Geld_Bonnen",
            "Timestamp"
        ]
        return pd.DataFrame(columns=cols)

def save_transaction(datum, omschrijving, df_input, totaal_omzet, totaal_geld, verschil):
    """Vertaalt de visuele lijst naar een database regel."""
    
    # 1. We laden de oude data
    df_db = load_database()
    
    # 2. We maken een nieuwe lege regel
    new_row = {
        "Datum": datum,
        "Omschrijving": omschrijving,
        "Totaal_Omzet": totaal_omzet,
        "Totaal_Geld": totaal_geld,
        "Verschil": verschil,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # Zet standaardwaarden op 0.00
        "Omzet_0": 0.0, "Omzet_6": 0.0, "Omzet_12": 0.0, "Omzet_21": 0.0,
        "Geld_Bancontact": 0.0, "Geld_Cash": 0.0, "Geld_Payconiq": 0.0, "Geld_Bonnen": 0.0
    }
    
    # 3. We lopen door de invoerlijst en vullen de juiste vakjes
    # We gebruiken 'in' om te zoeken, zodat emoji's geen probleem zijn
    for index, row in df_input.iterrows():
        label = row['Label']
        bedrag = row['Bedrag']
        
        if bedrag > 0: # Alleen opslaan wat niet 0 is
            if "0%" in label:  new_row["Omzet_0"] = bedrag
            elif "6%" in label:  new_row["Omzet_6"] = bedrag
            elif "12%" in label: new_row["Omzet_12"] = bedrag
            elif "21%" in label: new_row["Omzet_21"] = bedrag
            elif "Bancontact" in label: new_row["Geld_Bancontact"] = bedrag
            elif "Cash" in label: new_row["Geld_Cash"] = bedrag
            elif "Payconiq" in label: new_row["Geld_Payconiq"] = bedrag
            elif "Bonnen" in label: new_row["Geld_Bonnen"] = bedrag

    # 4. Toevoegen en opslaan (gebruik pd.concat i.p.v. append)
    new_entry_df = pd.DataFrame([new_row])
    df_db = pd.concat([df_db, new_entry_df], ignore_index=True)
    df_db.to_csv(DATA_FILE, index=False)

# --- STATE MANAGEMENT ---
if 'reset_count' not in st.session_state:
    st.session_state.reset_count = 0

def reset_app():
    st.session_state.reset_count += 1
    st.session_state.omschrijving = ""

# ==========================================
# ⚙️ SIDEBAR
# ==========================================
with st.sidebar:
    st.header("⚙️ Instellingen")
    
    st.subheader("BTW")
    use_0  = st.checkbox("0% (Vrijgesteld)", value=True)
    use_6  = st.checkbox("6% (Voeding)", value=True)
    use_12 = st.checkbox("12% (Horeca)", value=False)
    use_21 = st.checkbox("21% (Algemeen)", value=True)
    
    st.divider()
    
    st.subheader("Betaling")
    use_bc   = st.checkbox("Bancontact", value=True)
    use_cash = st.checkbox("Cash", value=True)
    use_payq = st.checkbox("Payconiq", value=True)
    use_vouc = st.checkbox("Cadeaubonnen", value=False)
    
    st.divider()
    
    # DOWNLOAD KNOP VOOR DE ADMINISTRATIE
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "rb") as f:
            st.download_button(
                label="📥 Download Excel/CSV",
                data=f,
                file_name="dagontvangsten.csv",
                mime="text/csv"
            )

# ==========================================
# 📅 HOOFDSCHERM
# ==========================================

st.header("📅 Dagontvangst") 

c1, c2 = st.columns([1, 2])
with c1:
    datum = st.date_input("Datum", datetime.now(), label_visibility="collapsed")
with c2:
    omschrijving = st.text_input("Omschrijving", placeholder="Korte notitie...", label_visibility="collapsed", key="omschrijving")

st.divider()

# --- DATAFRAME BOUWEN ---
data_items = []

if use_0:  data_items.append({"Label": "🎫 0% (Vrijgesteld)", "Bedrag": 0.00, "Type": "Omzet"})
if use_6:  data_items.append({"Label": "🎫 6% (Voeding)",     "Bedrag": 0.00, "Type": "Omzet"})
if use_12: data_items.append({"Label": "🎫 12% (Horeca)",     "Bedrag": 0.00, "Type": "Omzet"})
if use_21: data_items.append({"Label": "🎫 21% (Algemeen)",   "Bedrag": 0.00, "Type": "Omzet"})

data_items.append({"Label": "⬇️ --- LADE INHOUD --- ⬇️", "Bedrag": None, "Type": "Separator"})

if use_bc:   data_items.append({"Label": "💳 Bancontact",   "Bedrag": 0.00, "Type": "Geld"})
if use_cash: data_items.append({"Label": "💶 Cash",         "Bedrag": 0.00, "Type": "Geld"})
if use_payq: data_items.append({"Label": "📱 Payconiq",     "Bedrag": 0.00, "Type": "Geld"})
if use_vouc: data_items.append({"Label": "🎁 Bonnen",       "Bedrag": 0.00, "Type": "Geld"})

df_start = pd.DataFrame(data_items)

# --- EDITOR ---
st.caption("Typ het bedrag en druk op **ENTER**.")

edited_df = st.data_editor(
    df_start,
    column_config={
        "Label": st.column_config.TextColumn("Omschrijving", disabled=True),
        "Bedrag": st.column_config.NumberColumn("Waarde (€)", min_value=0, format="%.2f"),
        "Type": None
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    height=(len(data_items) * 35) + 38,
    key=f"editor_dynamic_{st.session_state.reset_count}"
)

# --- BEREKENINGEN ---
regels = edited_df[edited_df["Type"] != "Separator"].copy()
regels["Bedrag"] = regels["Bedrag"].fillna(0.0)

som_omzet = regels[regels["Type"] == "Omzet"]["Bedrag"].sum()
som_geld = regels[regels["Type"] == "Geld"]["Bedrag"].sum()
verschil = round(som_omzet - som_geld, 2)

# --- STATUS & OPSLAAN ---
st.divider()
c_info, c_knop = st.columns([1, 1])

with c_info:
    if som_omzet == 0:
        st.info("👆 Vul de gegevens in.")
    elif verschil == 0:
        st.markdown(f"### ✅ :green[OK: € {som_omzet:.2f}]")
    else:
        st.markdown(f"### ❌ :red[Verschil: € {verschil:.2f}]")

with c_knop:
    is_valid = (som_omzet > 0) and (verschil == 0)
    
    if st.button("💾 Opslaan & Volgende", type="primary", disabled=not is_valid, use_container_width=True):
        
        # 1. VISUELE FEEDBACK
        with st.spinner("Gegevens worden opgeslagen..."):
            
            # 2. DATA OPSLAAN
            save_transaction(
                datum=datum,
                omschrijving=omschrijving,
                df_input=edited_df,       # We sturen de ingevulde tabel mee
                totaal_omzet=som_omzet,
                totaal_geld=som_geld,
                verschil=verschil
            )
            time.sleep(0.5) # Korte pauze voor het gevoel
        
        # 3. SUCCES MELDING
        st.toast("Succesvol opgeslagen in bestand!", icon="✅")
        time.sleep(1)
        
        # 4. RESET
        reset_app()
        st.rerun()

# --- HISTORIEK TONEN (OPTIONEEL ONDERAAN) ---
if os.path.exists(DATA_FILE):
    with st.expander("🔍 Bekijk laatst ingevoerde gegevens"):
        df_hist = pd.read_csv(DATA_FILE)
        # Toon nieuwste bovenaan
        st.dataframe(df_hist.sort_values(by="Timestamp", ascending=False).head(5))
