# Agents for Humans: the model reads, the code decides

*Post 2 of 3 on building Clausewitz for the Agents for Humans hackathon.
[Post 1](.) explained why we built a tool that screens open calls for small
organisations. This one is about the architecture, which is one idea repeated
everywhere.*

---

Clausewitz tells a two-person nonprofit whether it is eligible for a grant. Get
that wrong in the confident direction and somebody does not apply for money they
would have won.

So the design question was never *"how do we make the model accurate?"* It was
**"what happens when the model is wrong?"** — because it will be, and the answer
has to be built out of something sturdier than a good prompt.

## The split

**The model reads. The code decides.** Those are two different programs and they
share almost nothing.

A Strands agent is given exactly one job: report each demand a call makes on who
may enter, quoting the sentence it came from. It has one tool:

```python
@tool
def report_requirement(kind: str, quote: str, value: str) -> str:
    """Report one eligibility requirement found in the call, with the exact
    sentence it came from."""
```

That is the whole surface. There is no `report_verdict`, no `is_eligible`, no
free-text conclusion the caller might be tempted to read. **The agent has no
vocabulary for the answer.** It can tell you what a document says. It cannot tell
you what that means for you, because we never gave it a way to say so.

Then `screening.py` — ordinary Python, one pure function per rule, no model, no
network, no third-party dependencies at all — decides.

```python
def _check_in_person(req: Requirement, p: Profile) -> str | None:
    if req.value is not False and not p.can_travel:
        return "attendance in person is required and this profile cannot travel"
    return None
```

Nine of those. Each returns the reason it excluded you, or `None`. You can read
the entire decision layer in one sitting and disagree with specific lines of it.

**Why split it this way:** a language model is genuinely good at finding the
eligibility sentence buried on page four between the sponsor logos and the
schedule. It is genuinely bad at being trusted with the answer, because when it
is wrong it is wrong *fluently* — the false rejection arrives in the same calm
prose as the true one. So it is given the reading and denied the verdict.

## The part that actually enforces it

Here is where most "the model just extracts, we decide" designs quietly fail.

If the model invents a requirement, the deterministic layer will evaluate the
invented requirement — deterministically, correctly, and to a wrong conclusion.
Splitting the responsibilities does not help if the data crossing the boundary
is unchecked. **You have not removed the model from the decision. You have moved
it upstream and stopped looking at it.**

So the boundary is a function, not a promise:

```python
def quote_is_grounded(quote: str, source_text: str) -> bool:
    """True when `quote` really is in `source_text`."""
    if not quote or not quote.strip():
        return False
    return _normalise(quote) in _normalise(source_text)
```

Every requirement must quote text that appears **verbatim** in the source. A
requirement the model invented quotes nothing that exists, fails the check, and
is dropped before any rule sees it.

`_normalise` folds only the differences that are not differences — curly quotes,
non-breaking spaces, line wrapping — because copy-pasted rules text arrives full
of those and a model will silently normalise them when quoting. Treating them as
mismatches would reject honest quotes. Treating *case or wording* as equal would
accept dishonest ones. So it folds those three things and nothing else.

**A hallucination cannot become a rejection.** At worst it becomes a missing data
point, which pushes the call towards a human.

And because that is a property of the code rather than a claim about the model,
it is testable without ever calling one:

```
$ python -m clausewitz --audit
12/12 quotes found verbatim in their source text.
```

Non-zero exit if any quote is not found. The check that guards the design is
itself in CI.

## Three buckets, because two is a lie

Most screeners answer yes or no. The third bucket is the design decision that
took the longest to accept, because it makes the demo look worse.

A call that says nothing about who may enter is **not** a call that admits
everyone. It is a call that has to be read by a person. Forcing that into a yes
or a no is exactly what makes tools like this unusable for deciding anything
real.

So every ambiguity fails towards CANNOT DECIDE, never towards NOT ELIGIBLE:

- a quote not found in the source → undecidable
- a rule kind this screener has no check for → undecidable
- a place named that cannot be resolved to a country → undecidable
- nothing extracted at all → undecidable

**Wrongly telling someone not to apply costs them a grant. Wrongly asking a
human to look costs them a minute.** The asymmetry is deliberate, and it is
tested — 67 tests, most of them about what happens when something goes wrong.

The output says so out loud:

```
CANNOT DECIDE (2)   -- and saying so is the point
   Fondo Municipal de Cultura 2026
        no eligibility criteria could be extracted at all

   Regional Libraries Innovation Award
        this screener has no rule for: requires_accreditation
```

That second line is the tool filing its own feature request. Every
`unsupported rule` in the output is a check somebody should write next.

## On Strands, and on not using Bedrock

We used **Strands Agents SDK** with the **LiteLLM** provider rather than Bedrock,
and AgentCore is not used at all. That is a deliberate choice and worth stating
plainly, because the hackathon is an AWS one.

The reason is the same reason the whole project exists. A judge — or a
volunteer at a food bank — should be able to clone this and watch it work
without attaching a credit card to anything. The screening layer needs **no
credentials at all**; `python -m clausewitz` runs against bundled fixtures of
real calls, offline, and prints the full three-bucket output. Only `--read`,
which points the agent at a live document, needs a model key of any kind.

Strands earned its place by being the part that made the one-tool constraint
cheap to express. The agent's entire configuration is a system prompt that says
*report what the document demands, quote the sentence* and a tool list of length
one. Nothing in the framework fought that.

## What this bought us

The honest summary: **the architecture did not make the tool smarter. It made
its failures survivable.**

In four separate live runs the model did something wrong — invented a
requirement, returned a string where a list belonged, named a place that is not
a country. In none of those runs did a small organisation get told not to apply.
Three of them landed in CANNOT DECIDE, which is the correct place for them, and
the fourth taught us something about being too careful.

That fourth one is the next post.

MIT, no credentials required: **https://github.com/ssw-dot/clausewitz**

---

*Next: "Agents for Humans: caution is not free" — four bugs found by running the
thing against real calls.*
