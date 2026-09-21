"""Cloud/local LLM provider hardening: retries, response_format fallback,
local-Ollama fallback, and metadata reporting. All HTTP is mocked via
monkeypatched httpx.post (or, for the local-fallback leg, a mocked Ollama
client function) - no real cloud call, no API key needed, ever.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import settings
from app.llm import cloud_client, generate as generate_mod


@pytest.fixture(autouse=True)
def _cloud_settings(monkeypatch):
    """A minimal valid cloud config for every test in this file, and a
    fast retry loop so tests don't actually sleep."""
    monkeypatch.setattr(settings, "cloud_llm_base_url", "https://fake-cloud.example/v1")
    monkeypatch.setattr(settings, "cloud_llm_model", "fake-model")
    monkeypatch.setattr(settings, "cloud_llm_api_key", "sk-test-super-secret-123")
    monkeypatch.setattr(settings, "cloud_llm_json_mode", True)
    monkeypatch.setattr(cloud_client, "_sleep", lambda attempt: None)
    yield


def _json_response(status_code: int, payload: dict) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


def _cloud_success_body(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


# ---------------------------------------------------------------------------
# cloud_client.generate_json - reliability
# ---------------------------------------------------------------------------


def test_cloud_success_path_parses_json(monkeypatch):
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append((url, headers, json))
        return _json_response(200, _cloud_success_body('{"answer": "ok"}'))

    monkeypatch.setattr(httpx, "post", fake_post)

    result = cloud_client.generate_json("prompt")

    assert result == {"answer": "ok"}
    assert len(calls) == 1
    assert calls[0][2]["response_format"] == {"type": "json_object"}


def test_generate_json_facade_reports_cloud_metadata(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return _json_response(200, _cloud_success_body('{"x": 1}'))

    monkeypatch.setattr(httpx, "post", fake_post)

    result = generate_mod.generate_json("prompt", provider="cloud")

    assert result == {"x": 1}
    meta = generate_mod.get_last_call_metadata()
    assert meta.provider == "cloud"
    assert meta.model == "fake-model"
    assert meta.fallback_used is False


def test_5xx_then_success_is_retried(monkeypatch):
    responses = [
        httpx.Response(500, text="server error"),
        _json_response(200, _cloud_success_body('{"ok": true}')),
    ]
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append(json)
        return responses.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)

    result = cloud_client.generate_json("prompt")

    assert result == {"ok": True}
    assert len(calls) == 2


def test_401_is_not_retried_and_raises(monkeypatch):
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append(json)
        return _json_response(401, {"error": "invalid api key"})

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(cloud_client.CloudLLMError):
        cloud_client.generate_json("prompt")

    assert len(calls) == 1


def test_response_format_unsupported_is_retried_without_it(monkeypatch):
    payloads = []

    def fake_post(url, *, headers, json, timeout):
        payloads.append(json)
        if len(payloads) == 1:
            return _json_response(400, {"error": {"message": "Unknown parameter: response_format"}})
        content = "Here you go:\n```json\n" + json_module_dumps({"answer": "fenced"}) + "\n```"
        return _json_response(200, _cloud_success_body(content))

    def json_module_dumps(obj):
        return json.dumps(obj)

    monkeypatch.setattr(httpx, "post", fake_post)

    result = cloud_client.generate_json("prompt")

    assert result == {"answer": "fenced"}
    assert len(payloads) == 2
    assert "response_format" in payloads[0]
    assert "response_format" not in payloads[1]


# ---------------------------------------------------------------------------
# generate.generate_json facade - local fallback
# ---------------------------------------------------------------------------


def test_cloud_failure_with_fallback_on_uses_ollama(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return httpx.Response(500, text="down")

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(settings, "llm_fallback_to_local", True)
    monkeypatch.setattr(generate_mod, "ollama_generate_json", lambda *a, **kw: {"local": True})

    result = generate_mod.generate_json("prompt", provider="cloud")

    assert result == {"local": True}
    meta = generate_mod.get_last_call_metadata()
    assert meta.provider == "ollama"
    assert meta.fallback_used is True


def test_cloud_failure_with_fallback_off_raises(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return httpx.Response(500, text="down")

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(settings, "llm_fallback_to_local", False)

    with pytest.raises(cloud_client.CloudLLMError):
        generate_mod.generate_json("prompt", provider="cloud")


# ---------------------------------------------------------------------------
# Secret hygiene
# ---------------------------------------------------------------------------


def test_api_key_never_appears_in_exception_or_logs(monkeypatch, caplog):
    secret = settings.cloud_llm_api_key
    assert secret

    def fake_post(url, *, headers, json, timeout):
        # Echo the auth header back in the error body - the worst case,
        # where the provider's own error response contains the key.
        return httpx.Response(401, text=f"unauthorized, saw header {headers.get('Authorization')}")

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level("WARNING"):
        with pytest.raises(cloud_client.CloudLLMError) as excinfo:
            cloud_client.generate_json("prompt")

    assert secret not in str(excinfo.value)
    for record in caplog.records:
        assert secret not in record.getMessage()
