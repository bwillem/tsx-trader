"""
Multibagger Stock Screener

Based on Anna Yartseva's research "The Alchemy of Multibagger Stocks" (2025),
this screener identifies stocks with the highest potential for 10x+ returns.

Key findings from the paper:
1. FCF/Price (free cash flow yield) - STRONGEST PREDICTOR (coefficients 46-82)
2. Book-to-Market ratio > 0.40 with positive profitability
3. Small cap stocks ($300M-$2B market cap)
4. Asset growth ≤ EBITDA growth (reinvestment quality)
5. Stocks near 12-month lows (entry timing)
6. No negative equity (automatic disqualifier)
7. 3-6 month momentum is NEGATIVE (mean reversion, not trend following)
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.models.stock import Stock, MarketDataDaily
from app.models.fundamentals import FundamentalDataQuarterly


@dataclass
class MultibaggerCandidate:
    """A stock that passes multibagger screening criteria"""
    stock_id: int
    symbol: str
    name: str
    sector: str

    # Fundamental metrics (from latest quarter)
    market_cap: float
    fcf_price_ratio: float  # Free cash flow yield - STRONGEST PREDICTOR
    book_to_market: float  # Value factor
    roa: float  # Profitability
    roe: float
    ebitda_margin: float

    # Growth metrics
    asset_growth_rate: Optional[float]
    ebitda_growth_rate: Optional[float]
    revenue_growth_rate: Optional[float]

    # Quality flags
    reinvestment_quality_flag: bool
    is_profitable: bool

    # Technical metrics (for timing)
    current_price: Optional[float]
    distance_from_52w_high: Optional[float]  # Negative = below high
    distance_from_52w_low: Optional[float]   # Positive = above low
    momentum_6m: Optional[float]  # Should be negative per Yartseva

    # Composite score
    multibagger_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "stock_id": self.stock_id,
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "market_cap": self.market_cap,
            "fcf_price_ratio": self.fcf_price_ratio,
            "book_to_market": self.book_to_market,
            "roa": self.roa,
            "roe": self.roe,
            "ebitda_margin": self.ebitda_margin,
            "asset_growth_rate": self.asset_growth_rate,
            "ebitda_growth_rate": self.ebitda_growth_rate,
            "revenue_growth_rate": self.revenue_growth_rate,
            "reinvestment_quality_flag": self.reinvestment_quality_flag,
            "is_profitable": self.is_profitable,
            "current_price": self.current_price,
            "distance_from_52w_high": self.distance_from_52w_high,
            "distance_from_52w_low": self.distance_from_52w_low,
            "momentum_6m": self.momentum_6m,
            "multibagger_score": self.multibagger_score,
        }


class MultibaggerScreener:
    """Screens for potential multibagger stocks using Yartseva's criteria

    The screening process:
    1. Fundamental filters (hard requirements)
    2. Scoring based on key metrics
    3. Technical timing overlay
    4. Ranked output
    """

    def __init__(
        self,
        min_fcf_price_ratio: float = 0.05,  # 5% FCF yield minimum
        min_book_to_market: float = 0.40,   # Yartseva's threshold
        min_market_cap: float = 300_000_000,  # $300M minimum
        max_market_cap: float = 2_000_000_000,  # $2B maximum (small cap)
        require_profitability: bool = True,
        exclude_negative_equity: bool = True,
        require_reinvestment_quality: bool = False,  # Optional since needs 2+ years data
    ):
        """Initialize screener with Yartseva-based criteria

        Args:
            min_fcf_price_ratio: Minimum FCF/Price ratio (free cash flow yield)
            min_book_to_market: Minimum B/M ratio (0.40 per Yartseva)
            min_market_cap: Minimum market cap ($300M per Yartseva)
            max_market_cap: Maximum market cap ($2B for small caps)
            require_profitability: Must have positive operating income
            exclude_negative_equity: Exclude stocks with negative equity
            require_reinvestment_quality: Require asset_growth <= ebitda_growth
        """
        self.min_fcf_price_ratio = min_fcf_price_ratio
        self.min_book_to_market = min_book_to_market
        self.min_market_cap = min_market_cap
        self.max_market_cap = max_market_cap
        self.require_profitability = require_profitability
        self.exclude_negative_equity = exclude_negative_equity
        self.require_reinvestment_quality = require_reinvestment_quality

    def screen(
        self,
        db: Session,
        limit: int = 20,
        include_technical: bool = True
    ) -> List[MultibaggerCandidate]:
        """Run multibagger screening on all stocks

        Args:
            db: Database session
            limit: Maximum number of results to return
            include_technical: Whether to include technical timing metrics

        Returns:
            List of MultibaggerCandidate objects, ranked by multibagger_score
        """
        # Get latest fundamental data for each stock
        # We use a subquery to get the most recent quarter for each stock
        subquery = (
            db.query(
                FundamentalDataQuarterly.stock_id,
                func.max(FundamentalDataQuarterly.fiscal_date).label('max_date')
            )
            .group_by(FundamentalDataQuarterly.stock_id)
            .subquery()
        )

        # Join to get full records for latest quarters
        query = (
            db.query(Stock, FundamentalDataQuarterly)
            .join(Stock.fundamental_data)
            .join(
                subquery,
                and_(
                    FundamentalDataQuarterly.stock_id == subquery.c.stock_id,
                    FundamentalDataQuarterly.fiscal_date == subquery.c.max_date
                )
            )
            .filter(Stock.is_active == True)
        )

        # Apply fundamental filters
        filters = []

        # CRITICAL: FCF/Price ratio (STRONGEST PREDICTOR)
        if self.min_fcf_price_ratio:
            filters.append(
                FundamentalDataQuarterly.fcf_price_ratio >= self.min_fcf_price_ratio
            )

        # CRITICAL: Book-to-Market ratio
        if self.min_book_to_market:
            filters.append(
                FundamentalDataQuarterly.book_to_market >= self.min_book_to_market
            )

        # Size factor: Small caps only ($300M-$2B)
        if self.min_market_cap:
            filters.append(
                FundamentalDataQuarterly.market_cap >= self.min_market_cap
            )
        if self.max_market_cap:
            filters.append(
                FundamentalDataQuarterly.market_cap <= self.max_market_cap
            )

        # Profitability requirement
        if self.require_profitability:
            filters.append(
                FundamentalDataQuarterly.is_profitable == True
            )

        # Exclude negative equity (RED FLAG)
        if self.exclude_negative_equity:
            filters.append(
                or_(
                    FundamentalDataQuarterly.has_negative_equity == False,
                    FundamentalDataQuarterly.has_negative_equity == None
                )
            )

        # Reinvestment quality
        if self.require_reinvestment_quality:
            filters.append(
                FundamentalDataQuarterly.reinvestment_quality_flag == True
            )

        query = query.filter(and_(*filters))

        results = query.all()

        # Convert to MultibaggerCandidate objects with scoring
        candidates = []

        for stock, fundamentals in results:
            # Calculate technical metrics if requested
            technical_data = None
            if include_technical:
                technical_data = self._get_technical_metrics(db, stock.id)

            # Calculate multibagger score
            score = self._calculate_multibagger_score(fundamentals, technical_data)

            candidate = MultibaggerCandidate(
                stock_id=stock.id,
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector or "Unknown",
                # Fundamental metrics
                market_cap=fundamentals.market_cap or 0,
                fcf_price_ratio=fundamentals.fcf_price_ratio or 0,
                book_to_market=fundamentals.book_to_market or 0,
                roa=fundamentals.roa or 0,
                roe=fundamentals.roe or 0,
                ebitda_margin=fundamentals.ebitda_margin or 0,
                # Growth metrics
                asset_growth_rate=fundamentals.asset_growth_rate,
                ebitda_growth_rate=fundamentals.ebitda_growth_rate,
                revenue_growth_rate=fundamentals.revenue_growth_rate,
                # Quality flags
                reinvestment_quality_flag=fundamentals.reinvestment_quality_flag or False,
                is_profitable=fundamentals.is_profitable or False,
                # Technical metrics
                current_price=technical_data.get("current_price") if technical_data else None,
                distance_from_52w_high=technical_data.get("distance_from_52w_high") if technical_data else None,
                distance_from_52w_low=technical_data.get("distance_from_52w_low") if technical_data else None,
                momentum_6m=technical_data.get("momentum_6m") if technical_data else None,
                # Score
                multibagger_score=score,
            )

            candidates.append(candidate)

        # Sort by multibagger score (highest first)
        candidates.sort(key=lambda x: x.multibagger_score, reverse=True)

        return candidates[:limit]

    def _get_technical_metrics(self, db: Session, stock_id: int) -> Optional[Dict[str, float]]:
        """Get technical timing metrics for a stock

        Calculates:
        - Current price
        - Distance from 52-week high/low
        - 6-month momentum (should be negative per Yartseva)
        """
        # Get data from last year
        one_year_ago = datetime.now() - timedelta(days=365)

        market_data = (
            db.query(MarketDataDaily)
            .filter(
                MarketDataDaily.stock_id == stock_id,
                MarketDataDaily.date >= one_year_ago.date()
            )
            .order_by(MarketDataDaily.date.desc())
            .all()
        )

        if not market_data or len(market_data) < 2:
            return None

        # Current price (most recent)
        current_price = market_data[0].close

        # 52-week high/low
        high_52w = max(d.high for d in market_data)
        low_52w = min(d.low for d in market_data)

        distance_from_high = (current_price - high_52w) / high_52w
        distance_from_low = (current_price - low_52w) / low_52w

        # 6-month momentum (should be negative = mean reversion opportunity)
        six_months_ago = datetime.now() - timedelta(days=180)
        six_month_data = [d for d in market_data if d.date >= six_months_ago.date()]

        if six_month_data and len(six_month_data) > 1:
            price_6m_ago = six_month_data[-1].close
            momentum_6m = (current_price - price_6m_ago) / price_6m_ago
        else:
            momentum_6m = None

        return {
            "current_price": current_price,
            "distance_from_52w_high": distance_from_high,
            "distance_from_52w_low": distance_from_low,
            "momentum_6m": momentum_6m,
        }

    def _calculate_multibagger_score(
        self,
        fundamentals: FundamentalDataQuarterly,
        technical: Optional[Dict[str, float]]
    ) -> float:
        """Calculate composite multibagger score

        Scoring based on Yartseva's regression coefficients:
        - FCF/Price: Highest weight (coefficients 46-82 in paper)
        - Book/Market: Medium weight
        - Profitability (ROA): Medium weight
        - Reinvestment quality: Bonus points
        - Technical timing: Bonus points (near lows, negative momentum)

        Score range: 0-100
        """
        score = 0.0

        # FCF/Price (40 points max) - STRONGEST PREDICTOR
        # Yartseva found coefficients of 46-82, we scale proportionally
        if fundamentals.fcf_price_ratio:
            # Scale: 0.10 FCF yield = 20 points, 0.20 = 40 points
            fcf_score = min(fundamentals.fcf_price_ratio * 200, 40)
            score += fcf_score

        # Book-to-Market (20 points max) - VALUE FACTOR
        if fundamentals.book_to_market:
            # Scale: 0.40 = 8 points, 1.00 = 20 points
            bm_score = min((fundamentals.book_to_market - 0.40) * 33.3, 20)
            score += max(bm_score, 0)

        # Profitability - ROA (15 points max)
        if fundamentals.roa:
            # Scale: 0.05 ROA = 7.5 points, 0.10 = 15 points
            roa_score = min(fundamentals.roa * 150, 15)
            score += max(roa_score, 0)

        # Reinvestment quality (10 points bonus)
        # Yartseva: Asset growth > EBITDA growth is NEGATIVE
        if fundamentals.reinvestment_quality_flag:
            score += 10

        # EBITDA margin (5 points max) - Operating efficiency
        if fundamentals.ebitda_margin and fundamentals.ebitda_margin > 0:
            ebitda_score = min(fundamentals.ebitda_margin * 50, 5)
            score += ebitda_score

        # Technical timing factors (10 points bonus)
        if technical:
            # Near 52-week low is positive (mean reversion opportunity)
            if technical.get("distance_from_52w_low") is not None:
                dist_low = technical["distance_from_52w_low"]
                # 0-10% above low = 5 points, 10-20% = 2.5 points
                if dist_low <= 0.10:
                    score += 5
                elif dist_low <= 0.20:
                    score += 2.5

            # Negative 6-month momentum is POSITIVE per Yartseva (mean reversion)
            if technical.get("momentum_6m") is not None:
                mom_6m = technical["momentum_6m"]
                # -10% to 0% momentum = 5 points, -20% to -10% = 3 points
                if -0.10 <= mom_6m < 0:
                    score += 5
                elif -0.20 <= mom_6m < -0.10:
                    score += 3

        return round(score, 2)

    def get_screening_stats(self, db: Session) -> Dict[str, Any]:
        """Get statistics about the screening universe

        Returns counts and averages to help understand the dataset
        """
        # Total stocks with fundamental data
        total_with_fundamentals = (
            db.query(func.count(func.distinct(FundamentalDataQuarterly.stock_id)))
            .scalar()
        )

        # Stocks passing each filter
        subquery = (
            db.query(
                FundamentalDataQuarterly.stock_id,
                func.max(FundamentalDataQuarterly.fiscal_date).label('max_date')
            )
            .group_by(FundamentalDataQuarterly.stock_id)
            .subquery()
        )

        base_query = (
            db.query(FundamentalDataQuarterly)
            .join(
                subquery,
                and_(
                    FundamentalDataQuarterly.stock_id == subquery.c.stock_id,
                    FundamentalDataQuarterly.fiscal_date == subquery.c.max_date
                )
            )
        )

        stats = {
            "total_stocks_with_fundamentals": total_with_fundamentals,
            "passing_fcf_filter": base_query.filter(
                FundamentalDataQuarterly.fcf_price_ratio >= self.min_fcf_price_ratio
            ).count(),
            "passing_bm_filter": base_query.filter(
                FundamentalDataQuarterly.book_to_market >= self.min_book_to_market
            ).count(),
            "passing_size_filter": base_query.filter(
                and_(
                    FundamentalDataQuarterly.market_cap >= self.min_market_cap,
                    FundamentalDataQuarterly.market_cap <= self.max_market_cap
                )
            ).count(),
            "passing_profitability_filter": base_query.filter(
                FundamentalDataQuarterly.is_profitable == True
            ).count(),
            "passing_all_filters": len(self.screen(db, limit=1000, include_technical=False)),
        }

        # Average metrics for stocks passing all filters
        passing_stocks = self.screen(db, limit=1000, include_technical=False)
        if passing_stocks:
            stats["avg_fcf_price_ratio"] = sum(s.fcf_price_ratio for s in passing_stocks) / len(passing_stocks)
            stats["avg_book_to_market"] = sum(s.book_to_market for s in passing_stocks) / len(passing_stocks)
            stats["avg_roa"] = sum(s.roa for s in passing_stocks) / len(passing_stocks)
            stats["avg_market_cap"] = sum(s.market_cap for s in passing_stocks) / len(passing_stocks)

        return stats
