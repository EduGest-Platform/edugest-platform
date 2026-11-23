"""KAN-130 part B: embedding providers, tested offline (no network, no API key)."""

import json
import math

import httpx
import pytest

from app.modules.knowledge.embedder import (
    BATCH_SIZE, GEMINI_MODEL, EmbeddingError, FakeEmbedder, GeminiEmbedder, Passage,
)
from app.modules.knowledge.models import EMBEDDING_DIM

KEY = "synthetic-test-key"
P1 = Passage("Calendario", "Las clases empiezan a las 9:00.")
P2 = Passage("Proyecto final", "La entrega es el 10 de diciembre.")


def norm(values):
    return math.sqrt(sum(v * v for v in values))


def gemini(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GeminiEmbedder(KEY, client=client, sleep=lambda seconds: None, **kwargs)


def ok(request, dims=EMBEDDING_DIM):
    count = len(json.loads(request.content)["requests"])
    return httpx.Response(200, json={"embeddings": [{"values": [3.0] + [0.0] * (dims - 1)} for _ in range(count)]})


# ---------- FakeEmbedder ----------


def test_fake_vectors_are_deterministic_normalised_and_distinct():
    fake = FakeEmbedder()
    first, second = fake.embed_documents([P1, P2])
    assert len(first) == EMBEDDING_DIM and math.isclose(norm(first), 1.0)
    assert fake.embed_documents([P1])[0] == first
    assert first != second
    assert fake.calls == 2


def test_fake_vector_changes_with_the_title():
    fake = FakeEmbedder()
    assert fake.embed_documents([P1])[0] != fake.embed_documents([Passage("Otro título", P1.text)])[0]


# ---------- GeminiEmbedder ----------


def test_gemini_request_uses_the_adr_model_title_task_and_dimensions():
    seen = []

    def handler(request):
        seen.append(request)
        return ok(request)

    vectors = gemini(handler).embed_documents([P1, P2])
    body = json.loads(seen[0].content)["requests"][0]
    assert seen[0].headers["x-goog-api-key"] == KEY
    assert body["model"] == f"models/{GEMINI_MODEL}"
    assert body["taskType"] == "RETRIEVAL_DOCUMENT" and body["title"] == "Calendario"
    assert body["outputDimensionality"] == EMBEDDING_DIM
    assert len(vectors) == 2 and math.isclose(norm(vectors[0]), 1.0) and vectors[0][0] == 1.0


def test_gemini_retries_rate_limits_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429) if len(calls) < 3 else ok(request)

    assert len(gemini(handler).embed_documents([P1])) == 1
    assert len(calls) == 3


@pytest.mark.parametrize(("status", "attempts"), [(400, 1), (403, 1), (503, 3)])
def test_gemini_errors_report_only_a_code(status, attempts):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(status, json={"error": {"message": "secret detail"}})

    with pytest.raises(EmbeddingError) as error:
        gemini(handler).embed_documents([P1])
    assert error.value.code == f"http_{status}" and str(error.value) == f"http_{status}"
    assert KEY not in str(error.value) and "secret detail" not in str(error.value)
    assert len(calls) == attempts


def test_gemini_timeout_is_retried_and_reported():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(EmbeddingError) as error:
        gemini(handler).embed_documents([P1])
    assert error.value.code == "timeout"


def test_gemini_rejects_wrong_dimensions_and_bad_payloads():
    with pytest.raises(EmbeddingError) as error:
        gemini(lambda request: ok(request, dims=3072)).embed_documents([P1])
    assert error.value.code == "wrong_dimensions"
    with pytest.raises(EmbeddingError) as error:
        gemini(lambda request: httpx.Response(200, json={"nothing": []})).embed_documents([P1])
    assert error.value.code == "unexpected_response"


def test_gemini_splits_large_inputs_into_batches():
    sizes = []

    def handler(request):
        sizes.append(len(json.loads(request.content)["requests"]))
        return ok(request)

    vectors = gemini(handler).embed_documents([P1] * (BATCH_SIZE + 50))
    assert sizes == [BATCH_SIZE, 50] and len(vectors) == BATCH_SIZE + 50


def test_gemini_requires_an_api_key():
    with pytest.raises(EmbeddingError) as error:
        GeminiEmbedder("")
    assert error.value.code == "missing_api_key"


MALFORMED_VECTORS = [
    pytest.param({"embeddings": [{"values": None}]}, id="values-null"),
    pytest.param({"embeddings": [{"values": 5}]}, id="values-scalar"),
    pytest.param({"embeddings": [{"values": ["0.1"] * EMBEDDING_DIM}]}, id="values-strings"),
    pytest.param({"embeddings": [{"values": [True] * EMBEDDING_DIM}]}, id="values-booleans"),
    pytest.param({"embeddings": [{"values": [0.1] * (EMBEDDING_DIM - 1) + [None]}]}, id="one-null-element"),
    pytest.param({"embeddings": [{}]}, id="values-missing"),
    pytest.param({"embeddings": ["not-an-object"]}, id="item-not-an-object"),
]


@pytest.mark.parametrize("payload", MALFORMED_VECTORS)
def test_gemini_malformed_vectors_raise_a_safe_code(payload):
    with pytest.raises(EmbeddingError) as error:
        gemini(lambda request: httpx.Response(200, json=payload)).embed_documents([P1])
    assert error.value.code == "malformed_vector"


@pytest.mark.parametrize("payload", [{"embeddings": None}, {"embeddings": {"values": [0.1]}}, [1, 2]])
def test_gemini_malformed_envelope_is_an_unexpected_response(payload):
    with pytest.raises(EmbeddingError) as error:
        gemini(lambda request: httpx.Response(200, json=payload)).embed_documents([P1])
    assert error.value.code == "unexpected_response"


def test_gemini_query_vector_uses_retrieval_query_without_title():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content)["requests"])
        return ok(request)

    vector = gemini(handler).embed_query("¿Cuándo se entrega el proyecto?")
    [body] = seen[0]
    assert body["taskType"] == "RETRIEVAL_QUERY" and "title" not in body
    assert body["outputDimensionality"] == EMBEDDING_DIM and len(vector) == EMBEDDING_DIM
