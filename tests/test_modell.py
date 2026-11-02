"""Die 48 Fachmodelltests aus Phase 2, erneut gegen das Phase-3-Modell ausgeführt."""
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modell import (Modul, Notenziel, Pruefungsleistung, Pruefungsstatus, Semester,
                    Studiengang, Studienziel, Zeitziel, Zielbewertung,
                    abgeschlossene_monate, addiere_monate)


def beispiel() -> Studiengang:
    return Studiengang("Synthetisch", date(2024, 10, 1), 180)


class EigenschaftenTests(unittest.TestCase):
    def test_abstrakte_klasse_nicht_instanzierbar(self):
        with self.assertRaises(TypeError):
            Studienziel()

    def test_enum_hat_genau_zwei_pruefungswerte(self):
        self.assertEqual([s.value for s in Pruefungsstatus], ["bestanden", "nicht_bestanden"])

    def test_bewertungs_enum_hat_genau_drei_werte(self):
        self.assertEqual([s.value for s in Zielbewertung], ["offen", "erreicht", "nicht_erreicht"])

    def test_string_ist_kein_status_enum(self):
        with self.assertRaises(TypeError):
            Pruefungsleistung(date(2024, 11, 1), "bestanden", 2.0)

    def test_pruefungsleistung_unveraenderlich(self):
        ergebnis = Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN, 2.0)
        with self.assertRaises(FrozenInstanceError):
            ergebnis.note = 1.0
        self.assertEqual(ergebnis.note, 2.0)

    def test_leertext_abgelehnt(self):
        with self.assertRaises(ValueError):
            Studiengang("  ", date(2024, 10, 1), 180)
        with self.assertRaises(ValueError):
            Modul("", 5)

    def test_positive_ganzzahlen_ohne_bool(self):
        for wert in (0, -1, True, 5.5):
            with self.subTest(wert=wert), self.assertRaises(ValueError):
                Modul("Synthetisch", wert)
            with self.subTest(wert=wert), self.assertRaises(ValueError):
                Zeitziel(wert)
            with self.subTest(wert=wert), self.assertRaises(ValueError):
                Semester(wert)

    def test_ungueltige_noten_abgelehnt(self):
        for wert in (0.9, 4.1, float("nan"), float("inf"), True, "2.0"):
            with self.subTest(wert=wert), self.assertRaises(ValueError):
                Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN, wert)

    def test_modulnote_diskret_abschluss_und_zielnote_kontinuierlich(self):
        with self.assertRaises(ValueError):
            Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN, 2.1)
        self.assertEqual(Notenziel(2.1).max_note, 2.1)
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 9, 30), 2.1)
        self.assertEqual(studium.abschlussnote, 2.1)

    def test_status_note_konsistenz(self):
        with self.assertRaises(ValueError):
            Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.NICHT_BESTANDEN, 2.0)
        self.assertEqual(Pruefungsleistung(date(2024, 11, 1),
                         Pruefungsstatus.NICHT_BESTANDEN, 5).note, 5.0)
        self.assertIsNone(Pruefungsleistung(date(2024, 11, 1),
                          Pruefungsstatus.NICHT_BESTANDEN).note)

    def test_datetime_anstelle_date_abgelehnt(self):
        with self.assertRaises(TypeError):
            Studiengang("Synthetisch", datetime(2024, 10, 1), 180)

    def test_oeffentliche_eigenschaften_ohne_setter(self):
        studium = beispiel()
        with self.assertRaises(AttributeError):
            studium.start = date(2023, 1, 1)
        with self.assertRaises(AttributeError):
            studium.zieltermin = date(2030, 1, 1)


