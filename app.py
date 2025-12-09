import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import time
import os
import locale
import calendar
import json
import random

# Probeer NL instellingen
try: locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
except: pass

# --- CONFIGURATIE ---
DATA_FILE = "kassa_historiek.csv"
SETTINGS_FILE = "kassa_settings.csv"
EXPORT_CONFIG_FILE = "export_config.csv"
CONFIG_FILE = "kassa_config.json"
ADMIN_PASSWORD = "Yuki2025!" 

st.set_page_config(page_title="Dagontvangsten App", page_icon="💶", layout="centered")

# --- CSS STYLING ---
st.markdown("""
    <style>
    /* Header transparant */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    .block-container { 
        padding-top: 3.5rem !important; 
        padding-bottom: 2rem; 
    }
    
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

def generate_valid_belgian_iban():
    protocol = "999" 
    random_part = "".join([str(random.randint(0, 9)) for _ in range(7)])
    base_num = int(protocol + random_part)
    remainder = base_num % 97
    check_digits = 97 if remainder == 0 else remainder
    bban = f"{protocol}{random_part}{check_digits:02d}"
    country_code_num = "111400" 
    iban_check_base = int(bban + country_code_num)
    iban_remainder = iban_check_base % 97
    iban_check = 98 - iban_remainder
    return f"BE{iban_check:02d}{bban}"

def load_config():
    default_config = {
        "start_saldo": 0.0, 
        "iban": "", # Standaard leeg, gebruiker moet invullen
        "bic": "KASSBE22",
        "coda_seq": 0,
        "laatste_update": str(datetime.now().date())
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: 
            data = json.load(f)
            if "iban" not in data: data["iban"] = default_config["iban"]
            if "bic" not in data: data["bic"] = default_config["bic"]
            if "coda_seq" not in data: data["coda_seq"] = 0
            return data
    return default_config

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f: json.dump(config_data, f)

def get_default_settings():
    return [
        {"Code": "Omzet_21",   "Label": "Omzet 21%",       "Rekening": "700021", "ExportDesc": "Omzet 21% (&notitie&) GL-700021", "BtwCode": "V21", "Type": "Credit"},
        {"Code": "Omzet_12",   "Label": "Omzet 12%",       "Rekening": "700012", "ExportDesc": "Omzet 12% (&notitie&) GL-700012", "BtwCode": "V12", "Type": "Credit"},
        {"Code": "Omzet_6",    "Label": "Omzet 6%",        "Rekening": "700006", "ExportDesc": "Omzet 6% (&notitie&) GL-700006",  "BtwCode": "V6",  "Type": "Credit"},
        {"Code": "Omzet_0",    "Label": "Omzet 0%",        "Rekening": "700000", "ExportDesc": "Omzet 0% (&notitie&) GL-700000",  "BtwCode": "V0",  "Type": "Credit"},
        {"Code": "Cash",       "Label": "Kas (Cash)",      "Rekening": "570000", "ExportDesc": "Ontvangst Cash GL-570000",        "BtwCode": "",    "Type": "Debet"},
        {"Code": "Bancontact", "Label": "Bancontact",      "Rekening": "580000", "ExportDesc": "Bancontact &datum& GL-580000",    "BtwCode": "",    "Type": "Debet"},
        {"Code": "Payconiq",   "Label": "Payconiq",        "Rekening": "580000", "ExportDesc": "Payconiq &datum& GL-580000",      "BtwCode": "",    "Type": "Debet"},
        {"Code": "Oversch",    "Label": "Overschrijving",  "Rekening": "580000", "ExportDesc": "Overschrijving &datum& GL-580000","BtwCode": "",    "Type": "Debet"},
        {"Code": "Bonnen",     "Label": "Cadeaubonnen",    "Rekening": "440000", "ExportDesc": "Cadeaubon &datum& GL-440000",     "BtwCode": "",    "Type": "Debet"},
        {"Code": "Afstorting", "Label": "Afstorting Bank", "Rekening": "550000", "ExportDesc": "Afstorting &datum& GL-550000",    "BtwCode": "",    "Type": "Credit"},
    ]

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        df = pd.read_csv(SETTINGS_FILE, dtype={"Rekening": str, "BtwCode": str})
        if "ExportDesc" not in df.columns:
            df["ExportDesc"] = df["Label"]
            df.to_csv(SETTINGS_FILE, index=False)
        if "Kas" in df["Code"].values:
            df.loc[df["Code"] == "Kas", "Code"] = "Cash"
            df.to_csv(SETTINGS_FILE, index=False)
        defaults = pd.DataFrame(get_default_settings())
        for code in ["Oversch", "Afstorting"]:
            if code not in df["Code"].values:
                row = defaults[defaults["Code"] == code].iloc[0]
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                df.to_csv(SETTINGS_FILE, index=False)
        return df
    else:
        df = pd.DataFrame(get_default_settings())
        df["Rekening"] = df["Rekening"].astype(str)
        df.to_csv(SETTINGS_FILE, index=False)
        return df

def save_settings(df_settings): df_settings.to_csv(SETTINGS_FILE, index=False)
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
    if os.path.exists(EXPORT_CONFIG_FILE):
        df = pd.read_csv(EXPORT_CONFIG_FILE)
        if "BTW Code" in df["Kolom"].values:
            df = df[df["Kolom"] != "BTW Code"]
            df.to_csv(EXPORT_CONFIG_FILE, index=False)
        return df
    else:
        df = pd.DataFrame(get_default_export_config())
        df.to_csv(EXPORT_CONFIG_FILE, index=False)
        return df

def save_export_config(df): df.to_csv(EXPORT_CONFIG_FILE, index=False)

# --- DATA ---
def load_database():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = df.fillna("") 
        for col in ["Geld_Overschrijving", "Geld_Afstorting"]:
            if col not in df.columns: df[col] = 0.0
        return df
    else:
        cols = ["Datum", "Omschrijving", "Totaal_Omzet", "Totaal_Geld", "Verschil", "Omzet_0", "Omzet_6", "Omzet_12", "Omzet_21", "Geld_Bancontact", "Geld_Cash", "Geld_Payconiq", "Geld_Overschrijving", "Geld_Bonnen", "Geld_Afstorting", "Timestamp"]
        return pd.DataFrame(columns=cols)

def get_data_by_date(datum_obj):
    df = load_database()
    match = df[df['Datum'] == str(datum_obj)]
    return match.iloc[0] if not match.empty else None

def calculate_current_saldo(target_date):
    config = load_config()
    start = float(config.get("start_saldo", 0.0))
    df = load_database()
    if df.empty: return start
    df['DatumDT'] = pd.to_datetime(df['Datum'])
    hist = df[df['DatumDT'] < pd.to_datetime(target_date)]
    return start + hist['Geld_Cash'].sum() - hist['Geld_Afstorting'].sum()

def save_transaction(datum, omschrijving, df_input, totaal_omzet, totaal_geld, verschil):
    df_db = load_database()
    datum_str = str(datum)
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
    df_db = pd.concat([df_db, new_entry_df], ignore_index=True)
    df_db = df_db.sort_values(by="Datum", ascending=False)
    if 'DatumDT' in df_db.columns: del df_db['DatumDT']
    df_db.to_csv(DATA_FILE, index=False)

def handle_save_click(datum, omschrijving, edited_df, som_omzet, som_geld, verschil):
    save_transaction(datum, omschrijving, edited_df, som_omzet, som_geld, verschil)
    st.session_state.reset_count += 1
    st.session_state.omschrijving = "" 
    st.session_state['show_success_toast'] = True

# --- EXPORT ENGINE (CSV) ---
def generate_csv_export(start_date, end_date):
    df_data = load_database()
    export_config = load_export_config()
    MAPPING = get_yuki_mapping() 
    
    mask = (df_data['Datum'] >= str(start_date)) & (df_data['Datum'] <= str(end_date))
    selection = df_data.loc[mask].sort_values(by="Datum", ascending=True)
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
            final_desc = template.replace("&datum&", datum_fmt).replace("&date&", datum_fmt).replace("&label&", label).replace("&notitie&", desc_user)
            if not final_desc: final_desc = f"{label} {datum_fmt}"
            transactions.append({"Rek": rekening, "Bedrag": bedrag, "Btw": btw, "Desc": final_desc, "Label": label})

        # ALLES POSITIEF BEHALVE AFSTORTING
        if row['Omzet_21'] > 0: add_trx("Omzet_21", row['Omzet_21'], "V21")
        if row['Omzet_12'] > 0: add_trx("Omzet_12", row['Omzet_12'], "V12")
        if row['Omzet_6'] > 0:  add_trx("Omzet_6",  row['Omzet_6'],  "V6")
        if row['Omzet_0'] > 0:  add_trx("Omzet_0",  row['Omzet_0'],  "V0")
        if row['Geld_Bancontact'] > 0:   add_trx("Bancontact", row['Geld_Bancontact'], "")
        if row['Geld_Payconiq'] > 0:     add_trx("Payconiq",   row['Geld_Payconiq'],   "")
        if row['Geld_Overschrijving'] > 0: add_trx("Oversch",  row['Geld_Overschrijving'], "")
        if row['Geld_Bonnen'] > 0:       add_trx("Bonnen",     row['Geld_Bonnen'],     "")
        if row['Geld_Cash'] > 0:         add_trx("Cash",       row['Geld_Cash'],       "")
        if row['Geld_Afstorting'] > 0:   add_trx("Afstorting", -row['Geld_Afstorting'], "")

        for t in transactions:
            export_row = {}
            for _, cfg in export_config.iterrows():
                col_name = cfg['Kolom']
                source = cfg['Bron']
                val_key = cfg['Waarde']
                final_val = ""
                if source == "Vast": final_val = val_key if val_key and str(val_key) != "nan" else ""
                elif source == "Veld":
                    if val_key == "Datum": final_val = datum_fmt
                    elif val_key == "Omschrijving": final_val = t['Desc']
                    elif val_key == "Label": final_val = t['Label']       
                    elif val_key == "Bedrag": final_val = f"{abs(t['Bedrag']):.2f}".replace('.',',') # POSITIEF in CSV
                    elif val_key == "Grootboekrekening": final_val = t['Rek']
                    elif val_key == "BtwCode": final_val = t['Btw']
                export_row[col_name] = final_val
            export_rows.append(export_row)
    return pd.DataFrame(export_rows)

# --- CODA EXPORT ENGINE ---
def generate_coda_export(start_date, end_date):
    df_data = load_database()
    config = load_config()
    mask = (df_data['Datum'] >= str(start_date)) & (df_data['Datum'] <= str(end_date))
    selection = df_data.loc[mask].sort_values(by="Datum", ascending=True)
    if selection.empty: return None, None 

    my_iban = config.get("iban", "").replace(" ", "")
    my_bic = config.get("bic", "KASSBE22")
    start_seq = int(config.get("coda_seq", 0)) + 1
    
    first_day_in_selection = selection.iloc[0]['Datum']
    current_balance = calculate_current_saldo(first_day_in_selection)
    
    coda_lines = []
    seq_nr = start_seq - 1
    
    total_debit = 0.0
    total_credit = 0.0
    record_count = 0
    
    MAPPING = get_yuki_mapping()

    for index, row in selection.iterrows():
        if row['Totaal_Omzet'] == 0 and row['Totaal_Geld'] == 0: continue
        
        seq_nr += 1
        datum_dt = pd.to_datetime(row['Datum'])
        datum_coda = datum_dt.strftime("%d%m%y") 
        
        transactions = []
        
        # Omzet (Credit = 0)
        totaal_omzet = row['Totaal_Omzet']
        if totaal_omzet > 0:
            transactions.append({"amount": totaal_omzet, "sign": "0", "desc": f"Dagontvangsten {row['Omschrijving']}"})
            total_credit += totaal_omzet

        # Betalingen (Debet = 1)
        for col, code_key in [('Geld_Bancontact', 'Bancontact'), ('Geld_Payconiq', 'Payconiq'), 
                          ('Geld_Overschrijving', 'Oversch'), ('Geld_Bonnen', 'Bonnen'),
                          ('Geld_Afstorting', 'Afstorting')]:
            val = row[col]
            if val > 0:
                info = MAPPING.get(code_key, {})
                template = info.get('Template', '')
                label = info.get('Label', code_key)
                
                desc_text = template.replace("&datum&", datum_dt.strftime('%d-%m-%Y')).replace("&notitie&", "")
                if not desc_text: desc_text = label
                
                transactions.append({"amount": val, "sign": "1", "desc": desc_text})
                total_debit += val

        daily_movement = 0
        for t in transactions:
            if t['sign'] == '0': daily_movement += t['amount'] 
            else: daily_movement -= t['amount']
            
        old_balance = current_balance
        new_balance = old_balance + daily_movement
        current_balance = new_balance

        # 0. HEADER
        line0 = f"0{seq_nr:04d}{datum_coda}{my_bic:<11}{my_iban:<34}{'':<67}2"
        coda_lines.append(line0.ljust(128)[:128])

        # 1. OLD BALANCE
        old_sign = "0" if old_balance >= 0 else "1"
        old_abs = abs(old_balance)
        line1 = f"10{seq_nr:04d}{my_iban:<37}{old_sign}{old_abs:015.3f}".replace(".", "") + f"{datum_coda}{'':<63}"
        coda_lines.append(line1.ljust(128)[:128])

        # 2. MOVEMENTS
        for trx in transactions:
            amount_str = f"{trx['amount']:015.3f}".replace(".", "")
            line21 = f"21{seq_nr:04d}0000{'':<21}{trx['sign']}{amount_str}{datum_coda}{'':<53}"
            coda_lines.append(line21.ljust(128)[:128])
            record_count += 1
            
            desc_short = trx['desc'][:53]
            line22 = f"22{seq_nr:04d}0000{'':<10}{desc_short:<53}{'':<53}" 
            coda_lines.append(line22.ljust(128)[:128])
            record_count += 1

        # 8. NEW BALANCE
        new_sign = "0" if new_balance >= 0 else "1"
        new_abs = abs(new_balance)
        line8 = f"80{seq_nr:04d}{my_iban:<37}{new_sign}{new_abs:015.3f}".replace(".", "") + f"{datum_coda}{'':<63}"
        coda_lines.append(line8.ljust(128)[:128])

    # 9. TRAILER
    str_debit = f"{total_debit:015.3f}".replace(".", "")
    str_credit = f"{total_credit:015.3f}".replace(".", "")
    line9 = f"9{'':<5}{record_count:06d}{str_debit}{str_credit}{'':<80}2"
    coda_lines.append(line9.ljust(128)[:128])
    
    config["coda_seq"] = seq_nr
    save_config(config)
    
    clean_iban = my_iban.replace(" ", "")
    filename = f"{clean_iban}_{datetime.now().year}-{start_seq:03d}_{datetime.now().year}-{seq_nr:03d}.cod"

    return "\r\n".join(coda_lines), filename

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
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, "rb") as f: st.download_button("📥 Backup", f, "backup.csv", "text/csv")
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
        st.toast("Opgeslagen!", icon="✅")
        st.session_state['show_success_toast'] = False
    
    datum_geselecteerd = st.session_state.date_picker_val
    
    # Header & Status
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

    # Invoer
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
    st.info("Stel hier het initiële startsaldo en de CODA gegevens in.")
    
    config = load_config()
    curr_start = config.get("start_saldo", 0.0)
    curr_iban = config.get("iban", "")
    curr_bic = config.get("bic", "KASSBE22")
    curr_seq = config.get("coda_seq", 0)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        new_start = st.number_input("Startsaldo (€)", value=float(curr_start), step=10.0, format="%.2f")
    with c2:
        new_bic = st.text_input("BIC Code", value=curr_bic)
    with c3:
        new_seq = st.number_input("Laatste Volgnummer", value=int(curr_seq), step=1)
    
    st.markdown("---")
    st.write(" **Virtuele IBAN (Kassa):**")
    
    # AANGEPAST: Tekstveld om manueel te plakken (ipv label)
    new_iban_input = st.text_input("IBAN (Kopieer exact uit Yuki)", value=curr_iban, help="Plak hier de IBAN die Yuki aan het kasboek heeft gegeven (bv. BE99...)")
    
    if st.button("Genereer Random IBAN (Niet aanbevolen)"):
        new_iban_input = generate_valid_belgian_iban()
        st.rerun()

    if st.button("💾 Opslaan Instellingen"):
        config["start_saldo"] = new_start
        config["bic"] = new_bic
        config["coda_seq"] = new_seq
        config["iban"] = new_iban_input # Opslaan van het tekstveld
        save_config(config)
        st.success("Opgeslagen!")

elif app_mode == "Export (Yuki)":
    st.header("📤 Export Yuki")
    col_start, col_end = st.columns(2)
    start_date = col_start.date_input("Van", datetime(datetime.now().year, datetime.now().month, 1))
    end_date = col_end.date_input("Tot", datetime.now())
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Genereer CSV (Import)", type="primary", use_container_width=True):
            yuki_df = generate_csv_export(start_date, end_date)
            if yuki_df is not None:
                st.success(f"{len(yuki_df)} regels.")
                csv = yuki_df.to_csv(sep=';', index=False).encode('utf-8-sig')
                st.download_button("Download CSV", csv, "export.csv", "text/csv")
            else: st.warning("Geen data.")
    with c2:
        if st.button("Genereer CODA (Bank)", type="secondary", use_container_width=True):
            coda_content, filename = generate_coda_export(start_date, end_date)
            if coda_content:
                st.success(f"CODA gegenereerd: {filename}")
                st.download_button("Download .COD", coda_content, filename, "text/plain")
            else:
                st.warning("Geen data.")

elif app_mode == "Export Configuratie":
    st.header("📤 Export Configuratie (CSV)")
    current_export_config = load_export_config()
    source_options = ["Vast", "Veld"]
    internal_fields = ["Datum", "Omschrijving", "Bedrag", "Grootboekrekening", "BtwCode", "Label"]
    edited_export = st.data_editor(current_export_config, column_config={"Kolom": st.column_config.TextColumn("CSV Kolom", required=True), "Bron": st.column_config.SelectboxColumn("Type", options=source_options), "Waarde": st.column_config.TextColumn("Waarde")}, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("💾 Opslaan", type="primary"):
        save_export_config(edited_export)
        st.success("Opgeslagen!")

elif app_mode == "Instellingen":
    st.header("⚙️ Rekeningen & Omschrijvingen")
    st.info("Gebruik &datum&, &label& of &notitie& in de tekst.")
    current_settings = load_settings()
    
    edited_settings = st.data_editor(
        current_settings, 
        column_order=["Rekening", "BtwCode", "Label", "ExportDesc"],
        column_config={
            "Code": None, 
            "Label": st.column_config.TextColumn("Label", required=True),
            "Rekening": st.column_config.TextColumn("Grootboekrekening", required=True),
            "ExportDesc": st.column_config.TextColumn("Omschrijving"),
            "BtwCode": st.column_config.TextColumn("BTW Code"),
            "Type": None
        },
        hide_index=True, use_container_width=True, num_rows="fixed"
    )
    
    if st.button("Opslaan", type="primary"):
        save_settings(edited_settings)
        st.success("Opgeslagen!")
