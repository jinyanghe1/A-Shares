"""交易日历服务"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx


class TradingCalendarService:
    """交易日历服务 - 检测交易日和非交易日"""

    def __init__(self):
        self.calendar_file = "trading_days.json"
        self.calendar_cache: Dict[str, bool] = {}
        self._load_calendar()

    def _load_calendar(self):
        """从文件加载交易日历缓存"""
        if os.path.exists(self.calendar_file):
            try:
                with open(self.calendar_file, 'r', encoding='utf-8') as f:
                    self.calendar_cache = json.load(f)
            except Exception as e:
                print(f"加载交易日历失败: {e}")
                self.calendar_cache = {}
        else:
            self.calendar_cache = {}

    def _save_calendar(self):
        """保存交易日历到文件"""
        try:
            with open(self.calendar_file, 'w', encoding='utf-8') as f:
                json.dump(self.calendar_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存交易日历失败: {e}")

    def _get_date_key(self, date: datetime) -> str:
        """获取日期键（YYYY-MM-DD格式）"""
        return date.strftime("%Y-%m-%d")

    async def is_trading_day(self, date: datetime) -> bool:
        """
        检查是否为交易日
        规则：
        1. 周一到周五为潜在交易日
        2. 周六、周日为非交易日
        3. 法定节假日为非交易日（简化版：仅检查周末）
        """
        date_key = self._get_date_key(date)

        # 检查缓存
        if date_key in self.calendar_cache:
            return self.calendar_cache[date_key]

        # 周末判断
        weekday = date.weekday()
        if weekday >= 5:  # 周六、周日
            self.calendar_cache[date_key] = False
            self._save_calendar()
            return False

        # 简化版：周一到周五默认为交易日
        # TODO: 未来可接入官方交易日历API
        # 暂时使用简单规则：排除中国法定节假日（需要手动维护）
        is_trading = await self._check_holiday(date)
        self.calendar_cache[date_key] = is_trading
        self._save_calendar()

        return is_trading

    async def _check_holiday(self, date: datetime) -> bool:
        """
        检查是否为法定节假日
        简化版：使用硬编码的2026年节假日列表
        """
        # 2026年中国法定节假日（粗略版本）
        holidays_2026 = [
            # 元旦 (2026-01-01 至 2026-01-03)
            "2026-01-01", "2026-01-02", "2026-01-03",
            # 春节 (2026-02-17 至 2026-02-23)
            "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
            "2026-02-21", "2026-02-22", "2026-02-23",
            # 清明节 (2026-04-05 至 2026-04-07)
            "2026-04-05", "2026-04-06", "2026-04-07",
            # 劳动节 (2026-05-01 至 2026-05-05)
            "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
            # 端午节 (2026-06-25 至 2026-06-27)
            "2026-06-25", "2026-06-26", "2026-06-27",
            # 中秋节 (2026-10-04 至 2026-10-06)
            "2026-10-04", "2026-10-05", "2026-10-06",
            # 国庆节 (2026-10-01 至 2026-10-07)
            "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-07",
        ]

        date_key = self._get_date_key(date)
        if date_key in holidays_2026:
            return False

        return True

    async def is_trading_hours(self, dt: datetime) -> bool:
        """
        检查是否为交易时间
        A股交易时间：
        - 上午 9:30-11:30
        - 下午 13:00-15:00
        """
        if not await self.is_trading_day(dt):
            return False

        hour = dt.hour
        minute = dt.minute

        # 上午时段 9:30-11:30
        if (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30):
            return True

        # 下午时段 13:00-15:00
        if (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
            return True

        return False

    async def get_last_trading_day(self, date: datetime) -> datetime:
        """
        获取上一个交易日
        从给定日期往前推，找到最近的交易日
        """
        current = date - timedelta(days=1)
        max_lookback = 10  # 最多往前查找10天

        for _ in range(max_lookback):
            if await self.is_trading_day(current):
                return current
            current -= timedelta(days=1)

        # 如果10天内找不到交易日，返回当前日期
        return date

    async def get_next_trading_day(self, date: datetime) -> datetime:
        """
        获取下一个交易日
        从给定日期往后推，找到最近的交易日
        """
        current = date + timedelta(days=1)
        max_lookforward = 10

        for _ in range(max_lookforward):
            if await self.is_trading_day(current):
                return current
            current += timedelta(days=1)

        return date


# 全局单例
trading_calendar = TradingCalendarService()
