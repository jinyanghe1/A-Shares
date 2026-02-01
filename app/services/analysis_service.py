"""相关性分析服务"""
import numpy as np
from scipy import stats
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from app.utils.eastmoney import eastmoney_api
from app.utils.nbs import nbs_api
from app.utils.akshare_macro import akshare_macro_service
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
        # 优先使用国家统计局API（最新数据）
        if code == "MACRO_CPI":
            return await nbs_api.get_cpi_monthly(months)
        elif code == "MACRO_PMI":
            return await nbs_api.get_pmi_manufacturing(months)
        elif code == "MACRO_PMI_NON":
            return await nbs_api.get_pmi_non_manufacturing(months)

        # 使用AKshare获取其他宏观数据
        elif code in ["MACRO_GDP", "MACRO_INDUSTRIAL", "MACRO_FIXED_INVESTMENT",
                      "MACRO_RETAIL", "MACRO_PPI", "MACRO_M1", "MACRO_M2",
                      "MACRO_FINANCING", "MACRO_EXCHANGE", "MACRO_UNEMPLOYMENT", "MACRO_TRADE"]:
            return await akshare_macro_service.get_macro_data(code, months)

        return []

    def resample_stock_to_monthly(
        self,
        daily_data: List[Dict[str, Any]],
        indicators: List[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        将日线数据重采样为月度数据
        返回：字典，键为指标名，值为月度数据列表
        """
        if indicators is None:
            indicators = ["close"]  # 默认只返回收盘价

        monthly_groups = defaultdict(lambda: defaultdict(list))

        for item in daily_data:
            try:
                dt = datetime.strptime(item["date"], "%Y-%m-%d")
                month_key = dt.strftime("%Y年%m月")

                # 收集各个指标的数据
                for indicator in indicators:
                    if indicator == "ma5":
                        # ma5需要特殊处理，使用收盘价
                        value = item.get("close", 0)
                    else:
                        value = item.get(indicator, 0)

                    # 确保值是数字类型
                    if isinstance(value, (list, tuple)):
                        value = float(value[0]) if value else 0.0
                    else:
                        value = float(value)

                    monthly_groups[month_key][indicator].append(value)

            except (ValueError, TypeError, KeyError) as e:
                print(f"处理日线数据时出错: {e}, item: {item}")
                continue

        # 为每个指标构建月度结果
        results_by_indicator = {}
        for indicator in indicators:
            results = []
            for month, indicators_data in sorted(monthly_groups.items()):
                values = indicators_data.get(indicator, [])
                if not values:
                    continue

                # 确保所有值都是数字
                valid_values = []
                for v in values:
                    try:
                        valid_values.append(float(v))
                    except (ValueError, TypeError):
                        continue

                if not valid_values:
                    continue

                # 使用平均值作为月度代表值
                avg_value = sum(valid_values) / len(valid_values)
                results.append({
                    "date": month,
                    "value": avg_value
                })

            results_by_indicator[indicator] = results

        return results_by_indicator

    async def analyze_correlation(
        self,
        code1: str,
        code2: str,
        days: int = 60,
        indicators: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        分析两只股票/宏观数据的相关性
        支持的指标：
        - turnover_rate: 换手率相关性
        - amplitude: 振幅相关性
        - ma5: 5日均价相关性
        - volume: 成交量相关性（新增）
        - change_percent: 涨跌幅相关性（新增）
        - volatility: 波动率相关性（新增）
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

        # 计算波动率（收盘价的标准差，使用滚动窗口）
        def calculate_volatility(prices, window=5):
            """计算滚动波动率"""
            volatility = []
            for i in range(window - 1, len(prices)):
                window_prices = prices[i - window + 1:i + 1]
                if len(window_prices) >= 2:
                    volatility.append(np.std(window_prices))
                else:
                    volatility.append(0.0)
            return volatility

        volatility1 = calculate_volatility(close1)
        volatility2 = calculate_volatility(close2)

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
            elif indicator == "volume":
                # 成交量相关性
                values1 = [d.get("volume", 0) for d in aligned_data1]
                values2 = [d.get("volume", 0) for d in aligned_data2]

                corr_value = self.calculate_correlation(values1, values2)
                level, color = self.get_correlation_level(corr_value)

                correlation_matrix[indicator] = {
                    "value": round(corr_value, 4),
                    "description": "成交量相关性",
                    "level": level,
                    "color": color
                }
            elif indicator == "volatility":
                # 波动率相关性
                if len(volatility1) >= 2 and len(volatility2) >= 2:
                    corr_value = self.calculate_correlation(volatility1, volatility2)
                    level, color = self.get_correlation_level(corr_value)

                    correlation_matrix[indicator] = {
                        "value": round(corr_value, 4),
                        "description": "波动率相关性",
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
        volatility_start_idx = len(common_dates) - len(volatility1)

        for i, date in enumerate(common_dates):
            item = {
                "date": date,
                "code1": {
                    "turnover_rate": aligned_data1[i].get("turnover_rate", 0),
                    "amplitude": aligned_data1[i].get("amplitude", 0),
                    "change_percent": aligned_data1[i].get("change_percent", 0),
                    "volume": aligned_data1[i].get("volume", 0),
                    "close": aligned_data1[i].get("close", 0),
                    "ma5": ma5_1[i - ma5_start_idx] if i >= ma5_start_idx else None,
                    "volatility": volatility1[i - volatility_start_idx] if i >= volatility_start_idx else None
                },
                "code2": {
                    "turnover_rate": aligned_data2[i].get("turnover_rate", 0),
                    "amplitude": aligned_data2[i].get("amplitude", 0),
                    "change_percent": aligned_data2[i].get("change_percent", 0),
                    "volume": aligned_data2[i].get("volume", 0),
                    "close": aligned_data2[i].get("close", 0),
                    "ma5": ma5_2[i - ma5_start_idx] if i >= ma5_start_idx else None,
                    "volatility": volatility2[i - volatility_start_idx] if i >= volatility_start_idx else None
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
        months_needed = max(12, int(days / 30) + 1)

        # 宏观数据名称映射
        macro_names = {
            "MACRO_CPI": "CPI指数",
            "MACRO_PPI": "PPI指数",
            "MACRO_PMI": "制造业PMI",
            "MACRO_PMI_NON": "非制造业PMI",
            "MACRO_GDP": "GDP",
            "MACRO_M1": "M1货币供应",
            "MACRO_M2": "M2货币供应",
            "MACRO_INDUSTRIAL": "工业增加值",
            "MACRO_FIXED_INVESTMENT": "固定资产投资",
            "MACRO_RETAIL": "社消零售总额",
            "MACRO_FINANCING": "社会融资规模",
            "MACRO_EXCHANGE": "美元汇率",
            "MACRO_UNEMPLOYMENT": "失业率",
            "MACRO_TRADE": "进出口总额"
        }

        # 指标名称映射
        indicator_names = {
            "close": "收盘价",
            "turnover_rate": "换手率",
            "amplitude": "振幅",
            "volume": "成交量",
            "change_percent": "涨跌幅",
            "ma5": "5日均价"
        }

        # Prepare Data 1
        data1_by_indicator = {}
        name1 = code1
        is_macro1 = code1.startswith("MACRO_")

        if is_macro1:
            # 宏观数据只有一个值序列
            macro_data = await self.get_macro_data_series(code1, months_needed)
            data1_by_indicator["value"] = macro_data
            name1 = macro_names.get(code1, code1)
        else:
            # 股票数据，按指标重采样
            stock_data = await eastmoney_api.get_kline_data(code1, days=months_needed*30)
            if stock_data:
                data1_by_indicator = self.resample_stock_to_monthly(stock_data, indicators)
            quote = await stock_service.get_quote(code1)
            name1 = quote.name if quote else code1

        # Prepare Data 2
        data2_by_indicator = {}
        name2 = code2
        is_macro2 = code2.startswith("MACRO_")

        if is_macro2:
            macro_data = await self.get_macro_data_series(code2, months_needed)
            data2_by_indicator["value"] = macro_data
            name2 = macro_names.get(code2, code2)
        else:
            stock_data = await eastmoney_api.get_kline_data(code2, days=months_needed*30)
            if stock_data:
                data2_by_indicator = self.resample_stock_to_monthly(stock_data, indicators)
            quote = await stock_service.get_quote(code2)
            name2 = quote.name if quote else code2

        # 检查是否有数据
        if not data1_by_indicator or not data2_by_indicator:
            print(f"宏观数据分析失败: data1={len(data1_by_indicator)}, data2={len(data2_by_indicator)}")
            return None

        # 2. 根据数据类型组合，计算相关性
        correlation_matrix = {}
        time_series_data = {}

        if is_macro1 and is_macro2:
            # 两个都是宏观数据：只计算一个相关性
            data1 = data1_by_indicator.get("value", [])
            data2 = data2_by_indicator.get("value", [])

            dict1 = {d["date"]: float(d["value"]) for d in data1}
            dict2 = {d["date"]: float(d["value"]) for d in data2}
            common_months = sorted(set(dict1.keys()) & set(dict2.keys()))

            if len(common_months) >= 3:
                values1 = [dict1[m] for m in common_months]
                values2 = [dict2[m] for m in common_months]

                corr_value = self.calculate_correlation(values1, values2)
                level, color = self.get_correlation_level(corr_value)

                correlation_matrix["monthly_value"] = {
                    "value": round(corr_value, 4),
                    "description": "月度数值相关性",
                    "level": level,
                    "color": color
                }

                time_series_data["monthly_value"] = {
                    "dates": common_months,
                    "values1": values1,
                    "values2": values2
                }

        elif is_macro1 or is_macro2:
            # 一个是宏观，一个是股票：对每个指标计算相关性
            macro_data = data1_by_indicator.get("value", []) if is_macro1 else data2_by_indicator.get("value", [])
            stock_data_dict = data2_by_indicator if is_macro1 else data1_by_indicator

            # 构建宏观数据字典
            macro_dict = {d["date"]: float(d["value"]) for d in macro_data}

            for indicator in indicators:
                stock_monthly = stock_data_dict.get(indicator, [])
                if not stock_monthly:
                    continue

                stock_dict = {d["date"]: float(d["value"]) for d in stock_monthly}
                common_months = sorted(set(macro_dict.keys()) & set(stock_dict.keys()))

                if len(common_months) < 3:
                    continue

                macro_values = [macro_dict[m] for m in common_months]
                stock_values = [stock_dict[m] for m in common_months]

                # 如果是宏观在code1位置，顺序不变；否则交换
                values1 = macro_values if is_macro1 else stock_values
                values2 = stock_values if is_macro1 else macro_values

                corr_value = self.calculate_correlation(values1, values2)
                level, color = self.get_correlation_level(corr_value)

                indicator_desc = indicator_names.get(indicator, indicator)
                correlation_matrix[indicator] = {
                    "value": round(corr_value, 4),
                    "description": f"{indicator_desc}相关性",
                    "level": level,
                    "color": color
                }

                time_series_data[indicator] = {
                    "dates": common_months,
                    "values1": values1,
                    "values2": values2
                }

        if not correlation_matrix:
            print("未能计算出有效的相关性")
            return None

        # 3. 构建时间序列（使用第一个有效指标）
        first_indicator = list(time_series_data.keys())[0]
        ts_data = time_series_data[first_indicator]

        time_series = []
        for i, month in enumerate(ts_data["dates"]):
            time_series.append({
                "date": month,
                "code1": {"ma5": ts_data["values1"][i]},
                "code2": {"ma5": ts_data["values2"][i]}
            })

        return {
            "code1": code1,
            "code2": code2,
            "name1": name1,
            "name2": name2,
            "correlation_matrix": correlation_matrix,
            "time_series": time_series,
            "days": len(ts_data["dates"]) * 30
        }


# 全局实例
analysis_service = AnalysisService()
