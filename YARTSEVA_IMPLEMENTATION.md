# Yartseva Multibagger Implementation

Implementation of hybrid fundamental + technical stock analysis based on:
**"The Alchemy of Multibagger Stocks"** by Anna Yartseva (CAFE Working Paper 33, 2025)

## Summary

This implementation adds **fundamental analysis** to the existing technical/sentiment system, creating a hybrid approach for identifying stocks with 10x+ return potential.

### Key Research Findings (Yartseva 2025)

Based on analysis of 464 stocks that achieved 10x+ returns from 2009-2024:

1. **FCF/Price (free cash flow yield)** - STRONGEST PREDICTOR
   - Regression coefficients: 46-82 (highly significant)
   - Minimum threshold: 5% FCF yield

2. **Book-to-Market ratio** - Value factor
   - Must be > 0.40 with positive profitability
   - High B/M + high FCF = "value + quality"

3. **Small cap focus** - Size effect
   - Optimal range: $300M-$2B market cap
   - Median starting cap of multibaggers: $348M
   - Large caps rarely achieve 10x

4. **Reinvestment quality** - Growth efficiency
   - Asset growth ≤ EBITDA growth is POSITIVE
   - Asset growth > EBITDA growth is NEGATIVE signal
   - Shows disciplined capital allocation

5. **Entry timing** - Mean reversion
   - Buy near 12-month lows
   - **Negative 3-6 month momentum is POSITIVE** (contrary to trend following)
   - Avoid stocks at 52-week highs

6. **Red flags** - Automatic disqualifiers
   - Negative equity
   - High valuation without cash flow
   - Poor reinvestment track record

---

## What Was Implemented

### 1. Database Models (`backend/app/models/fundamentals.py`)

Created two new models:

- **`FundamentalDataQuarterly`** - Stores quarterly financial data
  - Balance sheet: assets, equity, debt, cash
  - Income statement: revenue, EBITDA, operating income, net income
  - Cash flow: operating cash flow, free cash flow, capex
  - **Calculated ratios**: FCF/Price, B/M, ROA, ROE, margins
  - **Growth rates**: YoY asset, EBITDA, revenue growth
  - **Quality flags**: profitable, negative equity, reinvestment quality

- **`FundamentalDataAnnual`** - Annual aggregated data for trend analysis

**Database migration**: `backend/alembic/versions/2026_01_19_2230-add_fundamental_data_tables.py`

---

### 2. Data Integration (`backend/app/services/market_data/alpha_vantage.py`)

Extended `AlphaVantageService` with fundamental data fetching:

#### New Methods:
- `fetch_company_overview()` - Company info and key ratios
- `fetch_income_statement()` - Quarterly/annual income statements
- `fetch_balance_sheet()` - Quarterly/annual balance sheets
- `fetch_cash_flow()` - Quarterly/annual cash flows
- `update_fundamental_data_quarterly()` - Main method to fetch and store data
- `_calculate_derived_metrics()` - Calculates FCF/Price, B/M, ROA, etc.
- `_calculate_quarterly_growth_rates()` - YoY growth rates + reinvestment quality flag

#### Data Sources:
- Alpha Vantage Fundamental Data API
- OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW endpoints
- Rate limited: ~1 minute per stock (4 API calls with delays)

---

### 3. Multibagger Screening (`backend/app/services/screening/multibagger_screener.py`)

New `MultibaggerScreener` class that implements Yartseva's criteria:

#### Screening Filters:
```python
MultibaggerScreener(
    min_fcf_price_ratio=0.05,      # 5% FCF yield
    min_book_to_market=0.40,       # Yartseva threshold
    min_market_cap=300_000_000,    # $300M
    max_market_cap=2_000_000_000,  # $2B (small cap)
    require_profitability=True,
    exclude_negative_equity=True,
    require_reinvestment_quality=False,  # Optional (needs 2+ years data)
)
```

#### Scoring Algorithm:
- **FCF/Price**: 40 points max (strongest predictor)
- **Book/Market**: 20 points max (value factor)
- **ROA**: 15 points max (profitability)
- **Reinvestment quality**: 10 points bonus
- **EBITDA margin**: 5 points max
- **Technical timing**: 10 points bonus (near lows, negative momentum)

