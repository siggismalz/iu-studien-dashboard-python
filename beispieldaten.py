"""Kleine frei erfundene Datenmenge für Vorführung und nachvollziehbare Tests."""
from datetime import date
from modell import Studiengang, Pruefungsleistung, Pruefungsstatus


def beispielstudium() -> Studiengang:
    studium = Studiengang("Informatik (Beispieldaten)", date(2026, 4, 1), 180)
    erstes = studium.neues_semester(1)
    zweites = studium.neues_semester(2)
    daten = (
        ("Einführung in die Programmierung", 5, date(2026, 5, 12), "bestanden", 1.0),
        ("Mathematik", 10, date(2026, 6, 20), "bestanden", 3.0),
        ("Projektarbeit", 5, date(2026, 7, 10), "bestanden", None),
        ("Datenbanken", 5, date(2026, 8, 3), "nicht_bestanden", 5.0),
    )
    for titel, ects, datum, status, note in daten:
        modul = studium.neues_modul(titel, ects, erstes)
        modul.setze_ergebnis(Pruefungsleistung(datum, Pruefungsstatus(status), note))
    studium.neues_modul("Objektorientierte Programmierung", 5, zweites)
    return studium
