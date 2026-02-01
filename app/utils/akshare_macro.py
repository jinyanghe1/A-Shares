"""AKshare 宏观数据封装
用于抓取2024年前的历史数据，最新数据使用国家统计局披露
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio


class AKShareMacroService:
    """AKshare 宏观数据服务"""

    @staticmethod
    def _to_dict_list(df: pd.DataFrame, date_col: str = "date", value_col: str = "value") -> List[Dict[str, Any]]:
        """将 DataFrame 转换为字典列表"""
        if df is None or df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            try:
                results.append({
                    "date": str(row[date_col]) if date_col in row else "",
                    "value": float(row[value_col]) if value_col in row else 0.0
                })
            except (ValueError, KeyError, TypeError) as e:
                print(f"数据转换错误: {e}, row: {row}")
                continue

        return results

    async def get_gdp_year(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """
        获取年度GDP数据
        使用 AKshare: macro_china_gdp_year
        """
        try:
            import akshare as ak
            # 在异步环境中运行同步函数
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_gdp_year)

            if df is None or df.empty:
                return []

            # 数据格式: 季度, 国内生产总值-绝对值(亿元), 等
            # 取最近N年数据
            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["季度"]) if "季度" in row else "",
                        "value": float(row["国内生产总值-绝对值(亿元)"]) if "国内生产总值-绝对值(亿元)" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"GDP数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取GDP数据失败: {e}")
            return []

    async def get_industrial_added_value(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取工业增加值数据
        使用 AKshare: macro_china_industrial_production_yoy
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_industrial_production_yoy)

            if df is None or df.empty:
                return []

            # 取最近N月数据
            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    # 数据格式: 月份, 同比增长, 累计增长
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["同比增长"]) if "同比增长" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"工业增加值数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取工业增加值数据失败: {e}")
            return []

    async def get_fixed_asset_investment(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取固定资产投资数据
        使用 AKshare: macro_china_fixed_asset_investment_yoy
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_fixed_asset_investment_yoy)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["同比增长"]) if "同比增长" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"固定资产投资数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取固定资产投资数据失败: {e}")
            return []

    async def get_social_consumption_retail(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取社会消费品零售总额数据
        使用 AKshare: macro_china_consumer_goods_retail
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_consumer_goods_retail)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["同比增长"]) if "同比增长" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"社会消费品零售数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取社会消费品零售数据失败: {e}")
            return []

    async def get_ppi(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取工业生产者出厂价格指数(PPI)
        使用 AKshare: macro_china_ppi_yearly
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_ppi_yearly)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["当月同比"]) if "当月同比" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"PPI数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取PPI数据失败: {e}")
            return []

    async def get_money_supply_m1(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取货币供应量M1
        使用 AKshare: macro_china_money_supply
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_money_supply)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["货币和准货币(M1)同比增长"]) if "货币和准货币(M1)同比增长" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"M1数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取M1数据失败: {e}")
            return []

    async def get_money_supply_m2(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取货币供应量M2
        使用 AKshare: macro_china_money_supply
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_money_supply)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["货币和准货币(M2)同比增长"]) if "货币和准货币(M2)同比增长" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"M2数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取M2数据失败: {e}")
            return []

    async def get_social_financing_scale(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取社会融资规模
        使用 AKshare: macro_china_shrzgm
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_shrzgm)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["社会融资规模增量-当月值"]) if "社会融资规模增量-当月值" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"社会融资规模数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取社会融资规模数据失败: {e}")
            return []

    async def get_exchange_rate_usd_cny(self, last_n: int = 30) -> List[Dict[str, Any]]:
        """
        获取人民币兑美元汇率
        使用 AKshare: currency_boc_sina (中间价)
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            # 获取美元/人民币汇率
            df = await loop.run_in_executor(
                None,
                lambda: ak.currency_boc_sina(symbol="美元", start_date="20230101", end_date=datetime.now().strftime("%Y%m%d"))
            )

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["日期"]) if "日期" in row else "",
                        "value": float(row["中间价"]) if "中间价" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"汇率数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取汇率数据失败: {e}")
            return []

    async def get_unemployment_rate(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取城镇调查失业率
        使用 AKshare: macro_china_urban_unemployment
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_urban_unemployment)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": float(row["城镇调查失业率"]) if "城镇调查失业率" in row else 0.0
                    })
                except (ValueError, KeyError) as e:
                    print(f"失业率数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取失业率数据失败: {e}")
            return []

    async def get_import_export(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        获取进出口总额
        使用 AKshare: macro_china_trade_balance
        """
        try:
            import akshare as ak
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.macro_china_trade_balance)

            if df is None or df.empty:
                return []

            df = df.tail(last_n)

            results = []
            for _, row in df.iterrows():
                try:
                    # 计算进出口总额 = 出口 + 进口
                    export = float(row["出口金额"]) if "出口金额" in row else 0.0
                    import_val = float(row["进口金额"]) if "进口金额" in row else 0.0
                    total = export + import_val

                    results.append({
                        "date": str(row["月份"]) if "月份" in row else "",
                        "value": total
                    })
                except (ValueError, KeyError) as e:
                    print(f"进出口数据转换错误: {e}")
                    continue

            return results

        except Exception as e:
            print(f"获取进出口数据失败: {e}")
            return []

    async def get_macro_data(self, indicator: str, last_n: int = 12) -> List[Dict[str, Any]]:
        """
        统一接口获取宏观数据
        :param indicator: 指标名称
        :param last_n: 最近N期数据
        """
        indicator_map = {
            "MACRO_GDP": self.get_gdp_year,
            "MACRO_INDUSTRIAL": self.get_industrial_added_value,
            "MACRO_FIXED_INVESTMENT": self.get_fixed_asset_investment,
            "MACRO_RETAIL": self.get_social_consumption_retail,
            "MACRO_PPI": self.get_ppi,
            "MACRO_M1": self.get_money_supply_m1,
            "MACRO_M2": self.get_money_supply_m2,
            "MACRO_FINANCING": self.get_social_financing_scale,
            "MACRO_EXCHANGE": self.get_exchange_rate_usd_cny,
            "MACRO_UNEMPLOYMENT": self.get_unemployment_rate,
            "MACRO_TRADE": self.get_import_export,
        }

        func = indicator_map.get(indicator)
        if func:
            return await func(last_n)
        else:
            print(f"不支持的宏观指标: {indicator}")
            return []


# 全局实例
akshare_macro_service = AKShareMacroService()
