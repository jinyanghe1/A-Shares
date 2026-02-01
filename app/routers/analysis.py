"""分析相关路由 - 使用 DeepSeek API"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.services.deepseek_service import deepseek_service
from app.services.stock_service import stock_service
from app.services.analysis_service import analysis_service
from app.services.sentiment_service import sentiment_service
from app.services.technical_service import technical_service
from app.services.finance_service import finance_service
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
    limit: int = Query(5, description="新闻数量"),
    sentiment_analysis: bool = Query(True, description="是否进行情绪分析")
):
    """
    获取股票相关新闻，并可选择使用 AI 分析和情绪分析
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    stock_name = quote.name if quote else ""

    # 获取新闻（默认获取50条用于情绪分析）
    news_count = max(limit, 50) if sentiment_analysis else limit
    news_list = await eastmoney_api.get_stock_news(code, page_size=news_count)

    if not news_list:
        return {
            "success": True,
            "data": {
                "code": code,
                "name": stock_name,
                "news": [],
                "sentiment_summary": None,
                "message": "暂无相关新闻"
            }
        }

    # 情绪分析
    sentiment_summary = None
    if sentiment_analysis:
        sentiment_result = sentiment_service.analyze_news_list(news_list[:50])
        sentiment_summary = {
            "overall_score": sentiment_result["overall_score"],
            "overall_label": sentiment_result["overall_label"],
            "positive_count": sentiment_result["positive_count"],
            "neutral_count": sentiment_result["neutral_count"],
            "negative_count": sentiment_result["negative_count"],
            "positive_ratio": sentiment_result["positive_ratio"],
            "negative_ratio": sentiment_result["negative_ratio"],
            "neutral_ratio": sentiment_result["neutral_ratio"]
        }

        # 为前limit条新闻添加情绪信息
        for i, news in enumerate(news_list[:limit]):
            if i < len(sentiment_result["news_sentiments"]):
                news["sentiment"] = sentiment_result["news_sentiments"][i]["sentiment"]

    # 如果需要AI分析，分析第一条新闻
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
            "news": news_list[:limit],  # 只返回前limit条
            "sentiment_summary": sentiment_summary,
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

    # 获取主要股指行情
    indices = await stock_service.get_default_indices_quotes()

    # 生成总结
    summary = await deepseek_service.generate_daily_summary(
        watch_list_data=quotes,
        market_sentiment=sentiment.model_dump(),
        indices_data=indices
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


# ============ 舆情指数模块 ============

@router.get("/sentiment/index", summary="获取市场舆情指数")
async def get_sentiment_index(
    category: str = Query("all", description="新闻类别: stock(股票), market(大盘), finance(财经), all(全部)"),
    count: int = Query(100, description="分析的新闻数量(最多100)")
):
    """
    计算市场舆情指数
    基于最新新闻进行情感分析，返回综合舆情指数和详细分析
    """
    # 获取市场新闻
    news_list = await eastmoney_api.get_market_news(
        category=category,
        page_size=min(count, 100)
    )

    if not news_list:
        return {
            "success": False,
            "message": "无法获取市场新闻数据"
        }

    # 计算舆情指数
    result = sentiment_service.calculate_sentiment_index(news_list)

    return {
        "success": result["success"],
        "data": result
    }


@router.get("/sentiment/stock/{code}", summary="获取个股舆情指数")
async def get_stock_sentiment_index(
    code: str,
    count: int = Query(50, description="分析的新闻数量")
):
    """
    计算个股舆情指数
    获取个股相关新闻进行情感分析
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    stock_name = quote.name if quote else code

    # 获取个股新闻
    news_list = await eastmoney_api.get_stock_news(code, page_size=min(count, 100))

    if not news_list:
        return {
            "success": False,
            "message": f"无法获取 {stock_name} 的相关新闻"
        }

    # 计算舆情指数
    result = sentiment_service.calculate_sentiment_index(news_list)

    return {
        "success": result["success"],
        "data": {
            "code": code,
            "name": stock_name,
            **result
        }
    }


@router.get("/sentiment/compare", summary="舆情指数对比")
async def compare_sentiment(
    codes: str = Query(..., description="股票代码列表，逗号分隔，如: 000001,600000,00700")
):
    """
    对比多只股票的舆情指数
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]

    if len(code_list) < 2:
        raise HTTPException(status_code=400, detail="请至少输入2个股票代码")

    if len(code_list) > 5:
        raise HTTPException(status_code=400, detail="最多支持5只股票对比")

    results = []

    for code in code_list:
        quote = await stock_service.get_quote(code)
        stock_name = quote.name if quote else code

        news_list = await eastmoney_api.get_stock_news(code, page_size=50)

        if news_list:
            sentiment_result = sentiment_service.calculate_sentiment_index(news_list)
            results.append({
                "code": code,
                "name": stock_name,
                "index": sentiment_result["index"],
                "level": sentiment_result["level_info"]["level"],
                "color": sentiment_result["level_info"]["color"],
                "icon": sentiment_result["level_info"]["icon"],
                "positive_ratio": sentiment_result["distribution"]["positive"]["ratio"],
                "negative_ratio": sentiment_result["distribution"]["negative"]["ratio"],
                "trend": sentiment_result["trend"]["direction"],
                "news_count": sentiment_result["total_news"]
            })
        else:
            results.append({
                "code": code,
                "name": stock_name,
                "index": 50,
                "level": "无数据",
                "color": "#999999",
                "icon": "❓",
                "positive_ratio": 0,
                "negative_ratio": 0,
                "trend": "unknown",
                "news_count": 0
            })

    # 按舆情指数排序
    results.sort(key=lambda x: x["index"], reverse=True)

    return {
        "success": True,
        "data": {
            "stocks": results,
            "best": results[0] if results else None,
            "worst": results[-1] if results else None
        }
    }


