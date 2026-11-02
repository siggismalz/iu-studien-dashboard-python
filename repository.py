"""Lädt und speichert genau einen Studiengang in einer lokalen SQLite-Datei.

Die vier Tabellen enthalten nur Ausgangsdaten. Kennzahlen und Zielbewertungen
werden im Fachmodell berechnet. Technische Modulschlüssel bleiben hier.
"""
from datetime import date
from pathlib import Path
import sqlite3

from modell import Studiengang, Pruefungsleistung, Pruefungsstatus


class SQLiteRepository:
    def __init__(self, pfad: str | Path) -> None:
        self.verbindung = sqlite3.connect(str(pfad))
        self.verbindung.row_factory = sqlite3.Row
        self.verbindung.execute("PRAGMA foreign_keys = ON")
        self.verbindung.executescript("""
            CREATE TABLE IF NOT EXISTS studiengang (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL, start TEXT NOT NULL,
                gesamt_ects INTEGER NOT NULL CHECK (gesamt_ects > 0),
                dauer_monate INTEGER NOT NULL CHECK (dauer_monate > 0),
                max_note REAL NOT NULL,
                abschlussdatum TEXT, abschlussnote REAL
            );
            CREATE TABLE IF NOT EXISTS semester (
                nummer INTEGER PRIMARY KEY CHECK (nummer > 0),
                studium_id INTEGER NOT NULL REFERENCES studiengang(id)
            );
            CREATE TABLE IF NOT EXISTS modul (
                id INTEGER PRIMARY KEY,
                studium_id INTEGER NOT NULL REFERENCES studiengang(id),
                titel TEXT NOT NULL, ects INTEGER NOT NULL CHECK (ects > 0),
                semester_nummer INTEGER REFERENCES semester(nummer)
            );
            CREATE TABLE IF NOT EXISTS ergebnis (
                modul_id INTEGER PRIMARY KEY REFERENCES modul(id),
                datum TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('bestanden', 'nicht_bestanden')),
                note REAL
            );
        """)

    def laden(self) -> Studiengang | None:
        """Stellt Beziehungen über die öffentlichen Methoden des Fachmodells her."""
        zeile = self.verbindung.execute("SELECT * FROM studiengang WHERE id = 1").fetchone()
        if zeile is None:
            return None
        studium = Studiengang(
            zeile["name"], date.fromisoformat(zeile["start"]), zeile["gesamt_ects"],
            date.fromisoformat(zeile["abschlussdatum"]) if zeile["abschlussdatum"] else None,
            zeile["abschlussnote"], dauer_monate=zeile["dauer_monate"],
            max_note=zeile["max_note"],
        )
        semester = {}
        for zeile in self.verbindung.execute("SELECT nummer FROM semester ORDER BY nummer"):
            nummer = zeile["nummer"]
            semester[nummer] = studium.neues_semester(nummer)
        for zeile in self.verbindung.execute("""
            SELECT m.*, e.datum, e.status, e.note FROM modul m
            LEFT JOIN ergebnis e ON e.modul_id = m.id ORDER BY m.id
        """):
            modul = studium.neues_modul(zeile["titel"], zeile["ects"],
                                       semester.get(zeile["semester_nummer"]))
            if zeile["datum"]:
                modul.setze_ergebnis(Pruefungsleistung(date.fromisoformat(zeile["datum"]),
                                    Pruefungsstatus(zeile["status"]), zeile["note"]))
        return studium

    def speichern(self, studium: Studiengang) -> None:
        """Ersetzt den gespeicherten Studiengang in einer einzigen Transaktion.

        Bei der kleinen Datenmenge ist das einfacher als einzelne Änderungen
        nachzuführen. Schlägt ein SQL-Befehl fehl, wird alles zurückgerollt.
        """
        if not isinstance(studium, Studiengang):
            raise TypeError("speichern erwartet einen Studiengang.")
        with self.verbindung:
            for tabelle in ("ergebnis", "modul", "semester", "studiengang"):
                self.verbindung.execute(f"DELETE FROM {tabelle}")
            self.verbindung.execute("INSERT INTO studiengang VALUES (1, ?, ?, ?, ?, ?, ?, ?)", (
                studium.name, studium.start.isoformat(), studium.gesamt_ects,
                studium.zeitziel.dauer_monate, studium.notenziel.max_note,
                studium.abschlussdatum.isoformat() if studium.abschlussdatum else None,
                studium.abschlussnote,
            ))
            self.verbindung.executemany("INSERT INTO semester VALUES (?, 1)",
                                       [(s.nummer,) for s in studium.semester])
            for schluessel, modul in enumerate(studium.module):
                self.verbindung.execute("INSERT INTO modul VALUES (?, 1, ?, ?, ?)", (
                    schluessel, modul.titel, modul.ects,
                    modul.semester.nummer if modul.semester else None,
                ))
                if modul.ergebnis is not None:
                    ergebnis = modul.ergebnis
                    self.verbindung.execute("INSERT INTO ergebnis VALUES (?, ?, ?, ?)", (
                        schluessel, ergebnis.datum.isoformat(), ergebnis.status.value, ergebnis.note,
                    ))

    def schliessen(self) -> None:
        self.verbindung.close()
