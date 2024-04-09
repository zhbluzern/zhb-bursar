import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

# Api key
load_dotenv()
api_key = os.getenv('api_key_prod')
counter = 0
countersperren = 0
counterrechnung = 0
prod = 'True' # Durchlauf ohne Alma-Update: False, mit Update: True

# 1. Lies die Eingabedatei 
input_filename = 'Bursar_15608_01.04.2024.xlsx'
df = pd.read_excel(input_filename)  

# 2. Filtere Zeilen, bei denen 'Grund Abzuege' gleich 'Closed after final reminder' ist
filtered_df = df[df['Grund Abzuege'] == 'Closed after final reminder']


# 3. Iteriere über die verbleibenden Zeilen
for user_id, user_group in filtered_df.groupby('UserID'):
    
    
    counter+= 1
    print("\n", counter)
    
    # 4. Hole den user mit der UserID als primary_id im JSON-Format    
    alma_api_url = f'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/users/{user_id}?apikey={api_key}'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.get(alma_api_url, headers=headers)

    # Überprüfe, ob die Anfrage erfolgreich war, bevor du versuchst, JSON zu decodieren
    if response.status_code == 200:
        print("Abfrage erfolgreich", user_id)
        user_data = response.json()

        # 5. Hole den vollen Namen und schreibe ihn in die Eingabedatei
        first_name = user_data.get('first_name', '')
        df.loc[df['UserID'] == user_id, 'Vorname'] = first_name
        last_name = user_data.get('last_name', '')
        df.loc[df['UserID'] == user_id, 'Nachname'] = last_name
        print(first_name, last_name)

        # 6. Hole die bevorzugte Adresse aus dem JSON-Objekt
        preferred_address = next((address for address in user_data.get('contact_info', {}).get('address', []) if address.get('preferred')), None)

        if preferred_address:
            address = preferred_address.get('line1', '')
            address2 = preferred_address.get('line2', '')
            postal_code = preferred_address.get('postal_code', '')
            city = preferred_address.get('city', '')
            country = preferred_address.get('country', {}).get('value', '')
            df.loc[df['UserID'] == user_id, 'Adresse'] = address
            df.loc[df['UserID'] == user_id, 'Adresse2'] = address2
            df.loc[df['UserID'] == user_id, 'PLZ'] = postal_code
            df.loc[df['UserID'] == user_id, 'Ort'] = city
            df.loc[df['UserID'] == user_id, 'Land'] = country
            print(address, address2, postal_code, city, country)
        else:
            print("Keine bevorzugte Adresse vorhanden")
            df.loc[df['UserID'] == user_id, 'Adresse'] = ''
            df.loc[df['UserID'] == user_id, 'Adresse2'] = ''
            df.loc[df['UserID'] == user_id, 'PLZ'] = ''
            df.loc[df['UserID'] == user_id, 'Ort'] = ''
            df.loc[df['UserID'] == user_id, 'Land'] = ''
            
        # 7. Überprüfe, ob bereits ein user_block mit block_type.value 'CASH' vorhanden ist, oder eine Debitorennummer
        user_blocks = user_data.get('user_block', [])
        cash_block = next((block for block in user_blocks if block.get('block_type', {}).get('value') == 'CASH'), None)
        user_block = next((block for block in user_blocks if block.get('block_type', {}).get('value') == 'USER'), None)
        user_notes = user_data.get('user_note', [])
        registrar_note = next((note for note in user_notes if note.get('note_type', {}).get('value') == 'REGISTAR'), None)

        if cash_block:
            # Schreibe Informationen zu vorherigem cash_block in die Eingabedatei
            sperrmeldung = f"{cash_block.get('block_note', '')}, created {cash_block.get('created_date', '')} by {cash_block.get('created_by','')}"
            print(sperrmeldung)
            df.loc[df['UserID'] == user_id, 'Alte CASH-Sperren'] = sperrmeldung
            
        if user_block:
            # Schreibe Informationen zu vorherigem user_block in die Eingabedatei
            wrongaddress = f"{user_block.get('block_note', '')}, created {user_block.get('created_date', '')} by {user_block.get('created_by','')}"
            print(wrongaddress)
            df.loc[df['UserID'] == user_id, 'Adresssperre'] = wrongaddress

        if registrar_note:
            # schreibe Debitorennummer in Ausgabedatei
            debitorennummer = registrar_note.get('note_text','')
            print(debitorennummer)
            df.loc[df['UserID'] == user_id, 'Debitorennummer'] = debitorennummer[9:] #cut ZHB-SAP: 
        
        # 8. Berechne den Gesamtbetrag und Aktion basierend auf dem Gesamtbetrag
        gesamtbetrag = user_group['Fakturierter Betrag'].sum()
        df.loc[df['UserID'] == user_id, 'Gesamtbetrag'] = gesamtbetrag
        print("Gesamtbetrag:", gesamtbetrag)

        if gesamtbetrag >= 50.00:
            aktion = 'Rechnung'
            counterrechnung += 1
        else:
            aktion = 'Sperre'
            countersperren += 1
        
        df.loc[df['UserID'] == user_id, 'Aktion'] = aktion
        print("Aktion:", aktion)


        # 9. Aktion Sperre: bilde den String für die Sperrnotiz
        if aktion == 'Sperre':
            sperrnotiz = f"Total {gesamtbetrag} CHF. Bitte an der Theke einkassieren und anschliessend Sperre entfernen, keine Ausleihe, bis Sperre gelöscht. Details: "
            sperrnotiz += ' / '.join([f"{betrag} CHF {library_code} {gebuehrentyp} {gebuehrendatum.strftime('%d-%m-%Y')}" for _, (betrag, library_code, gebuehrentyp, gebuehrendatum) in user_group[['Fakturierter Betrag', 'Library Code', 'Gebührentyp', 'Gebührendatum']].iterrows()])
            df.loc[df['UserID'] == user_id, 'Neue Notiz / Sperre'] = sperrnotiz
            print(sperrnotiz)

            # Erstelle einen neuen user_block mit Sperrnotiz
            new_block = {
                "block_type": {"value": "CASH", "desc": "Cash"},
                "block_description": {"value": "05", "desc": "Unpaid bill"},
                "block_status": "ACTIVE",
                "block_note": sperrnotiz,
                "created_by": "lit@zhbluzern.ch",
                "created_date": datetime.now().isoformat(),
                "segment_type": "Internal"
            }

            user_blocks.append(new_block)
            user_data['user_block'] = user_blocks

        # 10. Aktion Rechnung: erstelle eine Nutzernotiz
        if aktion == 'Rechnung':
            rechnungsnotiz = f'ZHB-SAP: Rechnung über Gesamtbetrag von {gesamtbetrag} CHF erstellt am ' + datetime.now().strftime('%d-%m-%Y')
            new_note = {
              "note_type": {
                "value": "OTHER",
                "desc": "Other"
              },
              "note_text": rechnungsnotiz,
              "user_viewable": "false",
              "popup_note": "false",
              "created_by": "lit@zhbluzern.ch",
              "created_date": datetime.now().isoformat(),
              "segment_type": "Internal"
            }
            df.loc[df['UserID'] == user_id, 'Neue Notiz / Sperre'] = rechnungsnotiz
            print(rechnungsnotiz)            
            
            user_notes.append(new_note)
            user_data['user_note'] = user_notes
        
        # 12: update user: lade den angereicherten Benutzer mit einem PUT-Request in Alma hoch
        alma_update = 'no update'
        if prod == 'True':
            put_response = requests.put(alma_api_url, json=user_data, headers=headers)
            if put_response.status_code == 200:
                print(f"Benutzer {user_id} aktualisiert. Statuscode: {put_response.status_code}")
                alma_update = 'success'
            else:
                print("Benutzerupdate failed:", put_response.content)
                alma_update = 'failed'
        df.loc[df['UserID'] == user_id, 'Alma update'] = alma_update
    else:
        fehlermeldung = f"Fehler bei der API-Anfrage für Benutzer {user_id}. Statuscode: {response.status_code}"
        df.loc[df['UserID'] == user_id, 'Fehlermeldung'] = fehlermeldung
        print(fehlermeldung)

# 13. Speichere die aktualisierte Eingabedatei
output_filename = 'Bursar-09-04-2024-Rechnungen-Sperren.xlsx'
df.to_excel(output_filename, index=False)
print(f'-------------------------------\n\n\nAktualisierte Eingabedatei wurde unter "{output_filename}" gespeichert.')
print("Anzahl Rechnungen: ",counterrechnung)
print("Anzahl Sperren: ",countersperren)
print("Total Aktionen: ",counter)
