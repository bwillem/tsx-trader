#!/usr/bin/env python3
"""
Quick script to check trading recommendations from the cloud database.

Usage:
    python check_recommendations.py

Set your DATABASE_URL environment variable or update the script.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime, timedelta

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    print("\nSet it with:")
    print("  export DATABASE_URL='your-neon-connection-string'")
    print("\nOr on Windows:")
    print("  set DATABASE_URL=your-neon-connection-string")
    sys.exit(1)

# Create database connection
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


def get_recommendations(hours=24, min_confidence=0.0):
    """Get recent trading recommendations"""

    since = datetime.utcnow() - timedelta(hours=hours)

    query = """
        SELECT
            s.symbol,
            s.name as stock_name,
            td.decision,
            td.confidence,
            td.technical_signal,
            td.sentiment_score,
            td.reasoning,
            td.suggested_action,
            td.action_taken,
            td.created_at
        FROM trading_decisions td
        JOIN stocks s ON td.stock_id = s.id
        WHERE td.created_at >= :since
          AND td.confidence >= :min_confidence
        ORDER BY td.confidence DESC, td.created_at DESC
    """

    result = session.execute(query, {'since': since, 'min_confidence': min_confidence})
    return result.fetchall()


def get_actionable():
    """Get high-confidence buy/sell recommendations"""

    since = datetime.utcnow() - timedelta(hours=24)

    query = """
        SELECT
            s.symbol,
            s.name as stock_name,
            td.decision,
            td.confidence,
            td.technical_signal,
            td.sentiment_score,
            td.reasoning,
            td.suggested_action,
            td.created_at
        FROM trading_decisions td
        JOIN stocks s ON td.stock_id = s.id
        WHERE td.created_at >= :since
          AND td.decision IN ('buy', 'sell')
          AND td.confidence >= 0.7
          AND td.action_taken = false
        ORDER BY td.confidence DESC
    """

    result = session.execute(query, {'since': since})
    return result.fetchall()


def print_recommendation(rec):
    """Pretty print a recommendation"""

    print(f"\n{'='*70}")
    print(f"Symbol: {rec.symbol} - {rec.stock_name}")
    print(f"Decision: {rec.decision.upper()}")
    print(f"Confidence: {rec.confidence:.1%}")
    print(f"Technical: {rec.technical_signal}")
    print(f"Sentiment: {rec.sentiment_score:.2f}" if rec.sentiment_score else "Sentiment: N/A")
    print(f"Created: {rec.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\nReasoning:")
    print(f"  {rec.reasoning[:300]}...")

    if rec.suggested_action:
        try:
            action = json.loads(rec.suggested_action)
            print(f"\nSuggested Action:")
            print(f"  Quantity: {action.get('quantity')} shares")
            print(f"  Entry Price: ${action.get('entry_price', 0):.2f}")
            print(f"  Stop Loss: ${action.get('stop_loss_price', 0):.2f}")
            print(f"  Take Profit: ${action.get('take_profit_price', 0):.2f}")
            print(f"  Order Type: {action.get('order_type', 'N/A')}")
        except:
            pass


def main():
    print("="*70)
    print("TSX Trading Recommendations".center(70))
    print("="*70)

    # Get actionable recommendations
    actionable = get_actionable()

    if actionable:
        print(f"\n🔥 ACTIONABLE RECOMMENDATIONS (High Confidence Buy/Sell):")
        print(f"   Found {len(actionable)} recommendation(s)\n")

        for rec in actionable:
            print_recommendation(rec)
    else:
        print(f"\n📊 No high-confidence buy/sell recommendations in the last 24 hours")

    # Get all recent recommendations
    all_recs = get_recommendations(hours=24, min_confidence=0.5)

    if all_recs:
        print(f"\n\n📈 ALL RECENT RECOMMENDATIONS (Last 24 hours, confidence ≥ 50%):")
        print(f"   Found {len(all_recs)} recommendation(s)\n")

        for rec in all_recs:
            if rec not in actionable:  # Don't duplicate
                print_recommendation(rec)

    # Summary stats
    print(f"\n\n{'='*70}")
    print("SUMMARY".center(70))
    print(f"{'='*70}")

    stats_query = """
        SELECT
            decision,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence
        FROM trading_decisions
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY decision
        ORDER BY count DESC
    """

    stats = session.execute(stats_query).fetchall()

    for stat in stats:
        print(f"{stat.decision.upper():15} {stat.count:3} decisions (avg confidence: {stat.avg_confidence:.1%})")

    session.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nMake sure:")
        print("  1. DATABASE_URL is set correctly")
        print("  2. Database has been migrated (tables exist)")
        print("  3. You can connect to the database")
        sys.exit(1)
