# Changes for Analysis-Only Mode

This document summarizes the changes made to convert the system from automated trading to analysis-only mode for Questrade compliance.

## Reason for Changes

Questrade's API Terms of Service explicitly prohibit:
- Automated order execution via third-party apps
- Pre-scheduled trading without explicit permission

To comply, the system now provides **analysis and recommendations only**. You must manually review and execute each trade.

## Code Changes

### 1. ClaudeTrader Service (`backend/app/services/chat/claude_trader.py`)

**Before**: Automatically executed trades when confidence ≥ 70%
```python
# Old code (removed)
if analysis["decision"] in ["buy", "sell"] and confidence >= 0.7:
    order = self.trade_executor.place_order(...)
    decision.action_taken = True
```

**After**: Only logs recommendations for manual review
```python
# New code
# ANALYSIS-ONLY MODE: Never execute trades automatically
decision.action_taken = False
decision.action_reason = f"Recommendation ready for manual review (confidence: {confidence})"
```

**Added**: Stores suggested action as JSON
```python
suggested_action_json = json.dumps(analysis.get("suggested_action"))
decision.suggested_action = suggested_action_json
```

### 2. TradingDecision Model (`backend/app/models/decision.py`)

**Added**: New column to store suggested trade details
```python
suggested_action = Column(Text, nullable=True)  # JSON string with trade details
```

This stores Claude's recommended:
- Quantity
- Entry price
- Stop loss price
- Take profit price
- Order type (market/limit)

### 3. New Recommendations API (`backend/app/api/v1/recommendations.py`)

**Created**: New endpoint for viewing recommendations

Endpoints:
- `GET /api/v1/recommendations/latest` - Get latest recommendations
- `GET /api/v1/recommendations/actionable` - High-confidence buy/sell only
- `GET /api/v1/recommendations/{id}` - Detailed view
- `POST /api/v1/recommendations/{id}/dismiss` - Mark as reviewed

### 4. Analysis Prompt Updated

**Added** to Claude prompt:
```
NOTE: This is ANALYSIS-ONLY mode. You will provide recommendations but NOT execute trades.
The trader will review and execute manually.
```

### 5. Configuration Updates

**.env.example**:
```env
# IMPORTANT: System is in ANALYSIS-ONLY mode (Questrade compliant)
# Claude provides recommendations but does NOT execute trades automatically
# You must manually review and execute each trade
ANALYSIS_ONLY_MODE=True
```

## Database Migration Needed

You'll need to add the new column to the `trading_decisions` table:

```sql
ALTER TABLE trading_decisions
ADD COLUMN suggested_action TEXT;
```

Or create a new Alembic migration:
```bash
docker-compose exec backend alembic revision --autogenerate -m "add suggested_action to trading_decisions"
docker-compose exec backend alembic upgrade head
```

## What Still Works

✅ **Automated data collection**:
- Market data updates (Alpha Vantage)
- Sentiment scraping (Reddit)
- Technical indicator calculations

✅ **Scheduled analysis**:
- 9:30 AM EST: Morning analysis
- 4:00 PM EST: Closing analysis
- Every 30 min: Sentiment updates
- Every hour: Market data updates

✅ **Claude AI analysis**:
- Portfolio evaluation
- Technical analysis
- Sentiment scoring
- Risk calculations
- Detailed reasoning

✅ **Questrade integration**:
- OAuth authentication
- Account monitoring
- Position tracking
- Balance updates

## What Changed

❌ **Automatic trade execution**: Removed completely

✅ **Manual review workflow**: You now:
1. Receive recommendations via API or database
2. Review Claude's analysis and reasoning
3. Decide whether to execute
4. Place orders manually in Questrade

## How to Use

### View Recommendations via API

```bash
# Get latest recommendations
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/recommendations/latest

# Get actionable (high-confidence buy/sell)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/recommendations/actionable
```

### View Recommendations via Database

```python
from app.database import get_db_context
from app.models import TradingDecision, Stock
import json

with get_db_context() as db:
    decisions = db.query(TradingDecision, Stock).join(Stock).filter(
        TradingDecision.action_taken == False,
        TradingDecision.confidence >= 0.7
    ).all()

    for decision, stock in decisions:
        print(f"Symbol: {stock.symbol}")
        print(f"Decision: {decision.decision}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reasoning: {decision.reasoning}")

        if decision.suggested_action:
            action = json.loads(decision.suggested_action)
            print(f"Suggested: {action}")
```

### Execute Trade Manually

1. Review the recommendation
2. Log into Questrade (web or app)
3. Place the order with suggested parameters (or adjust)
4. Optionally mark as reviewed:
   ```bash
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/v1/recommendations/{id}/dismiss
   ```

## Benefits

✅ **Compliant**: Follows Questrade API terms exactly
✅ **Safe**: You control all trades
✅ **Transparent**: See all reasoning
✅ **Educational**: Learn from Claude's analysis
✅ **Flexible**: Accept, modify, or reject suggestions

## Documentation Updated

- `README.md`: Updated title, features, workflow
- `QUICKSTART.md`: Updated testing and workflow
- `ANALYSIS_ONLY_MODE.md`: New comprehensive guide
- `.env.example`: Added compliance notice

## Testing After Changes

1. **Run migration** (if needed):
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

2. **Test analysis**:
   ```bash
   docker-compose exec backend python -c "
   from app.database import get_db_context
   from app.models import User
   from app.services.chat import ClaudeTrader

   with get_db_context() as db:
       user = db.query(User).first()
       trader = ClaudeTrader(db, user)
       decision = trader.analyze_symbol('TD.TO')
       print(f'Decision: {decision.decision}')
       print(f'Action taken: {decision.action_taken}')  # Should be False
   "
   ```

3. **Verify no auto-execution**: Check that `action_taken` is always False

4. **Test API**:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/v1/recommendations/latest
   ```

## Summary

The system is now **Questrade-compliant** and operates in analysis-only mode. Claude provides intelligent trading recommendations with full context and reasoning, but you maintain complete control over execution. This gives you AI-powered insights while respecting broker terms and keeping you in the decision-making loop.
