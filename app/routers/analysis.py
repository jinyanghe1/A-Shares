"""分析相关路由 - 使用 DeepSeek API"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.services.deepseek_service import deepseek_service
from app.services.stock_service import stock_service
from app.services.analysis_service import analysis_service
from app.utils.eastmoney import eastmoney_api
from app.models import CorrelationRequest

router = APIRouter(prefix="/api/analysis", tags=["AI分析"])


class NewsAnalysisRequest(BaseModel):
    """新闻分析请求"""
    title: str = Field(..., description="新闻标题")
    content: str = Field(..., description="新闻内容")
    stock_name: str = Field("", description="相关股票名称")


class AnnouncementAnalysisRequest(BaseModel):
    """公告分析请求"""
    title: str = Field(..., description="公告标题")
    content: str = Field(..., description="公告内容")


@router.get("/stock/{code}", summary="分析股票行情")
async def analyze_stock(code: str):
    """
    使用 AI 分析股票行情走势
    """
    # 获取股票行情
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取资金流向
    flow = await stock_service.get_capital_flow(code)
    main_net = flow.main_net_inflow if flow else None

    # AI 分析
    analysis = await deepseek_service.analyze_stock_trend(
        code=quote.code,
        name=quote.name,
        price=quote.price,
        change_percent=quote.change_percent,
        volume=quote.volume,
        turnover_rate=quote.turnover_rate,
        main_net_inflow=main_net
    )

    return {
        "success": True,
        "data": {
            "code": quote.code,
            "name": quote.name,
            "quote": quote.model_dump(mode="json"),
            "analysis": analysis
        }
    }


@router.get("/market", summary="分析市场情绪")
async def analyze_market():
    """
    使用 AI 分析当前市场情绪
    """
    # 获取市场数据
    sentiment = await stock_service.get_market_sentiment()

    # AI 分析
    analysis = await deepseek_service.analyze_market_sentiment(
        up_count=sentiment.up_count,
        down_count=sentiment.down_count,
        limit_up_count=sentiment.limit_up_count,
        limit_down_count=sentiment.limit_down_count,
        north_net_inflow=sentiment.north_net_inflow
    )

    return {
        "success": True,
        "data": {
            "sentiment": sentiment.model_dump(mode="json"),
            "analysis": analysis
        }
    }


@router.post("/news", summary="解读新闻")
async def analyze_news(request: NewsAnalysisRequest):
    """
    使用 AI 解读新闻内容
    """
    analysis = await deepseek_service.analyze_news(
        news_title=request.title,
        news_content=request.content,
        stock_name=request.stock_name
    )

    return {
        "success": True,
        "data": {
            "title": request.title,
            "analysis": analysis
        }
    }


@router.post("/announcement", summary="解读公告")
async def analyze_announcement(request: AnnouncementAnalysisRequest):
    """
    使用 AI 解读公司公告
    """
    analysis = await deepseek_service.interpret_announcement(
        title=request.title,
        content=request.content
    )

    return {
        "success": True,
        "data": {
            "title": request.title,
            "analysis": analysis
        }
    }


@router.get("/news/{code}", summary="获取并分析股票新闻")
async def get_and_analyze_news(
    code: str,
    analyze: bool = Query(True, description="是否进行 AI 分析"),
    limit: int = Query(5, description="新闻数量")
):
    """
    获取股票相关新闻，并可选择使用 AI 分析
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    stock_name = quote.name if quote else ""

    # 获取新闻
    news_list = await eastmoney_api.get_stock_news(code, page_size=limit)

    if not news_list:
        return {
            "success": True,
            "data": {
                "code": code,
                "name": stock_name,
                "news": [],
                "message": "暂无相关新闻"
            }
        }

    # 如果需要分析，分析第一条新闻
    analysis = None
    if analyze and news_list:
        first_news = news_list[0]
        analysis = await deepseek_service.analyze_news(
            news_title=first_news["title"],
            news_content=first_news.get("content", ""),
            stock_name=stock_name
        )

    return {
        "success": True,
        "data": {
            "code": code,
            "name": stock_name,
            "news": news_list,
            "latest_analysis": analysis
        }
    }


@router.get("/announcements/{code}", summary="获取并分析股票公告")
async def get_and_analyze_announcements(
    code: str,
    analyze: bool = Query(False, description="是否进行 AI 分析（公告内容通常较长）"),
    limit: int = Query(5, description="公告数量")
):
    """
    获取股票相关公告列表
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    stock_name = quote.name if quote else ""

    # 获取公告
    announcements = await eastmoney_api.get_stock_announcements(code, page_size=limit)

    return {
        "success": True,
        "data": {
            "code": code,
            "name": stock_name,
            "announcements": announcements
        }
    }


@router.get("/daily-summary", summary="生成每日盯盘总结")
async def generate_daily_summary():
    """
    使用 AI 生成关注股票的每日盯盘总结
    """
    # 获取关注列表行情
    quotes = await stock_service.get_watch_list_quotes()
    if not quotes:
        return {
            "success": False,
            "message": "关注列表为空，请先添加股票"
        }

    # 获取市场情绪
    sentiment = await stock_service.get_market_sentiment()

    # 生成总结
    summary = await deepseek_service.generate_daily_summary(
        watch_list_data=quotes,
        market_sentiment=sentiment.model_dump()
    )

    return {
        "success": True,
        "data": {
            "date": sentiment.date.isoformat(),
            "watch_list_count": len(quotes),
            "summary": summary
        }
    }


@router.post("/correlation", summary="计算相关性")
async def calculate_correlation(request: CorrelationRequest):
    """
    计算两只股票/指数的指标相关性
    支持的指标：换手率(turnover_rate)、振幅(amplitude)、5日均价(ma5)
    """
    result = await analysis_service.analyze_correlation(
        code1=request.code1,
        code2=request.code2,
        days=request.days,
        indicators=request.indicators
    )

    if not result:
        raise HTTPException(
            status_code=400,
            detail=f"数据不足，无法计算 {request.code1} 和 {request.code2} 的相关性"
        )

    return {"success": True, "data": result}
