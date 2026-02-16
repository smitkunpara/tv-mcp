"""
Domain service modules.

Each module encapsulates a single domain concern and exposes functions
that accept validated inputs and return standardized internal contracts.

Modules:
    historical  – OHLCV + indicator data fetching
    technicals  – all-indicators snapshot
    news        – headlines and article content
    ideas       – community trading ideas
    minds       – community discussions
    options     – option chain fetching and analytics
"""

from .historical import fetch_historical_data
from .technicals import fetch_all_indicators
from .news import fetch_news_headlines, fetch_news_content
from .ideas import fetch_ideas
from .minds import fetch_minds
from .options import (
    fetch_option_chain_data,
    get_current_spot_price,
    process_option_chain_with_analysis,
)

__all__ = [
    "fetch_historical_data",
    "fetch_all_indicators",
    "fetch_news_headlines",
    "fetch_news_content",
    "fetch_ideas",
    "fetch_minds",
    "fetch_option_chain_data",
    "get_current_spot_price",
    "process_option_chain_with_analysis",
]
