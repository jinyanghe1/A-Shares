"""市场数据相关路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.utils.eastmoney import eastmoney_api

router = APIRouter(prefix="/api/market", tags=["市场数据"])


@router.get("/north-flow", summary="获取北向资金实时数据")
async def get_north_flow():
    """
    获取北向资金实时净流入数据
    包括沪股通和深股通的分别数据
    """
    result = await eastmoney_api.get_north_flow()

    if not result:
        raise HTTPException(status_code=500, detail="获取北向资金数据失败")

    return {
        "success": True,
        "data": result
    }


@router.get("/north-flow/minute", summary="获取北向资金日内分时数据")
async def get_north_flow_minute():
    """
    获取北向资金日内分时数据
    返回今日每分钟的资金流入情况
    """
    result = await eastmoney_api.get_north_flow_minute()

    if not result:
        raise HTTPException(status_code=500, detail="获取北向资金分时数据失败")

    return {
        "success": True,
        "data": result
    }


@router.get("/north-flow/history", summary="获取北向资金历史数据")
async def get_north_flow_history(
    days: int = Query(30, description="获取天数", ge=1, le=365)
):
    """
    获取北向资金历史数据
    返回最近N天的每日北向资金净流入
    """
    result = await eastmoney_api.get_north_flow_history(days=days)

    if not result:
        raise HTTPException(status_code=500, detail="获取北向资金历史数据失败")

    # 计算统计数据
    total_inflow = sum(d["total_net"] for d in result)
    positive_days = sum(1 for d in result if d["total_net"] > 0)
    negative_days = sum(1 for d in result if d["total_net"] < 0)
    max_inflow = max(result, key=lambda x: x["total_net"])
    min_inflow = min(result, key=lambda x: x["total_net"])

    return {
        "success": True,
        "data": {
            "history": result,
            "statistics": {
                "total_days": len(result),
                "total_inflow": total_inflow,
                "avg_inflow": total_inflow / len(result) if result else 0,
                "positive_days": positive_days,
                "negative_days": negative_days,
                "max_inflow_day": {
                    "date": max_inflow["date"],
                    "amount": max_inflow["total_net"]
                },
                "min_inflow_day": {
                    "date": min_inflow["date"],
                    "amount": min_inflow["total_net"]
                }
            }
        }
    }


@router.get("/north-flow/holdings", summary="获取北向资金持股排行")
async def get_north_holdings(
    market: str = Query("all", description="市场: sh(沪股通), sz(深股通), all(全部)"),
    count: int = Query(20, description="返回数量", ge=1, le=100)
):
    """
    获取北向资金持股排行
    按持股市值排序
    """
    if market not in ["sh", "sz", "all"]:
        raise HTTPException(status_code=400, detail="market 参数必须是 sh, sz 或 all")

    result = await eastmoney_api.get_north_top_holdings(market=market, count=count)

    if not result:
        raise HTTPException(status_code=500, detail="获取北向资金持股数据失败")

    return {
        "success": True,
        "data": {
            "market": market,
            "count": len(result),
            "holdings": result
        }
    }


@router.get("/north-flow/analysis", summary="北向资金综合分析")
async def analyze_north_flow():
    """
    北向资金综合分析
    包括实时数据、今日走势、近期趋势
    """
    # 获取实时数据
    realtime = await eastmoney_api.get_north_flow()

    # 获取分时数据
    minute_data = await eastmoney_api.get_north_flow_minute()

    # 获取历史数据（近10天）
    history = await eastmoney_api.get_north_flow_history(days=10)

    # 分析结果
    analysis = {
        "trend": "unknown",
        "trend_text": "",
        "signal": "neutral",
        "alerts": []
    }

    if realtime and history:
        total = realtime.get("total_net", 0)

        # 判断资金流入趋势
        if history and len(history) >= 5:
            recent_5 = sum(d["total_net"] for d in history[-5:])
            recent_3 = sum(d["total_net"] for d in history[-3:])

            if recent_5 > 0 and recent_3 > 0:
                analysis["trend"] = "bullish"
                analysis["trend_text"] = "近期北向资金持续流入"
                analysis["signal"] = "buy"
            elif recent_5 < 0 and recent_3 < 0:
                analysis["trend"] = "bearish"
                analysis["trend_text"] = "近期北向资金持续流出"
                analysis["signal"] = "sell"
            elif recent_3 > 0:
                analysis["trend"] = "improving"
                analysis["trend_text"] = "近3日北向资金转为流入"
            elif recent_3 < 0:
                analysis["trend"] = "weakening"
                analysis["trend_text"] = "近3日北向资金转为流出"
            else:
                analysis["trend"] = "neutral"
                analysis["trend_text"] = "北向资金流向无明显趋势"

        # 异常提醒
        if abs(total) > 10000000000:  # 大于100亿
            direction = "流入" if total > 0 else "流出"
            analysis["alerts"].append({
                "type": "large_flow",
                "level": "high",
                "message": f"今日北向资金大额{direction}，金额超过100亿"
            })

        if history and len(history) >= 5:
            # 连续5天同向流动
            directions = [1 if d["total_net"] > 0 else -1 for d in history[-5:]]
            if all(d == 1 for d in directions):
                analysis["alerts"].append({
                    "type": "consecutive_inflow",
                    "level": "medium",
                    "message": "北向资金连续5日净流入"
                })
            elif all(d == -1 for d in directions):
                analysis["alerts"].append({
                    "type": "consecutive_outflow",
                    "level": "medium",
                    "message": "北向资金连续5日净流出"
                })

    return {
        "success": True,
        "data": {
            "realtime": realtime,
            "minute_data": minute_data.get("minute_data", []) if minute_data else [],
            "history": history[-10:] if history else [],
            "analysis": analysis
        }
    }


# ============ 板块分析模块 ============

@router.get("/sectors", summary="获取板块列表")
async def get_sector_list(
    type: str = Query("industry", description="板块类型: industry(行业), concept(概念), area(地域)")
):
    """
    获取板块列表
    返回板块涨跌排行
    """
    if type not in ["industry", "concept", "area"]:
        raise HTTPException(status_code=400, detail="type 参数必须是 industry, concept 或 area")

    result = await eastmoney_api.get_sector_list(sector_type=type)

    if not result:
        raise HTTPException(status_code=500, detail="获取板块数据失败")

    # 分组统计
    up_count = sum(1 for s in result if (s.get("change_percent") or 0) > 0)
    down_count = sum(1 for s in result if (s.get("change_percent") or 0) < 0)
    flat_count = len(result) - up_count - down_count

    return {
        "success": True,
        "data": {
            "type": type,
            "count": len(result),
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "sectors": result
        }
    }


@router.get("/sectors/top", summary="获取涨跌幅榜")
async def get_sector_top(
    type: str = Query("industry", description="板块类型"),
    direction: str = Query("up", description="方向: up(涨幅榜), down(跌幅榜)"),
    count: int = Query(10, description="返回数量", ge=1, le=50)
):
    """
    获取板块涨跌幅排行榜
    """
    result = await eastmoney_api.get_sector_list(sector_type=type)

    if not result:
        raise HTTPException(status_code=500, detail="获取板块数据失败")

    # 根据方向排序
    if direction == "down":
        result.sort(key=lambda x: x.get("change_percent") or 0)
    else:
        result.sort(key=lambda x: x.get("change_percent") or 0, reverse=True)

    return {
        "success": True,
        "data": {
            "type": type,
            "direction": direction,
            "sectors": result[:count]
        }
    }


@router.get("/sectors/{sector_code}/stocks", summary="获取板块成分股")
async def get_sector_stocks(
    sector_code: str,
    count: int = Query(20, description="返回数量", ge=1, le=100)
):
    """
    获取板块成分股列表
    """
    result = await eastmoney_api.get_sector_stocks(sector_code=sector_code, count=count)

    if not result:
        raise HTTPException(status_code=500, detail=f"获取板块 {sector_code} 成分股失败")

    return {
        "success": True,
        "data": {
            "sector_code": sector_code,
            "count": len(result),
            "stocks": result
        }
    }


@router.get("/sectors/flow", summary="获取板块资金流向")
async def get_sector_flow(
    type: str = Query("industry", description="板块类型: industry(行业), concept(概念)"),
    count: int = Query(20, description="返回数量", ge=1, le=50)
):
    """
    获取板块资金流向排行
    按主力净流入排序
    """
    if type not in ["industry", "concept"]:
        raise HTTPException(status_code=400, detail="type 参数必须是 industry 或 concept")

    result = await eastmoney_api.get_sector_flow(sector_type=type, count=count)

    if not result:
        raise HTTPException(status_code=500, detail="获取板块资金流向失败")

    # 分组
    inflow = [s for s in result if (s.get("main_net_inflow") or 0) > 0]
    outflow = [s for s in result if (s.get("main_net_inflow") or 0) < 0]

    return {
        "success": True,
        "data": {
            "type": type,
            "inflow_count": len(inflow),
            "outflow_count": len(outflow),
            "top_inflow": inflow[:10],
            "top_outflow": outflow[-10:][::-1] if outflow else [],
            "all": result
        }
    }


@router.get("/sectors/overview", summary="板块概览")
async def get_sectors_overview():
    """
    获取板块市场概览
    包括行业和概念板块的涨跌统计
    """
    # 获取行业板块
    industry = await eastmoney_api.get_sector_list(sector_type="industry")

    # 获取概念板块
    concept = await eastmoney_api.get_sector_list(sector_type="concept")

    def get_stats(sectors):
        if not sectors:
            return {"up": 0, "down": 0, "flat": 0, "top3": [], "bottom3": []}

        up = sum(1 for s in sectors if (s.get("change_percent") or 0) > 0)
        down = sum(1 for s in sectors if (s.get("change_percent") or 0) < 0)
        flat = len(sectors) - up - down

        sorted_sectors = sorted(sectors, key=lambda x: x.get("change_percent") or 0, reverse=True)

        return {
            "total": len(sectors),
            "up": up,
            "down": down,
            "flat": flat,
            "top3": sorted_sectors[:3],
            "bottom3": sorted_sectors[-3:][::-1]
        }

    return {
        "success": True,
        "data": {
            "industry": get_stats(industry),
            "concept": get_stats(concept)
        }
    }


# ============ 龙虎榜模块 ============

@router.get("/lhb", summary="获取龙虎榜列表")
async def get_lhb_list(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)，默认最新")
):
    """
    获取龙虎榜股票列表
    """
    result = await eastmoney_api.get_lhb_list(date=date)

    if not result:
        return {
            "success": True,
            "data": {
                "date": date,
                "count": 0,
                "stocks": [],
                "message": "今日暂无龙虎榜数据，可能是非交易日或数据尚未更新"
            }
        }

    # 统计
    net_buy_total = sum(s.get("net_buy", 0) for s in result)
    net_buy_stocks = sum(1 for s in result if (s.get("net_buy") or 0) > 0)
    net_sell_stocks = sum(1 for s in result if (s.get("net_buy") or 0) < 0)

    return {
        "success": True,
        "data": {
            "date": result[0].get("date") if result else date,
            "count": len(result),
            "net_buy_total": net_buy_total,
            "net_buy_stocks": net_buy_stocks,
            "net_sell_stocks": net_sell_stocks,
            "stocks": result
        }
    }


@router.get("/lhb/{code}", summary="获取龙虎榜个股详情")
async def get_lhb_detail(
    code: str,
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)")
):
    """
    获取龙虎榜个股的买卖席位详情
    """
    result = await eastmoney_api.get_lhb_detail(code=code, date=date)

    return {
        "success": True,
        "data": result
    }


@router.get("/lhb/traders/hot", summary="获取活跃游资席位")
async def get_hot_traders(
    days: int = Query(5, description="统计周期(天)", ge=1, le=30)
):
    """
    获取近期活跃的游资/机构席位统计
    """
    result = await eastmoney_api.get_hot_traders(days=days)

    if not result:
        return {
            "success": True,
            "data": {
                "days": days,
                "traders": [],
                "message": "暂无数据"
            }
        }

    return {
        "success": True,
        "data": {
            "days": days,
            "count": len(result),
            "traders": result
        }
    }
