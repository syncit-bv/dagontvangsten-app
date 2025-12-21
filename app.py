import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import time
import os
import locale
import calendar
import json
import random
from jinja2 import Environment, FileSystemLoader
import streamlit_shadcn_ui as ui

# Probeer NL instellingen
try:
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
except:
    pass

# --- CONFIGURATIE ---
DATA_FILE = "kassa_historiek.csv"
SETTINGS_FILE = "kassa_settings.csv"
EXPORT_CONFIG_FILE = "export_config.csv"
CONFIG_FILE = "kassa_config.json"
ADMIN_PASSWORD = "Yuki2025!"

st.set_page_config(page_title="Dagontvangsten Pro", page_icon="💶", layout="centered")

# --- FUNCTIES ---

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
        "iban": "",
        "coda_seq": 0,
        "laatste_update": str(datetime.now().date())
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            for key, value in default_config.items():
                if key not in data:
                    data[key] = value
            return data
    return default_config

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

def get_default_settings():
    return [
        {"Code": "Omzet_21",   "Label": "Omzet 21%",       "Rekening": "700021", "ExportDesc": "Omzet 21% (&notitie&) GL-700021", "BtwCode": "V21", "Type": "Credit"},
        {"Code": "Omzet_12",   "Label": "Omzet 12%",       "Rekening": "700012", "ExportDesc": "Omzet 12% (&notitie&) GL-700012", "BtwCode": "V12", "Type": "Credit"},
        {"Code": "Omzet_6",    "Label": "Omzet 6%",        "Rekening": "700006", "ExportDesc": "Omzet 6% (&notitie&) GL-700006",  "BtwCode": "V6",  "Type": "Credit"},
        {"Code": "Omzet_0",    "Label": "Omzet 0%",        "Rekening": "700000", "ExportDesc": "Omzet 0% (&notitie&) GL-700000",  "BtwCode": "V0",  "Type": "Credit"},
        {"Code": "Cash",       "Label": "Kas (Cash)",      "Rekening": "570000", "ExportDesc": "Ontvangst Cash GL-570000",        "BtwCode": "",    "Type": "Debet"},
        {"Code": "Bancontact", "Label": "Bancontact",      "Rekening": "580000", "ExportDesc": "Bancontact &datum& GL-580000",     "BtwCode": "",    "Type": "Debet"},
        {"Code": "Payconiq",   "Label": "Payconiq",        "Rekening": "580000", "ExportDesc": "Payconiq &datum& GL-580000",       "BtwCode": "",    "Type": "Debet"},
        {"Code": "Oversch",    "Label": "Overschrijving",  "Rekening": "580000", "ExportDesc": "Overschrijving &datum& GL-580000","BtwCode": "",    "Type": "Debet"},
        {"Code": "Bonnen",     "Label": "Cadeaubonnen",    "Rekening": "440000", "ExportDesc": "Cadeaubon &datum& GL-440000",      "BtwCode": "",    "Type": "Debet"},
        {"Code": "Afstorting", "Label": "Afstorting Bank", "Rekening": "550000", "ExportDesc": "Afstorting &datum& GL-550000",     "BtwCode": "",    "Type": "Credit"},
    ]

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        df = pd.read_csv(SETTINGS_FILE, dtype={"Rekening": str, "BtwCode": str})
        defaults = pd.DataFrame(get_default_settings())
        for code in defaults["Code"]:
            if code not in df["Code"].values:
                row = defaults[defaults["Code"] == code].iloc[0]
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        return df
    else:
        df = pd.DataFrame(get_default_settings())
        df["Rekening"] = df["Rekening"].astype(str)
        df.to_csv(SETTINGS_FILE, index=False)
        return df

def save_settings(df_settings):
    df_settings.to_csv(SETTINGS_FILE, index=False)

def get_yuki_mapping():
    df = load_settings()
    mapping = {}
    for _, row in df.iterrows():
        mapping[row['Code']] = {
            'Rekening': row['Rekening'],
            'Label': row['Label'],
            'Template': row.get('ExportDesc', row['Label'])
        }
    return mapping

def get_default_export_config():
    return pd.DataFrame([
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
    ])

def load_export_config():
    if os.path.exists(EXPORT_CONFIG_FILE):
        return pd.read_csv(EXPORT_CONFIG_FILE)
    else:
        df = get_default_export_config()
        df.to_csv(EXPORT_CONFIG_FILE, index=False)
        return df

def save_export_config(df):
    df.to_csv(EXPORT_CONFIG_FILE, index=False)

