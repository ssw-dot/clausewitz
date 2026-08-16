"""An unresolved term on an allow list is not always a reason to stop.

The asymmetry under test: adding an unknown entry to a list of who MAY enter
cannot remove anyone from it. So once the profile is on the list by a term we
did resolve, whatever else is on it cannot change the verdict.

The same leftover on a DENY list is dangerous -- it could be this profile's own
country under a name the table does not carry -- and must still stop the screen.

Getting this backwards has a cost in each direction. Too strict, and plainly
eligible calls get sent to a human, which trains people to ignore the warnings.
Too loose, and an exclusion nobody read becomes a green light.
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
        headcount=2,
    )
    base.update(over)
    return Profile(**base)


def call(text, *reqs) -> Call:
    return Call(name="A Call", source_text=text, requirements=tuple(reqs))


class AllowListLeftovers(unittest.TestCase):
    def test_matched_allowlist_ignores_an_unknown_sibling(self):
        """The regression this was written for.

        A real call read 'registered nonprofits and community groups'. The
        profile is a nonprofit, which is on the list. 'community_group' is not
        a term the table carries -- and the screen used to stop on it, sending
        an obviously eligible call to a human.
        """
        src = "Open to registered nonprofits and community groups operating in Mexico."
        c = call(src, Requirement("legal_form", src, ["nonprofit", "community_group"]))
        r = screen(c, profile(legal_form="nonprofit"))
        self.assertEqual(r.verdict, Verdict.ELIGIBLE)
        self.assertEqual(r.unresolved_places, ())

    def test_unmatched_allowlist_still_reports_the_unknown(self):
        """The profile is not on the list by any term we understood.

        Now the leftover matters: 'community_group' might be exactly what this
        profile is. Refusing to decide is the correct answer.
        """
        src = "Open to registered nonprofits and community groups operating in Mexico."
        c = call(src, Requirement("legal_form", src, ["charity", "community_group"]))
        r = screen(c, profile(legal_form="cooperative"))
        self.assertNotEqual(r.verdict, Verdict.ELIGIBLE)

    def test_matched_country_allowlist_ignores_an_unknown_sibling(self):
        src = "Open to organisations in Mexico, Colombia and the Southern Cone."
        c = call(src, Requirement("allowed_countries", src,
                                  ["Mexico", "Colombia", "the Southern Cone"]))
        r = screen(c, profile(country="MX"))
        self.assertEqual(r.verdict, Verdict.ELIGIBLE)

    def test_deny_list_never_ignores_an_unknown(self):
        """The dangerous direction. Quebec is not a country code, and an
        unrecognised place on a deny list could be this profile under another
        name. It must always stop the screen."""
        src = "The contest is void in Brazil, Quebec and Russia."
        c = call(src, Requirement("excluded_countries", src,
                                  ["Brazil", "Quebec", "Russia"]))
        r = screen(c, profile(country="MX"))
        self.assertEqual(r.verdict, Verdict.UNDECIDABLE)
        self.assertTrue(r.unresolved_places)

    def test_deny_list_unknown_does_not_hide_a_real_exclusion(self):
        """A resolved exclusion still wins over an unresolved one."""
        src = "The contest is void in Mexico, Quebec and Russia."
        c = call(src, Requirement("excluded_countries", src,
                                  ["Mexico", "Quebec", "Russia"]))
        r = screen(c, profile(country="MX"))
        self.assertEqual(r.verdict, Verdict.EXCLUDED)

    def test_an_exclusion_elsewhere_still_outranks_a_satisfied_allowlist(self):
        """Being on the allow list is not a pass if another rule blocks."""
        src = ("Open to registered nonprofits and community groups. "
               "At least one member must attend in person.")
        c = call(
            src,
            Requirement("legal_form", "Open to registered nonprofits and "
                                      "community groups.",
                        ["nonprofit", "community_group"]),
            Requirement("in_person_required",
                        "At least one member must attend in person.", True),
        )
        r = screen(c, profile(can_travel=False))
        self.assertEqual(r.verdict, Verdict.EXCLUDED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
