# Voeg deze import bovenaan toe als je die nog niet hebt
from jinja2 import Environment, FileSystemLoader

# --- XML EXPORT ENGINE (TEMPLATE VERSIE) ---
def generate_xml_export(start_date, end_date):
    df_data = load_database()
    config = load_config()
    mask = (df_data['Datum'] >= str(start_date)) & (df_data['Datum'] <= str(end_date))
    selection = df_data.loc[mask].sort_values(by="Datum", ascending=True)
    if selection.empty: return None, None 
    
    my_iban = config.get("iban", "").replace(" ", "")
    coda_seq = int(config.get("coda_seq", 0))
    MAPPING = get_yuki_mapping()

    # Data voorbereiden voor de template
    statements_data = []
    
    # Startsaldo ophalen
    first_date = selection.iloc[0]['Datum']
    current_balance_val = calculate_current_saldo(first_date)

    # Loop door de dagen
    for index, row in selection.iterrows():
        if row['Totaal_Omzet'] == 0 and row['Totaal_Geld'] == 0: continue
        
        coda_seq += 1
        datum_iso = row['Datum']
        
        # 1. Transacties verzamelen
        transactions = []
        
        # Omzet
        totaal_omzet = float(row['Totaal_Omzet'])
        if totaal_omzet > 0:
             transactions.append({
                "amt": totaal_omzet, "sign": "CRDT", 
                "desc": f"Dagontvangsten {row['Omschrijving']}", 
                "dom": "PMNT", "fam": "RCDT", "sub": "ESCT"
            })

        # Uitgaven
        for col, code_key in [('Geld_Bancontact', 'Bancontact'), ('Geld_Payconiq', 'Payconiq'), 
                              ('Geld_Overschrijving', 'Oversch'), ('Geld_Bonnen', 'Bonnen'),
                              ('Geld_Afstorting', 'Afstorting')]:
            val = float(row[col])
            if val > 0:
                info = MAPPING.get(code_key, {})
                template_str = info.get('Template', '')
                label = info.get('Label', code_key)
                desc_text = template_str.replace("&datum&", datum_iso).replace("&notitie&", "")
                if not desc_text: desc_text = label
                
                transactions.append({
                    "amt": val, "sign": "DBIT", "desc": desc_text,
                    "dom": "PMNT", "fam": "ICDT", "sub": "ESCT"
                })
        
        # 2. Eindsaldo berekenen
        daily_movement = 0.0
        for t in transactions:
            if t['sign'] == "CRDT": daily_movement += t['amt']
            else: daily_movement -= t['amt']
            
        closing_balance_val = current_balance_val + daily_movement
        
        # 3. Dag toevoegen aan data-lijst
        statements_data.append({
            "id": f"{datetime.now().year}-{coda_seq}",
            "seq_nb": coda_seq,
            "date": datum_iso,
            "opening_balance": current_balance_val,
            "closing_balance": closing_balance_val,
            "entries": transactions
        })
        
        # Saldo doorschuiven
        current_balance_val = closing_balance_val

    # Update config
    config["coda_seq"] = coda_seq
    save_config(config)

    # 4. Template laden en invullen
    try:
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template('camt053_template.xml')
        
        context = {
            "msg_id": f"KASSA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "creation_datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "iban": my_iban,
            "statements": statements_data
        }
        
        full_xml_string = template.render(context)
        filename = f"CAMT053_{my_iban}_{datetime.now().strftime('%Y%m%d')}.xml"
        return full_xml_string, filename
        
    except Exception as e:
        st.error(f"Fout bij laden template: {e}")
        return None, None