**Total score range**: 0-100

#### Output:
Returns `MultibaggerCandidate` objects with:
- All fundamental metrics (FCF/P, B/M, ROA, etc.)
- Growth rates and quality flags
- Technical timing (52-week highs/lows, momentum)
- Composite multibagger score
- Which Yartseva filters the stock passes

---

### 4. Claude Integration (`backend/app/services/chat/claude_trader.py`)

Updated `ClaudeTrader` to use **hybrid fundamental + technical analysis**:

#### New Methods:
- `_get_fundamental_context()` - Fetches latest quarterly fundamentals
- `_categorize_market_cap()` - Identifies small cap sweet spot
- `_check_yartseva_filters()` - Checks which filters stock passes

#### Enhanced Prompt:
The Claude analysis prompt now includes:

1. **Research Foundation**
   - Cites Yartseva (2025) paper
   - Lists 6 key findings from the research

2. **Fundamental Analysis Section**
   - FCF/Price, B/M ratio, market cap category
   - Profitability metrics (ROA, ROE, margins)
   - Growth quality (asset vs EBITDA growth)
   - Passes/fails status for each Yartseva filter (✓ or ✗)

3. **Decision Framework**
   - STEP 1: Fundamental screening (Yartseva criteria)
   - STEP 2: Entry timing (technical signals)
   - STEP 3: Decision logic (buy/hold/sell rules)

4. **Enhanced Reasoning**
   - Claude must address which filters stock passes/fails
   - Whether fundamentals support multibagger potential
   - Whether current timing is good for entry
   - Key risks and catalysts

---

### 5. Celery Tasks (`backend/app/tasks/market_data_tasks.py`)

Added background tasks for fundamental data updates:

- `update_fundamental_data()` - Update all active stocks
- `update_single_stock_fundamentals(symbol)` - Update specific stock

**Note**: Fundamental updates are SLOW due to rate limiting (~1 min per stock)

---

### 6. Testing Scripts

#### `backend/scripts/test-fundamentals.py`
Tests fundamental data fetching for a single stock.

**Usage**:
```bash
python backend/scripts/test-fundamentals.py TD.TO
```

**Output**:
- Fetches all fundamental data from Alpha Vantage
- Displays latest quarterly metrics
- Shows Yartseva multibagger metrics with ✓/✗ flags
- Calculates FCF/Price, B/M, ROA, growth rates

#### `backend/scripts/screen-multibaggers.py`
Runs multibagger screening on all stocks in database.

**Usage**:
```bash
python backend/scripts/screen-multibaggers.py 20
```

**Output**:
- Screening statistics (how many pass each filter)
- Top N candidates ranked by multibagger score
- Detailed breakdown of each candidate's metrics
- Which Yartseva filters they pass/fail
- Entry timing assessment

---

### 7. Expanded Stock Universe (`backend/scripts/init-db.py`)

Expanded from 10 to **39 TSX stocks**:

- **10 large caps** - Blue chips for reference/diversification
- **29 small & mid caps** - In the $300M-$2B multibagger range

**Sectors covered**:
- Technology (4 small caps)
- Energy & Materials (7 small caps)
- Industrials (4 small caps)
- Healthcare (3 small caps)
- Financials (3 smaller banks/lenders)
- Real Estate (3 REITs)
- Consumer (3 companies)

---

### 8. Automated Stock Discovery (`backend/app/services/stock_discovery/`)

**NEW**: Automated system to keep the stock universe fresh and current.

#### Service: `TSXStockDiscovery`

Automatically discovers and maintains the TSX stock universe:

**Features**:
- **Discover new stocks** - Checks 60+ potential TSX candidates
- **Market cap filtering** - Only adds stocks in $300M-$2B range
- **Auto-deactivation** - Removes stocks that grew too large or too small
- **Blue chip preservation** - Keeps large caps for diversification
- **Rate limiting** - Respects Alpha Vantage API limits

**Methods**:
- `discover_and_update()` - Find and add new stocks in multibagger range
- `review_existing_stocks()` - Check if existing stocks still fit criteria
- `get_discovery_stats()` - Show current universe statistics

