from celery import shared_task
from datetime import datetime
from app.database import get_db_context
from app.models.user import User, UserSettings
from app.models.trade import Position, OrderSide, OrderType
from app.models.stock import Stock
from app.services.chat import ClaudeTrader
from app.services.market_data import AlphaVantageService
from app.services.trading import TradeExecutor


@shared_task(name="app.tasks.trading_tasks.run_trading_analysis")
def run_trading_analysis():
    """Run automated trading analysis for all users with auto-trading enabled"""
    print(f"Starting trading analysis at {datetime.utcnow()}")

    with get_db_context() as db:
        # Get users with auto-trading enabled
        users = (
            db.query(User)
            .join(UserSettings)
            .filter(
                User.is_active == True,
                UserSettings.auto_trading_enabled == True,
            )
            .all()
        )

        if not users:
            print("No users with auto-trading enabled")
            return {"status": "no_users"}

        results = {}

        for user in users:
            try:
                trader = ClaudeTrader(db, user)

                # Analyze existing portfolio
                decisions = trader.analyze_portfolio()

                # If no positions, analyze all active stocks for opportunities
                if not decisions:
                    print(f"User {user.email}: No positions, analyzing all stocks...")
                    stocks = db.query(Stock).filter(Stock.is_active == True).all()

                    for stock in stocks:
                        try:
                            decision = trader.analyze_symbol(stock.symbol)
                            if decision:
                                decisions.append(decision)
                        except Exception as e:
                            print(f"  Error analyzing {stock.symbol}: {e}")

                results[user.email] = {
                    "status": "success",
                    "decisions": len(decisions),
                    "actions": sum(1 for d in decisions if d.action_taken),
                }

                print(f"User {user.email}: {len(decisions)} decisions, "
                      f"{results[user.email]['actions']} actions taken")

            except Exception as e:
                print(f"Error analyzing for user {user.email}: {e}")
                results[user.email] = {"status": "error", "error": str(e)}

        return results


@shared_task(name="app.tasks.trading_tasks.analyze_symbol_for_user")
def analyze_symbol_for_user(user_id: int, symbol: str):
    """Analyze a specific symbol for a user

    Args:
        user_id: User ID
        symbol: Stock symbol to analyze
    """
    print(f"Analyzing {symbol} for user {user_id}")

    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return {"status": "error", "error": "User not found"}

        try:
            trader = ClaudeTrader(db, user)
            decision = trader.analyze_symbol(symbol)

            return {
                "status": "success",
                "decision": decision.decision,
                "confidence": decision.confidence,
                "action_taken": decision.action_taken,
                "reasoning": decision.reasoning,
            }
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return {"status": "error", "error": str(e)}


@shared_task(name="app.tasks.trading_tasks.monitor_stop_losses")
def monitor_stop_losses():
    """Monitor open positions and execute stop losses if triggered"""
    print("Monitoring stop losses...")

    with get_db_context() as db:
        # Get all open positions with stop losses
        positions = (
            db.query(Position, Stock, User)
            .join(Stock)
            .join(User)
            .filter(
                Position.is_open == True,
                Position.stop_loss_price.isnot(None),
                User.is_active == True,
            )
            .all()
        )

        if not positions:
            return {"status": "no_positions"}

        av_service = AlphaVantageService()
        triggered = []

        for position, stock, user in positions:
            try:
                # Get current price
                current_price = av_service.get_latest_price(stock.symbol)

                if not current_price:
                    continue

                # Update position price
                position.current_price = current_price
                position.market_value = position.quantity * current_price
                position.unrealized_pnl = (
                    current_price - position.average_cost
                ) * position.quantity
                position.unrealized_pnl_pct = (
                    ((current_price - position.average_cost) / position.average_cost) * 100
                    if position.average_cost > 0
                    else 0
                )

                # Check stop loss
                if current_price <= position.stop_loss_price:
                    print(f"Stop loss triggered for {stock.symbol}: "
                          f"${current_price} <= ${position.stop_loss_price}")

                    # Execute stop loss
                    executor = TradeExecutor(db, user)

                    order = executor.place_order(
                        symbol=stock.symbol,
                        side=OrderSide.SELL,
                        quantity=position.quantity,
                        order_type=OrderType.MARKET,
                        reasoning=f"Stop loss triggered at ${current_price}",
                    )

                    triggered.append({
                        "symbol": stock.symbol,
                        "user": user.email,
                        "quantity": position.quantity,
                        "price": current_price,
                        "stop_loss": position.stop_loss_price,
                        "order_id": order.id,
                    })

                # Check take profit
                elif (
                    position.take_profit_price
                    and current_price >= position.take_profit_price
                ):
                    print(f"Take profit triggered for {stock.symbol}: "
                          f"${current_price} >= ${position.take_profit_price}")

                    executor = TradeExecutor(db, user)

                    order = executor.place_order(
                        symbol=stock.symbol,
                        side=OrderSide.SELL,
                        quantity=position.quantity,
                        order_type=OrderType.MARKET,
                        reasoning=f"Take profit triggered at ${current_price}",
                    )

                    triggered.append({
                        "symbol": stock.symbol,
                        "user": user.email,
                        "quantity": position.quantity,
                        "price": current_price,
                        "take_profit": position.take_profit_price,
                        "order_id": order.id,
                    })

            except Exception as e:
                print(f"Error monitoring {stock.symbol}: {e}")

        db.commit()

        return {
            "status": "success",
            "positions_monitored": len(positions),
            "stop_losses_triggered": len(triggered),
            "triggered": triggered,
        }
