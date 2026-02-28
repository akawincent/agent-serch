from __future__ import annotations

import csv
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScheduleConfig(BaseModel):
    pre_open: str = "09:05"
    intraday_every_minutes: int = 30
    post_close: str = "15:10"


class RiskConfig(BaseModel):
    max_drawdown_limit: float = 0.15
    risk_per_trade: float = 0.01
    atr_stop_multiple: float = 1.5


class SignalConfig(BaseModel):
    technical_weight: float = 0.7
    news_weight: float = 0.3
    buy_threshold: float = 4.0
    reduce_threshold: float = 1.0


class IntegrationsConfig(BaseModel):
    serper_api_key_env: str = "SERPER_API_KEY"
    openai_api_key_env: str = "OPENAI_API_KEY"
    wecom_webhook_env: str = "WECOM_WEBHOOK_URL"


class StorageConfig(BaseModel):
    db_path: str = "data/agent_search.db"


class ModelConfig(BaseModel):
    base_url: str = "https://right.codes/codex/v1"
    model: str = "gpt-5.2"
    max_rounds: int = 10


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timezone: str = "Asia/Shanghai"
    universe_file: str = "config/watchlist.csv"
    results_dir: str = "results"
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    signal: SignalConfig = Field(default_factory=SignalConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    llm: ModelConfig = Field(default_factory=ModelConfig)

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("timezone cannot be empty")
        return value


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path or "config/config.yaml")
    if not config_path.exists():
        return AppConfig()
    raw = config_path.read_text(encoding="utf-8")
    payload = _load_yaml_payload(raw)
    return AppConfig.model_validate(payload)


def load_watchlist(universe_file: str | Path) -> list[str]:
    csv_path = Path(universe_file)
    if not csv_path.exists():
        return []

    symbols: list[str] = []
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if "symbol" in reader.fieldnames if reader.fieldnames else []:
            for row in reader:
                symbol = (row.get("symbol") or "").strip()
                if symbol:
                    symbols.append(symbol)
        else:
            handle.seek(0)
            for line in handle:
                symbol = line.strip().split(",")[0]
                if symbol and symbol.lower() != "symbol":
                    symbols.append(symbol)

    deduped: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        if symbol not in seen:
            seen.add(symbol)
            deduped.append(symbol)
    return deduped


def _load_yaml_payload(raw: str) -> dict:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(raw) or {}
    except Exception:
        return _simple_yaml_parse(raw)


def _coerce_scalar(value: str):
    text = value.strip()
    if not text:
        return ""
    if text.startswith(("'", '"')) and text.endswith(("'", '"')) and len(text) >= 2:
        return text[1:-1]
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _simple_yaml_parse(raw: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(0, root)]

    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if value == "":
            node: dict = {}
            parent[key] = node
            stack.append((indent + 2, node))
        else:
            parent[key] = _coerce_scalar(value)

    return root
