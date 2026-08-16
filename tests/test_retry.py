"""A call nobody could read must not look like a call that demands nothing.

Both produce zero requirements. Downstream, zero requirements prints as "no
eligibility criteria could be extracted at all" -- a true sentence about a
vaguely written call, and a false one about a network failure.

Google's free tier answers 503 often enough that this is not hypothetical: it
happened twice while building the feature these tests cover.

No test here reaches the network. The agent is replaced by a fake whose only
job is to fail in a specific way.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from clausewitz import agent as agent_module
from clausewitz.agent import TransportFailed, read_call
from clausewitz.screening import Requirement

TEXT = "Applications are accepted from nonprofit organisations only."


class FakeAgent:
    """One attempt. Either it raises, or it records what the script says."""

    def __init__(self, action, collected):
        self.action = action
        self.collected = collected

    def __call__(self, prompt):
        if isinstance(self.action, Exception):
            raise self.action
        self.collected.extend(self.action or [])
        return "done"


def with_agent(script):
    """Patch build_agent so read_call drives fakes instead of a model.

    `script` is one entry per attempt: an Exception to raise, or a list of
    requirements to report. read_call builds a fresh agent per attempt, so
    the entries are consumed in order.
    """
    remaining = list(script)
    holder: dict[str, list] = {"agents": []}

    def build(model=None):
        collected: list[Requirement] = []
        action = remaining.pop(0) if remaining else []
        fake = FakeAgent(action, collected)
        holder["agents"].append(fake)
        return fake, collected

    return patch.object(agent_module, "build_agent", build), holder


class TransientFailuresAreRetried(unittest.TestCase):

    def test_a_503_is_retried_and_can_succeed(self):
        found = [Requirement("legal_form", TEXT, "nonprofit organisations")]
        patcher, holder = with_agent([
            RuntimeError("litellm.ServiceUnavailableError: 503 high demand"),
            found,
        ])
        with patcher:
            grounded, _ = read_call(TEXT, sleep=lambda _: None)
        self.assertEqual(len(grounded), 1)
        self.assertEqual(len(holder["agents"]), 2, "it should have tried twice")

    def test_exhausting_retries_raises_rather_than_returning_empty(self):
        boom = RuntimeError("503 Service Unavailable: experiencing high demand")
        patcher, _ = with_agent([boom, boom, boom, boom])
        with patcher:
            with self.assertRaises(TransportFailed):
                read_call(TEXT, sleep=lambda _: None)

    def test_the_error_says_it_could_not_reach_the_model(self):
        boom = RuntimeError("429 rate limit exceeded")
        patcher, _ = with_agent([boom] * 4)
        with patcher:
            try:
                read_call(TEXT, sleep=lambda _: None)
            except TransportFailed as e:
                self.assertIn("could not reach the model", str(e))


class PermanentFailuresAreNotRetried(unittest.TestCase):

    def test_a_bad_api_key_fails_immediately(self):
        """Retrying a 401 four times wastes the user's time and says nothing."""
        patcher, holder = with_agent([
            RuntimeError("401 API key not valid"),
            [Requirement("legal_form", TEXT, "nonprofit")],
        ])
        with patcher:
            with self.assertRaises(TransportFailed):
                read_call(TEXT, sleep=lambda _: None)
        self.assertEqual(len(holder["agents"]), 1,
                         "a permanent error must not be retried")


class SilenceIsRetriedOnceThenBelieved(unittest.TestCase):

    def test_a_model_that_reports_nothing_is_asked_again(self):
        found = [Requirement("legal_form", TEXT, "nonprofit organisations")]
        patcher, holder = with_agent([[], found])
        with patcher:
            grounded, _ = read_call(TEXT, sleep=lambda _: None)
        self.assertEqual(len(grounded), 1)
        self.assertEqual(len(holder["agents"]), 2)

    def test_persistent_silence_returns_empty_rather_than_raising(self):
        """A call that genuinely restricts nobody is a real answer."""
        patcher, _ = with_agent([[], [], [], []])
        with patcher:
            grounded, ungrounded = read_call(TEXT, sleep=lambda _: None)
        self.assertEqual(grounded, [])
        self.assertEqual(ungrounded, [])


class GroundingStillApplies(unittest.TestCase):

    def test_an_invented_quote_is_separated_even_after_a_retry(self):
        invented = [Requirement("legal_form", "a sentence never written", "company")]
        patcher, _ = with_agent([
            RuntimeError("503 high demand"),
            invented,
        ])
        with patcher:
            grounded, ungrounded = read_call(TEXT, sleep=lambda _: None)
        self.assertEqual(grounded, [])
        self.assertEqual(len(ungrounded), 1)


if __name__ == "__main__":
    unittest.main()
