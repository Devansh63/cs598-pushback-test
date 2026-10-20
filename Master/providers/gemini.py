"""Gemini adapter (Google AI Studio REST API) for the shared Provider interface.

Key: GEMINI_API_KEY, sent as the x-goog-api-key header. Uses `requests`.
Notes from the pilots: gemini-2.5-* is closed to new API keys; the free tier allows 20
requests per model per day, so runs need a billed (prepaid) project.
"""
import os

import requests

from providers.base import Provider, Usage

BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self):
        self.key = os.environ.get("GEMINI_API_KEY")
        if not self.key:
            raise SystemExit("GEMINI_API_KEY is not set")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "x-goog-api-key": self.key})
        self.usage = Usage()

    def chat(self, messages, model, temperature=0.0, max_tokens=None, json_mode=False, retries=6):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system") or None
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                    for m in messages if m["role"] != "system"]
        config = {"temperature": temperature}
        if max_tokens or self.default_max_tokens:
            config["maxOutputTokens"] = max_tokens or self.default_max_tokens
        if json_mode:
            config["responseMimeType"] = "application/json"
        body = {"contents": contents, "generationConfig": config}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        last = None
        for attempt in range(retries):
            try:
                r = self.session.post(f"{BASE}/models/{model}:generateContent", json=body, timeout=180)
            except requests.RequestException as e:
                last = repr(e)
                self._backoff(attempt)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                self._backoff(attempt)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:400]}")
            out = r.json()
            cand = (out.get("candidates") or [{}])[0]
            parts = cand.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            u = out.get("usageMetadata", {})
            self.usage.add(u.get("promptTokenCount"), u.get("candidatesTokenCount"))
            if not text and cand.get("finishReason") == "MAX_TOKENS" and attempt < retries - 1:
                config["maxOutputTokens"] = int(config["maxOutputTokens"] * 2)
                last = "empty content: token budget consumed"
                continue
            return text, {"provider": self.name, "model": model,
                          "model_version": out.get("modelVersion", model),
                          "temperature": temperature, "finish_reason": cand.get("finishReason"),
                          "usage": u}
        raise RuntimeError(f"Gemini chat failed after {retries} attempts: {last}")


PROVIDER_CLASS = GeminiProvider
