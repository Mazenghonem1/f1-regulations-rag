# 1. Exact numpy search instead of FAISS

Date: 2026-09-22

## Status

Accepted. Supersedes the FAISS requirement in `PROJECT_BRIEF.md`.

## Context

The project brief specifies FAISS as the vector store. The target corpus for v1
is 150–300 chunks, embedded with `bge-small-en-v1.5` (384 dimensions).

FAISS exists to make approximate nearest-neighbour search tractable at scale.
At 300×384 floats, the entire embedding matrix is under 500KB and an exact
cosine similarity search is a single matrix multiply — sub-millisecond, and
*more* accurate than an approximate index because there is no approximation.

There is also an install cost. `faiss-cpu` wheel availability lags new CPython
releases, and the build environment here is an Intel Mac, where prebuilt wheels
are progressively less well maintained.

## Decision

Implement dense retrieval as exact cosine similarity over a numpy array, behind
a retriever interface narrow enough that FAISS can be dropped in without
touching callers.

Pin Python 3.11 rather than 3.13, independently of this decision, to avoid
wheel-availability problems across the wider ML stack.

## Consequences

Fewer dependencies, no install risk, exact rather than approximate results, and
roughly fifteen lines of code instead of an index build/persist/load cycle.

The cost is that this does not scale. Somewhere around 10⁵ vectors the linear
scan stops being free and FAISS becomes the right answer. The interface is the
hedge: swapping it is a contained change, not a refactor.

A reader who expects FAISS because the brief promised it should read this as a
deliberate override, not an omission. The write-up states it plainly —
recognising when *not* to reach for the heavyweight tool is the point.
