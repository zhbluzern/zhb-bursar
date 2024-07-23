import pandas as pd
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os

# .env file laden
load_dotenv()

# API-Schlüssel aus .env Datei laden
ALMA_API_KEY = os.getenv('api_key_prod')
input_file = 'Bursar-06-07-2024-Rechnungen-Sperren.xlsx'

# Excel-Datei laden
df = pd.read_excel(input_file)

# Funktion zum Erstellen der neuen user_note
def create_user_note(debitorennummer):
    return {
        "note_type": {
            "value": "REGISTAR",
            "desc": "Registrar"
        },
        "note_text": f"ZHB-SAP: {debitorennummer}",
        "user_viewable": "false",
        "popup_note": "false",
        "created_by": "lit@zhbluzern.ch",
        "created_date": datetime.now().isoformat(),
        "segment_type": "Internal"
    }

# Funktion zum Holen des Users aus der Alma API
def get_user(user_id):
    url = f"https://api-eu.hosted.exlibrisgroup.com/almaws/v1/users/{user_id}"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'apikey {ALMA_API_KEY}'
    }
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

# Funktion zum Aktualisieren des Users in der Alma API
def update_user(user_id, user_data):
    url = f"https://api-eu.hosted.exlibrisgroup.com/almaws/v1/users/{user_id}"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'apikey {ALMA_API_KEY}'
    }
    response = requests.put(url, headers=headers, data=json.dumps(user_data))
    return response.status_code

# Verarbeitung der Excel-Daten und API-Anfragen
for index, row in df.iterrows():
    user_id = row['UserID']
    if pd.isna(row['Debitorennummer']):
        # Wenn keine Rg.nr.: überspringe den Rest des Schleifendurchlaufs und gehe zur nächsten Zeile
        #print("Keine Debitorennummer!")
        continue

    debitorennummer = str(int(row['Debitorennummer']))
    
    user_data = get_user(user_id)
    if user_data:
        print(user_data['full_name'])
        if 'user_note' not in user_data:
            user_data['user_note'] = []
        existing_note  = None
        for note in user_data['user_note']:
            if note['note_type']['value'] == 'REGISTAR':
                existing_note = note
                break
        if existing_note:
            print(f"User {user_id} already has a REGISTAR note: {existing_note['note_text']}")                
        else:
            new_note = create_user_note(debitorennummer)
            user_data['user_note'].append(new_note)
            #status_code = update_user(user_id, user_data)
            status_code = "test" # TEST-MODUS
            if status_code == 200:
                print(f"User {user_id} successfully updated.")
            else:
                print(f"Failed to update user {user_id} with {debitorennummer}. Status code: {status_code}")
    else:
        print(f"User {user_id} not found.")

print("Processing complete.")
