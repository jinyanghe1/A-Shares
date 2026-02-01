"""股票筛选路由"""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.screener_service import screener_service

router = APIRouter(prefix="/api/screener", tags=["股票筛选"])


@router.get("/filter", summary="筛选股票")
async def filter_stocks(
    market_cap_min: Optional[float] = Query(None, description="最小市值(亿)"),
    market_cap_max: Optional[float] = Query(None, description="最大市值(亿)"),
    pe_min: Optional[float] = Query(None, description="最小PE"),
    pe_max: Optional[float] = Query(None, description="最大PE"),
    pb_min: Optional[float] = Query(None, description="最小PB"),
    pb_max: Optional[float] = Query(None, description="最大PB"),
    change_min: Optional[float] = Query(None, description="最小涨跌幅(%)"),
    change_max: Optional[float] = Query(None, description="最大涨跌幅(%)"),
    turnover_min: Optional[float] = Query(None, description="最小换手率(%)"),
    turnover_max: Optional[float] = Query(None, description="最大换手率(%)"),
    industry: Optional[str] = Query(None, description="行业代码"),
    sort_by: str = Query("market_cap", description="排序字段: market_cap, pe, pb, change, turnover"),
    sort_order: str = Query("desc", description="排序方式: asc, desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量")
):
    """
    根据多种条件筛选股票
    """
    result = await screener_service.screen_stocks(
        market_cap_min=market_cap_min,
        market_cap_max=market_cap_max,
        pe_min=pe_min,
        pe_max=pe_max,
        pb_min=pb_min,
        pb_max=pb_max,
        change_min=change_min,
        change_max=change_max,
        turnover_min=turnover_min,
        turnover_max=turnover_max,
        industry=industry,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    return result


@router.get("/quick/{screen_type}", summary="快速筛选")
async def quick_screen(screen_type: str):
    """
    使用预设条件快速筛选股票

    可用类型:
    - low_pe: 低估值股票(PE<15,市值>100亿)
    - high_turnover: 活跃股票(换手率>5%)
    - big_cap: 大盘蓝筹(市值>500亿,PE<30)
    - small_cap_growth: 小盘成长(市值30-100亿,涨幅>0)
    - limit_up: 涨停板(涨幅>=9.9%)
    - limit_down: 跌停板(跌幅<=-9.9%)
    - high_volume: 放量上涨(换手率>10%,涨幅>3%)
    """
    result = await screener_service.get_quick_screen(screen_type)
    return result


@router.get("/config", summary="获取筛选配置")
async def get_filter_config():
    """
    获取筛选条件配置，用于前端展示
    """
    return {
        "success": True,
        "data": screener_service.get_filter_configs()
    }


@router.get("/industries", summary="获取行业列表")
async def get_industries():
    """
    获取行业列表，用于行业筛选
    """
    industries = await screener_service.get_industry_list()
    return {
        "success": True,
        "data": industries
    }


@router.get("/presets", summary="获取预设筛选列表")
async def get_presets():
    """
    获取所有预设筛选选项
    """
    presets = [
        {"type": "low_pe", "name": "低估值股票", "description": "PE<15，市值>100亿"},
        {"type": "high_turnover", "name": "活跃股票", "description": "换手率>5%"},
        {"type": "big_cap", "name": "大盘蓝筹", "description": "市值>500亿，PE<30"},
        {"type": "small_cap_growth", "name": "小盘成长", "description": "市值30-100亿，涨幅>0"},
        {"type": "limit_up", "name": "涨停板", "description": "涨幅>=9.9%"},
        {"type": "limit_down", "name": "跌停板", "description": "跌幅<=-9.9%"},
        {"type": "high_volume", "name": "放量上涨", "description": "换手率>10%，涨幅>3%"}
    ]

    return {
        "success": True,
        "data": presets
    }
