"""Verarbeitet Formulare und steuert Änderungen, ohne HTML zu erzeugen."""
from copy import deepcopy
from datetime import date

from modell import Studiengang, Pruefungsleistung, Pruefungsstatus
from repository import SQLiteRepository


def datum(text: str, bezeichnung: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{bezeichnung}: Bitte ein gültiges Datum angeben.") from None


def ganzzahl(text: str, bezeichnung: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{bezeichnung}: Bitte eine ganze Zahl angeben.") from None


def dezimalzahl(text: str, bezeichnung: str) -> float:
    try:
        return float(text.replace(",", "."))
    except ValueError:
        raise ValueError(f"{bezeichnung}: Bitte eine Zahl angeben.") from None


class DashboardController:
    def __init__(self, studium: Studiengang, repository: SQLiteRepository) -> None:
        self.studium = studium
        self.repository = repository
        self.version = 0

    def aendern(self, form: dict[str, str]) -> None:
        """Erst prüfen und speichern, dann den angezeigten Zustand ersetzen.

        Eine Arbeitskopie hält Eingabe- und Speicherfehler vom bisherigen
        Zustand fern. Für einen einzelnen Studiengang ist dies ausreichend.
        """
        neu = deepcopy(self.studium)
        aktion = form.get("aktion", "")

        def feld(name: str) -> str:
            return form.get(name, "").strip()

        def modul():
            index = ganzzahl(feld("modul"), "Modul")
            if not 0 <= index < len(neu.module):
                raise ValueError("Das gewählte Modul existiert nicht.")
            return neu.module[index]

        def semester():
            if not feld("semester"):
                return None
            nummer = ganzzahl(feld("semester"), "Semester")
            for eintrag in neu.semester:
                if eintrag.nummer == nummer:
                    return eintrag
            raise ValueError("Das gewählte Semester existiert nicht.")

        if aktion == "modul_neu":
            neu.neues_modul(feld("titel"), ganzzahl(feld("ects"), "ECTS"), semester())
        elif aktion == "modul_aendern":
            neu.aendere_modul(modul(), feld("titel"), ganzzahl(feld("ects"), "ECTS"), semester())
        elif aktion == "ergebnis":
            ausgewaehlt = modul()
            if feld("status") == "offen":
                ausgewaehlt.setze_ergebnis(None)
            else:
                try:
                    status = Pruefungsstatus(feld("status"))
                except ValueError:
                    raise ValueError("Bitte einen gültigen Prüfungsstatus wählen.") from None
                note = dezimalzahl(feld("note"), "Note") if feld("note") else None
                ausgewaehlt.setze_ergebnis(Pruefungsleistung(
                    datum(feld("datum"), "Prüfungsdatum"), status, note))
        elif aktion == "semester_neu":
            neu.neues_semester(ganzzahl(feld("nummer"), "Semesternummer"))
        elif aktion == "semester_entfernen":
            ausgewaehlt = semester()
            if ausgewaehlt is None:
                raise ValueError("Bitte ein Semester zum Entfernen wählen.")
            neu.entferne_semester(ausgewaehlt)
        elif aktion == "ziele":
            neu.passe_ziele_an(ganzzahl(feld("dauer_monate"), "Zieldauer"),
                              dezimalzahl(feld("max_note"), "Zielnote"))
        elif aktion == "abschluss":
            abschluss = datum(feld("abschlussdatum"), "Abschlussdatum") if feld("abschlussdatum") else None
            note = dezimalzahl(feld("abschlussnote"), "Abschlussnote") if feld("abschlussnote") else None
            neu.bestaetige_abschluss(abschluss, note)
        elif aktion == "stammdaten":
            neu.passe_stammdaten_an(feld("name"), datum(feld("start"), "Studienbeginn"),
                                   ganzzahl(feld("gesamt_ects"), "Gesamt-ECTS"))
        else:
            raise ValueError("Diese Aktion ist nicht bekannt.")
        self.repository.speichern(neu)
        self.studium = neu
        self.version += 1
