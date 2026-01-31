"""股票数据服务"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os

from app.models import WatchListItem, StockQuote, CapitalFlow, MarketSentiment
from app.utils.eastmoney import eastmoney_api
from app.utils.biying import biying_api
from app.services.trading_calendar import trading_calendar
from app.config import DEFAULT_INDICES, DEFAULT_COMMODITIES


class StockService:
    """股票服务"""

    def __init__(self):
        self.watch_list: Dict[str, WatchListItem] = {}
        self.quotes_cache: Dict[str, StockQuote] = {}
        self.historical_quotes: Dict[str, Dict[str, Any]] = {}
        self.data_file = "watch_list.json"
        self.historical_file = "historical_quotes.json"
        self._load_watch_list()
        self._load_historical_quotes()

    def _load_watch_list(self):
        """从文件加载关注列表"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        watch_item = WatchListItem(**item)
                        self.watch_list[watch_item.code] = watch_item
            except Exception as e:
                print(f"加载关注列表失败: {e}")

    def _save_watch_list(self):
        """保存关注列表到文件"""
        try:
            data = [item.model_dump(mode="json") for item in self.watch_list.values()]
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"保存关注列表失败: {e}")

    async def add_to_watch_list(
        self,
        code: str,
        alert_up: Optional[float] = None,
        alert_down: Optional[float] = None,
        note: str = ""
    ) -> Optional[WatchListItem]:
        """添加股票到关注列表"""
        # 获取股票信息
        quote = await eastmoney_api.get_stock_quote(code)
        if not quote:
             # 尝试备用源
            quote = await biying_api.get_stock_quote(code)
        
        if not quote:
            return None

        item = WatchListItem(
            code=code,
            name=quote.get("name", ""),
            added_time=datetime.now(),
            alert_up=alert_up,
            alert_down=alert_down,
            note=note
        )
        self.watch_list[code] = item
        self._save_watch_list()
        return item

    def remove_from_watch_list(self, code: str) -> bool:
        """从关注列表移除股票"""
        if code in self.watch_list:
            del self.watch_list[code]
            self._save_watch_list()
            return True
        return False

    def get_watch_list(self) -> List[WatchListItem]:
        """获取关注列表"""
        return list(self.watch_list.values())

    def update_alert_settings(
        self,
        code: str,
        alert_up: Optional[float] = None,
        alert_down: Optional[float] = None
    ) -> Optional[WatchListItem]:
        """更新提醒设置"""
        if code not in self.watch_list:
            return None

        item = self.watch_list[code]
        if alert_up is not None:
            item.alert_up = alert_up
        if alert_down is not None:
            item.alert_down = alert_down
        self._save_watch_list()
        return item

    async def get_quote(self, code: str) -> Optional[StockQuote]:
        """获取单只股票行情"""
        data = await eastmoney_api.get_stock_quote(code)
        if not data:
            # 尝试备用源
            data = await biying_api.get_stock_quote(code)
            
        if not data:
            return None

        quote = StockQuote(
            code=data["code"],
            name=data["name"],
            price=data["price"],
            change=data["change"],
            change_percent=data["change_percent"],
            open_price=data["open_price"],
            high_price=data["high_price"],
            low_price=data["low_price"],
            pre_close=data.get("pre_close", 0),
            volume=data["volume"],
            amount=data["amount"],
            turnover_rate=data.get("turnover_rate", 0),
            pe_ratio=data.get("pe_ratio"),
            total_value=data.get("total_value"),
            flow_value=data.get("flow_value")
        )
        self.quotes_cache[code] = quote
        return quote

    async def get_watch_list_quotes(self) -> List[Dict[str, Any]]:
        """获取关注列表所有股票的行情"""
        codes = list(self.watch_list.keys())
        if not codes:
            return []

        quotes = await eastmoney_api.get_batch_quotes(codes)
        
        # 如果获取数量不完整，尝试用备用源补充或全部使用备用源
        # 简单策略: 如果为空则使用备用源
        if not quotes and codes:
            print("Eastmoney batch quotes failed, trying Biying API...")
            quotes = await biying_api.get_batch_quotes(codes)

        # 合并关注信息
        results = []
        for quote in quotes:
            code = quote["code"]
            watch_item = self.watch_list.get(code)
            if watch_item:
                quote["alert_up"] = watch_item.alert_up
                quote["alert_down"] = watch_item.alert_down
                quote["note"] = watch_item.note
            results.append(quote)

        return results

    async def get_capital_flow(self, code: str) -> Optional[CapitalFlow]:
        """获取个股资金流向"""
        data = await eastmoney_api.get_capital_flow(code)
        if not data:
            return None

        return CapitalFlow(
            code=data["code"],
            name=data["name"],
            main_net_inflow=data["main_net_inflow"],
            super_large_net=data["super_large_net"],
            large_net=data["large_net"],
            medium_net=data["medium_net"],
            small_net=data["small_net"]
        )

    async def get_market_sentiment(self) -> MarketSentiment:
        """获取市场情绪数据"""
        overview = await eastmoney_api.get_market_overview()
        north_flow = await eastmoney_api.get_north_flow()

        return MarketSentiment(
            date=datetime.now(),
            up_count=overview.get("up_count", 0),
            down_count=overview.get("down_count", 0),
            flat_count=overview.get("flat_count", 0),
            limit_up_count=overview.get("limit_up_count", 0),
            limit_down_count=overview.get("limit_down_count", 0),
            north_net_inflow=(north_flow.get("total_net", 0) / 100000000) if north_flow else 0
        )

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """搜索股票"""
        return await eastmoney_api.search_stock(keyword)

    def _load_historical_quotes(self):
        """从文件加载历史行情"""
        if os.path.exists(self.historical_file):
            try:
                with open(self.historical_file, "r", encoding="utf-8") as f:
                    self.historical_quotes = json.load(f)
            except Exception as e:
                print(f"加载历史行情失败: {e}")
                self.historical_quotes = {}

    def _save_historical_quotes(self):
        """保存历史行情到文件"""
        try:
            with open(self.historical_file, "w", encoding="utf-8") as f:
                json.dump(self.historical_quotes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史行情失败: {e}")

    def _save_historical_quote(self, code: str, quote_data: Dict[str, Any]):
        """保存单只股票的历史行情"""
        today = datetime.now().strftime("%Y-%m-%d")
        if code not in self.historical_quotes:
            self.historical_quotes[code] = {}

        self.historical_quotes[code][today] = quote_data
        self._save_historical_quotes()

    def _get_historical_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """获取历史行情（最近的一次）"""
        if code not in self.historical_quotes:
            return None

        # 获取最新日期的数据
        dates = sorted(self.historical_quotes[code].keys(), reverse=True)
        if dates:
            return self.historical_quotes[code][dates[0]]
        return None

    async def get_quote_with_fallback(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取行情，支持fallback到历史数据
        如果当前不是交易时间，返回缓存的历史数据
        """
        now = datetime.now()
        is_trading = await trading_calendar.is_trading_hours(now)

        if is_trading:
            # 交易时间，获取实时数据
            quote = await eastmoney_api.get_stock_quote(code)
            if not quote:
                # 尝试备用源
                quote = await biying_api.get_stock_quote(code)
                
            if quote:
                # 保存到历史快照
                self._save_historical_quote(code, quote)
                return quote

        # 非交易时间或获取失败，返回历史数据
        historical = self._get_historical_quote(code)
        if historical:
            return historical

        # 如果历史数据也没有，尝试获取最新数据
        quote = await eastmoney_api.get_stock_quote(code)
        if not quote:
            quote = await biying_api.get_stock_quote(code)
        return quote

    async def save_daily_snapshot(self):
        """
        保存每日行情快照（定时任务调用）
        """
        try:
            all_codes = list(self.watch_list.keys())
            if not all_codes:
                return

            quotes = await eastmoney_api.get_batch_quotes(all_codes)
            for quote in quotes:
                self._save_historical_quote(quote['code'], quote)

            print(f"[快照] 已保存 {len(quotes)} 只股票行情快照")
        except Exception as e:
            print(f"保存行情快照失败: {e}")

    async def get_default_indices_quotes(self) -> List[Dict[str, Any]]:
        """
        获取默认股指行情
        """
        codes = [idx["code"] for idx in DEFAULT_INDICES]
        return await eastmoney_api.get_batch_quotes(codes)

    async def get_commodities_quotes(self) -> List[Dict[str, Any]]:
        """
        获取大宗商品行情
        """
        results = []
        for commodity in DEFAULT_COMMODITIES:
            quote = await eastmoney_api.get_futures_quote(commodity["code"])
            if quote:
                quote["unit"] = commodity["unit"]
                quote["name"] = commodity["name"]
                results.append(quote)

        return results


# 创建全局服务实例
stock_service = StockService()
