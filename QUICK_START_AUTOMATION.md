# 5-Minute Automation Setup Checklist

Follow these steps to enable **100% automated** multibagger stock analysis.

## ✅ Step 1: Get API Keys

You'll need these API keys (all have free tiers):

### 1. Claude API Key (Anthropic)
- Visit: https://console.anthropic.com/
- Sign up / Log in
- Go to API Keys → Create Key
- Copy your key: `sk-ant-...`

**Cost:** ~$1-2/month for 2x daily analysis

### 2. Alpha Vantage API Key
- Visit: https://www.alphavantage.co/support/#api-key
- Enter email → Get Free API Key
- Copy your key

**Cost:** FREE (25 API calls/day)

### 3. Reddit API Credentials (Optional - for sentiment)
- Visit: https://www.reddit.com/prefs/apps
- Click "create another app..."
- Choose "script" type
- Name: "TSX Trader"
- Redirect URI: `http://localhost:8000`
- Copy Client ID and Client Secret

**Cost:** FREE

---

## ✅ Step 2: Push to GitHub

```bash
cd /Users/bryan/claude-code/tsx-trader

# Check if git is initialized
git status

# If not initialized:
git init
git add .
git commit -m "Initial commit - automated multibagger trader"

# Create a NEW repo on GitHub (https://github.com/new)
# Name it: tsx-trader
# Keep it PRIVATE (contains API keys in Actions)
# Don't initialize with README (we already have one)

# Then connect and push:
git remote add origin https://github.com/YOUR_USERNAME/tsx-trader.git
git branch -M main
git push -u origin main
```

---

## ✅ Step 3: Add GitHub Secrets

Go to your GitHub repo:
```
https://github.com/YOUR_USERNAME/tsx-trader/settings/secrets/actions
```

Click "New repository secret" for each:

### Required Secrets:

**1. DATABASE_URL**
```
postgresql://neondb_owner:npg_9UQMpzZf7Pmy@ep-rapid-star-ahch70oz-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
```

**2. ALPHA_VANTAGE_API_KEY**
```
your-alpha-vantage-key-from-step-1
```

**3. CLAUDE_API_KEY**
```
sk-ant-your-key-from-step-1
```

**4. SECRET_KEY** (generate a random string)
```bash
# Generate on Mac/Linux:
openssl rand -base64 32
```
Copy the output

**5. REDDIT_CLIENT_ID** (if you got Reddit credentials)
```
your-reddit-client-id
```

**6. REDDIT_CLIENT_SECRET**
```
your-reddit-secret
```

**7. REDIS_URL** (optional - not used by GitHub Actions)
```
redis://localhost:6379/0
```

---

## ✅ Step 4: Enable GitHub Actions

1. Go to your repo → **Actions** tab
2. If prompted: Click **"I understand my workflows, go ahead and enable them"**
3. You should see 5 workflows listed:
   - Market Data & Sentiment Updates
   - Daily Multibagger Analysis
   - Weekly Fundamental Data Update
   - Monthly Stock Discovery
   - Database Setup

---

## ✅ Step 5: Run Initial Setup

### 5a. Initialize Database (one-time)

Go to Actions → "Database Setup" → "Run workflow"
- Choose action: **full-setup**
- Click "Run workflow"

Wait ~2 minutes. This will:
- Run migrations (create tables)
- Add 37 TSX stocks to database

### 5b. Fetch Initial Fundamental Data (one-time)

Go to Actions → "Weekly Fundamental Data Update" → "Run workflow"
- Click "Run workflow"

Wait ~40 minutes. This fetches quarterly financials for all 37 stocks.

**Note:** This normally runs automatically every Saturday, but we're triggering it manually now so you don't have to wait.

---

## ✅ Step 6: Verify It's Working

### Option 1: Check GitHub Actions Logs

Go to Actions → "Daily Multibagger Analysis" → "Run workflow"

Wait ~5 minutes, then click the run to see:
- Multibagger screening results
- Claude's analysis of top 5 candidates
- Buy/Hold/Sell recommendations

### Option 2: Query Database Locally

