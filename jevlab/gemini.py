"""Optional LLM baseline. Used only when GEMINI_API_KEY is set."""
import json
import time
import urllib.error
import urllib.request

from . import env


def available() -> bool:
    return bool(env.get("GEMINI_API_KEY"))


def model() -> str:
    return env.get("GEMINI_MODEL", "gemini-3.7-flash")


def ask(prompt: str, schema: dict, retries: int = 5) -> tuple[dict | None, float, dict]:
    """Return (parsed JSON or None, latency in ms, usage metadata)."""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model()}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": env.get("GEMINI_API_KEY")},
    )
    started = time.perf_counter()
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text), (time.perf_counter() - started) * 1000, payload.get("usageMetadata", {})
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 503):
                time.sleep(3 * (attempt + 1))
                continue
            return None, 0.0, {"error": f"HTTP {error.code}"}
        except Exception:  # malformed JSON, timeout: try again
            time.sleep(2)
    return None, 0.0, {"error": "retries exhausted"}


def count_tokens(text: str) -> int:
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model()}:countTokens",
        data=json.dumps({"contents": [{"parts": [{"text": text}]}]}).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": env.get("GEMINI_API_KEY")},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())["totalTokens"]
