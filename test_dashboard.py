"""Beispiele für die wichtigsten Berechnungen und das Speichern."""
from datetime import date
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from beispieldaten import beispielstudium
from controller import DashboardController
from modell import Studiengang, Pruefungsleistung, Pruefungsstatus, Zielbewertung
from repository import SQLiteRepository
from view import DashboardView


class DashboardTests(unittest.TestCase):
    def test_beispiel_kennzahlen(self):
        studium = beispielstudium()
        stichtag = date(2026, 10, 1)
        self.assertEqual(studium.erreichte_ects(stichtag), 20)
        self.assertEqual(studium.ects_soll(stichtag), 30)
        self.assertEqual(studium.abweichung(stichtag), -10)
        # Die unbenoteten 5 ECTS gehören nicht in die Notenberechnung.
        self.assertAlmostEqual(studium.notenschnitt(stichtag), 35 / 15)

    def test_repository_speichert_uebergebenen_studiengang(self):
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "test.sqlite3"
            repo = SQLiteRepository(pfad)
            try:
                repo.speichern(beispielstudium())
                anderer = Studiengang("Anderer Studiengang", date(2026, 1, 1), 120)
                semester = anderer.neues_semester(1)
                modul = anderer.neues_modul("Statistik", 5, semester)
                modul.setze_ergebnis(Pruefungsleistung(
                    date(2026, 2, 1), Pruefungsstatus.BESTANDEN, 2.3))
                repo.speichern(anderer)
            finally:
                repo.schliessen()

            # Neue Verbindung: Es zählt der gespeicherte Stand der Datei.
            repo = SQLiteRepository(pfad)
            try:
                geladen = repo.laden()
                self.assertEqual(geladen.name, "Anderer Studiengang")
                self.assertEqual(geladen.gesamt_ects, 120)
                self.assertEqual(len(geladen.module), 1)
                self.assertEqual(geladen.module[0].titel, "Statistik")
                self.assertIs(geladen.module[0].semester, geladen.semester[0])
                self.assertEqual(geladen.module[0].ergebnis.note, 2.3)
            finally:
                repo.schliessen()

    def test_ungueltige_note_bleibt_unveraendert(self):
        with TemporaryDirectory() as ordner:
            repo = SQLiteRepository(Path(ordner) / "test.sqlite3")
            try:
                studium = beispielstudium()
                repo.speichern(studium)
                controller = DashboardController(studium, repo)
                with self.assertRaises(ValueError):
                    controller.aendern({
                        "aktion": "ergebnis", "modul": "0", "status": "bestanden",
                        "datum": "2026-05-12", "note": "2,1",
                    })
                self.assertEqual(controller.studium.module[0].ergebnis.note, 1.0)
                self.assertEqual(repo.laden().module[0].ergebnis.note, 1.0)
            finally:
                repo.schliessen()

    def test_semester_entfernen_erhaelt_modul_und_ergebnis(self):
        studium = beispielstudium()
        modul = studium.module[0]
        ergebnis = modul.ergebnis
        studium.entferne_semester(studium.semester[0])
        self.assertIn(modul, studium.module)
        self.assertIs(modul.ergebnis, ergebnis)
        self.assertIsNone(modul.semester)
        self.assertEqual(studium.erreichte_ects(date(2026, 10, 1)), 20)

    def test_zeit_und_notenziel_bewerten_unterschiedlich(self):
        studium = beispielstudium()
        studium.bestaetige_abschluss(date(2029, 3, 31), 2.3)
        bewertungen = [ziel.bewerten(studium, date(2029, 4, 1))
                       for ziel in studium.ziele]
        self.assertEqual(bewertungen,
                         [Zielbewertung.ERREICHT, Zielbewertung.NICHT_ERREICHT])

    def test_noten_im_formular_bleiben_genau(self):
        studium = beispielstudium()
        studium.passe_ziele_an(36, 2.15)
        studium.bestaetige_abschluss(date(2029, 3, 31), 2.15)
        seite = DashboardView().rendern(studium, date(2029, 4, 1))
        # Erneutes Speichern darf aus 2,15 nicht versehentlich 2,1 machen.
        self.assertRegex(seite, r'name="max_note"[^>]*value="2,15"')
        self.assertRegex(seite, r'name="abschlussnote"[^>]*value="2,15"')


if __name__ == "__main__":
    unittest.main(verbosity=2)
