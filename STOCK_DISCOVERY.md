# Automated Stock Discovery System

Keep your TSX multibagger stock universe fresh and current with automated discovery.

## Why Stock Discovery?

The multibagger criteria requires stocks in the **$300M-$2B market cap range**. But this range is dynamic:

- **New IPOs** enter the market
- **Successful companies** grow from micro-cap into small-cap range
- **Existing holdings** may grow too large (>$2B) or shrink too small (<$300M)
- **Sector changes** bring new opportunities

Without automated discovery, you'd miss opportunities or hold outdated positions.

## What It Does

### 1. Discovers New Stocks
- Checks 60+ potential TSX small caps
- Fetches market caps from Alpha Vantage
- Adds stocks in $300M-$2B range to database
- Categorizes by sector for diversification

### 2. Reviews Existing Stocks
- Checks market caps of all active stocks
- Deactivates stocks that grew too large (>$2B)
- Deactivates stocks that became too small (<$300M)
- Preserves blue chips regardless of size

### 3. Maintains Blue Chips
- Always keeps ~20 large cap blue chips
- Provides diversification and stability
- Includes major banks, energy, telecom, etc.

## How to Use

### Manual Discovery

#### Discover New Stocks
```bash
docker-compose exec backend python scripts/discover-stocks.py discover [max_new]
```

**What it does**:
- Checks curated list of potential candidates
- Adds stocks in $300M-$2B range
- Limit new additions with `max_new` parameter

**Example**:
```bash
# Add up to 20 new stocks
docker-compose exec backend python scripts/discover-stocks.py discover 20
```

**Output**:
```
=== TSX Stock Discovery ===
Checking 65 TSX symbols...

✓ WELL.TO: Added as small cap ($850,000,000) - WELL Health Technologies
✓ DCBO.TO: Added as small cap ($1,200,000,000) - Docebo Inc
✓ PXT.TO: Added as small cap ($750,000,000) - Parex Resources
  TD.TO: Already active ($145,000,000,000)
  XYZ.TO: Outside range ($200,000,000), skipping

Discovery Complete:
  Symbols checked: 65
  New stocks added: 12
  Stocks deactivated: 0
  Small caps found: 12
```

#### Review Existing Stocks
```bash
docker-compose exec backend python scripts/discover-stocks.py review
```

**What it does**:
- Checks all active stocks
- Deactivates if outside $300M-$2B range
- Keeps blue chips active

**Example output**:
```
=== Reviewing Existing Stocks ===
Reviewing 45 active stocks...

✓ WELL.TO: Still in range ($850,000,000)
✓ DCBO.TO: Still in range ($1,200,000,000)
○ XYZ.TO: Deactivated (grew too large) ($2,500,000,000)
○ ABC.TO: Deactivated (became too small) ($250,000,000)

Review Complete:
  Total stocks: 45
  Reviewed: 45
  Still in range: 38
  Deactivated: 2
```

#### Full Refresh (Both)
```bash
docker-compose exec backend python scripts/discover-stocks.py refresh
```

**What it does**:
1. Reviews existing stocks (deactivate if needed)
2. Discovers new stocks (add candidates)

**When to run**: Monthly or quarterly

#### Show Statistics
```bash
docker-compose exec backend python scripts/discover-stocks.py stats
```

**Output**:
```
=== Stock Universe Statistics ===
Total stocks:    52
Active stocks:   47
Inactive stocks: 5
TSX stocks:      52
Last updated:    2026-01-19 22:00:00
```

---

## Automated Schedule

The system runs these tasks automatically via Celery Beat:

### Weekly: Update Fundamental Data
- **Schedule**: Saturdays at 2 AM
- **Task**: `update_fundamental_data()`
- **What it does**: Fetches latest quarterly financials for all active stocks
- **Duration**: ~1 minute per stock (slow due to API rate limits)

### Monthly: Review Existing Stocks
- **Schedule**: 1st of month at 3 AM
- **Task**: `review_existing_stocks()`
- **What it does**: Checks if existing stocks still fit $300M-$2B range
- **Duration**: ~5-15 minutes (depends on number of active stocks)

### Monthly: Discover New Stocks
- **Schedule**: 1st of month at 4 AM
- **Task**: `discover_new_stocks()`
- **What it does**: Finds and adds new stocks in multibagger range
- **Duration**: ~10-30 minutes (checks 60+ candidates)

---

## How It Works

### Discovery Process

