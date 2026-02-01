"""数据导出路由"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List
import csv
import io
from datetime import datetime

from app.services.stock_service import stock_service
from app.services.finance_service import finance_service
from app.utils.eastmoney import eastmoney_api

router = APIRouter(prefix="/api/export", tags=["数据导出"])


@router.get("/stock/{code}/kline", summary="导出K线数据为CSV")
async def export_kline_csv(
    code: str,
    days: int = Query(60, description="导出天数", ge=1, le=5000)
):
    """
    导出股票历史K线数据为CSV格式
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取K线数据
    kline_data = await eastmoney_api.get_kline_data(code, days=days)

    if not kline_data:
        raise HTTPException(status_code=400, detail=f"无法获取 {quote.name} 的K线数据")

    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow([
        '日期', '开盘价', '收盘价', '最高价', '最低价',
        '成交量', '成交额', '振幅(%)', '涨跌幅(%)', '换手率(%)'
    ])

    # 写入数据
    for row in kline_data:
        writer.writerow([
            row.get('date', ''),
            row.get('open', ''),
            row.get('close', ''),
            row.get('high', ''),
            row.get('low', ''),
            row.get('volume', ''),
            row.get('amount', ''),
            row.get('amplitude', ''),
            row.get('change_percent', ''),
            row.get('turnover_rate', '')
        ])

    # 准备响应
    output.seek(0)
    filename = f"{quote.name}_{code}_kline_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter(['\ufeff' + output.getvalue()]),  # 添加BOM以支持Excel中文
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.get("/watchlist", summary="导出关注列表为CSV")
async def export_watchlist_csv():
    """
    导出关注列表及最新行情为CSV格式
    """
    # 获取关注列表行情
    quotes = await stock_service.get_watch_list_quotes()

    if not quotes:
        raise HTTPException(status_code=400, detail="关注列表为空")

    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow([
        '代码', '名称', '分组', '现价', '涨跌幅(%)', '涨跌额',
        '开盘价', '最高价', '最低价', '昨收价',
        '成交量', '成交额', '换手率(%)', '市盈率', '总市值', '流通市值'
    ])

    # 写入数据
    for item in quotes:
        quote = item.get('quote', {})
        writer.writerow([
            item.get('code', ''),
            item.get('name', ''),
            item.get('group', '默认'),
            quote.get('price', ''),
            quote.get('change_percent', ''),
            quote.get('change', ''),
            quote.get('open_price', ''),
            quote.get('high_price', ''),
            quote.get('low_price', ''),
            quote.get('pre_close', ''),
            quote.get('volume', ''),
            quote.get('amount', ''),
            quote.get('turnover_rate', ''),
            quote.get('pe_ratio', ''),
            quote.get('total_value', ''),
            quote.get('flow_value', '')
        ])

    output.seek(0)
    filename = f"watchlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter(['\ufeff' + output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.get("/stock/{code}/finance", summary="导出财务数据为CSV")
