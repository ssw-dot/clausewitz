# Clausewitz

**Screens open calls against what your organisation actually is, and quotes the
clause that disqualifies you — before you spend a week on the application.**

Built for the AWS **Agents for Humans** hackathon · track: **Good Neighbor
Agents** · [MIT licensed](LICENSE)

---

## The problem, and how we found it

We went looking for funding for a small project. In one afternoon we read the
rules of three open calls advertising **$224,000 between them**. Here is what
the rules actually said:

| Advertised | The sentence that ended it |
|---|---|
| **$148,445** | *"Grand Champion: $300 in Featherless AI credits"* — the prize is not money |
| **$35,320** | *"Prizes: TBD. Further announcements will be made soon!"* — and students only |
| **$40,000** | *"At least one team member must attend the NeurIPS 2026 presentation in person."* |

Three for three. Each one findable in ten minutes of reading, and each one
capable of eating a week of work if you don't do that reading.

Now picture who this actually happens to: a neighbourhood library, a food bank,
an all-volunteer group with two people and no grants officer. They write the
application. They find out at the end — if they find out at all.

**Clausewitz is that ten minutes of reading, done for every call at once, with
the disqualifying sentence quoted back to you.**

## What it does

```
$ python -m clausewitz

Screening 8 open calls for: Biblioteca Vecinal San Andres

  eligible 3   not eligible 3   needs a human 2

ELIGIBLE (3)
   Agents for Humans Hackathon  --  $10,000 / $5,000 / $3,000 / $2,000 cash
   CALL-E: Your Code Is Calling  --  $200 x 5 feedback prize
   Neighbourhood Resilience Micro-Grant  --  $5,000 cash

NOT ELIGIBLE (3)   -- with the clause, not a label
   Global Innovation Build Challenge V2
        "Grand Champion: $300 in Featherless AI credits"
        -> the award is not money, and this profile needs cash rather than credit

   AWS Trainium Frontier Competition
        "At least one team member must attend the NeurIPS 2026 presentation in
         person."
        -> attendance in person is required and this profile cannot travel

CANNOT DECIDE (2)   -- and saying so is the point
   Fondo Municipal de Cultura 2026
        no eligibility criteria could be extracted at all

   Regional Libraries Innovation Award
        this screener has no rule for: requires_accreditation

3 applications not worth writing. At roughly six hours each, about 18 hours back.
```

## The design decision everything follows from

**The model reads. The code decides.**

A language model is genuinely good at finding the eligibility sentence buried on
page four between the sponsor logos and the schedule. It is genuinely bad at
being trusted with the answer, because **when it is wrong it is wrong fluently.**

So the Strands agent is given exactly one job: report each demand the call makes,
**quoting the sentence it came from**. It never returns a verdict.

Then every quote is checked against the source text, character for character. A
requirement the model invented quotes nothing that exists — it fails the check
and is dropped.

**A hallucination cannot become a rejection.** At worst it becomes a missing
data point, which pushes the call towards a human.

That guarantee is not a claim about the prompt. It is a property of the code,
and it is tested 61 times without ever calling a model.

### Three buckets, because two is a lie

Most screeners answer yes or no. The third bucket is the point:

- **ELIGIBLE** — every rule that was read, passed
- **EXCLUDED** — a rule blocked, **and here is the sentence**
- **UNDECIDABLE** — something could not be read, resolved, or understood

A call that says nothing about who may enter is **not** a call that admits
everyone. It is one that needs a person. Forcing that into a yes or a no is
exactly what makes these tools unusable for deciding anything.

**Every ambiguity fails towards UNDECIDABLE, never towards EXCLUDED.** Wrongly
telling someone not to apply costs them a grant. Wrongly asking a human to look
costs them a minute.

## Try it

No account, no key, no network:

```bash
git clone <this repo> && cd clausewitz
python -m clausewitz                              # the screening above
python -m clausewitz --audit                      # prove every quote is verbatim
python -m unittest discover -s tests -p "test_*.py"
```

`--audit` prints each quote against its source and exits non-zero if any is not
found. It is the guarantee, made runnable:

```
12/12 quotes found verbatim in their source text.
```

To read a **new** call with the model:

```bash
pip install "strands-agents[litellm]"
export GOOGLE_API_KEY=...          # a free-tier key is enough
python -m clausewitz --read path/to/rules.txt
```

## Architecture

Full diagram and rationale in **[ARQUITECTURA.md](ARQUITECTURA.md)**.

```
rules text ──► Strands Agent ──► Requirement{kind, quote, value}
                                        │
                                        ▼
                            quote_is_grounded()?          ◄── the gate
                          ┌─────────────┴─────────────┐
                       no │                           │ yes
                          ▼                           ▼
                    UNDECIDABLE            screening.py  ◄── profile
                                          (pure functions,
                                           no model, no net)
                                                │
                              ┌─────────────────┼─────────────────┐
                              ▼                 ▼                 ▼
                          ELIGIBLE          EXCLUDED         UNDECIDABLE
                                          + the clause
```

## Built with

- **[Strands Agents SDK](https://strandsagents.com)** — the reading layer
- **LiteLLM** provider, so it runs on a free API key rather than requiring an
  AWS account with billing attached. AgentCore is not used, deliberately: a
  judge should be able to reproduce this without putting a card down.
- Python standard library for everything that decides. The screening layer has
  **no third-party dependencies at all.**

## What's next

- More rule kinds. Every `unsupported rule` in the output is a feature request
  the tool wrote for itself.
- A shared profile format, so a small organisation fills it in once.
- Watching calls over time: the interesting event is a call whose rules *change*
  after you started writing.

## Disclosure of pre-existing work

The hackathon rules require that projects be newly created during the submission
period and that any pre-existing work be disclosed. Stating it plainly:

- **All code in this repository was written during the submission period.** No
  file was carried in from an earlier project.
- **The ideas were not invented here.** The authors previously built an
  unrelated tool (a phone-quote agent) that established two patterns reused as
  *design knowledge*: printing exclusions rather than silently filtering them,
  and validating narrow fields against their expected shape rather than
  redacting bluntly. No code, tests or text were copied.
- The three real calls quoted in `fixtures/calls.json` are calls the authors
  read while looking for funding. The wording is theirs; the screening is ours.
- Development used AI coding assistants, which the rules permit explicitly.
