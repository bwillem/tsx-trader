# Alpha Vantage API Limits & Batching Strategy

## The Problem

Alpha Vantage free tier has strict rate limits:
- **25 API calls per day**
- **5 API calls per minute**

Each stock requires **4 API calls** to fetch full fundamental data:
1. Company Overview (market cap, book value, etc.)
2. Income Statement (revenue, EBITDA, net income)
3. Balance Sheet (assets, equity, debt)
4. Cash Flow (operating cash flow, FCF, capex)

**Math**: 37 stocks × 4 calls = **148 API calls needed**

With 25 calls/day, it takes **6 days** to populate all fundamental data.

---

## The Solution: Intelligent Batching

### How It Works

The system now uses **smart batching**:

1. **Prioritizes stocks without data** (fetches new stocks first)
2. **Processes 6 stocks per day** (6 × 4 = 24 calls, under 25 limit)
3. **Tracks update timestamps** (avoids re-fetching recent data)
4. **Runs daily** instead of weekly
5. **Gradually populates** the entire dataset over 7 days

### Daily Schedule

```
Day 1: Stocks 1-6   (24 API calls)
Day 2: Stocks 7-12  (24 API calls)
Day 3: Stocks 13-18 (24 API calls)
Day 4: Stocks 19-24 (24 API calls)
Day 5: Stocks 25-30 (24 API calls)
Day 6: Stocks 31-36 (24 API calls)
Day 7: Stock 37     (4 API calls)

After Day 7: All stocks have data ✓
```

### Automated Workflow

GitHub Actions runs daily at 2 AM EST:
- **Workflow**: `.github/workflows/daily-fundamentals.yml`
- **Frequency**: Every day
- **Batch size**: 6 stocks
- **Duration**: ~6 minutes per run (52 sec × 6 stocks)

---

## Testing & Diagnostics

### Test Alpha Vantage Support for TSX

Before relying on Alpha Vantage, verify it supports TSX stocks:

```bash
docker-compose run --rm backend python scripts/test-alpha-vantage.py
```

**This script tests**:
1. ✓ API key is valid
2. ✓ Which symbol format works for TSX (.TO, .TSE, TOR:, TSE:)
3. ✓ Whether fundamental data is available

**Important**: This uses 5+ API calls, so don't run repeatedly.

### Test Single Stock

```bash
docker-compose run --rm backend python scripts/test-fundamentals.py TD.TO
```

This:
- Fetches data for one stock (4 API calls)
- Shows which metrics are available
- Displays Yartseva filter results
- Takes ~1 minute

### Manual Batch Update

```bash
docker-compose run --rm backend python -c "
from app.database import get_db_context
from app.tasks.market_data_tasks import update_fundamental_data

# Process 6 stocks (default)
result = update_fundamental_data()
print(result)
"
```

Or process fewer stocks to conserve API calls:

```bash
# Process only 3 stocks
docker-compose run --rm backend python -c "
from app.database import get_db_context
from app.tasks.market_data_tasks import update_fundamental_data

result = update_fundamental_data(batch_size=3)
print(result)
"
```

---

## Checking Progress

### Via GitHub Actions

1. Go to: `https://github.com/YOUR_USERNAME/tsx-trader/actions`
2. Click "Daily Fundamental Data Update"
3. View latest run logs
4. See which stocks were updated

### Via Database Query

```bash
docker-compose run --rm backend python -c "
from app.database import get_db_context
from app.models.fundamentals import FundamentalDataQuarterly
from sqlalchemy import func

with get_db_context() as db:
    # Count stocks with data
    count = db.query(func.count(func.distinct(FundamentalDataQuarterly.stock_id))).scalar()

    print(f'Stocks with fundamental data: {count}/37')
    print(f'Progress: {count/37:.1%}')

    if count < 37:
        remaining = 37 - count
        days_left = (remaining + 5) // 6  # Round up
        print(f'Remaining: {remaining} stocks (~{days_left} days)')
"
```

---

## Alpha Vantage Limitations

### What It Doesn't Support Well

❌ **TSX stocks may have limited coverage**
- Some TSX stocks may not have fundamental data
- `.TO` suffix might not work for all stocks
- Small caps especially may be missing

❌ **Free tier is very limited**
- Only 25 calls/day
- Takes 7 days to fetch all 37 stocks
- Can't refresh data frequently

❌ **Rate limiting is strict**
- 5 calls per minute maximum
- Need 12+ second delays between calls
- Easy to hit limits accidentally

### What Works Well

✓ **Large cap TSX stocks**
- TD, RY, SHOP, ENB usually have data
- Major banks and blue chips covered

✓ **US stocks**
- Full coverage of US markets
- Faster data updates
- More reliable

