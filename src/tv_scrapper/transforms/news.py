"""
News content transformation utilities.
"""

from typing import Any, Dict

from bs4 import Tag
from bs4.element import NavigableString


def clean_for_json(obj: Any) -> Any:
    """Convert BeautifulSoup objects to JSON-serializable format."""
    if isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: clean_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, (Tag, NavigableString)):
        return str(obj)
    return obj


def extract_news_body(content: Dict) -> str:
    """Extract text body from news content dictionary.

    Args:
        content: News content dict with an optional ``body`` list.

    Returns:
        Extracted text body as a single string.
    """
    body = ""
    for data in content.get("body", []):
        if data.get("type") == "text":
            body += data.get("content", "") + "\n"
    return body.strip()
