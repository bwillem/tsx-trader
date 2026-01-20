#!/usr/bin/env python3
"""
Initialize database with sample data
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.models import Stock

# TSX stocks to track
SAMPLE_STOCKS = [
    {"symbol": "TD.TO", "name": "Toronto-Dominion Bank", "sector": "Financials"},
    {"symbol": "RY.TO", "name": "Royal Bank of Canada", "sector": "Financials"},
    {"symbol": "SHOP.TO", "name": "Shopify Inc", "sector": "Technology"},
    {"symbol": "ENB.TO", "name": "Enbridge Inc", "sector": "Energy"},
    {"symbol": "CNQ.TO", "name": "Canadian Natural Resources", "sector": "Energy"},
    {"symbol": "BMO.TO", "name": "Bank of Montreal", "sector": "Financials"},
    {"symbol": "BNS.TO", "name": "Bank of Nova Scotia", "sector": "Financials"},
    {"symbol": "CP.TO", "name": "Canadian Pacific Railway", "sector": "Industrials"},
    {"symbol": "CNR.TO", "name": "Canadian National Railway", "sector": "Industrials"},
    {"symbol": "SU.TO", "name": "Suncor Energy", "sector": "Energy"},
]


def init_stocks():
    """Initialize stock database with common TSX stocks"""
    db = SessionLocal()
    try:
        print("Initializing stocks...")
        added = 0

        for stock_data in SAMPLE_STOCKS:
            existing = db.query(Stock).filter(Stock.symbol == stock_data["symbol"]).first()

            if not existing:
                stock = Stock(**stock_data, exchange="TSX", is_active=True)
                db.add(stock)
                added += 1
                print(f"  Added {stock_data['symbol']} - {stock_data['name']}")

        db.commit()
        print(f"\n✓ Added {added} new stocks")
        print(f"✓ Total stocks in database: {db.query(Stock).count()}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_stocks()
