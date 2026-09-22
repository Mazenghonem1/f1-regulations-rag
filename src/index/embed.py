"""Embed corpus chunks with BAAI/bge-small-en-v1.5, cached to disk.

CPU-only Intel Mac (docs/RECON.md) -- embedding ~1700 chunks is slow enough
to do once and cache, keyed on the chunk_id+text pairs so a corpus edit
invalidates the cache rather than silently serving stale vectors.
"""
import hashlib
import pathlib

import numpy as np
from sentence_transformers import SentenceTransformer

CACHE_DIR = pathlib.Path("data/processed/.embed_cache")
MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _corpus_hash(chunks: list[dict]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c["chunk_id"].encode())
        h.update(b"\0")
        h.update(c["text"].encode())
        h.update(b"\0")
    return h.hexdigest()[:16]


def embed_chunks(chunks: list[dict]) -> np.ndarray:
    """Return an (N, D) float32 array of embeddings, one row per chunk, in
    the same order as `chunks`. Cached to disk by a hash of chunk_id+text."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{_corpus_hash(chunks)}.npy"
    if cache_file.exists():
        return np.load(cache_file)

    model = _get_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(
        texts, normalize_embeddings=True, show_progress_bar=True, convert_to_numpy=True
    ).astype(np.float32)
    np.save(cache_file, embeddings)
    return embeddings


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string with the same model/normalisation as the
    corpus, so dot product == cosine similarity."""
    return embed_texts([query])[0]


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of strings as one batch (uncached) -- for ad-hoc text
    comparisons outside the indexed corpus, e.g. comparing two Decisions'
    Fact text. Use embed_chunks for the corpus itself, which caches to disk."""
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True).astype(
        np.float32
    )
