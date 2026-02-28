from __future__ import annotations

import time
from datetime import datetime
from zoneinfo import ZoneInfo

from agent_search.engine import TradingResearchAgent


class AgentScheduler:
    def __init__(self, agent: TradingResearchAgent, timezone: str = "Asia/Shanghai") -> None:
        self.agent = agent
        self.tz = ZoneInfo(timezone)
        self._last_run: dict[str, str] = {}

    @staticmethod
    def _hhmm(value: str) -> str:
        return value.strip()[:5]

    def _should_run_slot(self, slot_name: str, minute_key: str) -> bool:
        if self._last_run.get(slot_name) == minute_key:
            return False
        self._last_run[slot_name] = minute_key
        return True

    @staticmethod
    def _in_intraday_window(now: datetime) -> bool:
        hhmm = now.strftime("%H:%M")
        in_am = "09:30" <= hhmm <= "11:30"
        in_pm = "13:00" <= hhmm <= "15:00"
        return in_am or in_pm

    def run_forever(self, equity: float) -> None:
        pre_open = self._hhmm(self.agent.config.schedule.pre_open)
        post_close = self._hhmm(self.agent.config.schedule.post_close)
        interval = max(1, int(self.agent.config.schedule.intraday_every_minutes))

        while True:
            now = datetime.now(self.tz)
            hhmm = now.strftime("%H:%M")
            minute_key = now.strftime("%Y-%m-%d %H:%M")

            if hhmm == pre_open and self._should_run_slot("pre_open", minute_key):
                self.agent.run_once(equity=equity)

            if hhmm == post_close and self._should_run_slot("post_close", minute_key):
                self.agent.run_once(equity=equity)

            if self._in_intraday_window(now) and now.minute % interval == 0:
                if self._should_run_slot("intraday", minute_key):
                    self.agent.run_once(equity=equity)

            time.sleep(20)
