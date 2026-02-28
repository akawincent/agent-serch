"""A-share trading research agent package."""

from .config import AppConfig, load_config
from .engine import TradingResearchAgent

__all__ = ["AppConfig", "TradingResearchAgent", "load_config"]
