from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.user import User, UserSettings
from app.models.trade import (
    TradeOrder,
    OrderType,
    OrderSide,
    OrderStatus,
    TradeExecution,
    Position,
)
from app.models.stock import Stock
from app.services.questrade import QuestradeClient
from .risk_manager import RiskManager


class TradeExecutor:
    """Executes trades through Questrade or paper trading"""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.risk_manager = RiskManager(db, user)
        self.settings = self._get_user_settings()

    def _get_user_settings(self) -> UserSettings:
        """Get user settings"""
        settings = (
            self.db.query(UserSettings)
            .filter(UserSettings.user_id == self.user.id)
            .first()
        )
        if not settings:
            raise ValueError("User settings not found")
        return settings

    def _get_or_create_stock(self, symbol: str) -> Stock:
        """Get or create stock record"""
        stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            stock = Stock(symbol=symbol, name=symbol, exchange="TSX")
            self.db.add(stock)
            self.db.flush()
        return stock

    def _get_or_create_position(self, stock: Stock) -> Position:
        """Get or create position for stock"""
        position = (
            self.db.query(Position)
            .filter(
                Position.user_id == self.user.id,
                Position.stock_id == stock.id,
                Position.is_open == True,
            )
            .first()
        )

        if not position:
            position = Position(
                user_id=self.user.id,
                stock_id=stock.id,
                quantity=0,
                average_cost=0.0,
                is_open=False,
            )
            self.db.add(position)
            self.db.flush()

        return position

    def _update_position_on_buy(
        self, position: Position, quantity: int, price: float
    ) -> None:
        """Update position after buy execution"""
        if position.quantity == 0:
            # New position
            position.quantity = quantity
            position.average_cost = price
            position.is_open = True
            position.opened_at = datetime.utcnow()
        else:
            # Add to existing position (average up/down)
            total_cost = (position.quantity * position.average_cost) + (quantity * price)
            position.quantity += quantity
            position.average_cost = total_cost / position.quantity

        # Update market value
        position.current_price = price
        position.market_value = position.quantity * price
        position.unrealized_pnl = (price - position.average_cost) * position.quantity
        position.unrealized_pnl_pct = (
            ((price - position.average_cost) / position.average_cost) * 100
            if position.average_cost > 0
            else 0
        )

    def _update_position_on_sell(
        self, position: Position, quantity: int, price: float
    ) -> None:
        """Update position after sell execution"""
        # Calculate realized P&L
        realized_pnl = (price - position.average_cost) * quantity
        position.realized_pnl += realized_pnl

        # Update quantity
        position.quantity -= quantity

        if position.quantity == 0:
            # Position closed
            position.is_open = False
            position.closed_at = datetime.utcnow()
            position.market_value = 0.0
            position.unrealized_pnl = 0.0
            position.unrealized_pnl_pct = 0.0
        else:
            # Partial sell
            position.current_price = price
            position.market_value = position.quantity * price
            position.unrealized_pnl = (
                price - position.average_cost
            ) * position.quantity
            position.unrealized_pnl_pct = (
                ((price - position.average_cost) / position.average_cost) * 100
                if position.average_cost > 0
                else 0
            )

    def execute_paper_trade(self, order: TradeOrder, price: float) -> TradeExecution:
        """Execute a paper trade (simulated)

        Args:
            order: TradeOrder to execute
            price: Execution price

        Returns:
            TradeExecution record
        """
        # Create execution record
        execution = TradeExecution(
            order_id=order.id,
            quantity=order.quantity,
            price=price,
            commission=0.0,  # No commission for paper trading
            executed_at=datetime.utcnow(),
        )
        self.db.add(execution)

        # Update order
        order.filled_quantity = order.quantity
        order.average_fill_price = price
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()

        # Update position
        stock = self.db.query(Stock).filter(Stock.id == order.stock_id).first()
        position = self._get_or_create_position(stock)

        if order.side == OrderSide.BUY:
            self._update_position_on_buy(position, order.quantity, price)
            # Set stop loss and take profit
            if order.stop_loss_price:
                position.stop_loss_price = order.stop_loss_price
            if order.take_profit_price:
                position.take_profit_price = order.take_profit_price
        else:
            self._update_position_on_sell(position, order.quantity, price)

        self.db.commit()
        return execution

    def execute_live_trade(
        self, order: TradeOrder, account_id: str
    ) -> Optional[TradeExecution]:
        """Execute a live trade through Questrade

        Args:
            order: TradeOrder to execute
            account_id: Questrade account ID

        Returns:
            TradeExecution record if successful, None otherwise
        """
        if not self.user.questrade_access_token:
            raise ValueError("Questrade not connected")

        client = QuestradeClient(self.user)
        stock = self.db.query(Stock).filter(Stock.id == order.stock_id).first()

        # Get symbol ID
        symbol_id = client.get_symbol_id(stock.symbol)
        if not symbol_id:
            raise ValueError(f"Symbol {stock.symbol} not found")

        # Map order types
        order_type_map = {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit",
            OrderType.STOP: "Stop",
            OrderType.STOP_LIMIT: "StopLimit",
        }

        action = "Buy" if order.side == OrderSide.BUY else "Sell"

        # Place order
        try:
            response = client.place_order(
                account_id=account_id,
                symbol_id=symbol_id,
                quantity=order.quantity,
                order_type=order_type_map[order.order_type],
                action=action,
                price=order.limit_price,
                stop_price=order.stop_price,
            )

            # Update order with broker ID
            order.broker_order_id = str(response.get("orderId"))
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.utcnow()
            self.db.commit()

            # Check execution (for market orders, might be immediate)
            # In production, you'd poll this or use webhooks
            return None  # Return None for now, will be filled by monitoring task

        except Exception as e:
            order.status = OrderStatus.REJECTED
            self.db.commit()
            raise

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        reasoning: Optional[str] = None,
        conversation_id: Optional[int] = None,
    ) -> TradeOrder:
        """Place a trade order with validation

        Args:
            symbol: Stock symbol
            side: Buy or Sell
            quantity: Number of shares
            order_type: Market, Limit, Stop, or StopLimit
            limit_price: Limit price (for Limit orders)
            stop_price: Stop price (for Stop orders)
            stop_loss_price: Stop loss price for position
            take_profit_price: Take profit price for position
            reasoning: Trading reasoning/rationale
            conversation_id: Associated conversation ID

        Returns:
            TradeOrder record
        """
        # Get or create stock
        stock = self._get_or_create_stock(symbol)

        # Determine execution price for validation
        price = limit_price if limit_price else stop_price
        if not price:
            # For market orders, get current price
            from app.services.market_data import AlphaVantageService

            av = AlphaVantageService()
            price = av.get_latest_price(symbol)
            if not price:
                raise ValueError(f"Could not get price for {symbol}")

        # Validate trade
        validation_result = self.risk_manager.validate_trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
        )

        # Create order
        order = TradeOrder(
            user_id=self.user.id,
            stock_id=stock.id,
            order_type=order_type,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            position_size_pct=validation_result["position_size_pct"],
            risk_amount=validation_result["risk_amount"],
            reasoning=reasoning,
            conversation_id=conversation_id,
            is_paper_trade=self.settings.paper_trading_enabled,
        )
        self.db.add(order)
        self.db.flush()

        # Execute based on mode
        if self.settings.paper_trading_enabled:
            self.execute_paper_trade(order, price)
        else:
            # For live trading, would need account_id
            # This would be called by a background task
            pass

        self.db.commit()
        return order