def load_database():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = df.fillna("")
        for col in ["Geld_Overschrijving", "Geld_Afstorting"]:
            if col not in df.columns:
                df[col] = 0.0
        return df
    else:
        cols = ["Datum", "Omschrijving", "Totaal_Omzet", "Totaal_Geld", "Verschil",
                "Omzet_0", "Omzet_6", "Omzet_12", "Omzet_21",
                "Geld_Bancontact", "Geld_Cash", "Geld_Payconiq", "Geld_Overschrijving",
                "Geld_Bonnen", "Geld_Afstorting", "Timestamp"]
        return pd.DataFrame(columns=cols)

def get_data_by_date(datum_obj):
    df = load_database()
    match = df[df['Datum'] == str(datum_obj)]
    return match.iloc[0] if not match.empty else None

def calculate_current_saldo(target_date):
    config = load_config()
    start = float(config.get("start_saldo", 0.0))
    df = load_database()
    if df.empty:
        return start
    df['DatumDT'] = pd.to_datetime(df['Datum'])
    hist = df[df['DatumDT'] < pd.to_datetime(target_date)]
    return start + hist['Geld_Cash'].sum() - hist['Geld_Afstorting'].sum()

def save_transaction(datum, omschrijving, df_input, totaal_omzet, totaal_geld, verschil):
    df_db = load_database()
    datum_str = str(datum)
    df_db = df_db[df_db['Datum'] != datum_str]

    if df_input is None:
        df_input = pd.DataFrame(columns=['Label', 'Bedrag'])
    if not omschrijving or str(omschrijving).strip() == "":
        omschrijving = f"Dagontvangsten {pd.to_datetime(datum).strftime('%d-%m-%Y')}"

    new_row = {
        "Datum": datum_str, "Omschrijving": omschrijving, "Totaal_Omzet": totaal_omzet,
        "Totaal_Geld": totaal_geld, "Verschil": verschil,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Omzet_0": 0.0, "Omzet_6": 0.0, "Omzet_12": 0.0, "Omzet_21": 0.0,
        "Geld_Bancontact": 0.0, "Geld_Cash": 0.0, "Geld_Payconiq": 0.0,
        "Geld_Overschrijving": 0.0, "Geld_Bonnen": 0.0, "Geld_Afstorting": 0.0
    }
    for _, row in df_input.iterrows():
        label = row['Label']
        bedrag = float(row['Bedrag'])
        if bedrag <= 0:
            continue
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
    if 'DatumDT' in df_db.columns:
        del df_db['DatumDT']
    df_db.to_csv(DATA_FILE, index=False)

def generate_csv_export(start_date, end_date):
    df_data = load_database()
    export_config = load_export_config()
    MAPPING = get_yuki_mapping()
    mask = (df_data['Datum'] >= str(start_date)) & (df_data['Datum'] <= str(end_date))
    selection = df_data.loc[mask].sort_values(by="Datum")
    if selection.empty:
        return None

    export_rows = []
    for _, row in selection.iterrows():
        if row['Totaal_Omzet'] == 0 and row['Totaal_Geld'] == 0:
            continue
        datum_fmt = pd.to_datetime(row['Datum']).strftime('%d-%m-%Y')
        desc_user = row['Omschrijving']

        transactions = []
        def add_trx(code_key, bedrag, btw):
            if bedrag <= 0:
                return
            info = MAPPING.get(code_key, {})
            final_desc = info.get('Template', '').replace("&datum&", datum_fmt).replace("&notitie&", desc_user)
            if not final_desc:
                final_desc = info.get('Label', code_key)
            transactions.append({"Rek": info.get('Rekening', ''), "Bedrag": -bedrag if code_key == "Afstorting" else bedrag, "Btw": btw, "Desc": final_desc, "Label": info.get('Label', '')})

        for code, col, btw in [("Omzet_21", "Omzet_21", "V21"), ("Omzet_12", "Omzet_12", "V12"), ("Omzet_6", "Omzet_6", "V6"), ("Omzet_0", "Omzet_0", "V0")]:
            if row[col] > 0:
                add_trx(code, row[col], btw)
        for code, col in [("Bancontact", "Geld_Bancontact"), ("Payconiq", "Geld_Payconiq"), ("Oversch", "Geld_Overschrijving"), ("Bonnen", "Geld_Bonnen"), ("Cash", "Geld_Cash")]:
            if row[col] > 0:
                add_trx(code, row[col], "")
        if row['Geld_Afstorting'] > 0:
            add_trx("Afstorting", row['Geld_Afstorting'], "")

        for t in transactions:
            export_row = {}
            for _, cfg in export_config.iterrows():
                col_name = cfg['Kolom']
                source = cfg['Bron']
                val_key = cfg['Waarde']
                val = ""
                if source == "Vast":
                    val = val_key
                elif source == "Veld":
                    if val_key == "Datum":
                        val = datum_fmt
                    elif val_key == "Omschrijving":
                        val = t['Desc']
                    elif val_key == "Label":
                        val = t['Label']
                    elif val_key == "Bedrag":
                        val = f"{t['Bedrag']:.2f}".replace('.', ',')
                    elif val_key == "Grootboekrekening":
                        val = t['Rek']
                    elif val_key == "BtwCode":
                        val = t['Btw']
                export_row[col_name] = val
            export_rows.append(export_row)
    return pd.DataFrame(export_rows)

