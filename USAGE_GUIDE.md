# TSX Trader - Complete Usage Guide

> 🤖 **AUTOMATED MODE AVAILABLE**: This guide shows manual commands, but everything can run automatically via GitHub Actions. See [AUTOMATION_SETUP.md](AUTOMATION_SETUP.md) for zero-touch operation.

## Quick Start (First Time Setup)

### 1. Initialize Stocks
```bash
cd /Users/bryan/claude-code/tsx-trader/backend

# Add 39 starter stocks to database
python3 scripts/init-db.py
```

### 2. Fetch Fundamental Data (Test with One Stock)
```bash
# Test with TD Bank (~1 minute)
python3 scripts/test-fundamentals.py TD.TO
```

**What this does**:
- Fetches quarterly financials from Alpha Vantage
- Calculates FCF/Price, Book/Market, ROA, etc.
- Shows which Yartseva filters it passes
- Stores data in database

### 3. Run Multibagger Screening
```bash
# Screen all stocks with fundamental data
python3 scripts/screen-multibaggers.py 20
```

**What you'll see**:
```
SCREENING RESULTS (Top 20):

Found 5 potential multibagger candidates

1. WELL.TO - WELL Health Technologies
   Sector: Technology
   MULTIBAGGER SCORE: 78.5/100

   KEY METRICS (Yartseva's predictors):
     FCF/Price:       12.5% ✓ ⭐ STRONGEST
     Book/Market:     0.85 ✓
     ROA:             8.2%
     EBITDA Margin:   15.3%

   SIZE & PROFITABILITY:
     Market Cap:      $850,000,000
     Profitable:      ✓ Yes

   GROWTH QUALITY:
     Asset Growth:    15.2%
     EBITDA Growth:   18.5%
     Reinvestment:    ✓ Good

   TECHNICAL TIMING:
     Current Price:   $4.25
     vs 52w Low:      +8.3% ✓ Near lows (good entry)
     6m Momentum:     -12.5% ✓ Negative (good)
```

### 4. Get Claude's Analysis for a Specific Stock
```bash
# Analyze a specific stock using Claude
python3 -c "
from app.database import get_db_context
from app.models.user import User
from app.services.chat import ClaudeTrader

with get_db_context() as db:
    user = db.query(User).first()
    if not user:
        print('ERROR: No user found. Create a user first.')
    else:
        trader = ClaudeTrader(db, user)
        decision = trader.analyze_symbol('WELL.TO')

        print(f'\n=== CLAUDE ANALYSIS FOR WELL.TO ===\n')
        print(f'Decision: {decision.decision.upper()}')
        print(f'Confidence: {decision.confidence:.0%}')
        print(f'\nReasoning:')
        print(decision.reasoning)

        if decision.suggested_action:
            import json
            action = json.loads(decision.suggested_action)
            print(f'\nSUGGESTED ACTION:')
            print(f'  Quantity: {action.get(\"quantity\")} shares')
            print(f'  Entry: \${action.get(\"entry_price\"):.2f}')
            print(f'  Stop Loss: \${action.get(\"stop_loss_price\"):.2f}')
            print(f'  Take Profit: \${action.get(\"take_profit_price\"):.2f}')
"
```

---

## Daily Workflow

### Morning Routine (9:30 AM - Market Open)

#### 1. Check Latest Recommendations
```bash
# View latest trading decisions from Claude
python3 -c "
from app.database import get_db_context
from app.models.decision import TradingDecision
from app.models.stock import Stock
from sqlalchemy import desc

with get_db_context() as db:
    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock)
        .filter(TradingDecision.action_taken == False)
        .order_by(desc(TradingDecision.created_at))
        .limit(10)
        .all()
    )

    print('=== LATEST RECOMMENDATIONS ===\n')
    for decision, stock in decisions:
        print(f'{stock.symbol}: {decision.decision.upper()} (confidence: {decision.confidence:.0%})')
        print(f'  {decision.reasoning[:200]}...\n')
"
```

#### 2. Run Fresh Analysis (Optional)
```bash
# Analyze all positions + watch list
python3 -c "
from app.database import get_db_context
from app.models.user import User
from app.services.chat import ClaudeTrader

with get_db_context() as db:
    user = db.query(User).first()
    trader = ClaudeTrader(db, user)

    # Analyze your watch list
    watch_list = ['WELL.TO', 'DCBO.TO', 'PXT.TO']

    for symbol in watch_list:
        print(f'\n=== Analyzing {symbol} ===')
        decision = trader.analyze_symbol(symbol)
        print(f'Decision: {decision.decision.upper()} ({decision.confidence:.0%})')
"
```

---

## Weekly Tasks

