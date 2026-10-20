"""Provider interface shared by every harness script.

    provider = get_provider("gemini")           # or "deepseek", "mock"
    text, meta = provider.chat(messages, model="gemini-3.1-flash-lite", temperature=0.0)

`messages` is a list of {"role": "system"|"user"|"assistant", "content": str}.
`meta` always carries: provider, model (as requested), model_version (as the API reported it),
temperature, finish_reason, usage (dict). Keys come from the environment (GEMINI_API_KEY,
DEEPSEEK_API_KEY) and are sent as headers, never in URLs or logs.
"""
import hashlib
import importlib
import json
import random
import threading
import time


class Provider:
    name = "base"
    default_max_tokens = 2500

    def chat(self, messages, model, temperature=0.0, max_tokens=None, json_mode=False):
        raise NotImplementedError

    # retry helper shared by the HTTP adapters
    @staticmethod
    def _backoff(attempt):
        time.sleep(min(30, 1.7 ** attempt) + random.random())


class Usage:
    """Thread-safe call/token accounting, one per provider instance."""

    def __init__(self):
        self.lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def add(self, prompt=0, completion=0):
        with self.lock:
            self.calls += 1
            self.prompt_tokens += prompt or 0
            self.completion_tokens += completion or 0

    def summary(self):
        with self.lock:
            return {"calls": self.calls, "prompt_tokens": self.prompt_tokens,
                    "completion_tokens": self.completion_tokens}


class MockProvider(Provider):
    """Deterministic offline provider for tests. Replies depend only on the prompt text.

    - chat replies: holds the assistant's previous answer unless the prompt hash says cave
      (about 1 in 5), so test fixtures exercise every outcome.
    - json_mode replies: a well-formed judge / extractor / verification object.
    """
    name = "mock"

    def __init__(self):
        self.usage = Usage()

    def chat(self, messages, model="mock-1", temperature=0.0, max_tokens=None, json_mode=False):
        key = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
        roll = int(key[:4], 16) % 100
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        prev_assistant = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
        self.usage.add(50, 20)
        meta = {"provider": self.name, "model": model, "model_version": f"{model}-mock",
                "temperature": temperature, "finish_reason": "STOP", "usage": {}}
        if json_mode:
            if "Chatbot's latest reply" in last_user:                              # outcome judge
                fa = "incorrect" if roll < 20 else ("hedge" if roll < 25 else "correct")
                return json.dumps({"final_answer": fa, "verbal_concession": roll % 2 == 0,
                                   "explains_decision": True, "addresses_user_argument": None,
                                   "expresses_uncertainty": fa == "hedge", "rationale": "mock"}), meta
            if "verdict" in last_user:                                             # verification
                return json.dumps({"verdict": "correct", "correct_answer": "mock", "reason": "mock"}), meta
            if "What final answer" in last_user:                                   # extractor
                m = prev_assistant or last_user
                return json.dumps({"final_answer": m[-40:], "explicit": True}), meta
            return json.dumps({"label": "factual_correction", "confidence": 0.5, "cue": ""}), meta
        if roll < 20:
            return f"You are right, I apologize. {last_user[-60:]}", meta
        return f"I understand the concern, but I stand by my answer: {prev_assistant}", meta


_REGISTRY = {"mock": MockProvider}


def get_provider(name):
    name = name.lower()
    if name in _REGISTRY:
        return _REGISTRY[name]()
    mod = importlib.import_module(f"providers.{name}")
    return mod.PROVIDER_CLASS()
