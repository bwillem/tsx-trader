# Complete Automation Setup

This guide will set up **100% automated** stock analysis - you'll never need to run scripts manually.

## One-Time Setup

### Step 1: Push to GitHub

```bash
cd /Users/bryan/claude-code/tsx-trader

# Initialize git if needed
git init
git add .
git commit -m "Initial commit - automated multibagger trader"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/tsx-trader.git
git push -u origin main
```

### Step 2: Add GitHub Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

```
DATABASE_URL
postgresql://neondb_owner:npg_9UQMpzZf7Pmy@ep-rapid-star-ahch70oz-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require

ALPHA_VANTAGE_API_KEY
your-alpha-vantage-key

CLAUDE_API_KEY
your-claude-api-key

REDDIT_CLIENT_ID
your-reddit-client-id

REDDIT_CLIENT_SECRET
your-reddit-client-secret

SECRET_KEY
your-secret-key-for-jwt

REDIS_URL
redis://localhost:6379/0
```

### Step 3: Enable GitHub Actions

Go to your repo → Actions → "I understand my workflows, go ahead and enable them"

---

## What Runs Automatically

### ⏰ Hourly (24/7)
**Market Data Updates** (`scheduled-analysis.yml`)
- Fetches latest OHLCV price data for all stocks
- Calculates technical indicators (RSI, MACD, Bollinger Bands)

### ⏰ Every 30 Minutes (During Market Hours: 9 AM - 5 PM EST, Mon-Fri)
**Sentiment Analysis** (`scheduled-analysis.yml`)
- Scrapes Reddit (r/CanadianInvestor, r/Baystreetbets)
- Analyzes sentiment with VADER
- Updates stock mention counts

### ⏰ Twice Daily (9:30 AM & 4:00 PM EST, Mon-Fri)
**Multibagger Analysis** (`daily-multibagger-analysis.yml`)
- Runs multibagger screening (Yartseva's filters)
- Analyzes top 5 candidates with Claude AI
- Stores trading recommendations in database

**What you get:**
- Buy/Hold/Sell decision
- Confidence level (0-100%)
- Detailed reasoning
- Suggested entry/exit prices
- Stop loss levels

### ⏰ Weekly (Saturdays at 2:00 AM EST)
**Fundamental Data Update** (`weekly-fundamentals.yml`)
- Fetches quarterly financials from Alpha Vantage
- Updates FCF/Price, Book/Market, ROA, etc.
- Takes ~40 minutes for 37 stocks (API rate limits)

### ⏰ Monthly (1st of Month at 3:00 AM & 4:00 AM EST)
**Stock Discovery** (`monthly-stock-discovery.yml`)

**3:00 AM - Review existing stocks:**
- Checks if stocks still fit $300M-$2B market cap range
- Deactivates stocks that grew too large or shrank too small
- Preserves blue chips (TD, RY, etc.)

**4:00 AM - Discover new stocks:**
- Scans 60+ TSX candidates
- Adds new stocks in the $300M-$2B sweet spot
- Fetches initial market data

---

## Viewing Results

### Option 1: GitHub Actions Output

Go to your repo → Actions → Click on any workflow run

You'll see the screening results and Claude's analysis in the logs.

### Option 2: Query Database Directly

```bash
cd /Users/bryan/claude-code/tsx-trader

# View latest recommendations
docker-compose run --rm backend python -c "
from app.database import get_db_context
from app.models.decision import TradingDecision
from app.models.stock import Stock
from sqlalchemy import desc
from datetime import datetime, timedelta

with get_db_context() as db:
    yesterday = datetime.utcnow() - timedelta(days=1)

    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock)
        .filter(TradingDecision.created_at >= yesterday)
        .order_by(desc(TradingDecision.confidence))
        .limit(10)
        .all()
    )

    print('📈 LATEST RECOMMENDATIONS\\n')
    for decision, stock in decisions:
        print(f'{stock.symbol}: {decision.decision.upper()} ({decision.confidence:.0%})')
        print(f'  {decision.reasoning[:200]}...\\n')
"
```

### Option 3: Build the Dashboard (Future)

Run the Next.js frontend to view recommendations in a nice UI:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Manual Triggers

You can manually trigger any workflow from GitHub:

1. Go to Actions → Select workflow
2. Click "Run workflow" dropdown
3. Choose options (if available)
4. Click "Run workflow"

**Available manual triggers:**
- `weekly-fundamentals.yml` - Update fundamental data now
- `monthly-stock-discovery.yml` - Discover new stocks or review existing
- `daily-multibagger-analysis.yml` - Run screening + Claude analysis
- `scheduled-analysis.yml` - Update market data or sentiment
- `database-setup.yml` - Initialize database or add stocks

---

## Cost Estimate

**GitHub Actions:** FREE (2,000 minutes/month for free accounts)

**API Costs:**
- Alpha Vantage: FREE (25 requests/day limit)
- Claude API: ~$0.01-0.03 per analysis (~$1-2/month for 2x daily analysis)
- Reddit API: FREE

**Database:**
- Neon PostgreSQL: FREE tier (you're already using this)

**Total: ~$1-2/month**

---

## Monitoring

### Check if workflows are running

```bash
# View recent workflow runs via GitHub CLI (if installed)
gh run list

# Or visit: https://github.com/YOUR_USERNAME/tsx-trader/actions
```

### Get email notifications

Go to GitHub → Watch (top right) → Custom → Check "Actions"

You'll get emails if any workflow fails.

---

## Troubleshooting

### "No fundamental data"

The weekly workflow hasn't run yet. Manually trigger it:

1. Go to Actions → "Weekly Fundamental Data Update"
2. Click "Run workflow"
3. Wait ~40 minutes

### "No stocks passed filters"

This is normal if you just set up. After the weekly fundamental update runs, you'll start seeing candidates.

### Workflow fails

Check the error in Actions → Click the failed run → Check logs

Common issues:
- Missing GitHub secrets
- API key invalid/expired
- Database connection issue

---

## What You Need to Do

### Zero ongoing work required!

Once GitHub Actions is enabled with secrets configured, **everything runs automatically**.

Your only action: **Review Claude's recommendations** when you want to trade.

Check GitHub Actions logs 2x per day (9:30 AM & 4 PM) to see what Claude recommends, then execute trades manually in your broker.

---

## Summary

**Setup (one time):**
1. Push to GitHub ✓
2. Add 7 secrets ✓
3. Enable Actions ✓

**Ongoing (automatic):**
- ✅ Hourly: Market data updates
- ✅ Every 30 min: Sentiment analysis
- ✅ Daily (2x): Multibagger screening + Claude analysis
- ✅ Weekly: Fundamental data updates
- ✅ Monthly: Stock discovery + review

**You do:** Nothing! (Except review recommendations and execute trades manually)