### Update Fundamental Data (Runs Automatically on Saturdays)

Or run manually:

```bash
# Update fundamental data for all active stocks
# WARNING: This is SLOW (~1 min per stock due to API rate limits)
# For 39 stocks = ~40 minutes

python3 -c "
from app.database import get_db_context
from app.tasks.market_data_tasks import update_fundamental_data

print('Starting fundamental data update...')
print('This will take ~40 minutes for 39 stocks')

result = update_fundamental_data()
print(f'\nResults: {result}')
"
```

**Better approach**: Let it run automatically on Saturdays at 2 AM via Celery.

---

## Monthly Tasks

### Discover New Stocks (Runs Automatically on 1st of Month)

Or run manually:

```bash
# Discover new TSX small caps
python3 scripts/discover-stocks.py discover 20

# Or full refresh (review + discover)
python3 scripts/discover-stocks.py refresh
```

**What this does**:
- Checks 60+ potential TSX candidates
- Adds stocks in $300M-$2B range
- Deactivates stocks outside range
- Takes ~10-20 minutes

---

## Common Use Cases

### Use Case 1: "What Should I Buy Today?"

```bash
# Step 1: Run multibagger screening
python3 scripts/screen-multibaggers.py 10

# Step 2: Pick a high-scoring stock from the results
# Step 3: Get Claude's detailed analysis
python3 -c "
from app.database import get_db_context
from app.models.user import User
from app.services.chat import ClaudeTrader

with get_db_context() as db:
    user = db.query(User).first()
    trader = ClaudeTrader(db, user)

    # Analyze the top candidate
    decision = trader.analyze_symbol('WELL.TO')

    print(f'\nDecision: {decision.decision}')
    print(f'Confidence: {decision.confidence:.0%}')
    print(f'\n{decision.reasoning}')

    import json
    if decision.suggested_action:
        action = json.loads(decision.suggested_action)
        print(f'\nSUGGESTED TRADE:')
        print(f'  Buy {action[\"quantity\"]} shares at ${action[\"entry_price\"]}')
        print(f'  Stop loss: ${action[\"stop_loss_price\"]}')
        print(f'  Take profit: ${action[\"take_profit_price\"]}')
"
```

### Use Case 2: "Check My Current Positions"

```bash
python3 -c "
from app.database import get_db_context
from app.models.user import User
from app.services.chat import ClaudeTrader

with get_db_context() as db:
    user = db.query(User).first()
    trader = ClaudeTrader(db, user)

    # Analyze existing portfolio
    decisions = trader.analyze_portfolio()

    print(f'\n=== PORTFOLIO ANALYSIS ===')
    print(f'Analyzed {len(decisions)} positions\n')

    for decision in decisions:
        print(f'{decision.stock.symbol}: {decision.decision} ({decision.confidence:.0%})')
"
```

### Use Case 3: "Find New Multibagger Candidates"

```bash
# Step 1: Discover new stocks (monthly)
python3 scripts/discover-stocks.py discover 20

# Step 2: Fetch fundamentals for new stocks (slow!)
# This runs automatically via Celery on weekends

# Step 3: Run screening
python3 scripts/screen-multibaggers.py 20

# Step 4: Review top candidates with Claude
```

### Use Case 4: "Check Which Stocks Pass Yartseva Filters"

```bash
python3 -c "
from app.database import get_db_context
from app.services.screening import MultibaggerScreener

with get_db_context() as db:
    screener = MultibaggerScreener(
        min_fcf_price_ratio=0.05,
        min_book_to_market=0.40,
        min_market_cap=300_000_000,
        max_market_cap=2_000_000_000,
    )

    # Get statistics
    stats = screener.get_screening_stats(db)

    print('=== SCREENING STATISTICS ===')
    print(f'Total stocks with fundamentals: {stats[\"total_stocks_with_fundamentals\"]}')
    print(f'Passing FCF/Price filter (≥5%):  {stats[\"passing_fcf_filter\"]}')
    print(f'Passing B/M filter (≥0.40):      {stats[\"passing_bm_filter\"]}')
    print(f'Passing size filter ($300M-$2B): {stats[\"passing_size_filter\"]}')
    print(f'Passing ALL filters:             {stats[\"passing_all_filters\"]}')

    if stats['passing_all_filters'] > 0:
        print(f'\nAverage metrics (passing stocks):')
        print(f'  FCF/Price:    {stats[\"avg_fcf_price_ratio\"]:.2%}')
        print(f'  Book/Market:  {stats[\"avg_book_to_market\"]:.2f}')
        print(f'  ROA:          {stats[\"avg_roa\"]:.2%}')
"
```

---

## Database Queries (Advanced)

