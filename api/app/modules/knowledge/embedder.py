"""Embedding providers for the RAG knowledge base (KAN-130, part B).

Ingestion depends only on the Embedder protocol, so the provider can change without touching the pipeline.
Vectors are L2-normalised: gemini-embedding-001 only normalises them itself at 3072 dimensions (ADR-0005).
Errors carry a short code that is safe to log and audit; they never contain the API key or document text.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.modules.knowledge.models import EMBEDDING_DIM

GEMINI_MODEL = "gemini-embedding-001"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:batchEmbedContents"
BATCH_SIZE = 100  # maximum number of requests we send in one batchEmbedContents call
RETRY_STATUS = frozenset({429, 500, 503})


@dataclass(frozen=True)
class Passage:
    """One chunk to embed. The title improves retrieval quality for RETRIEVAL_DOCUMENT."""

    title: str
    text: str


class EmbeddingError(RuntimeError):
    """Vectors could not be obtained. `code` is the only detail: no secrets, no text."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Embedder(Protocol):
    model: str
    dimensions: int

    def embed_documents(self, passages: Sequence[Passage]) -> list[list[float]]: ...


def normalize(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0 or not math.isfinite(norm):
        raise EmbeddingError("invalid_vector")
    return [v / norm for v in values]


class FakeEmbedder:
    """Deterministic offline vectors for tests and CI: the same passage always gives the same vector."""

    def __init__(self, model: str = "fake-embedding-v1", dimensions: int = EMBEDDING_DIM):
        self.model = model
        self.dimensions = dimensions
        self.calls = 0

    def embed_documents(self, passages: Sequence[Passage]) -> list[list[float]]:
        self.calls += 1
        return [self._vector(f"{p.title}\n{p.text}") for p in passages]

    def _vector(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self.dimensions:
            digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
            values.extend((byte - 127.5) / 127.5 for byte in digest)
            counter += 1
        return normalize(values[: self.dimensions])


class GeminiEmbedder:
    """gemini-embedding-001 through the batch endpoint, with retries on rate limits, server errors and network errors."""

    def __init__(self, api_key: str, client: httpx.Client | None = None, timeout: float = 30.0,
                 attempts: int = 3, sleep: Callable[[float], None] = time.sleep):
        if not api_key:
            raise EmbeddingError("missing_api_key")
        self.model = GEMINI_MODEL
        self.dimensions = EMBEDDING_DIM
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {"x-goog-api-key": api_key}
        self._attempts = attempts
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def embed_documents(self, passages: Sequence[Passage]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(passages), BATCH_SIZE):
            vectors.extend(self._batch(passages[start:start + BATCH_SIZE]))
        return vectors

    def _batch(self, passages: Sequence[Passage]) -> list[list[float]]:
        body = {"requests": [
            {"model": f"models/{GEMINI_MODEL}", "content": {"parts": [{"text": p.text}]},
             "taskType": "RETRIEVAL_DOCUMENT", "title": p.title, "outputDimensionality": self.dimensions}
            for p in passages
        ]}
        response = self._post(body)
        try:
            items = response.json()["embeddings"]
        except (ValueError, KeyError, TypeError):
            raise EmbeddingError("unexpected_response") from None
        if not isinstance(items, list) or len(items) != len(passages):
            raise EmbeddingError("unexpected_response")
        return [normalize(self._values(item)) for item in items]

    def _values(self, item: object) -> list[float]:
        """One vector from a 200 response. Any malformed shape becomes an EmbeddingError, never a TypeError,
        so the pipeline keeps the text and moves on to the next document."""
        values = item.get("values") if isinstance(item, dict) else None
        if not isinstance(values, list) or not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in values
        ):
            raise EmbeddingError("malformed_vector")
        if len(values) != self.dimensions:
            raise EmbeddingError("wrong_dimensions")
        return [float(v) for v in values]

    def _post(self, body: dict) -> httpx.Response:
        code = "no_attempt"
        for attempt in range(1, self._attempts + 1):
            try:
                response = self._client.post(GEMINI_URL, json=body, headers=self._headers)
            except httpx.TimeoutException:
                code = "timeout"
            except httpx.TransportError:
                code = "network_error"
            else:
                if response.status_code == 200:
                    return response
                code = f"http_{response.status_code}"
                if response.status_code not in RETRY_STATUS:
                    raise EmbeddingError(code)
            if attempt < self._attempts:
                self._sleep(2 * attempt)
        raise EmbeddingError(code)
