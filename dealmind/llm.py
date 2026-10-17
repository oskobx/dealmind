"""Crusoe Managed Inference client (§7). Every model call goes through `chat`/`chat_full`.

Applies docs/crusoe-skill.md:
- §6 rate limits: per-model client-side pacing (RPM window), jittered exponential backoff on
  429/503/connection errors, Retry-After honored, rate-limit headers recorded per call.
- §4.5/§4.6 reasoning: thinking toggled per role via chat_template_kwargs.enable_thinking;
  empty content (reasoning ate the budget) retried once with a larger max_tokens.
- §8 prefix caching: callers keep the system prompt byte-identical and histories append-only;
  usage.prompt_tokens_details.cached_tokens is logged for every call so hit rates are visible.

The API key is read from the environment and never logged, printed or returned.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
from collections import deque
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from dealmind import config, events

load_dotenv(override=True)

RETRYABLE = (RateLimitError, InternalServerError, APIConnectionError, APITimeoutError)
JITTER_SECONDS = 0.5
RETRY_AFTER_CAP_SECONDS = 30.0
REQUEST_TIMEOUT_SECONDS = 90.0
# crusoe-skill.md §6 describes 30 RPM per model without a payment method. Measured on Oct 17 on this
# account: 40 sequential calls each on Nano, Qwen and Lightning with no 429, so the RPM pacer is off
# by default (DEALMIND_RPM=N turns it on). What did fail was concurrency: Lightning returns 429
# "max_requests_limit (orchestrator)" above ~3 requests in flight, while Nano and Qwen took 12 in
# parallel. So every model gets an in-flight cap instead.
RPM_LIMIT = int(os.environ.get("DEALMIND_RPM", "0"))  # 0 = off
MAX_INFLIGHT = int(os.environ.get("DEALMIND_MAX_INFLIGHT", "8"))
MAX_INFLIGHT_PER_MODEL: dict[str, int] = {config.MODEL_LIGHTNING: 2}


@dataclass(frozen=True)
class RoleSettings:
    temperature: float
    top_p: float = 0.95
    presence_penalty: float = 0.0
    thinking: bool = False  # chat_template_kwargs.enable_thinking (crusoe-skill.md §4.6)


# Sampling per crusoe-skill.md §4.5. Qwen non-thinking: temperature 0.7, top_p 0.8, presence 1.5.
# Thinking is off everywhere: the negotiator and suppliers only write short messages, the tone
# labeler answers one word, and the coach gets a larger budget with thinking off for speed.
ROLE_SETTINGS: dict[str, RoleSettings] = {
    "negotiator": RoleSettings(temperature=0.6),
    "tone": RoleSettings(temperature=0.0),
    "supplier": RoleSettings(temperature=0.7, top_p=0.8, presence_penalty=1.5),
    "coach": RoleSettings(temperature=0.5),
    "report": RoleSettings(temperature=0.5),
}
DEFAULT_SETTINGS = RoleSettings(temperature=0.5)


@dataclass
class LLMResponse:
    content: str
    model: str  # what we asked for
    served_by: str  # what the API reports it used (matters for the Switchyard router, §7.1)
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    finish_reason: str
    attempts: int
    reasoning_chars: int = 0


class LLMError(RuntimeError):
    pass


# --- client and pacing -------------------------------------------------------

_client: OpenAI | None = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    with _client_lock:
        if _client is None:
            key = os.environ.get(config.API_KEY_ENV)
            if not key:
                raise LLMError(f"{config.API_KEY_ENV} is not set; put it in .env")
            # max_retries=0: we retry ourselves so every attempt is paced and logged.
            _client = OpenAI(base_url=config.CRUSOE_BASE_URL, api_key=key, max_retries=0, timeout=REQUEST_TIMEOUT_SECONDS)
        return _client


class _Pacer:
    """Keeps requests per model under RPM_LIMIT in any 60 s window (crusoe-skill.md §6)."""

    def __init__(self, rpm: int) -> None:
        self.rpm = rpm
        self._lock = threading.Lock()
        self._calls: dict[str, deque[float]] = {}

    def wait(self, model: str) -> float:
        waited = 0.0
        while True:
            with self._lock:
                window = self._calls.setdefault(model, deque())
                now = time.monotonic()
                while window and now - window[0] > 60.0:
                    window.popleft()
                if len(window) < self.rpm:
                    window.append(now)
                    return waited
                sleep_for = 60.0 - (now - window[0]) + 0.05
            time.sleep(sleep_for)
            waited += sleep_for


_pacer = _Pacer(RPM_LIMIT) if RPM_LIMIT > 0 else None


class _Gate:
    """Caps the number of requests in flight per model (the limit Crusoe actually enforced on Oct 17)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._slots: dict[str, threading.Semaphore] = {}

    def slot(self, model: str) -> threading.Semaphore:
        with self._lock:
            if model not in self._slots:
                self._slots[model] = threading.Semaphore(MAX_INFLIGHT_PER_MODEL.get(model, MAX_INFLIGHT))
            return self._slots[model]


