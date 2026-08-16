"""The Strands agent, and the narrow job it is allowed to have.

The model does one thing here: read a call for proposals and report which
demands it makes, quoting the sentence each demand came from. It does not
decide whether anyone is eligible. That decision belongs to `screening`, which
is ordinary Python and can be read, tested and argued with.

The split is the design. A language model is genuinely good at finding the
sentence about who may enter, buried on page four between the sponsor logos
and the schedule. It is genuinely bad at being trusted with the answer,
because when it is wrong it is wrong fluently. So it is given the reading and
denied the verdict.

What enforces the split is not the prompt. It is `quote_is_grounded`: every
requirement the model reports must quote text that appears verbatim in the
source. A requirement the model invented quotes nothing, fails that check, and
is dropped -- which pushes the call towards UNDECIDABLE, towards a human, and
never towards a false rejection.

    from clausewitz.agent import read_call
    reqs = read_call(call_text)          # requirements, each with its quote
"""

from __future__ import annotations

import json
import os

from strands import Agent, tool

from .screening import CHECKS, Requirement, quote_is_grounded

# What the model is allowed to report. A kind outside this list is surfaced to
# a human rather than guessed at -- see `unknown_kinds` in Result.
KINDS = sorted(CHECKS)

INSTRUCTIONS = f"""
You read one call for proposals and report the demands it makes on who may
enter. You do not decide whether anybody is eligible. Something else does that.

For each demand, call `report_requirement` once with:

  kind   one of: {", ".join(KINDS)}
  quote  the sentence from the call that states it, copied EXACTLY
  value  the machine-readable part (a country list, a fee, a headcount, or
         true/false), or null when the kind needs no value

Three rules, and the second is the one that matters:

1. Read the whole text before reporting anything.

2. NEVER write a quote you did not copy from the text in front of you. Every
   quote is checked against the source, character for character. A requirement
   whose quote is not found is thrown away -- so an invented quote does not
   fool anyone, it just loses a real requirement you could have reported.

3. If the call does not state something, do not report it. A call that is
   silent about who may enter is not a call that admits everyone; it is a call
   that has to be read by a person. Reporting nothing is the correct output for
   a text that demands nothing, and saying so is useful.

Report only what restricts entry. Deadlines, judging criteria and prize
categories are not requirements unless they gate who may apply.
""".strip()


def build_agent(model=None) -> tuple[Agent, list]:
    """An agent whose only tool records requirements into a list we keep.

    The list is closed over rather than parsed back out of the transcript,
    because a tool call is a fact and a final message is a summary. We want the
    facts.
    """
    collected: list[Requirement] = []

    @tool
    def report_requirement(kind: str, quote: str, value: object = None) -> str:
        """Record one entry requirement stated by the call.

        Args:
            kind: which requirement this is; see the list in the instructions.
            quote: the exact sentence from the call that states it.
            value: the machine-readable part, or null when not applicable.
        """
        collected.append(Requirement(kind=kind, quote=quote, value=value))
        return f"recorded {kind}"

    agent = Agent(
        model=model or default_model(),
        tools=[report_requirement],
        system_prompt=INSTRUCTIONS,
    )
    return agent, collected


def default_model():
    """Gemini through LiteLLM.

    Strands defaults to Amazon Bedrock, which needs an AWS account with billing
    attached. This project deliberately runs on a free API key instead, so that
    a judge can reproduce it without putting a card down -- the same reason the
    screening layer runs with no credentials at all.
    """
    from strands.models.litellm import LiteLLMModel

    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. The screening layer runs without it; "
            "only reading a call with the model needs one."
        )
    # A floating alias, not a pinned version. Google retires pinned Gemini ids
    # for new API keys without warning -- `gemini-2.5-flash` answers 404 with
    # "no longer available to new users" on a key issued today, while still
    # working for anyone who onboarded earlier. A judge reproducing this months
    # from now gets a fresh key, so the pin would break for them and not for
    # us: the worst kind of bug, invisible to the person who wrote it.
    #
    # Temperature 0 because the job is transcription, not composition. There is
    # exactly one correct quote for a requirement and it is already written.
    # stream=False is not a preference, it is a requirement of the free tier.
    # On a no-cost API key `generateContent` answers 200 while
    # `streamGenerateContent` answers 503 "experiencing high demand" — every
    # time, not intermittently. Strands streams by default, so the default
    # configuration cannot talk to Google on a free key at all. Nothing here
    # needs tokens as they arrive: the output is a handful of tool calls that
    # are only useful complete.
    return LiteLLMModel(
        client_args={"api_key": key},
        model_id=os.environ.get("CLAUSEWITZ_MODEL", "gemini/gemini-flash-latest"),
        params={"temperature": 0, "stream": False},
    )


class TransportFailed(RuntimeError):
    """The model could not be reached. Distinct from the model finding nothing.

    These two look identical downstream -- both produce zero requirements, and
    a call with zero requirements is reported as "no eligibility criteria could
    be extracted at all". That sentence is true of a call written in vague
    prose. It is a lie about a call nobody managed to read. Conflating them
    tells the user something about a document when the real news is about the
    network.
    """


# Google's no-cost tier answers 503 "experiencing high demand" often enough
# that a single attempt is not a reproducible instruction. A judge following
# the README should not have to guess whether the project is broken.
ATTEMPTS = 4
BACKOFF_SECONDS = (2, 5, 12)

_TRANSIENT = ("503", "429", "unavailable", "high demand", "rate limit",
              "overloaded", "timeout", "temporarily")


def _is_transient(error: Exception) -> bool:
    text = f"{type(error).__name__} {error}".lower()
    return any(marker in text for marker in _TRANSIENT)


def read_call(source_text: str, model=None,
              attempts: int = ATTEMPTS, sleep=None) -> tuple[list[Requirement], list[Requirement]]:
    """Read a call and return (grounded, ungrounded) requirements.

    Both halves are returned on purpose. The ungrounded ones are not silently
    swallowed: they are what the model claimed and could not support, and a
    run that produces several of them is telling you something about that run.

    Raises TransportFailed if the model could never be reached. Returning empty
    lists in that case would be indistinguishable from a call that states no
    requirements, and those two facts must not share an output.
    """
    import time

    sleep = sleep or time.sleep
    prompt = f"Here is the full text of the call:\n\n---\n{source_text}\n---"
    last: Exception | None = None

    for attempt in range(attempts):
        agent, collected = build_agent(model)
        try:
            agent(prompt)
        except Exception as error:  # noqa: BLE001 - re-raised below
            last = error
            if not _is_transient(error) or attempt == attempts - 1:
                raise TransportFailed(
                    f"could not reach the model after {attempt + 1} "
                    f"attempt(s): {error}"
                ) from error
            sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])
            continue

        # A clean response with no tool calls at all. The model answered in
        # prose instead of reporting, which happens and is not an error --
        # but on the first occurrence it is worth one more try before
        # concluding the call demands nothing.
        if not collected and attempt < attempts - 1:
            prompt = (
                f"{prompt}\n\nReport each entry requirement by calling "
                f"report_requirement. If the text truly places no restriction "
                f"on who may apply, reply with the single word NONE."
            )
            continue

        grounded, ungrounded = [], []
        for req in collected:
            target = grounded if quote_is_grounded(req.quote, source_text) else ungrounded
            target.append(req)
        return grounded, ungrounded

    raise TransportFailed(f"could not reach the model: {last}")
