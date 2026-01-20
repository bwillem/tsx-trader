# GitHub Actions Deployment Guide

This guide explains how to deploy the TSX Trading Analysis system using GitHub Actions with cloud databases. This approach is **free** and doesn't require your laptop to be running.

## Architecture

- **Database**: Neon (serverless Postgres) - Free tier
- **Cache**: Upstash Redis (serverless Redis) - Free tier
- **Scheduled Tasks**: GitHub Actions - Free for public repos, 2000 minutes/month for private
- **API Access**: Run locally when needed to view recommendations

**Total Cost**: $0/month

## Prerequisites

You already have these set up:
- ✅ Neon database (PostgreSQL)
- ✅ Upstash Redis
- ✅ Claude API key
- ✅ GitHub repository with secrets configured

### Required GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions

Make sure you have:
- `DATABASE_URL` - Your Neon connection string
- `REDIS_URL` - Your Upstash Redis URL
- `CLAUDE_API_KEY` - Your Claude API key
- `SECRET_KEY` - Any random string (used for JWT signing)
- `ALPHA_VANTAGE_API_KEY` - Your Alpha Vantage API key
- `REDDIT_CLIENT_ID` - Reddit app client ID
- `REDDIT_CLIENT_SECRET` - Reddit app client secret

## Initial Setup

### 1. Push Code to GitHub

```bash
cd tsx-trader

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - TSX Trading Analysis System"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/tsx-trader.git

# Push
git push -u origin main
```

### 2. Run Database Migration

Go to your GitHub repo → Actions → "Database Setup" → Run workflow

Select action: **full-setup**

This will:
1. Create all database tables (users, stocks, trading_decisions, etc.)
2. Initialize sample TSX stocks (TD.TO, RY.TO, SHOP.TO, etc.)

**Or run manually** (if you have Neon CLI):
```bash
# Update .env with your cloud DATABASE_URL
cd tsx-trader/backend

# Install dependencies locally
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Initialize stocks
python scripts/init-db.py
```

### 3. Verify Setup

Check the Actions tab to see if the workflow succeeded:
- Green checkmark = Success
- Red X = Failed (check logs)

## Scheduled Tasks

Once set up, these tasks run automatically:

### Market Data Update
- **Schedule**: Every hour
- **What it does**: Fetches OHLCV data from Alpha Vantage, calculates technical indicators
- **Rate limit**: 5 calls/minute (Alpha Vantage free tier)

### Sentiment Analysis
- **Schedule**: Every 30 minutes during trading hours (9 AM - 5 PM EST)
- **What it does**: Scrapes r/CanadianInvestor and r/Baystreetbets for stock mentions and sentiment

### Trading Analysis (Morning)
- **Schedule**: 9:30 AM EST weekdays (market open)
- **What it does**: Claude analyzes all positions and market data, creates recommendations

### Trading Analysis (Afternoon)
- **Schedule**: 4:00 PM EST weekdays (market close)
- **What it does**: Claude does closing analysis, creates recommendations

## Viewing Recommendations

### Option 1: Run API Locally

```bash
cd tsx-trader

# Create .env with your cloud database URLs
cat > .env << EOF
DATABASE_URL=your-neon-url
REDIS_URL=your-upstash-url
SECRET_KEY=your-secret-key
CLAUDE_API_KEY=your-claude-key
ALPHA_VANTAGE_API_KEY=your-av-key
REDDIT_CLIENT_ID=your-reddit-id
REDDIT_CLIENT_SECRET=your-reddit-secret
REDDIT_USER_AGENT=TSXTrader/1.0
EOF

# Start just the backend API
docker-compose up backend

# Or without Docker:
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then access:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Recommendations: http://localhost:8000/api/v1/recommendations/latest

### Option 2: Query Database Directly

Using Neon SQL Editor or any Postgres client:

```sql
-- View latest recommendations
SELECT
    s.symbol,
    td.decision,
    td.confidence,
    td.reasoning,
    td.suggested_action,
    td.created_at
FROM trading_decisions td
JOIN stocks s ON td.stock_id = s.id
WHERE td.action_taken = false
  AND td.created_at > NOW() - INTERVAL '24 hours'
ORDER BY td.confidence DESC
LIMIT 10;

-- View actionable recommendations (high confidence buy/sell)
SELECT
    s.symbol,
    td.decision,
    ROUND(td.confidence::numeric, 2) as confidence,
    td.suggested_action,
    td.reasoning
FROM trading_decisions td
JOIN stocks s ON td.stock_id = s.id
WHERE td.decision IN ('buy', 'sell')
  AND td.confidence >= 0.7
  AND td.action_taken = false
  AND td.created_at > NOW() - INTERVAL '24 hours'
ORDER BY td.confidence DESC;
```

### Option 3: Python Script

Create a simple script to check recommendations:

```python
# check_recommendations.py
import os
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import json

