from typing import Dict, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User, UserSettings
from app.models.trade import TradeOrder, Position, OrderSide
from app.models.portfolio import PortfolioSnapshot


class RiskValidationError(Exception):
    """Raised when a trade fails risk validation"""

    pass


class RiskManager:
    """Validates trades against risk parameters and circuit breakers"""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.settings = self._get_user_settings()

    def _get_user_settings(self) -> UserSettings:
        """Get user trading settings"""
        settings = (
            self.db.query(UserSettings)
            .filter(UserSettings.user_id == self.user.id)
            .first()
        )
        if not settings:
            raise ValueError("User settings not found")
        return settings

    def _get_portfolio_value(self) -> float:
        """Get total portfolio value (cash + positions)"""
        snapshot = (
            self.db.query(PortfolioSnapshot)
            .filter(PortfolioSnapshot.user_id == self.user.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .first()
        )
        return snapshot.total_value if snapshot else 0.0

    def _get_cash_balance(self) -> float:
        """Get available cash balance"""
        snapshot = (
            self.db.query(PortfolioSnapshot)
            .filter(PortfolioSnapshot.user_id == self.user.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .first()
        )
        return snapshot.cash_balance if snapshot else 0.0

    def _get_open_positions_count(self) -> int:
        """Get number of open positions"""
        return (
            self.db.query(Position)
            .filter(Position.user_id == self.user.id, Position.is_open == True)
            .count()
        )

    def _get_daily_pnl(self) -> Tuple[float, float]:
        """Get today's P&L (amount and percentage)"""
        today_snapshot = (
            self.db.query(PortfolioSnapshot)
            .filter(
                PortfolioSnapshot.user_id == self.user.id,
                PortfolioSnapshot.snapshot_date == date.today(),
            )
            .first()
        )

        if today_snapshot:
            return today_snapshot.daily_pnl, today_snapshot.daily_pnl_pct
        return 0.0, 0.0

    def validate_position_size(
        self, symbol: str, quantity: int, price: float, side: OrderSide
    ) -> None:
        """Validate position size against limits

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share
            side: Buy or Sell

        Raises:
            RiskValidationError: If validation fails
        """
        if side == OrderSide.SELL:
            # For sells, just verify we have the position
            position = (
                self.db.query(Position)
                .join(Position.stock)
                .filter(
                    Position.user_id == self.user.id,
                    Position.is_open == True,
                    Position.stock.has(symbol=symbol),
                )
                .first()
            )

            if not position:
                raise RiskValidationError(f"No open position for {symbol}")

            if position.quantity < quantity:
                raise RiskValidationError(
                    f"Insufficient shares: have {position.quantity}, trying to sell {quantity}"
                )
            return

        # For buys, validate position size
        portfolio_value = self._get_portfolio_value()
        if portfolio_value == 0:
            raise RiskValidationError("Portfolio value is zero")

        trade_value = quantity * price
        position_size_pct = (trade_value / portfolio_value) * 100

        max_position_size = self.settings.position_size_pct

        if position_size_pct > max_position_size:
            raise RiskValidationError(
                f"Position size {position_size_pct:.1f}% exceeds limit of {max_position_size}%"
            )

    def validate_cash_available(self, quantity: int, price: float, side: OrderSide) -> None:
        """Validate sufficient cash for purchase

        Raises:
            RiskValidationError: If insufficient cash
        """
        if side == OrderSide.SELL:
            return  # Selling doesn't require cash

        trade_value = quantity * price
        cash_balance = self._get_cash_balance()

        # Check minimum cash reserve
        portfolio_value = self._get_portfolio_value()
        min_cash_reserve = portfolio_value * (self.settings.min_cash_reserve_pct / 100)

        available_cash = cash_balance - min_cash_reserve

        if trade_value > available_cash:
            raise RiskValidationError(
                f"Insufficient cash: need ${trade_value:,.2f}, have ${available_cash:,.2f} available "
                f"(after ${min_cash_reserve:,.2f} reserve)"
            )

    def validate_stop_loss(self, stop_loss_price: Optional[float], price: float) -> None:
        """Validate stop loss is required and set correctly

        Raises:
            RiskValidationError: If stop loss validation fails
        """
        if not self.settings.require_stop_loss:
            return

        if stop_loss_price is None:
            raise RiskValidationError("Stop loss is required but not provided")

        # Validate stop loss is reasonable (within 10% of entry)
        stop_loss_pct = abs((stop_loss_price - price) / price) * 100

        if stop_loss_pct < 1:
            raise RiskValidationError("Stop loss too tight (< 1%)")

        if stop_loss_pct > 20:
            raise RiskValidationError("Stop loss too wide (> 20%)")

    def validate_risk_reward(
        self,
        entry_price: float,
        stop_loss_price: Optional[float],
        take_profit_price: Optional[float],
    ) -> None:
        """Validate risk/reward ratio

        Raises:
            RiskValidationError: If risk/reward ratio is too low
        """
        if stop_loss_price is None or take_profit_price is None:
            return  # Can't calculate without both

        risk = abs(entry_price - stop_loss_price)
        reward = abs(take_profit_price - entry_price)

        if risk == 0:
            raise RiskValidationError("Risk cannot be zero")

        risk_reward_ratio = reward / risk

        if risk_reward_ratio < self.settings.min_risk_reward_ratio:
            raise RiskValidationError(
                f"Risk/reward ratio {risk_reward_ratio:.2f} is below minimum "
                f"{self.settings.min_risk_reward_ratio}"
            )

    def check_circuit_breaker(self) -> None:
        """Check if circuit breaker should halt trading

        Raises:
            RiskValidationError: If circuit breaker is triggered
        """
        if not self.settings.circuit_breaker_enabled:
            return

        daily_pnl, daily_pnl_pct = self._get_daily_pnl()

        # Check daily loss limit
        if daily_pnl_pct < -self.settings.daily_loss_limit_pct:
            raise RiskValidationError(
                f"Circuit breaker triggered: daily loss {daily_pnl_pct:.1f}% exceeds limit "
                f"of {self.settings.daily_loss_limit_pct}%"
            )

    def check_max_positions(self, side: OrderSide) -> None:
        """Check if maximum positions limit is reached

        Raises:
            RiskValidationError: If max positions exceeded
        """
        if side == OrderSide.SELL:
            return  # Selling reduces positions

        open_positions = self._get_open_positions_count()

        if open_positions >= self.settings.max_open_positions:
            raise RiskValidationError(
                f"Maximum positions ({self.settings.max_open_positions}) reached"
            )

    def validate_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> Dict[str, any]:
        """Comprehensive trade validation

        Args:
            symbol: Stock symbol
            side: Buy or Sell
            quantity: Number of shares
            price: Entry price
            stop_loss_price: Stop loss price (optional)
            take_profit_price: Take profit price (optional)

        Returns:
            Dictionary with validation results and trade metrics

        Raises:
            RiskValidationError: If any validation fails
        """
        # Run all validations
        self.check_circuit_breaker()
        self.check_max_positions(side)
        self.validate_position_size(symbol, quantity, price, side)
        self.validate_cash_available(quantity, price, side)
        self.validate_stop_loss(stop_loss_price, price)
        self.validate_risk_reward(price, stop_loss_price, take_profit_price)

        # Calculate trade metrics
        portfolio_value = self._get_portfolio_value()
        trade_value = quantity * price
        position_size_pct = (trade_value / portfolio_value) * 100 if portfolio_value > 0 else 0

        risk_amount = 0.0
        if stop_loss_price:
            risk_amount = abs(price - stop_loss_price) * quantity

        return {
            "validated": True,
            "trade_value": trade_value,
            "position_size_pct": position_size_pct,
            "risk_amount": risk_amount,
            "portfolio_value": portfolio_value,
        }
