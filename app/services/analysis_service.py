"""相关性分析服务"""
import numpy as np
from scipy import stats
from typing import List, Dict, Any, Optional
from app.utils.eastmoney import eastmoney_api


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

    async def analyze_correlation(
        self,
        code1: str,
        code2: str,
        days: int = 60,
        indicators: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        分析两只股票的相关性

        Args:
            code1: 股票1代码
            code2: 股票2代码
            days: 分析天数
            indicators: 分析指标列表 ["turnover_rate", "amplitude", "ma5"]

        Returns:
            相关性分析结果字典
        """
        if indicators is None:
            indicators = ["turnover_rate", "amplitude", "ma5"]

        # 获取历史数据
        data1 = await eastmoney_api.get_kline_data(code1, days)
        data2 = await eastmoney_api.get_kline_data(code2, days)

        if not data1 or not data2:
            return None

        # 提取名称
        name1 = code1
        name2 = code2
        # TODO: 可以通过get_stock_quote获取完整名称

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


# 全局实例
analysis_service = AnalysisService()