1. **Candidate List** - Start with curated list of ~60 TSX symbols
   - Technology: WELL.TO, DCBO.TO, TOI.TO, LSPD.TO, etc.
   - Energy: PXT.TO, TVE.TO, BTE.TO, WCP.TO, etc.
   - Healthcare: QIPT.TO, PHM.TO, MT.TO, etc.
   - Financials: EQB.TO, GSY.TO, HCG.TO, etc.
   - Industrials: NFI.TO, BYD.TO, GFL.TO, etc.

2. **Fetch Market Caps** - Call Alpha Vantage OVERVIEW endpoint
   ```python
   overview = av_service.fetch_company_overview(symbol)
   market_cap = float(overview.get("MarketCapitalization"))
   ```

3. **Filter by Range**
   ```python
   in_range = 300_000_000 <= market_cap <= 2_000_000_000
   ```

4. **Add to Database** - If in range and not exists
   ```python
   if in_range and not db.query(Stock).filter(Stock.symbol == symbol).first():
       stock = Stock(symbol=symbol, name=name, sector=sector, is_active=True)
       db.add(stock)
   ```

5. **Rate Limiting** - Sleep 13 seconds between API calls
   ```python
   time.sleep(13)  # Alpha Vantage free tier: 5 calls/min
   ```

### Review Process

1. **Get Active Stocks** - Query database
   ```python
   stocks = db.query(Stock).filter(Stock.is_active == True).all()
   ```

2. **Check Each Stock** - Fetch current market cap
   ```python
   for stock in stocks:
       overview = av_service.fetch_company_overview(stock.symbol)
       market_cap = float(overview.get("MarketCapitalization"))
   ```

3. **Determine Status**
   ```python
   in_range = min_cap <= market_cap <= max_cap
   is_blue_chip = stock.symbol in BLUE_CHIPS
   should_keep = in_range or is_blue_chip
   ```

4. **Deactivate if Needed**
   ```python
   if not should_keep:
       stock.is_active = False
       reason = "grew too large" if market_cap > max_cap else "became too small"
   ```

---

## Configuration

### Market Cap Ranges

Default settings (can be customized in code):

```python
TSXStockDiscovery(
    min_market_cap=300_000_000,    # $300M - Yartseva's lower bound
    max_market_cap=2_000_000_000,  # $2B - small cap upper limit
    include_large_caps=True,        # Keep blue chips for diversification
    rate_limit_delay=13,            # 13 seconds = ~5 calls/min (free tier)
)
```

### Blue Chip Preservation

These symbols are always kept active regardless of market cap:

**Banks**: TD.TO, RY.TO, BMO.TO, BNS.TO, CM.TO
**Energy**: ENB.TO, CNQ.TO, SU.TO, TRP.TO
**Railroads**: CP.TO, CNR.TO
**Tech**: SHOP.TO
**Telecom**: BCE.TO, T.TO, RCI-B.TO
**Utilities**: FTS.TO, EMA.TO
**Consumer**: ATD.TO, DOL.TO, QSR.TO

### Candidate List

The discovery service checks these sectors:

- **Technology** (10 stocks): WELL.TO, DCBO.TO, TOI.TO, LSPD.TO, OTEX.TO, etc.
- **Energy** (11 stocks): PXT.TO, TVE.TO, BTE.TO, WCP.TO, ERF.TO, etc.
- **Materials** (10 stocks): HBM.TO, TKO.TO, FM.TO, EDV.TO, OR.TO, etc.
- **Industrials** (9 stocks): NFI.TO, BYD.TO, GFL.TO, TOY.TO, MTY.TO, etc.
- **Healthcare** (5 stocks): QIPT.TO, PHM.TO, MT.TO, NHC.TO, etc.
- **Financials** (6 stocks): EQB.TO, GSY.TO, HCG.TO, LB.TO, FSV.TO, etc.
- **Real Estate** (7 stocks): CAR-UN.TO, HR-UN.TO, DIR-UN.TO, SRU-UN.TO, etc.
- **Consumer** (8 stocks): TFII.TO, DOL.TO, ATD.TO, QSR.TO, MTY.TO, etc.

**Total**: 60+ potential candidates

---

## After Discovery

Once new stocks are discovered, you need to:

### 1. Fetch Fundamental Data
```bash
# For a specific stock
docker-compose exec backend python scripts/test-fundamentals.py WELL.TO

# Or update all stocks (slow!)
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.tasks.market_data_tasks import update_fundamental_data
update_fundamental_data()
"
```

### 2. Run Multibagger Screening
```bash
docker-compose exec backend python scripts/screen-multibaggers.py 20
```

This will:
- Apply Yartseva's filters to all stocks with fundamental data
- Rank by multibagger score
- Show which stocks pass screening criteria

