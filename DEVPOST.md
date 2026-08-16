# Candidatura de Devpost — Clausewitz

Todo listo para pegar. **agentsforhumans.devpost.com → Submit.**
Cierra el **14 de septiembre**.

---

## Campos del formulario

### Project name
```
Clausewitz
```

### Elevator pitch (máx. 200 caracteres)
```
Small orgs waste weeks applying for funding they were never eligible for. Clausewitz screens open calls against what you actually are, and quotes the clause that disqualifies you.
```
*(179 caracteres.)*

### Track
```
Good Neighbor Agents
```

### Built with (etiquetas)
```
strands-agents, python, litellm, gemini, json-schema, unittest, open-source
```

### Try it out (enlaces)
```
https://github.com/ssw-dot/clausewitz
```

### Video demo
```
[pegar el enlace de YouTube — PÚBLICO, no "no listado"]
```

### AWS Builder ID
```
[pegar el tuyo]
```

---

## Descripción larga

Pegar tal cual en el editor de Devpost.

---

### Inspiration

We went looking for funding for a small project. In one afternoon we read the
rules of three open calls advertising **$224,000 between them**. Here is what
the rules actually said:

- **$148,445** — *"Grand Champion: $300 in Featherless AI credits."* The prize
  is not money.
- **$35,320** — *"Prizes: TBD. Further announcements will be made soon!"* And
  students only.
- **$40,000** — *"At least one team member must attend the NeurIPS 2026
  presentation in person."*

Three for three. Every one of them findable in ten minutes of careful reading,
and every one of them capable of eating a week of work if you skip that reading.

We had the ten minutes. Then we thought about who doesn't.

A neighbourhood library. A food bank. An all-volunteer group with two people and
no grants officer, writing an application at night after the day job. They do
the work. They find out at the end — if they find out at all. Nobody writes back
to say *"you were never eligible, it was in paragraph nine."*

**Clausewitz is those ten minutes, done for every call at once, with the
disqualifying sentence quoted back to you.**

### What it does

You describe your organisation once — country, legal form, whether it can send
someone somewhere in person, whether it can pay costs up front and be reimbursed
later, how many people it has. Then you point it at open calls.

It returns three buckets:

