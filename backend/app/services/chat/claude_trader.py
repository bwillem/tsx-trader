import anthropic
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.config import get_settings
from app.models.user import User
from app.models.stock import Stock, MarketDataDaily
from app.models.fundamentals import FundamentalDataQuarterly
from app.models.trade import Position, OrderSide, OrderType
from app.models.decision import TradingDecision
from app.models.portfolio import PortfolioSnapshot
from app.services.sentiment import RedditScraper
from app.services.market_data import TechnicalIndicators
from app.services.trading import TradeExecutor, RiskManager

settings = get_settings()


class ClaudeTrader:
    """Uses Claude API to analyze market data and make trading decisions"""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        self.reddit_scraper = RedditScraper()
        self.trade_executor = TradeExecutor(db, user)

    def _get_portfolio_context(self) -> Dict:
        """Get current portfolio state"""
        snapshot = (
            self.db.query(PortfolioSnapshot)
            .filter(PortfolioSnapshot.user_id == self.user.id)
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .first()
        )

        positions = (
            self.db.query(Position, Stock)
            .join(Stock)
            .filter(Position.user_id == self.user.id, Position.is_open == True)
            .all()
        )

        position_data = [
            {
                "symbol": stock.symbol,
                "quantity": pos.quantity,
                "average_cost": pos.average_cost,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "stop_loss": pos.stop_loss_price,
            }
            for pos, stock in positions
        ]

        return {
            "total_value": snapshot.total_value if snapshot else 0,
            "cash_balance": snapshot.cash_balance if snapshot else 0,
            "positions_value": snapshot.positions_value if snapshot else 0,
            "daily_pnl": snapshot.daily_pnl if snapshot else 0,
            "daily_pnl_pct": snapshot.daily_pnl_pct if snapshot else 0,
            "num_positions": len(position_data),
            "positions": position_data,
        }

    def _get_market_data_context(self, symbol: str, days: int = 30) -> Optional[Dict]:
        """Get market data and technical indicators for a stock"""
        stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            return None

        # Get recent market data
        since_date = date.today() - timedelta(days=days)
        market_data = (
            self.db.query(MarketDataDaily)
            .filter(
                MarketDataDaily.stock_id == stock.id,
                MarketDataDaily.date >= since_date,
            )
            .order_by(MarketDataDaily.date)
            .all()
        )

        if not market_data:
            return None

        latest = market_data[-1]

        # Get technical signal
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "close": md.close,
                    "sma_20": md.sma_20,
                    "sma_50": md.sma_50,
                    "rsi_14": md.rsi_14,
                    "macd": md.macd,
                    "macd_signal": md.macd_signal,
                }
                for md in market_data
            ]
        )
        signal = TechnicalIndicators.get_signal(df)

        return {
            "symbol": symbol,
            "current_price": latest.close,
            "volume": latest.volume,
            "sma_20": latest.sma_20,
            "sma_50": latest.sma_50,
            "sma_200": latest.sma_200,
            "rsi_14": latest.rsi_14,
            "macd": latest.macd,
            "macd_signal": latest.macd_signal,
            "technical_signal": signal,
            "price_change_pct": (
                ((latest.close - market_data[0].close) / market_data[0].close) * 100
                if len(market_data) > 1
                else 0
            ),
        }

    def _get_sentiment_context(self, symbol: str, days: int = 7) -> Dict:
        """Get sentiment analysis for a stock"""
        return self.reddit_scraper.get_stock_sentiment_summary(self.db, symbol, days)

    def _get_fundamental_context(self, symbol: str) -> Optional[Dict]:
        """Get fundamental data for multibagger screening (Yartseva's metrics)

        Returns the latest quarterly fundamental data including:
        - FCF/Price (free cash flow yield) - STRONGEST PREDICTOR
        - Book-to-Market ratio - value factor
        - ROA - profitability
        - Reinvestment quality flags
        """
        stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            return None

        # Get latest fundamental data
        fundamentals = (
            self.db.query(FundamentalDataQuarterly)
            .filter(FundamentalDataQuarterly.stock_id == stock.id)
            .order_by(desc(FundamentalDataQuarterly.fiscal_date))
            .first()
        )

        if not fundamentals:
            return None

        # Calculate 52-week high/low for context
        one_year_ago = datetime.now() - timedelta(days=365)
        market_data = (
            self.db.query(MarketDataDaily)
            .filter(
                MarketDataDaily.stock_id == stock.id,
                MarketDataDaily.date >= one_year_ago.date()
            )
            .all()
        )

        high_52w = max(md.high for md in market_data) if market_data else None
        low_52w = min(md.low for md in market_data) if market_data else None
        current_price = market_data[-1].close if market_data else None

        distance_from_low = None
        if current_price and low_52w and low_52w > 0:
            distance_from_low = ((current_price - low_52w) / low_52w) * 100

        return {
            "fiscal_date": fundamentals.fiscal_date,
            # Market data
            "market_cap": fundamentals.market_cap,
            "market_cap_category": self._categorize_market_cap(fundamentals.market_cap),
            # Yartseva's key predictors
            "fcf_price_ratio": fundamentals.fcf_price_ratio,
            "book_to_market": fundamentals.book_to_market,
            "roa": fundamentals.roa,
            "roe": fundamentals.roe,
            # Profitability
            "ebitda_margin": fundamentals.ebitda_margin,
            "ebit_margin": fundamentals.ebit_margin,
            "is_profitable": fundamentals.is_profitable,
            # Growth metrics
            "asset_growth_rate": fundamentals.asset_growth_rate,
            "ebitda_growth_rate": fundamentals.ebitda_growth_rate,
            "revenue_growth_rate": fundamentals.revenue_growth_rate,
            # Quality flags
            "has_negative_equity": fundamentals.has_negative_equity,
            "reinvestment_quality_flag": fundamentals.reinvestment_quality_flag,
            # Technical context for entry timing
            "distance_from_52w_low": distance_from_low,
            "passes_yartseva_filters": self._check_yartseva_filters(fundamentals),
        }

    def _categorize_market_cap(self, market_cap: Optional[float]) -> str:
        """Categorize market cap size"""
        if not market_cap:
            return "Unknown"
        elif market_cap < 300_000_000:
            return "Micro Cap (<$300M)"
        elif market_cap < 2_000_000_000:
            return "Small Cap ($300M-$2B) ⭐ MULTIBAGGER RANGE"
        elif market_cap < 10_000_000_000:
            return "Mid Cap ($2B-$10B)"
        else:
            return "Large Cap (>$10B)"

    def _check_yartseva_filters(self, fundamentals: FundamentalDataQuarterly) -> Dict[str, bool]:
        """Check which Yartseva filters the stock passes

        Returns dict of filter names and pass/fail status
        """
        return {
            "high_fcf_yield": fundamentals.fcf_price_ratio and fundamentals.fcf_price_ratio >= 0.05,
            "value_stock": fundamentals.book_to_market and fundamentals.book_to_market >= 0.40,
            "profitable": fundamentals.is_profitable,
            "no_negative_equity": not fundamentals.has_negative_equity,
            "good_reinvestment": fundamentals.reinvestment_quality_flag if fundamentals.reinvestment_quality_flag is not None else False,
            "small_cap": fundamentals.market_cap and 300_000_000 <= fundamentals.market_cap <= 2_000_000_000,
        }

    def _build_analysis_prompt(self, symbol: str) -> str:
        """Build prompt for Claude with all relevant context"""
        portfolio = self._get_portfolio_context()
        market_data = self._get_market_data_context(symbol)
        sentiment = self._get_sentiment_context(symbol)
        fundamentals = self._get_fundamental_context(symbol)

        prompt = f"""You are an AI trading assistant using a HYBRID FUNDAMENTAL + TECHNICAL approach for multibagger stock discovery.

Your analysis is based on peer-reviewed research: "The Alchemy of Multibagger Stocks" (Yartseva, 2025) which analyzed 464 stocks that achieved 10x+ returns from 2009-2024.

KEY RESEARCH FINDINGS (Yartseva 2025):
1. FCF/Price (free cash flow yield) - STRONGEST PREDICTOR (regression coefficients 46-82)
2. Book-to-Market ratio > 0.40 + positive profitability
3. Small caps ($300M-$2B) outperform large caps (median starting cap $348M)
4. Reinvestment quality: Asset growth ≤ EBITDA growth (growth > EBITDA is NEGATIVE signal)
5. Entry timing: Stocks near 12-month lows with NEGATIVE 3-6 month momentum (mean reversion)
6. AVOID: Negative equity, high P/E without cash flow

NOTE: This is ANALYSIS-ONLY mode. You will provide recommendations but NOT execute trades. The trader will review and execute manually.

PORTFOLIO STATUS:
- Total Value: ${portfolio['total_value']:,.2f}
- Cash Available: ${portfolio['cash_balance']:,.2f}
- Current Positions: {portfolio['num_positions']}
- Daily P&L: ${portfolio['daily_pnl']:,.2f} ({portfolio['daily_pnl_pct']:.2f}%)

"""

        # Add fundamental data section if available
        if fundamentals:
            filters = fundamentals['passes_yartseva_filters']
            prompt += f"""
FUNDAMENTAL ANALYSIS for {symbol} (as of {fundamentals['fiscal_date']}):

MULTIBAGGER SCREENING (Yartseva Criteria):
  ✓ = Passes filter, ✗ = Fails filter

  FCF/Price (free cash flow yield): {fundamentals['fcf_price_ratio']:.2%} {'✓ ⭐ STRONGEST PREDICTOR' if filters['high_fcf_yield'] else '✗ Below 5% threshold'}
  Book/Market ratio:                {fundamentals['book_to_market']:.2f} {'✓ Value stock (>0.40)' if filters['value_stock'] else '✗ Not a value stock'}
  Market Cap:                        ${fundamentals['market_cap']:,.0f} ({fundamentals['market_cap_category']})
                                     {'✓ Small cap sweet spot' if filters['small_cap'] else '✗ Outside multibagger range'}
  Profitable:                        {'✓ Yes' if filters['profitable'] else '✗ No'}
  Negative Equity:                   {'✓ No (good)' if filters['no_negative_equity'] else '✗ Yes (RED FLAG - AVOID)'}

PROFITABILITY METRICS:
  ROA (Return on Assets):            {fundamentals['roa']:.2%} {'(Good)' if fundamentals['roa'] and fundamentals['roa'] > 0.05 else '(Low)'}
  ROE (Return on Equity):            {fundamentals['roe']:.2%}
  EBITDA Margin:                     {fundamentals['ebitda_margin']:.2%} {'(Good)' if fundamentals['ebitda_margin'] and fundamentals['ebitda_margin'] > 0.10 else '(Modest)'}

"""
            # Add growth metrics if available
            if fundamentals['asset_growth_rate'] is not None and fundamentals['ebitda_growth_rate'] is not None:
                prompt += f"""GROWTH QUALITY (YoY):
  Asset Growth:                      {fundamentals['asset_growth_rate']:.1%}
  EBITDA Growth:                     {fundamentals['ebitda_growth_rate']:.1%}
  Revenue Growth:                    {fundamentals['revenue_growth_rate']:.1%}
  Reinvestment Quality:              {'✓ Good (Asset ≤ EBITDA)' if filters['good_reinvestment'] else '⚠ Poor (Asset > EBITDA)'}

"""
        else:
            prompt += f"""
FUNDAMENTAL ANALYSIS for {symbol}:
  ⚠ No fundamental data available yet. Analysis will rely on technical + sentiment only.
  Recommend fetching fundamental data to enable multibagger screening.

"""

        if market_data:
            prompt += f"""TECHNICAL ANALYSIS for {symbol}:
- Current Price: ${market_data['current_price']:.2f}"""

            # Add entry timing context if we have fundamentals
            if fundamentals and fundamentals.get('distance_from_52w_low') is not None:
                prompt += f"""
- Distance from 52-week low: +{fundamentals['distance_from_52w_low']:.1f}% {'✓ Near lows (good entry)' if fundamentals['distance_from_52w_low'] < 20 else '⚠ Not near lows'}"""

            prompt += f"""
- Technical Signal: {market_data['technical_signal']}
- RSI(14): {market_data['rsi_14']:.2f if market_data['rsi_14'] else 'N/A'}
- Price above SMA(20): {'Yes' if market_data['sma_20'] and market_data['current_price'] > market_data['sma_20'] else 'No'}
- Price above SMA(50): {'Yes' if market_data['sma_50'] and market_data['current_price'] > market_data['sma_50'] else 'No'}
- MACD: {'Bullish' if market_data['macd'] and market_data['macd_signal'] and market_data['macd'] > market_data['macd_signal'] else 'Bearish'}
- 30-day Change: {market_data['price_change_pct']:.2f}%

"""

        prompt += f"""SENTIMENT ANALYSIS (Reddit - Last 7 days):
- Mentions: {sentiment['mention_count']}
- Posts: {sentiment.get('post_count', 0)}
- Average Sentiment: {sentiment['avg_sentiment']:.3f} (-1 to 1 scale)
- Bullish Ratio: {sentiment['bullish_ratio']:.1%}

TRADING PARAMETERS:
- Position Size: 15-25% of portfolio (aggressive)
- Required Stop Loss: 5%
- Min Risk/Reward: 2:1
- Max Open Positions: 10

DECISION FRAMEWORK (Hybrid Fundamental + Technical):

STEP 1 - FUNDAMENTAL SCREENING (Yartseva's multibagger criteria):
  - PRIORITY 1: High FCF/Price (≥5%) - This is the STRONGEST predictor
  - PRIORITY 2: Book/Market > 0.40 with profitability
  - PRIORITY 3: Small cap ($300M-$2B)
  - PRIORITY 4: Good reinvestment quality (Asset growth ≤ EBITDA growth)
  - RED FLAG: Negative equity (automatic disqualifier)

STEP 2 - ENTRY TIMING (Technical signals):
  - BEST: Stock near 52-week lows (Yartseva: buy near lows for mean reversion)
  - BEST: Negative 3-6 month momentum (contrary to typical trend following)
  - GOOD: RSI oversold (<30) or neutral (30-70)
  - GOOD: Positive sentiment shift
  - AVOID: Near 52-week highs with momentum exhaustion

STEP 3 - DECISION LOGIC:
  - STRONG BUY: Passes 4+ Yartseva filters + good entry timing
  - BUY: Passes 3+ filters + acceptable timing
  - HOLD: Passes 2-3 filters but poor timing OR existing position still valid
  - SELL/CLOSE: Fails key filters (negative equity, low FCF) OR stop loss triggered

Based on this analysis, provide a trading decision:
1. Should I BUY, SELL, HOLD, or CLOSE an existing position?
2. If buying, suggest:
   - Number of shares (respecting position size limits)
   - Entry price (limit order or market)
   - Stop loss price (5% default)
   - Take profit target (for 2:1 risk/reward, but multibaggers may take years)
3. Confidence level (0-1)
4. Detailed reasoning that addresses:
   - Which Yartseva filters this stock passes/fails
   - Whether fundamentals support multibagger potential
   - Whether current timing is good for entry
   - Key risks and catalysts

Format your response as JSON:
{{
    "decision": "buy|sell|hold|close_position",
    "symbol": "{symbol}",
    "confidence": 0.0-1.0,
    "technical_signal": "bullish|bearish|neutral",
    "sentiment_score": 0.0-1.0,
    "reasoning": "detailed explanation",
    "suggested_action": {{
        "quantity": 100,
        "entry_price": 50.00,
        "stop_loss_price": 47.50,
        "take_profit_price": 55.00,
        "order_type": "market|limit"
    }}
}}
"""

        return prompt

    def analyze_symbol(self, symbol: str) -> TradingDecision:
        """Analyze a symbol and make a trading decision

        Args:
            symbol: Stock symbol to analyze

        Returns:
            TradingDecision record
        """
        # Get or create stock
        stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            stock = Stock(symbol=symbol, name=symbol, exchange="TSX")
            self.db.add(stock)
            self.db.flush()

        # Build analysis prompt
        prompt = self._build_analysis_prompt(symbol)

        # Call Claude API
        try:
            message = self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Parse JSON response
            import json

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            analysis = json.loads(response_text)

            # Store suggested action as JSON for manual review
            suggested_action = analysis.get("suggested_action")
            suggested_action_json = json.dumps(suggested_action) if suggested_action else None

            # Create decision record
            decision = TradingDecision(
                user_id=self.user.id,
                stock_id=stock.id,
                decision=analysis["decision"],
                confidence=analysis.get("confidence"),
                technical_signal=analysis.get("technical_signal"),
                sentiment_score=analysis.get("sentiment_score"),
                reasoning=analysis["reasoning"],
                market_conditions=prompt,
                suggested_action=suggested_action_json,
            )
            self.db.add(decision)
            self.db.flush()

            # ANALYSIS-ONLY MODE: Never execute trades automatically
            # Store the suggestion for manual review
            decision.action_taken = False
            if analysis["decision"] in ["buy", "sell"]:
                decision.action_reason = (
                    f"Recommendation ready for manual review "
                    f"(confidence: {analysis.get('confidence', 0):.2f})"
                )
            else:
                decision.action_reason = f"Decision is {analysis['decision']} - no action needed"

            self.db.commit()
            return decision

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            # Create error decision
            decision = TradingDecision(
                user_id=self.user.id,
                stock_id=stock.id,
                decision="hold",
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                action_taken=False,
                action_reason=str(e),
            )
            self.db.add(decision)
            self.db.commit()
            return decision

    def analyze_portfolio(self) -> List[TradingDecision]:
        """Analyze all positions and potential opportunities

        Returns:
            List of trading decisions
        """
        decisions = []

        # Analyze existing positions
        positions = (
            self.db.query(Position, Stock)
            .join(Stock)
            .filter(Position.user_id == self.user.id, Position.is_open == True)
            .all()
        )

        for position, stock in positions:
            decision = self.analyze_symbol(stock.symbol)
            decisions.append(decision)

        return decisions
