"""Fetch small slices of public datasets from the Hugging Face datasets server, cached on disk."""
import json
import urllib.request

from .env import ROOT

CACHE = ROOT / ".cache"


def rows(dataset: str, split: str, offsets: list[int], length: int = 100, config: str = "default") -> list[dict]:
    CACHE.mkdir(exist_ok=True)
    out = []
    for offset in offsets:
        path = CACHE / f"{dataset.replace('/', '__')}-{split}-{offset}-{length}.json"
        if not path.exists():
            url = (
                "https://datasets-server.huggingface.co/rows"
                f"?dataset={dataset.replace('/', '%2F')}&config={config}&split={split}&offset={offset}&length={length}"
            )
            request = urllib.request.Request(url, headers={"User-Agent": "jev-field-tests/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                path.write_bytes(response.read())
        out += [r["row"] for r in json.loads(path.read_text())["rows"]]
    return out