_gate = _Gate()

# §7.1 optional NeMo Switchyard router for negotiator calls (off unless run.py --router switchyard)
_router_base_url: str | None = None
_router_client: OpenAI | None = None


def set_router(base_url: str | None) -> None:
    """Route negotiator calls through a local Switchyard proxy at `base_url`; None turns it off."""
    global _router_base_url, _router_client
    _router_base_url = base_url
    _router_client = None


def _get_router_client() -> OpenAI:
    global _router_client
    with _client_lock:
        if _router_client is None:
            key = os.environ.get(config.API_KEY_ENV) or "none"  # the local proxy holds the real key itself
            _router_client = OpenAI(base_url=_router_base_url, api_key=key, max_retries=0, timeout=REQUEST_TIMEOUT_SECONDS)
        return _router_client


def _retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    value = response.headers.get("retry-after")
    try:
        return min(float(value), RETRY_AFTER_CAP_SECONDS) if value else None
    except ValueError:
        return None


def _rate_headers(headers) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower().startswith("x-ratelimit")}


# --- the call ----------------------------------------------------------------


def _create(role: str, model: str, messages: list[dict], max_tokens: int, seed: int | None, client: OpenAI | None = None):
    settings = ROLE_SETTINGS.get(role, DEFAULT_SETTINGS)
    kwargs = dict(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=settings.temperature,
        top_p=settings.top_p,
        presence_penalty=settings.presence_penalty,
        extra_body={"chat_template_kwargs": {"enable_thinking": settings.thinking}},
    )
    if seed is not None:
        kwargs["seed"] = seed
    return (client or _get_client()).chat.completions.with_raw_response.create(**kwargs)


def _attempt(role: str, model: str, messages: list[dict], max_tokens: int, seed: int | None, client: OpenAI | None = None, retry: bool = True):
    """One paced request with backoff on transient errors. Returns (raw_response, attempts)."""
    for attempt, delay in enumerate([*config.RETRY_BACKOFF_SECONDS, None], start=1):
        if _pacer is not None:
            _pacer.wait(model)
        try:
            with _gate.slot(model):
                return _create(role, model, messages, max_tokens, seed, client), attempt
        except RETRYABLE as exc:
            if delay is None or not retry:
                raise LLMError(f"{role}/{model}: gave up after {attempt} attempts: {type(exc).__name__}") from exc
            sleep_for = _retry_after(exc) or (delay + random.uniform(0, JITTER_SECONDS))
            events.emit("llm_retry", role=role, model=model, attempt=attempt, error=type(exc).__name__, sleep_s=round(sleep_for, 2))
            time.sleep(sleep_for)
    raise AssertionError("unreachable")


