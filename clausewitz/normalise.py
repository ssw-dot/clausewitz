"""Turn what a model wrote into what the checks can read — or refuse to.

The screening layer compares ISO 3166-1 alpha-2 codes. A model reading a call
writes what the call wrote: "Brazil", "the United States", "Quebec". Those are
not the same strings, and the gap between them is dangerous in one specific
direction.

    countries = {str(c).upper() for c in (req.value or [])}
    if p.country.upper() in countries: ...

Hand that `"Brazil, Italy"` and Python iterates the *characters*. The set
becomes {'B','R','A','Z',...} and a two-letter country code can never be in it.
The call excludes you, the screen says you are eligible, and nothing anywhere
reports a problem. A tool whose entire promise is "I will show you the clause
that disqualifies you" failing silently in the disqualifying direction is worse
than no tool.

So this module does two things and refuses to do a third:

  * coerce a written list into a real list;
  * map country names to codes;
  * and when a name cannot be mapped, say so rather than drop it.

That last one is the point. A dropped country is an exclusion that vanished.
An unresolved one is a question, and questions route to a human.
"""

from __future__ import annotations

import re
import unicodedata

# Not a complete gazetteer, and deliberately so. It holds the places that
# actually appear in calls for proposals — sanctions lists, the handful of
# jurisdictions whose lottery law makes sponsors carve them out, and the
# countries a project has already met. Anything absent becomes a question
# rather than a guess, which is the behaviour we want as the list ages.
NAMES = {
    "afghanistan": "AF", "belarus": "BY", "brazil": "BR", "canada": "CA",
    "china": "CN", "cuba": "CU", "france": "FR", "germany": "DE",
    "india": "IN", "iran": "IR", "iraq": "IQ", "italy": "IT",
    "japan": "JP", "kazakhstan": "KZ", "mexico": "MX", "north korea": "KP",
    "russia": "RU", "singapore": "SG", "somalia": "SO", "south korea": "KR",
    "spain": "ES", "sudan": "SD", "syria": "SY", "ukraine": "UA",
    "united kingdom": "GB", "united states": "US", "venezuela": "VE",
    "vietnam": "VN", "australia": "AU", "argentina": "AR",
    "democratic people's republic of korea": "KP",
    "russian federation": "RU", "united states of america": "US",
    "great britain": "GB", "uk": "GB", "usa": "US", "u.s.": "US",
    "u.s.a.": "US", "korea": "KR", "myanmar": "MM", "burma": "MM",
    # Latin America in full. This is a Good Neighbor Agents entry, the profile
    # is a Mexican library, and the calls it will read are regional -- so the
    # region it lives in is the last one that should come back unrecognised.
    # It did, on the first live run: a fund open to "Mexico, Colombia and Peru"
    # cleared Mexico and could not read the other two.
    "colombia": "CO", "peru": "PE", "chile": "CL", "ecuador": "EC",
    "guatemala": "GT", "honduras": "HN", "nicaragua": "NI",
    "costa rica": "CR", "panama": "PA", "uruguay": "UY", "paraguay": "PY",
    "bolivia": "BO", "dominican republic": "DO", "el salvador": "SV",
    "portugal": "PT", "netherlands": "NL", "belgium": "BE", "poland": "PL",
    "sweden": "SE", "norway": "NO", "denmark": "DK", "finland": "FI",
    "ireland": "IE", "switzerland": "CH", "austria": "AT", "greece": "GR",
    "turkey": "TR", "israel": "IL", "egypt": "EG", "nigeria": "NG",
    "kenya": "KE", "south africa": "ZA", "morocco": "MA", "indonesia": "ID",
    "philippines": "PH", "thailand": "TH", "malaysia": "MY", "pakistan": "PK",
    "bangladesh": "BD", "new zealand": "NZ",
}

# Sub-national jurisdictions that get excluded on their own. Quebec is the
# one that shows up constantly, because its Consumer Protection Act makes
# running a contest there expensive. It is not a country and has no alpha-2
# code, so mapping it to "CA" would be a lie: excluding Quebec does not
# exclude Canada. It resolves to nothing, and is reported.
NOT_COUNTRIES = {
    "quebec", "québec", "crimea", "donetsk", "luhansk",
    "antarctica", "western sahara", "puerto rico",
}

_ARTICLES = re.compile(r"^(the|republic of|state of)\s+", re.I)

