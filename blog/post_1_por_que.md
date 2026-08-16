# Agents for Humans: we read $223,765 worth of open calls and none of them paid cash

*Post 1 of 3 on building Clausewitz for the Agents for Humans hackathon.*

---

We went looking for funding for a small project. In one afternoon we read the
rules of three open calls advertising **$223,765 between them**.

Here is what the rules actually said.

**$148,445.** The headline number on the front page. Down in the prize section:

> *"Grand Champion: $300 in Featherless AI credits."*

The prize is not money. It is credit on one vendor's inference platform. If what
you need is to pay a bill, winning this outright leaves you exactly where you
started.

**$35,320.** Also real, also advertised, also on the front page:

> *"Prizes: TBD. Further announcements will be made soon!"*

There is no prize yet. The number is a plan. And in the eligibility section, it
is open to enrolled students only.

**$40,000.** The most honest of the three, and the most expensive to miss:

> *"At least one team member must attend the NeurIPS 2026 presentation in
> person."*

A flight, a hotel, and a visa, on top of the work. For an organisation without a
travel budget this is not a competition, it is a wall — and the wall is in a
paragraph you reach after you have already started imagining what you would do
with the money.

Three for three. Every one of them findable in ten minutes of careful reading,
and every one of them capable of eating a week of work if you skip that reading.

## We had the ten minutes

That is the part worth sitting with.

We are two people with time to read rulebooks, because reading rulebooks is
adjacent to what we do. We caught all three before writing a line of code.

Then we thought about who doesn't.

A neighbourhood library. A food bank. An all-volunteer group with two people and
no grants officer, writing an application at eleven at night after the day job.
They do the work — six hours, eight hours, a weekend — and they find out at the
end. **If they find out at all.** Nobody writes back to say *"you were never
eligible, it was in paragraph nine."* The rejection, when it comes, says
*"thank you for your interest, we received many strong applications."*

The information that would have saved them the weekend was public, free, and
sitting in the rules the whole time. It just costs ten minutes per call to
extract, and it costs those ten minutes **whether or not** the answer turns out
to be no.

That asymmetry is the entire problem. Careful reading is cheapest for the people
who need it least.

## What we built

**Clausewitz is those ten minutes, done for every call at once, with the
disqualifying sentence quoted back to you.**

You describe your organisation once: country, legal form, whether it can send
someone somewhere in person, whether it can pay costs up front and be reimbursed
later, how many people it has. Then you point it at open calls.

It sorts them into three buckets and, for anything it rejects, it shows you the
sentence:

```
NOT ELIGIBLE (3)   -- with the clause, not a label
   Global Innovation Build Challenge V2
        "Grand Champion: $300 in Featherless AI credits"
        -> the award is not money, and this profile needs cash rather than credit

   AWS Trainium Frontier Competition
        "At least one team member must attend the NeurIPS 2026 presentation in
         person."
        -> attendance in person is required and this profile cannot travel

3 applications not worth writing. At roughly six hours each, about 18 hours back.
```

Those are the real calls. The wording is theirs.

## Why the quote is the product

The first version we sketched sorted calls into yes and no. It would have been
easier to build and it would have been useless.

A tool that says *no* without showing why has to be trusted completely or not at
all — and **nobody should trust this completely.** It is reading legal-ish prose
with a language model. It will be wrong sometimes.

Handing you the sentence changes what the tool is for. It stops being an oracle
and becomes a reader that points. You can look at *"Grand Champion: $300 in
Featherless AI credits"* and decide in two seconds whether the machine
understood the situation. When it is right, you saved six hours. When it is
wrong, you noticed immediately, because the evidence came attached.

**The useful output of a screening tool is the reason, not the answer.** That
took us one rewrite to learn and it shaped everything after it.

## Where the hackathon fits

Agents for Humans has a track called **Good Neighbor Agents**, and this is the
most literal reading of that phrase we could think of: the agent does the
tedious, skippable, high-stakes reading that a well-resourced organisation pays
someone to do, for the organisations that cannot.

The build itself is a Strands agent with exactly one tool and no authority to
decide anything — which is a longer story, and it is the next post.

The code is MIT and runs with no credentials:
**https://github.com/ssw-dot/clausewitz**

---

*Next: "Agents for Humans: the model reads, the code decides" — how we made it
structurally impossible for a hallucination to become a rejection.*