class BeziehungenTests(unittest.TestCase):
    def test_genau_ein_zeit_und_notenziel(self):
        studium = beispiel()
        self.assertEqual(len(studium.ziele), 2)
        self.assertIs(studium.ziele[0], studium.zeitziel)
        self.assertIs(studium.ziele[1], studium.notenziel)
        self.assertIsInstance(studium.zeitziel, Studienziel)
        self.assertIsInstance(studium.notenziel, Studienziel)

    def test_tupel_schuetzt_sammlungen(self):
        studium = beispiel()
        semester = studium.neues_semester(1)
        studium.neues_modul("Synthetisch", 5, semester)
        self.assertIsInstance(studium.semester, tuple)
        self.assertIsInstance(studium.module, tuple)
        self.assertIsInstance(semester.module, tuple)
        with self.assertRaises(AttributeError):
            studium.module.append(Modul("Fremd", 5))

    def test_semesternummer_eindeutig(self):
        studium = beispiel()
        studium.neues_semester(1)
        with self.assertRaises(ValueError):
            studium.neues_semester(1)
        self.assertEqual(len(studium.semester), 1)

    def test_fremdes_semester_abgelehnt(self):
        studium, fremd = beispiel(), beispiel()
        semester = fremd.neues_semester(1)
        with self.assertRaises(ValueError):
            studium.neues_modul("Synthetisch", 5, semester)
        self.assertEqual(studium.module, ())

    def test_fremdes_modul_beim_umplanen_abgelehnt(self):
        studium, fremd = beispiel(), beispiel()
        modul = fremd.neues_modul("Synthetisch", 5)
        with self.assertRaises(ValueError):
            studium.ordne_zu(modul, None)

    def test_umplanen_und_optionale_zuordnung(self):
        studium = beispiel()
        erstes, zweites = studium.neues_semester(1), studium.neues_semester(2)
        modul = studium.neues_modul("Synthetisch", 5, erstes)
        studium.ordne_zu(modul, zweites)
        self.assertEqual(erstes.module, ())
        self.assertEqual(zweites.module, (modul,))
        studium.ordne_zu(modul, None)
        self.assertIsNone(modul.semester)
        self.assertIn(modul, studium.module)

    def test_semesterentfernung_erhaelt_module_und_ergebnis(self):
        studium = beispiel()
        semester = studium.neues_semester(1)
        modul = studium.neues_modul("Synthetisch", 5, semester)
        ergebnis = Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN)
        modul.setze_ergebnis(ergebnis)
        studium.entferne_semester(semester)
        self.assertEqual(studium.semester, ())
        self.assertEqual(semester.module, ())
        self.assertIsNone(modul.semester)
        self.assertIs(modul.ergebnis, ergebnis)
        self.assertIn(modul, studium.module)

    def test_fremdes_semester_nicht_entfernbar(self):
        with self.assertRaises(ValueError):
            beispiel().entferne_semester(Semester(1))

    def test_ergebnis_nicht_gleichzeitig_teilbar(self):
        studium = beispiel()
        erstes, zweites = studium.neues_modul("A", 5), studium.neues_modul("B", 5)
        ergebnis = Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN)
        erstes.setze_ergebnis(ergebnis)
        with self.assertRaises(ValueError):
            zweites.setze_ergebnis(ergebnis)
        self.assertIs(erstes.ergebnis, ergebnis)
        self.assertIsNone(zweites.ergebnis)

    def test_fremdreferenz_beim_ersetzen_erhaelt_bestehendes_ergebnis(self):
        studium = beispiel()
        erstes, zweites = studium.neues_modul("A", 5), studium.neues_modul("B", 5)
        fremd = Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN, 1.0)
        bestehend = Pruefungsleistung(date(2024, 11, 2), Pruefungsstatus.BESTANDEN, 3.0)
        erstes.setze_ergebnis(fremd)
        zweites.setze_ergebnis(bestehend)
        with self.assertRaises(ValueError):
            zweites.setze_ergebnis(fremd)
        self.assertIs(zweites.ergebnis, bestehend)
        self.assertIs(erstes.ergebnis, fremd)
        self.assertIs(bestehend._modul, zweites)
        self.assertIs(fremd._modul, erstes)

    def test_ersetzen_hat_genau_ein_aktuelles_ergebnis(self):
        studium = beispiel()
        modul = studium.neues_modul("Synthetisch", 5)
        alt = Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.NICHT_BESTANDEN, 5.0)
        neu = Pruefungsleistung(date(2024, 12, 1), Pruefungsstatus.BESTANDEN, 2.0)
        modul.setze_ergebnis(alt)
        modul.setze_ergebnis(neu)
        self.assertIs(modul.ergebnis, neu)
        self.assertIsNone(alt._modul)
        self.assertEqual(studium.erreichte_ects(date(2024, 12, 1)), 5)
        modul.setze_ergebnis(None)
        self.assertIsNone(modul.ergebnis)
        self.assertEqual(studium.erreichte_ects(date(2024, 12, 1)), 0)

    def test_studienumfang_begrenzt(self):
        studium = Studiengang("Synthetisch", date(2024, 10, 1), 10)
        studium.neues_modul("A", 10)
        with self.assertRaises(ValueError):
            studium.neues_modul("B", 5)
        self.assertEqual(len(studium.module), 1)

    def test_ergebnis_vor_studienbeginn_abgelehnt(self):
        modul = beispiel().neues_modul("Synthetisch", 5)
        with self.assertRaises(ValueError):
            modul.setze_ergebnis(Pruefungsleistung(date(2024, 9, 30), Pruefungsstatus.BESTANDEN))
        self.assertIsNone(modul.ergebnis)


