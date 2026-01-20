import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.stock import Stock, MarketDataDaily
from app.models.fundamentals import FundamentalDataQuarterly, FundamentalDataAnnual
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

    def fetch_company_overview(self, symbol: str) -> Optional[Dict]:
        """Fetch company overview and key fundamental ratios

        This includes market cap, book value, P/E, P/B, and other overview metrics.
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Check if we got valid data (not rate limited or error)
            if not data or "Symbol" not in data:
                print(f"No overview data for {symbol}: {data}")
                return None

            return data
        except Exception as e:
            print(f"Error fetching overview for {symbol}: {e}")
            return None

    def fetch_income_statement(self, symbol: str) -> Optional[Dict]:
        """Fetch quarterly and annual income statement data"""
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "quarterlyReports" not in data and "annualReports" not in data:
                print(f"No income statement for {symbol}")
                return None

            return data
        except Exception as e:
            print(f"Error fetching income statement for {symbol}: {e}")
            return None

    def fetch_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """Fetch quarterly and annual balance sheet data"""
        params = {
            "function": "BALANCE_SHEET",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "quarterlyReports" not in data and "annualReports" not in data:
                print(f"No balance sheet for {symbol}")
                return None

            return data
        except Exception as e:
            print(f"Error fetching balance sheet for {symbol}: {e}")
            return None

    def fetch_cash_flow(self, symbol: str) -> Optional[Dict]:
        """Fetch quarterly and annual cash flow data"""
        params = {
            "function": "CASH_FLOW",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "quarterlyReports" not in data and "annualReports" not in data:
                print(f"No cash flow for {symbol}")
                return None

            return data
        except Exception as e:
            print(f"Error fetching cash flow for {symbol}: {e}")
            return None

    def _safe_float(self, value: any) -> Optional[float]:
        """Safely convert value to float, return None if invalid"""
        if value is None or value == "None" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _calculate_derived_metrics(
        self,
        overview: Dict,
        income: Dict,
        balance: Dict,
        cash_flow: Dict,
        market_cap: Optional[float] = None,
    ) -> Dict:
        """Calculate derived fundamental metrics based on Yartseva's research

        Key metrics calculated:
        - FCF/Price (free cash flow yield) - STRONGEST PREDICTOR
        - Book-to-Market ratio - value factor
        - ROA (return on assets) - profitability
        - EBITDA margin - operating efficiency
        - Reinvestment quality flags
        """
        metrics = {}

        # Use market cap from overview if not provided
        if market_cap is None:
            market_cap = self._safe_float(overview.get("MarketCapitalization"))

        # Get key values
        total_assets = self._safe_float(balance.get("totalAssets"))
        total_equity = self._safe_float(balance.get("totalShareholderEquity"))
        net_income = self._safe_float(income.get("netIncome"))
        operating_income = self._safe_float(income.get("operatingIncome"))
        ebitda = self._safe_float(income.get("ebitda"))
        revenue = self._safe_float(income.get("totalRevenue"))

        operating_cash_flow = self._safe_float(cash_flow.get("operatingCashflow"))
        capital_expenditures = self._safe_float(cash_flow.get("capitalExpenditures"))

        # Calculate free cash flow (OCF - CapEx)
        if operating_cash_flow and capital_expenditures:
            # CapEx is usually negative in Alpha Vantage data
            if capital_expenditures < 0:
                free_cash_flow = operating_cash_flow + capital_expenditures
            else:
                free_cash_flow = operating_cash_flow - capital_expenditures
            metrics["free_cash_flow"] = free_cash_flow
        else:
            free_cash_flow = None
            metrics["free_cash_flow"] = None

        # FCF/Price ratio (free cash flow yield) - STRONGEST PREDICTOR in Yartseva's paper
        if free_cash_flow and market_cap and market_cap > 0:
            metrics["fcf_price_ratio"] = free_cash_flow / market_cap
        else:
            metrics["fcf_price_ratio"] = None

        # Book-to-Market ratio - value factor
        if total_equity and market_cap and market_cap > 0:
            metrics["book_to_market"] = total_equity / market_cap
        else:
            metrics["book_to_market"] = None

        # ROA (Return on Assets) - profitability
        if net_income and total_assets and total_assets > 0:
            metrics["roa"] = net_income / total_assets
        else:
            metrics["roa"] = None

        # ROE (Return on Equity)
        if net_income and total_equity and total_equity > 0:
            metrics["roe"] = net_income / total_equity
        else:
            metrics["roe"] = None

        # EBITDA margin - operating efficiency
        if ebitda and revenue and revenue > 0:
            metrics["ebitda_margin"] = ebitda / revenue
        else:
            metrics["ebitda_margin"] = None

        # EBIT margin (operating margin)
        if operating_income and revenue and revenue > 0:
            metrics["ebit_margin"] = operating_income / revenue
        else:
            metrics["ebit_margin"] = None

        # Quality flags
        metrics["has_negative_equity"] = total_equity is not None and total_equity < 0
        metrics["is_profitable"] = operating_income is not None and operating_income > 0

        return metrics

    def update_fundamental_data_quarterly(
        self, db: Session, stock: Stock, max_quarters: int = 8
    ) -> bool:
        """Update quarterly fundamental data for a stock

        Fetches income statement, balance sheet, and cash flow data from
        Alpha Vantage and stores it in FundamentalDataQuarterly table.

        Args:
            db: Database session
            stock: Stock model instance
            max_quarters: Maximum number of quarters to fetch (default 8 = 2 years)

        Returns:
            True if successful, False otherwise
        """
        import time

        print(f"Fetching fundamental data for {stock.symbol}...")

        # Fetch all fundamental data types
        # Note: Alpha Vantage rate limit is 5 calls/min for free tier
        overview = self.fetch_company_overview(stock.symbol)
        time.sleep(13)  # Rate limiting

        income_stmt = self.fetch_income_statement(stock.symbol)
        time.sleep(13)

        balance_sheet = self.fetch_balance_sheet(stock.symbol)
        time.sleep(13)

        cash_flow = self.fetch_cash_flow(stock.symbol)

        if not all([overview, income_stmt, balance_sheet, cash_flow]):
            print(f"Failed to fetch complete fundamental data for {stock.symbol}")
            return False

        # Get market cap from overview
        market_cap = self._safe_float(overview.get("MarketCapitalization"))

        # Get existing quarters in DB
        existing_quarters = set(
            record[0]
            for record in db.query(FundamentalDataQuarterly.fiscal_date)
            .filter(FundamentalDataQuarterly.stock_id == stock.id)
            .all()
        )

        # Process quarterly reports
        new_records = 0
        quarterly_reports = income_stmt.get("quarterlyReports", [])[:max_quarters]

        for i, income_q in enumerate(quarterly_reports):
            fiscal_date_str = income_q.get("fiscalDateEnding")
            if not fiscal_date_str:
                continue

            fiscal_date = datetime.strptime(fiscal_date_str, "%Y-%m-%d").date()

            # Skip if already exists
            if fiscal_date in existing_quarters:
                continue

            # Find matching balance sheet and cash flow quarters
            balance_q = next(
                (
                    q
                    for q in balance_sheet.get("quarterlyReports", [])
                    if q.get("fiscalDateEnding") == fiscal_date_str
                ),
                {},
            )
            cash_q = next(
                (
                    q
                    for q in cash_flow.get("quarterlyReports", [])
                    if q.get("fiscalDateEnding") == fiscal_date_str
                ),
                {},
            )

            # Calculate derived metrics
            derived = self._calculate_derived_metrics(
                overview, income_q, balance_q, cash_q, market_cap
            )

            # Create fundamental data record
            fundamental = FundamentalDataQuarterly(
                stock_id=stock.id,
                fiscal_date=fiscal_date,
                market_cap=market_cap,
                enterprise_value=self._safe_float(overview.get("EnterpriseValue")),
                # Balance sheet
                total_assets=self._safe_float(balance_q.get("totalAssets")),
                total_equity=self._safe_float(balance_q.get("totalShareholderEquity")),
                book_value_per_share=self._safe_float(overview.get("BookValue")),
                total_debt=self._safe_float(balance_q.get("longTermDebt")),
                cash_and_equivalents=self._safe_float(
                    balance_q.get("cashAndCashEquivalentsAtCarryingValue")
                ),
                # Income statement
                revenue=self._safe_float(income_q.get("totalRevenue")),
                operating_income=self._safe_float(income_q.get("operatingIncome")),
                ebitda=self._safe_float(income_q.get("ebitda")),
                net_income=self._safe_float(income_q.get("netIncome")),
                # Cash flow
                operating_cash_flow=self._safe_float(
                    cash_q.get("operatingCashflow")
                ),
                free_cash_flow=derived["free_cash_flow"],
                capital_expenditures=self._safe_float(
                    cash_q.get("capitalExpenditures")
                ),
                # Calculated ratios (Yartseva's key metrics)
                fcf_price_ratio=derived["fcf_price_ratio"],
                book_to_market=derived["book_to_market"],
                roa=derived["roa"],
                roe=derived["roe"],
                ebitda_margin=derived["ebitda_margin"],
                ebit_margin=derived["ebit_margin"],
                # Quality flags
                has_negative_equity=derived["has_negative_equity"],
                is_profitable=derived["is_profitable"],
            )

            db.add(fundamental)
            new_records += 1

        # Calculate growth rates (requires at least 2 quarters)
        if new_records > 0:
            self._calculate_quarterly_growth_rates(db, stock)

        db.commit()
        print(f"Updated {stock.symbol}: {new_records} new quarterly fundamental records")
        return True

    def _calculate_quarterly_growth_rates(self, db: Session, stock: Stock):
        """Calculate QoQ and YoY growth rates for fundamental metrics

        Specifically calculates:
        - Asset growth rate (for reinvestment quality check)
        - EBITDA growth rate (for reinvestment quality check)
        - Revenue growth rate
        """
        # Get all quarterly data for this stock, ordered by date
        quarters = (
            db.query(FundamentalDataQuarterly)
            .filter(FundamentalDataQuarterly.stock_id == stock.id)
            .order_by(FundamentalDataQuarterly.fiscal_date.desc())
            .all()
        )

        if len(quarters) < 2:
            return

        # Calculate YoY growth (compare to 4 quarters ago)
        for i, current_q in enumerate(quarters):
            # Look for quarter 4 periods ago (1 year)
            if i + 4 < len(quarters):
                prior_q = quarters[i + 4]

                # Asset growth
                if current_q.total_assets and prior_q.total_assets and prior_q.total_assets > 0:
                    current_q.asset_growth_rate = (
                        (current_q.total_assets - prior_q.total_assets)
                        / prior_q.total_assets
                    )

                # EBITDA growth
                if current_q.ebitda and prior_q.ebitda and prior_q.ebitda > 0:
                    current_q.ebitda_growth_rate = (
                        (current_q.ebitda - prior_q.ebitda) / prior_q.ebitda
                    )

                # Revenue growth
                if current_q.revenue and prior_q.revenue and prior_q.revenue > 0:
                    current_q.revenue_growth_rate = (
                        (current_q.revenue - prior_q.revenue) / prior_q.revenue
                    )

                # Reinvestment quality flag: True if asset_growth <= ebitda_growth
                # Yartseva's finding: Asset growth > EBITDA growth is a NEGATIVE signal
                if (
                    current_q.asset_growth_rate is not None
                    and current_q.ebitda_growth_rate is not None
                ):
                    current_q.reinvestment_quality_flag = (
                        current_q.asset_growth_rate <= current_q.ebitda_growth_rate
                    )

        db.commit()
