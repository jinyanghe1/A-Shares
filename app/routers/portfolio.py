"""持仓管理路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.services.portfolio_service import portfolio_service
from app.services.stock_service import stock_service

router = APIRouter(prefix="/api/portfolio", tags=["持仓管理"])


class BuyRequest(BaseModel):
    """买入请求"""
    code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    price: float = Field(..., description="买入价格", gt=0)
    quantity: int = Field(..., description="买入数量", gt=0)
    note: str = Field("", description="备注")


class SellRequest(BaseModel):
    """卖出请求"""
    code: str = Field(..., description="股票代码")
    price: float = Field(..., description="卖出价格", gt=0)
    quantity: int = Field(..., description="卖出数量", gt=0)
    note: str = Field("", description="备注")


@router.get("/positions", summary="获取所有持仓")
async def get_positions(
    update_price: bool = Query(True, description="是否更新实时价格")
):
    """
    获取所有持仓列表
    可选择是否更新实时价格
    """
    positions = portfolio_service.get_positions()

    # 更新实时价格
    if update_price and positions:
        codes = [p["code"] for p in positions]
        prices = {}

        for code in codes:
            quote = await stock_service.get_quote(code)
            if quote:
                prices[code] = {
                    "price": quote.price,
                    "name": quote.name,
                    "change_percent": quote.change_percent
                }

        portfolio_service.update_prices(prices)
        positions = portfolio_service.get_positions()

        # 添加今日涨跌幅
        for pos in positions:
            if pos["code"] in prices:
                pos["today_change"] = prices[pos["code"]].get("change_percent", 0)

    return {
        "success": True,
        "data": {
            "positions": positions,
            "count": len(positions)
        }
    }


@router.get("/positions/{code}", summary="获取单个持仓")
async def get_position(code: str):
    """
    获取指定股票的持仓详情
    """
    position = portfolio_service.get_position(code)

    if not position:
        raise HTTPException(status_code=404, detail=f"未持有股票 {code}")

    # 更新实时价格
    quote = await stock_service.get_quote(code)
    if quote:
        portfolio_service.update_prices({
            code: {"price": quote.price, "name": quote.name}
        })
        position = portfolio_service.get_position(code)
        position["today_change"] = quote.change_percent

    return {
        "success": True,
        "data": position
    }


@router.post("/buy", summary="买入股票")
async def buy_stock(request: BuyRequest):
    """
    买入股票
    自动计算手续费并更新持仓
    """
    # 如果没有提供名称，尝试获取
    name = request.name
    if not name:
        quote = await stock_service.get_quote(request.code)
        name = quote.name if quote else request.code

    result = portfolio_service.buy(
        code=request.code,
        name=name,
        price=request.price,
        quantity=request.quantity,
        note=request.note
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/sell", summary="卖出股票")
async def sell_stock(request: SellRequest):
    """
    卖出股票
    自动计算手续费和盈亏
    """
    result = portfolio_service.sell(
        code=request.code,
        price=request.price,
        quantity=request.quantity,
        note=request.note
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/summary", summary="获取持仓汇总")
async def get_summary(
    update_price: bool = Query(True, description="是否更新实时价格")
):
    """
    获取持仓汇总统计
    包括总市值、总盈亏等
    """
    # 先更新价格
    if update_price:
        positions = portfolio_service.get_positions()
        if positions:
            codes = [p["code"] for p in positions]
            prices = {}
            for code in codes:
                quote = await stock_service.get_quote(code)
                if quote:
                    prices[code] = {"price": quote.price, "name": quote.name}
            portfolio_service.update_prices(prices)

    summary = portfolio_service.get_summary()

    return {
        "success": True,
        "data": summary
    }


@router.get("/transactions", summary="获取交易记录")
async def get_transactions(
    code: Optional[str] = Query(None, description="股票代码筛选"),
    limit: int = Query(50, description="返回数量", ge=1, le=200)
):
    """
    获取交易历史记录
    """
    transactions = portfolio_service.get_transactions(code=code, limit=limit)

    return {
        "success": True,
        "data": {
            "transactions": transactions,
            "count": len(transactions)
        }
    }


@router.delete("/positions/{code}", summary="删除持仓")
async def delete_position(code: str):
    """
    删除指定持仓（不记录交易）
    """
    result = portfolio_service.clear_position(code)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.delete("/clear", summary="清空所有数据")
async def clear_all():
    """
    清空所有持仓和交易记录
    谨慎使用！
    """
    result = portfolio_service.clear_all()
    return result


@router.get("/calculate-fee", summary="计算交易手续费")
async def calculate_fee(
    price: float = Query(..., description="交易价格", gt=0),
    quantity: int = Query(..., description="交易数量", gt=0),
    is_sell: bool = Query(False, description="是否卖出")
):
    """
    预估交易手续费
    """
    fee = portfolio_service.calculate_fee(price, quantity, is_sell)
    amount = price * quantity

    return {
        "success": True,
        "data": {
            "amount": amount,
            "fee": fee,
            "net_amount": amount - fee if is_sell else amount + fee,
            "fee_rate": round(fee / amount * 100, 4)
        }
    }
