"""Compatibility helpers for different tv_scraper API variants."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Iterable


def build_scraper(scraper_cls: type[Any], cookie: str | None = None) -> Any:
    """Create scraper instances across old/new tv_scraper constructor shapes."""
    params = inspect.signature(scraper_cls).parameters
    kwargs: dict[str, Any] = {}

    if "export" in params:
        kwargs["export"] = None
    elif "export_result" in params:
        kwargs["export_result"] = False

    if cookie and "cookie" in params:
        kwargs["cookie"] = cookie

    return scraper_cls(**kwargs)


def call_first_supported_method(
    obj: Any,
    method_names: Iterable[str],
    **kwargs: Any,
) -> Any:
    """Call the first method that exists, filtering kwargs by signature."""
    for method_name in method_names:
        method = getattr(obj, method_name, None)
        if callable(method):
            params = inspect.signature(method).parameters
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in params}
            return method(**filtered_kwargs)

    names = ", ".join(method_names)
    raise AttributeError(f"None of the methods are available: {names}")