✓ **Company overview data**
- Market cap, book value
- P/E, P/B ratios
- Generally available

---

## Alternatives to Alpha Vantage

If Alpha Vantage doesn't have TSX coverage, consider:

### 1. **Financial Modeling Prep** (Recommended)
- **Cost**: $15/month (Professional plan)
- **TSX Coverage**: Yes, excellent
- **API Limits**: 250 calls/day
- **Data Quality**: Very good for Canadian stocks
- **Website**: financialmodelingprep.com

### 2. **Polygon.io**
- **Cost**: $29/month (Starter plan)
- **TSX Coverage**: Yes
- **API Limits**: Unlimited
- **Data Quality**: Excellent
- **Website**: polygon.io

### 3. **Yahoo Finance (via yfinance)**
- **Cost**: FREE
- **TSX Coverage**: Yes
- **API Limits**: Soft limits (can be aggressive)
- **Data Quality**: Good but unofficial API
- **Website**: pypi.org/project/yfinance/

### 4. **Alpha Vantage Premium**
- **Cost**: $50/month
- **TSX Coverage**: Unknown (need to verify)
- **API Limits**: 75 calls/minute, 1200/day
- **Data Quality**: Same as free tier
- **Website**: alphavantage.co/premium

---

## Recommended Approach

### Option 1: Stick with Alpha Vantage (Free)

**Pros**:
- Free
- Works for testing
- Gradual data population is fine

**Cons**:
- Takes 7 days for initial population
- Limited TSX coverage
- Can't update frequently

**Best for**: Testing, small portfolios, patient users

### Option 2: Upgrade to Financial Modeling Prep ($15/month)

**Pros**:
- Excellent TSX coverage
- 250 calls/day (all 37 stocks in 1 day)
- Better data quality
- Can refresh weekly

**Cons**:
- Costs $15/month
- Need to rewrite API integration

**Best for**: Serious traders, production use

### Option 3: Use Yahoo Finance (Free)

**Pros**:
- Free
- Good TSX coverage
- Unlimited calls (soft limits)
- Easy to implement (yfinance library)

**Cons**:
- Unofficial API (could break)
- Less reliable
- Data quality varies

**Best for**: Free alternative with better TSX support

---

## Implementation Status

### Current Setup

✅ **Batching implemented** - Processes 6 stocks/day
✅ **Daily workflow** - Runs automatically at 2 AM EST
✅ **Smart prioritization** - Fetches stocks without data first
✅ **Rate limiting** - Respects 5 calls/minute limit
✅ **Error handling** - Logs failures, continues processing

### What to Do Now

**Immediate (Today)**:

1. **Test API compatibility**:
   ```bash
   docker-compose run --rm backend python scripts/test-alpha-vantage.py
   ```

2. **If TSX is supported**: Let daily workflow run for 7 days

3. **If TSX is NOT supported**: Choose alternative provider

**Short-term (This Week)**:

- Monitor GitHub Actions logs daily
- Check progress with database query
- Verify data quality once populated

**Long-term (After Data Populated)**:

- Decide if Alpha Vantage free tier is sufficient
- Consider upgrading to paid provider
- Set up monthly data refresh schedule

---

## FAQ

**Q: Can I speed this up?**

A: Not on the free tier. You'd need to:
- Upgrade to Alpha Vantage Premium ($50/month)
- Switch to Financial Modeling Prep ($15/month)
- Or accept the 7-day timeline

**Q: What if a stock fails to fetch?**

A: The script logs failures but continues. That stock will be retried on the next run (7 days later when all others are updated).

**Q: Can I manually trigger updates?**

A: Yes, via GitHub Actions "Run workflow" button, or run the script locally.

**Q: Will this work for 100+ stocks?**

A: Not efficiently on free tier. With 100 stocks:
- 100 × 4 = 400 API calls needed
- 400 / 24 calls per day = 17 days to populate
- Consider paid provider for larger universes

**Q: How often should data be refreshed?**

A: Quarterly data typically updates every 3 months. Monthly refresh is plenty. Weekly is overkill but doesn't hurt if you have API capacity.

---

## Summary

**Alpha Vantage free tier is usable but limited**:
- ✅ Works for testing and small portfolios
- ✅ Gradual population is acceptable
- ⚠️ TSX coverage may be incomplete
- ❌ Not suitable for large-scale production

**For serious trading**:
- Consider Financial Modeling Prep ($15/month)
- Or Yahoo Finance (free but unofficial)
- Or Polygon.io ($29/month for premium)

**Current status**:
- Batching system implemented
- Will take 7 days to populate all data
- Runs automatically every day at 2 AM
