import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import time
import os
import locale
import calendar
import json
import gspread
from google.oauth2.service_account import Credentials

# Probeer NL instellingen
try: locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
except: pass

# --- CONFIGURATIE ---
# LET OP: Zorg dat je secrets goed staan in .streamlit/secrets.toml of op Streamlit Cloud
# SHEET_URL = st.secrets["sheet_url"] 
# Voor lokaal gebruik (als je nog geen secrets hebt) kan je dit hardcoden, maar voor Cloud gebruik je secrets.
# Hieronder ga ik ervan uit dat de secrets aanwezig zijn zoals eerder besproken.

try:
    SHEET_URL = st.secrets["sheet_url"]
except:
    st.error("Geen 'sheet_url' gevonden in secrets. Configureer dit eerst.")
    st.stop()

ADMIN_PASSWORD = "Yuki2025!" 

st.set_page_config(page_title="Dagontvangsten App", page_icon="💶", layout="centered")

# --- GOOGLE SHEETS CONNECTIE ---
@st.cache_resource
def get_google_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URL)

def get_worksheet_data(worksheet_name):
    sh = get_google_sheet()
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        if not data: return pd.DataFrame()
        # Zorg dat lege strings NaN worden en conversie types
        df = pd.DataFrame(data)
        return df
    except gspread.WorksheetNotFound:
        sh.add_worksheet(title=worksheet_name, rows=1000, cols=20)
        return pd.DataFrame()

def save_dataframe_to_sheet(df, worksheet_name):
    sh = get_google_sheet()
    try: ws = sh.worksheet(worksheet_name)
    except: ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=20)
    ws.clear()
    # Headers en data schrijven. Convert types naar string/json safe indien nodig voor gspread
    # Gspread update verwacht strings of ints, geen Pandas NaNs.
    df_clean = df.fillna("")
    ws.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())

