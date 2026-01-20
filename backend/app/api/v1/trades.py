from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.trade import TradeOrder, Position
from app.models.stock import Stock
from app.schemas.trade import TradeOrderCreate, TradeOrderResponse, PositionResponse
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/orders", response_model=list[TradeOrderResponse])
async def get_orders(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get trade orders"""
    orders = (
        db.query(TradeOrder, Stock)
        .join(Stock, TradeOrder.stock_id == Stock.id)
        .filter(TradeOrder.user_id == current_user.id)
        .order_by(desc(TradeOrder.created_at))
        .limit(limit)
        .all()
    )

    responses = []
    for order, stock in orders:
        responses.append(
            TradeOrderResponse(
                id=order.id,
                stock_id=order.stock_id,
                symbol=stock.symbol,
                order_type=order.order_type,
                side=order.side,
                quantity=order.quantity,
                limit_price=order.limit_price,
                stop_price=order.stop_price,
                status=order.status,
                broker_order_id=order.broker_order_id,
                stop_loss_price=order.stop_loss_price,
                take_profit_price=order.take_profit_price,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                created_at=order.created_at,
                submitted_at=order.submitted_at,
                filled_at=order.filled_at,
                is_paper_trade=order.is_paper_trade,
            )
        )

    return responses


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    include_closed: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get positions"""
    query = db.query(Position, Stock).join(Stock, Position.stock_id == Stock.id).filter(
        Position.user_id == current_user.id
    )

    if not include_closed:
        query = query.filter(Position.is_open == True)

    positions = query.order_by(desc(Position.created_at)).all()

    responses = []
    for position, stock in positions:
        responses.append(
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

    return responses


@router.get("/orders/{order_id}", response_model=TradeOrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get specific order details"""
    result = (
        db.query(TradeOrder, Stock)
        .join(Stock, TradeOrder.stock_id == Stock.id)
        .filter(TradeOrder.id == order_id, TradeOrder.user_id == current_user.id)
        .first()
    )

    if not result:
        raise HTTPException(status_code=404, detail="Order not found")

    order, stock = result
    return TradeOrderResponse(
        id=order.id,
        stock_id=order.stock_id,
        symbol=stock.symbol,
        order_type=order.order_type,
        side=order.side,
        quantity=order.quantity,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
        status=order.status,
        broker_order_id=order.broker_order_id,
        stop_loss_price=order.stop_loss_price,
        take_profit_price=order.take_profit_price,
        filled_quantity=order.filled_quantity,
        average_fill_price=order.average_fill_price,
        created_at=order.created_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        is_paper_trade=order.is_paper_trade,
    )
