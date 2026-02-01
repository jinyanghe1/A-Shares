"""财务分析服务"""
from typing import Dict, List, Any, Optional
from app.utils.eastmoney import eastmoney_api


class FinanceService:
    """财务分析服务 - 提供财报数据分析功能"""

    def __init__(self):
        self.health_weights = {
            "profitability": 0.30,  # 盈利能力权重
            "solvency": 0.25,       # 偿债能力权重
            "operation": 0.20,      # 运营能力权重
            "growth": 0.25          # 成长能力权重
        }

    async def get_comprehensive_finance(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票综合财务数据
        包括：主要指标、利润表、资产负债表、现金流量表
        """
        # 并行获取各类财务数据
        import asyncio

        results = await asyncio.gather(
            eastmoney_api.get_finance_indicators(code),
            eastmoney_api.get_income_statement(code),
            eastmoney_api.get_balance_sheet(code),
            eastmoney_api.get_cash_flow(code),
            return_exceptions=True
        )

        indicators = results[0] if not isinstance(results[0], Exception) else None
        income = results[1] if not isinstance(results[1], Exception) else None
        balance = results[2] if not isinstance(results[2], Exception) else None
        cashflow = results[3] if not isinstance(results[3], Exception) else None

        if not any([indicators, income, balance, cashflow]):
            return None

        return {
            "code": code,
            "indicators": indicators.get("indicators", []) if indicators else [],
            "income_statement": income.get("statements", []) if income else [],
            "balance_sheet": balance.get("sheets", []) if balance else [],
            "cash_flow": cashflow.get("flows", []) if cashflow else []
        }

    def calculate_financial_ratios(self, finance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算财务比率
        """
        ratios = {
            "profitability": {},  # 盈利能力
            "solvency": {},       # 偿债能力
            "operation": {},      # 运营能力
            "growth": {},         # 成长能力
            "valuation": {}       # 估值指标
        }

        indicators = finance_data.get("indicators", [])
        income = finance_data.get("income_statement", [])
        balance = finance_data.get("balance_sheet", [])
        cashflow = finance_data.get("cash_flow", [])

        # 获取最新数据
        latest_indicator = indicators[0] if indicators else {}
        latest_income = income[0] if income else {}
        latest_balance = balance[0] if balance else {}
        latest_cashflow = cashflow[0] if cashflow else {}

        # 盈利能力指标
        ratios["profitability"] = {
            "roe": latest_indicator.get("roe", 0),                    # 净资产收益率
            "gross_margin": latest_indicator.get("gross_margin", 0),  # 毛利率
            "net_margin": latest_indicator.get("net_margin", 0),      # 净利率
            "eps": latest_indicator.get("eps", 0),                    # 每股收益
        }

        # 偿债能力指标
        total_assets = latest_balance.get("total_assets", 0) or 1
        total_liabilities = latest_balance.get("total_liabilities", 0)
        current_assets = latest_balance.get("current_assets", 0)
        current_liabilities = latest_balance.get("current_liabilities", 0) or 1
        inventory = latest_balance.get("inventory", 0)

        ratios["solvency"] = {
            "debt_ratio": (total_liabilities / total_assets * 100) if total_assets else 0,
            "current_ratio": current_assets / current_liabilities if current_liabilities else 0,
            "quick_ratio": (current_assets - inventory) / current_liabilities if current_liabilities else 0,
            "debt_to_equity": total_liabilities / (total_assets - total_liabilities) if (total_assets - total_liabilities) else 0
        }

        # 运营能力指标 (需要计算周转率等)
        revenue = latest_income.get("revenue", 0)
        accounts_receivable = latest_balance.get("accounts_receivable", 0) or 1
        inventory_avg = inventory or 1

        ratios["operation"] = {
            "receivable_turnover": (revenue / accounts_receivable) if accounts_receivable else 0,
            "inventory_turnover": (latest_income.get("operating_cost", 0) / inventory_avg) if inventory_avg else 0,
            "asset_turnover": (revenue / total_assets) if total_assets else 0,
        }

        # 成长能力指标
        ratios["growth"] = {
            "revenue_yoy": latest_indicator.get("revenue_yoy", 0),
            "profit_yoy": latest_indicator.get("profit_yoy", 0),
        }

        # 计算历史趋势
        if len(indicators) >= 2:
            prev_indicator = indicators[1]
            ratios["growth"]["roe_change"] = (
                (latest_indicator.get("roe", 0) or 0) - (prev_indicator.get("roe", 0) or 0)
            )
            ratios["growth"]["margin_change"] = (
                (latest_indicator.get("net_margin", 0) or 0) - (prev_indicator.get("net_margin", 0) or 0)
            )

        return ratios

    def calculate_health_score(self, ratios: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算财务健康度评分 (0-100)
        """
        scores = {}

        # 盈利能力评分 (30%)
        profitability = ratios.get("profitability", {})
        roe = profitability.get("roe", 0) or 0
        gross_margin = profitability.get("gross_margin", 0) or 0
        net_margin = profitability.get("net_margin", 0) or 0

        # ROE评分: 15%+ = 100, 0% = 0
        roe_score = min(100, max(0, roe / 15 * 100))
        # 毛利率评分: 50%+ = 100, 0% = 0
        gross_score = min(100, max(0, gross_margin / 50 * 100))
        # 净利率评分: 20%+ = 100, 0% = 0
        net_score = min(100, max(0, net_margin / 20 * 100))

        scores["profitability"] = {
            "score": (roe_score * 0.5 + gross_score * 0.25 + net_score * 0.25),
            "roe_score": roe_score,
            "gross_score": gross_score,
            "net_score": net_score,
            "level": self._get_score_level((roe_score * 0.5 + gross_score * 0.25 + net_score * 0.25))
        }

        # 偿债能力评分 (25%)
        solvency = ratios.get("solvency", {})
        debt_ratio = solvency.get("debt_ratio", 0) or 0
        current_ratio = solvency.get("current_ratio", 0) or 0
        quick_ratio = solvency.get("quick_ratio", 0) or 0

        # 负债率评分: 30%以下=100, 70%以上=0
        debt_score = max(0, min(100, (70 - debt_ratio) / 40 * 100))
        # 流动比率评分: 2.0+ = 100, 1.0以下 = 0
        current_score = min(100, max(0, (current_ratio - 1) * 100))
        # 速动比率评分: 1.5+ = 100, 0.5以下 = 0
        quick_score = min(100, max(0, (quick_ratio - 0.5) * 100))

        scores["solvency"] = {
            "score": (debt_score * 0.5 + current_score * 0.25 + quick_score * 0.25),
            "debt_score": debt_score,
            "current_score": current_score,
            "quick_score": quick_score,
            "level": self._get_score_level((debt_score * 0.5 + current_score * 0.25 + quick_score * 0.25))
        }

        # 运营能力评分 (20%)
        operation = ratios.get("operation", {})
        asset_turnover = operation.get("asset_turnover", 0) or 0
        receivable_turnover = operation.get("receivable_turnover", 0) or 0

        # 资产周转率评分: 1.0+ = 100, 0.2以下 = 0
        asset_score = min(100, max(0, (asset_turnover - 0.2) / 0.8 * 100))
        # 应收账款周转率评分: 10+ = 100, 2以下 = 0
        receivable_score = min(100, max(0, (receivable_turnover - 2) / 8 * 100))

        scores["operation"] = {
            "score": (asset_score * 0.5 + receivable_score * 0.5),
            "asset_score": asset_score,
            "receivable_score": receivable_score,
            "level": self._get_score_level((asset_score * 0.5 + receivable_score * 0.5))
        }

        # 成长能力评分 (25%)
        growth = ratios.get("growth", {})
        revenue_yoy = growth.get("revenue_yoy", 0) or 0
        profit_yoy = growth.get("profit_yoy", 0) or 0

        # 营收增长评分: 30%+ = 100, -10%以下 = 0
        revenue_score = min(100, max(0, (revenue_yoy + 10) / 40 * 100))
        # 利润增长评分: 30%+ = 100, -10%以下 = 0
        profit_score = min(100, max(0, (profit_yoy + 10) / 40 * 100))

        scores["growth"] = {
            "score": (revenue_score * 0.5 + profit_score * 0.5),
            "revenue_score": revenue_score,
            "profit_score": profit_score,
            "level": self._get_score_level((revenue_score * 0.5 + profit_score * 0.5))
        }

        # 计算总分
        total_score = (
            scores["profitability"]["score"] * self.health_weights["profitability"] +
            scores["solvency"]["score"] * self.health_weights["solvency"] +
            scores["operation"]["score"] * self.health_weights["operation"] +
            scores["growth"]["score"] * self.health_weights["growth"]
        )

        return {
            "total_score": round(total_score, 1),
            "total_level": self._get_score_level(total_score),
            "details": scores,
            "interpretation": self._get_health_interpretation(total_score, scores)
        }

    def _get_score_level(self, score: float) -> Dict[str, Any]:
        """根据分数获取等级"""
        if score >= 80:
            return {"level": "优秀", "color": "#22c55e", "icon": "🌟"}
        elif score >= 60:
            return {"level": "良好", "color": "#3b82f6", "icon": "✓"}
        elif score >= 40:
            return {"level": "一般", "color": "#f59e0b", "icon": "⚠"}
        elif score >= 20:
            return {"level": "较差", "color": "#ef4444", "icon": "⚡"}
        else:
            return {"level": "危险", "color": "#dc2626", "icon": "⛔"}

    def _get_health_interpretation(self, total_score: float, scores: Dict) -> List[str]:
        """生成财务健康度解读"""
        interpretation = []

        if total_score >= 80:
            interpretation.append("公司财务状况优秀，各项指标表现良好")
        elif total_score >= 60:
            interpretation.append("公司财务状况良好，整体运营健康")
        elif total_score >= 40:
            interpretation.append("公司财务状况一般，存在一定风险")
        else:
            interpretation.append("公司财务状况较差，需谨慎关注")

        # 分项解读
        profitability_score = scores.get("profitability", {}).get("score", 0)
        if profitability_score < 40:
            interpretation.append("盈利能力较弱，需关注毛利率和净利率变化")
        elif profitability_score >= 80:
            interpretation.append("盈利能力突出，ROE和利润率表现优秀")

        solvency_score = scores.get("solvency", {}).get("score", 0)
        if solvency_score < 40:
            interpretation.append("偿债压力较大，负债率偏高需关注")
        elif solvency_score >= 80:
            interpretation.append("偿债能力强，财务结构稳健")

        growth_score = scores.get("growth", {}).get("score", 0)
        if growth_score < 40:
            interpretation.append("成长性不足，营收和利润增速放缓")
        elif growth_score >= 80:
            interpretation.append("成长性强劲，业绩保持高速增长")

        return interpretation

    async def get_industry_comparison(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取同行业对比数据
        """
        # 获取股票所属行业
        industry_info = await eastmoney_api.get_stock_industry(code)

        if not industry_info:
            return None

        industry_code = industry_info.get("industry_code", "")
        industry_name = industry_info.get("industry", "")

        if not industry_code:
            return None

        # 获取同行业公司数据
        companies = await eastmoney_api.get_industry_comparison(industry_code, count=20)

        if not companies:
            return None

        # 计算行业平均值
        avg_pe = sum(c.get("pe_ttm", 0) or 0 for c in companies) / len(companies) if companies else 0
        avg_pb = sum(c.get("pb", 0) or 0 for c in companies) / len(companies) if companies else 0
        avg_roe = sum(c.get("roe", 0) or 0 for c in companies) / len(companies) if companies else 0
        avg_gross_margin = sum(c.get("gross_margin", 0) or 0 for c in companies) / len(companies) if companies else 0
        avg_net_margin = sum(c.get("net_margin", 0) or 0 for c in companies) / len(companies) if companies else 0

        # 找到目标股票的数据
        target_company = None
        target_rank = 0
        for i, c in enumerate(companies):
            if c.get("code") == code:
                target_company = c
                target_rank = i + 1
                break

        return {
            "code": code,
            "industry_code": industry_code,
            "industry_name": industry_name,
            "companies": companies,
            "industry_avg": {
                "pe_ttm": round(avg_pe, 2),
                "pb": round(avg_pb, 2),
                "roe": round(avg_roe, 2),
                "gross_margin": round(avg_gross_margin, 2),
                "net_margin": round(avg_net_margin, 2)
            },
            "target_company": target_company,
            "rank": target_rank,
            "total_count": len(companies)
        }

    def analyze_finance_trend(self, finance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析财务趋势
        """
        indicators = finance_data.get("indicators", [])
        income = finance_data.get("income_statement", [])

        trends = {
            "roe_trend": [],
            "margin_trend": [],
            "revenue_trend": [],
            "profit_trend": [],
            "summary": []
        }

        # ROE趋势
        for ind in indicators[:8]:  # 最近8个季度
            if ind.get("report_date"):
                trends["roe_trend"].append({
                    "date": ind["report_date"],
                    "value": ind.get("roe", 0) or 0
                })

        # 利润率趋势
        for ind in indicators[:8]:
            if ind.get("report_date"):
                trends["margin_trend"].append({
                    "date": ind["report_date"],
                    "gross_margin": ind.get("gross_margin", 0) or 0,
                    "net_margin": ind.get("net_margin", 0) or 0
                })

        # 营收和利润趋势
        for inc in income[:8]:
            if inc.get("report_date"):
                trends["revenue_trend"].append({
                    "date": inc["report_date"],
                    "revenue": inc.get("revenue", 0) or 0,
                    "net_profit": inc.get("parent_net_profit", 0) or 0
                })

        # 趋势总结
        if len(trends["roe_trend"]) >= 2:
            latest_roe = trends["roe_trend"][0]["value"]
            prev_roe = trends["roe_trend"][1]["value"]
            if latest_roe > prev_roe:
                trends["summary"].append(f"ROE环比上升 {round(latest_roe - prev_roe, 2)}%")
            elif latest_roe < prev_roe:
                trends["summary"].append(f"ROE环比下降 {round(prev_roe - latest_roe, 2)}%")

        if len(trends["revenue_trend"]) >= 2:
            latest_rev = trends["revenue_trend"][0]["revenue"]
            prev_rev = trends["revenue_trend"][1]["revenue"]
            if prev_rev > 0:
                change = (latest_rev - prev_rev) / prev_rev * 100
                if change > 0:
                    trends["summary"].append(f"营收环比增长 {round(change, 2)}%")
                else:
                    trends["summary"].append(f"营收环比下降 {round(abs(change), 2)}%")

        return trends

    async def get_full_analysis(self, code: str) -> Dict[str, Any]:
        """
        获取完整财务分析报告
        """
        # 获取综合财务数据
        finance_data = await self.get_comprehensive_finance(code)

        if not finance_data:
            return {"success": False, "error": "无法获取财务数据"}

        # 计算财务比率
        ratios = self.calculate_financial_ratios(finance_data)

        # 计算健康度评分
        health_score = self.calculate_health_score(ratios)

        # 分析财务趋势
        trends = self.analyze_finance_trend(finance_data)

        # 获取行业对比
        industry_comparison = await self.get_industry_comparison(code)

        return {
            "success": True,
            "code": code,
            "finance_data": finance_data,
            "ratios": ratios,
            "health_score": health_score,
            "trends": trends,
            "industry_comparison": industry_comparison
        }


# 创建全局实例
finance_service = FinanceService()
