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
        返回格式: 1.600000 (沪) 或 0.000001 (深) 或 116.01211 (港)
        """
        code = code.strip()
        # 去除可能的后缀
        code = re.sub(r'\.(SH|SZ|BJ|HK|sh|sz|bj|hk)$', '', code)

        # 港股判断：5位数字或以01、02、03、06、07、08、09开头的代码
        # 港股代码通常是5位数字，如01211、00700、81211等
        if len(code) == 5 and code.isdigit():
            # 可能是港股，使用116（港股通）市场代码
            return f"116.{code}"

        # 特殊指数处理 (上海指数)
        # 000001(上证指数), 000300(沪深300), 000016(上证50), 000688(科创50), 000905(中证500), 000852(中证1000)
        sh_indices = ['000001', '000300', '000016', '000688', '000905', '000852']
        if code in sh_indices:
            return f"1.{code}"

        # A股判断
        if code.startswith('6') or code.startswith('9'):
            # 上海市场
            return f"1.{code}"
        elif code.startswith('0') or code.startswith('2') or code.startswith('3'):
            # 深圳市场 (排除5位数字的情况)
            if len(code) == 6:
                return f"0.{code}"
            # 5位数字但以0开头可能是港股
            elif len(code) == 5:
                return f"116.{code}"
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

    async def get_north_flow_minute(self) -> Optional[Dict[str, Any]]:
        """
        获取北向资金日内分时数据
        返回今日分钟级别的资金流入数据
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

            # 解析分时数据
            sh_data = []  # 沪股通
            sz_data = []  # 深股通

            # 解析沪股通分时 (s2n)
            if d.get("s2n"):
                for item in d["s2n"]:
                    parts = item.split(",")
                    if len(parts) >= 3:
                        sh_data.append({
                            "time": parts[0],
                            "net_inflow": float(parts[1]) if parts[1] != "-" else 0,  # 净流入
                            "buy": float(parts[2]) if parts[2] != "-" else 0  # 买入
                        })

            # 解析深股通分时 (n2s)
            if d.get("n2s"):
                for item in d["n2s"]:
                    parts = item.split(",")
                    if len(parts) >= 3:
                        sz_data.append({
                            "time": parts[0],
                            "net_inflow": float(parts[1]) if parts[1] != "-" else 0,
                            "buy": float(parts[2]) if parts[2] != "-" else 0
                        })

            # 合并计算总北向资金
            total_data = []
            max_len = max(len(sh_data), len(sz_data))
            for i in range(max_len):
                sh_item = sh_data[i] if i < len(sh_data) else {"time": "", "net_inflow": 0, "buy": 0}
                sz_item = sz_data[i] if i < len(sz_data) else {"time": "", "net_inflow": 0, "buy": 0}
                total_data.append({
                    "time": sh_item["time"] or sz_item["time"],
                    "net_inflow": sh_item["net_inflow"] + sz_item["net_inflow"],
                    "sh_inflow": sh_item["net_inflow"],
                    "sz_inflow": sz_item["net_inflow"]
                })

            # 最新值
            latest_sh = sh_data[-1]["net_inflow"] if sh_data else 0
            latest_sz = sz_data[-1]["net_inflow"] if sz_data else 0

            return {
                "sh_net": latest_sh,
                "sz_net": latest_sz,
                "total_net": latest_sh + latest_sz,
                "minute_data": total_data,
                "sh_minute": sh_data,
                "sz_minute": sz_data,
                "update_time": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取北向资金分时数据失败: {e}")
            return None

    async def get_north_flow_history(self, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        获取北向资金历史数据
        days: 获取的天数
        """
        # 北向资金历史数据接口
        url = "https://push2his.eastmoney.com/api/qt/kamt.kline/get"
        params = {
            "fields1": "f1,f2,f3,f4,f5",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": 101,  # 日K
            "lmt": days,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return None

            d = data["data"]
            history = []

            # 解析数据 (s2n是沪股通到陆, n2s是深股通到陆)
            sh_data = {}
            sz_data = {}

            if d.get("s2n"):
                for item in d["s2n"]:
                    parts = item.split(",")
                    if len(parts) >= 4:
                        date = parts[0]
                        sh_data[date] = {
                            "net_inflow": float(parts[1]) if parts[1] != "-" else 0,
                            "buy": float(parts[2]) if parts[2] != "-" else 0,
                            "sell": float(parts[3]) if parts[3] != "-" else 0
                        }

            if d.get("n2s"):
                for item in d["n2s"]:
                    parts = item.split(",")
                    if len(parts) >= 4:
                        date = parts[0]
                        sz_data[date] = {
                            "net_inflow": float(parts[1]) if parts[1] != "-" else 0,
                            "buy": float(parts[2]) if parts[2] != "-" else 0,
                            "sell": float(parts[3]) if parts[3] != "-" else 0
                        }

            # 合并数据
            all_dates = sorted(set(sh_data.keys()) | set(sz_data.keys()))
            for date in all_dates:
                sh = sh_data.get(date, {"net_inflow": 0, "buy": 0, "sell": 0})
                sz = sz_data.get(date, {"net_inflow": 0, "buy": 0, "sell": 0})
                history.append({
                    "date": date,
                    "sh_net": sh["net_inflow"],
                    "sz_net": sz["net_inflow"],
                    "total_net": sh["net_inflow"] + sz["net_inflow"],
                    "sh_buy": sh["buy"],
                    "sz_buy": sz["buy"],
                    "sh_sell": sh["sell"],
                    "sz_sell": sz["sell"]
                })

            return history

        except Exception as e:
            print(f"获取北向资金历史数据失败: {e}")
            return None

    async def get_north_top_holdings(self, market: str = "all", count: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        获取北向资金持股排行
        market: sh(沪股通), sz(深股通), all(全部)
        count: 返回数量
        """
        # 北向持股排行接口
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        # 市场筛选
        if market == "sh":
            filter_str = '(MARKET_CODE="001")'
        elif market == "sz":
            filter_str = '(MARKET_CODE="003")'
        else:
            filter_str = ""

        params = {
            "sortColumns": "ADD_MARKET_CAP",
            "sortTypes": "-1",
            "pageSize": count,
            "pageNumber": 1,
            "reportName": "RPT_MUTUAL_HOLDSTOCKNORTH_STA",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": filter_str
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return None

            holdings = []
            for item in data["result"].get("data", [])[:count]:
                holdings.append({
                    "code": item.get("SECURITY_CODE", ""),
                    "name": item.get("SECURITY_NAME_ABBR", ""),
                    "hold_shares": item.get("HOLD_SHARES", 0),  # 持股数量
                    "hold_market_cap": item.get("HOLD_MARKET_CAP", 0),  # 持股市值
                    "hold_ratio": item.get("HOLD_RATIO", 0),  # 持股比例
                    "change_shares": item.get("ADD_SHARES_AMP", 0),  # 增减持股数
                    "change_ratio": item.get("ADD_SHARES_REPAMP", 0),  # 增减比例
                    "close_price": item.get("CLOSE_PRICE", 0),
                    "change_percent": item.get("CHANGE_RATE", 0)
                })

            return holdings

        except Exception as e:
            print(f"获取北向持股排行失败: {e}")
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

    async def get_market_news(self, category: str = "stock", page_size: int = 100) -> List[Dict[str, Any]]:
        """
        获取市场新闻（用于舆情分析）
        category: stock(股票), market(大盘), finance(财经)
        page_size: 新闻数量，最多100条
        """
        # 东方财富财经新闻API
        url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"

        # 不同类别对应不同的列ID
        column_ids = {
            "stock": "350,351",     # 股票新闻
            "market": "352",        # 大盘分析
            "finance": "353,354",   # 财经新闻
            "all": "350,351,352,353,354"  # 全部
        }

        params = {
            "client": "web",
            "biz": "web_news_col",
            "column": column_ids.get(category, column_ids["all"]),
            "pageSize": min(page_size, 100),
            "page": 1,
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            results = []
            articles = data.get("data", {}).get("list", [])
            for article in articles:
                results.append({
                    "title": article.get("title", ""),
                    "content": article.get("digest", ""),
                    "url": article.get("url", "") or f"https://finance.eastmoney.com/a/{article.get('code', '')}.html",
                    "source": article.get("source", "东方财富"),
                    "date": article.get("showTime", ""),
                    "category": category
                })
            return results
        except Exception as e:
            print(f"获取市场新闻失败: {e}")
            # 尝试备用API
            return await self._get_market_news_fallback(category, page_size)

    async def _get_market_news_fallback(self, category: str, page_size: int) -> List[Dict[str, Any]]:
        """市场新闻备用获取方法"""
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        keywords = {
            "stock": "A股",
            "market": "大盘",
            "finance": "财经",
            "all": "股市"
        }
        keyword = keywords.get(category, "股市")

        params = {
            "cb": "jQuery",
            "param": f'{{"uid":"","keyword":"{keyword}","type":["cmsArticleWebOld"],"client":"web","clientType":"web","clientVersion":"curr","param":{{"cmsArticleWebOld":{{"searchScope":"default","sort":"time","pageIndex":1,"pageSize":{min(page_size, 100)},"preTag":"","postTag":""}}}}}}',
        }

        try:
            resp = await self.client.get(url, params=params)
            text = resp.text
            json_str = text[text.index('(') + 1:text.rindex(')')]
            import json
            data = json.loads(json_str)

            results = []
            articles = data.get("result", {}).get("cmsArticleWebOld", [])
            for article in articles:
                results.append({
                    "title": article.get("title", "").replace("<em>", "").replace("</em>", ""),
                    "content": article.get("content", "")[:200] if article.get("content") else "",
                    "url": article.get("url", ""),
                    "source": article.get("mediaName", "东方财富"),
                    "date": article.get("date", ""),
                    "category": category
                })
            return results
        except Exception as e:
            print(f"备用新闻API失败: {e}")
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
        days: 获取天数（API会返回全部历史数据，然后取最近N天）
        返回字段：日期、开高低收、成交量、成交额、振幅、涨跌幅、换手率
        """
        secid = self.get_market_code(code)
        # 注意：东财API的lmt参数似乎会被忽略，总是返回全部历史数据
        # 我们在客户端进行截取
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": 101,  # 日K
            "fqt": 1,    # 前复权
            "beg": 0,
            "end": 20500101,
            "lmt": min(days, 10000),  # 设置较大的值以获取足够的历史数据
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

            # 取最近N天的数据
            if len(results) > days:
                results = results[-days:]

            return results
        except Exception as e:
            print(f"获取K线数据失败 {code}: {e}")
            return []

    async def get_sector_list(self, sector_type: str = "industry") -> List[Dict[str, Any]]:
        """
        获取板块列表
        sector_type: industry(行业板块), concept(概念板块), area(地域板块)
        """
        # 板块类型映射
        type_map = {
            "industry": "m:90+t:2",  # 行业板块
            "concept": "m:90+t:3",   # 概念板块
            "area": "m:90+t:1"       # 地域板块
        }

        fs = type_map.get(sector_type, type_map["industry"])

        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 500,
            "po": 1,
            "np": 1,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs,
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f11,f62,f128,f136,f115,f152,f124,f107,f104,f105,f140,f141,f207,f208,f209,f222",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return []

            sectors = []
            for item in data["data"].get("diff", []):
                sectors.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "change_percent": item.get("f3", 0),
                    "change_amount": item.get("f4", 0),
                    "volume": item.get("f5", 0),
                    "turnover": item.get("f6", 0),
                    "amplitude": item.get("f7", 0),
                    "high": item.get("f15", 0),
                    "low": item.get("f16", 0),
                    "open": item.get("f17", 0),
                    "prev_close": item.get("f18", 0),
                    "total_market_cap": item.get("f20", 0),
                    "circulating_cap": item.get("f21", 0),
                    "turnover_rate": item.get("f8", 0),
                    "up_count": item.get("f104", 0),
                    "down_count": item.get("f105", 0),
                    "lead_stock": item.get("f140", ""),
                    "lead_change": item.get("f136", 0)
                })

            # 按涨跌幅排序
            sectors.sort(key=lambda x: x["change_percent"] or 0, reverse=True)
            return sectors

        except Exception as e:
            print(f"获取{sector_type}板块列表失败: {e}")
            return []

    async def get_sector_stocks(self, sector_code: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        获取板块成分股
        sector_code: 板块代码
        """
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": count,
            "po": 1,
            "np": 1,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": f"b:{sector_code}+f:!50",
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return []

            stocks = []
            for item in data["data"].get("diff", []):
                stocks.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "change_percent": item.get("f3", 0),
                    "change_amount": item.get("f4", 0),
                    "volume": item.get("f5", 0),
                    "turnover": item.get("f6", 0),
                    "amplitude": item.get("f7", 0),
                    "turnover_rate": item.get("f8", 0),
                    "pe_ratio": item.get("f9", 0),
                    "market_cap": item.get("f20", 0)
                })

            return stocks

        except Exception as e:
            print(f"获取板块成分股失败 {sector_code}: {e}")
            return []

    async def get_sector_flow(self, sector_type: str = "industry", count: int = 20) -> List[Dict[str, Any]]:
        """
        获取板块资金流向
        sector_type: industry(行业), concept(概念)
        """
        # 板块类型映射
        type_map = {
            "industry": "1",
            "concept": "2"
        }

        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": count,
            "po": 1,
            "np": 1,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": 2,
            "invt": 2,
            "fid": "f62",
            "fs": f"m:90+t:{type_map.get(sector_type, '1')}",
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124",
            "_": int(datetime.now().timestamp() * 1000)
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if data.get("rc") != 0 or not data.get("data"):
                return []

            sectors = []
            for item in data["data"].get("diff", []):
                sectors.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "change_percent": item.get("f3", 0),
                    "main_net_inflow": item.get("f62", 0),  # 主力净流入
                    "main_net_ratio": item.get("f184", 0),  # 主力净流入占比
                    "super_large_inflow": item.get("f66", 0),  # 超大单净流入
                    "large_inflow": item.get("f72", 0),  # 大单净流入
                    "medium_inflow": item.get("f78", 0),  # 中单净流入
                    "small_inflow": item.get("f84", 0),  # 小单净流入
                })

            # 按主力净流入排序
            sectors.sort(key=lambda x: x["main_net_inflow"] or 0, reverse=True)
            return sectors

        except Exception as e:
            print(f"获取板块资金流向失败: {e}")
            return []


    async def get_lhb_list(self, date: str = None) -> List[Dict[str, Any]]:
        """
        获取龙虎榜股票列表
        date: 日期，格式 YYYY-MM-DD，默认为最新交易日
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        # 如果没有指定日期，获取最新的
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        params = {
            "sortColumns": "SECURITY_CODE,TRADE_DATE",
            "sortTypes": "1,-1",
            "pageSize": 500,
            "pageNumber": 1,
            "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(TRADE_DATE>=\'{date}\')'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return []

            stocks = []
            seen_codes = set()

            for item in data["result"].get("data", []):
                code = item.get("SECURITY_CODE", "")
                if code in seen_codes:
                    continue
                seen_codes.add(code)

                stocks.append({
                    "date": item.get("TRADE_DATE", "")[:10],
                    "code": code,
                    "name": item.get("SECURITY_NAME_ABBR", ""),
                    "close": item.get("CLOSE_PRICE", 0),
                    "change_percent": item.get("CHANGE_RATE", 0),
                    "turnover_rate": item.get("TURNOVERRATE", 0),
                    "net_buy": item.get("NET_BUY_AMT", 0),  # 净买入额
                    "buy_amount": item.get("BUY_AMT", 0),   # 买入金额
                    "sell_amount": item.get("SELL_AMT", 0), # 卖出金额
                    "reason": item.get("EXPLANATION", ""),  # 上榜原因
                    "market": item.get("MARKET", "")
                })

            return stocks

        except Exception as e:
            print(f"获取龙虎榜列表失败: {e}")
            return []

    async def get_lhb_detail(self, code: str, date: str = None) -> Dict[str, Any]:
        """
        获取龙虎榜个股详情（买卖席位）
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        params = {
            "sortColumns": "NET_BUY_AMT",
            "sortTypes": "-1",
            "pageSize": 50,
            "pageNumber": 1,
            "reportName": "RPT_BILLBOARD_DAILYDETAILSBUY",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(TRADE_DATE>=\'{date}\')(SECURITY_CODE="{code}")'
        }

        try:
            # 获取买入席位
            resp = await self.client.get(url, params=params)
            buy_data = resp.json()

            # 获取卖出席位
            params["reportName"] = "RPT_BILLBOARD_DAILYDETAILSSELL"
            resp = await self.client.get(url, params=params)
            sell_data = resp.json()

            buy_list = []
            sell_list = []

            if buy_data.get("success") and buy_data.get("result"):
                for item in buy_data["result"].get("data", [])[:5]:
                    buy_list.append({
                        "rank": item.get("RANK", 0),
                        "trader": item.get("OPERATEDEPT_NAME", ""),
                        "buy_amount": item.get("BUY_AMT", 0),
                        "sell_amount": item.get("SELL_AMT", 0),
                        "net_amount": item.get("NET_BUY_AMT", 0),
                        "buy_ratio": item.get("BUY_RATE", 0),
                        "reason": item.get("EXPLANATION", "")
                    })

            if sell_data.get("success") and sell_data.get("result"):
                for item in sell_data["result"].get("data", [])[:5]:
                    sell_list.append({
                        "rank": item.get("RANK", 0),
                        "trader": item.get("OPERATEDEPT_NAME", ""),
                        "buy_amount": item.get("BUY_AMT", 0),
                        "sell_amount": item.get("SELL_AMT", 0),
                        "net_amount": item.get("NET_BUY_AMT", 0),
                        "sell_ratio": item.get("SELL_RATE", 0),
                        "reason": item.get("EXPLANATION", "")
                    })

            return {
                "code": code,
                "date": date,
                "buy_seats": buy_list,
                "sell_seats": sell_list
            }

        except Exception as e:
            print(f"获取龙虎榜详情失败 {code}: {e}")
            return {"code": code, "date": date, "buy_seats": [], "sell_seats": []}

    async def get_hot_traders(self, days: int = 5) -> List[Dict[str, Any]]:
        """
        获取活跃游资/机构席位统计
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "sortColumns": "OPERATEDEPT_COUNT",
            "sortTypes": "-1",
            "pageSize": 50,
            "pageNumber": 1,
            "reportName": "RPT_OPERATEDEPT_ACTIVE_STA",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(STATISTICS_CYCLE="{days}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return []

            traders = []
            for item in data["result"].get("data", []):
                traders.append({
                    "name": item.get("OPERATEDEPT_NAME", ""),
                    "count": item.get("OPERATEDEPT_COUNT", 0),  # 上榜次数
                    "buy_amount": item.get("BUY_AMT", 0),
                    "sell_amount": item.get("SELL_AMT", 0),
                    "net_amount": item.get("NET_BUY_AMT", 0),
                    "win_rate": item.get("TOTAL_NETAMT_RATE", 0),  # 收益率
                    "stocks": item.get("STATISTICS_CYCLE", "")
                })

            return traders

        except Exception as e:
            print(f"获取活跃游资统计失败: {e}")
            return []


    async def get_finance_indicators(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票主要财务指标
        返回：每股收益、净资产收益率、毛利率、净利率、负债率等
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        # 判断市场
        if code.startswith('6'):
            market = "SH"
        elif code.startswith('0') or code.startswith('3'):
            market = "SZ"
        else:
            market = "SZ"

        params = {
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": 8,  # 获取最近8个季度
            "pageNumber": 1,
            "reportName": "RPT_DMSK_FN_ZCFZ",  # 主要财务指标
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(SECURITY_CODE="{code}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                # 尝试备用接口
                return await self._get_finance_indicators_v2(code)

            indicators = []
            for item in data["result"].get("data", []):
                indicators.append({
                    "report_date": item.get("REPORT_DATE", "")[:10] if item.get("REPORT_DATE") else "",
                    "report_type": item.get("REPORT_TYPE", ""),
                    "eps": item.get("EPSJB", 0),  # 每股收益
                    "bps": item.get("BPS", 0),  # 每股净资产
                    "roe": item.get("ROEJQ", 0),  # 净资产收益率
                    "gross_margin": item.get("XSMLL", 0),  # 毛利率
                    "net_margin": item.get("XSJLL", 0),  # 净利率
                    "debt_ratio": item.get("ZCFZL", 0),  # 资产负债率
                    "current_ratio": item.get("LD", 0),  # 流动比率
                    "quick_ratio": item.get("SD", 0),  # 速动比率
                })

            return {
                "code": code,
                "indicators": indicators
            }

        except Exception as e:
            print(f"获取财务指标失败 {code}: {e}")
            return await self._get_finance_indicators_v2(code)

    async def _get_finance_indicators_v2(self, code: str) -> Optional[Dict[str, Any]]:
        """
        备用财务指标获取方法 - 使用另一个API
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": 8,
            "pageNumber": 1,
            "reportName": "RPT_LICO_FN_CPD",  # 另一个财务指标接口
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(SECURITY_CODE="{code}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return None

            indicators = []
            for item in data["result"].get("data", []):
                indicators.append({
                    "report_date": item.get("REPORT_DATE", "")[:10] if item.get("REPORT_DATE") else "",
                    "report_type": self._get_report_type(item.get("REPORT_DATE", "")),
                    "eps": item.get("BASIC_EPS", 0),  # 每股收益
                    "bps": item.get("BPS", 0),  # 每股净资产
                    "roe": item.get("WEIGHTAVG_ROE", 0),  # 净资产收益率
                    "gross_margin": item.get("GROSSPROFIT_MARGIN", 0),  # 毛利率
                    "net_margin": item.get("NETPROFIT_MARGIN", 0),  # 净利率
                    "debt_ratio": item.get("DEBT_ASSET_RATIO", 0),  # 资产负债率
                    "revenue_yoy": item.get("TOTAL_OPERATE_INCOME_YOY", 0),  # 营收同比
                    "profit_yoy": item.get("PARENT_NETPROFIT_YOY", 0),  # 净利润同比
                })

            return {
                "code": code,
                "indicators": indicators
            }

        except Exception as e:
            print(f"备用财务指标API失败 {code}: {e}")
            return None

    def _get_report_type(self, date_str: str) -> str:
        """根据日期判断报告类型"""
        if not date_str:
            return ""
        month = date_str[5:7] if len(date_str) >= 7 else ""
        if month == "03":
            return "一季报"
        elif month == "06":
            return "半年报"
        elif month == "09":
            return "三季报"
        elif month == "12":
            return "年报"
        return ""

    async def get_income_statement(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取利润表数据
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": 8,
            "pageNumber": 1,
            "reportName": "RPT_LICO_FN_INCOME",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(SECURITY_CODE="{code}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return None

            statements = []
            for item in data["result"].get("data", []):
                statements.append({
                    "report_date": item.get("REPORT_DATE", "")[:10] if item.get("REPORT_DATE") else "",
                    "report_type": self._get_report_type(item.get("REPORT_DATE", "")),
                    "revenue": item.get("TOTAL_OPERATE_INCOME", 0),  # 营业总收入
                    "operating_cost": item.get("TOTAL_OPERATE_COST", 0),  # 营业总成本
                    "gross_profit": item.get("OPERATE_PROFIT", 0),  # 营业利润
                    "total_profit": item.get("TOTAL_PROFIT", 0),  # 利润总额
                    "net_profit": item.get("NETPROFIT", 0),  # 净利润
                    "parent_net_profit": item.get("PARENT_NETPROFIT", 0),  # 归母净利润
                    "rd_expense": item.get("RESEARCH_EXPENSE", 0),  # 研发费用
                    "finance_expense": item.get("FINANCE_EXPENSE", 0),  # 财务费用
                    "sale_expense": item.get("SALE_EXPENSE", 0),  # 销售费用
                    "manage_expense": item.get("MANAGE_EXPENSE", 0),  # 管理费用
                })

            return {
                "code": code,
                "statements": statements
            }

        except Exception as e:
            print(f"获取利润表失败 {code}: {e}")
            return None

    async def get_balance_sheet(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取资产负债表数据
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": 8,
            "pageNumber": 1,
            "reportName": "RPT_LICO_FN_BALANCE",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(SECURITY_CODE="{code}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return None

            sheets = []
            for item in data["result"].get("data", []):
                sheets.append({
                    "report_date": item.get("REPORT_DATE", "")[:10] if item.get("REPORT_DATE") else "",
                    "report_type": self._get_report_type(item.get("REPORT_DATE", "")),
                    "total_assets": item.get("TOTAL_ASSETS", 0),  # 总资产
                    "total_liabilities": item.get("TOTAL_LIABILITIES", 0),  # 总负债
                    "total_equity": item.get("TOTAL_EQUITY", 0),  # 所有者权益
                    "current_assets": item.get("TOTAL_CURRENT_ASSETS", 0),  # 流动资产
                    "current_liabilities": item.get("TOTAL_CURRENT_LIAB", 0),  # 流动负债
                    "cash": item.get("MONETARYFUNDS", 0),  # 货币资金
                    "accounts_receivable": item.get("ACCOUNTS_RECE", 0),  # 应收账款
                    "inventory": item.get("INVENTORY", 0),  # 存货
                    "fixed_assets": item.get("FIXED_ASSET", 0),  # 固定资产
                    "short_loan": item.get("SHORT_LOAN", 0),  # 短期借款
                    "long_loan": item.get("LONG_LOAN", 0),  # 长期借款
                })

            return {
                "code": code,
                "sheets": sheets
            }

        except Exception as e:
            print(f"获取资产负债表失败 {code}: {e}")
            return None

    async def get_cash_flow(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取现金流量表数据
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": 8,
            "pageNumber": 1,
            "reportName": "RPT_LICO_FN_CASHFLOW",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(SECURITY_CODE="{code}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return None

            flows = []
            for item in data["result"].get("data", []):
                flows.append({
                    "report_date": item.get("REPORT_DATE", "")[:10] if item.get("REPORT_DATE") else "",
                    "report_type": self._get_report_type(item.get("REPORT_DATE", "")),
                    "operating_cash_flow": item.get("NETCASH_OPERATE", 0),  # 经营活动现金流净额
                    "investing_cash_flow": item.get("NETCASH_INVEST", 0),  # 投资活动现金流净额
                    "financing_cash_flow": item.get("NETCASH_FINANCE", 0),  # 筹资活动现金流净额
                    "net_cash_increase": item.get("CCE_ADD", 0),  # 现金净增加额
                    "sales_cash": item.get("SALES_SERVICES", 0),  # 销售商品收到的现金
                    "purchase_cash": item.get("BUY_SERVICES", 0),  # 购买商品支付的现金
                    "capex": item.get("CONSTRUCT_LONG_ASSET", 0),  # 资本性支出
                })

            return {
                "code": code,
                "flows": flows
            }

        except Exception as e:
            print(f"获取现金流量表失败 {code}: {e}")
            return None

    async def get_stock_industry(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票所属行业
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "reportName": "RPT_F10_CORETHEME_BOARDTYPE",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(SECURITY_CODE="{code}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return None

            result = data["result"].get("data", [])
            if result:
                return {
                    "code": code,
                    "industry": result[0].get("BOARD_NAME", ""),
                    "industry_code": result[0].get("BOARD_CODE", "")
                }
            return None

        except Exception as e:
            print(f"获取股票行业失败 {code}: {e}")
            return None

    async def get_industry_comparison(self, industry_code: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        获取同行业公司财务对比数据
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "sortColumns": "TOTAL_MARKET_CAP",
            "sortTypes": "-1",
            "pageSize": count,
            "pageNumber": 1,
            "reportName": "RPT_VALUEINDUSTRY_DET",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(INDUSTRY_CODE="{industry_code}")'
        }

        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return []

            companies = []
            for item in data["result"].get("data", []):
                companies.append({
                    "code": item.get("SECURITY_CODE", ""),
                    "name": item.get("SECURITY_NAME_ABBR", ""),
                    "market_cap": item.get("TOTAL_MARKET_CAP", 0),
                    "pe_ttm": item.get("PE_TTM", 0),
                    "pb": item.get("PB_MRQ", 0),
                    "ps_ttm": item.get("PS_TTM", 0),
                    "roe": item.get("WEIGHTAVG_ROE", 0),
                    "gross_margin": item.get("GROSSPROFIT_MARGIN", 0),
                    "net_margin": item.get("NETPROFIT_MARGIN", 0),
                    "revenue_yoy": item.get("OPERATE_INCOME_YOY", 0),
                    "profit_yoy": item.get("NETPROFIT_YOY", 0),
                })

            return companies

        except Exception as e:
            print(f"获取行业对比数据失败: {e}")
            return []


# 创建全局实例
eastmoney_api = EastMoneyAPI()
