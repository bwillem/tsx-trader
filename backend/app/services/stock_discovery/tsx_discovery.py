"""
TSX Stock Discovery Service

Automatically discovers and maintains a list of TSX stocks that fit
the multibagger criteria (primarily market cap $300M-$2B).

This service:
1. Fetches current TSX listings
2. Checks market caps via Alpha Vantage
3. Adds new candidates to the database
4. Deactivates stocks that no longer fit criteria
5. Runs periodically to keep the universe fresh
"""

import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.stock import Stock
from app.services.market_data import AlphaVantageService


class TSXStockDiscovery:
    """Discovers and maintains TSX stock universe for multibagger screening"""

    def __init__(
        self,
        min_market_cap: float = 300_000_000,  # $300M
        max_market_cap: float = 2_000_000_000,  # $2B
        include_large_caps: bool = True,  # Keep some large caps for diversification
        rate_limit_delay: int = 13,  # Seconds between API calls
    ):
        """Initialize discovery service

        Args:
            min_market_cap: Minimum market cap for small caps ($300M)
            max_market_cap: Maximum market cap for small caps ($2B)
            include_large_caps: Whether to keep large blue chips for diversification
            rate_limit_delay: Delay between API calls (default 13s for free tier)
        """
        self.min_market_cap = min_market_cap
        self.max_market_cap = max_market_cap
        self.include_large_caps = include_large_caps
        self.rate_limit_delay = rate_limit_delay
        self.av_service = AlphaVantageService()

    def discover_and_update(
        self,
        db: Session,
        symbol_list: Optional[List[str]] = None,
        max_new_stocks: int = 50,
    ) -> Dict[str, any]:
        """Discover new stocks and update existing ones

        Args:
            db: Database session
            symbol_list: Optional list of symbols to check (if None, uses default TSX list)
            max_new_stocks: Maximum number of new stocks to add in one run

        Returns:
            Dictionary with statistics about the update
        """
        print(f"=== TSX Stock Discovery - {datetime.utcnow()} ===\n")

        stats = {
            "checked": 0,
            "added": 0,
            "updated": 0,
            "deactivated": 0,
            "errors": 0,
            "in_range": [],
            "out_of_range": [],
            "large_caps_kept": [],
        }

        # If no symbol list provided, use a curated list of potential candidates
        if symbol_list is None:
            symbol_list = self._get_default_tsx_candidates()

        print(f"Checking {len(symbol_list)} TSX symbols...\n")

        for symbol in symbol_list:
            if stats["added"] >= max_new_stocks:
                print(f"\nReached max new stocks limit ({max_new_stocks}), stopping.")
                break

            stats["checked"] += 1

            try:
                # Check if stock exists
                stock = db.query(Stock).filter(Stock.symbol == symbol).first()

                # Get market cap and company info
                overview = self.av_service.fetch_company_overview(symbol)

                if not overview or "Symbol" not in overview:
                    print(f"⚠ {symbol}: No data available")
                    stats["errors"] += 1
                    time.sleep(self.rate_limit_delay)
                    continue

                # Parse market cap and name
                market_cap_str = overview.get("MarketCapitalization")
                market_cap = float(market_cap_str) if market_cap_str and market_cap_str != "None" else None

                name = overview.get("Name", symbol)
                sector = overview.get("Sector", "Unknown")
                industry = overview.get("Industry", "Unknown")
                exchange = overview.get("Exchange", "TSX")

                if not market_cap:
                    print(f"⚠ {symbol}: No market cap data")
                    stats["errors"] += 1
                    time.sleep(self.rate_limit_delay)
                    continue

                # Determine if stock fits criteria
                in_small_cap_range = self.min_market_cap <= market_cap <= self.max_market_cap
                is_large_cap = market_cap > 10_000_000_000  # $10B+
                is_blue_chip = symbol in self._get_blue_chip_symbols()

                # Decision logic
                should_be_active = in_small_cap_range or (self.include_large_caps and is_blue_chip)

                if stock:
                    # Existing stock - update status
                    if should_be_active and not stock.is_active:
                        stock.is_active = True
                        stock.sector = sector
                        stock.industry = industry
                        print(f"✓ {symbol}: Reactivated (${market_cap:,.0f})")
                        stats["updated"] += 1

                    elif not should_be_active and stock.is_active:
                        stock.is_active = False
                        reason = "grew too large" if market_cap > self.max_market_cap else "became too small"
                        print(f"○ {symbol}: Deactivated ({reason}) (${market_cap:,.0f})")
                        stats["deactivated"] += 1
                        stats["out_of_range"].append({
                            "symbol": symbol,
                            "market_cap": market_cap,
                            "reason": reason
                        })

                    elif should_be_active:
                        # Update metadata
                        stock.name = name
                        stock.sector = sector
                        stock.industry = industry
                        print(f"  {symbol}: Already active (${market_cap:,.0f})")

                else:
                    # New stock
                    if should_be_active:
                        new_stock = Stock(
                            symbol=symbol,
                            name=name,
                            exchange=exchange,
                            sector=sector,
                            industry=industry,
                            is_active=True,
                        )
                        db.add(new_stock)

                        if in_small_cap_range:
                            print(f"✓ {symbol}: Added as small cap (${market_cap:,.0f}) - {name}")
                            stats["added"] += 1
                            stats["in_range"].append({
                                "symbol": symbol,
                                "name": name,
                                "market_cap": market_cap,
                                "sector": sector
                            })
                        else:
                            print(f"✓ {symbol}: Added as blue chip (${market_cap:,.0f}) - {name}")
                            stats["added"] += 1
                            stats["large_caps_kept"].append(symbol)
                    else:
                        print(f"  {symbol}: Outside range (${market_cap:,.0f}), skipping")
                        stats["out_of_range"].append({
                            "symbol": symbol,
                            "market_cap": market_cap,
                            "reason": "outside range"
                        })

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            except Exception as e:
                print(f"✗ {symbol}: Error - {e}")
                stats["errors"] += 1
                time.sleep(self.rate_limit_delay)

        # Commit changes
        db.commit()

        print(f"\n{'='*60}")
        print(f"DISCOVERY COMPLETE")
        print(f"{'='*60}")
        print(f"Symbols checked:     {stats['checked']}")
        print(f"New stocks added:    {stats['added']}")
        print(f"Stocks updated:      {stats['updated']}")
        print(f"Stocks deactivated:  {stats['deactivated']}")
        print(f"Errors:              {stats['errors']}")
        print(f"\nSmall caps found:    {len(stats['in_range'])}")
        print(f"Blue chips kept:     {len(stats['large_caps_kept'])}")
        print(f"Out of range:        {len(stats['out_of_range'])}")

        return stats

    def review_existing_stocks(self, db: Session) -> Dict[str, any]:
        """Review all existing stocks and update their active status

        Checks market caps of all stocks in the database and deactivates
        those that no longer fit the criteria.

        Args:
            db: Database session

        Returns:
            Dictionary with review statistics
        """
        print(f"=== Reviewing Existing Stocks - {datetime.utcnow()} ===\n")

        stats = {
            "total_stocks": 0,
            "reviewed": 0,
            "still_in_range": 0,
            "deactivated": 0,
            "errors": 0,
            "details": []
        }

        # Get all active stocks
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        stats["total_stocks"] = len(stocks)

        print(f"Reviewing {len(stocks)} active stocks...\n")

        for stock in stocks:
            stats["reviewed"] += 1

            try:
                # Fetch current market cap
                overview = self.av_service.fetch_company_overview(stock.symbol)

                if not overview or "Symbol" not in overview:
                    print(f"⚠ {stock.symbol}: No data available")
                    stats["errors"] += 1
                    time.sleep(self.rate_limit_delay)
                    continue

                market_cap_str = overview.get("MarketCapitalization")
                market_cap = float(market_cap_str) if market_cap_str and market_cap_str != "None" else None

                if not market_cap:
                    print(f"⚠ {stock.symbol}: No market cap data")
                    stats["errors"] += 1
                    time.sleep(self.rate_limit_delay)
                    continue

                # Check if still in range
                in_range = self.min_market_cap <= market_cap <= self.max_market_cap
                is_blue_chip = stock.symbol in self._get_blue_chip_symbols()
                should_keep = in_range or (self.include_large_caps and is_blue_chip)

                if should_keep:
                    print(f"✓ {stock.symbol}: Still in range (${market_cap:,.0f})")
                    stats["still_in_range"] += 1
                else:
                    stock.is_active = False
                    reason = "grew too large" if market_cap > self.max_market_cap else "became too small"
                    print(f"○ {stock.symbol}: Deactivated ({reason}) (${market_cap:,.0f})")
                    stats["deactivated"] += 1
                    stats["details"].append({
                        "symbol": stock.symbol,
                        "market_cap": market_cap,
                        "reason": reason
                    })

                time.sleep(self.rate_limit_delay)

            except Exception as e:
                print(f"✗ {stock.symbol}: Error - {e}")
                stats["errors"] += 1
                time.sleep(self.rate_limit_delay)

        db.commit()

        print(f"\n{'='*60}")
        print(f"REVIEW COMPLETE")
        print(f"{'='*60}")
        print(f"Total stocks:        {stats['total_stocks']}")
        print(f"Reviewed:            {stats['reviewed']}")
        print(f"Still in range:      {stats['still_in_range']}")
        print(f"Deactivated:         {stats['deactivated']}")
        print(f"Errors:              {stats['errors']}")

        return stats

    def _get_default_tsx_candidates(self) -> List[str]:
        """Get a curated list of potential TSX small cap candidates

        This is a starting point - you can expand this list or fetch from
        a TSX listing API.

        Returns:
            List of TSX symbols to check
        """
        # Small & mid cap candidates across various sectors
        return [
            # Technology
            "WELL.TO", "DCBO.TO", "TOI.TO", "GDNP.TO", "REAL.TO", "DOC.TO",
            "OTEX.TO", "ENGH.TO", "GOOS.TO", "LSPD.TO",

            # Energy & Resources
            "PXT.TO", "TVE.TO", "BTE.TO", "VII.TO", "WCP.TO", "ERF.TO",
            "CPG.TO", "KEL.TO", "BIR.TO", "ARX.TO", "PEY.TO",

            # Materials & Mining
            "HBM.TO", "TKO.TO", "FM.TO", "CS.TO", "EDV.TO", "OR.TO",
            "EQX.TO", "SMT.TO", "MAI.TO", "NGD.TO",

            # Industrials
            "NFI.TO", "BYD.TO", "GFL.TO", "TOY.TO", "MTY.TO", "GIL.TO",
            "TIH.TO", "PKI.TO", "CWB.TO",

            # Healthcare
            "MT.TO", "QIPT.TO", "PHM.TO", "NHC.TO", "CXRX.TO",

            # Financials (smaller)
            "EQB.TO", "GSY.TO", "HCG.TO", "LB.TO", "FSV.TO", "DXT.TO",

            # Real Estate
            "CAR-UN.TO", "HR-UN.TO", "DIR-UN.TO", "SRU-UN.TO", "IIP-UN.TO",
            "MRT-UN.TO", "BTB-UN.TO",

            # Consumer
            "TFII.TO", "DOL.TO", "ATD.TO", "QSR.TO", "MTY.TO", "PZA.TO",
            "RECP.TO", "GIL.TO",

            # Telecom
            "RCI-B.TO", "T.TO", "BCE.TO",
        ]

    def _get_blue_chip_symbols(self) -> List[str]:
        """Get list of blue chip symbols to always keep

        These are large caps kept for diversification even though
        they're outside the multibagger range.

        Returns:
            List of blue chip symbols
        """
        return [
            # Big banks
            "TD.TO", "RY.TO", "BMO.TO", "BNS.TO", "CM.TO",

            # Energy majors
            "ENB.TO", "CNQ.TO", "SU.TO", "TRP.TO",

            # Railroads
            "CP.TO", "CNR.TO",

            # Tech
            "SHOP.TO",

            # Telecom
            "BCE.TO", "T.TO", "RCI-B.TO",

            # Utilities
            "FTS.TO", "EMA.TO",

            # Consumer
            "ATD.TO", "DOL.TO", "QSR.TO",
        ]

    def get_discovery_stats(self, db: Session) -> Dict[str, any]:
        """Get current statistics about the stock universe

        Returns:
            Dictionary with current stock universe statistics
        """
        total_stocks = db.query(Stock).count()
        active_stocks = db.query(Stock).filter(Stock.is_active == True).count()
        inactive_stocks = total_stocks - active_stocks

        # Get stocks by exchange
        tsx_stocks = db.query(Stock).filter(Stock.exchange == "TSX").count()

        return {
            "total_stocks": total_stocks,
            "active_stocks": active_stocks,
            "inactive_stocks": inactive_stocks,
            "tsx_stocks": tsx_stocks,
            "last_updated": datetime.utcnow(),
        }