```
Screening 8 open calls for: Biblioteca Vecinal San Andres

  eligible 3   not eligible 3   needs a human 2

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

**No exclusion is ever a bare label.** If we cannot show you the sentence, we do
not reject the call.

### How we built it

Two layers, and the split between them is the whole design.

**The model reads.** A Strands agent is given exactly one job: report each demand
a call makes on who may enter, quoting the sentence it came from. It has one
tool, `report_requirement`, and no ability to return a verdict.

**The code decides.** `screening.py` is ordinary Python — one pure function per
rule, no model, no network, and no third-party dependencies at all. It can be
read, tested and argued with.

Why split them: a language model is genuinely good at finding the eligibility
sentence buried on page four between the sponsor logos and the schedule. It is
genuinely bad at being trusted with the answer, because **when it is wrong it is
wrong fluently.** So it is given the reading and denied the verdict.

We used the LiteLLM provider rather than Bedrock, deliberately. AgentCore is not
used either. A judge should be able to clone this and watch it work without
attaching a credit card to anything — and the screening layer needs no
credentials at all.

### The part we are most pleased with

**What enforces the split is not the prompt. It is a function.**

Prompts are requests. Every requirement the model reports must quote text that
appears **verbatim** in the source — after folding only the differences that are
not differences: curly quotes, non-breaking spaces, line wrapping.

A requirement the model invented quotes nothing that exists. It fails the check
and is dropped.

**A hallucination cannot become a rejection.** At worst it becomes a missing data
point, which pushes the call towards a human.

That is a property of the code, not a claim about the model — so it is testable
without ever calling one. `--audit` prints every quote against its source and
exits non-zero if any is not found:

```
12/12 quotes found verbatim in their source text.
```

### Three buckets, because two is a lie

Most screeners answer yes or no. The third bucket is the design decision.

A call that says nothing about who may enter is **not** a call that admits
everyone. It is a call that has to be read by a person. Forcing that into a yes
or a no is exactly what makes tools like this unusable for deciding anything.

So every ambiguity fails towards CANNOT DECIDE, never towards NOT ELIGIBLE:

- a quote not found in the source → undecidable
- a rule kind this screener has no check for → undecidable
- a place named that cannot be resolved to a country → undecidable
- nothing extracted at all → undecidable

**Wrongly telling someone not to apply costs them a grant. Wrongly asking a human
to look costs them a minute.** The asymmetry is deliberate, and it is tested.

### Challenges we ran into

**A country is not a country.** Our first version compared the profile's country
against whatever list the model returned. Then a real call said *"void in Brazil,
Quebec, Russia..."* — and Quebec is not a country. The screen silently ignored
it and called the org eligible. It now reports any place it cannot resolve and
sends the call to a human. An exclusion nobody evaluated is not an absence of
exclusion.

**A string is a list of letters.** A live run returned `value="individual"`
where a list was expected, and the code dutifully iterated it, producing the
reason *"the call requires ['a','d','i','l','n','u','v'], and this profile is a
nonprofit."* Funny in a test, catastrophic in production: it excludes wrongly and
sounds authoritative doing it. Normalising inputs is now its own module with its
own tests.

**Caution is not free.** We made every unrecognised term stop the screen, which
sounded rigorous until a real call read *"open to registered nonprofits and
community groups."* The profile **is** a nonprofit — it is on the list — but
`community_group` was not a term our table carried, so a plainly eligible call
got sent to a human. The fix is an asymmetry: an unknown entry on an **allow**
list can only ever widen who may enter, so once the profile matches something we
did resolve, the leftovers cannot change the answer. On a **deny** list the same
leftover is dangerous — it could be this profile's own country under another
name — and always stops the screen. A tool that cries wolf on the easy cases
stops being read on the hard ones.

**A network failure is not a verdict.** When the model could not be reached, the
run produced zero requirements — which printed as *"no eligibility criteria could
be extracted at all."* That sentence is a statement about the document. When the
truth is that the connection failed, it is a lie in the user's favour, and they
would act on it. Transport failures now have their own exit code and say so.

Each of those was found by running the thing against real calls, not by
imagining edge cases.

### What we learned

**The useful output of a screening tool is the reason, not the answer.** We
started out trying to sort calls into yes and no. What actually helps someone is
being handed the sentence, so they can disagree with it. A tool that says "no"
without showing why has to be trusted completely or not at all, and nobody
should trust this completely.

### What's next

- **More rule kinds.** Every `unsupported rule` in the output is a feature
  request the tool wrote for itself.
- **A shared profile format**, so a small organisation fills it in once and
  reuses it.
- **Watching calls over time.** The genuinely interesting event is a call whose
  rules *change* after you started writing.

### Disclosure of pre-existing work

The rules require projects to be newly created during the submission period and
any pre-existing work to be disclosed. Stating it plainly:

- **All code in this repository was written during the submission period.** No
  file was carried in from an earlier project.
- **The ideas were not all invented here.** We previously built an unrelated tool
  (a phone-quote agent) that established two patterns reused here as design
  knowledge: printing exclusions rather than silently filtering them, and
  validating narrow fields against their expected shape rather than redacting
  bluntly. No code, tests or text were copied.
- The real calls quoted in `fixtures/calls.json` are calls we read while looking
  for funding. The wording is theirs; the screening is ours.
- Development used AI coding assistants, which the rules permit explicitly.

---

## Antes de enviar

- [ ] Vídeo subido a YouTube **como público** (no "no listado")
- [ ] Menos de 5 minutos — el nuestro dura **2:39**
- [ ] Repo público con **licencia MIT visible en About** ✅ ya verificado
- [ ] AWS Builder ID pegado
- [ ] Enlace de demo en vivo, si el endpoint está desplegado (**sube nota**)
- [ ] Post en builder.aws.com (**puntos extra**)