### View All Stocks
```bash
python3 -c "
from app.database import get_db_context
from app.models.stock import Stock

with get_db_context() as db:
    stocks = db.query(Stock).filter(Stock.is_active == True).all()

    print(f'Active stocks: {len(stocks)}\n')
    for stock in stocks:
        print(f'{stock.symbol:<15} {stock.name:<40} {stock.sector}')
"
```

### View Latest Trading Decisions
```bash
python3 -c "
from app.database import get_db_context
from app.models.decision import TradingDecision
from app.models.stock import Stock
from sqlalchemy import desc
import json

with get_db_context() as db:
    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock)
        .order_by(desc(TradingDecision.created_at))
        .limit(5)
        .all()
    )

    for decision, stock in decisions:
        print(f'\n{\"=\"*60}')
        print(f'{stock.symbol} - {decision.decision.upper()}')
        print(f'Confidence: {decision.confidence:.0%}')
        print(f'Created: {decision.created_at}')
        print(f'\nReasoning: {decision.reasoning[:300]}...')

        if decision.suggested_action:
            action = json.loads(decision.suggested_action)
            print(f'\nSuggested: {action}')
"
```

### View Stocks with Best Fundamentals
```bash
python3 -c "
from app.database import get_db_context
from app.models.stock import Stock
from app.models.fundamentals import FundamentalDataQuarterly
from sqlalchemy import desc, func

with get_db_context() as db:
    # Get latest fundamental data for each stock
    subquery = (
        db.query(
            FundamentalDataQuarterly.stock_id,
            func.max(FundamentalDataQuarterly.fiscal_date).label('max_date')
        )
        .group_by(FundamentalDataQuarterly.stock_id)
        .subquery()
    )

    results = (
        db.query(Stock, FundamentalDataQuarterly)
        .join(Stock.fundamental_data)
        .join(
            subquery,
            (FundamentalDataQuarterly.stock_id == subquery.c.stock_id) &
            (FundamentalDataQuarterly.fiscal_date == subquery.c.max_date)
        )
        .filter(
            FundamentalDataQuarterly.fcf_price_ratio.isnot(None),
            FundamentalDataQuarterly.fcf_price_ratio >= 0.05
        )
        .order_by(desc(FundamentalDataQuarterly.fcf_price_ratio))
        .limit(10)
        .all()
    )

    print('=== TOP 10 STOCKS BY FCF/PRICE ===\n')
    for stock, fund in results:
        print(f'{stock.symbol:<15} FCF/P: {fund.fcf_price_ratio:.2%}  B/M: {fund.book_to_market:.2f}  ROA: {fund.roa:.2%}')
"
```

---

## Troubleshooting

### "No user found"
You need to create a user first via the API or database:

```bash
python3 -c "
from app.database import SessionLocal
from app.models.user import User, UserSettings
from passlib.context import CryptContext

db = SessionLocal()
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

user = User(
    email='trader@example.com',
    hashed_password=pwd_context.hash('password123'),
    is_active=True
)
db.add(user)
db.flush()

settings = UserSettings(
    user_id=user.id,
    auto_trading_enabled=True,
    position_size_pct=0.20,
    stop_loss_pct=0.05
)
db.add(settings)
db.commit()

print(f'✓ Created user: {user.email}')
db.close()
"
```

### "No fundamental data"
Run the test script to fetch data:
```bash
python3 scripts/test-fundamentals.py TD.TO
```

### "Screening returns no results"
Lower the thresholds:
```python
screener = MultibaggerScreener(
    min_fcf_price_ratio=0.03,  # Lower from 0.05
    min_book_to_market=0.30,   # Lower from 0.40
)
```

---

## Automation Setup

To run tasks automatically via Celery (Docker):

```bash
# Make sure .env has the connection string
echo 'DATABASE_URL=postgresql://neondb_owner:npg_9UQMpzZf7Pmy@ep-rapid-star-ahch70oz-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require' >> .env

# Start Celery workers
docker-compose up -d celery_worker celery_beat
```

**Automated tasks**:
- **Weekly (Saturdays 2 AM)**: Update fundamental data
- **Monthly (1st at 3 AM)**: Review existing stocks
- **Monthly (1st at 4 AM)**: Discover new stocks

---

## Summary

**For daily trading**:
1. Run screening: `python3 scripts/screen-multibaggers.py 20`
2. Pick a candidate from top results
3. Get Claude analysis with the code snippet above
4. Review reasoning and suggested action
5. Execute trade manually in your broker

**For maintenance**:
- Let Celery handle weekly/monthly updates
- Or run scripts manually when needed

**For discovery**:
- Monthly: `python3 scripts/discover-stocks.py refresh`
- Adds new small caps, removes stocks outside range
