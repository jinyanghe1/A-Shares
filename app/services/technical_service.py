"""技术指标分析服务"""
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime


class TechnicalService:
    """技术指标计算服务"""

    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> List[Optional[float]]:
        """计算移动平均线"""
        if len(prices) < period:
            return [None] * len(prices)

        ma = [None] * (period - 1)
        for i in range(period - 1, len(prices)):
            ma.append(sum(prices[i - period + 1:i + 1]) / period)
        return ma

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[Optional[float]]:
        """计算指数移动平均线"""
        if len(prices) < period:
            return [None] * len(prices)

        multiplier = 2 / (period + 1)
        ema = [None] * (period - 1)

        # 第一个EMA使用简单平均
        first_ema = sum(prices[:period]) / period
        ema.append(first_ema)

        # 后续使用EMA公式
        for i in range(period, len(prices)):
            current_ema = (prices[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(current_ema)

        return ema

    def calculate_macd(
        self,
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, List[Optional[float]]]:
        """
        计算MACD指标
        返回: DIF(快线), DEA(慢线/信号线), MACD柱(DIF-DEA)*2
        """
        if len(prices) < slow_period + signal_period:
            return {
                "dif": [None] * len(prices),
                "dea": [None] * len(prices),
                "macd": [None] * len(prices),
                "signal": ["neutral"] * len(prices)
            }

        # 计算快慢EMA
        ema_fast = self.calculate_ema(prices, fast_period)
        ema_slow = self.calculate_ema(prices, slow_period)

        # 计算DIF (快线 - 慢线)
        dif = []
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                dif.append(ema_fast[i] - ema_slow[i])
            else:
                dif.append(None)

        # 过滤None值计算DEA
        dif_values = [v for v in dif if v is not None]
        if len(dif_values) >= signal_period:
            dea_values = self.calculate_ema(dif_values, signal_period)
            # 将DEA对齐回原始长度
            dea = [None] * (len(dif) - len(dea_values)) + dea_values
        else:
            dea = [None] * len(prices)

        # 计算MACD柱
        macd = []
        for i in range(len(prices)):
            if dif[i] is not None and dea[i] is not None:
                macd.append((dif[i] - dea[i]) * 2)
            else:
                macd.append(None)

        # 判断信号
        signals = self._get_macd_signals(dif, dea, macd)

        return {
            "dif": [round(v, 4) if v is not None else None for v in dif],
            "dea": [round(v, 4) if v is not None else None for v in dea],
            "macd": [round(v, 4) if v is not None else None for v in macd],
            "signal": signals
        }

    def _get_macd_signals(
        self,
        dif: List[Optional[float]],
        dea: List[Optional[float]],
        macd: List[Optional[float]]
    ) -> List[str]:
        """获取MACD信号"""
        signals = []
        for i in range(len(dif)):
            if i == 0 or dif[i] is None or dea[i] is None or dif[i-1] is None or dea[i-1] is None:
                signals.append("neutral")
                continue

            # 金叉：DIF从下方穿过DEA
            if dif[i-1] < dea[i-1] and dif[i] > dea[i]:
                signals.append("golden_cross")
            # 死叉：DIF从上方穿过DEA
            elif dif[i-1] > dea[i-1] and dif[i] < dea[i]:
                signals.append("death_cross")
            # DIF在DEA上方
            elif dif[i] > dea[i]:
                signals.append("bullish")
            # DIF在DEA下方
            else:
                signals.append("bearish")

        return signals

    def calculate_kdj(
        self,
        high: List[float],
        low: List[float],
        close: List[float],
        period: int = 9,
        k_period: int = 3,
        d_period: int = 3
    ) -> Dict[str, List[Optional[float]]]:
        """
        计算KDJ指标
        RSV = (收盘价 - N日最低价) / (N日最高价 - N日最低价) * 100
        K = RSV的M1日移动平均
        D = K的M2日移动平均
        J = 3K - 2D
        """
        if len(close) < period:
            return {
                "k": [None] * len(close),
                "d": [None] * len(close),
                "j": [None] * len(close),
                "signal": ["neutral"] * len(close)
            }

        rsv = []
        for i in range(len(close)):
            if i < period - 1:
                rsv.append(None)
            else:
                highest = max(high[i - period + 1:i + 1])
                lowest = min(low[i - period + 1:i + 1])
                if highest == lowest:
                    rsv.append(50.0)
                else:
                    rsv.append((close[i] - lowest) / (highest - lowest) * 100)

        # 计算K值（RSV的指数移动平均）
        k = [None] * (period - 1)
        k.append(50.0)  # K初始值为50
        for i in range(period, len(close)):
            if rsv[i] is not None:
                k.append((2/3) * k[-1] + (1/3) * rsv[i])
            else:
                k.append(k[-1])

        # 计算D值（K的指数移动平均）
        d = [None] * (period - 1)
        d.append(50.0)  # D初始值为50
        for i in range(period, len(close)):
            if k[i] is not None:
                d.append((2/3) * d[-1] + (1/3) * k[i])
            else:
                d.append(d[-1])

        # 计算J值
        j = []
        for i in range(len(close)):
            if k[i] is not None and d[i] is not None:
                j.append(3 * k[i] - 2 * d[i])
            else:
                j.append(None)

        # 判断信号
        signals = self._get_kdj_signals(k, d, j)

        return {
            "k": [round(v, 2) if v is not None else None for v in k],
            "d": [round(v, 2) if v is not None else None for v in d],
            "j": [round(v, 2) if v is not None else None for v in j],
            "signal": signals
        }

    def _get_kdj_signals(
        self,
        k: List[Optional[float]],
        d: List[Optional[float]],
        j: List[Optional[float]]
    ) -> List[str]:
        """获取KDJ信号"""
        signals = []
        for i in range(len(k)):
            if i == 0 or k[i] is None or d[i] is None:
                signals.append("neutral")
                continue

            # 超买区（K/D > 80）
            if k[i] > 80 and d[i] > 80:
                if k[i-1] > d[i-1] and k[i] < d[i]:
                    signals.append("overbought_cross")  # 超买区死叉
                else:
                    signals.append("overbought")
            # 超卖区（K/D < 20）
            elif k[i] < 20 and d[i] < 20:
                if k[i-1] < d[i-1] and k[i] > d[i]:
                    signals.append("oversold_cross")  # 超卖区金叉
                else:
                    signals.append("oversold")
            # 金叉
            elif k[i-1] < d[i-1] and k[i] > d[i]:
                signals.append("golden_cross")
            # 死叉
            elif k[i-1] > d[i-1] and k[i] < d[i]:
                signals.append("death_cross")
            else:
                signals.append("neutral")

        return signals

    def calculate_rsi(
        self,
        prices: List[float],
        period: int = 14
    ) -> Dict[str, List[Optional[float]]]:
        """
        计算RSI指标
        RSI = 100 - 100 / (1 + RS)
        RS = 平均上涨幅度 / 平均下跌幅度
        """
        if len(prices) < period + 1:
            return {
                "rsi": [None] * len(prices),
                "signal": ["neutral"] * len(prices)
            }

        # 计算价格变动
        changes = [0]
        for i in range(1, len(prices)):
            changes.append(prices[i] - prices[i-1])

        # 分离涨跌
        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]

        # 计算平均涨跌幅
        rsi = [None] * period
        avg_gain = sum(gains[1:period+1]) / period
        avg_loss = sum(losses[1:period+1]) / period

        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - 100 / (1 + rs))

        # 后续使用平滑公式
        for i in range(period + 1, len(prices)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                rsi.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - 100 / (1 + rs))

        # 判断信号
        signals = []
        for i, r in enumerate(rsi):
            if r is None:
                signals.append("neutral")
            elif r >= 70:
                signals.append("overbought")
            elif r <= 30:
                signals.append("oversold")
            elif r >= 50:
                signals.append("bullish")
            else:
                signals.append("bearish")

        return {
            "rsi": [round(v, 2) if v is not None else None for v in rsi],
            "signal": signals
        }

    def calculate_boll(
        self,
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, List[Optional[float]]]:
        """
        计算布林带
        中轨 = N日移动平均线
        上轨 = 中轨 + K * N日标准差
        下轨 = 中轨 - K * N日标准差
        """
        if len(prices) < period:
            return {
                "upper": [None] * len(prices),
                "middle": [None] * len(prices),
                "lower": [None] * len(prices),
                "signal": ["neutral"] * len(prices)
            }

        upper = [None] * (period - 1)
        middle = [None] * (period - 1)
        lower = [None] * (period - 1)

        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            ma = sum(window) / period
            std = np.std(window)

            middle.append(ma)
            upper.append(ma + std_dev * std)
            lower.append(ma - std_dev * std)

        # 判断信号
        signals = []
        for i in range(len(prices)):
            if upper[i] is None or lower[i] is None:
                signals.append("neutral")
            elif prices[i] >= upper[i]:
                signals.append("overbought")
            elif prices[i] <= lower[i]:
                signals.append("oversold")
            elif prices[i] > middle[i]:
                signals.append("bullish")
            else:
                signals.append("bearish")

        return {
            "upper": [round(v, 4) if v is not None else None for v in upper],
            "middle": [round(v, 4) if v is not None else None for v in middle],
            "lower": [round(v, 4) if v is not None else None for v in lower],
            "signal": signals
        }

    def calculate_all_indicators(
        self,
        kline_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算所有技术指标
        kline_data: K线数据列表，每条包含date, open, high, low, close, volume
        """
        if not kline_data or len(kline_data) < 30:
            return {"error": "数据不足，需要至少30条K线数据"}

        dates = [d["date"] for d in kline_data]
        opens = [float(d["open"]) for d in kline_data]
        highs = [float(d["high"]) for d in kline_data]
        lows = [float(d["low"]) for d in kline_data]
        closes = [float(d["close"]) for d in kline_data]
        volumes = [float(d["volume"]) for d in kline_data]

        # 计算各项指标
        macd = self.calculate_macd(closes)
        kdj = self.calculate_kdj(highs, lows, closes)
        rsi = self.calculate_rsi(closes)
        boll = self.calculate_boll(closes)

        # 计算均线
        ma5 = self.calculate_ma(closes, 5)
        ma10 = self.calculate_ma(closes, 10)
        ma20 = self.calculate_ma(closes, 20)
        ma60 = self.calculate_ma(closes, 60)

        # 获取最新信号
        latest_signals = self._get_latest_signals(macd, kdj, rsi, boll, ma5, ma10, ma20, closes)

        return {
            "dates": dates,
            "prices": {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes
            },
            "indicators": {
                "macd": macd,
                "kdj": kdj,
                "rsi": rsi,
                "boll": boll,
                "ma": {
                    "ma5": [round(v, 4) if v is not None else None for v in ma5],
                    "ma10": [round(v, 4) if v is not None else None for v in ma10],
                    "ma20": [round(v, 4) if v is not None else None for v in ma20],
                    "ma60": [round(v, 4) if v is not None else None for v in ma60]
                }
            },
            "latest_signals": latest_signals,
            "data_count": len(kline_data)
        }

    def _get_latest_signals(
        self,
        macd: Dict,
        kdj: Dict,
        rsi: Dict,
        boll: Dict,
        ma5: List,
        ma10: List,
        ma20: List,
        closes: List
    ) -> Dict[str, Any]:
        """获取最新的技术信号摘要"""
        signals = []
        bullish_count = 0
        bearish_count = 0

        # MACD信号
        macd_signal = macd["signal"][-1] if macd["signal"] else "neutral"
        if macd_signal == "golden_cross":
            signals.append({"indicator": "MACD", "signal": "金叉", "type": "buy"})
            bullish_count += 2
        elif macd_signal == "death_cross":
            signals.append({"indicator": "MACD", "signal": "死叉", "type": "sell"})
            bearish_count += 2
        elif macd_signal == "bullish":
            bullish_count += 1
        elif macd_signal == "bearish":
            bearish_count += 1

        # KDJ信号
        kdj_signal = kdj["signal"][-1] if kdj["signal"] else "neutral"
        if kdj_signal == "oversold_cross":
            signals.append({"indicator": "KDJ", "signal": "超卖金叉", "type": "buy"})
            bullish_count += 2
        elif kdj_signal == "overbought_cross":
            signals.append({"indicator": "KDJ", "signal": "超买死叉", "type": "sell"})
            bearish_count += 2
        elif kdj_signal == "golden_cross":
            signals.append({"indicator": "KDJ", "signal": "金叉", "type": "buy"})
            bullish_count += 1
        elif kdj_signal == "death_cross":
            signals.append({"indicator": "KDJ", "signal": "死叉", "type": "sell"})
            bearish_count += 1
        elif kdj_signal == "overbought":
            signals.append({"indicator": "KDJ", "signal": "超买", "type": "warning"})
        elif kdj_signal == "oversold":
            signals.append({"indicator": "KDJ", "signal": "超卖", "type": "warning"})

        # RSI信号
        rsi_signal = rsi["signal"][-1] if rsi["signal"] else "neutral"
        rsi_value = rsi["rsi"][-1] if rsi["rsi"] and rsi["rsi"][-1] is not None else 50
        if rsi_signal == "overbought":
            signals.append({"indicator": "RSI", "signal": f"超买({rsi_value:.1f})", "type": "sell"})
            bearish_count += 1
        elif rsi_signal == "oversold":
            signals.append({"indicator": "RSI", "signal": f"超卖({rsi_value:.1f})", "type": "buy"})
            bullish_count += 1

        # 布林带信号
        boll_signal = boll["signal"][-1] if boll["signal"] else "neutral"
        if boll_signal == "overbought":
            signals.append({"indicator": "BOLL", "signal": "触及上轨", "type": "warning"})
        elif boll_signal == "oversold":
            signals.append({"indicator": "BOLL", "signal": "触及下轨", "type": "warning"})

        # 均线信号
        if len(closes) > 0 and ma5[-1] is not None and ma10[-1] is not None:
            close = closes[-1]
            if close > ma5[-1] > ma10[-1]:
                signals.append({"indicator": "均线", "signal": "多头排列", "type": "buy"})
                bullish_count += 1
            elif close < ma5[-1] < ma10[-1]:
                signals.append({"indicator": "均线", "signal": "空头排列", "type": "sell"})
                bearish_count += 1

        # 综合评估
        if bullish_count > bearish_count + 2:
            overall = "强烈看多"
            overall_color = "#52c41a"
        elif bullish_count > bearish_count:
            overall = "偏多"
            overall_color = "#73d13d"
        elif bearish_count > bullish_count + 2:
            overall = "强烈看空"
            overall_color = "#f5222d"
        elif bearish_count > bullish_count:
            overall = "偏空"
            overall_color = "#ff7875"
        else:
            overall = "中性"
            overall_color = "#faad14"

        return {
            "signals": signals,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "overall": overall,
            "overall_color": overall_color,
            "latest_values": {
                "macd_dif": macd["dif"][-1] if macd["dif"] else None,
                "macd_dea": macd["dea"][-1] if macd["dea"] else None,
                "kdj_k": kdj["k"][-1] if kdj["k"] else None,
                "kdj_d": kdj["d"][-1] if kdj["d"] else None,
                "kdj_j": kdj["j"][-1] if kdj["j"] else None,
                "rsi": rsi["rsi"][-1] if rsi["rsi"] else None,
                "boll_upper": boll["upper"][-1] if boll["upper"] else None,
                "boll_middle": boll["middle"][-1] if boll["middle"] else None,
                "boll_lower": boll["lower"][-1] if boll["lower"] else None
            }
        }


# 全局实例
technical_service = TechnicalService()