# --- XML EXPORT ENGINE (CAMT.053) ---
# VERSIE: STRING BUILDER (Veiliger voor Yuki dan ElementTree)
def generate_xml_export(start_date, end_date):
    df_data = load_database()
    config = load_config()
    mask = (df_data['Datum'] >= str(start_date)) & (df_data['Datum'] <= str(end_date))
    selection = df_data.loc[mask].sort_values(by="Datum", ascending=True)
    if selection.empty: return None, None 
    
    my_iban = config.get("iban", "").replace(" ", "")
    coda_seq = int(config.get("coda_seq", 0))
    MAPPING = get_yuki_mapping()

    # We bouwen de XML op als een lange string om namespace problemen te vermijden
    xml_output = []
    
    # 1. DE HEADER (Exact zoals in het werkende v4 bestand)
    xml_output.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_output.append('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">')
    xml_output.append('  <BkToCstmrStmt>')
    
    # GrpHdr
    cre_dt_tm = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    msg_id = f"KASSA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    xml_output.append('    <GrpHdr>')
    xml_output.append(f'      <MsgId>{msg_id}</MsgId>')
    xml_output.append(f'      <CreDtTm>{cre_dt_tm}</CreDtTm>')
    xml_output.append('    </GrpHdr>')

    # Init balances
    first_date = selection.iloc[0]['Datum']
    current_balance_val = calculate_current_saldo(first_date)

    # Loop per dag
    for index, row in selection.iterrows():
        if row['Totaal_Omzet'] == 0 and row['Totaal_Geld'] == 0: continue
        
        coda_seq += 1
        datum_iso = row['Datum'] # YYYY-MM-DD
        
        # -----------------------------------------------------------
        # STAP 1: Berekeningen doen (nog niks schrijven)
        # -----------------------------------------------------------
        transactions = []
        
        # A. Omzet (Credit)
        totaal_omzet = float(row['Totaal_Omzet'])
        if totaal_omzet > 0:
             desc_full = f"Dagontvangsten {row['Omschrijving']}"
             transactions.append({
                "amt": totaal_omzet, "sign": "CRDT", "desc": desc_full, 
                "dom": "PMNT", "fam": "RCDT", "sub": "ESCT"
            })

        # B. Uitgaven (Debet)
        for col, code_key in [('Geld_Bancontact', 'Bancontact'), ('Geld_Payconiq', 'Payconiq'), 
                              ('Geld_Overschrijving', 'Oversch'), ('Geld_Bonnen', 'Bonnen'),
                              ('Geld_Afstorting', 'Afstorting')]:
            val = float(row[col])
            if val > 0:
                info = MAPPING.get(code_key, {})
                template = info.get('Template', '')
                label = info.get('Label', code_key)
                desc_text = template.replace("&datum&", datum_iso).replace("&notitie&", "")
                if not desc_text: desc_text = label
                
                transactions.append({
                    "amt": val, "sign": "DBIT", "desc": desc_text,
                    "dom": "PMNT", "fam": "ICDT", "sub": "ESCT"
                })
        
        # Bereken eindsaldo van deze dag
        daily_movement = 0.0
        for t in transactions:
            if t['sign'] == "CRDT": daily_movement += t['amt']
            else: daily_movement -= t['amt']
            
        closing_balance_val = current_balance_val + daily_movement

        # -----------------------------------------------------------
        # STAP 2: De Statement (Stmt) schrijven
        # -----------------------------------------------------------
        xml_output.append('    <Stmt>')
        xml_output.append(f'      <Id>{datetime.now().year}-{coda_seq}</Id>')
        xml_output.append(f'      <ElctrncSeqNb>{coda_seq}</ElctrncSeqNb>')
        xml_output.append(f'      <CreDtTm>{cre_dt_tm}</CreDtTm>')
        
        # Account
        xml_output.append('      <Acct>')
        xml_output.append('        <Id>')
        xml_output.append(f'          <IBAN>{my_iban}</IBAN>')
        xml_output.append('        </Id>')
        xml_output.append('        <Ccy>EUR</Ccy>')
        xml_output.append('      </Acct>')
        
        # --- OPENINGSSALDO (OPBD) ---
        sign_op = "CRDT" if current_balance_val >= 0 else "DBIT"
        xml_output.append('      <Bal>')
        xml_output.append('        <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>')
        xml_output.append(f'        <Amt Ccy="EUR">{abs(current_balance_val):.2f}</Amt>')
        xml_output.append(f'        <CdtDbtInd>{sign_op}</CdtDbtInd>')
        xml_output.append(f'        <Dt><Dt>{datum_iso}</Dt></Dt>')
        xml_output.append('      </Bal>')

        # --- EINDSALDO (CLBD) - MOET HIER STAAN! ---
        sign_cl = "CRDT" if closing_balance_val >= 0 else "DBIT"
        xml_output.append('      <Bal>')
        xml_output.append('        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>')
        xml_output.append(f'        <Amt Ccy="EUR">{abs(closing_balance_val):.2f}</Amt>')
        xml_output.append(f'        <CdtDbtInd>{sign_cl}</CdtDbtInd>')
        xml_output.append(f'        <Dt><Dt>{datum_iso}</Dt></Dt>')
        xml_output.append('      </Bal>')

        # --- TRANSACTIES (Ntry) ---
        for t in transactions:
            xml_output.append('      <Ntry>')
            xml_output.append(f'        <Amt Ccy="EUR">{t["amt"]:.2f}</Amt>')
            xml_output.append(f'        <CdtDbtInd>{t["sign"]}</CdtDbtInd>')
            xml_output.append('        <Sts>BOOK</Sts>')
            xml_output.append(f'        <BookgDt><Dt>{datum_iso}</Dt></BookgDt>')
            xml_output.append(f'        <ValDt><Dt>{datum_iso}</Dt></ValDt>')
            xml_output.append('        <BkTxCd>')
            xml_output.append('          <Domn>')
            xml_output.append(f'            <Cd>{t["dom"]}</Cd>')
            xml_output.append(f'            <Fmly><Cd>{t["fam"]}</Cd><SubFmlyCd>{t["sub"]}</SubFmlyCd></Fmly>')
            xml_output.append('          </Domn>')
            xml_output.append('        </BkTxCd>')
            xml_output.append('        <NtryDtls>')
            xml_output.append('          <TxDtls>')
            xml_output.append(f'            <RmtInf><Ustrd>{t["desc"]}</Ustrd></RmtInf>')
            xml_output.append('          </TxDtls>')
            xml_output.append('        </NtryDtls>')
            xml_output.append('      </Ntry>')
            
        xml_output.append('    </Stmt>')
        
        # Saldo doorzetten naar volgende dag
        current_balance_val = closing_balance_val

    # Update sequence en afsluiten
    config["coda_seq"] = coda_seq
    save_config(config)
    
    xml_output.append('  </BkToCstmrStmt>')
    xml_output.append('</Document>')
    
    # Alles samenvoegen tot 1 string
    full_xml_string = "\n".join(xml_output)
    filename = f"CAMT053_{my_iban}_{datetime.now().strftime('%Y%m%d')}.xml"
    
    return full_xml_string, filename
