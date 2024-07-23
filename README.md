# zhb-bursar

# Bursar ZHB Closed after final reminder


## Workflow

Es gibt eine Eingabedatei von SLSP im Excel-Format. Vorgehen des Skripts:

- Excel-Datei einlesen und in einem Dataframe speichern

- Spalte 'Grund Abzuege': nur Zeilen berücksichtigen, bei denen der Wert "Closed after final reminder" steht (filtern).

- Spalte 'UserID' gruppieren und die Spalte 'Fakturierter Betrag' pro Benutzer summieren. 

- Summierten Betrag speichern in einer Variable 'Gesamtbetrag'.

- Pro UserID einen GET request auf die Alma user API abschicken und den user mittels der variable 'UserID' als primary_id im JSON-Format holen. Headers: 'Accept': 'application/json', 'Content-Type': 'application/json'. 

- user in einem JSON-Objekt speichern, Name und Vorname auslesen (Attribut 'first_name' und 'last_name')

- Bereich 'contact_info', 'address': Attribut "preferred": true berücksichtigen

- Daten der preferred address in einzelne Spalten speichern: 'line1', 'line2', 'postal_code' 'city', 'country.value'

- prüfen ob bereits ein user_block mit block_type.value 'CASH' vorhanden ist. Wenn ja: Spalte "Frühere Sperren": block_note und created_date dieses user_blocks speichern 
- dasselbe für USER-Sperren (Falsche Adressen)

- Ist der Gesamtbetrag pro UserID 50.00 CHF oder höher: Aktion = "Rechnung". Ist der Gesamtbetrag kleiner als 50.00 CHF: Aktion = "Sperre"

- Bei Aktion Sperre: String nach folgendem Muster als Variable 'Sperrnotiz' basteln: 

    'Gesamtbetrag' CHF. Bitte an der Theke einkassieren und anschliessend Sperre entfernen, keine Ausleihe, bis Sperre gelöscht. Details: 'Fakturierter Betrag', 'Library code'/'Gebührentyp'/'Gebührendatum'", wiederhole dies für jeden Einzelbetrag dieser UserID.  

- Einen neuen (zusätzlichen) Block in folgender Struktur anlegen:

  "user_block": [
    {
      "block_type": {
        "value": "CASH",
        "desc": "Cash"
      },
      "block_description": {
        "value": "05",
        "desc": "Unpaid bill"
      },
      "block_status": "ACTIVE",
      "block_note": "'Sperrnotiz'",
      "created_by": "lit@zhbluzern.ch",
      "created_date": "(aktuellet Timestamp ISO)",
      "segment_type": "Internal"
    }


- Bei Aktion Rechnung: Benutzernotiz (user_note) anlegen "Rechnung 'gesamtbetrag' erstellt am..." anlegen

- Den angereicherten user mit einem PUT-request in Alma hochladen. (Für prod-Durchlauf auf 'True' setzen)



## Voraussetzungen für Python script:

Beachte bitte, dass du möglicherweise zusätzliche Bibliotheken installieren musst. Verwende 

        !pip install pandas requests openpyxl os datetime load_dotenv
        
um die benötigten Bibliotheken zu installieren.

Für die API-Keys wird ein .env file verwendet. 

Dateinamen anpassen: Variablen 'input_filename' und 'output_filename' müssen angepasst werden. Die Input-Datei muss im selben Verzeichnis liegen. 

Skript ausführen:

```
python zhb-bursar-prod.py
```

## Rechnungsnummern nachtragen

Das Script "update-Rechnungsnummer.py" trägt nachträglich die in SAP erstellten Debitorennummern als Registrar-Notiz in Alma ein. Sie benötigt die überarbeitete Eingabedatei (von der Buchhaltung, nach Erstellung der Debitoren).
 
