# GitHub Actions Workflows Summary

All workflows are configured for **100% automation** - no manual script running required.

## Workflow Files

### 1. **scheduled-analysis.yml** - Market Data & Sentiment
**Location:** `.github/workflows/scheduled-analysis.yml`

**Runs:**
- Every hour: Market data updates (OHLCV, technical indicators)
- Every 30 min (9 AM - 5 PM EST): Sentiment analysis (Reddit)

**Jobs:**
- `market-data-update` - Fetches latest prices, calculates indicators
- `sentiment-update` - Scrapes Reddit, analyzes sentiment

**Manual Trigger:** Yes (choose market-data, sentiment, or all)

---

### 2. **daily-multibagger-analysis.yml** - Core Trading Logic
**Location:** `.github/workflows/daily-multibagger-analysis.yml`

**Runs:**
- 9:30 AM EST (Mon-Fri) - Market open analysis
- 4:00 PM EST (Mon-Fri) - Market close analysis

**Jobs:**
1. `multibagger-screening`
   - Screens all stocks using Yartseva's filters
   - Scores 0-100 based on FCF/Price, Book/Market, ROA
   - Returns top 10 candidates

2. `claude-analysis`
   - Analyzes top 5 candidates with Claude AI
   - Generates buy/hold/sell decisions
   - Provides detailed reasoning + suggested trade parameters
   - Creates system user if needed
   - Stores recommendations in `trading_decisions` table

**Manual Trigger:** Yes

---

### 3. **weekly-fundamentals.yml** - Fundamental Data Updates
**Location:** `.github/workflows/weekly-fundamentals.yml`

**Runs:**
- Saturdays at 2:00 AM EST (weekly)

**Jobs:**
- `update-fundamentals`
  - Fetches quarterly financials from Alpha Vantage (all stocks)
  - Updates FCF/Price, Book/Market, ROA, growth metrics
  - Takes ~40 minutes for 37 stocks (API rate limits: 4 calls/stock × 13 sec delay)

**Manual Trigger:** Yes

**Timeout:** 90 minutes (with buffer)

---

### 4. **monthly-stock-discovery.yml** - Stock Universe Maintenance
**Location:** `.github/workflows/monthly-stock-discovery.yml`

**Runs:**
- 1st of month at 3:00 AM EST - Stock review
- 1st of month at 4:00 AM EST - New stock discovery

**Jobs:**
1. `review-stocks`
   - Checks if existing stocks still fit $300M-$2B criteria
   - Deactivates stocks outside range
   - Preserves blue chips (TD, RY, BMO, etc.)

2. `discover-new-stocks`
   - Scans 60+ TSX candidate symbols
   - Adds new stocks in $300M-$2B range
   - Fetches initial market data

**Manual Trigger:** Yes (choose review, discover, or full-refresh)

---

### 5. **database-setup.yml** - One-Time Setup
**Location:** `.github/workflows/database-setup.yml`

**Runs:** Manual only

**Jobs:**
1. `database-migrate` - Run Alembic migrations
2. `init-stocks` - Initialize 39 starter stocks

**Manual Trigger:** Yes (choose migrate, init-stocks, or full-setup)

**Use:** Run once during initial setup, or after schema changes

---

## Workflow Schedule Overview

```
HOURLY (24/7):
  00:00 → Market data update
  01:00 → Market data update
  ...

EVERY 30 MIN (Mon-Fri, 9 AM - 5 PM EST):
  09:00 → Sentiment update
  09:30 → Sentiment update + MULTIBAGGER ANALYSIS 🎯
  10:00 → Sentiment update
  10:30 → Sentiment update
  ...
  16:00 → Sentiment update + MULTIBAGGER ANALYSIS 🎯
  16:30 → Sentiment update
  17:00 → Sentiment update

WEEKLY (Saturdays):
  02:00 → Fundamental data update (~40 min)

MONTHLY (1st of month):
  03:00 → Review existing stocks
  04:00 → Discover new stocks
```

---

## Required GitHub Secrets

All workflows need these secrets configured in repo settings:

```
DATABASE_URL              → Neon PostgreSQL connection string
ALPHA_VANTAGE_API_KEY     → For fundamental & market data
CLAUDE_API_KEY            → For AI analysis
REDDIT_CLIENT_ID          → For sentiment analysis
REDDIT_CLIENT_SECRET      → For sentiment analysis
SECRET_KEY                → JWT signing
REDIS_URL                 → Optional (for caching)
```

---

## Workflow Dependencies

```
daily-multibagger-analysis.yml
  ├─ Requires: fundamental data (from weekly-fundamentals.yml)
  ├─ Requires: stocks initialized (from database-setup.yml)
  └─ Requires: user account (auto-created by workflow)

weekly-fundamentals.yml
  ├─ Requires: stocks initialized
  └─ Requires: ALPHA_VANTAGE_API_KEY

monthly-stock-discovery.yml
  ├─ Requires: ALPHA_VANTAGE_API_KEY
  └─ Can run standalone

scheduled-analysis.yml
  ├─ market-data: Requires ALPHA_VANTAGE_API_KEY
  └─ sentiment: Requires REDDIT_CLIENT_ID + SECRET
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ MONTHLY (1st): Stock Discovery                          │
│ → Scans 60+ TSX symbols                                 │
│ → Adds/removes stocks based on market cap              │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ WEEKLY (Sat): Fundamental Data Update                   │
│ → Fetches quarterly financials (Alpha Vantage)         │
│ → Calculates FCF/Price, B/M, ROA, growth               │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ HOURLY: Market Data Update                              │
│ → OHLCV prices, technical indicators                   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ EVERY 30 MIN: Sentiment Update                          │
│ → Reddit scraping, VADER scoring                       │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 2x DAILY (9:30 AM & 4 PM): MULTIBAGGER ANALYSIS 🎯     │
│                                                          │
│ 1. Screen all stocks (Yartseva filters)                │
│    → FCF/Price ≥ 5%, Book/Market ≥ 0.40                │
│    → Market cap $300M-$2B                               │
│    → Score 0-100                                        │
│                                                          │
│ 2. Claude analyzes top 5 candidates                    │
│    → Hybrid fundamental + technical + sentiment        │
│    → Buy/Hold/Sell decision                            │
│    → Entry/exit prices, stop loss                      │
│    → Stores in trading_decisions table                 │
└─────────────────────────────────────────────────────────┘
                         ↓
              📊 REVIEW RECOMMENDATIONS
              (Check GitHub Actions logs or
               query trading_decisions table)
```

---

## Monitoring

### View Workflow Status
1. GitHub repo → Actions tab
2. See all workflow runs (success/failure)
3. Click any run to see detailed logs

### Get Notifications
GitHub repo → Watch → Custom → Check "Actions"
- Emails when workflows fail

### Manual Triggers
Actions → Select workflow → "Run workflow" button

---

## Next Steps After Setup

1. **Push to GitHub** with workflows
2. **Add GitHub Secrets** (7 required)
3. **Enable GitHub Actions** in repo settings
4. **Run initial setup:**
   - Manually trigger `database-setup.yml` → full-setup
   - Manually trigger `weekly-fundamentals.yml` (don't wait for Saturday)
5. **Wait 24 hours** for first automated analysis
6. **Review recommendations** in Actions logs

After that, **everything runs automatically** - just check the logs 2x daily to see what Claude recommends!
