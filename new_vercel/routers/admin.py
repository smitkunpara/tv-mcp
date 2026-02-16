"""
Admin-authenticated route — cookie update endpoint.

Uses ``verify_admin`` for auth and verifies cookies by calling
``fetch_ideas`` before committing the update.
"""

from fastapi import APIRouter, Depends

from src.tv_mcp.services.ideas import fetch_ideas
from src.tv_mcp.core.settings import settings

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
            return {"success": False, "message": "No cookies provided in payload"}

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
            test_result = fetch_ideas("BTCUSD", startPage=1, endPage=1, cookie=new_cookie_string)

            if isinstance(test_result, dict) and test_result.get("success") is False:
                raise ValueError("Validation request returned failure.")

            print("✅ Cookie Verification Successful!")
            settings.update_cookie(new_cookie_string)
            return {
                "success": True,
                "message": "Cookies verified and updated successfully.",
                "count": len(cookie_parts),
            }

        except Exception as e:
            print(f"❌ Verification Failed: {str(e)}")
            return {
                "success": False,
                "message": f"Cookie validation failed: {str(e)}. Reverted to previous session.",
            }

    except Exception as e:
        return {"success": False, "message": f"Server error processing cookies: {str(e)}"}
