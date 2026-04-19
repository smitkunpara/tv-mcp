"""
Admin-authenticated route — cookie update endpoint.

Uses ``verify_admin`` for auth and verifies cookies by calling
``fetch_ideas`` before committing the update.
"""

from fastapi import APIRouter, Depends, HTTPException
from tv_mcp.services.ideas import fetch_ideas
from tv_mcp.core.settings import settings

from ..auth import verify_admin

router = APIRouter()


@router.post("/update-cookies", include_in_schema=False, dependencies=[Depends(verify_admin)])
async def update_cookies(request: dict) -> dict:
    """
    Receives raw cookies from extension, validates them, and updates server config.
    """
    try:
        raw_cookies = request.get("cookies", [])
        source = request.get("source", "unknown")

        if not raw_cookies:
            raise HTTPException(status_code=400, detail="No cookies provided in payload")

        print(f"📥 Received {len(raw_cookies)} cookies from {source}")

        # 1. CONSTRUCT COOKIE STRING
        cookie_parts: list[str] = []
        for c in raw_cookies:
            name = c.get("name")
            value = c.get("value")
            if name and value:
                cookie_parts.append(f"{name}={value}")

        new_cookie_string = "; ".join(cookie_parts)
        print("🕵️ Verifying new session...")

        try:
            test_result = fetch_ideas(symbol="BTCUSD", exchange="BITSTAMP", startPage=1, endPage=1, cookie=new_cookie_string)

            if isinstance(test_result, dict) and test_result.get("success") is False:
                raise ValueError(test_result.get("message", "Validation request returned failure."))

            print("✅ Cookie Verification Successful!")
            settings.update_cookie(new_cookie_string)
            return {
                "success": True,
                "message": "Cookies verified and updated successfully.",
                "count": len(cookie_parts),
            }

        except Exception as e:
            print(f"❌ Verification Failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Cookie validation failed: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error processing cookies: {str(e)}")
