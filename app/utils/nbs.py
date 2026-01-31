"""国家统计局 API 封装"""
import httpx
import time
import json
import os
from typing import Optional, List, Dict, Any

class NBSAPI:
    """国家统计局数据接口 (stats.gov.cn)"""
    
    BASE_URL = "https://data.stats.gov.cn/easyquery.htm"
    
    # 常用指标代码
    INDICATORS = {
        "CPI_MONTHLY": "A01030101",   # 居民消费价格指数(上年同月=100)
        "PMI_MANUFACTURING": "A0B0101", # 制造业采购经理指数
        "PMI_NON_MANUFACTURING": "A0B0201", # 非制造业商务活动指数
    }

    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """延迟初始化 HTTP 客户端（禁用代理以避免 SSL 问题）"""
        if self._client is None:
            # 清除代理环境变量
            for key in ['ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy', 
                       'HTTPS_PROXY', 'https_proxy']:
                os.environ.pop(key, None)
                
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://data.stats.gov.cn/easyquery.htm?cn=A01",
                "Origin": "https://data.stats.gov.cn",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
            # verify=False 因为国家统计局证书链有时不完整
            self._client = httpx.AsyncClient(
                timeout=30.0, 
                headers=headers, 
                verify=False, 
                trust_env=False,
                follow_redirects=True
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_timestamp(self) -> str:
        return str(int(time.time() * 1000))

    async def query_data(self, indicator_code: str, dbcode: str = "hgyd", last_n: int = 12, sub_indicator: str = None) -> List[Dict[str, Any]]:
        """
        查询数据
        :param indicator_code: 指标代码 (如 PMI 的父代码)
        :param dbcode: 数据库代码
        :param last_n: 最近 N 期
        :param sub_indicator: 具体子指标代码 (如 PMI 的具体项)
        """
        wds = [{"wdcode": "zb", "valuecode": indicator_code}]
        dfwds = [{"wdcode": "sj", "valuecode": f"LAST{last_n}"}]
        
        params = {
            "m": "QueryData",
            "dbcode": dbcode,
            "rowcode": "zb",
            "colcode": "sj",
            "wds": json.dumps(wds),
            "dfwds": json.dumps(dfwds),
            "k1": self._get_timestamp()
        }
        
        try:
            resp = await self.client.post(self.BASE_URL, data=params)
            if resp.status_code != 200:
                print(f"NBS API Error: {resp.status_code}")
                return []
                
            data = resp.json()
            if not data or "returndata" not in data:
                return []
            
            datanodes = data["returndata"].get("datanodes", [])
            wdnodes = data["returndata"].get("wdnodes", [])
            
            # 解析数据
            results = []
            if not datanodes:
                return []
                
            # 找到时间维度的映射
            time_nodes = next((node["nodes"] for node in wdnodes if node["wdcode"] == "sj"), [])
            time_map = {node["code"]: node["name"] for node in time_nodes}
            
            # Debug: print zb nodes
            zb_nodes = next((node["nodes"] for node in wdnodes if node["wdcode"] == "zb"), [])
            print("Returned Indicators:", [(n["code"], n["name"]) for n in zb_nodes])

            for node in datanodes:
                # 解析 valuecode 找到对应的时间
                wds_list = node.get("wds", [])
                
                # 过滤子指标
                zb_code = next((wd["valuecode"] for wd in wds_list if wd["wdcode"] == "zb"), None)
                if sub_indicator and zb_code != sub_indicator:
                    continue
                # 如果没指定 sub_indicator，默认只取第一个匹配的或者全部（这里简化为只取第一个匹配的，防止重复）
                # 实际上 NBS 接口返回的是一组相关的 zb，我们需要明确指定我们要哪个
                # 如果没指定 sub_indicator, 但返回了多个 zb，我们可能需要全部返回或者调用者需要知道他在做什么
                
                time_code = next((wd["valuecode"] for wd in wds_list if wd["wdcode"] == "sj"), None)
                
                if time_code and time_code in time_map:
                    value = node["data"]["data"]
                    results.append({
                        "date": time_map[time_code], # e.g. "2023年12月"
                        "value": value,
                        "code": time_code
                    })
            
            # 按时间倒序排序
            results.sort(key=lambda x: x["code"], reverse=True)
            return results
            
        except Exception as e:
            print(f"NBS API Exception: {e}")
            return []

    async def get_cpi_monthly(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """获取月度 CPI (同比) - A01030101"""
        return await self.query_data("A010301", "hgyd", last_n, sub_indicator="A01030101")
        
    async def get_pmi_manufacturing(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """获取制造业 PMI - A0B0101"""
        # PMI 数据通常在 A0B01 下，制造业 PMI 是 A0B0101
        return await self.query_data("A0B01", "hgyd", last_n, sub_indicator="A0B0101")

    async def get_pmi_non_manufacturing(self, last_n: int = 12) -> List[Dict[str, Any]]:
        """获取非制造业 PMI - A0B0201"""
        return await self.query_data("A0B02", "hgyd", last_n, sub_indicator="A0B0201")

# 全局实例
nbs_api = NBSAPI()
