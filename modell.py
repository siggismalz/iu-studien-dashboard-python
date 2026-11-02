"""Klassen und Berechnungen für das Studium, übernommen und ergänzt aus Phase 2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from math import isfinite

_MODULNOTEN = frozenset((1.0, 1.3, 1.7, 2.0, 2.3, 2.7, 3.0, 3.3, 3.7, 4.0))


class Pruefungsstatus(Enum):
    BESTANDEN = "bestanden"
    NICHT_BESTANDEN = "nicht_bestanden"


class Zielbewertung(Enum):
    OFFEN = "offen"
    ERREICHT = "erreicht"
    NICHT_ERREICHT = "nicht_erreicht"


def _text(wert: str, name: str) -> str:
    if not isinstance(wert, str) or not wert.strip():
        raise ValueError(f"{name} muss nichtleerer Text sein.")
    return wert.strip()


def _positiv(wert: int, name: str) -> int:
    # bool ist eine int-Unterklasse; fachlich ist True keine ECTS-Zahl.
    if type(wert) is not int or wert <= 0:
        raise ValueError(f"{name} muss eine positive ganze Zahl sein.")
    return wert


def _datum(wert: date, name: str) -> date:
    if type(wert) is not date:
        raise TypeError(f"{name} muss ein date sein.")
    return wert


def _note(wert: float, *, bestanden: bool = True) -> float:
    if isinstance(wert, bool) or not isinstance(wert, (int, float)):
        raise ValueError("Eine Note muss eine endliche Zahl sein.")
    grenze = 4.0 if bestanden else 5.0
    if not isfinite(wert) or not 1.0 <= wert <= grenze:
        raise ValueError(f"Note muss zwischen 1,0 und {grenze} liegen.")
    return float(wert)


def addiere_monate(start: date, monate: int) -> date:
    """Kalendermonate addieren; fehlenden Tag auf Monatsende kappen."""
    _datum(start, "Start")
    if type(monate) is not int or monate < 0:
        raise ValueError("Monate müssen eine nichtnegative ganze Zahl sein.")
    jahr, monat0 = divmod(start.year * 12 + start.month - 1 + monate, 12)
    monat = monat0 + 1
    tag = min(start.day, monthrange(jahr, monat)[1])
    return date(jahr, monat, tag)


def abgeschlossene_monate(start: date, stichtag: date) -> int:
    """Vollständige Monatsintervalle; Monatsende folgt addiere_monate()."""
    _datum(start, "Start")
    _datum(stichtag, "Stichtag")
    if stichtag <= start:
        return 0
    monate = (stichtag.year - start.year) * 12 + stichtag.month - start.month
    if stichtag < addiere_monate(start, monate):
        monate -= 1
    return monate


@dataclass(frozen=True, eq=False)
class Pruefungsleistung:
    datum: date
    status: Pruefungsstatus
    note: float | None = None
    _modul: Modul | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        _datum(self.datum, "Prüfungsdatum")
        if not isinstance(self.status, Pruefungsstatus):
            raise TypeError("status muss ein Pruefungsstatus sein.")
        if self.status is Pruefungsstatus.NICHT_BESTANDEN:
            if self.note is not None and _note(self.note, bestanden=False) != 5.0:
                raise ValueError("Nicht bestanden erlaubt nur Note 5,0 oder None.")
        elif self.note is not None:
            _note(self.note)
            if self.note not in _MODULNOTEN:
                raise ValueError("Bestandene Modulnote muss aus der vorgesehenen Notenmenge stammen.")
        if self.note is not None:
            object.__setattr__(self, "note", float(self.note))


class Studienziel(ABC):
    @abstractmethod
    def bewerten(self, studium: Studiengang, stichtag: date) -> Zielbewertung:
        """Ein fachliches Ziel bewerten; konkretes Kriterium folgt im Subtyp."""


@dataclass(frozen=True)
class Zeitziel(Studienziel):
    dauer_monate: int = 36

    def __post_init__(self) -> None:
        _positiv(self.dauer_monate, "Zieldauer")

    def bewerten(self, studium: Studiengang, stichtag: date) -> Zielbewertung:
        _datum(stichtag, "Stichtag")
        zieltermin = addiere_monate(studium.start, self.dauer_monate)
        if studium.abschlussdatum is not None and studium.abschlussdatum <= stichtag:
            return (Zielbewertung.ERREICHT if studium.abschlussdatum <= zieltermin
                    else Zielbewertung.NICHT_ERREICHT)
        return (Zielbewertung.OFFEN if stichtag <= zieltermin
                else Zielbewertung.NICHT_ERREICHT)


@dataclass(frozen=True)
class Notenziel(Studienziel):
    max_note: float = 2.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_note", _note(self.max_note))

    def bewerten(self, studium: Studiengang, stichtag: date) -> Zielbewertung:
        _datum(stichtag, "Stichtag")
        if (studium.abschlussdatum is None or studium.abschlussdatum > stichtag
                or studium.abschlussnote is None):
            return Zielbewertung.OFFEN
        return (Zielbewertung.ERREICHT if studium.abschlussnote <= self.max_note
                else Zielbewertung.NICHT_ERREICHT)


class Semester:
    __slots__ = ("_nummer", "_studium")

    def __init__(self, nummer: int) -> None:
        self._nummer = _positiv(nummer, "Semesternummer")
        self._studium: Studiengang | None = None

    @property
    def nummer(self) -> int:
        return self._nummer

    @property
    def module(self) -> tuple[Modul, ...]:
        if self._studium is None:
            return ()
        return tuple(m for m in self._studium.module if m.semester is self)


class Modul:
    __slots__ = ("_titel", "_ects", "_studium", "_semester", "_ergebnis")

    def __init__(self, titel: str, ects: int) -> None:
        self._titel = _text(titel, "Modultitel")
        self._ects = _positiv(ects, "Modul-ECTS")
        self._studium: Studiengang | None = None
        self._semester: Semester | None = None
        self._ergebnis: Pruefungsleistung | None = None

    @property
    def titel(self) -> str:
        return self._titel

    @property
    def ects(self) -> int:
        return self._ects

    @property
    def semester(self) -> Semester | None:
        return self._semester

    @property
    def ergebnis(self) -> Pruefungsleistung | None:
        return self._ergebnis

    def setze_ergebnis(self, ergebnis: Pruefungsleistung | None) -> None:
        if ergebnis is not None:
            if not isinstance(ergebnis, Pruefungsleistung):
                raise TypeError("Ergebnis muss Pruefungsleistung oder None sein.")
            if ergebnis._modul is not None and ergebnis._modul is not self:
                raise ValueError("Eine Prüfungsleistung gehört höchstens einem Modul.")
            if self._studium is not None and ergebnis.datum < self._studium.start:
                raise ValueError("Das Ergebnis darf nicht vor Studienbeginn liegen.")
        if self._ergebnis is not None:
            object.__setattr__(self._ergebnis, "_modul", None)
        self._ergebnis = ergebnis
        if ergebnis is not None:
            object.__setattr__(ergebnis, "_modul", self)


class Studiengang:
    __slots__ = ("_name", "_start", "_gesamt_ects", "_abschlussdatum",
                 "_abschlussnote", "_semester", "_module", "_zeitziel", "_notenziel")

    def __init__(self, name: str, start: date, gesamt_ects: int,
                 abschlussdatum: date | None = None, abschlussnote: float | None = None,
                 *, dauer_monate: int = 36, max_note: float = 2.0) -> None:
        self._name = _text(name, "Studiengangname")
        self._start = _datum(start, "Studienbeginn")
        self._gesamt_ects = _positiv(gesamt_ects, "Gesamt-ECTS")
        self._zeitziel = Zeitziel(dauer_monate)
        self._notenziel = Notenziel(max_note)
        # Früh prüfen, damit ein Zieltermin jenseits des date-Wertebereichs scheitert.
        addiere_monate(start, dauer_monate)
        self._semester: list[Semester] = []
        self._module: list[Modul] = []
        self._abschlussdatum: date | None = None
        self._abschlussnote: float | None = None
        self.bestaetige_abschluss(abschlussdatum, abschlussnote)

    @property
    def name(self) -> str:
        return self._name

    @property
    def start(self) -> date:
        return self._start

    @property
    def gesamt_ects(self) -> int:
        return self._gesamt_ects

    @property
    def abschlussdatum(self) -> date | None:
        return self._abschlussdatum

    @property
    def abschlussnote(self) -> float | None:
        return self._abschlussnote

    @property
    def zeitziel(self) -> Zeitziel:
        return self._zeitziel

    @property
    def notenziel(self) -> Notenziel:
        return self._notenziel

    @property
    def ziele(self) -> tuple[Studienziel, ...]:
        return (self.zeitziel, self.notenziel)

    @property
    def semester(self) -> tuple[Semester, ...]:
        return tuple(self._semester)

    @property
    def module(self) -> tuple[Modul, ...]:
        return tuple(self._module)

    @property
    def zieltermin(self) -> date:
        return addiere_monate(self.start, self.zeitziel.dauer_monate)

    def bestaetige_abschluss(self, datum: date | None, note: float | None = None) -> None:
        if datum is None:
            if note is not None:
                raise ValueError("Eine Abschlussnote benötigt ein Abschlussdatum.")
        else:
            _datum(datum, "Abschlussdatum")
            if datum < self.start:
                raise ValueError("Abschlussdatum liegt vor Studienbeginn.")
            if note is not None:
                note = _note(note)
        # Erst nach allen Prüfungen ändern: ein Fehler erhält den bisherigen Zustand.
        self._abschlussdatum, self._abschlussnote = datum, note

    def passe_ziele_an(self, dauer_monate: int, max_note: float) -> None:
        neues_zeitziel, neues_notenziel = Zeitziel(dauer_monate), Notenziel(max_note)
        addiere_monate(self.start, neues_zeitziel.dauer_monate)
        self._zeitziel, self._notenziel = neues_zeitziel, neues_notenziel

    def neues_semester(self, nummer: int) -> Semester:
        semester = Semester(nummer)
        if any(s.nummer == semester.nummer for s in self._semester):
            raise ValueError("Die Semesternummer ist bereits vergeben.")
        semester._studium = self
        self._semester.append(semester)
        return semester

    def neues_modul(self, titel: str, ects: int, semester: Semester | None = None) -> Modul:
        modul = Modul(titel, ects)
        if semester is not None and semester not in self._semester:
            raise ValueError("Semester gehört nicht zu diesem Studiengang.")
        if sum(m.ects for m in self._module) + ects > self.gesamt_ects:
            raise ValueError("Die Module überschreiten den Studienumfang.")
        modul._studium, modul._semester = self, semester
        self._module.append(modul)
        return modul

    def ordne_zu(self, modul: Modul, semester: Semester | None) -> None:
        if modul not in self._module:
            raise ValueError("Modul gehört nicht zu diesem Studiengang.")
        if semester is not None and semester not in self._semester:
            raise ValueError("Semester gehört nicht zu diesem Studiengang.")
        modul._semester = semester

    def aendere_modul(self, modul: Modul, titel: str, ects: int,
                     semester: Semester | None) -> None:
        """Stammdaten korrigieren; bei einem Fehler bleibt das Modul unverändert."""
        titel, ects = _text(titel, "Modultitel"), _positiv(ects, "Modul-ECTS")
        if modul not in self._module:
            raise ValueError("Modul gehört nicht zu diesem Studiengang.")
        if semester is not None and semester not in self._semester:
            raise ValueError("Semester gehört nicht zu diesem Studiengang.")
        if sum(m.ects for m in self._module if m is not modul) + ects > self.gesamt_ects:
            raise ValueError("Die Module überschreiten den Studienumfang.")
        modul._titel, modul._ects, modul._semester = titel, ects, semester

    def passe_stammdaten_an(self, name: str, start: date, gesamt_ects: int) -> None:
        """Studienbeginn und Umfang ändern, ohne vorhandene Ergebnisse zu entwerten."""
        name = _text(name, "Studiengangname")
        start = _datum(start, "Studienbeginn")
        gesamt_ects = _positiv(gesamt_ects, "Gesamt-ECTS")
        addiere_monate(start, self.zeitziel.dauer_monate)
        if sum(m.ects for m in self._module) > gesamt_ects:
            raise ValueError("Der Umfang ist kleiner als die Summe der Modul-ECTS.")
        if any(m.ergebnis and m.ergebnis.datum < start for m in self._module):
            raise ValueError("Ein vorhandenes Ergebnis liegt vor dem neuen Studienbeginn.")
        if self.abschlussdatum and self.abschlussdatum < start:
            raise ValueError("Der bestätigte Abschluss liegt vor dem neuen Studienbeginn.")
        self._name, self._start, self._gesamt_ects = name, start, gesamt_ects

    def entferne_semester(self, semester: Semester) -> None:
        if semester not in self._semester:
            raise ValueError("Semester gehört nicht zu diesem Studiengang.")
        for modul in semester.module:
            modul._semester = None
        self._semester.remove(semester)
        semester._studium = None

    def erreichte_ects(self, stichtag: date) -> int:
        _datum(stichtag, "Stichtag")
        return sum(m.ects for m in self._module if m.ergebnis is not None
                   and m.ergebnis.status is Pruefungsstatus.BESTANDEN
                   and m.ergebnis.datum <= stichtag)

    def notenschnitt(self, stichtag: date) -> float | None:
        _datum(stichtag, "Stichtag")
        basis = tuple(m for m in self._module if m.ergebnis is not None
                      and m.ergebnis.status is Pruefungsstatus.BESTANDEN
                      and m.ergebnis.note is not None and m.ergebnis.datum <= stichtag)
        gewicht = sum(m.ects for m in basis)
        return (sum(m.ergebnis.note * m.ects for m in basis) / gewicht
                if gewicht else None)

    def ects_soll(self, stichtag: date) -> float:
        monate = min(abgeschlossene_monate(self.start, stichtag), self.zeitziel.dauer_monate)
        return self.gesamt_ects * monate / self.zeitziel.dauer_monate

    def abweichung(self, stichtag: date) -> float:
        return self.erreichte_ects(stichtag) - self.ects_soll(stichtag)
