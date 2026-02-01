"""持仓模拟与盈亏跟踪服务"""
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """交易记录"""
    id: str = ""
    code: str
    name: str = ""
    type: str  # buy, sell
    price: float
    quantity: int
    amount: float = 0  # 成交金额
    fee: float = 0  # 手续费
    timestamp: str = ""
    note: str = ""


class Position(BaseModel):
    """持仓记录"""
    code: str
    name: str = ""
    quantity: int = 0  # 持仓数量
    cost_price: float = 0  # 成本价
    cost_amount: float = 0  # 成本金额
    current_price: float = 0  # 当前价
    current_amount: float = 0  # 当前市值
    profit: float = 0  # 盈亏金额
    profit_percent: float = 0  # 盈亏比例
    total_fee: float = 0  # 累计手续费
    first_buy_date: str = ""  # 首次买入日期
    last_trade_date: str = ""  # 最后交易日期


class PortfolioService:
    """持仓管理服务"""

    # 手续费率设置
    COMMISSION_RATE = 0.0003  # 佣金费率 0.03%
    MIN_COMMISSION = 5.0  # 最低佣金 5元
    STAMP_TAX_RATE = 0.001  # 印花税 0.1% (仅卖出收取)

    def __init__(self, data_file: str = "portfolio.json"):
        self.data_file = data_file
        self.positions: Dict[str, Position] = {}
        self.transactions: List[Transaction] = []
        self._load_data()

    def _load_data(self):
        """加载持仓数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.positions = {
                        k: Position(**v) for k, v in data.get("positions", {}).items()
                    }
                    self.transactions = [
                        Transaction(**t) for t in data.get("transactions", [])
                    ]
            except Exception as e:
                print(f"加载持仓数据失败: {e}")
                self.positions = {}
                self.transactions = []

    def _save_data(self):
        """保存持仓数据"""
        try:
            data = {
                "positions": {k: v.model_dump() for k, v in self.positions.items()},
                "transactions": [t.model_dump() for t in self.transactions]
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存持仓数据失败: {e}")

    def calculate_fee(self, price: float, quantity: int, is_sell: bool = False) -> float:
        """计算交易手续费"""
        amount = price * quantity

        # 佣金
        commission = max(amount * self.COMMISSION_RATE, self.MIN_COMMISSION)

        # 印花税（仅卖出）
        stamp_tax = amount * self.STAMP_TAX_RATE if is_sell else 0

        return round(commission + stamp_tax, 2)

    def buy(self, code: str, name: str, price: float, quantity: int, note: str = "") -> Dict[str, Any]:
        """买入股票"""
        if quantity <= 0 or price <= 0:
            return {"success": False, "message": "价格和数量必须大于0"}

        # 计算费用
        amount = price * quantity
        fee = self.calculate_fee(price, quantity, is_sell=False)
        total_cost = amount + fee

        # 更新持仓
        if code in self.positions:
            pos = self.positions[code]
            # 加仓：计算新的成本价
            new_quantity = pos.quantity + quantity
            new_cost_amount = pos.cost_amount + total_cost
            pos.quantity = new_quantity
            pos.cost_amount = new_cost_amount
            pos.cost_price = new_cost_amount / new_quantity
            pos.total_fee += fee
            pos.last_trade_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 新建持仓
            self.positions[code] = Position(
                code=code,
                name=name,
                quantity=quantity,
                cost_price=total_cost / quantity,
                cost_amount=total_cost,
                total_fee=fee,
                first_buy_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                last_trade_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        # 记录交易
        tx = Transaction(
            id=f"TX{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            code=code,
            name=name,
            type="buy",
            price=price,
            quantity=quantity,
            amount=amount,
            fee=fee,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note=note
        )
        self.transactions.append(tx)

        self._save_data()

        return {
            "success": True,
            "message": f"买入成功: {name} {quantity}股 @ {price}元",
            "transaction": tx.model_dump(),
            "position": self.positions[code].model_dump()
        }

    def sell(self, code: str, price: float, quantity: int, note: str = "") -> Dict[str, Any]:
        """卖出股票"""
        if code not in self.positions:
            return {"success": False, "message": f"未持有股票 {code}"}

        pos = self.positions[code]

        if quantity > pos.quantity:
            return {"success": False, "message": f"卖出数量超过持仓，当前持有 {pos.quantity} 股"}

        if quantity <= 0 or price <= 0:
            return {"success": False, "message": "价格和数量必须大于0"}

        # 计算费用
        amount = price * quantity
        fee = self.calculate_fee(price, quantity, is_sell=True)
        net_amount = amount - fee

        # 计算本次卖出的成本
        sell_cost = pos.cost_price * quantity

        # 更新持仓
        pos.quantity -= quantity
        pos.total_fee += fee
        pos.last_trade_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 计算盈亏
        profit = net_amount - sell_cost

        if pos.quantity == 0:
            # 清仓
            del self.positions[code]
        else:
            # 更新成本金额
            pos.cost_amount = pos.cost_price * pos.quantity

        # 记录交易
        tx = Transaction(
            id=f"TX{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            code=code,
            name=pos.name,
            type="sell",
            price=price,
            quantity=quantity,
            amount=amount,
            fee=fee,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note=note
        )
        self.transactions.append(tx)

        self._save_data()

        return {
            "success": True,
            "message": f"卖出成功: {pos.name} {quantity}股 @ {price}元，盈亏 {profit:.2f}元",
            "transaction": tx.model_dump(),
            "profit": profit,
            "remaining": pos.quantity if code in self.positions else 0
        }

    def update_prices(self, prices: Dict[str, Dict[str, Any]]):
        """更新持仓的当前价格"""
        for code, pos in self.positions.items():
            if code in prices:
                price_info = prices[code]
                pos.current_price = price_info.get("price", 0)
                pos.name = price_info.get("name", pos.name)
                pos.current_amount = pos.current_price * pos.quantity
                pos.profit = pos.current_amount - pos.cost_amount
                pos.profit_percent = (pos.profit / pos.cost_amount * 100) if pos.cost_amount > 0 else 0

        self._save_data()

    def get_positions(self) -> List[Dict[str, Any]]:
        """获取所有持仓"""
        return [pos.model_dump() for pos in self.positions.values()]

    def get_position(self, code: str) -> Optional[Dict[str, Any]]:
        """获取单个持仓"""
        if code in self.positions:
            return self.positions[code].model_dump()
        return None

    def get_transactions(self, code: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取交易记录"""
        txs = self.transactions
        if code:
            txs = [t for t in txs if t.code == code]

        # 按时间倒序
        txs = sorted(txs, key=lambda x: x.timestamp, reverse=True)

        return [t.model_dump() for t in txs[:limit]]

    def get_summary(self) -> Dict[str, Any]:
        """获取持仓汇总"""
        total_cost = sum(pos.cost_amount for pos in self.positions.values())
        total_current = sum(pos.current_amount for pos in self.positions.values())
        total_profit = total_current - total_cost
        total_fee = sum(pos.total_fee for pos in self.positions.values())

        # 统计盈亏股票数量
        profit_count = sum(1 for pos in self.positions.values() if pos.profit > 0)
        loss_count = sum(1 for pos in self.positions.values() if pos.profit < 0)

        return {
            "position_count": len(self.positions),
            "total_cost": round(total_cost, 2),
            "total_current": round(total_current, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_percent": round(total_profit / total_cost * 100, 2) if total_cost > 0 else 0,
            "total_fee": round(total_fee, 2),
            "profit_count": profit_count,
            "loss_count": loss_count,
            "transaction_count": len(self.transactions)
        }

    def clear_position(self, code: str) -> Dict[str, Any]:
        """删除持仓（不记录交易）"""
        if code in self.positions:
            pos = self.positions[code]
            del self.positions[code]
            self._save_data()
            return {"success": True, "message": f"已删除持仓 {pos.name}"}
        return {"success": False, "message": f"未找到持仓 {code}"}

    def clear_all(self) -> Dict[str, Any]:
        """清空所有持仓和交易记录"""
        self.positions = {}
        self.transactions = []
        self._save_data()
        return {"success": True, "message": "已清空所有数据"}


# 全局实例
portfolio_service = PortfolioService()
