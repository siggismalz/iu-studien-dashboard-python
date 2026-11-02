"""Erzeugt die HTML-Seite. Fachregeln und SQL gehören nicht in diese Klasse."""
from datetime import date
from html import escape
from urllib.parse import urlencode

from modell import Studiengang, Pruefungsstatus


class DashboardView:
    CSS = """
    :root {--blau:#194b7c;--text:#172b3a;--grau:#53616d;--linie:#b8c3cb;--hell:#eef3f6}
    * {box-sizing:border-box} body {margin:0;background:#f6f8fa;color:var(--text);
      font:16px/1.5 Arial,sans-serif} main {max-width:1120px;margin:auto;padding:28px 24px 48px}
    h1 {font-size:30px;margin:4px 0} h2 {font-size:21px;margin:0 0 12px}
    h3 {font-size:17px;margin:0 0 10px} p {margin:8px 0 16px} a {color:var(--blau)}
    header {margin-bottom:24px} .klein,small {font-size:14px;color:var(--grau)}
    .markierung {display:inline-block;background:#dfeaf3;padding:3px 9px;font-size:14px}
    .karten {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:20px 0}
    .karte,section {background:white;border:1px solid var(--linie);border-radius:5px;padding:20px}
    .karte h2 {font-size:16px;font-weight:normal;margin:0} .wert {font-size:30px;font-weight:bold}
    .karte p {margin-bottom:0} progress {width:100%;height:15px;accent-color:var(--blau)}
    section {margin:18px 0} .ziele {display:grid;grid-template-columns:1fr 1fr;gap:24px}
    table {border-collapse:collapse;width:100%;font-size:15px} caption {text-align:left;margin:0 0 12px}
    th,td {text-align:left;padding:10px 8px;border-bottom:1px solid #dce2e7;vertical-align:top}
    th {background:var(--hell)} .tabelle {overflow-x:auto} .zahl {white-space:nowrap}
    h1,h2,h3,td,header p {overflow-wrap:anywhere}
    form {margin:12px 0} .felder {display:flex;flex-wrap:wrap;gap:12px;align-items:end}
    label {display:flex;flex-direction:column;gap:4px;flex:1;min-width:150px;font-size:14px}
    input,select,button {font:inherit;min-height:44px;border:1px solid #8596a5;border-radius:3px;padding:9px}
    input,select {background:white;color:var(--text);width:100%} button {background:var(--blau);
      color:white;border-color:var(--blau);cursor:pointer;padding:9px 16px}
    button:hover {background:#123958} :focus-visible {outline:3px solid #c56714;outline-offset:3px}
    .sekundaer {background:white;color:var(--blau)} .sekundaer:hover {background:var(--hell)}
    .meldung {padding:12px 16px;background:#eaf4ec;border-left:4px solid #307744}
    .fehler {padding:12px 16px;background:#fff0eb;border-left:4px solid #a83220}
    details {padding:8px 0} summary {cursor:pointer;font-weight:bold;min-height:44px;padding:10px 0}
    .teilen {display:grid;grid-template-columns:1fr 1fr;gap:24px}
    .hinweis {font-size:14px;color:var(--grau);margin-top:12px} footer {font-size:14px;color:var(--grau)}
    @media(max-width:720px) {.karten,.ziele,.teilen {grid-template-columns:1fr}
      main {padding:18px 14px} h1 {font-size:26px} .karte,section {padding:16px}
      .felder {align-items:stretch} label {min-width:100%} button {width:100%}}
    """

    @staticmethod
    def _zahl(wert: float | None, stellen: int = 1) -> str:
        return "Noch keine Note" if wert is None else f"{wert:.{stellen}f}".replace(".", ",")

    @staticmethod
    def _feld(name: str, titel: str, wert="", typ: str = "text", zusatz: str = "") -> str:
        return (f'<label>{escape(titel)}<input name="{name}" type="{typ}" '
                f'value="{escape(str(wert), quote=True)}" {zusatz}></label>')

    @staticmethod
    def _auswahl(name: str, titel: str, optionen, wert="") -> str:
        optionen_html = "".join(
            f'<option value="{escape(str(schluessel), quote=True)}"'
            f'{" selected" if str(schluessel) == str(wert) else ""}>{escape(text)}</option>'
            for schluessel, text in optionen)
        return f'<label>{escape(titel)}<select name="{name}">{optionen_html}</select></label>'

    def rendern(self, studium: Studiengang, stichtag: date, csrf_token: str = "",
                version: int = 0, meldung: str = "", fehler: str = "",
                modul_index: int = 0, formulardaten: dict | None = None) -> str:
        """Setzt die Seite aus Modellwerten zusammen und maskiert Benutzereingaben."""
        form = formulardaten or {}

        def wert(aktion, name, standard=""):
            return form.get(name, standard) if form.get("aktion") == aktion else standard

        def formular(aktion, inhalt, taste, modul=None):
            verborgen = {"aktion": aktion, "csrf": csrf_token, "version": version,
                         "stichtag": stichtag.isoformat()}
            if modul is not None:
                verborgen["modul"] = modul
            felder = "".join(f'<input type="hidden" name="{name}" value="{escape(str(inhalt), quote=True)}">'
                             for name, inhalt in verborgen.items())
            return f'<form method="post" action="/">{felder}<div class="felder">{inhalt}<button>{taste}</button></div></form>'

        erreicht = studium.erreichte_ects(stichtag)
        soll = studium.ects_soll(stichtag)
        abweichung = studium.abweichung(stichtag)
        schnitt = studium.notenschnitt(stichtag)
        plantext = ("im Plan" if abweichung == 0 else "hinter dem Plan" if abweichung < 0 else "vor dem Plan")
        html = [f'<!doctype html><html lang="de"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>Studien-Dashboard</title><style>{self.CSS}</style></head><body><main>',
                '<header><span class="markierung">Lokaler Studienprototyp</span><h1>Mein Studien-Dashboard</h1>',
                f'<p>{escape(studium.name)} · Beginn {studium.start:%d.%m.%Y} · {studium.gesamt_ects} ECTS</p>',
                '<p class="klein">Beim ersten Start werden frei erfundene Beispieldaten angelegt. '
                'Es besteht keine Verbindung zu myCampus.</p></header>']
        if fehler:
            html.append(f'<p class="fehler" role="alert">Nicht gespeichert: {escape(fehler)}</p>')
        if meldung:
            html.append(f'<p class="meldung" role="status">{escape(meldung)}</p>')
        html.append('<form method="get" action="/" class="felder">' +
                    self._feld("stichtag", "Stichtag für die Auswertung", stichtag.isoformat(), "date", "required") +
                    '<button>Stichtag anzeigen</button></form>')
        html.append(f'<div class="karten"><div class="karte"><h2>Studienfortschritt</h2>'
                    f'<div class="wert">{erreicht} / {studium.gesamt_ects} ECTS</div>'
                    f'<progress aria-label="Studienfortschritt" value="{erreicht}" max="{studium.gesamt_ects}"></progress>'
                    f'<p>{studium.gesamt_ects - erreicht} ECTS bis zum Gesamtumfang</p></div>'
                    f'<div class="karte"><h2>Soll-Ist-Vergleich</h2><div class="wert">'
                    f'{self._zahl(abweichung)} ECTS</div><p>Soll: {self._zahl(soll)} ECTS · {plantext}</p></div>'
                    f'<div class="karte"><h2>Laufender Notenschnitt</h2><div class="wert">'
                    f'{self._zahl(schnitt, 2)}</div><p>ECTS-gewichtet; nur bestanden und benotet</p></div></div>')
        zeit, note = [ziel.bewerten(studium, stichtag).value.replace("_", " ") for ziel in studium.ziele]
        html.append(f'<section><h2>Meine Studienziele</h2><div class="ziele"><div><h3>Abschluss in '
                    f'{studium.zeitziel.dauer_monate} Monaten</h3><p>Zieltermin: {studium.zieltermin:%d.%m.%Y}'
                    f'<br>Zeitliches Ziel: <strong>{zeit}</strong></p></div><div><h3>Abschlussnote höchstens '
                    f'{str(studium.notenziel.max_note).replace(".", ",")}</h3><p>Notenziel: <strong>{note}</strong><br>'
                    f'Der laufende Schnitt ist keine amtliche Abschlussnote.</p></div></div></section>')
        html.append('<section><h2>Module und Ergebnisse</h2><div class="tabelle"><table>'
                    '<caption>Die Ergebnisanzeige gilt für den gewählten Stichtag.</caption>'
                    '<thead><tr><th>Modul</th><th>Semester</th><th>ECTS</th><th>Ergebnis</th><th>Note</th><th>Aktion</th></tr></thead><tbody>')
        for index, modul in enumerate(studium.module):
            ergebnis = modul.ergebnis
            sichtbar = ergebnis is not None and ergebnis.datum <= stichtag
            status = (ergebnis.status.value.replace("_", " ") if sichtbar else
                      "Ergebnis nach Stichtag" if ergebnis else "offen")
            datum_text = f'<br><small>{ergebnis.datum:%d.%m.%Y}</small>' if ergebnis else ""
            notentext = self._zahl(ergebnis.note) if sichtbar and ergebnis.note is not None else "–"
            link = "/?" + urlencode({"stichtag": stichtag.isoformat(), "modul": index}) + "#bearbeiten"
            html.append(f'<tr><td>{escape(modul.titel)}</td><td>{modul.semester.nummer if modul.semester else "ohne"}</td>'
                        f'<td>{modul.ects}</td><td>{status}{datum_text}</td><td>{notentext}</td>'
                        f'<td><a href="{escape(link, quote=True)}" aria-label="{escape(modul.titel, quote=True)} bearbeiten">Bearbeiten</a></td></tr>')
        if not studium.module:
            html.append('<tr><td colspan="6">Noch keine Module vorhanden. Lege unten das erste Modul an.</td></tr>')
        html.append('</tbody></table></div><p class="hinweis">Gespeichert wird nur das aktuelle Ergebnis pro Modul. '
                    'Ein ersetzter Prüfungsversuch ist später nicht mehr verfügbar; die Stichtagsauswertung ist daher keine vollständige Historie.</p></section>')
        semester_optionen = [("", "ohne Zuordnung")] + [(s.nummer, f"Semester {s.nummer}") for s in studium.semester]
        if studium.module:
            modul_index = max(0, min(modul_index, len(studium.module) - 1))
            modul = studium.module[modul_index]
            html.append(f'<section id="bearbeiten"><h2>Bearbeiten: {escape(modul.titel)}</h2>')
            html.append(formular("modul_aendern",
                self._feld("titel", "Modultitel", wert("modul_aendern", "titel", modul.titel), zusatz='required maxlength="150"') +
                self._feld("ects", "ECTS", wert("modul_aendern", "ects", modul.ects), "number", 'required min="1"') +
                self._auswahl("semester", "Semester", semester_optionen,
                    wert("modul_aendern", "semester", modul.semester.nummer if modul.semester else "")), "Modul speichern", modul_index))
            ergebnis = modul.ergebnis
            html.append('<h3>Aktuelles Prüfungsergebnis</h3><p class="klein">Leere Note bedeutet unbenotet. '
                        'Mit „offen / Ergebnis entfernen“ wird das bisherige Ergebnis entfernt.</p>')
            html.append(formular("ergebnis",
                self._auswahl("status", "Status", [("offen", "offen / Ergebnis entfernen"),
                    ("bestanden", "bestanden"), ("nicht_bestanden", "nicht bestanden")],
                    wert("ergebnis", "status", ergebnis.status.value if ergebnis else "offen")) +
                self._feld("datum", "Prüfungsdatum", wert("ergebnis", "datum", ergebnis.datum.isoformat() if ergebnis else ""), "date") +
                self._auswahl("note", "Note (optional)", [("", "unbenotet")] +
                    [(str(n), self._zahl(n)) for n in (1.0, 1.3, 1.7, 2.0, 2.3, 2.7, 3.0, 3.3, 3.7, 4.0, 5.0)],
                    wert("ergebnis", "note", str(ergebnis.note) if ergebnis and ergebnis.note is not None else "")),
                    "Ergebnis speichern", modul_index))
            html.append('</section>')
        html.append('<section><h2>Studium verwalten</h2><details><summary>Neues Modul anlegen</summary>')
        html.append(formular("modul_neu",
            self._feld("titel", "Modultitel", wert("modul_neu", "titel"), zusatz='required maxlength="150"') +
            self._feld("ects", "ECTS", wert("modul_neu", "ects", 5), "number", 'required min="1"') +
            self._auswahl("semester", "Semester", semester_optionen, wert("modul_neu", "semester")), "Modul anlegen"))
        html.append('</details><details><summary>Semester verwalten</summary>')
        html.append(formular("semester_neu", self._feld("nummer", "Neue Semesternummer",
            wert("semester_neu", "nummer"), "number", 'required min="1"'), "Semester anlegen"))
        if studium.semester:
            html.append(formular("semester_entfernen", self._auswahl("semester", "Zu entfernendes Semester",
                semester_optionen[1:], wert("semester_entfernen", "semester")), "Semester entfernen"))
            html.append('<p class="klein">Beim Entfernen bleiben die Module und Ergebnisse erhalten; nur ihre Zuordnung entfällt.</p>')
        html.append('</details><details><summary>Ziele ändern</summary>')
        html.append(formular("ziele",
            self._feld("dauer_monate", "Zieldauer in Monaten", wert("ziele", "dauer_monate", studium.zeitziel.dauer_monate), "number", 'required min="1"') +
            self._feld("max_note", "Maximale Abschlussnote", wert("ziele", "max_note", str(studium.notenziel.max_note).replace(".", ",")), zusatz='required inputmode="decimal"'), "Ziele speichern"))
        html.append('</details><details><summary>Abschluss bestätigen oder zurücknehmen</summary>')
        html.append('<p class="klein">Nur einen tatsächlich bestätigten Abschluss eintragen. Zum Zurücknehmen beide Felder leeren.</p>')
        html.append(formular("abschluss",
            self._feld("abschlussdatum", "Bestätigtes Abschlussdatum", wert("abschluss", "abschlussdatum", studium.abschlussdatum.isoformat() if studium.abschlussdatum else ""), "date") +
            self._feld("abschlussnote", "Abschlussnote (optional)", wert("abschluss", "abschlussnote", str(studium.abschlussnote).replace(".", ",") if studium.abschlussnote is not None else ""), zusatz='inputmode="decimal"'), "Abschluss speichern"))
        html.append('</details><details><summary>Studiengang und Studienbeginn ändern</summary>')
        html.append(formular("stammdaten",
            self._feld("name", "Studiengang", wert("stammdaten", "name", studium.name), zusatz='required maxlength="150"') +
            self._feld("start", "Studienbeginn", wert("stammdaten", "start", studium.start.isoformat()), "date", "required") +
            self._feld("gesamt_ects", "Gesamtumfang in ECTS", wert("stammdaten", "gesamt_ects", studium.gesamt_ects), "number", 'required min="1"'), "Stammdaten speichern"))
        html.append('</details></section><footer>Änderungen werden nach „Speichern“ in der lokalen SQLite-Datei abgelegt. '
                    'Der Prototyp ist für eine Person auf einem Rechner vorgesehen.</footer></main></body></html>')
        # Nach einem Eingabefehler das betroffene Verwaltungsformular offen lassen.
        if fehler and form.get("aktion"):
            aktion = form["aktion"]
            for nummer, teil in enumerate(html):
                if f'name="aktion" value="{escape(aktion, quote=True)}"' in teil and nummer > 0:
                    if "<details>" in html[nummer - 1]:
                        html[nummer - 1] = html[nummer - 1].replace("<details>", "<details open>")
        return "".join(html)