def generate_xml_export(start_date, end_date):
    df_data = load_database()
    config = load_config()
    mask = (df_data['Datum'] >= str(start_date)) & (df_data['Datum'] <= str(end_date))
    selection = df_data.loc[mask].sort_values(by="Datum")
    if selection.empty:
        return None, None

    my_iban = config.get("iban", "").replace(" ", "")
    coda_seq = int(config.get("coda_seq", 0))
    MAPPING = get_yuki_mapping()

    statements_data = []
    current_balance_val = calculate_current_saldo(start_date)

    for _, row in selection.iterrows():
        if row['Totaal_Omzet'] == 0 and row['Totaal_Geld'] == 0:
            continue

        coda_seq += 1
        datum_iso = row['Datum']

        transactions = []

        if float(row['Totaal_Omzet']) > 0:
            transactions.append({
                "amt": float(row['Totaal_Omzet']), "sign": "CRDT",
                "desc": f"Dagontvangsten {row['Omschrijving']}",
                "dom": "PMNT", "fam": "RCDT", "sub": "ESCT"
            })

        for col, code_key in [('Geld_Bancontact', 'Bancontact'), ('Geld_Payconiq', 'Payconiq'),
                              ('Geld_Overschrijving', 'Oversch'), ('Geld_Bonnen', 'Bonnen'),
                              ('Geld_Afstorting', 'Afstorting')]:
            val = float(row[col])
            if val > 0:
                info = MAPPING.get(code_key, {})
                desc_text = info.get('Template', '').replace("&datum&", datum_iso).replace("&notitie&", row['Omschrijving'])
                if not desc_text:
                    desc_text = info.get('Label', code_key)
                transactions.append({
                    "amt": val, "sign": "DBIT",
                    "desc": desc_text,
                    "dom": "PMNT", "fam": "ICDT", "sub": "ESCT"
                })

        daily_movement = sum(t["amt"] if t["sign"] == "CRDT" else -t["amt"] for t in transactions)
        closing_balance_val = current_balance_val + daily_movement

        statements_data.append({
            "id": f"KASSA-{coda_seq:04d}",
            "seq_nb": coda_seq,
            "date": datum_iso,
            "opening_balance": current_balance_val,
            "closing_balance": closing_balance_val,
            "entries": transactions
        })

        current_balance_val = closing_balance_val

    config["coda_seq"] = coda_seq
    save_config(config)

    try:
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template('camt053_template.xml')
        context = {
            "msg_id": f"KASSA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "creation_datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "iban": my_iban,
            "statements": statements_data
        }
        xml_string = template.render(context)
        filename = f"CAMT053_{my_iban}_{datetime.now().strftime('%Y%m%d')}.xml"
        return xml_string, filename
    except Exception as e:
        st.error(f"Template fout: {e}")
        return None, None

# --- STATE ---
if 'reset_count' not in st.session_state:
    st.session_state.reset_count = 0
if 'date_picker_val' not in st.session_state:
    st.session_state.date_picker_val = date.today()

# ==========================================
# SIDEBAR MET SHADCN
# ==========================================
with st.sidebar:
    ui.badge("Dagontvangsten Pro", color="blue", variant="default", class_name="text-xl font-bold mb-4")
    st.caption("Beter dan Scrada — moderner, flexibeler")

    pwd = st.text_input("Admin wachtwoord", type="password", placeholder="Voor instellingen & export")
    is_admin = (pwd == ADMIN_PASSWORD)

    if is_admin:
        ui.badge("Admin ingelogd", color="green", variant="outline")
        tabs_options = ["Invoer", "Export (Yuki)", "Instellingen", "Export Config", "Kassaldo Beheer"]
        app_mode = ui.tabs(tabs_options, default_index=0, key="main_nav")
    else:
        st.info("Alleen invoer mogelijk zonder wachtwoord")
        app_mode = "Invoer"

# ==========================================
# HOOFDSCHERM
# ==========================================
selected_date = st.session_state.date_picker_val
existing_data = get_data_by_date(selected_date)
openings_saldo = calculate_current_saldo(selected_date)

