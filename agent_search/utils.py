from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return "unknown"
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def round_safe(value: float | None, ndigits: int = 4) -> float | None:
    if value is None:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return round(value, ndigits)


def sanitize_filename(text: str, max_len: int = 32) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", "", text).strip()
    if not cleaned:
        cleaned = "report"
    return cleaned[:max_len]