#### Celery Tasks (`backend/app/tasks/stock_discovery_tasks.py`)

Automated periodic tasks:

- `discover_new_stocks()` - Runs monthly (1st at 4 AM)
- `review_existing_stocks()` - Runs monthly (1st at 3 AM)
- `full_universe_refresh()` - Both discovery + review

#### Manual Script (`backend/scripts/discover-stocks.py`)

Run stock discovery manually:

```bash
# Discover new stocks
python scripts/discover-stocks.py discover [max_new]

# Review existing stocks
python scripts/discover-stocks.py review

# Full refresh (both)
python scripts/discover-stocks.py refresh

# Show statistics
python scripts/discover-stocks.py stats
```

**How it works**:
1. Checks a curated list of 60+ TSX symbols
2. Fetches market cap from Alpha Vantage
3. Adds stocks in $300M-$2B range
4. Deactivates stocks outside range
5. Always keeps blue chips (big banks, etc.)

**Example output**:
```
=== TSX Stock Discovery ===
Checking 65 TSX symbols...

✓ WELL.TO: Added as small cap ($850,000,000) - WELL Health Technologies
✓ DCBO.TO: Added as small cap ($1,200,000,000) - Docebo Inc
○ SHOP.TO: Already active (large cap - blue chip)
○ XYZ.TO: Deactivated (grew too large) ($2,500,000,000)

Discovery Complete:
  Symbols checked: 65
  New stocks added: 12
  Stocks deactivated: 3
  Small caps found: 12
```

**Scheduled Tasks**:
- **Weekly**: Update fundamental data (Saturdays 2 AM)
- **Monthly**: Review existing stocks (1st of month, 3 AM)
- **Monthly**: Discover new stocks (1st of month, 4 AM)

---

## How It Works (Complete Flow)

### Phase 1: Data Collection
1. **Market data** - Daily OHLCV + technical indicators (existing)
2. **Fundamental data** - Quarterly financials from Alpha Vantage (NEW)
   - Run: `python backend/scripts/test-fundamentals.py SYMBOL`
   - Or Celery task: `update_fundamental_data()`
3. **Sentiment data** - Reddit scraping (existing, optional)

### Phase 2: Stock Screening
1. **Fundamental filters** - Apply Yartseva criteria
   - High FCF/Price (≥5%)
   - Value stock (B/M ≥ 0.40)
   - Small cap ($300M-$2B)
   - Profitable
   - No negative equity
   - Good reinvestment quality

2. **Scoring** - Calculate multibagger score (0-100)
   - Weighted by research findings
   - FCF/Price gets highest weight (40 points)

3. **Technical overlay** - Entry timing signals
   - Distance from 52-week lows
   - 6-month momentum (negative = good)
   - RSI levels

**Run screening**:
```bash
python backend/scripts/screen-multibaggers.py
```

### Phase 3: Claude Analysis
1. **Context assembly** - For each stock:
   - Portfolio status
   - Fundamental metrics (FCF/P, B/M, ROA, etc.)
   - Which Yartseva filters it passes
   - Technical indicators
   - Sentiment data

2. **AI decision** - Claude uses hybrid approach:
   - Evaluates fundamental quality
   - Checks entry timing
   - Provides BUY/HOLD/SELL recommendation
   - Detailed reasoning citing specific metrics

3. **Manual review** - User reviews recommendation
   - Claude provides suggested action
   - User decides whether to execute

---

## Database Schema

```sql
-- New tables
CREATE TABLE fundamental_data_quarterly (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    fiscal_date DATE NOT NULL,

    -- Market data
    market_cap FLOAT,
    enterprise_value FLOAT,

    -- Balance sheet
    total_assets FLOAT,
    total_equity FLOAT,
    book_value_per_share FLOAT,
    total_debt FLOAT,
    cash_and_equivalents FLOAT,

    -- Income statement
    revenue FLOAT,
    operating_income FLOAT,
    ebitda FLOAT,
    net_income FLOAT,

    -- Cash flow
    operating_cash_flow FLOAT,
    free_cash_flow FLOAT,
    capital_expenditures FLOAT,

    -- Yartseva's key metrics
    fcf_price_ratio FLOAT,      -- STRONGEST PREDICTOR
    book_to_market FLOAT,        -- Value factor
    roa FLOAT,                   -- Profitability
    roe FLOAT,
    ebitda_margin FLOAT,
    ebit_margin FLOAT,

    -- Growth metrics
    asset_growth_rate FLOAT,
    ebitda_growth_rate FLOAT,
    revenue_growth_rate FLOAT,

    -- Quality flags
    has_negative_equity BOOLEAN,
    reinvestment_quality_flag BOOLEAN,
    is_profitable BOOLEAN,

    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX ix_fundamentals_symbol_date
    ON fundamental_data_quarterly(stock_id, fiscal_date);
```

