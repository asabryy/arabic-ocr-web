"""ocr_page retry/backoff + token accounting, with a scripted fake Gemini client (no network)."""

from types import SimpleNamespace

import pytest
from google.genai import errors
from prometheus_client import REGISTRY

from app.core.config import settings
from app.ocr import pipeline

MODEL = settings.GEMINI_MODEL


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def err429(msg="You exceeded your current quota. Please retry in 26.4s.", retry_delay="26s"):
    body = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": msg, "details": []}}
    if retry_delay is not None:
        body["error"]["details"].append(
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}
        )
    return errors.ClientError(429, body)


def err503():
    return errors.ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "overloaded"}})


def ok(text="نص", usage=None):
    return SimpleNamespace(text=text, usage_metadata=usage)


class FakeClient:
    """Yields the scripted outcomes in order (exceptions are raised, responses returned)."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = 0
        self.models = self

    def generate_content(self, model, contents):
        self.calls += 1
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def gemini(monkeypatch):
    sleeps = []
    monkeypatch.setattr(pipeline, "_sleep", sleeps.append)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    def install(script):
        client = FakeClient(script)
        monkeypatch.setattr(pipeline, "_get_client", lambda: client)
        return client

    install.sleeps = sleeps
    return install


def test_429_then_success_honours_retry_hint(gemini):
    client = gemini([err429(), err429(), ok("hello")])
    r429 = sample("gemini_requests_total", outcome="retry_429", model=MODEL)
    rok = sample("gemini_requests_total", outcome="ok", model=MODEL)
    b0 = sample("gemini_backoff_seconds_total", reason="429")

    assert pipeline.ocr_page(b"png") == "hello"
    assert client.calls == 3
    assert gemini.sleeps == [26.0, 26.0]
    assert sample("gemini_requests_total", outcome="retry_429", model=MODEL) == r429 + 2
    assert sample("gemini_requests_total", outcome="ok", model=MODEL) == rok + 1
    assert sample("gemini_backoff_seconds_total", reason="429") == pytest.approx(b0 + 52.0)


def test_429_delay_is_capped(gemini, monkeypatch):
    monkeypatch.setattr(settings, "OCR_429_MAX_DELAY_S", 15.0)
    gemini([err429(retry_delay="600s"), ok()])
    pipeline.ocr_page(b"png")
    assert gemini.sleeps == [15.0]


def test_429_without_hint_uses_default_backoff(gemini, monkeypatch):
    monkeypatch.setattr(settings, "OCR_429_DEFAULT_DELAY_S", 3.0)
    gemini([err429(msg="quota exceeded", retry_delay=None), err429(msg="quota exceeded", retry_delay=None), ok()])
    pipeline.ocr_page(b"png")
    assert gemini.sleeps == [3.0, 6.0]  # default × attempt number


def test_429_exhausted_raises_and_counts_error(gemini, monkeypatch):
    monkeypatch.setattr(settings, "OCR_429_MAX_RETRIES", 2)
    gemini([err429(), err429(), err429()])
    e0 = sample("gemini_requests_total", outcome="error", model=MODEL)
    with pytest.raises(errors.ClientError):
        pipeline.ocr_page(b"png")
    assert len(gemini.sleeps) == 2
    assert sample("gemini_requests_total", outcome="error", model=MODEL) == e0 + 1


def test_503_retries_with_linear_backoff(gemini):
    gemini([err503(), ok()])
    r0 = sample("gemini_requests_total", outcome="retry_503", model=MODEL)
    pipeline.ocr_page(b"png")
    assert gemini.sleeps == [2.0]
    assert sample("gemini_requests_total", outcome="retry_503", model=MODEL) == r0 + 1


def test_non_retryable_error_raises_immediately(gemini):
    gemini([errors.ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "bad"}})])
    e0 = sample("gemini_requests_total", outcome="error", model=MODEL)
    with pytest.raises(errors.ClientError):
        pipeline.ocr_page(b"png")
    assert gemini.sleeps == []
    assert sample("gemini_requests_total", outcome="error", model=MODEL) == e0 + 1


def test_usage_metadata_tokens_and_cost(gemini, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_PRICE_INPUT_USD_PER_M", 0.75)
    monkeypatch.setattr(settings, "GEMINI_PRICE_OUTPUT_USD_PER_M", 3.75)
    usage = SimpleNamespace(prompt_token_count=1000, candidates_token_count=200, thoughts_token_count=100)
    gemini([ok(usage=usage)])
    t0 = {k: sample("gemini_tokens_total", kind=k, model=MODEL) for k in ("prompt", "candidates", "thoughts")}
    c0 = sample("gemini_cost_usd_total", model=MODEL)
    pipeline.ocr_page(b"png")
    assert sample("gemini_tokens_total", kind="prompt", model=MODEL) == t0["prompt"] + 1000
    assert sample("gemini_tokens_total", kind="candidates", model=MODEL) == t0["candidates"] + 200
    assert sample("gemini_tokens_total", kind="thoughts", model=MODEL) == t0["thoughts"] + 100
    # 1000*0.75/1e6 + 300*3.75/1e6
    assert sample("gemini_cost_usd_total", model=MODEL) == pytest.approx(c0 + 0.001875)


def test_missing_usage_metadata_is_safe(gemini):
    gemini([ok(usage=None)])
    c0 = sample("gemini_cost_usd_total", model=MODEL)
    assert pipeline.ocr_page(b"png") == "نص"
    assert sample("gemini_cost_usd_total", model=MODEL) == c0


def test_retry_delay_parsing_variants():
    assert pipeline._retry_delay_seconds(err429(retry_delay="26s")) == 26.0
    assert pipeline._retry_delay_seconds(err429(retry_delay={"seconds": 5, "nanos": 500000000})) == 5.5
    assert pipeline._retry_delay_seconds(err429(msg="Please retry in 12.5s.", retry_delay=None)) == 12.5
    assert pipeline._retry_delay_seconds(err429(msg="no hint", retry_delay=None)) is None
    assert pipeline._classify(err429()) == "429"
    assert pipeline._classify(err503()) == "503"
    assert pipeline._classify(RuntimeError("boom")) == "other"


def err402():
    """Billing failure. Google sends HTTP 402 with a RESOURCE_EXHAUSTED status, which
    must NOT be mistaken for a rate limit — retrying it never succeeds."""
    return errors.ClientError(
        402,
        {
            "error": {
                "code": 402,
                "status": "RESOURCE_EXHAUSTED",
                "message": (
                    "Your prepayment credits are depleted. Please go to AI Studio at "
                    "https://ai.studio/projects to manage your project and billing."
                ),
            }
        },
    )


def test_402_billing_error_fails_fast_without_retrying(gemini):
    client = gemini([err402()])
    e0 = sample("gemini_requests_total", outcome="error", model=MODEL)
    with pytest.raises(errors.ClientError):
        pipeline.ocr_page(b"png")
    assert client.calls == 1, "402 must not be retried"
    assert gemini.sleeps == []
    assert sample("gemini_requests_total", outcome="error", model=MODEL) == e0 + 1
    assert pipeline._classify(err402()) == "other"
