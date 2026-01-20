"""
Avantis-Style TSX Screener

Mirrors Avantis Investors' methodology for Canadian stocks:
- Value factor: Book-to-Price (inverse of P/B)
- Profitability factor: Cash from Operations / Book Equity
- Size factor: Small cap tilt ($300M-$2B)
- Quality screens: Positive profitability, no negative equity

This is a more diversified, factor-based approach compared to the
concentrated multibagger screening. Suitable for core portfolio holdings.

Key differences from multibagger screening:
1. Uses cash-based profitability (like Avantis) vs FCF focus
2. Holds more stocks (15-25) vs concentrated (5-10)
3. Equal or factor weighting vs score-based ranking
4. No explicit market timing filters
5. Quarterly rebalancing vs opportunistic entry
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.stock import Stock
from app.models.fundamentals import FundamentalDataQuarterly


@dataclass
class AvantisCandidate:
    """A stock that passes Avantis-style factor screening"""
    stock_id: int
    symbol: str
    name: str
    sector: str

    # Core Avantis factors
    market_cap: float
    book_to_price: float  # Book equity / Market cap (value factor)
    cash_profitability: float  # OCF / Book equity (profitability factor)

    # Additional metrics
    fcf_price_ratio: Optional[float]  # Your edge metric
    roa: Optional[float]
    roe: Optional[float]

    # Quality flags
    is_profitable: bool
    reinvestment_quality_flag: bool

    # Factor score (0-100)
    factor_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stock_id": self.stock_id,
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "market_cap": self.market_cap,
            "book_to_price": self.book_to_price,
            "cash_profitability": self.cash_profitability,
            "fcf_price_ratio": self.fcf_price_ratio,
            "roa": self.roa,
            "roe": self.roe,
            "is_profitable": self.is_profitable,
            "reinvestment_quality_flag": self.reinvestment_quality_flag,
            "factor_score": self.factor_score,
        }


class AvantisTSXScreener:
    """
    Screens TSX stocks using Avantis Investors' factor-based methodology

    This creates a diversified portfolio of small cap value stocks with
    strong profitability, suitable for core holdings.
    """

    def __init__(
        self,
        min_book_to_price: float = 0.40,  # Value factor threshold
        min_cash_profitability: float = 0.10,  # 10% cash ROE minimum
        min_market_cap: float = 300_000_000,  # $300M
        max_market_cap: float = 2_000_000_000,  # $2B
        include_fcf_filter: bool = True,  # Add FCF/Price as quality screen
        min_fcf_price_ratio: float = 0.03,  # Lower than multibagger (3%)
    ):
        """
        Initialize Avantis-style screener with factor thresholds

        Args:
            min_book_to_price: Minimum book-to-price ratio (value screen)
            min_cash_profitability: Minimum OCF/Book Equity (profitability screen)
            min_market_cap: Minimum market cap for small cap universe
            max_market_cap: Maximum market cap for small cap universe
            include_fcf_filter: Whether to add FCF/Price quality screen
            min_fcf_price_ratio: Minimum FCF yield if filter enabled
        """
        self.min_book_to_price = min_book_to_price
        self.min_cash_profitability = min_cash_profitability
        self.min_market_cap = min_market_cap
        self.max_market_cap = max_market_cap
        self.include_fcf_filter = include_fcf_filter
        self.min_fcf_price_ratio = min_fcf_price_ratio

    def screen(
        self,
        db: Session,
        limit: int = 25,
        return_scores: bool = True
    ) -> List[Tuple[Stock, FundamentalDataQuarterly, float]]:
        """
        Screen for Avantis-style factor candidates

        Returns top stocks by factor score (value + profitability + quality)

        Args:
            db: Database session
            limit: Maximum number of stocks to return
            return_scores: Whether to return (stock, fundamentals, score) tuples

        Returns:
            List of (Stock, FundamentalDataQuarterly, score) tuples
        """
        # Get latest fundamental data for each stock
        subquery = (
            db.query(
                FundamentalDataQuarterly.stock_id,
                func.max(FundamentalDataQuarterly.fiscal_date).label('max_date')
            )
            .group_by(FundamentalDataQuarterly.stock_id)
            .subquery()
        )

        # Build query with Avantis-style filters
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
            .filter(
                Stock.is_active == True,
                # Value factor: Book-to-Price (same as Book-to-Market in our model)
                FundamentalDataQuarterly.book_to_market >= self.min_book_to_price,
                # Size factor: Small cap range
                FundamentalDataQuarterly.market_cap >= self.min_market_cap,
                FundamentalDataQuarterly.market_cap <= self.max_market_cap,
                # Quality: Profitability required
                FundamentalDataQuarterly.is_profitable == True,
                # Quality: No negative equity
                FundamentalDataQuarterly.has_negative_equity == False,
                # Profitability factor: Need operating cash flow data
                FundamentalDataQuarterly.operating_cash_flow.isnot(None),
                FundamentalDataQuarterly.total_equity.isnot(None),
            )
        )

        # Optional: Add FCF/Price quality screen (your edge)
        if self.include_fcf_filter:
            query = query.filter(
                FundamentalDataQuarterly.fcf_price_ratio >= self.min_fcf_price_ratio
            )

        results = query.all()

        # Calculate factor scores
        scored_results = []
        for stock, fundamentals in results:
            # Calculate cash profitability: OCF / Book Equity
            cash_prof = (
                fundamentals.operating_cash_flow / fundamentals.total_equity
                if fundamentals.total_equity and fundamentals.total_equity > 0
                else 0
            )

            # Skip if cash profitability too low
            if cash_prof < self.min_cash_profitability:
                continue

            # Calculate factor score
            score = self._calculate_factor_score(fundamentals, cash_prof)
            scored_results.append((stock, fundamentals, score))

        # Sort by factor score (descending)
        scored_results.sort(key=lambda x: x[2], reverse=True)

        # Return top N
        return scored_results[:limit]

    def _calculate_factor_score(
        self,
        fundamentals: FundamentalDataQuarterly,
        cash_profitability: float
    ) -> float:
        """
        Calculate composite factor score (0-100)

        Avantis-style weighting:
        - Value (Book/Price): 40 points
        - Profitability (Cash ROE): 40 points
        - Quality bonuses: 20 points

        Args:
            fundamentals: Fundamental data for the stock
            cash_profitability: Calculated OCF / Book Equity

        Returns:
            Score from 0-100
        """
        score = 0.0

        # VALUE FACTOR: Book-to-Price (40 points max)
        # Scale: 0.40 = 20 pts, 0.80+ = 40 pts
        book_to_price = fundamentals.book_to_market or 0
        if book_to_price >= 0.40:
            value_score = min(40, 20 + (book_to_price - 0.40) * 50)
            score += value_score

        # PROFITABILITY FACTOR: Cash ROE (40 points max)
        # Scale: 10% = 20 pts, 30%+ = 40 pts
        if cash_profitability >= 0.10:
            prof_score = min(40, 20 + (cash_profitability - 0.10) * 100)
            score += prof_score

        # QUALITY BONUSES (20 points)

        # Reinvestment quality: 10 points
        if fundamentals.reinvestment_quality_flag:
            score += 10

        # FCF/Price > 5%: 5 points bonus (if available)
        if fundamentals.fcf_price_ratio and fundamentals.fcf_price_ratio >= 0.05:
            score += 5

        # Strong ROA (>10%): 5 points bonus
        if fundamentals.roa and fundamentals.roa >= 0.10:
            score += 5

        return score

    def get_candidates(
        self,
        db: Session,
        limit: int = 25
    ) -> List[AvantisCandidate]:
        """
        Get screened candidates as AvantisCandidate objects

        Useful for detailed analysis and portfolio construction

        Args:
            db: Database session
            limit: Maximum number of candidates

        Returns:
            List of AvantisCandidate objects
        """
        results = self.screen(db, limit=limit, return_scores=True)

        candidates = []
        for stock, fundamentals, score in results:
            # Calculate cash profitability
            cash_prof = (
                fundamentals.operating_cash_flow / fundamentals.total_equity
                if fundamentals.total_equity and fundamentals.total_equity > 0
                else 0
            )

            candidate = AvantisCandidate(
                stock_id=stock.id,
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector or "Unknown",
                market_cap=fundamentals.market_cap,
                book_to_price=fundamentals.book_to_market,
                cash_profitability=cash_prof,
                fcf_price_ratio=fundamentals.fcf_price_ratio,
                roa=fundamentals.roa,
                roe=fundamentals.roe,
                is_profitable=fundamentals.is_profitable,
                reinvestment_quality_flag=fundamentals.reinvestment_quality_flag,
                factor_score=score,
            )
            candidates.append(candidate)

        return candidates

    def get_portfolio_weights(
        self,
        db: Session,
        num_holdings: int = 20,
        weighting_method: str = "equal"  # "equal", "factor_score", "market_cap"
    ) -> List[Tuple[Stock, float]]:
        """
        Generate portfolio with weights for Avantis-style holdings

        Args:
            db: Database session
            num_holdings: Number of stocks to hold
            weighting_method: How to weight stocks
                - "equal": Equal weight (like most Avantis ETFs)
                - "factor_score": Weight by factor score
                - "market_cap": Weight by market cap (min variance)

        Returns:
            List of (Stock, weight) tuples summing to 1.0
        """
        results = self.screen(db, limit=num_holdings, return_scores=True)

        if not results:
            return []

        if weighting_method == "equal":
            weight = 1.0 / len(results)
            return [(stock, weight) for stock, _, _ in results]

        elif weighting_method == "factor_score":
            scores = [score for _, _, score in results]
            total_score = sum(scores)
            return [
                (stock, score / total_score)
                for stock, _, score in results
            ]

        elif weighting_method == "market_cap":
            market_caps = [fund.market_cap for _, fund, _ in results]
            total_cap = sum(market_caps)
            return [
                (stock, fund.market_cap / total_cap)
                for stock, fund, _ in results
            ]

        else:
            raise ValueError(f"Unknown weighting method: {weighting_method}")

    def get_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Get screening statistics for the Avantis-style universe

        Returns:
            Dictionary with screening stats
        """
        # Get all stocks with fundamental data
        total_with_data = (
            db.query(func.count(func.distinct(FundamentalDataQuarterly.stock_id)))
            .join(Stock)
            .filter(Stock.is_active == True)
            .scalar()
        )

        # Get stocks passing each filter
        results = self.screen(db, limit=1000, return_scores=True)
        passing_all = len(results)

        if results:
            avg_book_to_price = sum(f.book_to_market for _, f, _ in results) / len(results)

            # Calculate average cash profitability
            cash_profs = []
            for _, f, _ in results:
                if f.operating_cash_flow and f.total_equity and f.total_equity > 0:
                    cash_profs.append(f.operating_cash_flow / f.total_equity)
            avg_cash_prof = sum(cash_profs) / len(cash_profs) if cash_profs else 0

            avg_fcf_price = sum(
                f.fcf_price_ratio for _, f, _ in results if f.fcf_price_ratio
            ) / len([f for _, f, _ in results if f.fcf_price_ratio])

            avg_score = sum(s for _, _, s in results) / len(results)
        else:
            avg_book_to_price = 0
            avg_cash_prof = 0
            avg_fcf_price = 0
            avg_score = 0

        return {
            "total_stocks_with_fundamentals": total_with_data,
            "passing_all_filters": passing_all,
            "pass_rate": passing_all / total_with_data if total_with_data > 0 else 0,
            "avg_book_to_price": avg_book_to_price,
            "avg_cash_profitability": avg_cash_prof,
            "avg_fcf_price_ratio": avg_fcf_price,
            "avg_factor_score": avg_score,
            "filters": {
                "min_book_to_price": self.min_book_to_price,
                "min_cash_profitability": self.min_cash_profitability,
                "market_cap_range": f"${self.min_market_cap:,.0f} - ${self.max_market_cap:,.0f}",
                "fcf_filter_enabled": self.include_fcf_filter,
                "min_fcf_price_ratio": self.min_fcf_price_ratio if self.include_fcf_filter else None,
            }
        }