---

## Next Steps

### 1. Run Database Migration
```bash
# If using Docker
docker-compose exec backend alembic upgrade head

# Or provide connection string for local migration
```

### 2. Populate Fundamental Data
```bash
# Test single stock
docker-compose exec backend python scripts/test-fundamentals.py TD.TO

# Or update all stocks (slow - ~1 min per stock)
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.tasks.market_data_tasks import update_fundamental_data
update_fundamental_data()
"
```

### 3. Run Multibagger Screening
```bash
docker-compose exec backend python scripts/screen-multibaggers.py 20
```

### 4. Discover New TSX Stocks (Optional but Recommended)
```bash
# Run stock discovery to find new small caps
docker-compose exec backend python scripts/discover-stocks.py discover 20

# This will:
# - Check 60+ potential TSX candidates
# - Add stocks in $300M-$2B range
# - Skip stocks outside multibagger range
# - Takes ~10-20 minutes due to API rate limits
```

### 5. Test Claude Analysis
```bash
# Trigger analysis for a specific stock
# The analysis will now include fundamental metrics
docker-compose exec backend python -c "
from app.database import get_db_context
from app.models import User
from app.services.chat import ClaudeTrader

with get_db_context() as db:
    user = db.query(User).first()
    trader = ClaudeTrader(db, user)
    decision = trader.analyze_symbol('WELL.TO')  # Small cap tech stock
    print(f'Decision: {decision.decision}')
    print(f'Confidence: {decision.confidence}')
    print(f'Reasoning: {decision.reasoning[:500]}...')
"
```

### 6. Keep Stock Universe Fresh (Automated)

The system automatically runs these tasks:

- **Weekly (Saturdays 2 AM)**: Update fundamental data for all stocks
- **Monthly (1st at 3 AM)**: Review existing stocks, deactivate if outside range
- **Monthly (1st at 4 AM)**: Discover new stocks in multibagger range

**Manual refresh**:
```bash
# Full universe refresh (review + discover)
docker-compose exec backend python scripts/discover-stocks.py refresh
```

---

## Key Files Modified/Created

### Models
- ✅ **NEW**: `backend/app/models/fundamentals.py`
- ✅ Modified: `backend/app/models/stock.py` (added relationships)
- ✅ Modified: `backend/app/models/__init__.py` (exports)

### Services
- ✅ Modified: `backend/app/services/market_data/alpha_vantage.py` (added fundamental methods)
- ✅ **NEW**: `backend/app/services/screening/multibagger_screener.py`
- ✅ **NEW**: `backend/app/services/screening/__init__.py`
- ✅ **NEW**: `backend/app/services/stock_discovery/tsx_discovery.py`
- ✅ **NEW**: `backend/app/services/stock_discovery/__init__.py`
- ✅ Modified: `backend/app/services/chat/claude_trader.py` (hybrid prompt)

### Tasks
- ✅ Modified: `backend/app/tasks/market_data_tasks.py` (added fundamental tasks)
- ✅ **NEW**: `backend/app/tasks/stock_discovery_tasks.py` (discovery automation)
- ✅ Modified: `backend/app/tasks/celery_app.py` (added periodic discovery tasks)

### Scripts
- ✅ **NEW**: `backend/scripts/test-fundamentals.py`
- ✅ **NEW**: `backend/scripts/screen-multibaggers.py`
- ✅ **NEW**: `backend/scripts/discover-stocks.py`
- ✅ Modified: `backend/scripts/init-db.py` (expanded to 39 stocks)

