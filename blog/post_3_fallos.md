# Agents for Humans: caution is not free

*Post 3 of 3 on building Clausewitz for the Agents for Humans hackathon. The
tool screens funding calls for small organisations and quotes the clause that
disqualifies them. These are the four bugs that changed the design, all of them
found by running it against real calls rather than by imagining edge cases.*

---

## 1. A country is not a country

The first version compared the profile's country against whatever list the model
returned. Straightforward. Then a real call said:

> *"This contest is void in Brazil, Quebec, Russia..."*

**Quebec is not a country.** It has no ISO 3166-1 alpha-2 code. Our lookup
returned nothing for it, the code shrugged, and the call came out **eligible**.

Look at what happened there. The document named three places you cannot be. We
understood two of them, silently discarded the third, and reported no problem.
Had the profile been in Quebec, the tool would have cheerfully told a Montreal
nonprofit to spend a weekend on an application it was explicitly barred from.

The bug is not the missing lookup table entry. You cannot enumerate every
sub-national jurisdiction that a rulebook might name, and the next document will
say *"the Southern Cone"* or *"EEA member states"* anyway. **The bug is treating
"I did not understand this" as "this does not apply."**

It now reports any place it cannot resolve, and the call goes to a human:

```python
# Places a call named that could not be turned into a country code:
# sub-national jurisdictions like Quebec, regions, or a country missing
# from the table. Each one is an exclusion nobody has evaluated, so its
# presence makes the call undecidable rather than eligible.
unresolved_places: tuple[tuple[Requirement, str], ...]
```

**An exclusion nobody evaluated is not an absence of exclusion.**

## 2. A string is a list of letters

A live run returned `value="individual"` where the code expected a list of
permitted legal forms. Python does not object to this. Strings are iterable, so
the loop ran, one character at a time, and the tool produced this reason:

> *"the call requires `['a','d','i','l','n','u','v']`, and this profile is a
> nonprofit."*

Funny in a test. Catastrophic in production — it excludes wrongly and it sounds
authoritative doing it, in exactly the format that the rest of the output has
trained you to believe.

We fixed it by normalising inputs in one place, with its own module and its own
tests. But the comment we left in the code is the part that mattered:

```python
# That one is louder than the country bug because it excludes wrongly
# instead of clearing wrongly, so it shows up in the output. Worth saying
# plainly: the quiet direction is the dangerous one, and it is the same
# line of code.
```

The same class of bug — trusting the shape of what crossed the model boundary —
can fail loudly or silently. **The one you notice is the lucky one.** The country
bug and this bug are the same mistake; only one of them announced itself.

## 3. Caution is not free

After those two, our instinct was to make everything unrecognised stop the
screen. Rigorous. Safe. Obviously correct.

Then a real call read:

> *"Open to registered nonprofits and community groups operating in Mexico."*

Our profile **is** a registered nonprofit. It is on the list, by name. But
`community_group` was not a term our table carried, so the screen refused to
decide, and a plainly eligible call got sent to a human for review.

That looks like a small annoyance. It is not. **A tool that cries wolf on the
easy cases stops being read on the hard ones.** If two of every three calls come
back as "someone look at this", the human stops looking, and then the one
genuine "someone look at this" — the one hiding a real exclusion — goes past
unread. Excessive caution does not fail safe. It fails to a human who has
learned to ignore you.

The fix is an asymmetry, and the asymmetry is the interesting part:

```python
def _allowlist_already_satisfied(req: Requirement, p: Profile) -> bool:
    """True when the profile matches this allow list on a term we did resolve.

    Only allow lists qualify. Adding an unknown entry to a list of who MAY
    enter cannot take anyone off it, so once the profile is on the list by a
    term this code understood, the leftovers are irrelevant to the verdict.

    Deliberately returns False for every deny list and for every other kind:
    the safe direction here is to keep reporting.
    """
```

On a list of who **may** enter, an unknown entry can only ever widen the door.
Once you are through it by a term we understood, whatever else is written there
cannot take you back out.

On a list of who **may not**, the identical leftover is dangerous — it could be
this profile's own country under a name our table does not carry. There it
always stops the screen.

Same unrecognised string, opposite correct handling, and the difference is the
direction the list points. Six tests cover it in both directions, including that
a *resolved* exclusion still outranks an unresolved one.

## 4. A network failure is not a verdict

The last one is the one we would most likely have shipped.

When the model could not be reached, the run produced zero requirements. Zero
requirements flowed into the renderer, which printed the honest-looking line:

> *"no eligibility criteria could be extracted at all"*

Read that sentence carefully. **It is a statement about the document.** It says:
we looked, and this call does not specify who may enter.

When the truth is that a TCP connection failed, that sentence is a lie — and
it is a lie in the user's favour, which is the kind people act on. A volunteer
reads "no criteria specified", concludes the call is open to everyone, and
starts writing.

Transport failures now have their own exit code and say what actually happened.
The general shape of this bug is worth naming, because it is everywhere in
agent plumbing: **an empty result and a failed result are different, and every
layer that flattens them into the same thing is manufacturing a false statement
about the world.**

## What the four have in common

None of these were found by design review. Every one came from running the thing
against calls we had actually read ourselves, so we knew the right answer and
could see the tool disagree.

Three of the four are the same underlying mistake wearing different clothes:
**something the code did not understand got treated as something that was not
there.** An unresolvable place. A malformed value. A dead connection. In each
case the machinery had a gap, and the gap rendered as "nothing to report."

The third one is the counterweight, and we needed it. You cannot fix the other
three by escalating everything to a human, because a tool that escalates
everything has simply moved the six hours of reading back onto the person who
did not have six hours. **The goal is not maximum caution. It is caution aimed
at the cases where the answer is genuinely unknown, and confidence everywhere
else.**

Getting that aim right took all four bugs.

67 tests, most of them about what happens when something goes wrong. MIT, and it
runs with no credentials: **https://github.com/ssw-dot/clausewitz**

---

*Posts 1 and 2: why we built it, and how the model is structurally prevented
from deciding anything.*
