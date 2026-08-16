"""Turning results into something a human can act on.

The shape of this output is the product. Three buckets, never two: a call we
could not judge is not a rejection and not a pass, and collapsing it into
either would be the lie that makes these tools useless for deciding anything.

Every exclusion prints the sentence that caused it. A filter that will not show
its reasoning is indistinguishable from a broken one.
"""

from __future__ import annotations

import textwrap

from .screening import Result, Verdict

WRAP = 76


def _quote(text: str, indent: str = "        ") -> str:
    body = " ".join(text.split())
    if len(body) > 240:
        body = body[:237] + "..."
    return "\n".join(indent + '"' + line + '"' if i == 0 else indent + " " + line
                     for i, line in enumerate(textwrap.wrap(body, WRAP)))


def render(results: list[Result], profile_name: str) -> str:
    eligible = [r for r in results if r.verdict is Verdict.ELIGIBLE]
    excluded = [r for r in results if r.verdict is Verdict.EXCLUDED]
    unsure = [r for r in results if r.verdict is Verdict.UNDECIDABLE]

    out: list[str] = []
    out.append(f"Screening {len(results)} open calls for: {profile_name}")
    out.append("")
    out.append(f"  eligible {len(eligible)}   "
               f"not eligible {len(excluded)}   "
               f"needs a human {len(unsure)}")
    out.append("")

    out.append(f"ELIGIBLE ({len(eligible)})")
    if not eligible:
        out.append("   none")
    for r in eligible:
        out.append(f"   {r.call.name}"
                   + (f"  --  {r.call.prize_label}" if r.call.prize_label else ""))
    out.append("")

    out.append(f"NOT ELIGIBLE ({len(excluded)})   -- with the clause, not a label")
    if not excluded:
        out.append("   none")
    for r in excluded:
        out.append(f"   {r.call.name}")
        for f in r.blocking:
            out.append(_quote(f.requirement.quote))
            out.append(f"        -> {f.reason}")
        out.append("")

    out.append(f"CANNOT DECIDE ({len(unsure)})   -- and saying so is the point")
    if not unsure:
        out.append("   none")
    for r in unsure:
        out.append(f"   {r.call.name}")
        if r.unverified:
            out.append("        a requirement was claimed but its wording is not in the "
                       "source text, so it was discarded rather than trusted")
        if r.unknown_kinds:
            kinds = ", ".join(sorted({q.kind for q in r.unknown_kinds}))
            out.append(f"        this screener has no rule for: {kinds}")
        if r.unresolved_places:
            # The reason a call most often lands here, and the one it is most
            # embarrassing to omit: the rules WERE read, one term in them just
            # was not recognised. Saying "nothing could be extracted" in that
            # case blames the document for a gap in this table.
            for req, place in r.unresolved_places:
                out.append(f'        "{place}" appears in a {req.kind} rule and '
                           f"is not a term this screener knows")
        if not r.unverified and not r.unknown_kinds and not r.unresolved_places:
            out.append("        no eligibility criteria could be extracted at all")
        out.append("")

    hours = len(excluded) * 6
    if hours:
        out.append(f"{len(excluded)} applications not worth writing. At roughly six "
                   f"hours each, about {hours} hours back.")
    return "\n".join(out)
