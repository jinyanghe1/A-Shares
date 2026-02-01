"""股票相关路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.models import (
    AddWatchRequest,
    WatchListItem,
    StockQuote,
    CapitalFlow,
    MarketSentiment,
    ApiResponse
)
from app.services.stock_service import stock_service
from app.services.trading_calendar import trading_calendar
from datetime import datetime

router = APIRouter(prefix="/api/stocks", tags=["股票"])


@router.get("/search", summary="搜索股票")
async def search_stock(keyword: str = Query(..., description="搜索关键词")):
    """
    根据关键词搜索股票
    """
    results = await stock_service.search_stock(keyword)
    return {"success": True, "data": results}


@router.get("/quote/{code}", summary="获取单只股票行情")
async def get_stock_quote(
    code: str,
    fallback: bool = Query(True, description="休市时是否返回历史数据")
):
    """
    获取单只股票的实时行情
    fallback=True时，休市时返回缓存的历史数据
    """
    if fallback:
        quote = await stock_service.get_quote_with_fallback(code)
    else:
        quote_obj = await stock_service.get_quote(code)
        quote = quote_obj.model_dump(mode="json") if quote_obj else None

    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    return {"success": True, "data": quote}


@router.get("/capital-flow/{code}", summary="获取个股资金流向")
async def get_capital_flow(code: str):
    """
    获取个股资金流向数据
    """
    flow = await stock_service.get_capital_flow(code)
    if not flow:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code} 的资金流向数据")
    return {"success": True, "data": flow.model_dump(mode="json")}


@router.get("/watch-list", summary="获取关注列表")
async def get_watch_list():
    """
    获取当前关注列表
    """
    watch_list = stock_service.get_watch_list()
    return {
        "success": True,
        "data": [item.model_dump(mode="json") for item in watch_list]
    }


@router.get("/watch-list/quotes", summary="获取关注列表行情")
async def get_watch_list_quotes():
    """
    获取关注列表中所有股票的实时行情
    """
    quotes = await stock_service.get_watch_list_quotes()
    return {"success": True, "data": quotes}


@router.post("/watch-list", summary="添加股票到关注列表")
async def add_to_watch_list(request: AddWatchRequest):
    """
    添加股票到关注列表
    """
    item = await stock_service.add_to_watch_list(
        code=request.code,
        alert_up=request.alert_up,
        alert_down=request.alert_down,
        note=request.note,
        group=request.group
    )
    if not item:
        raise HTTPException(status_code=400, detail=f"添加股票 {request.code} 失败，请检查代码是否正确")

    return {"success": True, "message": "添加成功", "data": item.model_dump(mode="json")}


@router.delete("/watch-list/{code}", summary="从关注列表移除股票")
async def remove_from_watch_list(code: str):
    """
    从关注列表移除股票
    """
    success = stock_service.remove_from_watch_list(code)
    if not success:
        raise HTTPException(status_code=404, detail=f"未在关注列表中找到股票 {code}")

    return {"success": True, "message": "移除成功"}


@router.put("/watch-list/{code}/alert", summary="更新提醒设置")
async def update_alert_settings(
    code: str,
    alert_up: Optional[float] = Query(None, description="涨幅提醒阈值（%）"),
    alert_down: Optional[float] = Query(None, description="跌幅提醒阈值（%）")
):
    """
    更新股票的提醒设置
    """
    item = stock_service.update_alert_settings(code, alert_up, alert_down)
    if not item:
        raise HTTPException(status_code=404, detail=f"未在关注列表中找到股票 {code}")
    return {"success": True, "message": "更新成功", "data": item.model_dump(mode="json")}


# ============ 分组管理 ============

@router.get("/groups", summary="获取所有分组")
async def get_groups():
    """
    获取所有分组及其股票数量
    """
    groups = stock_service.get_groups()
    return {"success": True, "data": groups}


@router.put("/watch-list/{code}/group", summary="更新股票分组")
async def update_stock_group(
    code: str,
    group: str = Query(..., description="目标分组名称")
):
    """
    将股票移动到指定分组
    """
    success = stock_service.update_stock_group(code, group)
    if not success:
        raise HTTPException(status_code=404, detail=f"未在关注列表中找到股票 {code}")
    return {"success": True, "message": f"已将股票移动到分组 {group}"}


@router.put("/groups/{old_name}/rename", summary="重命名分组")
async def rename_group(
    old_name: str,
    new_name: str = Query(..., description="新分组名称")
):
    """
    重命名分组
    """
    if old_name == "default":
        raise HTTPException(status_code=400, detail="不能重命名默认分组")

    count = stock_service.rename_group(old_name, new_name)
    return {"success": True, "message": f"已重命名分组，影响 {count} 只股票"}


@router.delete("/groups/{group_name}", summary="删除分组")
async def delete_group(
    group_name: str,
    move_to: str = Query("default", description="将股票移动到的目标分组")
):
    """
    删除分组，将其中的股票移动到指定分组
    """
    if group_name == "default":
        raise HTTPException(status_code=400, detail="不能删除默认分组")

    count = stock_service.delete_group(group_name, move_to)
    return {"success": True, "message": f"已删除分组，{count} 只股票移动到 {move_to}"}


@router.get("/watch-list/by-group/{group}", summary="按分组获取关注列表")
async def get_watch_list_by_group(group: str):
    """
    获取指定分组的关注列表
    """
    watch_list = stock_service.get_watch_list(group=group)
    return {
        "success": True,
        "data": [item.model_dump(mode="json") for item in watch_list]
    }


@router.get("/market/sentiment", summary="获取市场情绪")
async def get_market_sentiment():
    """
    获取市场情绪数据（上涨/下跌家数、涨停/跌停数、北向资金等）
    """
    sentiment = await stock_service.get_market_sentiment()
    return {"success": True, "data": sentiment.model_dump(mode="json")}


@router.get("/trading-status", summary="获取交易状态")
async def get_trading_status():
    """
    获取当前交易状态
    返回是否交易日、是否交易时间、上一交易日
    """
    now = datetime.now()
    is_trading_day = await trading_calendar.is_trading_day(now)
    is_trading_hours = await trading_calendar.is_trading_hours(now)
    last_trading_day = await trading_calendar.get_last_trading_day(now)

    return {
        "success": True,
        "data": {
            "is_trading": is_trading_hours,
            "is_trading_day": is_trading_day,
            "last_trading_day": last_trading_day.strftime("%Y-%m-%d"),
            "current_time": now.isoformat()
        }
    }


@router.get("/indices/default", summary="获取默认股指行情")
async def get_default_indices():
    """
    获取主页展示的默认股指行情
    包括：上证50、科创50、北证50、深证成指、沪深300、上证指数
    """
    quotes = await stock_service.get_default_indices_quotes()
    return {"success": True, "data": quotes}


@router.get("/commodities", summary="获取大宗商品行情")
async def get_commodities():
    """
    获取大宗商品实时行情
    包括：黄金、原油、螺纹钢、铜等期货主力合约
    """
    quotes = await stock_service.get_commodities_quotes()
    return {"success": True, "data": quotes}
