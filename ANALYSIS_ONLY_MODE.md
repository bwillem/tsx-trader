# Analysis-Only Mode (Questrade Compliant)

## Important: Questrade API Terms

This system operates in **ANALYSIS-ONLY** mode to comply with Questrade's API Terms of Service:

> "I acknowledge that I am not permitted to send orders using an API app developed by a third party except where allowed by Questrade, Inc. I acknowledge and agree that I will not send orders on a pre-determined or automated basis using a partner application, except where allowed by Questrade, Inc."

## How It Works

### What Claude Does Automatically ✅

1. **Data Collection**:
   - Fetches market data from Alpha Vantage
   - Calculates technical indicators (RSI, MACD, SMA, etc.)
   - Scrapes Reddit sentiment from r/CanadianInvestor & r/Baystreetbets
   - Scores sentiment using VADER

2. **Portfolio Analysis**:
   - Monitors your positions from Questrade
   - Tracks P&L and performance
   - Calculates risk metrics

3. **Trading Recommendations**:
   - Claude analyzes all data (technical + sentiment + portfolio)
   - Generates buy/sell/hold recommendations
   - Provides detailed reasoning
   - Suggests entry/exit prices, stop-losses, position sizes
   - Logs everything to database for review

### What Claude DOES NOT Do ❌

- **Does NOT execute trades automatically**
- **Does NOT place orders without your approval**
- **Does NOT send any orders to Questrade**

## Your Workflow

### 1. View Recommendations

```bash
# Get latest recommendations via API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/recommendations/latest

# Get high-confidence actionable recommendations
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/recommendations/actionable
```

Or query the database directly:

```sql
-- View recent recommendations
SELECT
    s.symbol,
    td.decision,
    td.confidence,
    td.reasoning,
    td.suggested_action,
    td.created_at
FROM trading_decisions td
JOIN stocks s ON td.stock_id = s.id
ORDER BY td.created_at DESC
LIMIT 10;
```

### 2. Review Claude's Analysis

Each recommendation includes:
- **Symbol**: What stock
- **Decision**: buy, sell, hold, or close_position
- **Confidence**: 0-1 score (0.7+ is high confidence)
- **Technical Signal**: bullish, bearish, or neutral
- **Sentiment Score**: Reddit sentiment (-1 to 1)
- **Reasoning**: Claude's detailed explanation
- **Suggested Action**:
  ```json
  {
    "quantity": 100,
    "entry_price": 82.50,
    "stop_loss_price": 78.38,
    "take_profit_price": 90.74,
    "order_type": "limit"
  }
  ```

### 3. Execute Manually

If you agree with the recommendation:

1. **Log into Questrade** (web or app)
2. **Place the order manually**:
   - Use suggested quantity, prices, and order type
   - Or adjust based on your judgment
3. **Optional**: Mark the recommendation as reviewed:
   ```bash
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/v1/recommendations/{id}/dismiss
   ```

## API Endpoints

### Get Latest Recommendations
```
GET /api/v1/recommendations/latest?limit=20
```

### Get Actionable Recommendations
```
GET /api/v1/recommendations/actionable?min_confidence=0.7
```
Returns only high-confidence buy/sell recommendations from last 24 hours.

### Get Recommendation Details
```
GET /api/v1/recommendations/{decision_id}
```
Full details including market conditions snapshot.

### Dismiss Recommendation
```
POST /api/v1/recommendations/{decision_id}/dismiss
```
Mark as reviewed so it doesn't show in actionable list.

## Scheduled Analysis

Celery tasks still run on schedule:

- **9:30 AM EST**: Morning analysis (market open)
- **4:00 PM EST**: Closing analysis (market close)
- **Every 30 min**: Sentiment update
- **Every hour**: Market data update

Results are logged to `trading_decisions` table for your review.

## Example: Checking Recommendations

### Via Python
```python
from app.database import get_db_context
from app.models import TradingDecision, Stock, User
from sqlalchemy import desc
import json

with get_db_context() as db:
    user = db.query(User).filter(User.email == "your@email.com").first()

    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock)
        .filter(
            TradingDecision.user_id == user.id,
            TradingDecision.action_taken == False,
            TradingDecision.confidence >= 0.7
        )
        .order_by(desc(TradingDecision.created_at))
        .limit(5)
        .all()
    )

    for decision, stock in decisions:
        print(f"\n{'='*60}")
        print(f"Symbol: {stock.symbol}")
        print(f"Decision: {decision.decision.upper()}")
        print(f"Confidence: {decision.confidence:.1%}")
        print(f"Reasoning: {decision.reasoning}")

        if decision.suggested_action:
            action = json.loads(decision.suggested_action)
            print(f"\nSuggested Action:")
            print(f"  Quantity: {action.get('quantity')} shares")
            print(f"  Entry: ${action.get('entry_price'):.2f}")
            print(f"  Stop Loss: ${action.get('stop_loss_price'):.2f}")
            print(f"  Take Profit: ${action.get('take_profit_price'):.2f}")
```

### Via SQL
```sql
-- Today's high-confidence recommendations
SELECT
    s.symbol,
    td.decision,
    ROUND(td.confidence::numeric, 2) as confidence,
    td.technical_signal,
    ROUND(td.sentiment_score::numeric, 2) as sentiment,
    td.reasoning,
    td.suggested_action,
    td.created_at
FROM trading_decisions td
JOIN stocks s ON td.stock_id = s.id
WHERE td.created_at > CURRENT_DATE
    AND td.confidence >= 0.7
    AND td.decision IN ('buy', 'sell')
    AND td.action_taken = false
ORDER BY td.confidence DESC;
```

## Benefits of Analysis-Only Mode

✅ **Compliant**: Follows Questrade's terms exactly
✅ **Safe**: You maintain full control over trades
✅ **Transparent**: See all analysis and reasoning
✅ **Educational**: Learn from Claude's analysis
✅ **Flexible**: Accept, reject, or modify suggestions
✅ **Auditable**: Full history in database

## Risk Management Still Applies

Even though trades aren't executed automatically, Claude's recommendations **respect your risk parameters**:

- Position size limits (15-25% of portfolio)
- Stop-loss requirements (5% default)
- Risk/reward ratios (2:1 minimum)
- Cash reserves (10% minimum)
- Max positions (10 concurrent)

The `suggested_action` in each recommendation is already validated against these rules.

## Next Steps

1. **Set up the system** (see QUICKSTART.md)
2. **Connect Questrade** for portfolio monitoring
3. **Let Claude analyze** the market on schedule
4. **Review recommendations** daily
5. **Execute trades manually** in Questrade
6. **Track performance** via the dashboard

## Questions?

- View all recommendations: Check `trading_decisions` table
- See what Claude analyzed: Check `market_conditions` field
- Understand reasoning: Check `reasoning` field
- Get trade details: Parse `suggested_action` JSON

The system gives you AI-powered analysis while keeping you in control of execution.
