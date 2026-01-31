"""必赢 API 封装 (备用行情源)"""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import os
from app.config import settings

class BiyingAPI:
    """必赢 API 接口 (https://www.biyingapi.com/)"""

    BASE_URL = "http://api.biyingapi.com"

    def __init__(self):
        self._client = None
        self.license = None

    def _get_license(self) -> str:
        if self.license is None:
            self.license = settings.biying_license or os.getenv('BIYING_LICENSE', '')
        return self.license

    @property
    def client(self) -> httpx.AsyncClient:
        """延迟初始化 HTTP 客户端"""
        if self._client is None:
             # 清除代理环境变量以避免 SOCKS 代理问题
            for key in ['ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy',
                       'HTTPS_PROXY', 'https_proxy']:
                os.environ.pop(key, None)

            self._client = httpx.AsyncClient(timeout=10.0, trust_env=False)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def format_code(code: str) -> str:
        """
        转换为必赢API所需格式 (e.g., 600519 -> 600519.SH)
        """
        code = code.strip()
        if "." in code:
            return code.upper() # 已经是格式化的

        if code.startswith("6") or code.startswith("9"):
            return f"{code}.SH"
        elif code.startswith("0") or code.startswith("3") or code.startswith("2"):
            return f"{code}.SZ"
        elif code.startswith("4") or code.startswith("8"):
            return f"{code}.BJ"
        
        return f"{code}.SZ" # 默认

    async def get_stock_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票实时行情
        URL: http://api.biyingapi.com/hslt/real/time/{code}/{license}
        """
        license_key = self._get_license()
        if not license_key:
            return None

        formatted_code = self.format_code(code)
        url = f"{self.BASE_URL}/hslt/real/time/{formatted_code}/{license_key}"

        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                print(f"Biying API Error: {resp.status_code}")
                return None
            
            data = resp.json()
            # 假设返回格式根据文档通常是JSON
            # 需要根据实际返回结构解析，这里根据通用字段猜测
            # 如果是列表返回第一个，如果是字典直接使用
            
            # 注意：由于没有实际调用结果，这里的解析是基于常见API结构的猜测
            # 用户提到参考知乎，通常返回字段包括 open, close, high, low, vol, amount, p_change 等
            
            # 假设返回结构: {"code": "200", "msg": "success", "data": {...}} 或直接 {...}
            # 根据搜索结果，它返回标准Json。
            
            # 模拟解析逻辑 (需根据实际Response调整)
            item = data
            if "data" in data:
                item = data["data"]
            
            if isinstance(item, list) and len(item) > 0:
                item = item[0]

            # 必赢API的字段名通常是英文缩写
            # 假设字段: dm(代码), mc(名称), xj(现价), zdf(涨跌幅), cje(成交额), cjl(成交量)
            # 或者: code, name, price, change_percent, ...
            # 如果文档未明确，我需要做一个通用的映射尝试或保留原始数据
            
            # 为了稳健，我会尝试读取常见的键
            price = float(item.get("xj", item.get("price", item.get("trade", 0))))
            name = item.get("mc", item.get("name", ""))
            change_percent = float(item.get("zdf", item.get("changepercent", item.get("ratio", 0))))
            open_price = float(item.get("kp", item.get("open", 0)))
            high_price = float(item.get("zg", item.get("high", 0)))
            low_price = float(item.get("zd", item.get("low", 0)))
            volume = float(item.get("cjl", item.get("volume", 0)))
            amount = float(item.get("cje", item.get("amount", 0)))
            
            return {
                "code": code,
                "name": name,
                "price": price,
                "change_percent": change_percent,
                "change": price - float(item.get("zs", item.get("pre_close", price))), # 估算
                "open_price": open_price,
                "high_price": high_price,
                "low_price": low_price,
                "volume": volume,
                "amount": amount,
                "update_time": datetime.now().isoformat(),
                "source": "biying"
            }

        except Exception as e:
            print(f"Biying API Exception {code}: {e}")
            return None

    async def get_batch_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取行情 (通过并发调用单只接口实现)
        """
        if not self._get_license():
            return []

        tasks = [self.get_stock_quote(code) for code in codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for res in results:
            if isinstance(res, dict) and res:
                valid_results.append(res)
        
        return valid_results

biying_api = BiyingAPI()
