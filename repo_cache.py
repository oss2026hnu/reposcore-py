from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


CACHE_FILE = Path(".cache/reposcore_cache.json")
CACHE_TTL_SECONDS = 60 * 60


def read_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}

    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if not isinstance(cache, dict):
        return {}

    return cache


def write_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_cache_key(repository: str) -> str:
    return repository.lower()


def get_cached_repository_counts(repository: str) -> dict[str, Any] | None:
    cache = read_cache()
    cache_entry = cache.get(get_cache_key(repository))

    if not isinstance(cache_entry, dict):
        return None

    fetched_at = cache_entry.get("fetched_at")
    data = cache_entry.get("data")

    if not isinstance(fetched_at, (int, float)):
        return None

    if not isinstance(data, dict):
        return None

    if time.time() - fetched_at > CACHE_TTL_SECONDS:
        return None

    return data


def set_cached_repository_counts(repository: str, data: dict[str, Any]) -> None:
    cache = read_cache()
    cache[get_cache_key(repository)] = {
        "fetched_at": time.time(),
        "data": data,
    }
    write_cache(cache)
