from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, date
from app.database import get_db
from app.models.user import User
from app.models.trade import Position
from app.models.stock import Stock
from app.models.portfolio import PortfolioSnapshot
from app.schemas.portfolio import PortfolioSummary, PortfolioSnapshotResponse
from app.schemas.trade import PositionResponse
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get portfolio summary with current positions"""
    # Get open positions
    positions = (
        db.query(Position, Stock)
        .join(Stock, Position.stock_id == Stock.id)
        .filter(Position.user_id == current_user.id, Position.is_open == True)
        .all()
    )

    position_responses = []
    positions_value = 0.0

    for position, stock in positions:
        position_responses.append(
            PositionResponse(
                id=position.id,
                stock_id=position.stock_id,
                symbol=stock.symbol,
                quantity=position.quantity,
                average_cost=position.average_cost,
                current_price=position.current_price,
                market_value=position.market_value,
                unrealized_pnl=position.unrealized_pnl,
                unrealized_pnl_pct=position.unrealized_pnl_pct,
                realized_pnl=position.realized_pnl,
                stop_loss_price=position.stop_loss_price,
                take_profit_price=position.take_profit_price,
                is_open=position.is_open,
                opened_at=position.opened_at,
                closed_at=position.closed_at,
            )
        )
        positions_value += position.market_value or 0.0

    # Get latest snapshot for cash balance and P&L
    latest_snapshot = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.user_id == current_user.id)
        .order_by(desc(PortfolioSnapshot.snapshot_date))
        .first()
    )

    if latest_snapshot:
        cash_balance = latest_snapshot.cash_balance
        daily_pnl = latest_snapshot.daily_pnl
        daily_pnl_pct = latest_snapshot.daily_pnl_pct
        total_pnl = latest_snapshot.total_pnl
        total_pnl_pct = latest_snapshot.total_pnl_pct
    else:
        # Default values if no snapshot
        cash_balance = 0.0
        daily_pnl = 0.0
        daily_pnl_pct = 0.0
        total_pnl = 0.0
        total_pnl_pct = 0.0

    total_value = cash_balance + positions_value

    return PortfolioSummary(
        total_value=total_value,
        cash_balance=cash_balance,
        positions_value=positions_value,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        num_positions=len(position_responses),
        positions=position_responses,
    )


@router.get("/history", response_model=list[PortfolioSnapshotResponse])
async def get_portfolio_history(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get portfolio history snapshots"""
    snapshots = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.user_id == current_user.id)
        .order_by(desc(PortfolioSnapshot.snapshot_date))
        .limit(days)
        .all()
    )

    return [PortfolioSnapshotResponse.model_validate(s) for s in snapshots]
