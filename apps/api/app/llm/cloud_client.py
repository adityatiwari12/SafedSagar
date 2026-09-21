"""OpenAI-compatible chat completions client for optional cloud Llama.

Reliability:
- Bounded retries with backoff on transient failures (429, 5xx, timeouts).
  4xx auth/validation errors (401, 403, 400 unrelated to response_format,
  etc.) are NOT retried - they won't succeed on retry, so fail immediately.
- Some OpenAI-compatible providers reject `response_format:
  {"type": "json_object"}` outright (400/422 mentioning response_format in
  the error body). When that happens and `cloud_llm_json_mode` is on, retry
  once without it and pull the JSON object out of the raw text, tolerating
  a ```json ... ``` fence some providers wrap it in without strict JSON mode.
- The API key never appears in a raised exception or log line - see
  `redact_secret`.
"""

from __future__ import annotations

import json
import logging
import re
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Attempts include the first try, e.g. 3 = 1 initial + 2 retries.
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (0.5, 1.5)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class CloudLLMError(RuntimeError):
    """The cloud provider call failed (after retries, where applicable).
    The message is always pre-redacted - see `redact_secret`."""


def redact_secret(text: str) -> str:
    """Strip the configured cloud API key out of a string before it can
    land in an exception message or log line."""
    key = settings.cloud_llm_api_key
    if key and key in text:
        text = text.replace(key, "***REDACTED***")
    return text


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.cloud_llm_api_key:
        headers["Authorization"] = f"Bearer {settings.cloud_llm_api_key}"
    return headers


def _build_payload(prompt: str, json_mode: bool) -> dict:
    payload: dict = {
        "model": settings.cloud_llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _extract_json(content: str) -> dict:
    """Parse a JSON object out of model output, tolerating a ```json fence
    some providers wrap the answer in when response_format isn't honored
    (or wasn't sent at all, in the no-json-mode retry path)."""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    fence_match = _JSON_FENCE_RE.search(content)
    if fence_match:
        return json.loads(fence_match.group(1))
    # Re-raise the original error shape (JSONDecodeError) for callers that
    # branch on it.
    return json.loads(content)


def _response_format_unsupported(resp: httpx.Response) -> bool:
    """Detect a provider rejecting response_format rather than ignoring
    it. Scoped to 400/422 with 'response_format' in the error body so this
    doesn't misfire on an unrelated bad request."""
    if resp.status_code not in (400, 422):
        return False
    try:
        body_text = resp.text
    except Exception:
        return False
    return "response_format" in body_text.lower()


def _sleep(attempt: int) -> None:
    time.sleep(_BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)])


def generate_json(prompt: str, timeout: float = 120.0) -> dict:
    if not settings.cloud_llm_base_url or not settings.cloud_llm_model:
        raise RuntimeError(
            "CLOUD_LLM_BASE_URL and CLOUD_LLM_MODEL must be set when using the cloud LLM provider"
        )
    base = settings.cloud_llm_base_url.rstrip("/")
    url = f"{base}/chat/completions"
    headers = _headers()
    json_mode = settings.cloud_llm_json_mode

    last_error_text = "unknown error"
    for attempt in range(_MAX_ATTEMPTS):
        payload = _build_payload(prompt, json_mode)
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        except httpx.TimeoutException as exc:
            last_error_text = f"timeout: {exc}"
            logger.warning(
                "Cloud LLM request timed out (attempt %d/%d): %s",
                attempt + 1, _MAX_ATTEMPTS, redact_secret(str(exc)),
            )
            if attempt < _MAX_ATTEMPTS - 1:
                _sleep(attempt)
                continue
            raise CloudLLMError(redact_secret(f"Cloud LLM request timed out after {_MAX_ATTEMPTS} attempts: {exc}")) from None
        except httpx.HTTPError as exc:
            last_error_text = f"transport error: {exc}"
            logger.warning(
                "Cloud LLM request failed (attempt %d/%d): %s",
                attempt + 1, _MAX_ATTEMPTS, redact_secret(str(exc)),
            )
            if attempt < _MAX_ATTEMPTS - 1:
                _sleep(attempt)
                continue
            raise CloudLLMError(redact_secret(f"Cloud LLM request failed after {_MAX_ATTEMPTS} attempts: {exc}")) from None

        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                return _extract_json(content)
            except json.JSONDecodeError:
                last_error_text = "unparseable JSON response"
                logger.warning(
                    "Cloud LLM returned unparseable JSON (attempt %d/%d)",
                    attempt + 1, _MAX_ATTEMPTS,
                )
                if attempt < _MAX_ATTEMPTS - 1:
                    _sleep(attempt)
                    continue
                raise CloudLLMError(f"Cloud LLM returned unparseable JSON after {_MAX_ATTEMPTS} attempts") from None

        if json_mode and _response_format_unsupported(resp):
            logger.info("Cloud LLM provider rejected response_format=json_object; retrying without it")
            json_mode = False
            continue

        if resp.status_code in _RETRYABLE_STATUS:
            last_error_text = f"HTTP {resp.status_code}: {redact_secret(resp.text[:500])}"
            logger.warning(
                "Cloud LLM transient error %d (attempt %d/%d): %s",
                resp.status_code, attempt + 1, _MAX_ATTEMPTS, redact_secret(resp.text[:500]),
            )
            if attempt < _MAX_ATTEMPTS - 1:
                _sleep(attempt)
                continue
            raise CloudLLMError(
                redact_secret(f"Cloud LLM provider returned {resp.status_code} after {_MAX_ATTEMPTS} attempts: {resp.text[:500]}")
            ) from None

        # Non-retryable 4xx (auth/validation) - fail immediately, no retry.
        raise CloudLLMError(redact_secret(f"Cloud LLM provider returned {resp.status_code}: {resp.text[:500]}"))

    # Unreachable in practice (every branch above returns or raises), but
    # keeps this a well-formed function if that ever changes.
    raise CloudLLMError(redact_secret(f"Cloud LLM request failed: {last_error_text}"))
