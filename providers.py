"""Free-tier LLM provider clients, standard library only.

Keys come from the GROQ_API_KEY / GEMINI_API_KEY environment variables at call
time. They are never written to traces, logs, or the repo. The disk cache is
keyed by a SHA-256 hash that mixes in the key, so a cache entry cannot be
read without the key and never contains it.

Both accounts are on free plans with billing disabled. This module therefore
reports cost as exactly 0 and refuses models outside the free allowlist; it
cannot and does not estimate prices. Staying free is a hard requirement.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Free-plan limits observed on this account's own console pages on
# 2026-10-12. Groq limits are per organization; Gemini limits are per project
# and the daily quota resets at midnight Pacific. Conservative pacing below
# stays well under the minute limits.
FREE_MODELS = {
    "groq": {
        # console.groq.com/settings/limits: 30 RPM, 1K RPD, 8K TPM, 200K TPD
        "openai/gpt-oss-120b": {"rpm": 30, "rpd": 1000},
        "openai/gpt-oss-20b": {"rpm": 30, "rpd": 1000},
    },
    "gemini": {
        # aistudio.google.com/rate-limit: 15 RPM, 250K TPM, 500 RPD
        "gemini-3.5-flash-lite": {"rpm": 15, "rpd": 500},
        "gemini-3.1-flash-lite": {"rpm": 15, "rpd": 500},
        # 10 RPM, 250K TPM, 20 RPD
        "gemini-2.5-flash-lite": {"rpm": 10, "rpd": 20},
    },
}

# Minimum seconds between requests per provider. Chosen under the free RPM.
PACE_SECONDS = {"groq": 3.0, "gemini": 5.0}
MAX_ATTEMPTS = 6
_last_call = {}


class ProviderError(Exception):
    """Unrecoverable provider failure (bad key, quota exhausted, bad model)."""


class DailyQuotaExhausted(ProviderError):
    """The provider says the free daily quota is used up. Stop, don't spin."""


def _key(provider):
    env = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}[provider]
    value = os.environ.get(env, "").strip()
    if not value:
        raise ProviderError(f"{env} is not set; refusing to call {provider}")
    return value


def _pace(provider):
    wait = PACE_SECONDS[provider] - (time.monotonic() - _last_call.get(provider, 0))
    if wait > 0:
        time.sleep(wait)
    _last_call[provider] = time.monotonic()


def _post(url, headers, payload, provider):
    """POST with Retry-After-aware backoff. Returns (status, json, headers)."""
    body = json.dumps(payload).encode()
    for attempt in range(MAX_ATTEMPTS):
        _pace(provider)
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return resp.status, data, dict(resp.headers)
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:500].decode(errors="replace")
            if exc.code == 429 or exc.code >= 500:
                remaining = exc.headers.get("x-ratelimit-remaining-requests")
                if remaining == "0":
                    raise DailyQuotaExhausted(
                        f"{provider} free daily quota exhausted (RPD=0 remaining)")
                retry_after = exc.headers.get("retry-after")
                wait = float(retry_after) if retry_after else min(2 ** attempt * 5, 120)
                if attempt == MAX_ATTEMPTS - 1:
                    raise ProviderError(f"{provider} HTTP {exc.code} after retries: {detail}")
                time.sleep(wait)
                continue
            raise ProviderError(f"{provider} HTTP {exc.code}: {detail}")
        except urllib.error.URLError as exc:
            if attempt == MAX_ATTEMPTS - 1:
                raise ProviderError(f"{provider} connection failed: {exc.reason}")
            time.sleep(min(2 ** attempt * 5, 120))
    raise ProviderError("unreachable")


def _cache_path(cache_dir, provider, model, payload, api_key):
    material = json.dumps(
        {"provider": provider, "model": model, "payload": payload,
         "key": hashlib.sha256(api_key.encode()).hexdigest()},
        sort_keys=True, separators=(",", ":"))
    name = hashlib.sha256(material.encode()).hexdigest()
    return Path(cache_dir) / provider / (name + ".json")