class BerechnungenTests(unittest.TestCase):
    def test_zieltermin_36_monate(self):
        self.assertEqual(beispiel().zieltermin, date(2027, 10, 1))

    def test_monatsend_kappung_und_schaltjahr(self):
        self.assertEqual(addiere_monate(date(2024, 1, 31), 1), date(2024, 2, 29))
        self.assertEqual(addiere_monate(date(2023, 1, 31), 1), date(2023, 2, 28))
        self.assertEqual(addiere_monate(date(2024, 2, 29), 12), date(2025, 2, 28))

    def test_abgeschlossene_monate_mit_jahrestagsregel(self):
        self.assertEqual(abgeschlossene_monate(date(2024, 1, 31), date(2024, 2, 28)), 0)
        self.assertEqual(abgeschlossene_monate(date(2024, 1, 31), date(2024, 2, 29)), 1)
        self.assertEqual(abgeschlossene_monate(date(2024, 1, 31), date(2024, 3, 30)), 1)
        self.assertEqual(abgeschlossene_monate(date(2024, 1, 31), date(2024, 3, 31)), 2)

    def test_soll_vor_start_am_start_nach_endtermin(self):
        studium = beispiel()
        self.assertEqual(studium.ects_soll(date(2024, 9, 30)), 0.0)
        self.assertEqual(studium.ects_soll(date(2024, 10, 1)), 0.0)
        self.assertEqual(studium.ects_soll(date(2027, 10, 1)), 180.0)
        self.assertEqual(studium.ects_soll(date(2030, 1, 1)), 180.0)

    def test_soll_sechs_monate_und_abgeschlossenes_raster(self):
        studium = beispiel()
        self.assertEqual(studium.ects_soll(date(2025, 3, 31)), 25.0)
        self.assertEqual(studium.ects_soll(date(2025, 4, 1)), 30.0)

    def test_leere_notenbasis_ist_none(self):
        self.assertIsNone(beispiel().notenschnitt(date(2025, 4, 1)))

    def test_gewichtet_unbenotet_nichtbestanden_zukunft(self):
        studium = beispiel()
        daten = ((5, 1.0, Pruefungsstatus.BESTANDEN, date(2024, 11, 1)),
                 (10, 3.0, Pruefungsstatus.BESTANDEN, date(2024, 12, 1)),
                 (5, None, Pruefungsstatus.BESTANDEN, date(2025, 1, 1)),
                 (5, 5.0, Pruefungsstatus.NICHT_BESTANDEN, date(2025, 1, 2)),
                 (10, 1.0, Pruefungsstatus.BESTANDEN, date(2025, 5, 1)))
        for nr, (ects, note, status, datum) in enumerate(daten):
            studium.neues_modul(f"Synthetisch {nr}", ects).setze_ergebnis(
                Pruefungsleistung(datum, status, note))
        stichtag = date(2025, 4, 1)
        self.assertEqual(studium.erreichte_ects(stichtag), 20)
        self.assertAlmostEqual(studium.notenschnitt(stichtag), 2.3333333333333335)
        self.assertEqual(studium.ects_soll(stichtag), 30.0)
        self.assertEqual(studium.abweichung(stichtag), -10.0)
        self.assertEqual(studium.erreichte_ects(date(2025, 5, 1)), 30)

    def test_nur_unbenotet_liefert_ects_aber_keinen_schnitt(self):
        studium = beispiel()
        studium.neues_modul("Unbenotet", 5).setze_ergebnis(
            Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN))
        self.assertEqual(studium.erreichte_ects(date(2024, 11, 1)), 5)
        self.assertIsNone(studium.notenschnitt(date(2024, 11, 1)))

    def test_kennzahlen_aendern_das_modell_nicht(self):
        studium = beispiel()
        vorher = (studium.module, studium.semester, studium.ziele, studium.abschlussdatum)
        for _ in range(2):
            self.assertEqual(studium.erreichte_ects(date(2025, 4, 1)), 0)
            self.assertEqual(studium.abweichung(date(2025, 4, 1)), -30.0)
        self.assertEqual((studium.module, studium.semester, studium.ziele,
                          studium.abschlussdatum), vorher)

    def test_aktuelles_ergebnis_ist_keine_historie(self):
        studium = beispiel()
        modul = studium.neues_modul("Synthetisch", 5)
        modul.setze_ergebnis(Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN, 3.0))
        self.assertEqual(studium.erreichte_ects(date(2024, 11, 1)), 5)
        modul.setze_ergebnis(Pruefungsleistung(date(2024, 12, 1), Pruefungsstatus.BESTANDEN, 2.0))
        self.assertEqual(studium.erreichte_ects(date(2024, 11, 1)), 0)
        self.assertIsNone(studium.notenschnitt(date(2024, 11, 1)))


