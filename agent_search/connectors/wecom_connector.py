from __future__ import annotations

import time
from typing import Any

import requests


class WecomConnector:
    def __init__(
        self,
        webhook_url: str | None,
        timeout: int = 10,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def send_text(self, content: str, mentioned_list: list[str] | None = None) -> dict[str, Any]:
        if not self.webhook_url:
            return {"ok": False, "error": "missing webhook"}

        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentioned_list or [],
            },
        }

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if int(data.get("errcode", -1)) == 0:
                    return {"ok": True, "data": data, "attempt": attempt}
                last_err = RuntimeError(f"wecom errcode={data.get('errcode')} errmsg={data.get('errmsg')}")
            except Exception as err:  # noqa: BLE001
                last_err = err

            if attempt < self.max_retries:
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))

        return {"ok": False, "error": str(last_err) if last_err else "unknown error"}
