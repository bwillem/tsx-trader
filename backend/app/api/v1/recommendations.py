from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import Optional
import json
from app.database import get_db
from app.models.user import User
from app.models.decision import TradingDecision
from app.models.stock import Stock
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/latest")
async def get_latest_recommendations(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get latest trading recommendations from Claude"""
    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock, TradingDecision.stock_id == Stock.id)
        .filter(TradingDecision.user_id == current_user.id)
        .order_by(desc(TradingDecision.created_at))
        .limit(limit)
        .all()
    )

    results = []
    for decision, stock in decisions:
        # Parse suggested action JSON
        suggested_action = None
        if decision.suggested_action:
            try:
                suggested_action = json.loads(decision.suggested_action)
            except:
                pass

        results.append({
            "id": decision.id,
            "symbol": stock.symbol,
            "stock_name": stock.name,
            "decision": decision.decision,
            "confidence": decision.confidence,
            "technical_signal": decision.technical_signal,
            "sentiment_score": decision.sentiment_score,
            "reasoning": decision.reasoning,
            "suggested_action": suggested_action,
            "action_taken": decision.action_taken,
            "action_reason": decision.action_reason,
            "created_at": decision.created_at,
        })

    return results


@router.get("/actionable")
async def get_actionable_recommendations(
    min_confidence: float = 0.7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get high-confidence buy/sell recommendations awaiting action"""
    # Get recommendations from last 24 hours
    since = datetime.utcnow() - timedelta(days=1)

    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock, TradingDecision.stock_id == Stock.id)
        .filter(
            TradingDecision.user_id == current_user.id,
            TradingDecision.action_taken == False,
            TradingDecision.confidence >= min_confidence,
            TradingDecision.decision.in_(["buy", "sell"]),
            TradingDecision.created_at >= since,
        )
        .order_by(desc(TradingDecision.confidence))
        .all()
    )

    results = []
    for decision, stock in decisions:
        suggested_action = None
        if decision.suggested_action:
            try:
                suggested_action = json.loads(decision.suggested_action)
            except:
                pass

        results.append({
            "id": decision.id,
            "symbol": stock.symbol,
            "stock_name": stock.name,
            "decision": decision.decision,
            "confidence": decision.confidence,
            "technical_signal": decision.technical_signal,
            "sentiment_score": decision.sentiment_score,
            "reasoning": decision.reasoning,
            "suggested_action": suggested_action,
            "created_at": decision.created_at,
        })

    return results


@router.get("/{decision_id}")
async def get_recommendation_detail(
    decision_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific recommendation"""
    result = (
        db.query(TradingDecision, Stock)
        .join(Stock, TradingDecision.stock_id == Stock.id)
        .filter(
            TradingDecision.id == decision_id,
            TradingDecision.user_id == current_user.id,
        )
        .first()
    )

    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    decision, stock = result

    # Parse suggested action and market conditions
    suggested_action = None
    if decision.suggested_action:
        try:
            suggested_action = json.loads(decision.suggested_action)
        except:
            pass

    return {
        "id": decision.id,
        "symbol": stock.symbol,
        "stock_name": stock.name,
        "decision": decision.decision,
        "confidence": decision.confidence,
        "technical_signal": decision.technical_signal,
        "sentiment_score": decision.sentiment_score,
        "reasoning": decision.reasoning,
        "suggested_action": suggested_action,
        "market_conditions": decision.market_conditions,
        "action_taken": decision.action_taken,
        "action_reason": decision.action_reason,
        "order_id": decision.order_id,
        "created_at": decision.created_at,
    }


@router.post("/{decision_id}/dismiss")
async def dismiss_recommendation(
    decision_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a recommendation as reviewed/dismissed"""
    decision = (
        db.query(TradingDecision)
        .filter(
            TradingDecision.id == decision_id,
            TradingDecision.user_id == current_user.id,
        )
        .first()
    )

    if not decision:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    decision.action_taken = True
    decision.action_reason = "Manually dismissed"
    db.commit()

    return {"message": "Recommendation dismissed"}
