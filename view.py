"""Erzeugt die Dashboard-Seite aus den Werten des Studiengangs."""
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlencode

from modell import Studiengang


class DashboardView:
    def rendern(self, studium: Studiengang, stichtag: date, csrf_token: str = "",
                version: int = 0, meldung: str = "", fehler: str = "",
                modul_index: int = 0, formulardaten: dict | None = None) -> str:
        css = Path(__file__).with_name("style.css").read_text(encoding="utf-8")
        form = formulardaten or {}

        # Diese Angaben braucht der Handler bei jedem abgesendeten Formular.
        verborgen = self._verborgen("csrf", csrf_token)
        verborgen += self._verborgen("version", version)
        verborgen += self._verborgen("stichtag", stichtag.isoformat())

        hinweis = ""
        if fehler:
            hinweis += f'<p class="fehler" role="alert">Nicht gespeichert: {escape(fehler)}</p>'
        if meldung:
            hinweis += f'<p class="meldung" role="status">{escape(meldung)}</p>'

        datumsfeld = self._feld("stichtag", "Stichtag für die Auswertung",
                               stichtag.isoformat(), "date", "required")
        return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Studien-Dashboard</title>
    <style>{css}</style>
</head>
<body>
<main>
    <header>
        <span class="markierung">Lokaler Studienprototyp</span>
        <h1>Mein Studien-Dashboard</h1>
        <p>{escape(studium.name)} · Beginn {studium.start:%d.%m.%Y} · {studium.gesamt_ects} ECTS</p>
        <p class="klein">Beim ersten Start werden frei erfundene Beispieldaten angelegt.
        Es besteht keine Verbindung zu myCampus.</p>
    </header>
    {hinweis}
    <form method="get" action="/" class="felder">
        {datumsfeld}
        <button>Stichtag anzeigen</button>
    </form>
    {self._kennzahlen(studium, stichtag)}
    {self._ziele(studium, stichtag)}
    {self._modultabelle(studium, stichtag)}
    {self._modul_bearbeiten(studium, modul_index, form, verborgen)}
    {self._verwaltung(studium, form, verborgen, fehler)}
    <footer>Änderungen werden nach „Speichern“ in der lokalen SQLite-Datei abgelegt.
    Der Prototyp ist für eine Person auf einem Rechner vorgesehen.</footer>
</main>
</body>
</html>"""

    def _kennzahlen(self, studium, stichtag):
        erreicht = studium.erreichte_ects(stichtag)
        soll = studium.ects_soll(stichtag)
        abweichung = studium.abweichung(stichtag)
        schnitt = studium.notenschnitt(stichtag)
        if abweichung < 0:
            plantext = "hinter dem Plan"
        elif abweichung > 0:
            plantext = "vor dem Plan"
        else:
            plantext = "im Plan"

        return f"""
<div class="karten">
    <div class="karte">
        <h2>Studienfortschritt</h2>
        <div class="wert">{erreicht} / {studium.gesamt_ects} ECTS</div>
        <progress aria-label="Studienfortschritt" value="{erreicht}" max="{studium.gesamt_ects}"></progress>
        <p>{studium.gesamt_ects - erreicht} ECTS bis zum Gesamtumfang</p>
    </div>
    <div class="karte">
        <h2>Soll-Ist-Vergleich</h2>
        <div class="wert">{self._zahl(abweichung)} ECTS</div>
        <p>Soll: {self._zahl(soll)} ECTS · {plantext}</p>
    </div>
    <div class="karte">
        <h2>Laufender Notenschnitt</h2>
        <div class="wert">{self._zahl(schnitt, 2)}</div>
        <p>ECTS-gewichtet; nur bestanden und benotet</p>
    </div>
</div>"""

    def _ziele(self, studium, stichtag):
        zeit = studium.zeitziel.bewerten(studium, stichtag).value.replace("_", " ")
        note = studium.notenziel.bewerten(studium, stichtag).value.replace("_", " ")
        zielnote = str(studium.notenziel.max_note).replace(".", ",")
        return f"""
<section>
    <h2>Meine Studienziele</h2>
    <div class="ziele">
        <div>
            <h3>Abschluss in {studium.zeitziel.dauer_monate} Monaten</h3>
            <p>Zieltermin: {studium.zieltermin:%d.%m.%Y}<br>
            Zeitliches Ziel: <strong>{zeit}</strong></p>
        </div>
        <div>
            <h3>Abschlussnote höchstens {zielnote}</h3>
            <p>Notenziel: <strong>{note}</strong><br>
            Der laufende Schnitt ist keine amtliche Abschlussnote.</p>
        </div>
    </div>
</section>"""

    def _modultabelle(self, studium, stichtag):
        zeilen = []
        for index, modul in enumerate(studium.module):
            status = "offen"
            notentext = "–"
            datum_text = ""
            ergebnis = modul.ergebnis
            if ergebnis is not None:
                datum_text = f'<br><small>{ergebnis.datum:%d.%m.%Y}</small>'
                if ergebnis.datum > stichtag:
                    status = "Ergebnis nach Stichtag"
                else:
                    status = ergebnis.status.value.replace("_", " ")
                    if ergebnis.note is not None:
                        notentext = self._zahl(ergebnis.note)

            semester = "ohne"
            if modul.semester is not None:
                semester = modul.semester.nummer
            link = "/?" + urlencode({"stichtag": stichtag.isoformat(), "modul": index})
            link += "#bearbeiten"
            zeilen.append(f"""
