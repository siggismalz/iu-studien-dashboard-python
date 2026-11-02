"""Startpunkt und HTTP-Anbindung des lokalen Studien-Dashboards.

Start: python app.py; danach die angezeigte Adresse im Browser öffnen.
Es werden ausschließlich Module der Python-Standardbibliothek benötigt.
"""
import argparse
from datetime import date
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
import sqlite3
import sys
from urllib.parse import parse_qs, urlencode, urlsplit

# Die portable Windows-Ausgabe von Python nimmt den Skriptordner nicht
# automatisch in den Suchpfad auf. So funktionieren beide Installationsarten.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from beispieldaten import beispielstudium
from controller import DashboardController, datum
from repository import SQLiteRepository
from view import DashboardView


class DashboardHandler(BaseHTTPRequestHandler):
    """Übersetzt HTTP-Anfragen in Aufrufe von Controller und View."""
    def __init__(self, *args, controller: DashboardController,
                 view: DashboardView, csrf_token: str, **kwargs):
        self.controller = controller
        self.view = view
        self.csrf_token = csrf_token
        super().__init__(*args, **kwargs)

    def _senden(self, status: int, text: str) -> None:
        daten = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(daten)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(daten)

    def _seite(self, status=200, stichtag=None, modul_index=0, **hinweise) -> None:
        self._senden(status, self.view.rendern(self.controller.studium, stichtag or date.today(),
                      self.csrf_token, self.controller.version, modul_index=modul_index, **hinweise))

    def do_GET(self) -> None:
        adresse = urlsplit(self.path)
        if adresse.path != "/":
            self._seite(404, fehler="Diese Seite existiert nicht.")
            return
        try:
            query = parse_qs(adresse.query, max_num_fields=20)
            stichtag = datum(query.get("stichtag", [date.today().isoformat()])[0], "Stichtag")
            index = int(query.get("modul", ["0"])[0])
            if index < 0 or (self.controller.studium.module and index >= len(self.controller.studium.module)):
                raise ValueError("Das gewählte Modul existiert nicht.")
            meldung = "Die Änderung wurde gespeichert." if query.get("gespeichert") == ["1"] else ""
            self._seite(stichtag=stichtag, modul_index=index, meldung=meldung)
        except ValueError as fehler:
            self._seite(400, fehler=str(fehler))

    def do_POST(self) -> None:
        if self.path != "/":
            self._seite(404, fehler="Diese Aktion ist nicht verfügbar.")
            return
        form = {}
        stichtag = date.today()
        index = 0
        try:
            if self.headers.get_content_type() != "application/x-www-form-urlencoded":
                raise ValueError("Es werden nur Formulare unterstützt.")
            laenge = int(self.headers.get("Content-Length", "0"))
            if not 0 < laenge <= 16384:
                raise ValueError("Das Formular ist leer oder zu groß.")
            werte = parse_qs(self.rfile.read(laenge).decode("utf-8"),
                             keep_blank_values=True, max_num_fields=20)
            if any(len(wert) != 1 for wert in werte.values()):
                raise ValueError("Ein Formularfeld wurde mehrfach übertragen.")
            form = {name: wert[0] for name, wert in werte.items()}
            if not secrets.compare_digest(form.get("csrf", ""), self.csrf_token):
                self._seite(403, fehler="Das Formular stammt nicht aus dieser Sitzung. Bitte die Seite neu laden.")
                return
            if form.get("version") != str(self.controller.version):
                self._seite(409, fehler="Die Daten wurden inzwischen geändert. Bitte das aktuelle Formular verwenden.")
                return
            stichtag = datum(form.get("stichtag", date.today().isoformat()), "Stichtag")
            index = int(form.get("modul", "0"))
            self.controller.aendern(form)
        except (ValueError, TypeError, UnicodeError) as fehler:
            self._seite(400, stichtag, index, fehler=str(fehler), formulardaten=form)
            return
        except sqlite3.Error:
            self._seite(500, stichtag, index,
                        fehler="Die Datenbank konnte nicht gespeichert werden. Der bisherige Stand bleibt erhalten.",
                        formulardaten=form)
            return
        self.send_response(303)
        self.send_header("Location", "/?" + urlencode({"stichtag": stichtag.isoformat(),
                         "modul": max(index, 0), "gespeichert": "1"}))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args) -> None:
        # Keine Formulare oder persönlichen Daten in die Konsole schreiben.
        pass


class Application:
    """Verbindet Speicherung, Fachmodell, Steuerung, Darstellung und HTTPServer."""
    def __init__(self, datenbank: str | Path, port: int = 8000) -> None:
        self.repository = SQLiteRepository(datenbank)
        try:
            studium = self.repository.laden()
            if studium is None:
                studium = beispielstudium()
                self.repository.speichern(studium)
            self.view = DashboardView()
            self.controller = DashboardController(studium, self.repository)
            # partial übergibt die vorhandenen Objekte an jeden neuen Handler.
            handler = partial(DashboardHandler, controller=self.controller,
                              view=self.view, csrf_token=secrets.token_hex(24))
            self.server = HTTPServer(("127.0.0.1", port), handler)
        except Exception:
            self.repository.schliessen()
            raise
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self._geschlossen = False

    def starten(self) -> None:
        print(f"Studien-Dashboard: {self.url}", flush=True)
        print("Beenden mit Strg+C. Die Daten bleiben gespeichert.", flush=True)
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.schliessen()

    def schliessen(self) -> None:
        """Nach dem Ende der Anfrageschleife Server und Datenbank freigeben."""
        if not self._geschlossen:
            self.server.server_close()
            self.repository.schliessen()
            self._geschlossen = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Lokales Studien-Dashboard")
    parser.add_argument("--datenbank", type=Path, default=Path(__file__).resolve().parent / "studium.sqlite3")
    parser.add_argument("--port", type=int, default=8000)
    optionen = parser.parse_args()
    try:
        Application(optionen.datenbank, optionen.port).starten()
    except (OSError, sqlite3.Error, ValueError) as fehler:
        parser.exit(1, f"Start nicht möglich: {fehler}\n")


if __name__ == "__main__":
    main()