```bash
cd /Users/bryan/claude-code/tsx-trader

docker-compose run --rm backend python -c "
from app.database import get_db_context
from app.models.decision import TradingDecision
from app.models.stock import Stock
from sqlalchemy import desc

with get_db_context() as db:
    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock)
        .order_by(desc(TradingDecision.created_at))
        .limit(5)
        .all()
    )

    print('\n📈 LATEST RECOMMENDATIONS\n')
    for decision, stock in decisions:
        print(f'{stock.symbol}: {decision.decision.upper()} ({decision.confidence:.0%})')
        print(f'  {decision.reasoning[:150]}...\n')
"
```

---

## 🎉 Done! What Happens Now

### Automatic Schedule (No Action Required)

**Every Hour:**
- Market data updates (OHLCV, technical indicators)

**Every 30 Minutes (Mon-Fri, 9 AM - 5 PM):**
- Sentiment analysis (Reddit scraping)

**2x Daily (Mon-Fri at 9:30 AM & 4:00 PM EST):**
- Multibagger screening (Yartseva filters)
- Claude analyzes top 5 candidates
- Stores buy/hold/sell recommendations in database

**Weekly (Saturdays at 2:00 AM):**
- Updates fundamental data for all stocks (~40 min)

**Monthly (1st of month at 3:00 AM & 4:00 AM):**
- Reviews existing stocks (deactivates if outside $300M-$2B)
- Discovers new TSX small caps

---

## 📊 How to View Recommendations

### Method 1: GitHub Actions (Easiest)

1. Go to Actions tab in your repo
2. Click "Daily Multibagger Analysis"
3. Click latest run
4. Expand "Run Claude trading analysis" step
5. See full analysis with buy/sell decisions

### Method 2: Email Notifications

Go to your GitHub repo → Watch (top right) → Custom → Check "Actions"

You'll get emails when:
- New recommendations are generated
- Workflows fail

### Method 3: Query Database (Most Detailed)

Use the Docker command from Step 6, Option 2 above.

---

## 🔧 Customization

### Change Screening Filters

Edit `.github/workflows/daily-multibagger-analysis.yml`:

```python
screener = MultibaggerScreener(
    min_fcf_price_ratio=0.05,      # Lower to 0.03 for more results
    min_book_to_market=0.40,       # Lower to 0.30 for more results
    min_market_cap=300_000_000,    # $300M
    max_market_cap=2_000_000_000,  # $2B
)
```

### Change Analysis Frequency

Edit `.github/workflows/daily-multibagger-analysis.yml`:

```yaml
on:
  schedule:
    - cron: '30 14 * * 1-5'  # 9:30 AM EST - Change time here
    - cron: '0 21 * * 1-5'   # 4:00 PM EST - Change time here
```

### Change Number of Stocks Analyzed

Edit `.github/workflows/daily-multibagger-analysis.yml`:

```python
results = screener.screen(db, limit=5)  # Change from 5 to 10
```

---

## ❌ Troubleshooting

### "No fundamental data"

Wait for weekly fundamentals workflow to run (Saturdays), or manually trigger it in Actions.

### "No stocks passed filters"

This is normal initially. After fundamental data is fetched:
- Lower the thresholds (see Customization above)
- Check stats: some stocks may be close to passing

### Workflow fails

1. Go to Actions → Click failed run
2. Check error message
3. Common issues:
   - Missing/incorrect GitHub secret
   - API key invalid/expired
   - Database connection issue

### Check if secrets are set

Go to Settings → Secrets and variables → Actions

You should see 7 secrets listed (names only, values hidden).

---

## 📚 Additional Documentation

- **[AUTOMATION_SETUP.md](AUTOMATION_SETUP.md)** - Detailed automation guide
- **[WORKFLOWS_SUMMARY.md](WORKFLOWS_SUMMARY.md)** - All workflows explained
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Manual usage (for development)
- **[YARTSEVA_IMPLEMENTATION.md](YARTSEVA_IMPLEMENTATION.md)** - Research foundation

---

## ✨ Summary

**What you just did:**
1. ✅ Got API keys (5 min)
2. ✅ Pushed to GitHub (2 min)
3. ✅ Added 7 secrets (3 min)
4. ✅ Enabled Actions (1 min)
5. ✅ Ran initial setup (45 min automated)

**What happens now:**
- **You:** Nothing! Just check recommendations 2x daily
- **System:** Automatically screens stocks, analyzes with Claude, stores recommendations

**Your involvement:**
- Review recommendations in GitHub Actions logs or email
- Manually execute trades in your broker

**That's it. No scripts to run. Ever.**
