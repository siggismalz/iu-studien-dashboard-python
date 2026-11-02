# Studien-Dashboard

Lokaler Python-Prototyp für das Portfolio im Kurs DLBDSOOFPP01_D.
Die Daten werden manuell erfasst und in einer SQLite-Datei gespeichert.
Es gibt keine Verbindung zu myCampus und keine zusätzlichen Python-Pakete.

## Start unter Windows

1. Python 3.12 oder neuer installieren. Für das Projekt wurde Python 3.15.0 verwendet.
2. Den Programmordner aus dem ZIP entpacken und dort ein Terminal öffnen.
3. `python app.py` ausführen. Falls der Befehl nicht verfügbar ist, `py app.py` verwenden.
4. Im Browser `http://127.0.0.1:8000` öffnen.
5. Das Programm im Terminal mit `Strg+C` beenden.

Beim ersten Start wird `studium.sqlite3` im Programmordner angelegt und mit
frei erfundenen Beispieldaten gefüllt. Beim nächsten Start wird dieselbe Datei
geladen. Der Ordner muss beschreibbar sein. Zum Ausprobieren einer getrennten
Datenbank: `python app.py --datenbank versuch.sqlite3 --port 8001`.
Der zusätzliche Port hilft auch, wenn Port 8000 schon belegt ist.

## Beispiel durchgehen

Den Stichtag auf **01.10.2026** setzen. Erwartet werden:

- 20 von 180 ECTS erreicht und 160 ECTS verbleibend;
- 30 ECTS Soll und damit eine Abweichung von -10 ECTS;
- ein gewichteter Schnitt von 2,33: `(5 × 1,0 + 10 × 3,0) / 15`;
- beide Abschlussziele noch offen.

Die unbenotete Projektarbeit mit 5 ECTS zählt zum Fortschritt, aber nicht zum
Notenschnitt. Die nicht bestandene Datenbankprüfung und das offene Pythonmodul
zählen zu keiner der beiden Kennzahlen.

In der Modulzeile auf **Bearbeiten** klicken, dann die Stammdaten oder das
Ergebnis ändern. **Offen / Ergebnis entfernen** entfernt das bisherige Ergebnis.
Unter **Studium verwalten** lassen sich Module und Semester anlegen, Ziele
ändern und ein bestätigter Abschluss eintragen. Das Entfernen eines Semesters
erhält dessen Module; sie haben anschließend keine Semesterzuordnung mehr.

Nach einer gültigen Änderung erscheint eine Speicherbestätigung. Bei ungültigen
Eingaben oder einem Speicherfehler bleibt der bisherige Stand erhalten.
Mehrere offene Browserformulare können veralten; dann muss die Seite neu geladen
werden, bevor die Änderung erneut eingegeben wird.

## Tests ausführen

Im Programmordner:

```text
python -m unittest discover -s tests -v
```

`tests/test_modell.py` enthält die 48 bisherigen Tests aus Phase 2. Die
Integrationstests ergänzen Speicherung, Controller und echte HTTP-Anfragen an
einen lokalen Testserver. Sie verwenden temporäre Datenbanken; die persönlichen
Einträge in `studium.sqlite3` werden dabei nicht verändert.

## Aufbau des Programms

| Datei | Aufgabe |
| --- | --- |
| `app.py` | `Application` erzeugt Repository, View und Controller, lädt den Studiengang und startet den HTTPServer mit `DashboardHandler`. |
| `modell.py` | Fachklassen, Beziehungen, Eingabegrenzen und Berechnungen aus Phase 2. |
| `repository.py` | `SQLiteRepository.laden()` und `speichern(studium)` für genau einen Studiengang. |
| `controller.py` | Verarbeitet Formulare und ruft die Fachmethoden auf; erzeugt kein HTML. |
| `view.py` | `DashboardView` erzeugt die gesamte HTML-Ausgabe und maskiert eingegebenen Text. |
| `beispieldaten.py` | Frei erfundene Daten für den ersten Start. |

Eine Änderung wird zunächst auf einer Kopie des Studiengangs ausgeführt.
Erst wenn die SQL-Transaktion erfolgreich war, übernimmt der Controller diese
Kopie. Das Repository ersetzt bei jedem Speichern den vollständigen kleinen
Datensatz. Das ist leicht nachvollziehbar, für große Datenmengen aber unnötig
aufwendig. Technische Modulschlüssel werden nur bei der Speicherung verwendet.

## Grenzen

- Ein Studiengang und eine Person pro Datenbankdatei; keine Benutzerverwaltung.
- Je Modul bleibt nur das aktuelle Prüfungsergebnis erhalten. Die Auswertung
  eines früheren Stichtags ersetzt daher keine vollständige Versuchshistorie.
- Das ECTS-Soll steigt in abgeschlossenen Kalendermonaten, nicht täglich.
- Der laufende Schnitt dient zur Orientierung. Die endgültige Zielbewertung
  verwendet ein manuell bestätigtes Abschlussdatum und die Abschlussnote.
- Die Prüfungsnotenmenge ist im Fachmodell festgelegt; Ziel- und Abschlussnote
  dürfen als Dezimalzahl zwischen 1,0 und 4,0 eingegeben werden.
- Der Server bindet nur an `127.0.0.1`. Das Programm ist ein lokaler
  Studienprototyp und wird nicht als öffentlicher Webdienst betrieben.

Die ergänzten Methoden `aendere_modul()` und `passe_stammdaten_an()` machen
Korrekturen über die Oberfläche möglich, ohne die internen Attribute direkt
aus dem Controller zu ändern.
