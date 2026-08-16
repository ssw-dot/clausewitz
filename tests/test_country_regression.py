"""The country bug, tested where it actually bit: through `screen`.

`test_normalise.py` proves the parsing. This proves the verdict — which is the
only thing a user ever sees, and the only place the bug could hurt anyone.

The value strings here are not invented for the test. They are what the live
agent returned when it read the real AWS Trainium rules.
"""

from __future__ import annotations

import unittest

from clausewitz.screening import Call, Profile, Requirement, Verdict, screen

RULES = (
    "The Challenge is open to individuals who are at least the age of majority "
    "in their jurisdiction of residence. Void in Brazil, Italy, Quebec, and "
    "where prohibited by law."
)

MEXICO = Profile(
    name="Asociación Vecinal",
    country="MX",
    legal_form="nonprofit",
    can_travel=False,
    can_front_money=False,
    needs_cash_prize=True,
)

BRAZIL = Profile(
    name="Associação de Bairro",
    country="BR",
    legal_form="nonprofit",
    can_travel=False,
    can_front_money=False,
    needs_cash_prize=True,
)


def call_with(value):
    return Call(
        name="AWS Trainium Frontier Challenge",
        source_text=RULES,
        requirements=(
            Requirement(
                kind="excluded_countries",
                quote="Void in Brazil, Italy, Quebec, and where prohibited by law.",
                value=value,
            ),
        ),
    )


class AWrittenListMustStillExclude(unittest.TestCase):
    """Before the fix this returned ELIGIBLE. Silently."""

    def test_a_brazilian_profile_is_excluded_by_a_comma_separated_string(self):
        result = screen(call_with("Brazil, Italy, Quebec"), BRAZIL)
        self.assertIs(result.verdict, Verdict.EXCLUDED)
        self.assertTrue(result.findings)
        self.assertIn("BR", result.findings[0].reason)

    def test_the_same_call_as_a_real_list_behaves_identically(self):
        as_string = screen(call_with("Brazil, Italy, Quebec"), BRAZIL)
        as_list = screen(call_with(["Brazil", "Italy", "Quebec"]), BRAZIL)
        self.assertIs(as_string.verdict, as_list.verdict)

    def test_country_names_are_matched_against_codes(self):
        """The profile says BR. The call says "Brazil". Those must meet."""
        result = screen(call_with("Brazil"), BRAZIL)
        self.assertIs(result.verdict, Verdict.EXCLUDED)


class AnUnresolvedPlaceIsAQuestionNotAPass(unittest.TestCase):

    def test_quebec_makes_the_call_undecidable_rather_than_eligible(self):
        result = screen(call_with("Brazil, Italy, Quebec"), MEXICO)
        self.assertIs(result.verdict, Verdict.UNDECIDABLE,
                      "Mexico is not excluded by name, but the call also bars "
                      "Quebec, which this code cannot evaluate. Clearing the "
                      "profile would be claiming an understanding it lacks")
        self.assertTrue(result.unresolved_places)
        self.assertEqual(result.unresolved_places[0][1], "Quebec")

    def test_a_clean_list_with_no_strays_can_still_be_eligible(self):
        clean = Call(
            name="A tidy call",
            source_text="Void in Brazil and Italy.",
            requirements=(
                Requirement(kind="excluded_countries",
                            quote="Void in Brazil and Italy.",
                            value="Brazil, Italy"),
            ),
        )
        self.assertIs(screen(clean, MEXICO).verdict, Verdict.ELIGIBLE)

    def test_an_unknown_country_does_not_quietly_disappear(self):
        odd = Call(
            name="A call naming somewhere unmapped",
            source_text="Void in Freedonia.",
            requirements=(
                Requirement(kind="excluded_countries",
                            quote="Void in Freedonia.",
                            value="Freedonia"),
            ),
        )
        result = screen(odd, MEXICO)
        self.assertIs(result.verdict, Verdict.UNDECIDABLE)
        self.assertEqual(result.unresolved_places[0][1], "Freedonia")


class TheFailureDirectionIsTheWholePoint(unittest.TestCase):

    def test_uncertainty_never_produces_eligible(self):
        """Across every shape of country value, ELIGIBLE requires certainty."""
        shapes = ["Brazil, Italy, Quebec", "Quebec", "Freedonia",
                  ["Quebec"], "Crimea", "where prohibited by law"]
        for value in shapes:
            with self.subTest(value=value):
                verdict = screen(call_with(value), MEXICO).verdict
                self.assertIsNot(
                    verdict, Verdict.ELIGIBLE,
                    f"{value!r} contains something unevaluated; clearing the "
                    f"profile on it is the failure this product must not have",
                )


if __name__ == "__main__":
    unittest.main()