<tr>
    <td>{escape(modul.titel)}</td>
    <td>{semester}</td>
    <td>{modul.ects}</td>
    <td>{status}{datum_text}</td>
    <td>{notentext}</td>
    <td><a href="{escape(link)}" aria-label="{escape(modul.titel)} bearbeiten">Bearbeiten</a></td>
</tr>""")
        if not zeilen:
            zeilen.append('<tr><td colspan="6">Noch keine Module vorhanden. Lege unten das erste Modul an.</td></tr>')

        return f"""
<section>
    <h2>Module und Ergebnisse</h2>
    <div class="tabelle">
        <table>
            <caption>Die Ergebnisanzeige gilt für den gewählten Stichtag.</caption>
            <thead><tr><th>Modul</th><th>Semester</th><th>ECTS</th><th>Ergebnis</th><th>Note</th><th>Aktion</th></tr></thead>
            <tbody>{''.join(zeilen)}</tbody>
        </table>
    </div>
    <p class="hinweis">Gespeichert wird nur das aktuelle Ergebnis pro Modul.
    Ein ersetzter Prüfungsversuch ist später nicht mehr verfügbar; die Stichtagsauswertung ist daher keine vollständige Historie.</p>
</section>"""

    def _modul_bearbeiten(self, studium, index, form, verborgen):
        if not studium.module:
            return ""
        index = max(0, min(index, len(studium.module) - 1))
        modul = studium.module[index]
        semester = modul.semester.nummer if modul.semester else ""
        werte = self._formwerte(form, "modul_aendern")
        felder = self._feld("titel", "Modultitel", werte.get("titel", modul.titel),
                            zusatz='required maxlength="150"')
        felder += self._feld("ects", "ECTS", werte.get("ects", modul.ects), "number", 'required min="1"')
        felder += self._auswahl("semester", "Semester", self._semester_optionen(studium),
                                werte.get("semester", semester))
        modulformular = self._formular("modul_aendern", felder, "Modul speichern", verborgen, index)

        status = "offen"
        datum = ""
        note = ""
        if modul.ergebnis is not None:
            status = modul.ergebnis.status.value
            datum = modul.ergebnis.datum.isoformat()
            if modul.ergebnis.note is not None:
                note = str(modul.ergebnis.note)

        status_optionen = [("offen", "offen / Ergebnis entfernen"),
                           ("bestanden", "bestanden"), ("nicht_bestanden", "nicht bestanden")]
        noten_optionen = [("", "unbenotet")]
        for zahl in (1.0, 1.3, 1.7, 2.0, 2.3, 2.7, 3.0, 3.3, 3.7, 4.0, 5.0):
            noten_optionen.append((str(zahl), self._zahl(zahl)))

        werte = self._formwerte(form, "ergebnis")
        felder = self._auswahl("status", "Status", status_optionen, werte.get("status", status))
        felder += self._feld("datum", "Prüfungsdatum", werte.get("datum", datum), "date")
        felder += self._auswahl("note", "Note (optional)", noten_optionen, werte.get("note", note))
        ergebnisformular = self._formular("ergebnis", felder, "Ergebnis speichern", verborgen, index)
        return f"""
<section id="bearbeiten">
    <h2>Bearbeiten: {escape(modul.titel)}</h2>
    {modulformular}
    <h3>Aktuelles Prüfungsergebnis</h3>
    <p class="klein">Leere Note bedeutet unbenotet.
    Mit „offen / Ergebnis entfernen“ wird das bisherige Ergebnis entfernt.</p>
    {ergebnisformular}
