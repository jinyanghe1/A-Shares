"""提醒相关路由"""
from fastapi import APIRouter, Query
from typing import Optional

from app.models import Alert, AlertSettingRequest
from app.services.alert_service import alert_service
from app.services.stock_service import stock_service

router = APIRouter(prefix="/api/alerts", tags=["提醒"])


@router.get("", summary="获取提醒列表")
async def get_alerts(
    limit: int = Query(50, description="返回数量"),
    code: Optional[str] = Query(None, description="按股票代码筛选")
):
    """
    获取提醒列表
    """
    if code:
        alerts = alert_service.get_alerts_by_code(code)
    else:
        alerts = alert_service.get_recent_alerts(limit)

    return {
        "success": True,
        "data": [alert.model_dump(mode="json") for alert in alerts]
    }


@router.post("/check", summary="检查并触发提醒")
async def check_alerts():
    """
    检查关注列表中的股票是否触发提醒条件
    """
    quotes = await stock_service.get_watch_list_quotes()
    watch_list = {item.code: item for item in stock_service.get_watch_list()}

    triggered = []
    for quote in quotes:
        code = quote["code"]
        watch_item = watch_list.get(code)

        alerts = alert_service.check_alerts(
            code=code,
            name=quote.get("name", ""),
            price=quote.get("price", 0),
            change_percent=quote.get("change_percent", 0),
            alert_up=watch_item.alert_up if watch_item else None,
            alert_down=watch_item.alert_down if watch_item else None
        )

        for alert in alerts:
            triggered.append(alert)
            alert_service.mark_alert_sent(alert)

    return {
        "success": True,
        "data": {
            "triggered_count": len(triggered),
            "alerts": [alert.model_dump(mode="json") for alert in triggered]
        }
    }


@router.delete("", summary="清除提醒")
async def clear_alerts():
    """
    清除所有提醒记录
    """
    alert_service.clear_alerts()
    return {"success": True, "message": "提醒已清除"}


@router.post("/settings", summary="批量更新提醒设置")
async def update_alert_settings(request: AlertSettingRequest):
    """
    更新股票的提醒设置
    """
    item = stock_service.update_alert_settings(
        code=request.code,
        alert_up=request.alert_up,
        alert_down=request.alert_down
    )

    if not item:
        return {"success": False, "message": f"未找到股票 {request.code}"}

    return {
        "success": True,
        "message": "设置已更新",
        "data": item.model_dump(mode="json")
    }
