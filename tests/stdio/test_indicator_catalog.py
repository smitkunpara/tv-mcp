"""
Tests for dynamic indicator catalog loading and mapping behavior.
"""

import types

from src.tv_mcp.core import validators


def _reset_indicator_cache() -> None:
    validators._INDICATOR_MAPPING_CACHE = None
    validators._INDICATOR_NAMES_CACHE = None


def test_fetch_live_indicator_mapping_adds_short_aliases(monkeypatch):
    def fake_import_module(name: str):
        if name != "tv_scraper.streaming.utils":
            raise ImportError(name)

        def fetch_available_indicators():
            return {
                "status": "success",
                "data": [
                    {
                        "name": "Relative Strength Index",
                        "id": "STD;RSI",
                        "version": "99.0",
                    },
                ],
            }

        return types.SimpleNamespace(fetch_available_indicators=fetch_available_indicators)

    monkeypatch.setattr(validators.importlib, "import_module", fake_import_module)

    mapping, names = validators._fetch_live_indicator_mapping()

    assert mapping["RELATIVE STRENGTH INDEX"] == ("STD;RSI", "99.0")
    assert mapping["RSI"] == ("STD;RSI", "99.0")
    assert names["RSI"] == "RSI"


def test_get_valid_indicator_mapping_fallback_on_failure(monkeypatch):
    _reset_indicator_cache()

    def fail_fetch():
        raise RuntimeError("fetch failed")

    monkeypatch.setattr(validators, "_fetch_live_indicator_mapping", fail_fetch)

    mapping = validators.get_valid_indicator_mapping(force_refresh=True)

    assert "RSI" in mapping
    assert mapping["RSI"][0] == "STD;RSI"


def test_validate_indicators_uses_dynamic_mapping(monkeypatch):
    _reset_indicator_cache()

    monkeypatch.setattr(
        validators,
        "get_valid_indicator_mapping",
        lambda force_refresh=False: {
            "RSI": ("STD;RSI", "44.0"),
            "CUSTOM": ("CUSTOM;IND", "1.0"),
        },
    )
    monkeypatch.setattr(
        validators,
        "get_valid_indicators",
        lambda force_refresh=False: ["RSI", "CUSTOM"],
    )

    ids, versions, errors, warnings = validators.validate_indicators(
        ["RSI", "custom", "unknown"]
    )

    assert ids == ["STD;RSI", "CUSTOM;IND"]
    assert versions == ["44.0", "1.0"]
    assert len(errors) == 1
    assert "unknown" in errors[0]
    assert warnings == []