def _complete(
    role: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    seed: int | None,
    client: OpenAI | None = None,
    retry: bool = True,
    via_router: bool = False,
) -> LLMResponse:
    """Call a model and return content plus metadata. Logs an `llm_call` event (never the key)."""
    started = time.perf_counter()
    raw, attempts = _attempt(role, model, messages, max_tokens, seed, client, retry)
    completion = raw.parse()
    message = completion.choices[0].message.model_dump()
    content = (message.get("content") or "").strip()
    finish_reason = completion.choices[0].finish_reason or ""
    total_attempts = attempts

    if not content:  # §7.2: a reasoning phase ate the budget; retry once with more room
        events.emit("llm_empty_content", role=role, model=model, finish_reason=finish_reason, max_tokens=max_tokens)
        raw, attempts = _attempt(role, model, messages, max(config.RETRY_MAX_TOKENS, 2 * max_tokens), seed, client, retry)
        completion = raw.parse()
        message = completion.choices[0].message.model_dump()
        content = (message.get("content") or "").strip()
        finish_reason = completion.choices[0].finish_reason or ""
        total_attempts += attempts

    usage = completion.usage
    details = getattr(usage, "prompt_tokens_details", None) if usage else None
    cached = getattr(details, "cached_tokens", None) or 0
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    response = LLMResponse(
        content=content,
        model=model,
        served_by=completion.model or model,
        latency_s=round(time.perf_counter() - started, 3),
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        cached_tokens=cached,
        finish_reason=finish_reason,
        attempts=total_attempts,
        reasoning_chars=len(reasoning),
    )
    events.emit(
        "llm_call",
        role=role,
        model=model,
        served_by=response.served_by,
        latency_s=response.latency_s,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        cached_tokens=response.cached_tokens,
        finish_reason=response.finish_reason,
        attempts=response.attempts,
        via_router=via_router,
        rate=_rate_headers(raw.headers),
    )
    return response


def chat_full(
    role: str,
    model: str,
    messages: list[dict],
    max_tokens: int = config.DEFAULT_MAX_TOKENS,
    seed: int | None = None,
) -> LLMResponse:
    """Call a model. With the Switchyard router on, negotiator calls go to the proxy as model
    "negotiator" (§7.1); if the proxy is down or errors, fall back to direct Nano and log it."""
    if role == "negotiator" and _router_base_url:
        try:
            return _complete(role, config.SWITCHYARD_MODEL, messages, max_tokens, seed, _get_router_client(), retry=False, via_router=True)
        except Exception as exc:  # never crash the demo over the router
            events.emit("router_fallback", error=f"{type(exc).__name__}: {str(exc)[:200]}")
    return _complete(role, model, messages, max_tokens, seed)


def chat(
    role: str,
    model: str,
    messages: list[dict],
    max_tokens: int = config.DEFAULT_MAX_TOKENS,
    seed: int | None = None,
) -> str:
    return chat_full(role, model, messages, max_tokens, seed).content


# --- JSON helpers ------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict | None:
    """Return the first balanced {...} block in `text` that parses as a JSON object, else None."""
    if not text:
        return None
    fenced = _FENCE.search(text)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text)
    for candidate in candidates:
        block = _first_balanced_object(candidate)
        if block is None:
            continue
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth, in_string, escaped = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]  # unbalanced; let json.loads reject it


def chat_json(
    role: str,
    model: str,
    messages: list[dict],
    max_tokens: int = config.DEFAULT_MAX_TOKENS,
    seed: int | None = None,
) -> tuple[dict | None, LLMResponse]:
    """Ask for JSON; on a parse failure retry once with 'Return valid JSON only.' (CLAUDE.md conventions)."""
    response = chat_full(role, model, messages, max_tokens, seed)
    parsed = extract_json(response.content)
    if parsed is not None:
        return parsed, response
    events.emit("json_parse_failed", role=role, model=model, attempt=1)
    retry_messages = [
        *messages,
        {"role": "assistant", "content": response.content or "(empty)"},
        {"role": "user", "content": "Return valid JSON only."},
    ]
    response = chat_full(role, model, retry_messages, max_tokens, seed)
    parsed = extract_json(response.content)
    if parsed is None:
        events.emit("json_parse_failed", role=role, model=model, attempt=2)
    return parsed, response
