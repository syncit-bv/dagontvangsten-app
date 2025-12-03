import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os

# --- CONFIGURATIE ---
DATA_FILE = "kassa_historiek.csv"
# KIES HIER JE WACHTWOORD VOOR DE BOEKHOUDER
ADMIN_PASSWORD = "Yuki2025!" 

st.set_page_config(page_title="Kassa App", page_icon="💶", layout="centered")

# CSS Styling
st.markdown("""
    <style>
    .block-container { padding-top: 4rem; padding-bottom: 2rem; }
    [data-testid="stDataFrameResizable"] { border: 1px solid #ddd; border-radius: 5px; }
    .stAlert { margin-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- YUKI CODES ---
YUKI_CODES = {
    "Omzet_21": "700021",
    "Omzet_12": "700012",
    "Omzet_6":  "700006",
    "Omzet_0":  "700000",
    "Kas":      "570000",
    "Kruisposten": "580000"
}

# --- FUNCTIES ---

def load_database():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        cols = [
            "Datum", "Omschrijving", "Totaal_Omzet", "Totaal_Geld", "Verschil",
            "Omzet_0", "Omzet_6", "Omzet_12", "Omzet_21",
            "Geld_Bancontact", "Geld_Cash", "Geld_Payconiq", "Geld_Bonnen",
            "Timestamp"
        ]
        return pd.DataFrame(columns=cols)

def get_data_by_date(datum_obj):
    df = load_database()
    match = df[df['Datum'] == str(datum_obj)]
    return match.iloc[0] if not match.empty else None

def save_transaction(datum, omschrijving, df_input, totaal_omzet, totaal_geld, verschil):
    df_db = load_database()
    datum_str = str(datum)
    df_db = df_db[df_db['Datum'] != datum_str]
    
    new_row = {
        "Datum": datum_str,
        "Omschrijving": omschrijving,
        "Totaal_Omzet": totaal_omzet,
        "Totaal_Geld": totaal_geld,
        "Verschil": verschil,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Omzet_0": 0.0, "Omzet_6": 0.0, "Omzet_12": 0.0, "Omzet_21": 0.0,
        "Geld_Bancontact": 0.0, "Geld_Cash": 0.0, "Geld_Payconiq": 0.0, "Geld_Bonnen": 0.0
    }
    
    for index, row in df_input.iterrows():
        label = row['Label']
        bedrag = row['Bedrag']
        if bedrag > 0:
            if "0%" in label:    new_row["Omzet_0"] = bedrag
            elif "6%" in label:  new_row["Omzet_6"] = bedrag
            elif "12%" in label: new_row["Omzet_12"] = bedrag
            elif "21%" in label: new_row["Omzet_21"] = bedrag
            elif "Bancontact" in label: new_row["Geld_Bancontact"] = bedrag
            elif "Cash" in label: new_row["Geld_Cash"] = bedrag
            elif "Payconiq" in label: new_row["Geld_Payconiq"] = bedrag
            elif "Bonnen" in label: new_row["Geld_Bonnen"] = bedrag

    new_entry_df = pd.DataFrame([new_row])
    df_db = pd.concat([df_db, new_entry_df], ignore_index=True)
    df_db = df_db.sort_values(by="Datum", ascending=False)
    df_db.to_csv(DATA_FILE, index=False)

def handle_save_click(datum, omschrijving, edited_df, som_omzet, som_geld, verschil):
    save_transaction(datum, omschrijving, edited_df, som_omzet, som_geld, verschil)
    st.session_state.reset_count += 1
    st.session_state.omschrijving = "" 
    st.session_state['show_success_toast'] = True

def generate_yuki_export(start_date, end_date):
    df = load_database()
    mask = (df['Datum'] >= str(start_date)) & (df['Datum'] <= str(end_date))
    selection = df.loc[mask]
    
    if selection.empty: return None

    yuki_rows = []
    for index, row in selection.iterrows():
        datum_fmt = pd.to_datetime(row['Datum']).strftime('%d-%m-%Y')
        desc = row['Omschrijving'] or "Dagontvangst"
        
        # Credit (Omzet)
        if row['Omzet_21'] > 0: yuki_rows.append([datum_fmt, YUKI_CODES["Omzet_21"], f"Omzet 21% - {desc}", f"{-row['Omzet_21']:.2f}".replace('.',','), "V21"])
        if row['Omzet_12'] > 0: yuki_rows.append([datum_fmt, YUKI_CODES["Omzet_12"], f"Omzet 12% - {desc}", f"{-row['Omzet_12']:.2f}".replace('.',','), "V12"])
        if row['Omzet_6'] > 0:  yuki_rows.append([datum_fmt, YUKI_CODES["Omzet_6"], f"Omzet 6% - {desc}", f"{-row['Omzet_6']:.2f}".replace('.',','), "V6"])
        if row['Omzet_0'] > 0:  yuki_rows.append([datum_fmt, YUKI_CODES["Omzet_0"], f"Omzet 0% - {desc}", f"{-row['Omzet_0']:.2f}".replace('.',','), "V0"])
            
        # Debet (Betalingen)
        if row['Geld_Cash'] > 0: yuki_rows.append([datum_fmt, YUKI_CODES["Kas"], "Ontvangst Cash", f"{row['Geld_Cash']:.2f}".replace('.',','), ""])
        tot_elec = row['Geld_Bancontact'] + row['Geld_Payconiq'] + row['Geld_Bonnen']
        if tot_elec > 0:         yuki_rows.append([datum_fmt, YUKI_CODES["Kruisposten"], "Ontvangst Elec.", f"{tot_elec:.2f}".replace('.',','), ""])

    return pd.DataFrame(yuki_rows, columns=["Datum", "Grootboekrekening", "Omschrijving", "Bedrag", "BtwCode"])

# --- STATE ---
if 'reset_count' not in st.session_state: st.session_state.reset_count = 0
if 'show_success_toast' not in st.session_state: st.session_state['show_success_toast'] = False

# ==========================================
# ⚙️ SIDEBAR (NU MET LOGIN LOGICA)
# ==========================================
with st.sidebar:
    st.header("⚙️ Menu")
    
    # 1. Beveiliging Sectie
    pwd = st.text_input("Boekhouder Login", type="password", placeholder="Wachtwoord")
    
    # Check of wachtwoord klopt
    is_admin = (pwd == ADMIN_PASSWORD)
    
    app_mode = "Invoer" # Standaard modus
    
    if is_admin:
        st.success("🔓 Toegang verleend")
        # Als admin is ingelogd, toon keuze menu
        app_mode = st.radio("Kies scherm:", ["Invoer", "Export (Yuki)"])
        
        st.divider()
        # Admin mag ook raw data downloaden
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, "rb") as f:
                st.download_button("📥 Backup (.csv)", f, "backup_db.csv", "text/csv")
    
    st.divider()
    
    # Instellingen alleen tonen bij Invoer
    if app_mode == "Invoer":
        st.subheader("Instellingen")
        use_0  = st.checkbox("0% (Vrijgesteld)", value=True)
        use_6  = st.checkbox("6% (Voeding)", value=True)
        use_12 = st.checkbox("12% (Horeca)", value=False)
        use_21 = st.checkbox("21% (Algemeen)", value=True)
        st.markdown("---")
        use_bc   = st.checkbox("Bancontact", value=True)
        use_cash = st.checkbox("Cash", value=True)
        use_payq = st.checkbox("Payconiq", value=True)
        use_vouc = st.checkbox("Cadeaubonnen", value=False)

# ==========================================
# 📅 HOOFDSCHERM (WISSELT OP BASIS VAN MODUS)
# ==========================================

# --- SCHERM 1: INVOER (Voor Klant & Boekhouder) ---
if app_mode == "Invoer":
    st.header("📝 Dagontvangst") 

    if st.session_state['show_success_toast']:
        st.toast("Succesvol opgeslagen!", icon="✅")
        st.session_state['show_success_toast'] = False

    c1, c2 = st.columns([1, 2])
    with c1:
        datum = st.date_input("Datum", datetime.now(), label_visibility="collapsed")
    with c2:
        omschrijving = st.text_input("Omschrijving", placeholder="Korte notitie...", label_visibility="collapsed", key="omschrijving")

    st.divider()

    existing_data = get_data_by_date(datum)
    is_overwrite_mode = existing_data is not None

    def get_val(col_name):
        return float(existing_data.get(col_name, 0.0)) if is_overwrite_mode else 0.00

    data_items = []
    if use_0:  data_items.append({"Label": "🎫 0% (Vrijgesteld)", "Bedrag": get_val("Omzet_0"), "Type": "Omzet"})
    if use_6:  data_items.append({"Label": "🎫 6% (Voeding)",     "Bedrag": get_val("Omzet_6"), "Type": "Omzet"})
    if use_12: data_items.append({"Label": "🎫 12% (Horeca)",     "Bedrag": get_val("Omzet_12"), "Type": "Omzet"})
    if use_21: data_items.append({"Label": "🎫 21% (Algemeen)",   "Bedrag": get_val("Omzet_21"), "Type": "Omzet"})

    data_items.append({"Label": "⬇️ --- LADE INHOUD --- ⬇️", "Bedrag": None, "Type": "Separator"})

    if use_bc:   data_items.append({"Label": "💳 Bancontact",   "Bedrag": get_val("Geld_Bancontact"), "Type": "Geld"})
    if use_cash: data_items.append({"Label": "💶 Cash",         "Bedrag": get_val("Geld_Cash"), "Type": "Geld"})
    if use_payq: data_items.append({"Label": "📱 Payconiq",     "Bedrag": get_val("Geld_Payconiq"), "Type": "Geld"})
    if use_vouc: data_items.append({"Label": "🎁 Bonnen",       "Bedrag": get_val("Geld_Bonnen"), "Type": "Geld"})

    df_start = pd.DataFrame(data_items)
    saved_desc = existing_data.get("Omschrijving", "") if is_overwrite_mode else ""

    overwrite_confirmed = True
    if is_overwrite_mode:
        st.warning(f"⚠️ Er zijn al gegevens voor {datum.strftime('%d-%m-%Y')}.")
        if saved_desc: st.info(f"Notitie: {saved_desc}")
        overwrite_confirmed = st.checkbox("Overschrijven toestaan", value=False)

    edited_df = st.data_editor(
        df_start,
        column_config={
            "Label": st.column_config.TextColumn("Omschrijving", disabled=True),
            "Bedrag": st.column_config.NumberColumn("Waarde (€)", min_value=0, format="%.2f"),
            "Type": None
        },
        hide_index=True, use_container_width=True, num_rows="fixed",
        height=(len(data_items) * 35) + 38,
        key=f"editor_{datum}_{st.session_state.reset_count}"
    )

    regels = edited_df[edited_df["Type"] != "Separator"].copy()
    regels["Bedrag"] = regels["Bedrag"].fillna(0.0)
    som_omzet = regels[regels["Type"] == "Omzet"]["Bedrag"].sum()
    som_geld = regels[regels["Type"] == "Geld"]["Bedrag"].sum()
    verschil = round(som_omzet - som_geld, 2)

    st.divider()
    c_inf, c_btn = st.columns([1, 1])

    with c_inf:
        if som_omzet == 0: st.info("👆 Vul de gegevens in.")
        elif verschil == 0: st.markdown(f"### ✅ :green[OK: € {som_omzet:.2f}]")
        else: st.markdown(f"### ❌ :red[Verschil: € {verschil:.2f}]")

    with c_btn:
        is_valid = (som_omzet > 0) and (verschil == 0) and overwrite_confirmed
        label = "🔄 Overschrijven" if is_overwrite_mode else "💾 Opslaan"
        
        st.button(label, type="primary", disabled=not is_valid, use_container_width=True,
                  on_click=handle_save_click,
                  args=(datum, omschrijving, edited_df, som_omzet, som_geld, verschil))

# --- SCHERM 2: EXPORT (Alleen zichtbaar voor admin) ---
elif app_mode == "Export (Yuki)":
    st.header("📤 Export voor Boekhouding")
    st.info("Selecteer de periode die je wilt exporteren naar Yuki.")
    
    col_start, col_end = st.columns(2)
    start_date = col_start.date_input("Van", datetime(datetime.now().year, datetime.now().month, 1))
    end_date = col_end.date_input("Tot", datetime.now())
    
    if st.button("Genereer Export Bestand", type="primary"):
        yuki_df = generate_yuki_export(start_date, end_date)
        
        if yuki_df is not None:
            st.success(f"✅ {len(yuki_df)} boekingsregels gegenereerd.")
            st.dataframe(yuki_df, hide_index=True)
            
            csv = yuki_df.to_csv(sep=';', index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Yuki Bestand (.csv)",
                data=csv,
                file_name=f"yuki_export_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.warning("Geen gegevens gevonden in deze periode.")
