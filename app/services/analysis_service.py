"""相关性分析服务"""
import numpy as np
from scipy import stats
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from app.utils.eastmoney import eastmoney_api
from app.utils.nbs import nbs_api
from app.services.stock_service import stock_service


class AnalysisService:
    """相关性分析服务"""

    @staticmethod
    def calculate_ma(data: List[float], period: int = 5) -> List[float]:
        """
        计算移动平均线
        data: 价格序列
        period: 周期
        """
        if len(data) < period:
            return []

        ma_values = []
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            ma_values.append(sum(window) / period)

        return ma_values

    @staticmethod
    def calculate_correlation(x: List[float], y: List[float]) -> float:
        """
        计算皮尔逊相关系数
        返回值范围：-1 到 1
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        try:
            correlation, _ = stats.pearsonr(x, y)
            return float(correlation) if not np.isnan(correlation) else 0.0
        except Exception as e:
            print(f"计算相关系数失败: {e}")
            return 0.0

    @staticmethod
    def get_correlation_level(corr: float) -> tuple:
        """
        获取相关性等级和颜色
        返回: (等级, 颜色)
        """
        abs_corr = abs(corr)
        if abs_corr >= 0.7:
            return ("强相关", "#f5222d" if corr > 0 else "#52c41a")
        elif abs_corr >= 0.4:
            return ("中等相关", "#fa8c16")
        else:
            return ("弱相关", "#8c8c8c")

    async def get_macro_data_series(self, code: str, months: int = 12) -> List[Dict[str, Any]]:
        """获取宏观数据序列"""
        if code == "MACRO_CPI":
            return await nbs_api.get_cpi_monthly(months)
        elif code == "MACRO_PMI":
            # 暂时使用 Manufacturing PMI
            return await nbs_api.get_pmi_manufacturing(months)
        # TODO: Add LPR / Margin Balance if source available
        return []

    def resample_stock_to_monthly(self, daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将日线数据重采样为月度均值"""
        monthly_groups = defaultdict(list)
        
        for item in daily_data:
            # item['date'] format: "2023-12-01"
            try:
                dt = datetime.strptime(item["date"], "%Y-%m-%d")
                month_key = dt.strftime("%Y年%m月") # Match NBS format "2023年12月"
                # NBS sometimes returns "202312", need to align formats.
                # NBSAPI returns "YYYY年MM月" via time_map.
                monthly_groups[month_key].append(item["close"])
            except ValueError:
                continue
                
        results = []
        for month, prices in monthly_groups.items():
            avg_price = sum(prices) / len(prices)
            results.append({
                "date": month,
                "value": avg_price,
                "code": month # Used for sorting/aligning
            })
            
        # Sort by date (assuming YYYY年MM月 sorts correctly string-wise, mostly yes)
        # But better to parse back to sort?
        # NBS code is YYYYMM (e.g. 202312).
        # We need to ensure we can match NBS data which has 'code': '202312'.
        
        # Let's fix the key to be YYYYMM for easier matching
        return results

    async def analyze_correlation(
        self,
        code1: str,
        code2: str,
        days: int = 60,
        indicators: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        分析两只股票/宏观数据的相关性
        """
        if indicators is None:
            indicators = ["turnover_rate", "amplitude", "ma5"]

        # Check for Macro Data
        is_macro1 = code1.startswith("MACRO_")
        is_macro2 = code2.startswith("MACRO_")

        if is_macro1 or is_macro2:
            return await self._analyze_macro_correlation(code1, code2, days, indicators)

        # 获取股票历史数据
        data1 = await eastmoney_api.get_kline_data(code1, days)
        data2 = await eastmoney_api.get_kline_data(code2, days)

        if not data1 or not data2:
            return None

        # 提取名称
        # 尝试从 StockService 缓存或 API 获取名称
        quote1 = await stock_service.get_quote(code1)
        name1 = quote1.name if quote1 else code1
        
        quote2 = await stock_service.get_quote(code2)
        name2 = quote2.name if quote2 else code2

        # 对齐日期（取交集）
        dates1 = {d["date"]: d for d in data1}
        dates2 = {d["date"]: d for d in data2}
        common_dates = sorted(set(dates1.keys()) & set(dates2.keys()))

        if len(common_dates) < 5:
            return None

        # 准备对齐后的数据
        aligned_data1 = [dates1[d] for d in common_dates]
        aligned_data2 = [dates2[d] for d in common_dates]

        # 计算MA5
        close1 = [d["close"] for d in aligned_data1]
        close2 = [d["close"] for d in aligned_data2]
        ma5_1 = self.calculate_ma(close1, 5)
        ma5_2 = self.calculate_ma(close2, 5)

        # 计算相关性矩阵
        correlation_matrix = {}

        for indicator in indicators:
            if indicator == "ma5":
                if len(ma5_1) >= 2 and len(ma5_2) >= 2:
                    corr_value = self.calculate_correlation(ma5_1, ma5_2)
                    level, color = self.get_correlation_level(corr_value)
                    correlation_matrix[indicator] = {
                        "value": round(corr_value, 4),
                        "description": "5日均价相关性",
                        "level": level,
                        "color": color
                    }
            elif indicator in ["turnover_rate", "amplitude", "change_percent"]:
                values1 = [d.get(indicator, 0) for d in aligned_data1]
                values2 = [d.get(indicator, 0) for d in aligned_data2]

                corr_value = self.calculate_correlation(values1, values2)
                level, color = self.get_correlation_level(corr_value)

                indicator_names = {
                    "turnover_rate": "换手率相关性",
                    "amplitude": "振幅相关性",
                    "change_percent": "涨跌幅相关性"
                }

                correlation_matrix[indicator] = {
                    "value": round(corr_value, 4),
                    "description": indicator_names.get(indicator, f"{indicator}相关性"),
                    "level": level,
                    "color": color
                }

        # 构建时间序列数据（用于图表）
        time_series = []
        ma5_start_idx = len(common_dates) - len(ma5_1)

        for i, date in enumerate(common_dates):
            item = {
                "date": date,
                "code1": {
                    "turnover_rate": aligned_data1[i].get("turnover_rate", 0),
                    "amplitude": aligned_data1[i].get("amplitude", 0),
                    "change_percent": aligned_data1[i].get("change_percent", 0),
                    "close": aligned_data1[i].get("close", 0),
                    "ma5": ma5_1[i - ma5_start_idx] if i >= ma5_start_idx else None
                },
                "code2": {
                    "turnover_rate": aligned_data2[i].get("turnover_rate", 0),
                    "amplitude": aligned_data2[i].get("amplitude", 0),
                    "change_percent": aligned_data2[i].get("change_percent", 0),
                    "close": aligned_data2[i].get("close", 0),
                    "ma5": ma5_2[i - ma5_start_idx] if i >= ma5_start_idx else None
                }
            }
            time_series.append(item)

        return {
            "code1": code1,
            "code2": code2,
            "name1": name1,
            "name2": name2,
            "correlation_matrix": correlation_matrix,
            "time_series": time_series,
            "days": len(common_dates)
        }

    async def _analyze_macro_correlation(
        self,
        code1: str,
        code2: str,
        days: int,
        indicators: List[str]
    ) -> Optional[Dict[str, Any]]:
        """分析宏观数据与股票/宏观数据的相关性（月度）"""
        # 1. Fetch Data
        # Macro data is Monthly. Stock data is Daily (needs resampling).
        # Calculate months needed based on days (approx days/30)
        months_needed = max(12, int(days / 30) + 1) # Minimum 12 months for good stats
        
        # Prepare Data 1
        data1_monthly = []
        name1 = code1
        if code1.startswith("MACRO_"):
            data1_monthly = await self.get_macro_data_series(code1, months_needed)
            macro_names = {"MACRO_CPI": "CPI指数", "MACRO_PMI": "制造业PMI"}
            name1 = macro_names.get(code1, code1)
        else:
            stock_data = await eastmoney_api.get_kline_data(code1, days=months_needed*30) # Fetch enough daily data
            data1_monthly = self.resample_stock_to_monthly(stock_data)
            quote = await stock_service.get_quote(code1)
            name1 = quote.name if quote else code1

        # Prepare Data 2
        data2_monthly = []
        name2 = code2
        if code2.startswith("MACRO_"):
            data2_monthly = await self.get_macro_data_series(code2, months_needed)
            macro_names = {"MACRO_CPI": "CPI指数", "MACRO_PMI": "制造业PMI"}
            name2 = macro_names.get(code2, code2)
        else:
            stock_data = await eastmoney_api.get_kline_data(code2, days=months_needed*30)
            data2_monthly = self.resample_stock_to_monthly(stock_data)
            quote = await stock_service.get_quote(code2)
            name2 = quote.name if quote else code2

        if not data1_monthly or not data2_monthly:
            return None
            
        # 2. Align Data by Date (Month string "YYYY年MM月")
        # NBS returns "YYYY年MM月". 
        # My resample returns "YYYY年MM月".
        # Need to ensure they match exactly.
        
        dict1 = {d["date"]: d["value"] for d in data1_monthly}
        dict2 = {d["date"]: d["value"] for d in data2_monthly}
        
        common_months = sorted(set(dict1.keys()) & set(dict2.keys()))
        
        if len(common_months) < 3: # Need at least 3 points
            return None
            
        aligned_values1 = [dict1[m] for m in common_months]
        aligned_values2 = [dict2[m] for m in common_months]
        
        # 3. Calculate Correlation
        corr_value = self.calculate_correlation(aligned_values1, aligned_values2)
        level, color = self.get_correlation_level(corr_value)
        
        # 4. Build Result
        correlation_matrix = {
            "monthly_value": {
                "value": round(corr_value, 4),
                "description": "月度数值相关性",
                "level": level,
                "color": color
            }
        }
        
        time_series = []
        for i, month in enumerate(common_months):
            time_series.append({
                "date": month,
                "code1": {"ma5": aligned_values1[i]}, # Reuse ma5 field for value to fit chart
                "code2": {"ma5": aligned_values2[i]}
            })
            
        return {
            "code1": code1,
            "code2": code2,
            "name1": name1,
            "name2": name2,
            "correlation_matrix": correlation_matrix,
            "time_series": time_series,
            "days": len(common_months) * 30 # Approximate days
        }


# 全局实例
analysis_service = AnalysisService()