DATABASE_URL = os.getenv('DATABASE_URL')  # From your Neon dashboard

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Import models (you'll need the models accessible)
# Or use raw SQL:
result = session.execute("""
    SELECT
        s.symbol,
        td.decision,
        td.confidence,
        td.reasoning,
        td.suggested_action,
        td.created_at
    FROM trading_decisions td
    JOIN stocks s ON td.stock_id = s.id
    WHERE td.action_taken = false
      AND td.created_at > NOW() - INTERVAL '24 hours'
    ORDER BY td.confidence DESC
    LIMIT 5
""")

for row in result:
    print(f"\n{'='*60}")
    print(f"Symbol: {row.symbol}")
    print(f"Decision: {row.decision.upper()}")
    print(f"Confidence: {row.confidence:.1%}")
    print(f"Reasoning: {row.reasoning[:200]}...")

    if row.suggested_action:
        action = json.loads(row.suggested_action)
        print(f"\nSuggested:")
        print(f"  Quantity: {action.get('quantity')} shares")
        print(f"  Entry: ${action.get('entry_price'):.2f}")
        print(f"  Stop Loss: ${action.get('stop_loss_price'):.2f}")

session.close()
```

## Manual Triggers

You can manually trigger workflows:

### Run Analysis Now
1. Go to Actions → "Scheduled Trading Analysis"
2. Click "Run workflow"
3. Select task:
   - `all` - Run everything
   - `market-data` - Update market data only
   - `sentiment` - Update sentiment only
   - `trading-analysis` - Run Claude analysis

### Database Operations
1. Go to Actions → "Database Setup"
2. Click "Run workflow"
3. Select action:
   - `migrate` - Run database migrations
   - `init-stocks` - Initialize stock symbols
   - `full-setup` - Do both

## Monitoring

### View Workflow Runs

GitHub Actions tab shows all runs:
- ✅ Success - Task completed
- ❌ Failure - Click to see logs
- 🟡 In Progress - Currently running

### View Logs

Click on any workflow run to see:
- Which task ran
- Output/errors
- Execution time

### Check Database

Connect to your Neon database to verify:
```sql
-- Check recent trading decisions
SELECT COUNT(*) as decisions_today
FROM trading_decisions
WHERE created_at > CURRENT_DATE;

-- Check market data freshness
SELECT symbol, MAX(date) as latest_data
FROM market_data_daily
GROUP BY symbol
ORDER BY symbol;

-- Check sentiment data
SELECT COUNT(*) as posts_today
FROM sentiment_posts
WHERE created_at > CURRENT_DATE;
```

## Troubleshooting

### Workflow Fails

1. **Check logs** in Actions tab
2. **Common issues**:
   - Database connection failed → Check DATABASE_URL secret
   - Import error → Missing dependency in requirements.txt
   - Rate limit → Alpha Vantage free tier limit (5 calls/min)

### No Recommendations Generated

1. **Check if analysis ran**: Go to Actions → Recent runs
2. **Check for users**: You need at least one user account
   ```sql
   SELECT * FROM users;
   ```
3. **Enable auto-trading** in user settings (even though it won't execute, it enables analysis)
4. **Check logs** in workflow run

### API Won't Connect Locally

1. **Verify .env has cloud URLs**:
   ```bash
   cat .env | grep DATABASE_URL
   # Should show your Neon URL, not localhost
   ```

2. **Test database connection**:
   ```python
   from sqlalchemy import create_engine
   engine = create_engine(DATABASE_URL)
   with engine.connect() as conn:
       result = conn.execute("SELECT 1")
       print("Connected!")
   ```

## Cost Analysis

### Free Tier Limits

**Neon (Postgres)**:
- ✅ 0.5 GB storage (plenty for this app)
- ✅ Compute: Always available on free tier

**Upstash Redis**:
- ✅ 10,000 commands/day (more than enough)
- ✅ 256 MB storage

**GitHub Actions**:
- ✅ 2,000 minutes/month (private repos)
- ✅ Unlimited for public repos

**Alpha Vantage**:
- ✅ 5 API calls/minute
- ✅ 500 calls/day
- Our usage: ~24 calls/day (hourly updates for ~10 stocks)

**Reddit API**:
- ✅ 60 requests/minute
- Our usage: ~48 requests/day (every 30 min, 2 subreddits)

**Claude API**:
- 💰 Pay per use
- Our usage: ~2-4 API calls/day (morning + afternoon analysis)
- Cost: ~$0.10-0.20/day = ~$3-6/month

**Total**: ~$3-6/month (Claude API only)

## Workflow Tips

### Daily Routine

**Morning (after 9:30 AM EST)**:
1. Check GitHub Actions to see if morning analysis ran
2. Query recommendations via API or SQL
3. Review Claude's reasoning
4. Execute trades manually in Questrade if you agree

**Afternoon (after 4:00 PM EST)**:
1. Check afternoon analysis results
2. Review any new recommendations
3. Adjust stops/positions in Questrade

**Weekly**:
1. Review all recommendations for the week
2. Check success rate of suggestions
3. Adjust risk parameters if needed

### Adding New Stocks

```python
# add_stock.py
from app.database import SessionLocal
from app.models import Stock

db = SessionLocal()

new_stock = Stock(
    symbol="NEW.TO",
    name="New Company Inc",
    sector="Technology",
    exchange="TSX",
    is_active=True
)

db.add(new_stock)
db.commit()
print(f"Added {new_stock.symbol}")
db.close()
```

Or run via GitHub Actions by modifying `scripts/init-db.py` and pushing.

## Next Steps

1. ✅ **Monitor first week**: Let scheduled tasks run, observe results
2. ✅ **Review recommendations**: Check daily for Claude's suggestions
3. ✅ **Adjust parameters**: Update risk settings in user_settings table
4. ✅ **Track performance**: Keep log of which suggestions you followed and results
5. ✅ **Iterate**: Refine your strategy based on what works

The system is now fully automated and running in the cloud for free (except Claude API costs). You just need to review recommendations and execute trades manually in Questrade!
