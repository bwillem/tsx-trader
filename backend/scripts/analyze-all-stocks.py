#!/usr/bin/env python3
"""
Analyze all stocks in the database for trading opportunities.
This is useful for initial setup when there are no existing positions.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.models.user import User, UserSettings
from app.models.stock import Stock
from app.services.chat import ClaudeTrader


def analyze_all_stocks():
    """Analyze all stocks for all users with auto-trading enabled"""
    db = SessionLocal()

    try:
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
            print("❌ No users with auto-trading enabled found")
            print("\nMake sure you have:")
            print("  1. Created a user account")
            print("  2. Set auto_trading_enabled = true in user_settings")
            return

        print(f"✓ Found {len(users)} user(s) with auto-trading enabled\n")

        # Get all active stocks
        stocks = db.query(Stock).filter(Stock.is_active == True).all()

        if not stocks:
            print("❌ No stocks found in database")
            return

        print(f"✓ Analyzing {len(stocks)} stocks...\n")

        total_decisions = 0

        for user in users:
            print(f"Analyzing for user: {user.email}")
            trader = ClaudeTrader(db, user)

            for stock in stocks:
                try:
                    print(f"  Analyzing {stock.symbol}...", end=" ")
                    decision = trader.analyze_symbol(stock.symbol)

                    if decision:
                        print(f"✓ {decision.decision.upper()} (confidence: {decision.confidence:.1%})")
                        total_decisions += 1
                    else:
                        print("⚠ No decision")

                except Exception as e:
                    print(f"✗ Error: {e}")

            print()

        print(f"\n✅ Complete! Created {total_decisions} trading decisions")
        print(f"\nView recommendations:")
        print(f"  python scripts/check_recommendations.py")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    analyze_all_stocks()
