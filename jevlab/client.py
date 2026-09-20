"""A minimal Jev client: one POST, retries on 429/5xx, latency measured around the call."""
import json
import time
import urllib.error
import urllib.request

from . import env

URL = "https://api.typesafe.ai/v1/systemone"
# Pinned on purpose. `jev-latest` moves when TypeSafe ships a new version.
DEFAULT_MODEL = "jev-1.13.0"


class JevError(RuntimeError):
    pass


def api_key() -> str:
    key = env.get("TYPESAFE_API_KEY") or env.get("JEV_API_KEY")
    if not key:
        raise SystemExit(
            "No API key. Copy .env.example to .env and set TYPESAFE_API_KEY, "
            "or export it in your shell."
        )
    return key


def model() -> str:
    return env.get("JEV_MODEL", DEFAULT_MODEL)


def ask(state, questions: dict, retries: int = 4) -> tuple[dict, float]:
    """Return (response, latency in ms). Raises JevError on a non-retryable failure."""
    body = json.dumps({"state": state, "model": model(), "questions": questions}).encode()
    request = urllib.request.Request(
        URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "jev-field-tests/1.0",
        },
    )
    last = "no attempt made"
    for attempt in range(retries):
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read())
            return payload, (time.perf_counter() - started) * 1000
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            last = f"HTTP {error.code}: {detail}"
            if error.code in (429, 500, 502, 503, 529):
                time.sleep(2 * (attempt + 1))
                continue
            raise JevError(last) from None
        except (urllib.error.URLError, TimeoutError) as error:
            last = str(error)
            time.sleep(2 * (attempt + 1))
    raise JevError(last)


def value(answer: dict) -> float:
    """One comparable number per answer: the probability, the score, or the winning option's probability."""
    if answer["type"] == "noul":
        return answer["noul"]
    if answer["type"] == "score":
        return answer["score"]
    return answer["probabilities"][answer["choice"]]