def chat(provider, model, messages, tools, cache_dir=".cache/llm", use_cache=True):
    """One tool-capable chat call. Returns {content, tool_calls, usage, raw}.

    messages use the internal shape from agent.py; tool_calls come back as
    [{"id", "name", "arguments": dict}]. Raises ProviderError on failure.
    Free tier only: unknown models are refused before any network call.
    """
    if provider not in FREE_MODELS:
        raise ProviderError(f"unknown provider {provider!r}")
    if model not in FREE_MODELS[provider]:
        raise ProviderError(
            f"{model!r} is not on the verified free-model list for {provider}; "
            "add it to FREE_MODELS only after checking the console limits page")
    api_key = _key(provider)
    if provider == "groq":
        url, headers, payload, parse = _groq_request(model, messages, tools, api_key)
    else:
        url, headers, payload, parse = _gemini_request(model, messages, tools, api_key)
    path = _cache_path(cache_dir, provider, model, payload, api_key)
    if use_cache and path.exists():
        cached = json.loads(path.read_text())
        cached["cached"] = True
        return cached
    status, data, _headers = _post(url, headers, payload, provider)
    result = parse(data)
    result["cached"] = False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result))
    return result


def _groq_request(model, messages, tools, api_key):
    payload = {
        "model": model,
        "messages": [_groq_message(m) for m in messages],
        "tools": [{"type": "function", "function": t} for t in tools],
        "tool_choice": "auto",
    }
    headers = {"Authorization": "Bearer " + api_key,
               "Content-Type": "application/json"}

    def parse(data):
        choice = data["choices"][0]["message"]
        calls = [{"id": c["id"], "name": c["function"]["name"],
                  "arguments": json.loads(c["function"]["arguments"] or "{}")}
                 for c in choice.get("tool_calls") or []]
        return {"content": choice.get("content") or "",
                "tool_calls": calls, "usage": data.get("usage", {}),
                "raw": choice}
    return GROQ_URL, headers, payload, parse


def _groq_message(m):
    if m["role"] == "assistant" and m.get("tool_calls"):
        return {"role": "assistant", "content": m.get("content") or None,
                "tool_calls": [{"id": c["id"], "type": "function",
                                "function": {"name": c["name"],
                                             "arguments": json.dumps(c["arguments"])}}
                               for c in m["tool_calls"]]}
    if m["role"] == "tool":
        return {"role": "tool", "tool_call_id": m["tool_call_id"],
                "content": m["content"]}
    return {"role": m["role"], "content": m.get("content") or ""}


def _gemini_request(model, messages, tools, api_key):
    payload = {
        "contents": [_gemini_content(m) for m in messages],
        "tools": [{"functionDeclarations": [
            {"name": t["name"], "description": t["description"],
             "parameters": t["parameters"]} for t in tools]}],
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    def parse(data):
        content = data["candidates"][0]["content"]
        parts = content.get("parts", [])
        calls = [{"id": p["functionCall"].get("id") or f"call_{i}",
                  "name": p["functionCall"]["name"],
                  "arguments": p["functionCall"].get("args", {})}
                 for i, p in enumerate(parts) if "functionCall" in p]
        text = "".join(p.get("text", "") for p in parts)
        # Keep the raw model turn: Gemini 3.x thought signatures must be
        # replayed verbatim on the next request in the same loop.
        return {"content": text, "tool_calls": calls,
                "usage": data.get("usageMetadata", {}), "raw": content}
    return GEMINI_URL.format(model=model), headers, payload, parse


def _gemini_content(m):
    if m["role"] == "user":
        return {"role": "user", "parts": [{"text": m.get("content") or ""}]}
    if m["role"] == "assistant":
        raw = m.get("raw")
        if raw:  # replay exactly, preserving thought signatures
            return raw
        parts = [{"text": m["content"]}] if m.get("content") else []
        parts += [{"functionCall": {"name": c["name"], "args": c["arguments"],
                                    "id": c["id"]}}
                  for c in m.get("tool_calls", [])]
        return {"role": "model", "parts": parts}
    if m["role"] == "tool":
        return {"role": "user", "parts": [{"functionResponse": {
            "name": m["name"], "id": m["tool_call_id"],
            "response": {"result": m["content"]}}}]}
    raise ProviderError(f"cannot map role {m['role']!r} for gemini")
