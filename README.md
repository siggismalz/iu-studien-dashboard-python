# Studien-Dashboard

Python-Prototyp für den Kurs DLBDSOOFPP01_D. Die Einträge werden lokal in SQLite gespeichert.

## Start

1. Python 3.12 oder neuer installieren und den Programmordner entpacken.
2. Dort ein Terminal öffnen und `python app.py` ausführen; alternativ `py app.py`.
3. Im Browser `http://127.0.0.1:8000` öffnen. Beenden im Terminal mit `Strg+C`.

Zusätzliche Python-Pakete werden nicht benötigt. Beim ersten Start legt das Programm
`studium.sqlite3` mit erfundenen Beispieldaten an. Änderungen bleiben nach einem Neustart erhalten.
Für eine getrennte Datenbank oder einen anderen Port:
`python app.py --datenbank versuch.sqlite3 --port 8001`.

## Beispiel und Tests

Am Stichtag **01.10.2026** ergeben die Beispieldaten 20 von 180 ECTS,
ein Soll von 30 ECTS und damit -10 ECTS Abweichung. Der Schnitt beträgt
`(5 × 1,0 + 10 × 3,0) / 15 = 2,33`. Die unbenoteten 5 ECTS zählen nur zum Fortschritt.

Über **Bearbeiten** lässt sich ein Modulergebnis ändern. Unter **Studium verwalten**
können Module, Semester, Ziele und der Abschluss bearbeitet werden.
Mit `python test_dashboard.py` lassen sich die ausgewählten Beispiele prüfen.
Die Tests verwenden eigene temporäre Datenbanken und verändern die gespeicherten Einträge nicht.

## Dateien

- `app.py`: Application verbindet die Klassen und startet den lokalen HTTPServer.
- `modell.py`: Studiengang, Module, Prüfungen, Ziele und ihre Berechnungen.
- `repository.py`: Studiengang laden und mit `speichern(studium)` ablegen.
- `controller.py`: Formulare prüfen und Änderungen ausführen.
- `view.py`: HTML-Seite und Eingabeformulare erzeugen.
- `beispieldaten.py`: Daten für den ersten Start.
- `test_dashboard.py`: Berechnung, Speicherung und ausgewählte Fehlerfälle prüfen.

## Grenzen

Es gibt einen Studiengang pro Datenbank und nur das aktuelle Ergebnis je Modul.
Frühere Prüfungsversuche werden nicht aufbewahrt. Der Notenschnitt dient zur Orientierung;
das endgültige Notenziel benötigt eine eingetragene Abschlussnote. Das Programm läuft nur
auf dem eigenen Rechner und hat keine Verbindung zu myCampus.
