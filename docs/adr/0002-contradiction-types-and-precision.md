# 2. Contradictions split by type, measured on precision as well as recall

Date: 2026-09-22

## Status

Accepted. Extends the project's evaluation contract.

## Context

The brief treats "contradiction" as one phenomenon and names one headline
metric: contradiction *recall*, the fraction of seeded contradictions the system
flags.

Two problems.

First, the phenomena differ in kind. A disagreement between two Stewards' panels
(*Divergent Precedent*) and a Decision made obsolete by a later rule change
(*Superseded Precedent*) share no detection logic: one compares Outcomes across
Decisions, the other compares dates against an Article's change history. Fusing
them into one detector means neither can be tuned or reported honestly.

Second, and more seriously: F1 penalties legitimately vary. They escalate with
repeat offences and turn on conditions, session, and intent. A naive rule of
"same Article, different Outcome → flag" fires constantly on *Justified
Distinctions*, which are correct outcomes, not contradictions.

Recall alone cannot detect this failure. A detector that flags every pair scores
recall 1.0 while being worthless. The brief's headline metric is, on its own,
trivially gamed.

## Decision

Model Divergent Precedent and Superseded Precedent as separate detectors with
separate reported numbers. Represent Justified Distinction explicitly, as a
suppression check rather than an unmodelled gap.

Report contradiction **precision alongside recall**, both overall and per
detector.

## Consequences

The eval set needs negative cases — question/context pairs where outcomes differ
for good reason and the correct behaviour is *not* to flag. This is extra
hand-authoring work the brief did not budget for, and it is the work that makes
the headline number mean something.

Two detectors mean two sets of numbers rather than one clean figure. That is a
fair description of the system rather than a flattering one.

Reporting "recall 0.9 / precision 0.7" invites the question of why precision is
lower. That question has a real answer — Justified Distinctions are genuinely
hard — and being able to answer it is worth more than a single unexamined
number.
