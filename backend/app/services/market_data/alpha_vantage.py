import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.stock import Stock, MarketDataDaily
from .indicators import TechnicalIndicators

settings = get_settings()


class AlphaVantageService:
    """Service for fetching and storing market data from Alpha Vantage"""

    def __init__(self):
        self.api_key = settings.ALPHA_VANTAGE_API_KEY
        self.base_url = "https://www.alphavantage.co/query"

    def fetch_daily_data(
        self, symbol: str, outputsize: str = "compact"
    ) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data for a symbol

        Args:
            symbol: Stock symbol (e.g., 'TD.TO')
            outputsize: 'compact' (100 days) or 'full' (20+ years)
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "Time Series (Daily)" not in data:
                print(f"No data found for {symbol}: {data}")
                return None

            # Convert to DataFrame
            ts_data = data["Time Series (Daily)"]
            df = pd.DataFrame.from_dict(ts_data, orient="index")
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)

            # Rename columns
            df.columns = ["open", "high", "low", "close", "volume"]

            # Convert to numeric
            for col in df.columns:
                df[col] = pd.to_numeric(df[col])

            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None

    def update_stock_data(self, db: Session, stock: Stock) -> bool:
        """Update market data for a stock

        Args:
            db: Database session
            stock: Stock model instance

        Returns:
            True if successful, False otherwise
        """
        # Fetch data
        df = self.fetch_daily_data(stock.symbol)
        if df is None or df.empty:
            return False

        # Calculate technical indicators
        df = TechnicalIndicators.calculate_all(df)

        # Get existing dates
        existing_dates = set(
            record[0]
            for record in db.query(MarketDataDaily.date)
            .filter(MarketDataDaily.stock_id == stock.id)
            .all()
        )

        # Insert new records
        new_records = 0
        for date, row in df.iterrows():
            if date.date() not in existing_dates:
                market_data = MarketDataDaily(
                    stock_id=stock.id,
                    date=date.date(),
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=int(row["volume"]),
                    sma_20=row.get("sma_20"),
                    sma_50=row.get("sma_50"),
                    sma_200=row.get("sma_200"),
                    ema_12=row.get("ema_12"),
                    ema_26=row.get("ema_26"),
                    rsi_14=row.get("rsi_14"),
                    macd=row.get("macd"),
                    macd_signal=row.get("macd_signal"),
                    macd_histogram=row.get("macd_histogram"),
                    bollinger_upper=row.get("bollinger_upper"),
                    bollinger_middle=row.get("bollinger_middle"),
                    bollinger_lower=row.get("bollinger_lower"),
                    atr_14=row.get("atr_14"),
                )
                db.add(market_data)
                new_records += 1

        db.commit()
        print(f"Updated {stock.symbol}: {new_records} new records")
        return True

    def update_multiple_stocks(self, db: Session, symbols: List[str]) -> Dict[str, bool]:
        """Update market data for multiple stocks

        Args:
            db: Database session
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbol to success status
        """
        results = {}

        for symbol in symbols:
            # Get or create stock
            stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                # Create stock if it doesn't exist
                stock = Stock(symbol=symbol, name=symbol, exchange="TSX")
                db.add(stock)
                db.flush()

            # Update data
            success = self.update_stock_data(db, stock)
            results[symbol] = success

            # Rate limiting (5 calls per minute for free tier)
            import time

            time.sleep(12)  # 12 seconds between calls

        return results

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol using GLOBAL_QUOTE"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                return float(data["Global Quote"]["05. price"])
            return None
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None
