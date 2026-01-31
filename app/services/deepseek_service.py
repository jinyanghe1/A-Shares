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
                return f"API 调用失败: {resp.status_code} - {resp.text}"

            data = resp.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            return f"API 调用出错: {str(e)}"

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

    async def analyze_market_sentiment(
        self,
        up_count: int,
        down_count: int,
        limit_up_count: int,
        limit_down_count: int,
        north_net_inflow: float
    ) -> str:
        """
        分析市场情绪
        """
        system_prompt = """你是一位专业的市场分析师。
请根据提供的市场数据，分析当前市场情绪和投资环境。
分析应包括：
1. 市场整体情绪判断（恐慌/谨慎/中性/乐观/狂热）
2. 涨跌比分析
3. 涨停跌停情况解读
4. 北向资金动向解读
5. 操作建议

请用中文回答，保持客观专业。不构成投资建议。"""

        data_str = f"""
上涨家数：{up_count}
下跌家数：{down_count}
涨停家数：{limit_up_count}
跌停家数：{limit_down_count}
北向资金净流入：{north_net_inflow:.2f} 亿元"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下市场数据：{data_str}"}
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
        market_sentiment: Dict[str, Any]
    ) -> str:
        """
        生成每日盯盘总结
        """
        system_prompt = """你是一位专业的投资顾问助手。
请根据用户关注的股票数据和市场情况，生成一份简洁的每日盯盘总结。
总结应包括：
1. 市场整体情况
2. 关注股票表现概览
3. 值得关注的异动股票
4. 明日关注要点
5. 风险提示

请用中文回答，语言简洁专业。"""

        # 构建股票数据摘要
        stocks_summary = "\n".join([
            f"- {s.get('name', '')}({s.get('code', '')}): {s.get('price', 0):.2f}元, "
            f"涨跌幅 {s.get('change_percent', 0):+.2f}%"
            for s in watch_list_data[:10]  # 最多10只
        ])

        market_str = f"""
市场数据：
- 上涨家数：{market_sentiment.get('up_count', 0)}
- 下跌家数：{market_sentiment.get('down_count', 0)}
- 涨停家数：{market_sentiment.get('limit_up_count', 0)}
- 跌停家数：{market_sentiment.get('limit_down_count', 0)}
- 北向资金：{market_sentiment.get('north_net_inflow', 0):.2f}亿"""

        user_content = f"""请生成今日盯盘总结：

{market_str}

关注股票表现：
{stocks_summary}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return await self._chat_completion(messages, max_tokens=1500)


# 创建全局实例
deepseek_service = DeepSeekService()