class ZielTests(unittest.TestCase):
    def test_zeitziel_offen_bis_einschliesslich_zieltermin(self):
        studium = beispiel()
        self.assertIs(studium.zeitziel.bewerten(studium, date(2027, 9, 30)), Zielbewertung.OFFEN)
        self.assertIs(studium.zeitziel.bewerten(studium, date(2027, 10, 1)), Zielbewertung.OFFEN)
        self.assertIs(studium.zeitziel.bewerten(studium, date(2027, 10, 2)), Zielbewertung.NICHT_ERREICHT)

    def test_bestaetigter_abschluss_am_zieltermin_erreicht(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 10, 1), 2.0)
        self.assertIs(studium.zeitziel.bewerten(studium, date(2027, 10, 1)), Zielbewertung.ERREICHT)

    def test_verspaeteter_abschluss_nicht_erreicht(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 10, 2), 2.0)
        self.assertIs(studium.zeitziel.bewerten(studium, date(2027, 10, 2)), Zielbewertung.NICHT_ERREICHT)

    def test_abschluss_in_zukunft_wird_am_stichtag_ignoriert(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 9, 30), 1.0)
        self.assertIs(studium.zeitziel.bewerten(studium, date(2026, 1, 1)), Zielbewertung.OFFEN)
        self.assertIs(studium.notenziel.bewerten(studium, date(2026, 1, 1)), Zielbewertung.OFFEN)

    def test_laufender_schnitt_bewertet_keinen_abschluss(self):
        studium = beispiel()
        studium.neues_modul("Synthetisch", 5).setze_ergebnis(
            Pruefungsleistung(date(2024, 11, 1), Pruefungsstatus.BESTANDEN, 1.0))
        self.assertEqual(studium.notenschnitt(date(2024, 11, 1)), 1.0)
        self.assertIs(studium.notenziel.bewerten(studium, date(2024, 11, 1)), Zielbewertung.OFFEN)

    def test_notenziel_grenzwert_erreicht(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 9, 30), 2.0)
        self.assertIs(studium.notenziel.bewerten(studium, date(2027, 9, 30)), Zielbewertung.ERREICHT)

    def test_notenziel_ueber_grenzwert_nicht_erreicht(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 9, 30), 2.1)
        self.assertIs(studium.notenziel.bewerten(studium, date(2027, 9, 30)), Zielbewertung.NICHT_ERREICHT)

    def test_abschluss_ohne_note_laesst_notenziel_offen(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 9, 30))
        self.assertIs(studium.notenziel.bewerten(studium, date(2027, 10, 1)), Zielbewertung.OFFEN)

    def test_abschlussnote_ohne_datum_abgelehnt(self):
        with self.assertRaises(ValueError):
            Studiengang("Synthetisch", date(2024, 10, 1), 180, abschlussnote=2.0)

    def test_ungueltige_abschlussaenderung_bleibt_atomar(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 9, 30), 2.0)
        with self.assertRaises(ValueError):
            studium.bestaetige_abschluss(date(2024, 9, 30), 1.0)
        self.assertEqual(studium.abschlussdatum, date(2027, 9, 30))
        self.assertEqual(studium.abschlussnote, 2.0)

    def test_ziele_anpassen_aktualisiert_zieltermin(self):
        studium = beispiel()
        studium.passe_ziele_an(24, 1.7)
        self.assertEqual(studium.zieltermin, date(2026, 10, 1))
        self.assertEqual(studium.notenziel.max_note, 1.7)
        self.assertEqual(studium.ects_soll(date(2025, 4, 1)), 45.0)
        self.assertEqual(len(studium.ziele), 2)

    def test_ungueltige_zielaenderung_erhaelt_beide_alten_ziele(self):
        studium = beispiel()
        vorher = studium.ziele
        with self.assertRaises(ValueError):
            studium.passe_ziele_an(24, 0.0)
        self.assertIs(studium.zeitziel, vorher[0])
        self.assertIs(studium.notenziel, vorher[1])
        self.assertEqual(studium.zieltermin, date(2027, 10, 1))

    def test_polymorphie_hat_unterschiedliche_kriterien(self):
        studium = beispiel()
        studium.bestaetige_abschluss(date(2027, 9, 30), 2.3)
        self.assertEqual([z.bewerten(studium, date(2027, 10, 1)) for z in studium.ziele],
                         [Zielbewertung.ERREICHT, Zielbewertung.NICHT_ERREICHT])


if __name__ == "__main__":
    unittest.main(verbosity=2)
