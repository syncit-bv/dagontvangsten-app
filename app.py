import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATIE ---
st.set_page_config(page_title="Kassa Grid", page_icon="⚡", layout="centered")

# --- INITIALISATIE DATA ---
# We maken de start-tabellen aan in het geheugen als ze er nog niet zijn
if 'df_omzet' not in st.session_state:
    # Tabelstructuur voor links
    data_omzet = {
        "Categorie": ["0% (Vrijgesteld)", "6%", "12%", "21%"],
        "Bedrag": [0.00, 0.00, 0.00, 0.00]
    }
    st.session_state.df_omzet = pd.DataFrame(data_omzet)

if 'df_geld' not in st.session_state:
    # Tabelstructuur voor rechts
    data_geld = {
        "Betaalwijze": ["Bancontact", "Cash", "Payconiq"],
        "Ontvangen": [0.00, 0.00, 0.00]
    }
    st.session_state.df_geld = pd.DataFrame(data_geld)

if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = 0

# Functie om alles te wissen na opslaan
def reset_data():
    st.session_state.df_omzet["Bedrag"] = 0.00
    st.session_state.df_geld["Ontvangen"] = 0.00
    st.session_state.omschrijving = ""
    st.session_state.reset_trigger += 1 # Forceer een herlading van de editors

# --- TITEL & DATUM ---
st.title("⚡ Snelle Invoer (Grid)")
st.caption("Klik op een bedrag, typ het getal en druk op ENTER om naar beneden te springen.")

c1, c2 = st.columns([1, 2])
with c1:
    datum = st.date_input("Datum", datetime.now())
with c2:
    omschrijving = st.text_input("Omschrijving", key="omschrijving")

st.markdown("---")

# --- DE GRIDS (DATA EDITORS) ---
col_links, col_rechts = st.columns(2)

with col_links:
    st.subheader("1. Omzet")
    # De data editor: num_rows="fixed" zorgt dat je geen regels kan toevoegen/wissen
    # key=... zorgt voor de state management
    edited_omzet = st.data_editor(
        st.session_state.df_omzet,
        column_config={
            "Categorie": st.column_config.TextColumn("BTW Tarief", disabled=True), # Read-only
            "Bedrag": st.column_config.NumberColumn(
                "Bedrag (€)", 
                min_value=0, 
                format="%.2f",
                required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key=f"editor_omzet_{st.session_state.reset_trigger}"
    )

with col_rechts:
    st.subheader("2. Betalingen")
    edited_geld = st.data_editor(
        st.session_state.df_geld,
        column_config={
            "Betaalwijze": st.column_config.TextColumn("Methode", disabled=True),
            "Ontvangen": st.column_config.NumberColumn(
                "Bedrag (€)", 
                min_value=0, 
                format="%.2f",
                required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key=f"editor_geld_{st.session_state.reset_trigger}"
    )

# --- BEREKENINGEN ---
# We trekken de totalen direct uit de bewerkte tabellen
totaal_omzet = edited_omzet["Bedrag"].sum()
totaal_betaald = edited_geld["Ontvangen"].sum()
verschil = round(totaal_omzet - totaal_betaald, 2)

# Voor het opslaan moeten we de specifieke waarden er weer uitvissen
# Dit is handig voor je latere export
vals_omzet = edited_omzet.set_index("Categorie")["Bedrag"]
vals_geld = edited_geld.set_index("Betaalwijze")["Ontvangen"]

st.markdown("---")

# --- STATUS & KNOP ---
c_tot1, c_tot2, c_stat = st.columns([1, 1, 2])

with c_tot1:
    st.metric("Totaal Ticket", f"€ {totaal_omzet:.2f}")
with c_tot2:
    st.metric("Totaal Geld", f"€ {totaal_betaald:.2f}")

with c_stat:
    is_valid = (totaal_omzet > 0) and (verschil == 0)
    
    if is_valid:
        st.success("✅ Klaar!")
        if st.button("💾 Opslaan & Reset", type="primary", use_container_width=True):
            # HIER KOMT DE SAVE LOGICA
            # Bijvoorbeeld:
            # save_row = {
            #    "Datum": datum,
            #    "Omzet_21": vals_omzet["21%"],
            #    "Cash": vals_geld["Cash"],
            #    ...
            # }
            
            st.toast("Succesvol opgeslagen!", icon="🎉")
            time.sleep(1)
            reset_data()
            st.rerun()
    else:
        if totaal_omzet == 0:
            st.info("Vul bedragen in...")
        else:
            st.error(f"❌ Verschil: € {verschil:.2f}")
            st.button("Correctie nodig", disabled=True, use_container_width=True)
