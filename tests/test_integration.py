"""Prüft Speicherung, Formularabläufe und echte lokale HTTP-Anfragen.

Alle Tests verwenden eigene temporäre Datenbanken mit erfundenen Daten.
Die produktive Datenbank wird weder geöffnet noch verändert.
"""
from contextlib import contextmanager
from datetime import date
from http.client import HTTPConnection
from pathlib import Path
from queue import Queue
import re
import sqlite3
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.parse import urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beispieldaten import beispielstudium
from controller import DashboardController
from modell import Studiengang, Zielbewertung
from repository import SQLiteRepository
from view import DashboardView


STICHTAG = date(2026, 10, 1)


class SpeicherUndFormularTests(unittest.TestCase):
    def setUp(self):
        self.ordner = TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        self.pfad = Path(self.ordner.name) / "studium.sqlite3"
        self.repo = SQLiteRepository(self.pfad)
        self.addCleanup(self.repo.schliessen)
        self.studium = beispielstudium()
        self.repo.speichern(self.studium)
        self.controller = DashboardController(self.studium, self.repo)

    def aendern(self, aktion, **felder):
        return self.controller.aendern({"aktion": aktion, **felder})

    def test_neuoeffnen_erhaelt_daten_beziehungen_und_kennzahlen(self):
        self.studium.passe_ziele_an(24, 1.7)
        self.studium.bestaetige_abschluss(date(2028, 3, 31), 1.7)
        self.repo.speichern(self.studium)
        neu = SQLiteRepository(self.pfad)
        try:
            geladen = neu.laden()
            self.assertEqual(geladen.name, "Informatik (Beispieldaten)")
            self.assertEqual(geladen.start, date(2026, 4, 1))
            self.assertEqual(geladen.zeitziel.dauer_monate, 24)
            self.assertEqual(geladen.notenziel.max_note, 1.7)
            self.assertEqual(geladen.abschlussdatum, date(2028, 3, 31))
            self.assertEqual(geladen.abschlussnote, 1.7)
            self.assertIs(geladen.module[0].semester, geladen.semester[0])
            self.assertEqual(len(geladen.semester[0].module), 4)
            self.assertEqual(geladen.erreichte_ects(STICHTAG), 20)
            self.assertAlmostEqual(geladen.notenschnitt(STICHTAG), 35 / 15)
            self.assertEqual(geladen.ects_soll(STICHTAG), 45)
            self.assertEqual(geladen.abweichung(STICHTAG), -25)
            self.assertIsNone(geladen.module[2].ergebnis.note)
            self.assertIsNone(geladen.module[4].ergebnis)
            # Auch rekonstruierte Prüfungen dürfen nur zu einem Modul gehören.
            with self.assertRaises(ValueError):
                geladen.module[4].setze_ergebnis(geladen.module[0].ergebnis)
        finally:
            neu.schliessen()

    def test_speichern_verwendet_den_uebergebenen_studiengang(self):
        anderer = Studiengang("Zweiter Studiengang", date(2025, 1, 1), 120)
        anderer.neues_modul("Neues Modul", 10)
        self.repo.speichern(anderer)
        geladen = self.repo.laden()
        self.assertEqual(geladen.name, "Zweiter Studiengang")
        self.assertEqual([m.titel for m in geladen.module], ["Neues Modul"])
        self.assertEqual(geladen.semester, ())

    def test_sql_fehler_rollt_gesamte_aenderung_zurueck(self):
        # Echter SQLite-Fehler nach den DELETEs und dem ersten INSERT.
        self.repo.verbindung.execute("""
            CREATE TRIGGER test_abbruch BEFORE INSERT ON modul
            WHEN NEW.titel = 'Abbruch'
            BEGIN SELECT RAISE(ABORT, 'Absichtlicher Testfehler'); END
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.aendern("modul_aendern", modul="0", titel="Abbruch", ects="5", semester="1")
        self.assertIs(self.controller.studium, self.studium)
        self.assertEqual(self.controller.version, 0)
        neu = SQLiteRepository(self.pfad)
        try:
            geladen = neu.laden()
            self.assertEqual(len(geladen.module), 5)
            self.assertEqual(geladen.module[0].titel, "Einführung in die Programmierung")
            self.assertEqual(geladen.erreichte_ects(STICHTAG), 20)
        finally:
            neu.schliessen()

    def test_ungueltige_moduleingabe_aendert_keine_teilwerte(self):
        with self.assertRaises(ValueError):
            self.aendern("modul_aendern", modul="0", titel="Anderer Titel", ects="180", semester="2")
        self.assertIs(self.controller.studium, self.studium)
        self.assertEqual(self.repo.laden().module[0].titel, "Einführung in die Programmierung")
        self.assertEqual(self.repo.laden().module[0].semester.nummer, 1)

    def test_modul_erfassen_korrigieren_ergebnis_setzen_und_entfernen(self):
        # Kein HTML-Rückgabewert: Die Darstellung gehört zur View.
        self.assertIsNone(self.aendern("semester_neu", nummer="3"))
        self.aendern("modul_neu", titel="Testmodul", ects="5", semester="3")
        self.aendern("modul_aendern", modul="5", titel="Korrigiert", ects="10", semester="")
        self.aendern("ergebnis", modul="5", status="bestanden", datum="2026-09-01", note="1,7")
        geladen = self.repo.laden()
        self.assertEqual(geladen.module[5].titel, "Korrigiert")
        self.assertIsNone(geladen.module[5].semester)
        self.assertEqual(geladen.erreichte_ects(STICHTAG), 30)
        self.assertAlmostEqual(geladen.notenschnitt(STICHTAG), 52 / 25)
        self.aendern("ergebnis", modul="5", status="offen")
        self.assertIsNone(self.repo.laden().module[5].ergebnis)
        self.assertEqual(self.controller.studium.erreichte_ects(STICHTAG), 20)

    def test_semester_entfernen_erhaelt_ergebnisse_auch_nach_laden(self):
        self.aendern("semester_entfernen", semester="1")
        geladen = self.repo.laden()
        self.assertEqual([s.nummer for s in geladen.semester], [2])
        self.assertEqual(len(geladen.module), 5)
        self.assertIsNone(geladen.module[0].semester)
        self.assertEqual(geladen.module[0].ergebnis.note, 1.0)
        self.assertEqual(geladen.erreichte_ects(STICHTAG), 20)

    def test_ziele_abschluss_und_ruecknahme_ueber_formular(self):
        self.aendern("ziele", dauer_monate="24", max_note="2,0")
        self.aendern("abschluss", abschlussdatum="2028-03-31", abschlussnote="2,3")
        geladen = self.repo.laden()
        self.assertEqual(geladen.zieltermin, date(2028, 4, 1))
        self.assertEqual([z.bewerten(geladen, date(2028, 4, 1)) for z in geladen.ziele],
                         [Zielbewertung.ERREICHT, Zielbewertung.NICHT_ERREICHT])
        self.aendern("abschluss", abschlussdatum="", abschlussnote="")
        self.assertIsNone(self.repo.laden().abschlussdatum)
        self.assertIsNone(self.repo.laden().abschlussnote)

    def test_stammdaten_pruefen_vorhandene_ergebnisdaten(self):
        with self.assertRaises(ValueError):
            self.aendern("stammdaten", name="Geändert", start="2026-06-01", gesamt_ects="180")
        self.assertEqual(self.repo.laden().start, date(2026, 4, 1))
        self.aendern("stammdaten", name="Eigener Studiengang", start="2026-03-01", gesamt_ects="120")
        geladen = self.repo.laden()
        self.assertEqual(geladen.name, "Eigener Studiengang")
        self.assertEqual(geladen.zieltermin, date(2029, 3, 1))
        self.assertEqual(geladen.gesamt_ects, 120)

    def test_formulare_runden_gespeicherte_ziel_und_abschlussnote_nicht(self):
        self.aendern("ziele", dauer_monate="36", max_note="2,15")
        self.aendern("abschluss", abschlussdatum="2029-03-31", abschlussnote="2,15")
        seite = DashboardView().rendern(self.controller.studium, STICHTAG)
        for name in ("max_note", "abschlussnote"):
            wert = re.search(fr'name="{name}"[^>]*value="([^"]*)"', seite).group(1)
            self.assertEqual(float(wert.replace(",", ".")), 2.15)


@contextmanager
def laufender_server(pfad):
    """Server und SQLite im selben Thread, Anfragen über einen echten Socket."""
    bereit = Queue()

    def ausfuehren():
        try:
            from app import Application
            app = Application(pfad, port=0)
        except Exception as fehler:
            bereit.put(fehler)
            return
        bereit.put(app)
        app.starten()

    thread = Thread(target=ausfuehren, daemon=True)
    thread.start()
    app = bereit.get(timeout=10)
    if isinstance(app, Exception):
        raise app
    try:
        yield app.url
    finally:
        app.server.shutdown()
        thread.join(timeout=10)
        if thread.is_alive():
            raise RuntimeError("Der Testserver wurde nicht beendet.")


def anfrage(url, form=None, pfad="/?stichtag=2026-10-01"):
    ziel = urlsplit(url)
    verbindung = HTTPConnection(ziel.hostname, ziel.port, timeout=5)
    try:
        if form is None:
            verbindung.request("GET", pfad)
        else:
            verbindung.request("POST", "/", urlencode(form),
                               {"Content-Type": "application/x-www-form-urlencoded"})
        antwort = verbindung.getresponse()
        return antwort.status, antwort.read().decode("utf-8"), dict(antwort.getheaders())
    finally:
        verbindung.close()


def formular(seite, **felder):
    felder["csrf"] = re.search(r'name="csrf" value="([^"]+)"', seite).group(1)
    felder["version"] = re.search(r'name="version" value="([^"]+)"', seite).group(1)
    felder["stichtag"] = "2026-10-01"
    return felder


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.ordner = TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        self.pfad = Path(self.ordner.name) / "http.sqlite3"

    def test_get_post_und_neustart_erhalten_aenderung(self):
        with laufender_server(self.pfad) as url:
            status, seite, _ = anfrage(url)
            self.assertEqual(status, 200)
            self.assertIn("2,33", seite)
            form = formular(seite, aktion="modul_neu", titel="HTTP-Testmodul", ects="5", semester="2")
            status, _, kopf = anfrage(url, form)
            self.assertEqual(status, 303)
            self.assertIn("Location", kopf)
            self.assertIn("HTTP-Testmodul", anfrage(url)[1])
        # Neue Application mit neuer SQLite-Verbindung liest die vorherige Datei.
        with laufender_server(self.pfad) as url:
            self.assertIn("HTTP-Testmodul", anfrage(url)[1])

    def test_ungueltiges_formular_zeigt_fehler_und_erhaelt_daten(self):
        with laufender_server(self.pfad) as url:
            _, seite, _ = anfrage(url)
            form = formular(seite, aktion="modul_neu", titel="DARF NICHT GESPEICHERT WERDEN", ects="-5")
            status, fehlerseite, _ = anfrage(url, form)
            self.assertEqual(status, 400)
            self.assertIn("positive ganze Zahl", fehlerseite)
            self.assertNotIn("DARF NICHT GESPEICHERT WERDEN", anfrage(url)[1])

    def test_html_sonderzeichen_werden_als_text_ausgegeben(self):
        with laufender_server(self.pfad) as url:
            _, seite, _ = anfrage(url)
            form = formular(seite, aktion="modul_neu", titel='<script>alert("Test")</script>', ects="5")
            self.assertEqual(anfrage(url, form)[0], 303)
            seite = anfrage(url)[1]
            self.assertIn("&lt;script&gt;", seite)
            self.assertNotIn('<script>alert("Test")</script>', seite)

    def test_altes_formular_wird_nicht_doppelt_gespeichert(self):
        with laufender_server(self.pfad) as url:
            _, seite, _ = anfrage(url)
            form = formular(seite, aktion="modul_neu", titel="Einmal speichern", ects="5")
            self.assertEqual(anfrage(url, form)[0], 303)
            self.assertEqual(anfrage(url, form)[0], 409)
        repo = SQLiteRepository(self.pfad)
        try:
            self.assertEqual([m.titel for m in repo.laden().module].count("Einmal speichern"), 1)
        finally:
            repo.schliessen()

    def test_speicherfehler_wird_im_http_angezeigt_ohne_datenverlust(self):
        with laufender_server(self.pfad) as url:
            _, seite, _ = anfrage(url)
            # Fehler wird in der echten SQLite-Transaktion ausgelöst.
            verbindung = sqlite3.connect(self.pfad)
            verbindung.execute("""
                CREATE TRIGGER test_http_abbruch BEFORE INSERT ON modul
                WHEN NEW.titel = 'Speicherfehler-Test'
                BEGIN SELECT RAISE(ABORT, 'Absichtlicher Testfehler'); END
            """)
            verbindung.close()
            form = formular(seite, aktion="modul_neu", titel="Speicherfehler-Test", ects="5")
            status, fehlerseite, _ = anfrage(url, form)
            self.assertEqual(status, 500)
            self.assertIn("Der bisherige Stand bleibt erhalten", fehlerseite)
            self.assertNotIn("Speicherfehler-Test", anfrage(url)[1])
        repo = SQLiteRepository(self.pfad)
        try:
            self.assertEqual(len(repo.laden().module), 5)
            self.assertEqual(repo.laden().erreichte_ects(STICHTAG), 20)
        finally:
            repo.schliessen()


if __name__ == "__main__":
    unittest.main(verbosity=2)
