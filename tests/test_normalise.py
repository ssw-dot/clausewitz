"""The bug these tests exist for was real, silent, and pointed the wrong way.

A live run of the agent against the AWS Trainium rules returned:

    kind  = excluded_countries
    value = "Brazil, Italy, Quebec"        <- a string, not a list

`screening._check_excluded_countries` does `for c in (req.value or [])`. Given
a string, Python iterates characters, the comparison set becomes single
letters, and no two-letter country code can ever match. The call excludes you
and the screen clears you.

Nothing raises. Nothing logs. The report reads "ELIGIBLE".
"""

from __future__ import annotations

import unittest

from clausewitz.normalise import as_list, countries


class TheBugThatStartedThis(unittest.TestCase):

    def test_a_written_list_is_not_iterated_as_characters(self):
        self.assertEqual(as_list("Brazil, Italy, Quebec"),
                         ["Brazil", "Italy", "Quebec"])

    def test_the_exact_value_from_the_live_run_resolves(self):
        codes, unresolved = countries("Brazil, Italy, Quebec")
        self.assertIn("BR", codes)
        self.assertIn("IT", codes)
        self.assertEqual(unresolved, ["Quebec"])

    def test_an_excluded_country_is_actually_caught(self):
        """The failure mode, stated as the thing that must not happen."""
        codes, _ = countries("Brazil, Mexico, Italy")
        self.assertIn("MX", codes,
                      "a call excluding Mexico must produce MX, or a "
                      "Mexico-based profile is cleared by a call that bars it")


class ProseIsNotAList(unittest.TestCase):

    def test_and_separates_as_well_as_commas(self):
        self.assertEqual(as_list("Brazil, Italy and Spain"),
                         ["Brazil", "Italy", "Spain"])

    def test_where_prohibited_by_law_is_not_a_place(self):
        codes, unresolved = countries("Brazil, and where prohibited by law")
        self.assertEqual(codes, ["BR"])
        self.assertEqual(len(unresolved), 1)

    def test_a_real_list_survives_untouched(self):
        self.assertEqual(as_list(["BR", "IT"]), ["BR", "IT"])

    def test_none_is_empty_not_a_crash(self):
        self.assertEqual(as_list(None), [])


class NamesAndCodes(unittest.TestCase):

    def test_codes_pass_through_uppercased(self):
        codes, unresolved = countries(["br", "It"])
        self.assertEqual(sorted(codes), ["BR", "IT"])
        self.assertEqual(unresolved, [])

    def test_accents_and_articles_do_not_defeat_the_table(self):
        self.assertEqual(countries("the United States")[0], ["US"])
        self.assertEqual(countries("México")[0], ["MX"])

    def test_a_country_not_in_the_table_is_surfaced_never_dropped(self):
        codes, unresolved = countries("Freedonia")
        self.assertEqual(codes, [])
        self.assertEqual(unresolved, ["Freedonia"],
                         "an unknown place must become a question; dropping it "
                         "deletes an exclusion the call actually made")


class SubNationalJurisdictions(unittest.TestCase):
    """Quebec is the one that appears in nearly every set of contest rules."""

    def test_quebec_does_not_become_canada(self):
        codes, unresolved = countries("Quebec")
        self.assertNotIn("CA", codes,
                         "excluding Quebec does not exclude Canada; mapping it "
                         "there would bar every Canadian entrant")
        self.assertEqual(unresolved, ["Quebec"])

    def test_crimea_does_not_become_ukraine_or_russia(self):
        codes, unresolved = countries("Crimea")
        self.assertEqual(codes, [])
        self.assertEqual(unresolved, ["Crimea"])


if __name__ == "__main__":
    unittest.main()
