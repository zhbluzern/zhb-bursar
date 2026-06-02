# zhb-bursar

# Bursar ZHB Closed after final reminder


## Ablauf des Python Scripts

Es gibt eine Eingabedatei von SLSP im Excel-Format. Das Python Script macht folgendes:

- Excel-Datei einlesen und in einem Dataframe speichern

- Spalte 'Grund Abzuege': nur Zeilen berücksichtigen, bei denen der Wert "Closed after final reminder" steht (filtern).

- Spalte 'UserID' gruppieren und die Spalte 'Fakturierter Betrag' pro Benutzer summieren. Summierten Betrag speichern in einer Variable 'Gesamtbetrag'.

- Pro UserID einen GET request auf die Alma user API abschicken und den user mittels der variable 'UserID' als primary_id im JSON-Format holen. User in einem JSON-Objekt speichern, Name und Vorname auslesen (Attribut 'first_name' und 'last_name')

- Bereich 'contact_info', 'address': Attribut "preferred": true berücksichtigen. Daten der preferred address in einzelne Spalten speichern: 'line1', 'line2', 'postal_code' 'city', 'country.value'

- prüfen ob bereits ein user_block mit block_type.value 'CASH' vorhanden ist. Wenn ja: Spalte "Frühere Sperren": block_note und created_date dieses user_blocks speichern, dasselbe für USER-Sperren (Falsche Adressen)

- Ist der Gesamtbetrag pro UserID 50.00 CHF oder höher: Aktion = "Rechnung". Ist der Gesamtbetrag kleiner als 50.00 CHF: Aktion = "Sperre"

- Bei Aktion Sperre: String nach folgendem Muster als Variable 'Sperrnotiz' basteln: 

    'Gesamtbetrag' CHF. Bitte an der Theke einkassieren und anschliessend Sperre entfernen, keine Ausleihe, bis Sperre gelöscht. Details: 'Fakturierter Betrag', 'Library code'/'Gebührentyp'/'Gebührendatum'", wiederhole dies für jeden Einzelbetrag dieser UserID.  

  Danach einen neuen (zusätzlichen) Block in folgender Struktur anlegen:

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


- Bei Aktion Rechnung: Benutzernotiz (user_note) "Rechnung 'gesamtbetrag' erstellt am..." anlegen

- Den angereicherten user mit einem PUT-request in Alma hochladen. (Wenn prod-Durchlauf auf 'True')



## Voraussetzungen für Python script:

Beachte bitte, dass du möglicherweise zusätzliche Bibliotheken installieren musst. Verwende 

        !pip install pandas requests openpyxl os datetime load_dotenv
        
um die benötigten Bibliotheken zu installieren.

Für die API-Keys wird ein .env file verwendet. Das File befindet sich im 1Password von LIT.

## Ausführen

Dateinamen anpassen: Variablen 'input_filename' und 'output_filename' müssen angepasst werden. Die Input-Datei muss im selben Verzeichnis liegen. Wenn das Original im CSV vorliegt, umwandeln in Excel. 
Bsp. 

```
input_filename = 'BURSAR_32505_01.07.2024.xlsx'
output_filename = 'Bursar-06-07-2024-Rechnungen-Sperren.xlsx'
```

Zunächst einen Testlauf machen (ohne Alma-Update) => im Script bei allgemeine Variablen:

```
  prod = 'False'
```

Skript ausführen:

```
python zhb-bursar-prod.py
```

Im Test-Modus wird nur die Ausgabedatei erstellt mit den Adressen (Alma-GET) sowie den zukünftigen Sperr- und Rechnungsnotizen. Ausgabedatei prüfen, wenn alles in Ordnung:
```
prod = "True"
```
Skript erneut ausführen => diesmal werden die Sperren und Rechnungsnotizen eingetragen. Am besten das Log als Datei speichern, z.B. so:
```
python zhb-bursar-prod.py > bursar-yyyy-mm-dd.log
```

Ausgabedatei nochmals prüfen, Filter setzen und vorfiltern auf "closed after final reminder", sortieren nach user id. 
Danach unbedingt(!) im Script wieder auf prod = 'False' setzen und die Dateinamen anonymisieren (Auskommentieren). So wird verhindert, dass das das Script versehentlich nochmals ausgeführt und alle Sperren doppelt eingetragen werden. 

## Rechnungsnummern nachtragen

Das Script "update-Rechnungsnummer.py" trägt nachträglich die in SAP erstellten Debitorennummern als Registrar-Notiz in Alma ein. Sie benötigt die überarbeitete Eingabedatei (von der Buchhaltung, nach Erstellung der Debitoren).

Aktualisierte Datei mit der Spalte Debitorennummer ausgefüllt herunterladen von Teams. 
Script 'update-rechnungsnummer.py' anpassen, Dateiname austauschen. Bsp. 
```
input_file = 'Bursar-06-07-2024-Rechnungen-Sperren.xlsx'
```
Danach zuerst einmal im Test-Modus durchlaufen lassen, um zu prüfen, ob alles korrekt verarbeitet wird. Dazu folgende Zeile aus bzw. einkommentieren: (ca. Zeile 80-81)
```
            #status_code = update_user(user_id, user_data)
           status_code = "test" # TEST-MODUS
```
Wenn der  Console output gut aussieht, obige beiden Zeilen umkommentieren und das Update laufen lassen. 
Wenn erfolgreich update gemacht, dann kurz in Alma prüfen, ob korrekt (Stichprobe). 
 
