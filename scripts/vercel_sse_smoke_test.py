#!/usr/bin/env python3
"""Simple smoke test for deployed SSE MCP server on Vercel."""

from __future__ import annotations

import argparse
import os
import sys

import requests


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _check_health(base_url: str) -> None:
    resp = requests.get(f"{base_url}/health", timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Health check failed with status {resp.status_code}: {resp.text}")

    body = resp.json()
    if body.get("status") != "healthy":
        raise RuntimeError(f"Health response is not healthy: {body}")

    print(f"[ok] /health -> {resp.status_code}")


def _check_unauth_sse(base_url: str) -> None:
    with requests.get(
        f"{base_url}/sse/",
        allow_redirects=True,
        stream=True,
        timeout=(10, 20),
    ) as resp:
        status = resp.status_code

    if status not in (403, 503):
        raise RuntimeError(f"Expected unauthenticated /sse/ to return 403/503, got {status}")

    print(f"[ok] /sse/ without key -> {status}")


def _check_auth_sse(base_url: str, client_key: str) -> None:
    headers = {"X-Client-Key": client_key}

    with requests.get(
        f"{base_url}/sse/",
        headers=headers,
        allow_redirects=True,
        stream=True,
        timeout=(10, 20),
    ) as resp:
        status = resp.status_code

    if status != 200:
        raise RuntimeError(f"Expected authenticated /sse/ to return 200, got {status}")

    print(f"[ok] /sse/ with key -> {status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test a deployed Vercel SSE MCP endpoint")
    parser.add_argument(
        "--url",
        default=os.getenv("SSE_BASE_URL", "https://tradingview-mcp.vercel.app"),
        help="Base URL of deployed service",
    )
    parser.add_argument(
        "--client-key",
        default=os.getenv("TV_CLIENT_KEY", ""),
        help="Client API key for authenticated SSE check",
    )
    args = parser.parse_args()

    base_url = _normalize_url(args.url)

    try:
        _check_health(base_url)
        _check_unauth_sse(base_url)

        if args.client_key:
            _check_auth_sse(base_url, args.client_key)
        else:
            print("[skip] Authenticated SSE check skipped (no client key provided)")

        print("Smoke test passed.")
        return 0

    except Exception as exc:  # pragma: no cover
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