async def export_finance_csv(code: str):
    """
    导出股票财务指标数据为CSV格式
    """
    # 获取股票信息
    quote = await stock_service.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {code}")

    # 获取财务数据
    finance_data = await finance_service.get_comprehensive_finance(code)

    if not finance_data:
        raise HTTPException(status_code=400, detail=f"无法获取 {quote.name} 的财务数据")

    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入财务指标
    writer.writerow(['===== 主要财务指标 ====='])
    writer.writerow([
        '报告期', '报告类型', '每股收益(EPS)', '每股净资产(BPS)',
        '净资产收益率(ROE)', '毛利率', '净利率', '资产负债率'
    ])

    for ind in finance_data.get('indicators', []):
        writer.writerow([
            ind.get('report_date', ''),
            ind.get('report_type', ''),
            ind.get('eps', ''),
            ind.get('bps', ''),
            ind.get('roe', ''),
            ind.get('gross_margin', ''),
            ind.get('net_margin', ''),
            ind.get('debt_ratio', '')
        ])

    writer.writerow([])

    # 写入利润表
    writer.writerow(['===== 利润表 ====='])
    writer.writerow([
        '报告期', '营业总收入', '营业总成本', '营业利润',
        '利润总额', '净利润', '归母净利润'
    ])

    for inc in finance_data.get('income_statement', []):
        writer.writerow([
            inc.get('report_date', ''),
            inc.get('revenue', ''),
            inc.get('operating_cost', ''),
            inc.get('gross_profit', ''),
            inc.get('total_profit', ''),
            inc.get('net_profit', ''),
            inc.get('parent_net_profit', '')
        ])

    writer.writerow([])

    # 写入资产负债表
    writer.writerow(['===== 资产负债表 ====='])
    writer.writerow([
        '报告期', '总资产', '总负债', '所有者权益',
        '流动资产', '流动负债', '货币资金', '存货'
    ])

    for bal in finance_data.get('balance_sheet', []):
        writer.writerow([
            bal.get('report_date', ''),
            bal.get('total_assets', ''),
            bal.get('total_liabilities', ''),
            bal.get('total_equity', ''),
            bal.get('current_assets', ''),
            bal.get('current_liabilities', ''),
            bal.get('cash', ''),
            bal.get('inventory', '')
        ])

    writer.writerow([])

    # 写入现金流量表
    writer.writerow(['===== 现金流量表 ====='])
    writer.writerow([
        '报告期', '经营活动现金流净额', '投资活动现金流净额',
        '筹资活动现金流净额', '现金净增加额'
    ])

    for cf in finance_data.get('cash_flow', []):
        writer.writerow([
            cf.get('report_date', ''),
            cf.get('operating_cash_flow', ''),
            cf.get('investing_cash_flow', ''),
            cf.get('financing_cash_flow', ''),
            cf.get('net_cash_increase', '')
        ])

    output.seek(0)
    filename = f"{quote.name}_{code}_finance_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter(['\ufeff' + output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.get("/portfolio", summary="导出持仓数据为CSV")
async def export_portfolio_csv():
    """
    导出持仓数据和交易记录为CSV格式
    """
    from app.services.portfolio_service import portfolio_service

    positions = portfolio_service.get_all_positions()

    if not positions:
        raise HTTPException(status_code=400, detail="暂无持仓数据")

    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入持仓汇总
    writer.writerow(['===== 持仓汇总 ====='])
    writer.writerow([
        '代码', '名称', '持仓数量', '持仓成本', '当前市值',
        '盈亏金额', '盈亏比例(%)', '买入日期'
    ])

    for pos in positions:
        writer.writerow([
            pos.get('code', ''),
            pos.get('name', ''),
            pos.get('shares', ''),
            pos.get('cost', ''),
            pos.get('current_value', ''),
            pos.get('profit', ''),
            pos.get('profit_percent', ''),
            pos.get('buy_date', '')
        ])

    writer.writerow([])

    # 写入交易记录
    writer.writerow(['===== 交易记录 ====='])
    summary = portfolio_service.get_summary()
    transactions = summary.get('transactions', [])

    writer.writerow([
        '时间', '代码', '名称', '类型', '数量', '价格', '金额', '手续费'
    ])

    for tx in transactions:
        writer.writerow([
            tx.get('time', ''),
            tx.get('code', ''),
            tx.get('name', ''),
            tx.get('type', ''),
            tx.get('shares', ''),
            tx.get('price', ''),
            tx.get('amount', ''),
            tx.get('fee', '')
        ])

    output.seek(0)
    filename = f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter(['\ufeff' + output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.get("/sectors/{sector_type}", summary="导出板块数据为CSV")
async def export_sectors_csv(
    sector_type: str = "industry",
    count: int = Query(100, description="导出数量", ge=1, le=500)
):
    """
    导出板块数据为CSV格式
    sector_type: industry(行业), concept(概念)
    """
    # 获取板块数据
    sectors = await eastmoney_api.get_sector_list(sector_type)

    if not sectors:
        raise HTTPException(status_code=400, detail="无法获取板块数据")

    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)

    type_name = "行业" if sector_type == "industry" else "概念"

    writer.writerow([f'{type_name}板块数据'])
    writer.writerow([
        '代码', '名称', '涨跌幅(%)', '成交额', '换手率(%)',
        '上涨家数', '下跌家数', '领涨股'
    ])

    for sector in sectors[:count]:
        writer.writerow([
            sector.get('code', ''),
            sector.get('name', ''),
            sector.get('change_percent', ''),
            sector.get('turnover', ''),
            sector.get('turnover_rate', ''),
            sector.get('up_count', ''),
            sector.get('down_count', ''),
            sector.get('lead_stock', '')
        ])

    output.seek(0)
    filename = f"{type_name}板块_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter(['\ufeff' + output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )
