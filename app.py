import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import time
import os
import locale
import calendar # Nodig voor de maand-matrix

# Probeer NL instellingen
try: locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
except: pass

# --- CONFIGURATIE ---
DATA_FILE = "kassa_historiek.csv"
SETTINGS_FILE = "kassa_settings.csv"
ADMIN_PASSWORD = "Yuki2025!" 

st.set_page_config(page_title="Dagontvangsten App", page_icon="💶", layout="centered")

# CSS Styling
st.markdown("""
    <style>
    .block-container { padding-top: 3rem; padding-bottom: 2rem; }
    [data-testid="stDataFrameResizable"] { border: 1px solid #ddd; border-radius: 5px; }
    .stAlert { margin-top: 1rem; }
    div.stButton > button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTIES ---

def get_default_settings():
    return [
        {"Code": "Omzet_21",   "Label": "Omzet 21%",       "Rekening": "700021", "BtwCode": "V21", "Type": "Credit"},
        {"Code": "Omzet_12",   "Label": "Omzet 12%",       "Rekening": "700012", "BtwCode": "V12", "Type": "Credit"},
        {"Code": "Omzet_6",    "Label": "Omzet 6%",        "Rekening": "700006", "BtwCode": "V6",  "Type": "Credit"},
        {"Code": "Omzet_0",    "Label": "Omzet 0%",        "Rekening": "700000", "BtwCode": "V0",  "Type": "Credit"},
        {"Code": "Kas",        "Label": "Kas (Cash)",      "Rekening": "570000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Bancontact", "Label": "Bancontact",      "Rekening": "580000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Payconiq",   "Label": "Payconiq",        "Rekening": "580000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Bonnen",     "Label": "Cadeaubonnen",    "Rekening": "440000", "BtwCode": "",    "Type": "Debet"},
    ]

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        return pd.read_csv(SETTINGS_FILE, dtype={"Rekening": str, "BtwCode": str})
    else:
        df = pd.DataFrame(get_default_settings())
        df["Rekening"] = df["Rekening"].astype(str)
        df.to_csv(SETTINGS_FILE, index=False)
        return df

def save_settings(df_settings):
    df_settings.to_csv(SETTINGS_FILE, index=False)

def get_yuki_mapping():
    df = load_settings()
    return dict(zip(df.Code, df.Rekening))

def load_database():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = df.fillna("") 
        return df
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
    
    if not omschrijving or omschrijving.strip() == "" or omschrijving == "nan":
        datum_fmt = pd.to_datetime(datum).strftime('%d-%m-%Y')
        omschrijving = f"Dagontvangsten {datum_fmt}"

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
    CODES = get_yuki_mapping() 
    yuki_rows = []
    for index, row in selection.iterrows():
        datum_fmt = pd.to_datetime(row['Datum']).strftime('%d-%m-%Y')
        desc = row['Omschrijving'] 
        if not desc: desc = f"Dagontvangsten {datum_fmt}"

        if row['Omzet_21'] > 0: yuki_rows.append([datum_fmt, CODES.get("Omzet_21", "700021"), f"Omzet 21% - {desc}", f"{-row['Omzet_21']:.2f}".replace('.',','), "V21"])
        if row['Omzet_12'] > 0: yuki_rows.append([datum_fmt, CODES.get("Omzet_12", "700012"), f"Omzet 12% - {desc}", f"{-row['Omzet_12']:.2f}".replace('.',','), "V12"])
        if row['Omzet_6'] > 0:  yuki_rows.append([datum_fmt, CODES.get("Omzet_6", "700006"), f"Omzet 6% - {desc}", f"{-row['Omzet_6']:.2f}".replace('.',','), "V6"])
        if row['Omzet_0'] > 0:  yuki_rows.append([datum_fmt, CODES.get("Omzet_0", "700000"), f"Omzet 0% - {desc}", f"{-row['Omzet_0']:.2f}".replace('.',','), "V0"])
        if row['Geld_Cash'] > 0: yuki_rows.append([datum_fmt, CODES.get("Kas", "570000"), "Ontvangst Cash", f"{row['Geld_Cash']:.2f}".replace('.',','), ""])
        if row['Geld_Bancontact'] > 0: yuki_rows.append([datum_fmt, CODES.get("Bancontact", "580000"), "Ontvangst Bancontact", f"{row['Geld_Bancontact']:.2f}".replace('.',','), ""])
        if row['Geld_Payconiq'] > 0: yuki_rows.append([datum_fmt, CODES.get("Payconiq", "580000"), "Ontvangst Payconiq", f"{row['Geld_Payconiq']:.2f}".replace('.',','), ""])
        if row['Geld_Bonnen'] > 0: yuki_rows.append([datum_fmt, CODES.get("Bonnen", "440000"), "Ontvangst Bonnen", f"{row['Geld_Bonnen']:.2f}".replace('.',','), ""])
    return pd.DataFrame(yuki_rows, columns=["Datum", "Grootboekrekening", "Omschrijving", "Bedrag", "BtwCode"])

# --- STATE ---
if 'reset_count' not in st.session_state: st.session_state.reset_count = 0
if 'show_success_toast' not in st.session_state: st.session_state['show_success_toast'] = False
if 'current_date' not in st.session_state: st.session_state.current_date = datetime.now().date()

def prev_day(): st.session_state.current_date -= timedelta(days=1)
def next_day(): st.session_state.current_date += timedelta(days=1)
def update_date(): st.session_state.current_date = st.session_state.date_picker_val

# ==========================================
# ⚙️ SIDEBAR
# ==========================================
with st.sidebar:
    st.header("⚙️ Menu")
    pwd = st.text_input("Boekhouder Login", type="password", placeholder="Wachtwoord")
    is_admin = (pwd == ADMIN_PASSWORD)
    app_mode = "Invoer" 
    if is_admin:
        st.success("🔓 Toegang verleend")
        app_mode = st.radio("Kies scherm:", ["Invoer", "Export (Yuki)", "Instellingen"])
        st.divider()
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, "rb") as f:
                st.download_button("📥 Backup (.csv)", f, "backup_db.csv", "text/csv")
    st.divider()
    if app_mode == "Invoer":
        st.subheader("Profiel & Sector")
        sector_keuze = st.selectbox(
            "Kies uw activiteit:", 
            ["Detailhandel (Standaard)", "Huisarts/Kiné (Medisch)", "Tandarts (Gemengd)", "Horeca/Café", "Bakkerij"]
        )
        # Defaults
        def_0, def_6, def_12, def_21 = True, True, False, True 
        if "Medisch" in sector_keuze: def_0, def_6, def_12, def_21 = True, False, False, False
        elif "Tandarts" in sector_keuze: def_0, def_6, def_12, def_21 = True, False, False, True
        elif "Horeca" in sector_keuze: def_0, def_6, def_12, def_21 = False, False, True, True
        elif "Bakkerij" in sector_keuze: def_0, def_6, def_12, def_21 = False, True, False, True
            
        st.write("**BTW Configuratie:**")
        use_0  = st.checkbox("0% (Vrijgesteld)", value=def_0)
        use_6  = st.checkbox("6% (Voeding/Krant)", value=def_6)
        use_12 = st.checkbox("12% (Horeca/Maaltijd)", value=def_12)
        use_21 = st.checkbox("21% (Algemeen/Drank)", value=def_21)
        st.markdown("---")
        st.write("**Betaalopties:**")
        use_bc   = st.checkbox("Bancontact", value=True)
        use_cash = st.checkbox("Cash", value=True)
        use_payq = st.checkbox("Payconiq", value=True)
        use_vouc = st.checkbox("Cadeaubonnen", value=False)

# ==========================================
# 📅 HOOFDSCHERM
# ==========================================

if app_mode == "Invoer":
    if st.session_state['show_success_toast']:
        st.toast("Succesvol opgeslagen!", icon="✅")
        st.session_state['show_success_toast'] = False

    # --- NIEUW: HET MAANDOVEZICHT ---
    # We maken een visuele kalender in een expander
    with st.expander("📅 Status Maandoverzicht", expanded=False):
        
        # Huidige maand selecteren
        huidige_maand = st.session_state.current_date.month
        huidig_jaar = st.session_state.current_date.year
        
        # Haal data op
        df_hist = load_database()
        
        # Genereer alle dagen van deze maand
        num_days = calendar.monthrange(huidig_jaar, huidige_maand)[1]
        days = [date(huidig_jaar, huidige_maand, day) for day in range(1, num_days + 1)]
        
        status_list = []
        for d in days:
            d_str = str(d)
            # Check of data bestaat in CSV
            row = df_hist[df_hist['Datum'] == d_str]
            
            status = "⚪" # Nog leeg
            omzet = 0.0
            
            if not row.empty:
                status = "✅" # Gedaan
                omzet = float(row.iloc[0]['Totaal_Omzet'])
            elif d < date.today():
                status = "❌" # Te laat!
            
            # Voeg toe aan lijst
            status_list.append({
                "Datum": d.strftime("%d-%m"),
                "Dag": d.strftime("%a"),
                "Status": status,
                "Omzet": f"€ {omzet:.2f}" if omzet > 0 else "-"
            })
            
        # Toon als dataframe
        df_status = pd.DataFrame(status_list)
        st.dataframe(
            df_status, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="small
