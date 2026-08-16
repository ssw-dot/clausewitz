"""No check may iterate a string as if it were a list.

Two separate bugs in this codebase were the same line written twice:

    {str(x).lower() for x in (req.value or [])}

A model writes `value="Brazil, Italy"` or `value="individual"`, Python iterates
characters, and the check compares against single letters. In the country
check that silently cleared an excluded profile. In the legal-form check it
excluded a valid one with the reason "the call requires ['a','d','i','l','n',
'u','v']".

Both were found by running the thing, not by reading it. So this file does not
test the two known sites — it sweeps every check that takes a list, so the
third one cannot be written without a test failing.
"""

from __future__ import annotations

import unittest

from clausewitz.screening import CHECKS, Profile, Requirement

# Kinds whose value is a collection. A check reading one of these must go
# through `normalise.as_list`; a check reading a scalar (a bool, a fee, a
# headcount) is not at risk and is not swept here.
LIST_VALUED = {
    "excluded_countries": ("Brazil, Italy", ["Brazil", "Italy"]),
    "allowed_countries": ("Mexico, Spain", ["Mexico", "Spain"]),
    "legal_form": ("nonprofit, company", ["nonprofit", "company"]),
}

PROFILE = Profile(
    name="Asociación Vecinal",
    country="MX",
    legal_form="nonprofit",
    can_travel=False,
    can_front_money=False,
    needs_cash_prize=True,
)


class EveryListCheckAcceptsProse(unittest.TestCase):

    def test_a_string_and_a_list_give_the_same_answer(self):
        """The invariant. If these ever diverge, a string is being iterated."""
        for kind, (written, real) in LIST_VALUED.items():
            with self.subTest(kind=kind):
                check = CHECKS[kind]
                self.assertEqual(
                    check(Requirement(kind, "quote", written), PROFILE),
                    check(Requirement(kind, "quote", real), PROFILE),
                    f"{kind} treats {written!r} differently from {real!r}, "
                    f"which means it is iterating the string as characters",
                )

    def test_no_reason_string_ever_contains_a_list_of_single_letters(self):
        """The signature the bug leaves in output a user would actually read."""
        for kind, (written, _) in LIST_VALUED.items():
            with self.subTest(kind=kind):
                reason = CHECKS[kind](Requirement(kind, "quote", written), PROFILE)
                if reason is None:
                    continue
                letters = [w for w in reason.replace("'", " ").split()
                           if len(w.strip(",[]")) == 1 and w.strip(",[]").isalpha()]
                self.assertEqual(
                    letters, [],
                    f"{kind} produced {reason!r} — single characters in a "
                    f"reason mean a string was iterated",
                )

    def test_every_list_valued_kind_is_actually_registered(self):
        """Guards the sweep itself: a renamed kind must not silently skip it."""
        for kind in LIST_VALUED:
            self.assertIn(kind, CHECKS)


class NoneAndEmptyAreNotExclusions(unittest.TestCase):

    def test_a_missing_value_never_excludes(self):
        for kind in LIST_VALUED:
            with self.subTest(kind=kind):
                self.assertIsNone(
                    CHECKS[kind](Requirement(kind, "quote", None), PROFILE))

    def test_an_empty_string_never_excludes(self):
        for kind in LIST_VALUED:
            with self.subTest(kind=kind):
                self.assertIsNone(
                    CHECKS[kind](Requirement(kind, "quote", ""), PROFILE))


if __name__ == "__main__":
    unittest.main()
