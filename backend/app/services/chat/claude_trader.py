import anthropic
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.config import get_settings
from app.models.user import User
from app.models.stock import Stock, MarketDataDaily
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

    def _build_analysis_prompt(self, symbol: str) -> str:
        """Build prompt for Claude with all relevant context"""
        portfolio = self._get_portfolio_context()
        market_data = self._get_market_data_context(symbol)
        sentiment = self._get_sentiment_context(symbol)

        prompt = f"""You are an AI trading assistant for an aggressive TSX stock trader. Analyze the following data and provide a trading recommendation.

NOTE: This is ANALYSIS-ONLY mode. You will provide recommendations but NOT execute trades. The trader will review and execute manually.

PORTFOLIO STATUS:
- Total Value: ${portfolio['total_value']:,.2f}
- Cash Available: ${portfolio['cash_balance']:,.2f}
- Current Positions: {portfolio['num_positions']}
- Daily P&L: ${portfolio['daily_pnl']:,.2f} ({portfolio['daily_pnl_pct']:.2f}%)

"""

        if market_data:
            prompt += f"""MARKET DATA for {symbol}:
- Current Price: ${market_data['current_price']:.2f}
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

Based on this analysis, provide a trading decision:
1. Should I BUY, SELL, HOLD, or CLOSE an existing position?
2. If buying, suggest:
   - Number of shares (respecting position size limits)
   - Entry price (limit order or market)
   - Stop loss price (5% default)
   - Take profit target (for 2:1 risk/reward)
3. Confidence level (0-1)
4. Detailed reasoning

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
