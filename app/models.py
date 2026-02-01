"""数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class StockType(str, Enum):
    """股票类型"""
    A_SHARE = "a_share"      # A股
    INDEX = "index"          # 指数
    FUTURES = "futures"      # 期货
    ETF = "etf"             # ETF


class Stock(BaseModel):
    """股票基本信息"""
    code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    market: str = Field("", description="市场（sh/sz/bj）")
    stock_type: StockType = Field(StockType.A_SHARE, description="股票类型")


class StockQuote(BaseModel):
    """股票行情数据"""
    code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    price: float = Field(0, description="当前价格")
    change: float = Field(0, description="涨跌额")
    change_percent: float = Field(0, description="涨跌幅（%）")
    open_price: float = Field(0, description="开盘价")
    high_price: float = Field(0, description="最高价")
    low_price: float = Field(0, description="最低价")
    pre_close: float = Field(0, description="昨收价")
    volume: float = Field(0, description="成交量（手）")
    amount: float = Field(0, description="成交额（元）")
    turnover_rate: float = Field(0, description="换手率（%）")
    pe_ratio: Optional[float] = Field(None, description="市盈率")
    pb_ratio: Optional[float] = Field(None, description="市净率")
    total_value: Optional[float] = Field(None, description="总市值")
    flow_value: Optional[float] = Field(None, description="流通市值")
    update_time: datetime = Field(default_factory=datetime.now, description="更新时间")


class WatchListItem(BaseModel):
    """关注列表项"""
    code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    added_time: datetime = Field(default_factory=datetime.now, description="添加时间")
    alert_up: Optional[float] = Field(None, description="涨幅提醒阈值")
    alert_down: Optional[float] = Field(None, description="跌幅提醒阈值")
    note: str = Field("", description="备注")
    group: str = Field("default", description="分组名称")


class AlertType(str, Enum):
    """提醒类型"""
    PRICE_UP = "price_up"        # 价格上涨
    PRICE_DOWN = "price_down"    # 价格下跌
    CONSECUTIVE_UP = "consecutive_up"    # 连续上涨
    CONSECUTIVE_DOWN = "consecutive_down"  # 连续下跌


class Alert(BaseModel):
    """提醒信息"""
    code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    alert_type: AlertType = Field(..., description="提醒类型")
    message: str = Field("", description="提醒内容")
    current_price: float = Field(0, description="当前价格")
    change_percent: float = Field(0, description="涨跌幅")
    triggered_at: datetime = Field(default_factory=datetime.now, description="触发时间")
    is_sent: bool = Field(False, description="是否已发送")


class MarketSentiment(BaseModel):
    """市场情绪数据"""
    date: datetime = Field(default_factory=datetime.now, description="日期")
    up_count: int = Field(0, description="上涨家数")
    down_count: int = Field(0, description="下跌家数")
    flat_count: int = Field(0, description="平盘家数")
    limit_up_count: int = Field(0, description="涨停家数")
    limit_down_count: int = Field(0, description="跌停家数")
    main_net_inflow: float = Field(0, description="主力净流入（亿）")
    north_net_inflow: float = Field(0, description="北向资金净流入（亿）")


class CapitalFlow(BaseModel):
    """资金流向"""
    code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    main_net_inflow: float = Field(0, description="主力净流入（万）")
    main_net_ratio: float = Field(0, description="主力净占比（%）")
    super_large_net: float = Field(0, description="超大单净流入（万）")
    large_net: float = Field(0, description="大单净流入（万）")
    medium_net: float = Field(0, description="中单净流入（万）")
    small_net: float = Field(0, description="小单净流入（万）")
    update_time: datetime = Field(default_factory=datetime.now, description="更新时间")


# 请求/响应模型
class AddWatchRequest(BaseModel):
    """添加关注请求"""
    code: str = Field(..., description="股票代码")
    alert_up: Optional[float] = Field(None, description="涨幅提醒阈值")
    alert_down: Optional[float] = Field(None, description="跌幅提醒阈值")
    note: str = Field("", description="备注")
    group: str = Field("default", description="分组名称")


class AlertSettingRequest(BaseModel):
    """提醒设置请求"""
    code: str = Field(..., description="股票代码")
    alert_up: Optional[float] = Field(None, description="涨幅提醒阈值")
    alert_down: Optional[float] = Field(None, description="跌幅提醒阈值")
    consecutive_count: int = Field(3, description="连续涨跌次数提醒")


class ApiResponse(BaseModel):
    """通用 API 响应"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("", description="消息")
    data: Optional[dict] = Field(None, description="数据")


# 相关性分析模型
class CorrelationRequest(BaseModel):
    """相关性分析请求"""
    code1: str = Field(..., description="股票/指数1代码")
    code2: str = Field(..., description="股票/指数2代码")
    days: int = Field(60, description="分析天数", ge=5, le=5000)
    indicators: List[str] = Field(
        default=["turnover_rate", "amplitude", "ma5"],
        description="分析指标列表"
    )


class CorrelationResult(BaseModel):
    """相关性分析结果"""
    code1: str = Field(..., description="股票1代码")
    code2: str = Field(..., description="股票2代码")
    name1: str = Field(..., description="股票1名称")
    name2: str = Field(..., description="股票2名称")
    correlation_matrix: dict = Field(..., description="相关性矩阵")
    time_series: List[dict] = Field(..., description="时间序列数据")