</section>"""

    def _verwaltung(self, studium, form, verborgen, fehler):
        teile = ['<section><h2>Studium verwalten</h2>']
        fehlerhafte_aktion = form.get("aktion", "") if fehler else ""

        werte = self._formwerte(form, "modul_neu")
        felder = self._feld("titel", "Modultitel", werte.get("titel", ""), zusatz='required maxlength="150"')
        felder += self._feld("ects", "ECTS", werte.get("ects", 5), "number", 'required min="1"')
        felder += self._auswahl("semester", "Semester", self._semester_optionen(studium), werte.get("semester", ""))
        inhalt = self._formular("modul_neu", felder, "Modul anlegen", verborgen)
        teile.append(self._klappbereich("Neues Modul anlegen", inhalt, fehlerhafte_aktion == "modul_neu"))

        werte = self._formwerte(form, "semester_neu")
        felder = self._feld("nummer", "Neue Semesternummer", werte.get("nummer", ""), "number", 'required min="1"')
        inhalt = self._formular("semester_neu", felder, "Semester anlegen", verborgen)
        if studium.semester:
            werte = self._formwerte(form, "semester_entfernen")
            felder = self._auswahl("semester", "Zu entfernendes Semester",
                                   self._semester_optionen(studium)[1:], werte.get("semester", ""))
            inhalt += self._formular("semester_entfernen", felder, "Semester entfernen", verborgen)
            inhalt += ('<p class="klein">Beim Entfernen bleiben die Module und Ergebnisse erhalten; '
                       'nur ihre Zuordnung entfällt.</p>')
        offen = fehlerhafte_aktion in ("semester_neu", "semester_entfernen")
        teile.append(self._klappbereich("Semester verwalten", inhalt, offen))

        werte = self._formwerte(form, "ziele")
        felder = self._feld("dauer_monate", "Zieldauer in Monaten",
                            werte.get("dauer_monate", studium.zeitziel.dauer_monate), "number", 'required min="1"')
        # In Formularen die vollständige Note verwenden, damit erneutes Speichern nichts rundet.
        zielnote = str(studium.notenziel.max_note).replace(".", ",")
        felder += self._feld("max_note", "Maximale Abschlussnote", werte.get("max_note", zielnote),
                             zusatz='required inputmode="decimal"')
        inhalt = self._formular("ziele", felder, "Ziele speichern", verborgen)
        teile.append(self._klappbereich("Ziele ändern", inhalt, fehlerhafte_aktion == "ziele"))

        werte = self._formwerte(form, "abschluss")
        datum = studium.abschlussdatum.isoformat() if studium.abschlussdatum else ""
        note = ""
        if studium.abschlussnote is not None:
            note = str(studium.abschlussnote).replace(".", ",")
        felder = self._feld("abschlussdatum", "Bestätigtes Abschlussdatum", werte.get("abschlussdatum", datum), "date")
        felder += self._feld("abschlussnote", "Abschlussnote (optional)", werte.get("abschlussnote", note),
                             zusatz='inputmode="decimal"')
        inhalt = ('<p class="klein">Nur einen tatsächlich bestätigten Abschluss eintragen. '
                  'Zum Zurücknehmen beide Felder leeren.</p>')
        inhalt += self._formular("abschluss", felder, "Abschluss speichern", verborgen)
        teile.append(self._klappbereich("Abschluss bestätigen oder zurücknehmen", inhalt,
                                        fehlerhafte_aktion == "abschluss"))

        werte = self._formwerte(form, "stammdaten")
        felder = self._feld("name", "Studiengang", werte.get("name", studium.name), zusatz='required maxlength="150"')
        felder += self._feld("start", "Studienbeginn", werte.get("start", studium.start.isoformat()), "date", "required")
        felder += self._feld("gesamt_ects", "Gesamtumfang in ECTS", werte.get("gesamt_ects", studium.gesamt_ects),
                             "number", 'required min="1"')
        inhalt = self._formular("stammdaten", felder, "Stammdaten speichern", verborgen)
        teile.append(self._klappbereich("Studiengang und Studienbeginn ändern", inhalt,
                                        fehlerhafte_aktion == "stammdaten"))
        teile.append('</section>')
        return "".join(teile)

    # Kleine Hilfsmethoden für die wiederkehrenden HTML-Elemente.
    def _zahl(self, wert, stellen=1):
        if wert is None:
            return "Noch keine Note"
        return f"{wert:.{stellen}f}".replace(".", ",")

    def _feld(self, name, titel, wert="", typ="text", zusatz=""):
        return f"""<label>{escape(titel)}
    <input name="{name}" type="{typ}" value="{escape(str(wert))}" {zusatz}>
</label>"""

    def _auswahl(self, name, titel, optionen, wert=""):
        html = f'<label>{escape(titel)}<select name="{name}">'
        for schluessel, text in optionen:
            ausgewaehlt = ""
            if str(schluessel) == str(wert):
                ausgewaehlt = " selected"
            html += f'<option value="{escape(str(schluessel))}"{ausgewaehlt}>{escape(text)}</option>'
        return html + '</select></label>'

    def _verborgen(self, name, wert):
        return f'<input type="hidden" name="{name}" value="{escape(str(wert))}">'

    def _formular(self, aktion, felder, taste, verborgen, modul=None):
        angaben = self._verborgen("aktion", aktion) + verborgen
        if modul is not None:
            angaben += self._verborgen("modul", modul)
        return f"""<form method="post" action="/">
    {angaben}
    <div class="felder">{felder}<button>{taste}</button></div>
</form>"""

    def _formwerte(self, form, aktion):
        # Nach einem Fehler nur das abgesendete Formular mit seinen Eingaben füllen.
        if form.get("aktion") == aktion:
            return form
        return {}

    def _semester_optionen(self, studium):
        optionen = [("", "ohne Zuordnung")]
        for semester in studium.semester:
            optionen.append((semester.nummer, f"Semester {semester.nummer}"))
        return optionen

    def _klappbereich(self, titel, inhalt, offen):
        attribut = " open" if offen else ""
        return f'<details{attribut}><summary>{titel}</summary>{inhalt}</details>'
