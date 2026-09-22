# Context

Glossary for the F1 Regulations & Stewards' Decisions RAG.
Terms only — no implementation details, no plans.

## Corpus terms

**Regulation** — FIA-published rulebook text (Sporting, Technical, Financial,
Operational). Issued in numbered *Issues*, each with an effective date.

**Issue** — One dated publication of a Regulation. Issue N+1 supersedes Issue N.
Every historical Issue remains published, so the change history is observable
rather than inferred.

**Article** — A numbered clause within a Regulation, the unit a citation points
to. Two notations exist and both are valid Article IDs:
- Bare (2023–2025): `33.3`
- Section-prefixed (2026+): `C3.14.4`

**Decision** — One FIA Stewards' document concerning one alleged infringement at
one event. Distinct from the other per-event documents (classifications,
scrutineering reports, event notes), which are *not* Decisions.

**Outcome** — What the Stewards imposed, extracted as structured metadata rather
than free text. Includes "No further action", which is an Outcome, not an
absence of one.

**Event** — One Grand Prix weekend. The unit Decisions are published under.

## Contradiction terms

**Contradiction** — Umbrella term only. Never used as a detector name, because
the detectable phenomena below are different in kind and must be measured
separately.

**Divergent Precedent** — Two or more Decisions citing the same Article on
materially similar incidents, reaching *different* Outcomes. A disagreement
between panels.

**Superseded Precedent** — A Decision applying an Article that was later
amended, such that the Decision no longer reflects the current rule. Not a
disagreement; a timeline problem. Requires the Article's actual change date.

**Justified Distinction** — Different Outcomes that are *correct* because the
facts differ: wet vs dry, first vs repeat offence, racing incident vs deliberate
act, different session. **This is not a contradiction.** Flagging one is a false
positive, and the reason contradiction detection is measured on precision as
well as recall.

**Mitigating Factor** — Evidence in a Decision that establishes a Justified
Distinction and therefore suppresses a Divergent Precedent flag.

## Evaluation terms

**Seeded Contradiction** — An eval question written against a *known*,
researched real-world divergence or supersession, for which the correct flag is
known in advance. The ground truth for contradiction recall.

**Coverage** — The fraction of Decision documents that yielded a given
structured field (cited Article, Outcome) during parsing. A corpus-quality
measure, reported per pipeline run — distinct from any retrieval metric.
