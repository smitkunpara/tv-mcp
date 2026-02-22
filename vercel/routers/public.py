"""
Public routes — no authentication required.

Includes health check, root info, and privacy policy endpoints.
"""

from fastapi import APIRouter

from ..config import get_public_url
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> dict:
    """Health check endpoint — no authentication required."""
    return {"status": "healthy", "service": "TradingView HTTP API"}


@router.get("/privacy-policy", include_in_schema=False)
async def get_privacy_policy() -> dict:
    """Privacy Policy endpoint."""
    return {
        "privacy_policy": """
        Privacy Policy for TradingView HTTP API Server

        This application and its associated API are created solely for learning and improving purposes. All data, tools, and information provided through this service are intended for educational use only.

        Important Disclaimer:
        This is not financial advice. The data and tools provided by this API should not be used as the basis for any financial decisions, investments, or trading activities. Users are responsible for their own financial decisions and should consult with qualified financial advisors before making any investment choices.

        Data Collection and Usage:
        - This API scrapes publicly available data from TradingView.
        - No personal user data is collected or stored by this service.
        - Authentication is handled via TradingView cookies, which are not stored on our servers.

        Liability:
        The creators and maintainers of this API are not liable for any losses, damages, or consequences arising from the use of this service or the data it provides.

        For any questions or concerns, please contact the repository owner.
        """
    }


@router.get("/", include_in_schema=False)
async def root() -> dict:
    """Root endpoint providing API information."""
    return {
        "message": "TradingView HTTP API Server",
        "version": "1.0.0",
        "servers": [
            {"url": get_public_url()}
        ],
        "endpoints": [
            "/historical-data",
            "/news-headlines",
            "/news-content",
            "/all-indicators",
            "/ideas",
            "/option-chain-greeks",
            "/nse-option-chain-oi",
            "/paper-trading/place-order",
            "/paper-trading/close-position",
            "/paper-trading/view-positions",
            "/paper-trading/show-capital",
            "/paper-trading/set-alert",
            "/paper-trading/alert-manager",
            "/paper-trading/view-alerts",
            "/paper-trading/remove-alert",
            "/privacy-policy",
        ],
    }
