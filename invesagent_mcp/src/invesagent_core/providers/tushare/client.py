from __future__ import annotations

from functools import lru_cache

from invesagent_core.config.settings import settings


class TushareTokenMissingError(RuntimeError):
    """Raised when TUSHARE_TOKEN is not configured."""


@lru_cache(maxsize=1)
def get_client():
    """Create and cache a Tushare Pro client."""
    if not settings.tushare_token:
        raise TushareTokenMissingError(
            "TUSHARE_TOKEN is not configured. Please copy .env.example to .env "
            "and fill in your Tushare token."
        )

    try:
        import tushare as ts
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'tushare' package is not installed. Install it with: pip install tushare"
        ) from exc

    return ts.pro_api(settings.tushare_token)
