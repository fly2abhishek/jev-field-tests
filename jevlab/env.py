"""Read settings from the process environment, then from a local .env file."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _dotenv() -> dict:
    path = ROOT / ".env"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


_FILE = _dotenv()


def get(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name) or _FILE.get(name) or default
