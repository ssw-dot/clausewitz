"""Command line entry point.

Runs against a fixture by default so anyone -- a judge, a volunteer, you --
can see the whole thing work with no account, no key and no network.

    python -m clausewitz.cli
    python -m clausewitz.cli --fixture fixtures/calls.json
    python -m clausewitz.cli --audit        # prove every quote is real
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import render
from .screening import Call, Profile, Requirement, quote_is_grounded, screen_all

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "fixtures" / "calls.json"


def load(path: Path) -> tuple[Profile, list[Call]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    profile = Profile(**data["profile"])
    calls = [
        Call(
            name=c["name"],
            source_text=c["source_text"],
            prize_label=c.get("prize_label", ""),
            requirements=tuple(
                Requirement(kind=r["kind"], quote=r["quote"], value=r.get("value"))
                for r in c.get("requirements", [])
            ),
        )
        for c in data["calls"]
    ]
    return profile, calls


def audit(calls: list[Call]) -> int:
    """Check every quote against its source. This is the guarantee, made visible.

    Exits non-zero if any quote is not verbatim, so it can run in CI.
    """
    bad = 0
    for call in calls:
        for req in call.requirements:
            ok = quote_is_grounded(req.quote, call.source_text)
            if not ok:
                bad += 1
            print(f"{'ok  ' if ok else 'BAD '} {call.name} :: {req.kind}")
    total = sum(len(c.requirements) for c in calls)
    print(f"\n{total - bad}/{total} quotes found verbatim in their source text.")
    if bad:
        print("A quote that cannot be found is discarded, never trusted.")
    return 1 if bad else 0


def read_new_call(path: Path, profile: Profile) -> int:
    """Read an unseen call with the model, then screen it.

    This is the only path that needs an API key, and it is separate on purpose:
    everything else in this tool runs on nothing. Imported lazily so that a
    machine without the SDK installed can still run the demo and the tests.
    """
    try:
        from .agent import TransportFailed, read_call
    except ImportError as e:
        print(f"The model layer needs the Strands SDK: pip install "
              f"'strands-agents[litellm]'  ({e})", file=sys.stderr)
        return 2

    source = path.read_text(encoding="utf-8")
    try:
        grounded, ungrounded = read_call(source)
    except TransportFailed as e:
        # Kept separate from every other failure, and from success. A call
        # nobody could read produces zero requirements, and zero requirements
        # prints as "no eligibility criteria could be extracted at all" -- a
        # statement about the document. When the truth is that the network
        # failed, that sentence is a lie in the user's favour, and they would
        # act on it.
        print(f"Could not read the call: {e}", file=sys.stderr)
        print("Nothing was screened. This is a connection problem, not a "
              "verdict about the call.", file=sys.stderr)
        return 3
    except RuntimeError as e:
        # Almost always a missing API key. Say so in one line rather than
        # showing a stack trace to someone who just wanted to try the tool.
        print(str(e), file=sys.stderr)
        return 2

    print(f"The model reported {len(grounded) + len(ungrounded)} requirements.")
    if ungrounded:
        # Not a footnote. This is the guarantee doing its job in the open.
        print(f"{len(ungrounded)} quoted text that is not in the source and were "
              f"discarded:")
        for req in ungrounded:
            print(f"   {req.kind}: {req.quote[:90]!r}")
    print()

    call = Call(name=path.stem, source_text=source,
                requirements=tuple(grounded))
    print(render(screen_all([call], profile), profile.name))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="clausewitz")
    ap.add_argument("--fixture", type=Path, default=DEFAULT)
    ap.add_argument("--audit", action="store_true",
                    help="verify every quote is verbatim, then exit")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--read", type=Path, metavar="FILE",
                    help="read an unseen call with the model (needs an API key) "
                         "and screen it against the fixture's profile")
    args = ap.parse_args(argv)

    profile, calls = load(args.fixture)

    if args.read:
        return read_new_call(args.read, profile)

    if args.audit:
        return audit(calls)

    results = screen_all(calls, profile)

    if args.json:
        print(json.dumps([
            {
                "call": r.call.name,
                "verdict": r.verdict.value,
                "blocking": [
                    {"quote": f.requirement.quote, "reason": f.reason}
                    for f in r.blocking
                ],
                "unverified_quotes": [q.quote for q in r.unverified],
                "unsupported_rules": [q.kind for q in r.unknown_kinds],
            }
            for r in results
        ], indent=2, ensure_ascii=False))
        return 0

    print(render(results, profile.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