# --- CSS STYLING ---
st.markdown("""
    <style>
    /* 1. Header Transparant */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    /* 2. Inhoud naar beneden */
    .block-container { 
        padding-top: 3.5rem !important; 
        padding-bottom: 2rem; 
    }
    
    /* 3. Info Kaarten */
    .info-card {
        height: 50px; display: flex; align-items: center; justify-content: center;
        border-radius: 8px; font-weight: bold; font-size: 0.95rem; margin-bottom: 10px;
        border: 1px solid rgba(49, 51, 63, 0.1);
    }
    .card-red   { background-color: #fce8e6; color: #a30f0f; }
    .card-green { background-color: #e6fcf5; color: #0f5132; }
    .card-grey  { background-color: #f0f2f6; color: #31333f; }
    .card-blue  { background-color: #e7f5ff; color: #004085; }
    
    .day-header { text-align: center; font-size: 1.3rem; font-weight: 700; margin-bottom: 0px; color: #31333f; }
    .sub-status { text-align: center; font-size: 0.85rem; margin-bottom: 5px; }
    
    div.stButton > button { width: 100%; }
    div[data-testid="stDateInput"] { text-align: center; }
    .streamlit-expanderHeader { background-color: #f8f9fa; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTIES: CONFIG & SETTINGS ---

def load_config():
    df = get_worksheet_data("Config")
    if df.empty: return {"start_saldo": 0.0}
    return df.iloc[0].to_dict()

def save_config_sheet(new_saldo):
    df = pd.DataFrame([{"start_saldo": new_saldo, "laatste_update": str(datetime.now())}])
    save_dataframe_to_sheet(df, "Config")

def get_default_settings():
    return [
        {"Code": "Omzet_21",   "Label": "Omzet 21%",       "Rekening": "700021", "ExportDesc": "Omzet 21% (&notitie&)", "BtwCode": "V21", "Type": "Credit"},
        {"Code": "Omzet_12",   "Label": "Omzet 12%",       "Rekening": "700012", "ExportDesc": "Omzet 12% (&notitie&)", "BtwCode": "V12", "Type": "Credit"},
        {"Code": "Omzet_6",    "Label": "Omzet 6%",        "Rekening": "700006", "ExportDesc": "Omzet 6% (&notitie&)",  "BtwCode": "V6",  "Type": "Credit"},
        {"Code": "Omzet_0",    "Label": "Omzet 0%",        "Rekening": "700000", "ExportDesc": "Omzet 0% (&notitie&)",  "BtwCode": "V0",  "Type": "Credit"},
        {"Code": "Cash",       "Label": "Kas (Cash)",      "Rekening": "570000", "ExportDesc": "Ontvangst Cash",        "BtwCode": "",    "Type": "Debet"},
        {"Code": "Bancontact", "Label": "Bancontact",      "Rekening": "580000", "ExportDesc": "Bancontact &datum&",    "BtwCode": "",    "Type": "Debet"},
        {"Code": "Payconiq",   "Label": "Payconiq",        "Rekening": "580000", "ExportDesc": "Payconiq &datum&",      "BtwCode": "",    "Type": "Debet"},
        {"Code": "Oversch",    "Label": "Overschrijving",  "Rekening": "580000", "ExportDesc": "Overschrijving &datum&","BtwCode": "",    "Type": "Debet"},
        {"Code": "Bonnen",     "Label": "Cadeaubonnen",    "Rekening": "440000", "ExportDesc": "Cadeaubon &datum&",     "BtwCode": "",    "Type": "Debet"},
        {"Code": "Afstorting", "Label": "Afstorting Bank", "Rekening": "550000", "ExportDesc": "Afstorting &datum&",    "BtwCode": "",    "Type": "Credit"},
    ]

def load_settings():
    df = get_worksheet_data("Instellingen")
    if df.empty:
        df = pd.DataFrame(get_default_settings())
        save_dataframe_to_sheet(df, "Instellingen")
    
    # Zorg dat types strings zijn
    df = df.astype(str)
    
    # Auto-migratie logica (indien nieuwe kolommen ontbreken)
    changes = False
    if "ExportDesc" not in df.columns:
        df["ExportDesc"] = df["Label"]
        changes = True
    
    # Check voor nieuwe rijen
    defaults = pd.DataFrame(get_default_settings())
    existing_codes = df["Code"].tolist()
    for code in ["Oversch", "Afstorting"]:
        if code not in existing_codes:
            row = defaults[defaults["Code"] == code].iloc[0]
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            changes = True
            
    if changes:
        save_dataframe_to_sheet(df, "Instellingen")
        
    return df

def save_settings(df_settings):
    save_dataframe_to_sheet(df_settings, "Instellingen")

def get_yuki_mapping():
    df = load_settings()
    mapping = {}
    for index, row in df.iterrows():
        mapping[row['Code']] = {
            'Rekening': row['Rekening'],
            'Label': row['Label'],
            'Template': row.get('ExportDesc', row['Label']) 
        }
    return mapping

# --- EXPORT CONFIG ---
def get_default_export_config():
    return [
        {"Kolom": "Grootboekrekening kas", "Bron": "Vast", "Waarde": "570000"},
        {"Kolom": "Kas omschrijving",      "Bron": "Vast", "Waarde": "Dagontvangsten"},
        {"Kolom": "Transactie code",       "Bron": "Vast", "Waarde": ""},
        {"Kolom": "Tegenrekening",         "Bron": "Veld", "Waarde": "Grootboekrekening"}, 
        {"Kolom": "Naam tegenrekening",    "Bron": "Veld", "Waarde": "Label"}, 
        {"Kolom": "Datum transactie",      "Bron": "Veld", "Waarde": "Datum"},             
        {"Kolom": "Omschrijving",          "Bron": "Veld", "Waarde": "Omschrijving"},
        {"Kolom": "Bedrag",                "Bron": "Veld", "Waarde": "Bedrag"},
        {"Kolom": "Saldo kas",             "Bron": "Vast", "Waarde": ""}, 
        {"Kolom": "Projectcode",           "Bron": "Vast", "Waarde": ""},
        {"Kolom": "Projectnaam",           "Bron": "Vast", "Waarde": ""},
    ]

def load_export_config():
    df = get_worksheet_data("ExportConfig")
    if df.empty:
        df = pd.DataFrame(get_default_export_config())
        save_dataframe_to_sheet(df, "ExportConfig")
    
    # Check oude BTW kolom
    if "BTW Code" in df["Kolom"].values:
        df = df[df["Kolom"] != "BTW Code"]
        save_dataframe_to_sheet(df, "ExportConfig")
        
    return df

def save_export_config(df):
    save_dataframe_to_sheet(df, "ExportConfig")

# --- DATA ---
def load_database():
    df = get_worksheet_data("Historiek")
    if df.empty:
        return pd.DataFrame(columns=["Datum", "Omschrijving", "Totaal_Omzet", "Totaal_Geld", "Verschil", 
                                     "Omzet_0", "Omzet_6", "Omzet_12", "Omzet_21", 
                                     "Geld_Bancontact", "Geld_Cash", "Geld_Payconiq", "Geld_Overschrijving", 
                                     "Geld_Bonnen", "Geld_Afstorting", "Timestamp"])
    
    # Numerieke kolommen forceren
    cols = ["Totaal_Omzet", "Totaal_Geld", "Verschil", "Omzet_0", "Omzet_6", "Omzet_12", "Omzet_21",
            "Geld_Bancontact", "Geld_Cash", "Geld_Payconiq", "Geld_Overschrijving", "Geld_Bonnen", "Geld_Afstorting"]
    
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
            
    return df

def get_data_by_date(datum_obj):
    df = load_database()
    match = df[df['Datum'] == str(datum_obj)]
    return match.iloc[0] if not match.empty else None

def calculate_current_saldo(target_date):
    config = load_config()
    start = float(config.get("start_saldo", 0.0))
    df = load_database()
    if df.empty: return start
    
    # Datum conversie voor vergelijking
    df['DatumDT'] = pd.to_datetime(df['Datum'])
    target_dt = pd.to_datetime(target_date)
    
    hist = df[df['DatumDT'] < target_dt]
    return start + hist['Geld_Cash'].sum() - hist['Geld_Afstorting'].sum()

def save_transaction(datum, omschrijving, df_input, totaal_omzet, totaal_geld, verschil):
    df_db = load_database()
    datum_str = str(datum)
    
    # Oude data verwijderen (filteren)
    if not df_db.empty:
        df_db = df_db[df_db['Datum'] != datum_str]
    
    if df_input is None: df_input = pd.DataFrame(columns=['Label', 'Bedrag'])
    if not omschrijving or omschrijving.strip() == "" or omschrijving == "nan":
        omschrijving = f"Dagontvangsten {pd.to_datetime(datum).strftime('%d-%m-%Y')}"
        
    new_row = {
        "Datum": datum_str, "Omschrijving": omschrijving, "Totaal_Omzet": totaal_omzet, "Totaal_Geld": totaal_geld, "Verschil": verschil,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Omzet_0": 0.0, "Omzet_6": 0.0, "Omzet_12": 0.0, "Omzet_21": 0.0,
        "Geld_Bancontact": 0.0, "Geld_Cash": 0.0, "Geld_Payconiq": 0.0, "Geld_Overschrijving": 0.0, "Geld_Bonnen": 0.0, "Geld_Afstorting": 0.0
    }
    
    for index, row in df_input.iterrows():
        label = row['Label']
        bedrag = row['Bedrag']
        if bedrag > 0:
            if "0%" in label: new_row["Omzet_0"] = bedrag
            elif "6%" in label: new_row["Omzet_6"] = bedrag
            elif "12%" in label: new_row["Omzet_12"] = bedrag
            elif "21%" in label: new_row["Omzet_21"] = bedrag
            elif "Bancontact" in label: new_row["Geld_Bancontact"] = bedrag
            elif "Cash" in label: new_row["Geld_Cash"] = bedrag
            elif "Payconiq" in label: new_row["Geld_Payconiq"] = bedrag
            elif "Overschrijving" in label: new_row["Geld_Overschrijving"] = bedrag
            elif "Bonnen" in label: new_row["Geld_Bonnen"] = bedrag
            elif "Afstorting" in label: new_row["Geld_Afstorting"] = bedrag
            
    new_entry_df = pd.DataFrame([new_row])
    df_final = pd.concat([df_db, new_entry_df], ignore_index=True)
    df_final = df_final.sort_values(by="Datum", ascending=False)
    
    # Opslaan naar GSheets
    save_dataframe_to_sheet(df_final, "Historiek")

def handle_save_click(datum, omschrijving, edited_df, som_omzet, som_geld, verschil):
    with st.spinner("Bezig met opslaan..."):
        save_transaction(datum, omschrijving, edited_df, som_omzet, som_geld, verschil)
    st.session_state.reset_count += 1
    st.session_state.omschrijving = "" 
    st.session_state['show_success_toast'] = True

# --- EXPORT ENGINE ---

def generate_flexible_export(start_date, end_date):
    df_data = load_database()
    export_config = load_export_config()
    MAPPING = get_yuki_mapping() 
    
    mask = (df_data['Datum'] >= str(start_date)) & (df_data['Datum'] <= str(end_date))
    selection = df_data.loc[mask]
    
    # Sorteer oplopend (Oud naar Nieuw)
    selection = selection.sort_values(by="Datum", ascending=True)
    
    if selection.empty: return None

    export_rows = []
    
    for index, row in selection.iterrows():
        if row['Totaal_Omzet'] == 0 and row['Totaal_Geld'] == 0: continue
        
        datum_fmt = pd.to_datetime(row['Datum']).strftime('%d-%m-%Y')
        desc_user = row['Omschrijving'] 
        
        transactions = []
        
        def add_trx(code_key, bedrag, btw, trx_type="Omzet"):
            info = MAPPING.get(code_key, {})
            rekening = info.get('Rekening', '')
            label = info.get('Label', code_key)
            template = info.get('Template', '')
            
            # Template invullen
            final_desc = template.replace("&datum&", datum_fmt)
            final_desc = final_desc.replace("&notitie&", desc_user)
            if not final_desc: final_desc = f"{label} {datum_fmt}"

            transactions.append({
                "Rek": rekening, 
                "Bedrag": bedrag, 
                "Btw": btw, 
                "Desc": final_desc, 
                "Label": label
            })

        # OMZET
        if row['Omzet_21'] > 0: add_trx("Omzet_21", row['Omzet_21'], "V21")
        if row['Omzet_12'] > 0: add_trx("Omzet_12", row['Omzet_12'], "V12")
        if row['Omzet_6'] > 0:  add_trx("Omzet_6",  row['Omzet_6'],  "V6")
        if row['Omzet_0'] > 0:  add_trx("Omzet_0",  row['Omzet_0'],  "V0")
        
        # GELD
        if row['Geld_Bancontact'] > 0:   add_trx("Bancontact", -row['Geld_Bancontact'], "")
        if row['Geld_Payconiq'] > 0:     add_trx("Payconiq",   -row['Geld_Payconiq'],   "")
        if row['Geld_Overschrijving'] > 0: add_trx("Oversch",  -row['Geld_Overschrijving'], "")
        if row['Geld_Bonnen'] > 0:       add_trx("Bonnen",     -row['Geld_Bonnen'],     "")
        if row['Geld_Afstorting'] > 0:   add_trx("Afstorting", -row['Geld_Afstorting'], "")
        if row['Geld_Cash'] > 0:         add_trx("Cash",       -row['Geld_Cash'],       "")

        for t in transactions:
            export_row = {}
            for _, cfg in export_config.iterrows():
                col_name = cfg['Kolom']
                source = cfg['Bron']
                val_key = cfg['Waarde']
                final_val = ""
                
                if source == "Vast":
                    final_val = val_key if val_key and str(val_key) != "nan" else ""
                elif source == "Veld":
                    if val_key == "Datum": final_val = datum_fmt
                    elif val_key == "Omschrijving": final_val = t['Desc']
                    elif val_key == "Label": final_val = t['Label']       
                    elif val_key == "Bedrag": final_val = f"{-t['Bedrag']:.2f}".replace('.',',')
                    elif val_key == "Grootboekrekening": final_val = t['Rek']
                    elif val_key == "BtwCode": final_val = t['Btw']
                
                export_row[col_name] = final_val
            export_rows.append(export_row)
            
    return pd.DataFrame(export_rows)

# --- STATE ---
if 'reset_count' not in st.session_state: st.session_state.reset_count = 0
if 'show_success_toast' not in st.session_state: st.session_state['show_success_toast'] = False
if 'date_picker_val' not in st.session_state: st.session_state.date_picker_val = datetime.now().date()

def prev_day(): st.session_state.date_picker_val -= timedelta(days=1)
def next_day(): 
    if st.session_state.date_picker_val < datetime.now().date():
        st.session_state.date_picker_val += timedelta(days=1)
def update_date(): pass

# ==========================================
# ⚙️ SIDEBAR
# ==========================================
with st.sidebar:
    st.header("⚙️ Menu")
    pwd = st.text_input("Boekhouder Login", type="password", placeholder="Wachtwoord")
    is_admin = (pwd == ADMIN_PASSWORD)
    app_mode = "Invoer" 
    
    if is_admin:
        st.success("🔓 Admin")
        app_mode = st.radio("Ga naar:", ["Invoer", "Export (Yuki)", "Instellingen", "Export Configuratie", "Kassaldo Beheer"])
    st.divider()
    if app_mode == "Invoer":
        st.subheader("Profiel")
        sector_keuze = st.selectbox("Sector:", ["Detailhandel", "Medisch", "Tandarts", "Horeca", "Bakkerij"])
        def_0, def_6, def_12, def_21 = True, True, False, True 
        if "Medisch" in sector_keuze: def_0, def_6, def_12, def_21 = True, False, False, False
        elif "Tandarts" in sector_keuze: def_0, def_6, def_12, def_21 = True, False, False, True
        elif "Horeca" in sector_keuze: def_0, def_6, def_12, def_21 = False, False, True, True
        elif "Bakkerij" in sector_keuze: def_0, def_6, def_12, def_21 = False, True, False, True
        st.caption("Instellingen")
        use_0  = st.checkbox("0%", value=def_0)
        use_6  = st.checkbox("6%", value=def_6)
        use_12 = st.checkbox("12%", value=def_12)
        use_21 = st.checkbox("21%", value=def_21)
        use_bc   = st.checkbox("Bancontact", value=True)
        use_cash = st.checkbox("Cash", value=True)
        use_payq = st.checkbox("Payconiq", value=True)
        use_over = st.checkbox("Overschrijving", value=True)
        use_vouc = st.checkbox("Cadeaubonnen", value=False)

# ==========================================
# 📅 HOOFDSCHERM
# ==========================================

if app_mode == "Invoer":
    if st.session_state['show_success_toast']:
        st.toast("Opgeslagen in Google Sheets!", icon="✅")
        st.session_state['show_success_toast'] = False
    
    datum_geselecteerd = st.session_state.date_picker_val
    
    # --- HEADER ---
    check_data = get_data_by_date(datum_geselecteerd)
    openings_saldo = calculate_current_saldo(datum_geselecteerd)
    
    if check_data is not None:
        omz = float(check_data['Totaal_Omzet'])
        gld = float(check_data['Totaal_Geld'])
        if omz == 0 and gld == 0: status_html = "<div class='info-card card-blue'>💤 GESLOTEN</div>"
        else: status_html = f"<div class='info-card card-green'>✅ OK: € {omz:.2f}</div>"
    elif datum_geselecteerd > datetime.now().date(): status_html = "<div class='info-card card-grey'>🔒 TOEKOMST</div>"
    else: status_html = "<div class='info-card card-red'>📝 NOG INVULLEN</div>"

    dag_naam = datum_geselecteerd.strftime("%A").upper()
    saldo_html = f"<div class='info-card card-grey'>💰 Saldo: € {openings_saldo:.2f}</div>"
    if check_data is not None: sub_txt, sub_col = "✅ Reeds verwerkt", "green"
    elif datum_geselecteerd > datetime.now().date(): sub_txt, sub_col = "🔒 Toekomst", "grey"
    else: sub_txt, sub_col = "❌ Nog in te vullen", "red"

    col_left, col_center, col_right = st.columns([1.5, 2, 1.5])
    with col_left:
        st.markdown(status_html, unsafe_allow_html=True)
        st.button("⬅️ Vorige", on_click=prev_day, use_container_width=True)
    with col_center:
        st.markdown(f"<div class='day-header'>{dag_naam}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub-status' style='color:{sub_col}'>{sub_txt}</div>", unsafe_allow_html=True)
        st.date_input("Datum", value=st.session_state.date_picker_val, max_value=datetime.now().date(), label_visibility="collapsed", key="date_picker_val")
    with col_right:
        st.markdown(saldo_html, unsafe_allow_html=True)
        is_today = (datum_geselecteerd >= datetime.now().date())
        st.button("Volgende ➡️", on_click=next_day, disabled=is_today, use_container_width=True)

    st.divider()

    # --- INVOER ---
    if datum_geselecteerd > datetime.now().date(): st.info("Toekomst.")
    else:
        existing_data = get_data_by_date(datum_geselecteerd)
        is_overwrite_mode = existing_data is not None
        omschr_value = existing_data.get("Omschrijving", "") if is_overwrite_mode else ""
        omschrijving = st.text_input("Omschrijving", value=omschr_value, placeholder=f"Dagontvangsten {datum_geselecteerd.strftime('%d-%m-%Y')}", key=f"omschr_{datum_geselecteerd}")
        
        is_gesloten = st.checkbox("🚫 Zaak gesloten", value=(is_overwrite_mode and float(existing_data['Totaal_Omzet']) == 0))
        if is_gesloten:
            st.info("Status: Gesloten")
            som_omzet, som_geld, verschil, cash_in_today, cash_out_today = 0.0, 0.0, 0.0, 0.0, 0.0
            edited_df = None 
            if not omschrijving: omschrijving = "SLUITINGSDAG"
        else:
            def get_val(col_name): return float(existing_data.get(col_name, 0.0)) if is_overwrite_mode else 0.00
            data_items = []
            if use_0:  data_items.append({"Sectie": "1. TICKET", "Label": "🎫 0% (Vrijgesteld)", "Bedrag": get_val("Omzet_0"), "Type": "Omzet"})
            if use_6:  data_items.append({"Sectie": "1. TICKET", "Label": "🎫 6% (Voeding)",     "Bedrag": get_val("Omzet_6"), "Type": "Omzet"})
            if use_12: data_items.append({"Sectie": "1. TICKET", "Label": "🎫 12% (Horeca)",     "Bedrag": get_val("Omzet_12"), "Type": "Omzet"})
            if use_21: data_items.append({"Sectie": "1. TICKET", "Label": "🎫 21% (Algemeen)",   "Bedrag": get_val("Omzet_21"), "Type": "Omzet"})
            if use_bc:   data_items.append({"Sectie": "2. GELD", "Label": "💳 Bancontact",     "Bedrag": get_val("Geld_Bancontact"), "Type": "Geld"})
            if use_cash: data_items.append({"Sectie": "2. GELD", "Label": "💶 Cash (Lade)",    "Bedrag": get_val("Geld_Cash"), "Type": "Geld"})
            if use_payq: data_items.append({"Sectie": "2. GELD", "Label": "📱 Payconiq",       "Bedrag": get_val("Geld_Payconiq"), "Type": "Geld"})
            if use_over: data_items.append({"Sectie": "2. GELD", "Label": "🏦 Overschrijving", "Bedrag": get_val("Geld_Overschrijving"), "Type": "Geld"})
            if use_vouc: data_items.append({"Sectie": "2. GELD", "Label": "🎁 Bonnen",         "Bedrag": get_val("Geld_Bonnen"), "Type": "Geld"})
            data_items.append({"Sectie": "3. BANK", "Label": "🏦 Afstorting",    "Bedrag": get_val("Geld_Afstorting"), "Type": "Afstorting"})

            df_start = pd.DataFrame(data_items)
            edited_df = st.data_editor(
                df_start,
                column_config={
                    "Sectie": st.column_config.TextColumn("Groep", disabled=True),
                    "Label": st.column_config.TextColumn("Omschrijving", disabled=True),
                    "Bedrag": st.column_config.NumberColumn("Waarde (€)", min_value=0, format="%.2f"),
                    "Type": None
                },
                hide_index=True, use_container_width=True, num_rows="fixed",
                height=(len(data_items) * 35) + 38,
                key=f"editor_{datum_geselecteerd}_{st.session_state.reset_count}"
            )
            regels = edited_df[edited_df["Type"] != "Separator"].copy()
            regels["Bedrag"] = regels["Bedrag"].fillna(0.0)
            som_omzet = regels[regels["Type"] == "Omzet"]["Bedrag"].sum()
            som_geld = regels[regels["Type"] == "Geld"]["Bedrag"].sum()
            verschil = round(som_omzet - som_geld, 2)
            cash_in_today = regels[regels["Label"] == "💶 Cash (Lade)"]["Bedrag"].sum()
            cash_out_today = regels[regels["Type"] == "Afstorting"]["Bedrag"].sum()

        eind_saldo = openings_saldo + cash_in_today - cash_out_today

        st.markdown("---")
        c_links, c_rechts = st.columns(2)
        with c_links:
            st.markdown("#### 📊 Dag Controle")
            if is_gesloten: st.info("Status: Gesloten")
            elif verschil == 0 and som_omzet > 0: st.success(f"✅ Balans OK: € {som_omzet:.2f}")
            elif som_omzet == 0: st.info("Nog in te vullen")
            else: st.error(f"❌ Verschil: € {verschil:.2f}")
        with c_rechts:
            st.markdown("#### 💰 Kassaldo")
            st.write(f"Begin: € {openings_saldo:.2f}")
            st.write(f"+ Cash: € {cash_in_today:.2f}")
            st.write(f"- Bank: € {cash_out_today:.2f}")
            st.markdown(f"**= Eind: € {eind_saldo:.2f}**")

        st.divider()
        overwrite_confirmed = True
        if is_overwrite_mode: overwrite_confirmed = st.checkbox("Ik wil wijzigingen opslaan", value=False)
        is_valid = ((som_omzet > 0 and verschil == 0) or is_gesloten) and overwrite_confirmed
        label = "🔄 Opslaan" if is_overwrite_mode else "💾 Opslaan"
        st.button(label, type="primary", disabled=not is_valid, use_container_width=True,
                  on_click=handle_save_click,
                  args=(datum_geselecteerd, omschrijving, edited_df, som_omzet, som_geld, verschil))

    # --- MAAND OVERZICHT (ONDERAAN) ---
    with st.expander("📅 Bekijk status maandoverzicht", expanded=False):
        huidige_maand = datum_geselecteerd.month
        huidig_jaar = datum_geselecteerd.year
        df_hist = load_database()
        num_days = calendar.monthrange(huidig_jaar, huidige_maand)[1]
        days = [date(huidig_jaar, huidige_maand, day) for day in range(1, num_days + 1)]
        status_list = []
        for d in days:
            d_str = str(d)
            row = df_hist[df_hist['Datum'] == d_str]
            omzet = 0.0
            status_txt = "⚪"
            if not row.empty:
                omzet_val = float(row.iloc[0]['Totaal_Omzet'])
                geld_val = float(row.iloc[0]['Totaal_Geld'])
                if omzet_val == 0 and geld_val == 0: status_txt = "💤"
                else: 
                    status_txt = "✅"
                    omzet = omzet_val
            elif d < date.today(): status_txt = "❌"
            status_list.append({"Datum": d.strftime("%d-%m"), "Dag": d.strftime("%a"), "Status": status_txt, "Omzet": f"€ {omzet:.2f}" if omzet > 0 else "-"})
        st.dataframe(pd.DataFrame(status_list), hide_index=True, use_container_width=True)

elif app_mode == "Kassaldo Beheer":
    st.header("💰 Kassaldo Beheer")
    st.info("Stel hier het initiële startsaldo in.")
    config = load_config()
    curr_start = config.get("start_saldo", 0.0)
    new_start = st.number_input("Startsaldo", value=float(curr_start), step=10.0, format="%.2f")
    if st.button("💾 Opslaan"):
        config["start_saldo"] = new_start
        save_config_sheet(new_start) # Opslaan in GSheet config tab
        st.success("Opgeslagen!")

elif app_mode == "Export (Yuki)":
    st.header("📤 Export Yuki")
    col_start, col_end = st.columns(2)
    start_date = col_start.date_input("Van", datetime(datetime.now().year, datetime.now().month, 1))
    end_date = col_end.date_input("Tot", datetime.now())
    if st.button("Genereer", type="primary"):
        yuki_df = generate_flexible_export(start_date, end_date)
        if yuki_df is not None:
            st.success(f"{len(yuki_df)} regels.")
            st.dataframe(yuki_df, hide_index=True)
            # UTF-8-SIG voor Excel compatibiliteit
            csv = yuki_df.to_csv(sep=';', index=False).encode('utf-8-sig')
            st.download_button("Download", csv, "export.csv", "text/csv")
        else: st.warning("Geen data.")

elif app_mode == "Export Configuratie":
    st.header("📤 Export Configuratie")
    current_export_config = load_export_config()
    source_options = ["Vast", "Veld"]
    internal_fields = ["Datum", "Omschrijving", "Bedrag", "Grootboekrekening", "BtwCode", "Label"]
    edited_export = st.data_editor(current_export_config, column_config={"Kolom": st.column_config.TextColumn("CSV Kolom", required=True), "Bron": st.column_config.SelectboxColumn("Type", options=source_options), "Waarde": st.column_config.TextColumn("Waarde")}, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("💾 Opslaan", type="primary"):
        save_dataframe_to_sheet(edited_export, "ExportConfig")
        st.success("Opgeslagen!")

elif app_mode == "Instellingen":
    st.header("⚙️ Rekeningen & Omschrijvingen")
    st.info("Gebruik &datum&, &label& of &notitie& in de tekst.")
    current_settings = load_settings()
    
    edited_settings = st.data_editor(
        current_settings, 
        column_config={
            "Code": None, 
            "Label": st.column_config.TextColumn("Type", disabled=True),
            "Rekening": st.column_config.TextColumn("Yuki Rekening"),
            "ExportDesc": st.column_config.TextColumn("Export Omschrijving"),
            "BtwCode": st.column_config.TextColumn("BTW Code"),
            "Type": None
        },
        hide_index=True, use_container_width=True, num_rows="fixed"
    )
    
    if st.button("Opslaan", type="primary"):
        save_dataframe_to_sheet(edited_settings, "Instellingen")
        st.success("Opgeslagen!")
