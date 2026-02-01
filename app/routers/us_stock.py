"""美股行情路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.utils.us_stock import us_stock_api

router = APIRouter(prefix="/api/us", tags=["美股行情"])


@router.get("/quote/{symbol}", summary="获取美股行情")
async def get_us_quote(symbol: str):
    """
    获取单只美股实时行情
    symbol: 美股代码，如 AAPL, MSFT, GOOGL
    """
    quote = await us_stock_api.get_quote(symbol)

    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol}")

    return {
        "success": True,
        "data": quote
    }


@router.get("/quotes", summary="批量获取美股行情")
async def get_us_quotes(symbols: str = Query(..., description="股票代码，逗号分隔")):
    """
    批量获取美股行情
    symbols: 股票代码列表，逗号分隔，如 AAPL,MSFT,GOOGL
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

    if not symbol_list:
        raise HTTPException(status_code=400, detail="请提供股票代码")

    quotes = await us_stock_api.get_batch_quotes(symbol_list)

    return {
        "success": True,
        "data": quotes
    }


@router.get("/kline/{symbol}", summary="获取美股K线数据")
async def get_us_kline(
    symbol: str,
    days: int = Query(60, ge=1, le=365, description="获取天数")
):
    """
    获取美股历史K线数据
    """
    kline = await us_stock_api.get_kline_data(symbol, days=days)

    if not kline:
        raise HTTPException(status_code=400, detail=f"无法获取 {symbol} 的K线数据")

    return {
        "success": True,
        "data": {
            "symbol": symbol.upper(),
            "kline": kline
        }
    }


@router.get("/search", summary="搜索美股")
async def search_us_stock(q: str = Query(..., description="搜索关键词")):
    """
    搜索美股
    """
    results = await us_stock_api.search_stock(q)

    return {
        "success": True,
        "data": results
    }


@router.get("/indices", summary="获取美股指数")
async def get_us_indices():
    """
    获取美股主要指数行情
    包括：道琼斯、标普500、纳斯达克、罗素2000
    """
    indices = await us_stock_api.get_us_indices()

    return {
        "success": True,
        "data": indices
    }


@router.get("/china-adr", summary="获取中概股行情")
async def get_china_adr():
    """
    获取热门中概股行情
    包括：阿里巴巴、京东、拼多多、百度、蔚来等
    """
    stocks = await us_stock_api.get_china_adr()

    return {
        "success": True,
        "data": stocks
    }


@router.get("/popular", summary="获取热门美股")
async def get_popular_us_stocks():
    """
    获取热门美股行情
    包括：苹果、微软、谷歌、亚马逊、特斯拉等
    """
    stocks = await us_stock_api.get_popular_us_stocks()

    return {
        "success": True,
        "data": stocks
    }


@router.get("/overview", summary="美股市场概览")
async def get_us_market_overview():
    """
    获取美股市场概览
    包括：主要指数、中概股、热门股
    """
    import asyncio

    # 并行获取数据
    indices, china_adr, popular = await asyncio.gather(
        us_stock_api.get_us_indices(),
        us_stock_api.get_china_adr(),
        us_stock_api.get_popular_us_stocks(),
        return_exceptions=True
    )

    return {
        "success": True,
        "data": {
            "indices": indices if not isinstance(indices, Exception) else [],
            "china_adr": china_adr if not isinstance(china_adr, Exception) else [],
            "popular": popular if not isinstance(popular, Exception) else []
        }
    }
