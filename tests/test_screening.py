"""Tests for the screening core.

None of these needs a model, a network or a credential. That is deliberate:
the guarantee this project sells is that a hallucination cannot become a
verdict, and a guarantee you can only test by calling an LLM is not a
guarantee.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clausewitz.screening import (  # noqa: E402
    Call,
    Profile,
    Requirement,
    Verdict,
    quote_is_grounded,
    screen,
)


def profile(**over) -> Profile:
    base = dict(
        name="Biblioteca Vecinal",
        country="MX",
        legal_form="nonprofit",
        can_travel=False,
        can_front_money=False,
        needs_cash_prize=True,
        is_student_body=False,
        headcount=2,
    )
    base.update(over)
    return Profile(**base)


def call(text, *reqs, name="A Call") -> Call:
    return Call(name=name, source_text=text, requirements=tuple(reqs))


class QuoteGrounding(unittest.TestCase):
    def test_exact_quote_is_grounded(self):
        self.assertTrue(quote_is_grounded("open to all", "This is open to all."))

    def test_invented_quote_is_not_grounded(self):
        self.assertFalse(quote_is_grounded("open to all", "Members only."))

    def test_empty_quote_is_never_grounded(self):
        # The shape a model produces when it inferred rather than read.
        self.assertFalse(quote_is_grounded("", "anything at all"))
        self.assertFalse(quote_is_grounded("   ", "anything at all"))

    def test_line_wrapping_does_not_break_a_true_quote(self):
        src = "Participants must\nattend  in person."
        self.assertTrue(quote_is_grounded("must attend in person", src))

    def test_curly_quotes_and_dashes_are_folded(self):
        src = "The organiser’s decision — final."
        self.assertTrue(quote_is_grounded("The organiser's decision - final.", src))

    def test_folding_does_not_make_different_words_equal(self):
        self.assertFalse(quote_is_grounded("must not attend", "must attend"))


class Grounding(unittest.TestCase):
    def test_ungrounded_requirement_cannot_exclude(self):
        """The core promise: an invented clause never produces a rejection."""
        c = call(
            "Open to organisations in any country.",
            Requirement("excluded_countries", quote="Mexico is excluded", value=["MX"]),
        )
        r = screen(c, profile())
        self.assertEqual(r.verdict, Verdict.UNDECIDABLE)
        self.assertEqual(r.findings, ())
        self.assertEqual(len(r.unverified), 1)

    def test_unknown_kind_is_surfaced_not_ignored(self):
        c = call(
            "Applicants must own a boat.",
            Requirement("must_own_boat", quote="Applicants must own a boat.", value=True),
        )
        r = screen(c, profile())
        self.assertEqual(r.verdict, Verdict.UNDECIDABLE)
        self.assertEqual(len(r.unknown_kinds), 1)

    def test_no_requirements_at_all_is_undecidable_not_eligible(self):
        """Silence is not a pass. Extracting nothing means we learned nothing."""
        r = screen(call("Some prose with no rules in it."), profile())
        self.assertEqual(r.verdict, Verdict.UNDECIDABLE)


class Exclusions(unittest.TestCase):
    def test_excluded_country_blocks_and_cites(self):
        src = "This contest is not open to residents of Mexico or Brazil."
        c = call(src, Requirement("excluded_countries", src, ["MX", "BR"]))
        r = screen(c, profile())
        self.assertEqual(r.verdict, Verdict.EXCLUDED)
        self.assertIn("MX", r.blocking[0].reason)
        self.assertEqual(r.blocking[0].requirement.quote, src)

    def test_allowlist_that_omits_us_blocks(self):
        src = "Open to residents of the United States and Canada only."
        c = call(src, Requirement("allowed_countries", src, ["US", "CA"]))
        self.assertEqual(screen(c, profile()).verdict, Verdict.EXCLUDED)

    def test_allowlist_that_includes_us_does_not_block(self):
        src = "Open to residents of Mexico and Canada."
        c = call(src, Requirement("allowed_countries", src, ["MX", "CA"]))
        self.assertEqual(screen(c, profile()).verdict, Verdict.ELIGIBLE)

    def test_in_person_blocks_a_profile_that_cannot_travel(self):
        src = "At least one team member must attend the ceremony in person."
        c = call(src, Requirement("in_person_required", src, True))
        r = screen(c, profile(can_travel=False))
        self.assertEqual(r.verdict, Verdict.EXCLUDED)

    def test_in_person_does_not_block_a_profile_that_can_travel(self):
        src = "At least one team member must attend the ceremony in person."
        c = call(src, Requirement("in_person_required", src, True))
        self.assertEqual(screen(c, profile(can_travel=True)).verdict, Verdict.ELIGIBLE)

    def test_non_cash_prize_blocks_when_cash_is_needed(self):
        src = "Grand Champion: $300 in Featherless AI credits"
        c = call(src, Requirement("prize_not_cash", src, True))
        r = screen(c, profile(needs_cash_prize=True))
        self.assertEqual(r.verdict, Verdict.EXCLUDED)
        self.assertIn("not money", r.blocking[0].reason)

    def test_undisclosed_prize_blocks(self):
        src = "Prizes: TBD. Further announcements will be made soon!"
        c = call(src, Requirement("prize_undisclosed", src, True))
        self.assertEqual(screen(c, profile()).verdict, Verdict.EXCLUDED)

    def test_entry_fee_blocks_when_money_cannot_be_fronted(self):
        src = "A submission fee of 25 USD applies."
        c = call(src, Requirement("entry_fee", src, 25))
        self.assertEqual(screen(c, profile(can_front_money=False)).verdict, Verdict.EXCLUDED)

    def test_entry_fee_does_not_block_when_it_can(self):
        src = "A submission fee of 25 USD applies."
        c = call(src, Requirement("entry_fee", src, 25))
        self.assertEqual(screen(c, profile(can_front_money=True)).verdict, Verdict.ELIGIBLE)

    def test_students_only_blocks_a_nonprofit(self):
        src = "All students aged 13+ are eligible to participate!"
        c = call(src, Requirement("students_only", src, True))
        self.assertEqual(screen(c, profile()).verdict, Verdict.EXCLUDED)

    def test_team_size_blocks_a_smaller_org(self):
        src = "Teams must have at least four members."
        c = call(src, Requirement("min_headcount", src, 4))
        r = screen(c, profile(headcount=2))
        self.assertEqual(r.verdict, Verdict.EXCLUDED)
        self.assertIn("has 2", r.blocking[0].reason)

    def test_every_exclusion_carries_a_quote_and_a_reason(self):
        """No bare labels. If we reject, we say which words did it."""
        src = "Not open to Mexico. Teams must have at least four members."
        c = call(
            src,
            Requirement("excluded_countries", "Not open to Mexico.", ["MX"]),
            Requirement("min_headcount", "Teams must have at least four members.", 4),
        )
        r = screen(c, profile())
        self.assertEqual(len(r.blocking), 2)
        for f in r.blocking:
            self.assertTrue(f.reason.strip())
            self.assertTrue(quote_is_grounded(f.requirement.quote, src))


class Precedence(unittest.TestCase):
    def test_a_real_block_outranks_an_unverified_claim(self):
        """One proven blocker settles it; unproven noise does not soften it."""
        src = "Not open to Mexico."
        c = call(
            src,
            Requirement("excluded_countries", "Not open to Mexico.", ["MX"]),
            Requirement("students_only", "invented sentence", True),
        )
        r = screen(c, profile())
        self.assertEqual(r.verdict, Verdict.EXCLUDED)
        self.assertEqual(len(r.unverified), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
