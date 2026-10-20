"""DeepSeek adapter for the shared Provider interface.

Ported from Devansh/progress/code/lib.py. Key: DEEPSEEK_API_KEY (Bearer header).
Both DeepSeek models are reasoning models: max_tokens covers reasoning plus visible content,
so an empty reply with finish_reason "length" is retried with a doubled budget.
Model ids: deepseek-flash (DeepSeek-V4.1-Flash), deepseek-v4-pro (DeepSeek-V4-Pro).
"""
import os

import requests

from providers.base import Provider, Usage

API_URL = "https://api.deepseek.com/chat/completions"


class DeepSeekProvider(Provider):
    name = "deepseek"

    def __init__(self, reasoning_effort="low"):
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise SystemExit("DEEPSEEK_API_KEY is not set")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        self.session.mount("https://", requests.adapters.HTTPAdapter(pool_connections=32, pool_maxsize=32))
        self.reasoning_effort = reasoning_effort
        self.usage = Usage()

    def chat(self, messages, model, temperature=0.0, max_tokens=None, json_mode=False, retries=5):
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens or self.default_max_tokens}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        last = None
        for attempt in range(retries):
            try:
                r = self.session.post(API_URL, json=payload, timeout=240)
            except requests.RequestException as e:
                last = repr(e)
                self._backoff(attempt)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                self._backoff(attempt)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"DeepSeek HTTP {r.status_code}: {r.text[:400]}")
            data = r.json()
            choice = data["choices"][0]
            text = (choice["message"].get("content") or "").strip()
            u = data.get("usage") or {}
            self.usage.add(u.get("prompt_tokens"), u.get("completion_tokens"))
            if not text and choice.get("finish_reason") == "length" and attempt < retries - 1:
                payload["max_tokens"] = int(payload["max_tokens"] * 2)
                last = "empty content: token budget consumed by reasoning"
                continue
            return text, {"provider": self.name, "model": model,
                          "model_version": data.get("model", model), "temperature": temperature,
                          "finish_reason": choice.get("finish_reason"), "usage": u}
        raise RuntimeError(f"DeepSeek chat failed after {retries} attempts: {last}")


PROVIDER_CLASS = DeepSeekProvider
