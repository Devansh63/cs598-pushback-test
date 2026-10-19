"""Minimal Gemini REST client (no SDK dependency).

Reads the key from GEMINI_API_KEY and sends it as a header, never in the URL.
"""
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://generativelanguage.googleapis.com/v1beta"


def _key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set. Run: export GEMINI_API_KEY=...")
    return key


def _request(method, path, body=None, retries=6):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{BASE}/{path}", data=data, method=method,
            headers={"Content-Type": "application/json", "x-goog-api-key": _key()},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(min(60, 2 ** attempt * 2))
                continue
            raise RuntimeError(f"Gemini HTTP {e.code}: {msg}") from None
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise


def list_models():
    out = _request("GET", "models?pageSize=200")
    return [m["name"].split("/", 1)[1] for m in out.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])]


def generate(model, turns, temperature=None, system=None, json_mode=False, max_tokens=None):
    """turns: list of (role, text) with role in {"user", "assistant"}.

    Returns dict with text, model_version, finish_reason, usage, and the config sent.
    """
    contents = [{"role": "model" if r == "assistant" else "user", "parts": [{"text": t}]}
                for r, t in turns]
    config = {}
    if temperature is not None:
        config["temperature"] = temperature
    if max_tokens is not None:
        config["maxOutputTokens"] = max_tokens
    if json_mode:
        config["responseMimeType"] = "application/json"
    body = {"contents": contents}
    if config:
        body["generationConfig"] = config
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    out = _request("POST", f"models/{model}:generateContent", body)
    cand = (out.get("candidates") or [{}])[0]
    parts = cand.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return {
        "text": text,
        "model_version": out.get("modelVersion", model),
        "finish_reason": cand.get("finishReason"),
        "usage": out.get("usageMetadata", {}),
        "config": config,
    }
