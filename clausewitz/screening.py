"""Eligibility screening.

The rule that shapes this module: **the model never decides.** A language model
reads a call for proposals and extracts requirements, each one carrying the
exact sentence it came from. This module then verifies every quote appears
verbatim in the source, and only after that does deterministic code decide.

So a hallucinated requirement cannot become a verdict. It can only become an
unverified quote, which is dropped, which turns the call UNDECIDABLE -- the
outcome that asks a human to look. Failing towards "ask a human" rather than
towards "no" is the whole point.

No third-party dependencies. Runs with no credentials.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from . import normalise


class Verdict(str, Enum):
    ELIGIBLE = "eligible"
    EXCLUDED = "excluded"
    UNDECIDABLE = "undecidable"


@dataclass(frozen=True)
class Profile:
    """What an organisation actually is. Every field is a fact it can prove."""

    name: str
    country: str                      # ISO 3166-1 alpha-2, e.g. "MX"
    legal_form: str                   # "nonprofit" | "individual" | "company" | ...
    can_travel: bool                  # can it send someone somewhere in person?
    can_front_money: bool             # can it pay costs and be reimbursed later?
    needs_cash_prize: bool            # would credits or vouchers be useless to it?
    is_student_body: bool = False
    headcount: int = 1
    tags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Requirement:
    """One demand a call makes, and the sentence it was taken from.

    `quote` must appear in the call's source text verbatim. `kind` names which
    check applies; an unknown kind is not guessed at, it is surfaced.
    """

    kind: str
    quote: str
    value: object = None


@dataclass(frozen=True)
class Call:
    """An open call, plus the raw text every quote must be traceable to."""

    name: str
    source_text: str
    requirements: tuple[Requirement, ...] = ()
    prize_label: str = ""


@dataclass(frozen=True)
class Finding:
    """Why a call landed where it did. Never a bare label."""

    requirement: Requirement
    reason: str


@dataclass(frozen=True)
class Result:
    call: Call
    verdict: Verdict
    findings: tuple[Finding, ...] = ()
    unverified: tuple[Requirement, ...] = ()
    unknown_kinds: tuple[Requirement, ...] = field(default=())
    # Places a call named that could not be turned into a country code:
    # sub-national jurisdictions like Quebec, regions, or a country missing
    # from the table. Each one is an exclusion nobody has evaluated, so its
    # presence makes the call undecidable rather than eligible.
    unresolved_places: tuple[tuple[Requirement, str], ...] = field(default=())

    @property
    def blocking(self) -> tuple[Finding, ...]:
        return self.findings if self.verdict is Verdict.EXCLUDED else ()


# --------------------------------------------------------------------------
# Quote verification
# --------------------------------------------------------------------------

_WS = re.compile(r"\s+")


def _normalise(text: str) -> str:
    """Fold the differences that are not differences.

    Copy-pasted rules text arrives with curly quotes, non-breaking spaces and
    line wrapping that a model will silently normalise when it quotes. Treating
    those as mismatches would reject honest quotes; treating case or wording as
    equal would accept dishonest ones. So: unicode-normalise, unify quote and
    dash characters, collapse whitespace -- and change nothing else.
    """
    text = unicodedata.normalize("NFKC", text)
    for fancy, plain in (
        ("‘", "'"), ("’", "'"),
        ("“", '"'), ("”", '"'),
        ("–", "-"), ("—", "-"),
        (" ", " "),
    ):
        text = text.replace(fancy, plain)
    return _WS.sub(" ", text).strip()


def quote_is_grounded(quote: str, source_text: str) -> bool:
    """True when `quote` really is in `source_text`.

    An empty quote is not grounded. That matters: it is the shape a model
    produces when it inferred a requirement it never actually read.
    """
    if not quote or not quote.strip():
        return False
    return _normalise(quote) in _normalise(source_text)


# --------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------
# Each returns a reason string when the requirement EXCLUDES the profile, or
# None when it does not. Adding a kind means adding a function here -- and a
# kind with no function is reported, never assumed harmless.

def _check_excluded_countries(req: Requirement, p: Profile) -> str | None:
    codes, _ = normalise.countries(req.value)
    if p.country.upper() in set(codes):
        return f"the call excludes {p.country}, and that is where {p.name} is based"
    return None


def _check_allowed_countries(req: Requirement, p: Profile) -> str | None:
    codes, _ = normalise.countries(req.value)
    if codes and p.country.upper() not in set(codes):
        return f"the call is limited to {sorted(set(codes))}, which does not include {p.country}"
    return None


# Kinds whose value is a list of places, and which therefore have something
# that can fail to resolve. Anything they cannot turn into a country code is
# an exclusion the screen did not understand, and is reported rather than
# dropped -- see `screen`.
PLACE_KINDS = ("excluded_countries", "allowed_countries")


def unresolved_places(req: Requirement) -> tuple[str, ...]:
    """Anything in a requirement's value this code could not make sense of.

    Covers places and legal forms alike: both are free text a model copied out
    of prose, both are compared against a controlled vocabulary, and in both
    the honest answer to "I do not recognise this" is a question rather than a
    verdict.
    """
    if req.kind in PLACE_KINDS:
        return tuple(normalise.countries(req.value)[1])
    if req.kind == "legal_form":
        return tuple(normalise.legal_forms(req.value)[1])
    return ()


def _check_in_person(req: Requirement, p: Profile) -> str | None:
    if req.value is not False and not p.can_travel:
        return "attendance in person is required and this profile cannot travel"
    return None


def _check_students_only(req: Requirement, p: Profile) -> str | None:
    if req.value is not False and not p.is_student_body:
        return "entry is limited to students and this profile is not a student body"
    return None


def _check_prize_not_cash(req: Requirement, p: Profile) -> str | None:
    if req.value is not False and p.needs_cash_prize:
        return "the award is not money, and this profile needs cash rather than credit"
    return None


def _check_prize_undisclosed(req: Requirement, p: Profile) -> str | None:
    if req.value is not False:
        return "the prize is not stated, so there is nothing to evaluate"
    return None


def _check_entry_fee(req: Requirement, p: Profile) -> str | None:
    try:
        fee = float(req.value or 0)
    except (TypeError, ValueError):
        return None
    if fee > 0 and not p.can_front_money:
        return f"entry costs {fee:g} up front and this profile cannot front money"
    return None


def _check_legal_form(req: Requirement, p: Profile) -> str | None:
    # `normalise.as_list` rather than iterating req.value directly. The same
    # trap as the country checks, and it was found the same way -- a live run
    # returned value="individual" and produced the reason "the call requires
    # ['a','d','i','l','n','u','v'], and this profile is a nonprofit".
    #
    # That one is louder than the country bug because it excludes wrongly
    # instead of clearing wrongly, so it shows up in the output. Worth saying
    # plainly: the quiet direction is the dangerous one, and it is the same
    # line of code.
    allowed, unresolved = normalise.legal_forms(req.value)
    mine, _ = normalise.legal_forms(p.legal_form)
    if not allowed or not mine:
        return None
    if set(mine) & set(allowed):
        return None
    if unresolved:
        # The call named a form this table does not know. The profile does not
        # match the ones we did resolve, but the unknown one might be exactly
        # it. Excluding here is a guess, and the guess costs somebody a grant,
        # so it stays quiet and `unresolved_forms` routes the call to a human.
        return None
    return (f"the call requires {sorted(set(allowed))}, "
            f"and this profile is a {p.legal_form}")


def _check_min_headcount(req: Requirement, p: Profile) -> str | None:
    try:
        needed = int(req.value)
    except (TypeError, ValueError):
        return None
    if p.headcount < needed:
        return f"a team of {needed} is required and this profile has {p.headcount}"
    return None


CHECKS: dict[str, Callable[[Requirement, Profile], "str | None"]] = {
    "excluded_countries": _check_excluded_countries,
    "allowed_countries": _check_allowed_countries,
    "in_person_required": _check_in_person,
    "students_only": _check_students_only,
    "prize_not_cash": _check_prize_not_cash,
    "prize_undisclosed": _check_prize_undisclosed,
    "entry_fee": _check_entry_fee,
    "legal_form": _check_legal_form,
    "min_headcount": _check_min_headcount,
}


# --------------------------------------------------------------------------
# Screening
# --------------------------------------------------------------------------

def _allowlist_already_satisfied(req: Requirement, p: Profile) -> bool:
    """True when the profile matches this allow list on a term we did resolve.

    Only allow lists qualify. Adding an unknown entry to a list of who MAY
    enter cannot take anyone off it, so once the profile is on the list by a
    term this code understood, the leftovers are irrelevant to the verdict.

    Deliberately returns False for every deny list and for every other kind:
    the safe direction here is to keep reporting.
    """
    if req.kind == "allowed_countries":
        codes, _ = normalise.countries(req.value)
        return p.country.upper() in set(codes)
    if req.kind == "legal_form":
        forms, _ = normalise.legal_forms(req.value)
        return p.legal_form.lower() in {f.lower() for f in forms}
    return False


def screen(call: Call, profile: Profile) -> Result:
    """Decide, and be able to show why.

    Order matters. A requirement is only allowed to exclude after its quote has
    been proven to exist. Anything ungrounded or unrecognised makes the call
    UNDECIDABLE, because a screen that quietly ignores what it did not
    understand is worse than one that admits it.
    """
    verified: list[Requirement] = []
    unverified: list[Requirement] = []
    unknown: list[Requirement] = []

    for req in call.requirements:
        if not quote_is_grounded(req.quote, call.source_text):
            unverified.append(req)
        elif req.kind not in CHECKS:
            unknown.append(req)
        else:
            verified.append(req)

    findings = tuple(
        Finding(req, reason)
        for req in verified
        if (reason := CHECKS[req.kind](req, profile)) is not None
    )

    # A place the call named and this code could not resolve is not noise. It
    # is a restriction whose effect on this profile is unknown, and the honest
    # answer to an unknown restriction is "someone look at this".
    #
    # With one exception, and the asymmetry is the reason for it. On an
    # ALLOW list, an unrecognised entry can only ever widen who may enter --
    # so once the profile already matches something on the list, whatever else
    # is there cannot change the answer. Reporting it anyway sends a call that
    # is plainly eligible to a human, and a screen that cries wolf on the easy
    # cases stops being read on the hard ones.
    #
    # On a DENY list the same leftover is dangerous: it could be this very
    # profile's country under a name the table does not carry. Unknown entries
    # there always stop the screen.
    stray = tuple(
        (req, place)
        for req in verified
        if not _allowlist_already_satisfied(req, profile)
        for place in unresolved_places(req)
    )

    if findings:
        verdict = Verdict.EXCLUDED
    elif unverified or unknown or stray:
        verdict = Verdict.UNDECIDABLE
    elif not verified:
        # Nothing was extracted at all. That is not eligibility, it is silence.
        verdict = Verdict.UNDECIDABLE
    else:
        verdict = Verdict.ELIGIBLE

    return Result(
        call=call,
        verdict=verdict,
        findings=findings,
        unverified=tuple(unverified),
        unknown_kinds=tuple(unknown),
        unresolved_places=stray,
    )


def screen_all(calls, profile: Profile) -> list[Result]:
    return [screen(c, profile) for c in calls]