# Alpha-3 codes, because models emit them. A live run against a fund open to
# "Mexico, Colombia and Peru" came back as "MEX, COL, PER" -- perfectly valid
# ISO 3166-1, just the other column. Without this the three resolve to nothing
# and a fund the profile qualifies for is sent to a human for no reason.
ALPHA3 = {
    "afg": "AF", "arg": "AR", "aus": "AU", "blr": "BY", "bra": "BR",
    "can": "CA", "chn": "CN", "col": "CO", "cub": "CU", "deu": "DE",
    "esp": "ES", "fra": "FR", "gbr": "GB", "ind": "IN", "irn": "IR",
    "irq": "IQ", "ita": "IT", "jpn": "JP", "kaz": "KZ", "kor": "KR",
    "mex": "MX", "mmr": "MM", "prk": "KP", "per": "PE", "rus": "RU",
    "sdn": "SD", "sgp": "SG", "som": "SO", "syr": "SY", "ukr": "UA",
    "usa": "US", "ven": "VE", "vnm": "VN", "chl": "CL", "ecu": "EC",
    "gtm": "GT", "hnd": "HN", "nic": "NI", "cri": "CR", "pan": "PA",
    "ury": "UY", "pry": "PY", "bol": "BO", "dom": "DO", "slv": "SV",
}


# How calls actually write legal forms, mapped to the handful a profile can
# declare. This exists because exact matching produced a false EXCLUDED on a
# live run: a call accepting "registered nonprofit organisations" rejected a
# profile whose legal_form is "nonprofit", which is the same thing said twice.
#
# Order matters below -- the first keyword found wins -- so the more specific
# phrases have to come before the words they contain.
FORM_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("community interest compan", "company"),
    ("social enterprise", "company"),
    ("not-for-profit", "nonprofit"),
    ("not for profit", "nonprofit"),
    ("non-profit", "nonprofit"),
    ("nonprofit", "nonprofit"),
    ("charitable", "nonprofit"),
    ("charity", "nonprofit"),
    ("ngo", "nonprofit"),
    ("non-governmental", "nonprofit"),
    ("asociacion civil", "nonprofit"),
    ("a.c.", "nonprofit"),
    ("foundation", "nonprofit"),
    ("cooperative", "cooperative"),
    ("co-operative", "cooperative"),
    ("natural person", "individual"),
    ("sole trader", "individual"),
    ("sole proprietor", "individual"),
    ("individual", "individual"),
    ("student", "student_group"),
    ("university", "academic"),
    ("academic", "academic"),
    ("research institution", "academic"),
    ("government", "government"),
    ("municipal", "government"),
    ("public body", "government"),
    ("for-profit", "company"),
    ("corporation", "company"),
    ("llc", "company"),
    ("compan", "company"),
    ("business", "company"),
    ("startup", "company"),
)


def legal_forms(value: object) -> tuple[list[str], list[str]]:
    """Return (canonical forms, phrases that could not be canonicalised).

    Same contract as `countries`, and for the same reason. A phrase this table
    does not recognise is not dropped and not treated as a mismatch: it comes
    back so the call can be marked undecidable. Excluding on a phrase nobody
    understood is how you tell a library not to apply for a grant it qualifies
    for.
    """
    canonical: list[str] = []
    unresolved: list[str] = []
    for raw in as_list(value):
        folded = _fold(raw)
        if not folded:
            continue
        for keyword, form in FORM_KEYWORDS:
            if keyword in folded:
                canonical.append(form)
                break
        else:
            unresolved.append(raw)
    return canonical, unresolved


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.strip().strip(".").lower()
    return _ARTICLES.sub("", text).strip()


def as_list(value: object) -> list[str]:
    """A written list becomes a real one; a real one is left alone.

    Splitting on commas *and* on " and " because calls are written in prose:
    "Void in Brazil, Italy, Quebec, and where prohibited by law".
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(v).strip() for v in value if str(v).strip()]
    parts = re.split(r",|\band\b|;|/", str(value))
    return [p.strip() for p in parts if p.strip()]


def countries(value: object) -> tuple[list[str], list[str]]:
    """Return (alpha-2 codes, things that could not be resolved).

    The second half is never empty by accident. Anything in it is a place the
    call named and this module could not turn into a code — a sub-national
    jurisdiction, a region, a country missing from the table, or a phrase like
    "where prohibited by law" that is not a place at all. It must reach the
    caller so the call can be marked undecidable rather than cleared.
    """
    codes: list[str] = []
    unresolved: list[str] = []
    for raw in as_list(value):
        folded = _fold(raw)
        if not folded or folded in {"where prohibited by law", "where prohibited",
                                    "and where prohibited by law"}:
            unresolved.append(raw)
        elif len(folded) == 2 and folded.isalpha():
            codes.append(folded.upper())
        elif folded in NAMES:
            codes.append(NAMES[folded])
        elif len(folded) == 3 and folded in ALPHA3:
            codes.append(ALPHA3[folded])
        else:
            # Includes NOT_COUNTRIES: a real exclusion this layer must not
            # pretend to have understood.
            unresolved.append(raw)
    return codes, unresolved
