"""股票筛选服务"""
from typing import Dict, List, Any, Optional
from app.utils.eastmoney import eastmoney_api


class ScreenerService:
    """股票筛选器服务"""

    def __init__(self):
        # 筛选条件配置
        self.filter_configs = {
            "market_cap": {
                "name": "市值",
                "unit": "亿",
                "ranges": [
                    {"label": "微盘股(<30亿)", "min": 0, "max": 30},
                    {"label": "小盘股(30-100亿)", "min": 30, "max": 100},
                    {"label": "中盘股(100-500亿)", "min": 100, "max": 500},
                    {"label": "大盘股(500-2000亿)", "min": 500, "max": 2000},
                    {"label": "超大盘(>2000亿)", "min": 2000, "max": None}
                ]
            },
            "pe_ratio": {
                "name": "市盈率(PE)",
                "unit": "倍",
                "ranges": [
                    {"label": "亏损", "min": None, "max": 0},
                    {"label": "低估值(<15)", "min": 0, "max": 15},
                    {"label": "中等(15-30)", "min": 15, "max": 30},
                    {"label": "较高(30-60)", "min": 30, "max": 60},
                    {"label": "高估值(>60)", "min": 60, "max": None}
                ]
            },
            "change_percent": {
                "name": "涨跌幅",
                "unit": "%",
                "ranges": [
                    {"label": "跌停", "min": None, "max": -9.9},
                    {"label": "大跌(<-5%)", "min": -9.9, "max": -5},
                    {"label": "下跌(-5%~0)", "min": -5, "max": 0},
                    {"label": "上涨(0~5%)", "min": 0, "max": 5},
                    {"label": "大涨(>5%)", "min": 5, "max": 9.9},
                    {"label": "涨停", "min": 9.9, "max": None}
                ]
            },
            "turnover_rate": {
                "name": "换手率",
                "unit": "%",
                "ranges": [
                    {"label": "低(<2%)", "min": 0, "max": 2},
                    {"label": "中等(2-5%)", "min": 2, "max": 5},
                    {"label": "较高(5-10%)", "min": 5, "max": 10},
                    {"label": "活跃(>10%)", "min": 10, "max": None}
                ]
            }
        }

    async def screen_stocks(
        self,
        market_cap_min: Optional[float] = None,
        market_cap_max: Optional[float] = None,
        pe_min: Optional[float] = None,
        pe_max: Optional[float] = None,
        pb_min: Optional[float] = None,
        pb_max: Optional[float] = None,
        change_min: Optional[float] = None,
        change_max: Optional[float] = None,
        turnover_min: Optional[float] = None,
        turnover_max: Optional[float] = None,
        industry: Optional[str] = None,
        sort_by: str = "market_cap",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        根据条件筛选股票
        """
        # 构建筛选条件字符串
        filters = []

        # 市值筛选（转换为元）
        if market_cap_min is not None:
            filters.append(f'(TOTAL_MARKET_CAP>={market_cap_min * 100000000})')
        if market_cap_max is not None:
            filters.append(f'(TOTAL_MARKET_CAP<={market_cap_max * 100000000})')

        # PE筛选
        if pe_min is not None:
            filters.append(f'(PE_TTM>={pe_min})')
        if pe_max is not None:
            filters.append(f'(PE_TTM<={pe_max})')

        # PB筛选
        if pb_min is not None:
            filters.append(f'(PB_MRQ>={pb_min})')
        if pb_max is not None:
            filters.append(f'(PB_MRQ<={pb_max})')

        # 涨跌幅筛选
        if change_min is not None:
            filters.append(f'(CHANGE_RATE>={change_min})')
        if change_max is not None:
            filters.append(f'(CHANGE_RATE<={change_max})')

        # 换手率筛选
        if turnover_min is not None:
            filters.append(f'(TURNOVER_RATE>={turnover_min})')
        if turnover_max is not None:
            filters.append(f'(TURNOVER_RATE<={turnover_max})')

        # 行业筛选
        if industry:
            filters.append(f'(INDUSTRY_CODE="{industry}")')

        # 获取筛选结果
        result = await self._fetch_screener_data(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )

        return result

    async def _fetch_screener_data(
        self,
        filters: List[str],
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int
    ) -> Dict[str, Any]:
        """
        从东方财富获取筛选数据
        """
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        # 排序字段映射
        sort_map = {
            "market_cap": "TOTAL_MARKET_CAP",
            "pe": "PE_TTM",
            "pb": "PB_MRQ",
            "change": "CHANGE_RATE",
            "turnover": "TURNOVER_RATE",
            "volume": "VOLUME",
            "amount": "DEAL_AMOUNT"
        }

        sort_column = sort_map.get(sort_by, "TOTAL_MARKET_CAP")
        sort_type = "-1" if sort_order == "desc" else "1"

        filter_str = "".join(filters) if filters else ""

        params = {
            "sortColumns": sort_column,
            "sortTypes": sort_type,
            "pageSize": page_size,
            "pageNumber": page,
            "reportName": "RPT_VALUEANALYSIS_DET",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": filter_str
        }

        try:
            resp = await eastmoney_api.client.get(url, params=params)
            data = resp.json()

            if not data.get("success") or not data.get("result"):
                return {"success": False, "stocks": [], "total": 0}

            stocks = []
            for item in data["result"].get("data", []):
                stocks.append({
                    "code": item.get("SECURITY_CODE", ""),
                    "name": item.get("SECURITY_NAME_ABBR", ""),
                    "price": item.get("NEW_PRICE", 0),
                    "change_percent": item.get("CHANGE_RATE", 0),
                    "market_cap": item.get("TOTAL_MARKET_CAP", 0),
                    "pe_ttm": item.get("PE_TTM", 0),
                    "pb": item.get("PB_MRQ", 0),
                    "turnover_rate": item.get("TURNOVER_RATE", 0),
                    "volume": item.get("VOLUME", 0),
                    "amount": item.get("DEAL_AMOUNT", 0),
                    "industry": item.get("INDUSTRY", ""),
                    "roe": item.get("WEIGHTAVG_ROE", 0)
                })

            total = data["result"].get("count", len(stocks))

            return {
                "success": True,
                "stocks": stocks,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

        except Exception as e:
            print(f"股票筛选失败: {e}")
            return {"success": False, "stocks": [], "total": 0, "error": str(e)}

    async def get_quick_screen(self, screen_type: str) -> Dict[str, Any]:
        """
        快速筛选预设
        """
        presets = {
            "low_pe": {
                "name": "低估值股票",
                "description": "PE<15，市值>100亿",
                "params": {"pe_max": 15, "market_cap_min": 100}
            },
            "high_turnover": {
                "name": "活跃股票",
                "description": "换手率>5%",
                "params": {"turnover_min": 5}
            },
            "big_cap": {
                "name": "大盘蓝筹",
                "description": "市值>500亿，PE<30",
                "params": {"market_cap_min": 500, "pe_max": 30}
            },
            "small_cap_growth": {
                "name": "小盘成长",
                "description": "市值30-100亿，涨幅>0",
                "params": {"market_cap_min": 30, "market_cap_max": 100, "change_min": 0}
            },
            "limit_up": {
                "name": "涨停板",
                "description": "涨幅>=9.9%",
                "params": {"change_min": 9.9}
            },
            "limit_down": {
                "name": "跌停板",
                "description": "跌幅<=-9.9%",
                "params": {"change_max": -9.9}
            },
            "high_volume": {
                "name": "放量上涨",
                "description": "换手率>10%，涨幅>3%",
                "params": {"turnover_min": 10, "change_min": 3}
            }
        }

        preset = presets.get(screen_type)
        if not preset:
            return {"success": False, "error": f"未知的筛选类型: {screen_type}"}

        result = await self.screen_stocks(**preset["params"])
        result["preset_name"] = preset["name"]
        result["preset_description"] = preset["description"]

        return result

    def get_filter_configs(self) -> Dict[str, Any]:
        """
        获取筛选条件配置
        """
        return self.filter_configs

    async def get_industry_list(self) -> List[Dict[str, str]]:
        """
        获取行业列表
        """
        sectors = await eastmoney_api.get_sector_list("industry")
        return [{"code": s["code"], "name": s["name"]} for s in sectors]


# 创建全局实例
screener_service = ScreenerService()
