"""美股数据接口封装"""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import re
import os


class USStockAPI:
    """美股数据接口 - 使用Yahoo Finance"""

    # Yahoo Finance API endpoints
    QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
    CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

    # 中概股映射
    CHINA_ADR_LIST = [
        {"symbol": "BABA", "name": "阿里巴巴"},
        {"symbol": "JD", "name": "京东"},
        {"symbol": "PDD", "name": "拼多多"},
        {"symbol": "BIDU", "name": "百度"},
        {"symbol": "NIO", "name": "蔚来汽车"},
        {"symbol": "XPEV", "name": "小鹏汽车"},
        {"symbol": "LI", "name": "理想汽车"},
        {"symbol": "BILI", "name": "哔哩哔哩"},
        {"symbol": "TME", "name": "腾讯音乐"},
        {"symbol": "IQ", "name": "爱奇艺"},
        {"symbol": "NTES", "name": "网易"},
        {"symbol": "TAL", "name": "好未来"},
        {"symbol": "EDU", "name": "新东方"},
        {"symbol": "VNET", "name": "世纪互联"},
        {"symbol": "FUTU", "name": "富途控股"},
        {"symbol": "TIGR", "name": "老虎证券"},
        {"symbol": "ZH", "name": "知乎"},
        {"symbol": "YMM", "name": "满帮集团"},
        {"symbol": "DIDI", "name": "滴滴"},
        {"symbol": "LCID", "name": "Lucid Motors"}
    ]

    # 热门美股列表
    POPULAR_US_STOCKS = [
        {"symbol": "AAPL", "name": "苹果"},
        {"symbol": "MSFT", "name": "微软"},
        {"symbol": "GOOGL", "name": "谷歌"},
        {"symbol": "AMZN", "name": "亚马逊"},
        {"symbol": "META", "name": "Meta"},
        {"symbol": "NVDA", "name": "英伟达"},
        {"symbol": "TSLA", "name": "特斯拉"},
        {"symbol": "AMD", "name": "AMD"},
        {"symbol": "INTC", "name": "英特尔"},
        {"symbol": "NFLX", "name": "奈飞"}
    ]

    # 主要美股指数
    US_INDICES = [
        {"symbol": "^DJI", "name": "道琼斯指数"},
        {"symbol": "^GSPC", "name": "标普500"},
        {"symbol": "^IXIC", "name": "纳斯达克"},
        {"symbol": "^RUT", "name": "罗素2000"}
    ]

    def __init__(self):
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """延迟初始化 HTTP 客户端"""
        if self._client is None:
            # 清除代理环境变量
            for key in ['ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy',
                       'HTTPS_PROXY', 'https_proxy']:
                os.environ.pop(key, None)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            self._client = httpx.AsyncClient(timeout=15.0, headers=headers, trust_env=False)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def is_us_stock(symbol: str) -> bool:
        """
        判断是否是美股代码
        美股代码通常是1-5个大写字母
        """
        symbol = symbol.upper().strip()
        # 美股代码：1-5个字母，可能带有.后缀
        if re.match(r'^[A-Z]{1,5}(\.[A-Z]+)?$', symbol):
            return True
        # 美股指数：以^开头
        if symbol.startswith('^'):
            return True
        return False

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取美股实时行情
        """
        symbol = symbol.upper().strip()

        params = {
            "symbols": symbol,
            "fields": "regularMarketPrice,regularMarketChange,regularMarketChangePercent,regularMarketOpen,regularMarketDayHigh,regularMarketDayLow,regularMarketPreviousClose,regularMarketVolume,marketCap,trailingPE,forwardPE,priceToBook,fiftyTwoWeekHigh,fiftyTwoWeekLow,averageVolume,shortName,longName,currency"
        }

        try:
            resp = await self.client.get(self.QUOTE_URL, params=params)
            data = resp.json()

            result = data.get("quoteResponse", {}).get("result", [])
            if not result:
                return None

            quote = result[0]
            return {
                "symbol": quote.get("symbol", symbol),
                "name": quote.get("shortName", "") or quote.get("longName", ""),
                "price": quote.get("regularMarketPrice", 0),
                "change": quote.get("regularMarketChange", 0),
                "change_percent": quote.get("regularMarketChangePercent", 0),
                "open_price": quote.get("regularMarketOpen", 0),
                "high_price": quote.get("regularMarketDayHigh", 0),
                "low_price": quote.get("regularMarketDayLow", 0),
                "pre_close": quote.get("regularMarketPreviousClose", 0),
                "volume": quote.get("regularMarketVolume", 0),
                "market_cap": quote.get("marketCap", 0),
                "pe_ratio": quote.get("trailingPE", 0),
                "pb_ratio": quote.get("priceToBook", 0),
                "52week_high": quote.get("fiftyTwoWeekHigh", 0),
                "52week_low": quote.get("fiftyTwoWeekLow", 0),
                "avg_volume": quote.get("averageVolume", 0),
                "currency": quote.get("currency", "USD"),
                "market": "US",
                "update_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取美股行情失败 {symbol}: {e}")
            return None

    async def get_batch_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取美股行情
        """
        if not symbols:
            return []

        symbols_str = ",".join([s.upper().strip() for s in symbols])

        params = {
            "symbols": symbols_str,
            "fields": "regularMarketPrice,regularMarketChange,regularMarketChangePercent,regularMarketVolume,marketCap,shortName"
        }

        try:
            resp = await self.client.get(self.QUOTE_URL, params=params)
            data = resp.json()

            results = []
            for quote in data.get("quoteResponse", {}).get("result", []):
                results.append({
                    "symbol": quote.get("symbol", ""),
                    "name": quote.get("shortName", ""),
                    "price": quote.get("regularMarketPrice", 0),
                    "change_percent": quote.get("regularMarketChangePercent", 0),
                    "change": quote.get("regularMarketChange", 0),
                    "volume": quote.get("regularMarketVolume", 0),
                    "market_cap": quote.get("marketCap", 0),
                    "market": "US",
                    "update_time": datetime.now().isoformat()
                })
            return results
        except Exception as e:
            print(f"批量获取美股行情失败: {e}")
            return []

    async def get_kline_data(self, symbol: str, days: int = 60) -> List[Dict[str, Any]]:
        """
        获取美股K线数据
        """
        symbol = symbol.upper().strip()

        # 计算时间范围
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())

        params = {
            "symbol": symbol,
            "period1": start_time,
            "period2": end_time,
            "interval": "1d",  # 日K
            "includePrePost": "false"
        }

        try:
            resp = await self.client.get(f"{self.CHART_URL}/{symbol}", params=params)
            data = resp.json()

            chart = data.get("chart", {}).get("result", [])
            if not chart:
                return []

            chart_data = chart[0]
            timestamps = chart_data.get("timestamp", [])
            indicators = chart_data.get("indicators", {})
            quote = indicators.get("quote", [{}])[0]
            adjclose = indicators.get("adjclose", [{}])[0].get("adjclose", [])

            results = []
            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])

            for i, ts in enumerate(timestamps):
                if i >= len(closes) or closes[i] is None:
                    continue

                date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                prev_close = closes[i - 1] if i > 0 and closes[i - 1] else closes[i]
                change_pct = ((closes[i] - prev_close) / prev_close * 100) if prev_close else 0

                results.append({
                    "date": date,
                    "open": opens[i] if i < len(opens) and opens[i] else 0,
                    "high": highs[i] if i < len(highs) and highs[i] else 0,
                    "low": lows[i] if i < len(lows) and lows[i] else 0,
                    "close": closes[i] if closes[i] else 0,
                    "volume": volumes[i] if i < len(volumes) and volumes[i] else 0,
                    "adj_close": adjclose[i] if i < len(adjclose) and adjclose[i] else closes[i],
                    "change_percent": round(change_pct, 2)
                })

            return results
        except Exception as e:
            print(f"获取美股K线失败 {symbol}: {e}")
            return []

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """
        搜索美股
        """
        params = {
            "q": keyword,
            "quotesCount": 10,
            "newsCount": 0,
            "enableFuzzyQuery": "true",
            "quotesQueryId": "tss_match_phrase_query"
        }

        try:
            resp = await self.client.get(self.SEARCH_URL, params=params)
            data = resp.json()

            results = []
            for quote in data.get("quotes", []):
                # 只返回股票类型
                if quote.get("quoteType") in ["EQUITY", "ETF", "INDEX"]:
                    results.append({
                        "symbol": quote.get("symbol", ""),
                        "name": quote.get("shortname", "") or quote.get("longname", ""),
                        "exchange": quote.get("exchange", ""),
                        "type": quote.get("quoteType", "")
                    })
            return results
        except Exception as e:
            print(f"搜索美股失败: {e}")
            return []

    async def get_us_indices(self) -> List[Dict[str, Any]]:
        """
        获取美股主要指数
        """
        symbols = [idx["symbol"] for idx in self.US_INDICES]
        quotes = await self.get_batch_quotes(symbols)

        # 合并名称
        for quote in quotes:
            for idx in self.US_INDICES:
                if quote["symbol"] == idx["symbol"]:
                    quote["name"] = idx["name"]
                    break

        return quotes

    async def get_china_adr(self) -> List[Dict[str, Any]]:
        """
        获取中概股行情
        """
        symbols = [stock["symbol"] for stock in self.CHINA_ADR_LIST]
        quotes = await self.get_batch_quotes(symbols)

        # 合并中文名称
        for quote in quotes:
            for stock in self.CHINA_ADR_LIST:
                if quote["symbol"] == stock["symbol"]:
                    quote["cn_name"] = stock["name"]
                    break

        return quotes

    async def get_popular_us_stocks(self) -> List[Dict[str, Any]]:
        """
        获取热门美股行情
        """
        symbols = [stock["symbol"] for stock in self.POPULAR_US_STOCKS]
        quotes = await self.get_batch_quotes(symbols)

        # 合并中文名称
        for quote in quotes:
            for stock in self.POPULAR_US_STOCKS:
                if quote["symbol"] == stock["symbol"]:
                    quote["cn_name"] = stock["name"]
                    break

        return quotes


# 创建全局实例
us_stock_api = USStockAPI()
