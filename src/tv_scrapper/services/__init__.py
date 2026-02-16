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
