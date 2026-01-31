"""东方财富 API 封装"""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
import os


class EastMoneyAPI:
    """东方财富数据接口"""

    # 行情接口
    QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    # 批量行情接口
    BATCH_QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    # 资金流向接口
    CAPITAL_FLOW_URL = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    # 实时资金流向
    REALTIME_FLOW_URL = "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
    # 市场概况
    MARKET_OVERVIEW_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    # 北向资金
    NORTH_FLOW_URL = "https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
    # 股票搜索
    SEARCH_URL = "https://searchapi.eastmoney.com/api/suggest/get"
    # K线数据接口
    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    def __init__(self):
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """延迟初始化 HTTP 客户端（禁用代理）"""
        if self._client is None:
            # 清除代理环境变量以避免 SOCKS 代理问题
            for key in ['ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy',
                       'HTTPS_PROXY', 'https_proxy']:
                os.environ.pop(key, None)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
            self._client = httpx.AsyncClient(timeout=10.0, headers=headers, trust_env=False)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def get_market_code(code: str) -> str:
        """
        根据股票代码获取市场标识
        返回格式: 1.600000 或 0.000001
        """
        code = code.strip()
        # 去除可能的后缀
        code = re.sub(r'\.(SH|SZ|BJ|sh|sz|bj)$', '', code)

        # 特殊指数处理 (上海指数)
        # 000001(上证指数), 000300(沪深300), 000016(上证50), 000688(科创50), 000905(中证500), 000852(中证1000)
        sh_indices = ['000001', '000300', '000016', '000688', '000905', '000852']
        if code in sh_indices:
            return f"1.{code}"

        # 判断市场
        if code.startswith('6') or code.startswith('9'):
            # 上海市场
            return f"1.{code}"
        elif code.startswith('0') or code.startswith('2') or code.startswith('3'):
            # 深圳市场
            return f"0.{code}"
        elif code.startswith('4') or code.startswith('8'):
            # 北交所
            return f"0.{code}"
        elif code.startswith('5'):
            # 上海ETF
            return f"1.{code}"
        elif code.startswith('1'):
            # 可能是深圳ETF或上海国债
            if code.startswith('159') or code.startswith('150'):
                return f"0.{code}"
            return f"1.{code}"
        else:
            # 默认深圳
            return f"0.{code}"

    @staticmethod
    def get_futures_code(symbol: str) -> str:
        """
        获取期货市场代码
        symbol: au(黄金), sc(原油), rb(螺纹钢)等
        返回: 113.au0 (上期所主力合约，0表示主力)
        """
        symbol = symbol.lower().strip()

        # 期货市场代码映射
        futures_markets = {
            "au": "113",  # 上期所黄金
            "sc": "142",  # 上海国际能源交易中心原油
            "rb": "113",  # 上期所螺纹钢
            "cu": "113",  # 上期所铜
            "ag": "113",  # 上期所白银
            "al": "113",  # 上期所铝
            "zn": "113",  # 上期所锌
        }

        market = futures_markets.get(symbol, "113")
        # 主力合约代码：品种+0
        return f"{market}.{symbol}0"

    async def get_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票实时行情
        """
        secid = self.get_market_code(code)
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f168,f169,f170",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(self.QUOTE_URL, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return None

            d = data["data"]
            return {
                "code": d.get("f57", code),
                "name": d.get("f58", ""),
                "price": d.get("f43", 0) / 100 if d.get("f43") else 0,
                "change": d.get("f169", 0) / 100 if d.get("f169") else 0,
                "change_percent": d.get("f170", 0) / 100 if d.get("f170") else 0,
                "open_price": d.get("f46", 0) / 100 if d.get("f46") else 0,
                "high_price": d.get("f44", 0) / 100 if d.get("f44") else 0,
                "low_price": d.get("f45", 0) / 100 if d.get("f45") else 0,
                "pre_close": d.get("f60", 0) / 100 if d.get("f60") else 0,
                "volume": d.get("f47", 0),  # 成交量（手）
                "amount": d.get("f48", 0),  # 成交额
                "turnover_rate": d.get("f168", 0) / 100 if d.get("f168") else 0,
                "pe_ratio": d.get("f162", 0) / 100 if d.get("f162") else None,
                "total_value": d.get("f116", 0) if d.get("f116") else None,  # 总市值
                "flow_value": d.get("f117", 0) if d.get("f117") else None,  # 流通市值
                "update_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取行情失败 {code}: {e}")
            return None

    async def get_batch_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取股票行情
        """
        if not codes:
            return []

        secids = ",".join([self.get_market_code(code) for code in codes])
        params = {
            "fltt": 2,
            "secids": secids,
            "fields": "f12,f13,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18,f8,f9,f20,f21",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(self.BATCH_QUOTE_URL, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return []

            results = []
            for item in data["data"].get("diff", []):
                results.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "change_percent": item.get("f3", 0),
                    "change": item.get("f4", 0),
                    "volume": item.get("f5", 0),
                    "amount": item.get("f6", 0),
                    "high_price": item.get("f15", 0),
                    "low_price": item.get("f16", 0),
                    "open_price": item.get("f17", 0),
                    "pre_close": item.get("f18", 0),
                    "turnover_rate": item.get("f8", 0),
                    "pe_ratio": item.get("f9", 0) if item.get("f9") else None,
                    "total_value": item.get("f20", 0),
                    "flow_value": item.get("f21", 0),
                    "update_time": datetime.now().isoformat()
                })
            return results
        except Exception as e:
            print(f"批量获取行情失败: {e}")
            return []

    async def get_capital_flow(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取个股资金流向
        """
        secid = self.get_market_code(code)
        params = {
            "secid": secid,
            "lmt": 1,
            "klt": 101,  # 日线
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(self.CAPITAL_FLOW_URL, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return None

            klines = data["data"].get("klines", [])
            if not klines:
                return None

            # 解析最新一条数据
            # 格式: 日期,主力净流入,小单净流入,中单净流入,大单净流入,超大单净流入
            latest = klines[-1].split(",")
            return {
                "code": code,
                "name": data["data"].get("name", ""),
                "main_net_inflow": float(latest[1]) if len(latest) > 1 else 0,
                "small_net": float(latest[2]) if len(latest) > 2 else 0,
                "medium_net": float(latest[3]) if len(latest) > 3 else 0,
                "large_net": float(latest[4]) if len(latest) > 4 else 0,
                "super_large_net": float(latest[5]) if len(latest) > 5 else 0,
                "update_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取资金流向失败 {code}: {e}")
            return None

    async def get_north_flow(self) -> Optional[Dict[str, Any]]:
        """
        获取北向资金数据
        """
        params = {
            "fields1": "f1,f2,f3,f4",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(self.NORTH_FLOW_URL, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return None

            d = data["data"]
            return {
                "sh_net": d.get("s2n", 0),  # 沪股通净流入
                "sz_net": d.get("n2s", 0),  # 深股通净流入
                "total_net": (d.get("s2n", 0) or 0) + (d.get("n2s", 0) or 0),
                "update_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取北向资金失败: {e}")
            return None

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """
        搜索股票
        """
        params = {
            "input": keyword,
            "type": 14,
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": 10
        }

        try:
            resp = await self.client.get(self.SEARCH_URL, params=params)
            data = resp.json()

            results = []
            for item in data.get("QuotationCodeTable", {}).get("Data", []):
                results.append({
                    "code": item.get("Code", ""),
                    "name": item.get("Name", ""),
                    "market": item.get("MktNum", ""),
                    "type": item.get("SecurityTypeName", "")
                })
            return results
        except Exception as e:
            print(f"搜索股票失败: {e}")
            return []

    async def get_market_overview(self) -> Dict[str, Any]:
        """
        获取市场概况（上涨/下跌家数等）
        """
        # 获取沪深A股列表统计
        params = {
            "fltt": 2,
            "np": 1,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields": "f3",
            "pn": 1,
            "pz": 5000,
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # 沪深A股
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(self.MARKET_OVERVIEW_URL, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return {}

            stocks = data["data"].get("diff", [])
            up_count = 0
            down_count = 0
            flat_count = 0
            limit_up = 0
            limit_down = 0

            for stock in stocks:
                change = stock.get("f3", 0)
                if change is None:
                    continue
                if change > 9.9:
                    limit_up += 1
                    up_count += 1
                elif change < -9.9:
                    limit_down += 1
                    down_count += 1
                elif change > 0:
                    up_count += 1
                elif change < 0:
                    down_count += 1
                else:
                    flat_count += 1

            return {
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "limit_up_count": limit_up,
                "limit_down_count": limit_down,
                "total_count": len(stocks),
                "update_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取市场概况失败: {e}")
            return {}

    async def get_stock_news(self, code: str, page_size: int = 10) -> List[Dict[str, Any]]:
        """
        获取个股新闻
        """
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        params = {
            "cb": "jQuery",
            "param": f'{{"uid":"","keyword":"{code}","type":["cmsArticleWebOld"],"client":"web","clientType":"web","clientVersion":"curr","param":{{"cmsArticleWebOld":{{"searchScope":"default","sort":"default","pageIndex":1,"pageSize":{page_size},"preTag":"<em>","postTag":"</em>"}}}}}}',
        }

        try:
            resp = await self.client.get(url, params=params)
            text = resp.text
            # 解析 JSONP 响应
            json_str = text[text.index('(') + 1:text.rindex(')')]
            import json
            data = json.loads(json_str)

            results = []
            articles = data.get("result", {}).get("cmsArticleWebOld", [])
            for article in articles:
                results.append({
                    "title": article.get("title", "").replace("<em>", "").replace("</em>", ""),
                    "content": article.get("content", "")[:500] if article.get("content") else "",
                    "url": article.get("url", ""),
                    "source": article.get("mediaName", ""),
                    "date": article.get("date", "")
                })
            return results
        except Exception as e:
            print(f"获取新闻失败 {code}: {e}")
            return []

    async def get_stock_announcements(self, code: str, page_size: int = 10) -> List[Dict[str, Any]]:
        """
        获取个股公告
        """
        # 判断市场
        if code.startswith('6'):
            market = "sh"
        else:
            market = "sz"

        url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        params = {
            "sr": -1,
            "page_size": page_size,
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
            "stock_list": f"{code}",
            "f_node": 0,
            "s_node": 0
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            results = []
            for item in data.get("data", {}).get("list", []):
                results.append({
                    "title": item.get("title", ""),
                    "code": item.get("codes", [{}])[0].get("stock_code", code) if item.get("codes") else code,
                    "name": item.get("codes", [{}])[0].get("short_name", "") if item.get("codes") else "",
                    "date": item.get("notice_date", ""),
                    "url": f"https://data.eastmoney.com/notices/detail/{code}/{item.get('art_code', '')}.html"
                })
            return results
        except Exception as e:
            print(f"获取公告失败 {code}: {e}")
            return []

    async def get_futures_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取期货实时行情
        symbol: au(黄金), sc(原油), rb(螺纹钢)等
        """
        secid = self.get_futures_code(symbol)
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f169,f170",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(self.QUOTE_URL, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return None

            d = data["data"]
            return {
                "code": symbol.upper(),
                "name": d.get("f58", ""),
                "price": d.get("f43", 0) / 100 if d.get("f43") else 0,
                "change": d.get("f169", 0) / 100 if d.get("f169") else 0,
                "change_percent": d.get("f170", 0) / 100 if d.get("f170") else 0,
                "open_price": d.get("f46", 0) / 100 if d.get("f46") else 0,
                "high_price": d.get("f44", 0) / 100 if d.get("f44") else 0,
                "low_price": d.get("f45", 0) / 100 if d.get("f45") else 0,
                "volume": d.get("f47", 0),
                "amount": d.get("f48", 0),
                "update_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取期货行情失败 {symbol}: {e}")
            return None

    async def get_kline_data(self, code: str, days: int = 60) -> List[Dict[str, Any]]:
        """
        获取K线历史数据
        code: 股票代码
        days: 获取天数（最多250天）
        返回字段：日期、开高低收、成交量、成交额、振幅、涨跌幅、换手率
        """
        secid = self.get_market_code(code)
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": 101,  # 日K
            "fqt": 1,    # 前复权
            "beg": 0,
            "end": 20500101,
            "lmt": min(days, 250),  # 限制最多250天
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(self.KLINE_URL, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return []

            klines = data["data"].get("klines", [])
            results = []

            for kline in klines:
                # 格式: 日期,收盘,开盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
                parts = kline.split(",")
                if len(parts) >= 11:
                    results.append({
                        "date": parts[0],
                        "close": float(parts[2]),
                        "open": float(parts[1]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": float(parts[5]),
                        "amount": float(parts[6]),
                        "amplitude": float(parts[7]),  # 振幅
                        "change_percent": float(parts[8]),
                        "turnover_rate": float(parts[10]) if len(parts) > 10 else 0
                    })

            return results
        except Exception as e:
            print(f"获取K线数据失败 {code}: {e}")
            return []


# 创建全局实例
eastmoney_api = EastMoneyAPI()
