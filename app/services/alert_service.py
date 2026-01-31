"""提醒服务"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from app.models import Alert, AlertType
from app.config import settings


class AlertService:
    """提醒服务"""

    def __init__(self):
        # 存储已触发的提醒
        self.alerts: List[Alert] = []
        # 连续涨跌记录 {code: [change_percent1, change_percent2, ...]}
        self.consecutive_records: Dict[str, List[float]] = defaultdict(list)
        # 每只股票上次提醒时间，避免重复提醒
        self.last_alert_time: Dict[str, datetime] = {}
        # 提醒冷却时间（秒）
        self.alert_cooldown = 300  # 5分钟内不重复提醒

    def check_alerts(
        self,
        code: str,
        name: str,
        price: float,
        change_percent: float,
        alert_up: Optional[float] = None,
        alert_down: Optional[float] = None
    ) -> List[Alert]:
        """
        检查是否触发提醒
        """
        triggered_alerts = []
        now = datetime.now()

        # 检查冷却时间
        last_time = self.last_alert_time.get(code)
        if last_time and (now - last_time).total_seconds() < self.alert_cooldown:
            return triggered_alerts

        # 使用自定义阈值或默认阈值
        threshold_up = alert_up if alert_up is not None else settings.alert_threshold_up
        threshold_down = alert_down if alert_down is not None else settings.alert_threshold_down

        # 检查涨幅提醒
        if change_percent >= threshold_up:
            alert = Alert(
                code=code,
                name=name,
                alert_type=AlertType.PRICE_UP,
                message=f"{name}({code}) 涨幅达到 {change_percent:.2f}%，当前价格 {price:.2f}",
                current_price=price,
                change_percent=change_percent,
                triggered_at=now
            )
            triggered_alerts.append(alert)

        # 检查跌幅提醒
        if change_percent <= threshold_down:
            alert = Alert(
                code=code,
                name=name,
                alert_type=AlertType.PRICE_DOWN,
                message=f"{name}({code}) 跌幅达到 {change_percent:.2f}%，当前价格 {price:.2f}",
                current_price=price,
                change_percent=change_percent,
                triggered_at=now
            )
            triggered_alerts.append(alert)

        if triggered_alerts:
            self.last_alert_time[code] = now
            self.alerts.extend(triggered_alerts)

        return triggered_alerts

    def record_daily_change(self, code: str, change_percent: float):
        """
        记录每日涨跌幅，用于连续涨跌提醒
        """
        records = self.consecutive_records[code]
        records.append(change_percent)
        # 只保留最近10天数据
        if len(records) > 10:
            records.pop(0)

    def check_consecutive_alert(
        self,
        code: str,
        name: str,
        price: float,
        consecutive_count: int = None
    ) -> Optional[Alert]:
        """
        检查连续涨跌提醒
        """
        count = consecutive_count or settings.consecutive_alert_count
        records = self.consecutive_records.get(code, [])

        if len(records) < count:
            return None

        recent = records[-count:]

        # 检查连续上涨
        if all(r > 0 for r in recent):
            total_change = sum(recent)
            return Alert(
                code=code,
                name=name,
                alert_type=AlertType.CONSECUTIVE_UP,
                message=f"{name}({code}) 连续 {count} 天上涨，累计涨幅 {total_change:.2f}%",
                current_price=price,
                change_percent=recent[-1],
                triggered_at=datetime.now()
            )

        # 检查连续下跌
        if all(r < 0 for r in recent):
            total_change = sum(recent)
            return Alert(
                code=code,
                name=name,
                alert_type=AlertType.CONSECUTIVE_DOWN,
                message=f"{name}({code}) 连续 {count} 天下跌，累计跌幅 {total_change:.2f}%",
                current_price=price,
                change_percent=recent[-1],
                triggered_at=datetime.now()
            )

        return None

    def get_recent_alerts(self, limit: int = 50) -> List[Alert]:
        """
        获取最近的提醒
        """
        return sorted(
            self.alerts,
            key=lambda x: x.triggered_at,
            reverse=True
        )[:limit]

    def get_alerts_by_code(self, code: str) -> List[Alert]:
        """
        获取指定股票的提醒
        """
        return [a for a in self.alerts if a.code == code]

    def clear_alerts(self):
        """
        清除所有提醒
        """
        self.alerts.clear()

    def mark_alert_sent(self, alert: Alert):
        """
        标记提醒已发送
        """
        alert.is_sent = True


# 创建全局实例
alert_service = AlertService()
