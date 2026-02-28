import requests

from agent_search.connectors.wecom_connector import WecomConnector


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_wecom_retry(monkeypatch) -> None:
    attempts = {"count": 0}

    def _fake_post(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise requests.ConnectionError("network")
        return _FakeResp({"errcode": 0, "errmsg": "ok"})

    monkeypatch.setattr(requests, "post", _fake_post)

    connector = WecomConnector(
        webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=demo",
        max_retries=3,
        backoff_seconds=0,
    )
    result = connector.send_text("hello")
    assert result["ok"] is True
    assert attempts["count"] == 2
