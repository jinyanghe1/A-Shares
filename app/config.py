"""应用配置"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    app_name: str = "ClawdBot Stock Monitor"
    debug: bool = True

    # DeepSeek API 配置
    deepseek_api_key: Optional[str] = None

    # Biying API 配置 (备用行情源)
    biying_license: Optional[str] = None

    # 提醒配置
    alert_threshold_up: float = 3.0   # 涨幅提醒阈值（%）
    alert_threshold_down: float = -3.0  # 跌幅提醒阈值（%）
    consecutive_alert_count: int = 3  # 连续涨跌次数提醒

    # 数据刷新间隔（秒）
    refresh_interval: int = 10

    class Config:
        env_file = ".env"


# 默认股指列表
DEFAULT_INDICES = [
    {"code": "000016", "name": "上证50"},
    {"code": "000688", "name": "科创50"},
    {"code": "899050", "name": "北证50"},
    {"code": "399001", "name": "深证成指"},
    {"code": "000300", "name": "沪深300"},
    {"code": "000001", "name": "上证指数"},
]

# 默认大宗商品列表
DEFAULT_COMMODITIES = [
    {"code": "au", "name": "黄金", "unit": "元/克"},
    {"code": "sc", "name": "原油", "unit": "元/桶"},
    {"code": "rb", "name": "螺纹钢", "unit": "元/吨"},
    {"code": "cu", "name": "铜", "unit": "元/吨"},
]

settings = Settings()
