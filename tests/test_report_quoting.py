"""Where a quotation ends is part of the quotation.

This tool's promise is "here is the sentence that disqualifies you". If the
closing quotation mark lands three words early, the reader is told the citation
stopped there and the remaining words are ours -- which is the one thing the
output must never imply about text we took from someone else's rules.

Found by rendering the real fixtures and reading them, not by reasoning about
textwrap.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clausewitz.report import _quote  # noqa: E402

LONG = ("At least one team member must attend the NeurIPS 2026 presentation "
        "in person, and travel costs are not reimbursed by the organisers.")


class Quoting(unittest.TestCase):
    def test_a_short_quote_is_bracketed_on_one_line(self):
        self.assertEqual(_quote("Prizes: TBD.", indent=""), '"Prizes: TBD."')

    def test_a_wrapped_quote_opens_once_and_closes_once(self):
        rendered = _quote(LONG, indent="")
        self.assertGreater(len(rendered.splitlines()), 1, "fixture must wrap")
        self.assertEqual(rendered.count('"'), 2)

    def test_the_closing_mark_is_at_the_very_end(self):
        rendered = _quote(LONG, indent="")
        self.assertTrue(rendered.startswith('"'))
        self.assertTrue(rendered.endswith('"'))
        self.assertNotIn('"\n', rendered)   # never closes mid-quote

    def test_the_words_survive_the_wrapping(self):
        """Bracketing is worthless if the text inside changed."""
        rendered = _quote(LONG, indent="        ")
        self.assertEqual(" ".join(rendered.replace('"', "").split()), LONG)

    def test_truncation_still_closes(self):
        rendered = _quote("word " * 200, indent="")
        self.assertTrue(rendered.endswith('..."'))
        self.assertEqual(rendered.count('"'), 2)

    def test_empty_text_does_not_produce_a_dangling_mark(self):
        self.assertEqual(_quote("   ", indent=""), '""')


if __name__ == "__main__":
    unittest.main(verbosity=2)
