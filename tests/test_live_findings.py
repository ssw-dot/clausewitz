"""Four bugs, all found by running the tool, none visible by reading it.

One fixture — a fund open to nonprofits in Mexico, Colombia and Peru, screened
against a Mexican nonprofit library. The right answer is ELIGIBLE and it took
four fixes to get there:

  1. EXCLUDED   legal_form compared "nonprofit" against the literal string
                "nonprofit organisations, community interest companies", so
                the call that accepts this profile rejected it.
  2. UNDECIDABLE the model answered in alpha-3 ("MEX, COL, PER") and the
                table only read alpha-2 and names.
  3. UNDECIDABLE with the report claiming "no eligibility criteria could be
                extracted at all" — untrue, and it blamed the document for a
                gap in this code.
  4. UNDECIDABLE Colombia and Peru were simply missing from the table, in a
                project whose users are Latin American community groups.

Every one of them failed quietly. Only the first was visible in the output,
and only because it printed a list of single letters.
"""

from __future__ import annotations

import unittest

from clausewitz.normalise import countries, legal_forms
from clausewitz.report import render
from clausewitz.screening import Call, Profile, Requirement, Verdict, screen

LIBRARY = Profile(
    name="Biblioteca Vecinal San Andrés",
    country="MX",
    legal_form="nonprofit",
    can_travel=False,
    can_front_money=False,
    needs_cash_prize=True,
)

RULES = (
    "Applications are accepted from registered nonprofit organisations and "
    "community interest companies. This fund is open to organisations based "
    "in Mexico, Colombia and Peru only."
)

FUND = Call(
    name="Neighbourhood Green Spaces Fund",
    source_text=RULES,
    requirements=(
        Requirement("legal_form",
                    "Applications are accepted from registered nonprofit "
                    "organisations and community interest companies.",
                    "nonprofit organisations, community interest companies"),
        Requirement("allowed_countries",
                    "This fund is open to organisations based in Mexico, "
                    "Colombia and Peru only.",
                    "MEX, COL, PER"),
    ),
)


class TheLibraryQualifies(unittest.TestCase):
    """The end state. If this regresses, a real user is told not to apply."""

    def test_a_mexican_nonprofit_is_eligible_for_a_fund_that_wants_exactly_that(self):
        result = screen(FUND, LIBRARY)
        self.assertIs(result.verdict, Verdict.ELIGIBLE,
                      f"findings={[f.reason for f in result.findings]} "
                      f"unresolved={result.unresolved_places}")


class PhrasingIsNotAVocabulary(unittest.TestCase):

    def test_nonprofit_organisations_means_nonprofit(self):
        forms, unresolved = legal_forms("nonprofit organisations")
        self.assertEqual(forms, ["nonprofit"])
        self.assertEqual(unresolved, [])

    def test_a_call_accepting_this_profile_does_not_exclude_it(self):
        req = Requirement("legal_form", "quote",
                          "nonprofit organisations, community interest companies")
        from clausewitz.screening import CHECKS
        self.assertIsNone(CHECKS["legal_form"](req, LIBRARY))

    def test_an_unknown_form_does_not_exclude_either(self):
        """The safe direction: unknown means ask, not refuse."""
        from clausewitz.screening import CHECKS
        req = Requirement("legal_form", "quote", "cabildo abierto")
        self.assertIsNone(CHECKS["legal_form"](req, LIBRARY),
                          "an unrecognised legal form must not produce a "
                          "rejection; it must produce a question")


class ModelsWriteAlphaThree(unittest.TestCase):

    def test_alpha3_resolves(self):
        codes, unresolved = countries("MEX, COL, PER")
        self.assertEqual(sorted(codes), ["CO", "MX", "PE"])
        self.assertEqual(unresolved, [])

    def test_alpha2_and_alpha3_agree(self):
        self.assertEqual(sorted(countries("MEX, COL")[0]),
                         sorted(countries("MX, CO")[0]))

    def test_latin_america_is_in_the_table_by_name(self):
        for name, code in [("Colombia", "CO"), ("Peru", "PE"),
                           ("Chile", "CL"), ("Guatemala", "GT"),
                           ("Bolivia", "BO"), ("Costa Rica", "CR")]:
            with self.subTest(name=name):
                self.assertEqual(countries(name)[0], [code])


class TheReportDoesNotBlameTheDocument(unittest.TestCase):

    def test_an_unresolved_term_is_named_rather_than_called_nothing(self):
        call = Call(
            name="A fund naming somewhere unmapped",
            source_text="Open to organisations based in Freedonia.",
            requirements=(
                Requirement("allowed_countries",
                            "Open to organisations based in Freedonia.",
                            "Freedonia"),
            ),
        )
        text = render([screen(call, LIBRARY)], LIBRARY)
        self.assertIn("Freedonia", text)
        self.assertNotIn("no eligibility criteria could be extracted at all", text,
                         "the rules were read; saying otherwise blames the "
                         "document for a gap in this screener")


if __name__ == "__main__":
    unittest.main()
