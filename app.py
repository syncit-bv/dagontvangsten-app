import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import time
import os
import locale
import calendar
import json

# Probeer NL instellingen
try: locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
except: pass

# --- CONFIGURATIE ---
DATA_FILE = "kassa_historiek.csv"
SETTINGS_FILE = "kassa_settings.csv"
CONFIG_FILE = "kassa_config.json"
ADMIN_PASSWORD = "Yuki2025!" 

st.set_page_config(page_title="Dagontvangsten App", page_icon="💶", layout="centered")

# CSS Styling
st.markdown("""
    <style>
    .block-container { padding-top: 3rem; padding-bottom: 2rem; }
    [data-testid="stDataFrameResizable"] { border: 1px solid #ddd; border-radius: 5px; }
    .stAlert { margin-top: 1rem; }
    div.stButton > button { width: 100%; }
    
    .saldo-box {
        padding: 15px;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 5px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTIES: CONFIGURATIE ---

def load_config():
    default_config = {"start_saldo": 0.0, "laatste_update": str(datetime.now().date())}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return default_config

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

# --- FUNCTIES: INSTELLINGEN ---

def get_default_settings():
    return [
        {"Code": "Omzet_21",   "Label": "Omzet 21%",       "Rekening": "700021", "BtwCode": "V21", "Type": "Credit"},
        {"Code": "Omzet_12",   "Label": "Omzet 12%",       "Rekening": "700012", "BtwCode": "V12", "Type": "Credit"},
        {"Code": "Omzet_6",    "Label": "Omzet 6%",        "Rekening": "700006", "BtwCode": "V6",  "Type": "Credit"},
        {"Code": "Omzet_0",    "Label": "Omzet 0%",        "Rekening": "700000", "BtwCode": "V0",  "Type": "Credit"},
        {"Code": "Kas",        "Label": "Kas (Cash)",      "Rekening": "570000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Bancontact", "Label": "Bancontact",      "Rekening": "580000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Payconiq",   "Label": "Payconiq",        "Rekening": "580000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Oversch",    "Label": "Overschrijving",  "Rekening": "580000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Bonnen",     "Label": "Cadeaubonnen",    "Rekening": "440000", "BtwCode": "",    "Type": "Debet"},
        {"Code": "Afstorting", "Label": "Afstorting Bank", "Rekening": "550000", "BtwCode": "",    "Type": "Credit"},
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

# --- FUNCTIES: DATA ---

def load_database():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = df.fillna("") 
        if "Geld_Overschrijving" not in df.columns: df["Geld_Overschrijving"] = 0.0
        if "Geld_Afstorting" not in df.columns: df["Geld_Afstorting"] = 0.0
        return df
    else:
        cols = [
            "Datum", "Omschrijving", "Totaal_Omzet", "Totaal_Geld", "Verschil",
            "Omzet_0", "Omzet_6", "Omzet_12", "Omzet_21",
            "Geld_Bancontact", "Geld_Cash", "Geld_Payconiq", 
            "Geld_Overschrijving", "Geld_Bonnen", "Geld_Afstorting",
            "Timestamp"
        ]
        return pd.DataFrame(columns=cols)

def get_data_by_date(datum_obj):
    df = load_database()
    match = df[df['Datum'] == str(datum_obj)]
    return match.iloc[0] if not match.empty else None

def calculate_current_saldo(target_date):
    config = load_config()
    start_saldo = float(config.get("start_saldo", 0.0))
    df = load_database()
    if df.empty: return start_saldo
    
    df['DatumDT'] = pd.to_datetime(df['Datum'])
    target_dt = pd.to_datetime(target_date)
    history = df[df['DatumDT'] < target_dt]
    
    total_cash_in = history['Geld_Cash'].sum()
    total_cash_out = history['Geld_Afstorting'].sum()
    
    return start_saldo + total_cash_in - total_cash_out

def save_transaction(datum, omschrijving, df_input, totaal_omzet, totaal_geld, verschil):
    df_db = load_database()
    datum_str = str(datum)
    df_db = df_db[df_db['Datum'] != datum_str]
    
    if df_input is None:
        df_input = pd.DataFrame(columns=['Label', 'Bedrag'])

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
        "Geld_Bancontact": 0.0, "Geld_Cash": 0.0, "Geld_Payconiq": 0.0, 
        "Geld_Overschrijving": 0.0, "Geld_Bonnen": 0.0, "Geld_Afstorting": 0.0
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

def generate_yuki_export(start_date, end_date):
    df = load_database()
    mask = (df['Datum'] >= str(start_date)) & (df['Datum'] <= str(end_date))
    selection = df.loc[mask]
    if selection.empty: return None
    CODES = get_yuki_mapping() 
    yuki_rows = []
    for index, row in selection.iterrows():
        if row['Totaal_Omzet'] == 0 and row['Totaal_Geld'] == 0: continue

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
        if row['Geld_Overschrijving'] > 0: yuki_rows.append([datum_fmt, CODES.get("Oversch", "580000"), "Ontvangst Overschr.", f"{row['Geld_Overschrijving']:.2f}".replace('.',','), ""])
        if row['Geld_Bonnen'] > 0: yuki_rows.append([datum_fmt, CODES.get("Bonnen", "440000"), "Ontvangst Bonnen", f"{row['Geld_Bonnen']:.2f}".replace('.',','), ""])
        
        if row['Geld_Afstorting'] > 0:
             yuki_rows.append([datum_fmt, CODES.get("Kas", "570000"), "Afstorting naar Bank", f"{-row['Geld_Afstorting']:.2f}".replace('.',','), ""])
             yuki_rows.append([datum_fmt, CODES.get("Afstorting", "550000"), "Afstorting naar Bank", f"{row['Geld_Afstorting']:.2f}".replace('.',','), ""])

    return pd.DataFrame(yuki_rows, columns=["Datum", "Grootboekrekening", "Omschrijving", "Bedrag", "BtwCode"])

# --- STATE MANAGEMENT (FIXED: Single Source of Truth) ---
if 'reset_count' not in st.session_state: st.session_state.reset_count = 0
if 'show_success_toast' not in st.session_state: st.session_state['show_success_toast'] = False

# We gebruiken enkel date_picker_val als de waarheid.
if 'date_picker_val' not in st.session_state:
    st.session_state.date_picker_val = datetime.now().date()

# Navigatie functies manipuleren DIRECT de state van de widget
def prev_day(): 
    st.session_state.date_picker_val -= timedelta(days=1)

def next_day(): 
    if st.session_state.date_picker_val < datetime.now().date():
        st.session_state.date_picker_val += timedelta(days=1)

# ==========================================
# ⚙️ SIDEBAR
# ==========================================
with st.sidebar:
    st.header("⚙️ Menu")
    pwd = st.text_input("Boekhouder Login", type="password", placeholder="Wachtwoord")
    is_admin = (pwd == ADMIN_PASSWORD)
    app_mode = "Invoer" 
    
    if is_admin:
        st.success("🔓 Admin Toegang")
        app_mode = st.radio("Kies scherm:", ["Invoer", "Export (Yuki)", "Instellingen", "Kassaldo Beheer"])
        st.divider()
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, "rb") as f:
                st.download_button("📥 Backup (.csv)", f, "backup_db.csv", "text/csv")
    st.divider()
    
    if app_mode == "Invoer":
        st.subheader("Profiel & Sector")
        sector_keuze = st.selectbox("Sector:", ["Detailhandel", "Medisch", "Tandarts", "Horeca", "Bakkerij"])
        
        def_0, def_6, def_12, def_21 = True, True, False, True 
        if "Medisch" in sector_keuze: def_0, def_6, def_12, def_21 = True, False, False, False
        elif "Tandarts" in sector_keuze: def_0, def_6, def_12, def_21 = True, False, False, True
        elif "Horeca" in sector_keuze: def_0, def_6, def_12, def_21 = False, False, True, True
        elif "Bakkerij" in sector_keuze: def_0, def_6, def_12, def_21 = False, True, False, True

        st.caption("BTW")
        use_0  = st.checkbox("0% (Vrijgesteld)", value=def_0)
        use_6  = st.checkbox("6%", value=def_6)
        use_12 = st.checkbox("12%", value=def_12)
        use_21 = st.checkbox("21%", value=def_21)
        st.caption("Betaalwijzen")
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
        st.toast("Succesvol opgeslagen!", icon="✅")
        st.session_state['show_success_toast'] = False

    # Huidige datum uit state halen
    datum_geselecteerd = st.session_state.date_picker_val

    # MAAND OVERZICHT
    with st.expander("📅 Status Maandoverzicht", expanded=False):
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
                if omzet_val == 0 and geld_val == 0:
                    status_txt = "💤"
                else:
                    status_txt = "✅"
                    omzet = omzet_val
            elif d < date.today(): 
                status_txt = "❌"
            
            status_list.append({"Datum": d.strftime("%d-%m"), "Dag": d.strftime("%a"), "Status": status_txt, "Omzet": f"€ {omzet:.2f}" if omzet > 0 else "-"})
        st.dataframe(pd.DataFrame(status_list), hide_index=True, use_container_width=True)

    # --- DATUM & STATUS ---
    check_data = get_data_by_date(datum_geselecteerd)
    
    if check_data is not None:
        if float(check_data['Totaal_Omzet']) == 0 and float(check_data['Totaal_Geld']) == 0:
            status_icon, status_text, status_color = "💤", "Sluitingsdag", "blue"
        else:
            status_icon, status_text, status_color = "✅", "Reeds ingevuld", "green"
    elif datum_geselecteerd > datetime.now().date():
        status_icon, status_text, status_color = "🔒", "Toekomst", "grey"
    else:
        status_icon, status_text, status_color = "❌", "Nog in te vullen", "red"

    dag_naam = datum_geselecteerd.strftime("%A").upper()

    col_prev, col_pick, col_next = st.columns([1, 2, 1])
    with col_prev: st.button("⬅️ Vorige", on_click=prev_day, use_container_width=True)
    with col_pick:
        # HIER ZAT DE FOUT: value=... moet EXACT de key zijn.
        # We gebruiken de key 'date_picker_val' om de state te delen.
        st.date_input(
            "Datum", 
            value=st.session_state.date_picker_val, # Expliciet koppelen aan state
            max_value=datetime.now().date(), 
            label_visibility="collapsed", 
            key="date_picker_val" # Dezelfde key als in state
        )
        st.markdown(f"<div style='text-align: center; font-weight: bold; font-size: 1.1em;'>{dag_naam}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; color: {status_color}; font-size: 0.9em; margin-bottom: 10px;'>{status_icon} {status_text}</div>", unsafe_allow_html=True)
    with col_next:
        is_today = (datum_geselecteerd >= datetime.now().date())
        st.button("Volgende ➡️", on_click=next_day, disabled=is_today, use_container_width=True)

    st.divider()

    # --- SALDO ---
    openings_saldo = calculate_current_saldo(datum_geselecteerd)

    # --- INVOER ---
    if datum_geselecteerd > datetime.now().date():
        st.error("Toekomst geblokkeerd.")
    else:
        existing_data = get_data_by_date(datum_geselecteerd)
        is_overwrite_mode = existing_data is not None
        
        omschr_value = existing_data.get("Omschrijving", "") if is_overwrite_mode else ""
        omschrijving = st.text_input("Omschrijving", value=omschr_value, placeholder=f"Dagontvangsten {datum_geselecteerd.strftime('%d-%m-%Y')}", key=f"omschr_{datum_geselecteerd}")

        # HIER IS DE CHECKBOX VOOR INACTIVITEIT
        is_gesloten = st.checkbox("🚫 Zaak gesloten / Geen ontvangsten", value=False)
        
        if is_overwrite_mode and not is_gesloten:
            if float(existing_data['Totaal_Omzet']) == 0 and float(existing_data['Totaal_Geld']) == 0:
                is_gesloten = True

        if is_gesloten:
            st.info("Status: Gesloten")
            som_omzet, som_geld, verschil, cash_in_today, cash_out_today = 0.0, 0.0, 0.0, 0.0, 0.0
            edited_df = None 
            if not omschrijving: omschrijving = "SLUITINGSDAG"
        else:
            def get_val(col_name): return float(existing_data.get(col_name, 0.0)) if is_overwrite_mode else 0.00

            data_items = []
            if use_0:  data_items.append({"Label": "🎫 0% (Vrijgesteld)", "Bedrag": get_val("Omzet_0"), "Type": "Omzet"})
            if use_6:  data_items.append({"Label": "🎫 6% (Voeding)",     "Bedrag": get_val("Omzet_6"), "Type": "Omzet"})
            if use_12: data_items.append({"Label": "🎫 12% (Horeca)",     "Bedrag": get_val("Omzet_12"), "Type": "Omzet"})
            if use_21: data_items.append({"Label": "🎫 21% (Algemeen)",   "Bedrag": get_val("Omzet_21"), "Type": "Omzet"})

            data_items.append({"Label": "⬇️ --- BETAALWIJZEN --- ⬇️", "Bedrag": None, "Type": "Separator"})

            if use_bc:   data_items.append({"Label": "💳 Bancontact",     "Bedrag": get_val("Geld_Bancontact"), "Type": "Geld"})
            if use_cash: data_items.append({"Label": "💶 Cash (Lade)",    "Bedrag": get_val("Geld_Cash"), "Type": "Geld"})
            if use_payq: data_items.append({"Label": "📱 Payconiq",       "Bedrag": get_val("Geld_Payconiq"), "Type": "Geld"})
            if use_over: data_items.append({"Label": "🏦 Overschrijving", "Bedrag": get_val("Geld_Overschrijving"), "Type": "Geld"})
            if use_vouc: data_items.append({"Label": "🎁 Bonnen",         "Bedrag": get_val("Geld_Bonnen"), "Type": "Geld"})
            
            data_items.append({"Label": "⬇️ --- KAS UITGAVEN --- ⬇️", "Bedrag": None, "Type": "Separator"})
            data_items.append({"Label": "🏦 Afstorting naar Bank",    "Bedrag": get_val("Geld_Afstorting"), "Type": "Afstorting"})

            df_start = pd.DataFrame(data_items)
            
            edited_df = st.data_editor(
                df_start,
                column_config={
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
            if is_gesloten:
                st.info("Status: Gesloten")
            elif verschil == 0 and som_omzet > 0:
                st.success(f"✅ Balans OK: € {som_omzet:.2f}")
            elif som_omzet == 0:
                st.info("Nog in te vullen")
            else:
                st.error(f"❌ Verschil: € {verschil:.2f}")

        with c_rechts:
            st.markdown("#### 💰 Kassaldo")
            st.write(f"Begin: € {openings_saldo:.2f}")
            st.write(f"+ Cash: € {cash_in_today:.2f}")
            st.write(f"- Bank: € {cash_out_today:.2f}")
            st.markdown(f"**= Eind: € {eind_saldo:.2f}**")

        st.divider()
        
        overwrite_confirmed = True
        if is_overwrite_mode:
            overwrite_confirmed = st.checkbox("Ik wil wijzigingen opslaan", value=False)
            
        is_valid = ((som_omzet > 0 and verschil == 0) or is_gesloten) and overwrite_confirmed
        label = "🔄 Opslaan" if is_overwrite_mode else "💾 Opslaan"
        
        st.button(label, type="primary", disabled=not is_valid, use_container_width=True,
                  on_click=handle_save_click,
                  args=(datum_geselecteerd, omschrijving, edited_df, som_omzet, som_geld, verschil))

elif app_mode == "Kassaldo Beheer":
    st.header("💰 Kassaldo Beheer")
    st.info("Stel hier het initiële startsaldo in.")
    config = load_config()
    curr_start = config.get("start_saldo", 0.0)
    new_start = st.number_input("Startsaldo (Opening Kasboek)", value=float(curr_start), step=10.0, format="%.2f")
    if st.button("💾 Opslaan"):
        config["start_saldo"] = new_start
        save_config(config)
        st.success("Opgeslagen!")

elif app_mode == "Export (Yuki)":
    st.header("📤 Export Yuki")
    col_start, col_end = st.columns(2)
    start_date = col_start.date_input("Van", datetime(datetime.now().year, datetime.now().month, 1))
    end_date = col_end.date_input("Tot", datetime.now())
    if st.button("Genereer", type="primary"):
        yuki_df = generate_yuki_export(start_date, end_date)
        if yuki_df is not None:
            st.success(f"{len(yuki_df)} regels.")
            st.dataframe(yuki_df, hide_index=True)
            csv = yuki_df.to_csv(sep=';', index=False).encode('utf-8')
            st.download_button("Download", csv, "export.csv", "text/csv")
        else: st.warning("Geen data.")

elif app_mode == "Instellingen":
    st.header("⚙️ Rekeningen")
    current_settings = load_settings()
    edited_settings = st.data_editor(current_settings, hide_index=True, use_container_width=True, num_rows="fixed")
    if st.button("Opslaan", type="primary"):
        save_settings(edited_settings)
        st.success("Opgeslagen!")
