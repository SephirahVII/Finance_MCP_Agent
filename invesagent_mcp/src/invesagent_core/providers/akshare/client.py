from __future__ import annotations


def get_client():
    """Import and return the AKShare module lazily."""
    try:
        import akshare as ak
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'akshare' package is not installed. Install it with: pip install akshare"
        ) from exc

    return ak