# ============ 技术指标分析模块 ============

@router.get("/technical/{code}", summary="获取股票技术指标分析")
async def get_technical_analysis(
    code: str,
    days: int = Query(120, description="分析周期（天数）", ge=30, le=500)
):
    """
    获取股票的技术指标分析
    包括：MACD、KDJ、RSI、布林带、均线系统
    返回完整的指标数据和买卖信号
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取K线数据
    kline_data = await eastmoney_api.get_kline_data(code, days=days)

    if not kline_data or len(kline_data) < 30:
        raise HTTPException(
            status_code=400,
            detail=f"数据不足，{quote.name} 的K线数据少于30条"
        )

    # 计算技术指标
    result = technical_service.calculate_all_indicators(kline_data)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "success": True,
        "data": {
            "code": code,
            "name": quote.name,
            "price": quote.price,
            "change_percent": quote.change_percent,
            **result
        }
    }


@router.get("/technical/{code}/signals", summary="获取技术信号摘要")
async def get_technical_signals(
    code: str,
    days: int = Query(60, description="分析周期（天数）", ge=30, le=500)
):
    """
    获取股票的技术信号摘要
    返回当前买卖信号和综合评估
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取K线数据
    kline_data = await eastmoney_api.get_kline_data(code, days=days)

    if not kline_data or len(kline_data) < 30:
        raise HTTPException(
            status_code=400,
            detail=f"数据不足，{quote.name} 的K线数据少于30条"
        )

    # 计算技术指标
    result = technical_service.calculate_all_indicators(kline_data)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "success": True,
        "data": {
            "code": code,
            "name": quote.name,
            "price": quote.price,
            "change_percent": quote.change_percent,
            "latest_signals": result["latest_signals"]
        }
    }


# ============ 财报分析模块 ============

@router.get("/finance/{code}", summary="获取股票财务分析")
async def get_finance_analysis(code: str):
    """
    获取股票完整财务分析报告
    包括：财务指标、健康度评分、行业对比、趋势分析
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取完整财务分析
    result = await finance_service.get_full_analysis(code)

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", f"无法获取 {quote.name} 的财务数据")
        )

    return {
        "success": True,
        "data": {
            "code": code,
            "name": quote.name,
            "price": quote.price,
            "change_percent": quote.change_percent,
            **result
        }
    }


@router.get("/finance/{code}/indicators", summary="获取财务指标")
async def get_finance_indicators(code: str):
    """
    获取股票主要财务指标
    返回最近8个季度的财务指标数据
    """
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取财务指标
    indicators = await eastmoney_api.get_finance_indicators(code)

    if not indicators:
        raise HTTPException(
            status_code=400,
            detail=f"无法获取 {quote.name} 的财务指标"
        )

    return {
        "success": True,
        "data": {
            "code": code,
            "name": quote.name,
            **indicators
        }
    }


@router.get("/finance/{code}/health", summary="获取财务健康度评分")
async def get_finance_health(code: str):
    """
    获取股票财务健康度评分
    评分维度：盈利能力、偿债能力、运营能力、成长能力
    """
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取综合财务数据
    finance_data = await finance_service.get_comprehensive_finance(code)

    if not finance_data:
        raise HTTPException(
            status_code=400,
            detail=f"无法获取 {quote.name} 的财务数据"
        )

    # 计算财务比率
    ratios = finance_service.calculate_financial_ratios(finance_data)

    # 计算健康度评分
    health_score = finance_service.calculate_health_score(ratios)

    return {
        "success": True,
        "data": {
            "code": code,
            "name": quote.name,
            "ratios": ratios,
            "health_score": health_score
        }
    }


@router.get("/finance/{code}/industry", summary="获取行业对比")
async def get_industry_comparison(code: str):
    """
    获取股票同行业对比数据
    返回行业排名和行业平均值
    """
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取行业对比
    comparison = await finance_service.get_industry_comparison(code)

    if not comparison:
        raise HTTPException(
            status_code=400,
            detail=f"无法获取 {quote.name} 的行业对比数据"
        )

    return {
        "success": True,
        "data": {
            "name": quote.name,
            **comparison
        }
    }


@router.get("/finance/{code}/statements", summary="获取财务报表")
async def get_finance_statements(
    code: str,
    statement_type: str = Query("all", description="报表类型: income(利润表), balance(资产负债表), cashflow(现金流量表), all(全部)")
):
    """
    获取股票财务报表数据
    """
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    result = {"code": code, "name": quote.name}

    if statement_type in ["income", "all"]:
        income = await eastmoney_api.get_income_statement(code)
        result["income_statement"] = income.get("statements", []) if income else []

    if statement_type in ["balance", "all"]:
        balance = await eastmoney_api.get_balance_sheet(code)
        result["balance_sheet"] = balance.get("sheets", []) if balance else []

    if statement_type in ["cashflow", "all"]:
        cashflow = await eastmoney_api.get_cash_flow(code)
        result["cash_flow"] = cashflow.get("flows", []) if cashflow else []

    return {
        "success": True,
        "data": result
    }