if app_mode == "Invoer":
    ui.card(
        title=f"Dagafsluiting — {selected_date.strftime('%A %d %B %Y')}".capitalize(),
        description="Vul de ontvangsten en betalingen in",
        key="header_card"
    )

    col_prev, col_date, col_next = st.columns([1, 3, 1])
    with col_prev:
        if ui.button("⬅️ Vorige", key="prev_day", use_container_width=True):
            st.session_state.date_picker_val -= timedelta(days=1)
            st.rerun()
    with col_date:
        st.date_input("Kies datum", value=st.session_state.date_picker_val, max_value=date.today(),
                      key="date_picker_val", label_visibility="collapsed")
    with col_next:
        disabled = selected_date >= date.today()
        if ui.button("Volgende ➡️", key="next_day", disabled=disabled, use_container_width=True):
            st.session_state.date_picker_val += timedelta(days=1)
            st.rerun()

    st.divider()

    omschrijving = st.text_input("Notitie (optioneel)", value=existing_data["Omschrijving"] if existing_data is not None else "",
                                 placeholder=f"Dagontvangsten {selected_date.strftime('%d-%m-%Y')}")

    is_gesloten = st.checkbox("Zaak gesloten deze dag", value=(existing_data is not None and float(existing_data.get('Totaal_Omzet', 0)) == 0))

    if is_gesloten:
        ui.alert(title="Gesloten dag", description="Geen omzet of betalingen", variant="destructive")
        som_omzet = som_geld = verschil = 0.0
        cash_in = cash_out = 0.0
        edited_df = None
    else:
        sector = st.selectbox("Sector (voor BTW-presets)", ["Algemeen", "Horeca", "Medisch", "Tandarts", "Bakkerij"])
        btw_presets = {
            "Algemeen": (True, False, False, True),
            "Horeca": (False, False, True, True),
            "Medisch": (True, False, False, False),
            "Tandarts": (True, False, False, True),
            "Bakkerij": (False, True, False, True)
        }
        use_0, use_6, use_12, use_21 = btw_presets.get(sector, (True, True, True, True))

        items = []
        def add_item(label, col):
            val = float(existing_data[col]) if existing_data is not None else 0.0
            items.append({"Label": label, "Bedrag": val})

        if use_0: add_item("0% (Vrijgesteld)", "Omzet_0")
        if use_6: add_item("6% (Voeding)", "Omzet_6")
        if use_12: add_item("12% (Horeca)", "Omzet_12")
        if use_21: add_item("21% (Algemeen)", "Omzet_21")
        add_item("Bancontact", "Geld_Bancontact")
        add_item("Cash", "Geld_Cash")
        add_item("Payconiq", "Geld_Payconiq")
        add_item("Overschrijving", "Geld_Overschrijving")
        add_item("Cadeaubonnen", "Geld_Bonnen")
        add_item("Afstorting Bank", "Geld_Afstorting")

        df_start = pd.DataFrame(items)
        edited_df = ui.data_table(df_start, key=f"table_{selected_date}_{st.session_state.reset_count}")

        som_omzet = edited_df[edited_df["Label"].str.contains("Omzet|%")]["Bedrag"].sum()
        som_geld = edited_df[~edited_df["Label"].str.contains("Afstorting")]["Bedrag"].sum() - edited_df[edited_df["Label"].str.contains("Afstorting")]["Bedrag"].sum()
        verschil = round(som_omzet - (edited_df["Bedrag"].sum() - edited_df[edited_df["Label"].str.contains("Afstorting")]["Bedrag"].sum()), 2)
        cash_in = edited_df[edited_df["Label"] == "Cash"]["Bedrag"].sum()
        cash_out = edited_df[edited_df["Label"] == "Afstorting Bank"]["Bedrag"].sum()

    eind_saldo = openings_saldo + cash_in - cash_out

    col_left, col_right = st.columns(2)
    with col_left:
        ui.card(title="Dagcontrole", description=f"Omzet: €{som_omzet:.2f} | Verschil: €{verschil:.2f}",
                key="dagcontrole", class_name="h-32")
    with col_right:
        ui.card(title="Kassaldo", description=f"Begin: €{openings_saldo:.2f}\nEind: €{eind_saldo:.2f}",
                key="saldo", class_name="h-32")

    st.divider()

    overwrite_ok = existing_data is not None and st.checkbox("Ik wil bestaande dag overschrijven", value=False)
    save_disabled = not ((verschil == 0 and som_omzet > 0) or is_gesloten) or (existing_data is not None and not overwrite_ok)

    if ui.button("Opslaan dagafsluiting", type="primary", size="lg", disabled=save_disabled, use_container_width=True):
        save_transaction(selected_date, omschrijving, edited_df, som_omzet, som_geld, verschil)
        st.session_state.reset_count += 1
        ui.toast("Dag succesvol opgeslagen!", icon="✅", duration=4000)
        st.rerun()

# Andere tabs (Export, Instellingen, etc.) kunnen we later verder uitbreiden met shadcn — dit is al een sterke basis.

st.caption("© 2025 — Jouw concurrent voor Scrada")
