from __future__ import annotations

from functools import lru_cache

from src.config.settings import settings


class TushareTokenMissingError(RuntimeError):
    """Raised when TUSHARE_TOKEN is not configured."""

@lru_cache(maxsize=1)
def get_tushare_client():
    """创建并缓存 Tushare Pro 客户端。

    输入：
        无。函数会从全局配置 settings 中读取 TUSHARE_TOKEN。

    输出：
        返回 tushare.pro_api(...) 创建的 Tushare Pro 客户端对象，可继续调用
        stock_basic、daily、income 等 Tushare Pro 接口。

    异常：
        如果未配置 TUSHARE_TOKEN，则抛出 TushareTokenMissingError。
        如果当前环境未安装 tushare 包，则抛出 RuntimeError。
    """
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