### Migrations
- ✅ **NEW**: `backend/alembic/versions/2026_01_19_2230-add_fundamental_data_tables.py`

### Documentation
- ✅ **NEW**: `YARTSEVA_IMPLEMENTATION.md` (this file)

---

## Theoretical Foundation

### Why This Works (Per Yartseva 2025)

1. **FCF/Price is the strongest predictor** because:
   - Cash flow is harder to manipulate than earnings
   - High FCF yield = company generates cash relative to price
   - Provides downside protection (value floor)
   - Enables reinvestment for growth

2. **Book-to-Market > 0.40 with profitability** because:
   - Combines value (low price relative to book) with quality (profitable)
   - "Growth stocks" with low B/M rarely become multibaggers
   - High B/M = margin of safety

3. **Small caps ($300M-$2B)** because:
   - Easier to grow from $500M to $5B than $50B to $500B
   - Less analyst coverage = more inefficiencies
   - Higher volatility allows for larger moves
   - But not micro-caps (<$300M) due to liquidity issues

4. **Reinvestment quality** because:
   - Asset growth > EBITDA growth = wasteful capital allocation
   - Growing assets without growing earnings destroys value
   - Disciplined reinvestment = compounding returns

5. **Entry timing near lows with negative momentum** because:
   - Mean reversion opportunity (contrary to trend following)
   - Stocks overshoot on the downside
   - Negative sentiment creates entry points
   - Patient capital gets rewarded

### What Doesn't Work (Surprising Findings)

- **Earnings growth** - NOT predictive (only cash flow matters)
- **High P/E ratios** - Growth stocks without cash flow rarely sustain
- **Momentum following** - Buying at highs underperforms
- **Large caps** - Scale limits upside potential
- **Asset-heavy growth** - Building assets faster than earnings is negative

---

## Limitations & Caveats

### Data Quality
- Alpha Vantage free tier: 5 calls/min (slow updates)
- Some TSX stocks may have limited fundamental data
- Quarterly data has reporting lag (up to 45 days)

### Screening Accuracy
- Fundamentals predict long-term potential, not timing
- Many stocks pass filters but don't become multibaggers
- False positives are common (need diversification)

### Time Horizon
- Multibaggers take YEARS to develop (median: 5-7 years)
- Not a day-trading or swing-trading system
- Requires patience and conviction

### Survivorship Bias
- Research analyzed successful multibaggers
- Many stocks with similar metrics may fail
- Position sizing and risk management critical

---

## Risk Management

Even with strong fundamentals, implement proper risk controls:

1. **Position sizing**: 15-25% max per position
2. **Diversification**: Hold 5-10 positions minimum
3. **Stop losses**: 5-10% below entry (fundamentals can change)
4. **Rebalancing**: Review quarterly, sell losers, add to winners
5. **Patience**: Hold for years, not months

---

## Performance Expectations

Based on Yartseva's research:

- **Median multibagger**: 10x return over 5-7 years (48% CAGR)
- **Hit rate**: ~5-10% of screened stocks become multibaggers
- **False positives**: Many stocks pass filters but underperform
- **Concentration**: Top performers drive majority of returns

**Portfolio approach**:
- Screen for 20-30 candidates
- Buy 5-10 positions
- Expect 1-2 to become multibaggers
- Others may be breakeven or small losses
- Winner(s) drive overall portfolio return

---

## References

**Yartseva, A. (2025)**. "The Alchemy of Multibagger Stocks: A Fresh Perspective on Growth and Value Investing." CAFE Working Paper 33, University of Reading.

**Key findings cited**:
- FCF/Price coefficients: 46-82 (Table 3-5)
- Book-to-Market threshold: 0.40 (Table 1-2)
- Median market cap: $348M (Table 1)
- Asset growth vs EBITDA growth: Investment dummy coefficient -4 to -11 (Table 4)
- Momentum effects: 3-6 month negative momentum positive predictor (Table 5)

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f backend`
2. Review API docs: http://localhost:8000/docs
3. Test individual components with provided scripts
4. Database inspection: `docker-compose exec postgres psql -U postgres -d tsx_trader`

---

**Implementation completed**: January 19, 2026
**Status**: Ready for testing and database migration
