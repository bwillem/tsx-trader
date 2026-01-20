#!/usr/bin/env python3
"""
Initialize database with sample data
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.models import Stock

# TSX stocks to track
# Mix of large caps (for diversification) and small caps ($300M-$2B for multibagger potential)
SAMPLE_STOCKS = [
    # Large cap blue chips (reference/diversification)
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

    # Small & Mid Caps ($300M-$2B) - Multibagger potential per Yartseva (2025)
    # Technology
    {"symbol": "WELL.TO", "name": "WELL Health Technologies", "sector": "Technology"},
    {"symbol": "DCBO.TO", "name": "Docebo Inc", "sector": "Technology"},
    {"symbol": "TOI.TO", "name": "Topicus.com Inc", "sector": "Technology"},
    {"symbol": "GDNP.TO", "name": "Goodfood Market", "sector": "Technology"},

    # Energy & Resources
    {"symbol": "PXT.TO", "name": "Parex Resources", "sector": "Energy"},
    {"symbol": "TVE.TO", "name": "Tamarack Valley Energy", "sector": "Energy"},
    {"symbol": "BTE.TO", "name": "Baytex Energy", "sector": "Energy"},
    {"symbol": "VII.TO", "name": "Seven Generations Energy", "sector": "Energy"},
    {"symbol": "TECK-B.TO", "name": "Teck Resources Limited", "sector": "Materials"},
    {"symbol": "HBM.TO", "name": "Hudbay Minerals", "sector": "Materials"},
    {"symbol": "TKO.TO", "name": "Taseko Mines", "sector": "Materials"},

    # Industrials
    {"symbol": "NFI.TO", "name": "NFI Group Inc", "sector": "Industrials"},
    {"symbol": "BYD.TO", "name": "Boyd Group Services", "sector": "Industrials"},
    {"symbol": "GFL.TO", "name": "GFL Environmental", "sector": "Industrials"},
    {"symbol": "TOY.TO", "name": "Spin Master Corp", "sector": "Consumer Discretionary"},

    # Healthcare & Life Sciences
    {"symbol": "MT.TO", "name": "Medicure Inc", "sector": "Healthcare"},
    {"symbol": "QIPT.TO", "name": "Quipt Home Medical", "sector": "Healthcare"},
    {"symbol": "PHM.TO", "name": "Partners Value", "sector": "Healthcare"},

    # Financials (smaller players)
    {"symbol": "EQB.TO", "name": "Equitable Group", "sector": "Financials"},
    {"symbol": "GSY.TO", "name": "goeasy Ltd", "sector": "Financials"},
    {"symbol": "HCG.TO", "name": "Home Capital Group", "sector": "Financials"},

    # Real Estate & REITs
    {"symbol": "CAR-UN.TO", "name": "Canadian Apartment Properties REIT", "sector": "Real Estate"},
    {"symbol": "HR-UN.TO", "name": "H&R REIT", "sector": "Real Estate"},
    {"symbol": "DIR-UN.TO", "name": "Dream Industrial REIT", "sector": "Real Estate"},

    # Consumer
    {"symbol": "ATD.TO", "name": "Alimentation Couche-Tard", "sector": "Consumer Staples"},
    {"symbol": "TFII.TO", "name": "TFI International", "sector": "Industrials"},
    {"symbol": "DOL.TO", "name": "Dollarama Inc", "sector": "Consumer Discretionary"},
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
