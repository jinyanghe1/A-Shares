"""DeepSeek API 服务 - 用于行情分析和新闻解读"""
import httpx
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import settings


class DeepSeekService:
    """DeepSeek API 服务"""

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self):
        self._client = None
        self.api_key = None

    def _get_api_key(self) -> str:
        """获取 API Key"""
        if self.api_key is None:
            self.api_key = getattr(settings, 'deepseek_api_key', None) or os.getenv('DEEPSEEK_API_KEY', '')
        return self.api_key

    @property
    def client(self) -> httpx.AsyncClient:
        """延迟初始化 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers={
                    "Authorization": f"Bearer {self._get_api_key()}",
                    "Content-Type": "application/json"
                },
                trust_env=False
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        调用 DeepSeek Chat API
        """
        if not self._get_api_key():
            return "DeepSeek API Key 未配置，请在 .env 文件中设置 DEEPSEEK_API_KEY"

        try:
            resp = await self.client.post(
                f"{self.BASE_URL}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )

            if resp.status_code != 200:
                error_msg = f"API 调用失败: {resp.status_code}"
                print(f"{error_msg} - Response: {resp.text[:200]}")
                return f"抱歉，AI分析服务暂时不可用。状态码: {resp.status_code}"

            try:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if not content:
                    print(f"DeepSeek 返回了空内容: {data}")
                    return "抱歉，AI分析未能生成有效内容，请稍后重试。"

                # 清理返回的内容，确保它是安全的字符串
                # 移除可能导致JSON序列化问题的特殊字符
                cleaned_content = str(content).strip()

                return cleaned_content

            except (ValueError, KeyError, IndexError) as e:
                error_text = resp.text[:200] if hasattr(resp, 'text') else "无法获取响应内容"
                print(f"解析 DeepSeek 响应失败: {e}, Response: {error_text}")
                return f"抱歉，AI返回的数据格式异常，请稍后重试。"

        except httpx.TimeoutException:
            print("DeepSeek API 请求超时")
            return "抱歉，AI分析请求超时，请稍后重试。"
        except httpx.HTTPError as e:
            print(f"DeepSeek API HTTP 错误: {e}")
            return f"抱歉，AI分析服务连接失败，请检查网络连接。"
        except Exception as e:
            print(f"DeepSeek API 调用异常: {type(e).__name__}: {str(e)}")
            return f"抱歉，AI分析出现未知错误，请稍后重试。"

    async def analyze_news(self, news_title: str, news_content: str, stock_name: str = "") -> str:
        """
        解读新闻/公告
        """
        system_prompt = """你是一位专业的股票分析师，擅长解读上市公司新闻和公告。
请用简洁专业的语言分析新闻内容，包括：
1. 新闻核心内容摘要
2. 对公司/股价可能的影响（利好/利空/中性）
3. 投资者应关注的要点
4. 风险提示（如有）

请用中文回答，保持客观专业。"""

        user_prompt = f"""请分析以下{'关于 ' + stock_name + ' 的' if stock_name else ''}新闻/公告：

标题：{news_title}

内容：{news_content}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return await self._chat_completion(messages)

    async def analyze_stock_trend(
        self,
        code: str,
        name: str,
        price: float,
        change_percent: float,
        volume: float,
        turnover_rate: float,
        main_net_inflow: Optional[float] = None
    ) -> str:
        """
        分析股票行情走势
        """
        system_prompt = """你是一位专业的股票技术分析师。
请根据提供的股票数据，给出简短的行情分析和操作建议。
分析应包括：
1. 当日表现评价
2. 成交量/换手率分析
3. 资金流向解读（如有数据）
4. 短期趋势判断
5. 注意事项

请用中文回答，保持简洁客观。不构成投资建议。"""

        data_str = f"""
股票：{name}（{code}）
当前价格：{price:.2f} 元
涨跌幅：{change_percent:+.2f}%
成交量：{volume/10000:.2f} 万手
换手率：{turnover_rate:.2f}%"""

        if main_net_inflow is not None:
            data_str += f"\n主力净流入：{main_net_inflow/10000:.2f} 万元"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下股票数据：{data_str}"}
        ]

        return await self._chat_completion(messages, temperature=0.5)

    async def interpret_announcement(self, title: str, content: str) -> str:
        """
        解读公司公告
        """
        system_prompt = """你是一位专业的证券分析师，擅长解读上市公司公告。
请对公告进行专业解读，包括：
1. 公告类型和核心内容
2. 对公司经营的影响
3. 对股价的潜在影响（利好/利空/中性）
4. 关键数据或时间节点
5. 投资者需要注意的风险

请用中文回答，保持专业客观。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请解读以下公告：\n\n标题：{title}\n\n内容：{content}"}
        ]

        return await self._chat_completion(messages)

    async def generate_daily_summary(
        self,
        watch_list_data: List[Dict[str, Any]],
        market_sentiment: Dict[str, Any],
        indices_data: List[Dict[str, Any]]
    ) -> str:
        """
        生成每日盯盘总结
        """
        system_prompt = """你是一位专业的投资顾问助手。
请根据用户关注的股票数据、市场大盘指数和市场情绪情况，生成一份结构化的每日盯盘总结。

请返回 **纯 JSON 格式** 的数据，不要包含 Markdown 格式标记（如 ```json ... ```）。
JSON 结构如下：
{
    "market_overview": "市场整体情况简述（包括大盘指数表现和市场情绪）",
    "indices_analysis": [
        {"name": "指数名称", "change": "涨跌幅描述", "analysis": "简评"}
    ],
    "watch_list_summary": "关注股票表现概览",
    "hot_stocks": [
        {"name": "股票名称", "code": "代码", "reason": "关注理由"}
    ],
    "focus_tomorrow": "明日关注要点",
    "risks": "风险提示"
}

请确保 JSON 格式合法。内容语言简洁专业。"""

        # 构建股票数据摘要
        stocks_summary = "\n".join([
            f"- {s.get('name', '')}({s.get('code', '')}): {s.get('price', 0):.2f}元, "
            f"涨跌幅 {s.get('change_percent', 0):+.2f}%"
            for s in watch_list_data[:15]  # 最多15只
        ])

        # 构建指数数据摘要
        indices_summary = "\n".join([
            f"- {idx.get('name', '')}: {idx.get('price', 0):.2f}, 涨跌幅 {idx.get('change_percent', 0):+.2f}%"
            for idx in indices_data
        ])

        market_str = f"""
市场数据：
- 上涨家数：{market_sentiment.get('up_count', 0)}
- 下跌家数：{market_sentiment.get('down_count', 0)}
- 涨停家数：{market_sentiment.get('limit_up_count', 0)}
- 跌停家数：{market_sentiment.get('limit_down_count', 0)}
- 北向资金：{market_sentiment.get('north_net_inflow', 0):.2f}亿"""

        user_content = f"""请生成今日盯盘总结：

主要股指表现：
{indices_summary}

{market_str}

关注股票表现：
{stocks_summary}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return await self._chat_completion(messages, max_tokens=2000)


# 创建全局实例
deepseek_service = DeepSeekService()