### 3. Trigger Claude Analysis
```bash
docker-compose exec backend python -c "
from app.database import get_db_context
from app.models import User
from app.services.chat import ClaudeTrader

with get_db_context() as db:
    user = db.query(User).first()
    trader = ClaudeTrader(db, user)
    decision = trader.analyze_symbol('WELL.TO')
    print(f'Decision: {decision.decision}')
    print(f'Reasoning: {decision.reasoning}')
"
```

---

## Performance Considerations

### API Rate Limits
- **Alpha Vantage free tier**: 5 calls/minute, 500 calls/day
- **Discovery**: ~13 seconds per stock (rate limited)
- **60 stocks**: ~13 minutes total
- **Review**: Same timing

### Timing Recommendations
- **Discovery**: Run monthly or when market conditions change
- **Review**: Run quarterly or after significant market moves
- **Full refresh**: Run at month start (automated)

### Optimization
- Discovery only adds up to `max_new_stocks` per run (default 50)
- Review can check all stocks (typically <100)
- Both tasks run during off-hours (nights/weekends)

---

## Monitoring

### Check Celery Logs
```bash
docker-compose logs -f celery_beat celery_worker
```

Look for:
```
[2026-01-01 03:00:00] Task app.tasks.stock_discovery_tasks.review_existing_stocks started
[2026-01-01 03:15:00] Task app.tasks.stock_discovery_tasks.review_existing_stocks succeeded
[2026-01-01 04:00:00] Task app.tasks.stock_discovery_tasks.discover_new_stocks started
```

### Database Queries
```sql
-- Check active stocks
SELECT symbol, name, sector, is_active
FROM stocks
WHERE is_active = true
ORDER BY sector, symbol;

-- Check by market cap (requires fundamental data)
SELECT s.symbol, s.name, f.market_cap
FROM stocks s
JOIN fundamental_data_quarterly f ON s.id = f.stock_id
WHERE s.is_active = true
  AND f.fiscal_date = (
      SELECT MAX(fiscal_date)
      FROM fundamental_data_quarterly
      WHERE stock_id = s.id
  )
ORDER BY f.market_cap;

-- Check recently added stocks
SELECT symbol, name, created_at
FROM stocks
WHERE created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;
```

---

## Troubleshooting

### No New Stocks Found
**Possible reasons**:
- All candidates already in database
- Candidates outside $300M-$2B range
- API rate limit hit
- Alpha Vantage API issues

**Solution**: Check logs, try again later, or adjust market cap range

### Stock Incorrectly Deactivated
**Possible reasons**:
- Market cap data from Alpha Vantage is stale
- Stock had temporary price drop

**Solution**: Manually reactivate in database
```sql
UPDATE stocks SET is_active = true WHERE symbol = 'XYZ.TO';
```

### Discovery Taking Too Long
**Possible reasons**:
- Checking too many symbols
- API rate limits

**Solution**: Reduce `max_new_stocks` parameter or run overnight

---

## Best Practices

1. **Run discovery monthly** - Markets change, new opportunities emerge
2. **Review quarterly** - Check if holdings still fit criteria
3. **Monitor deactivations** - Understand why stocks left the range
4. **Fetch fundamentals for new stocks** - Required for screening
5. **Re-run screening after discovery** - Find best new candidates
6. **Let automation work** - Celery tasks handle monthly refresh

---

## Example Workflow

### Initial Setup
```bash
# 1. Discover stocks
docker-compose exec backend python scripts/discover-stocks.py discover 50

# 2. Wait for completion (~20-30 minutes)

# 3. Fetch fundamentals for new stocks
docker-compose exec backend python -c "
from app.tasks.market_data_tasks import update_fundamental_data
update_fundamental_data()
"

# 4. Run screening
docker-compose exec backend python scripts/screen-multibaggers.py 20
```

### Monthly Maintenance
```bash
# Check what the automated tasks did
docker-compose logs celery_worker | grep stock_discovery

# Show current universe
docker-compose exec backend python scripts/discover-stocks.py stats

# Manual refresh if needed
docker-compose exec backend python scripts/discover-stocks.py refresh
```

---

## Summary

The automated stock discovery system ensures your multibagger universe stays:

✅ **Current** - New opportunities added monthly
✅ **Relevant** - Stocks outside range removed
✅ **Diversified** - Blue chips preserved
✅ **Efficient** - Automated with Celery
✅ **Aligned with Yartseva** - Focus on $300M-$2B small caps

**Set it and forget it** - The monthly automation keeps your stock list fresh while you focus on analysis and execution.
