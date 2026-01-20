# Avantis-Style TSX Strategy

## Overview

This strategy mirrors **Avantis Investors' factor-based methodology** for Canadian stocks on the TSX. It creates a diversified small cap value portfolio suitable for core holdings, using the same academic principles as Avantis's ETFs (AVUV, AVDV).

**Key Difference from Multibagger Strategy:**
- **Avantis TSX**: Diversified factor exposure (15-25 stocks) - **Core holdings**
- **Multibagger**: Concentrated high-conviction picks (5-10 stocks) - **Satellite holdings**

---

## Academic Foundation

### Avantis Investors' Approach

Founded by ex-Dimensional Fund Advisors (DFA) executives, Avantis implements:

1. **Value Factor**: Book Equity / Market Price
2. **Profitability Factor**: Cash from Operations / Book Equity
3. **Size Factor**: Small cap tilt
4. **Quality Screens**: Positive profitability, no negative equity

### Our TSX Implementation

We've added one enhancement to Avantis's core methodology:

**FCF/Price Quality Screen** (Your Edge):
- Avantis uses operating profitability
- We add: Free Cash Flow / Price ≥ 3%
- Why: FCF is what actually flows to shareholders (higher quality metric)

---

## Screening Criteria

### Hard Filters (Must Pass All)

1. **Value**: Book-to-Market ≥ 0.40
2. **Profitability**: Operating Cash Flow / Book Equity ≥ 10%
3. **Size**: Market cap $300M - $2B
4. **Quality**:
   - Profitable (positive net income)
   - No negative equity
5. **Edge**: FCF/Price ≥ 3% (optional but recommended)

### Scoring (0-100 points)

**Value Factor (40 points max):**
- 0.40 B/P = 20 points
- 0.80+ B/P = 40 points
- Linear scaling between

**Profitability Factor (40 points max):**
- 10% Cash ROE = 20 points
- 30%+ Cash ROE = 40 points
- Linear scaling between

**Quality Bonuses (20 points):**
- Reinvestment quality: +10 points
- FCF/Price ≥ 5%: +5 points
- ROA ≥ 10%: +5 points

---

## Portfolio Construction

### Option 1: Equal Weight (Recommended)

Like most Avantis ETFs:
- Hold 15-20 stocks
- Each gets equal weight (5-6.7%)
- Rebalance quarterly
- **Pros**: Simple, diversified, lower turnover
- **Cons**: Treats all passing stocks equally

### Option 2: Factor-Weighted

Weight by composite factor score:
- Hold 15-20 stocks
- Higher scores get larger weights
- Rebalance quarterly
- **Pros**: Emphasizes strongest factor characteristics
- **Cons**: Higher concentration in top names

### Option 3: Tiered (Hybrid Approach)

Combine with Multibagger strategy:

```
CORE (60-70%): Avantis TSX
├─ 15-20 stocks
├─ Equal weighted
└─ Quarterly rebalance

SATELLITE (30-40%): Multibagger
├─ 5-10 stocks
├─ Score weighted
└─ Opportunistic rebalance
```

**Total: ~25-30 holdings with smart diversification**

---

## Usage

### Run Avantis TSX Screening

```bash
# Screen top 20 stocks
docker-compose run --rm backend python scripts/screen-avantis-tsx.py 20

# Show portfolio with weights
docker-compose run --rm backend python scripts/screen-avantis-tsx.py portfolio

# Compare both strategies
docker-compose run --rm backend python scripts/compare-strategies.py
```

### Sample Output

```
🎯 TOP 20 AVANTIS-STYLE CANDIDATES

1. WELL.TO - WELL Health Technologies
   Sector: Technology
   FACTOR SCORE: 78.5/100

   AVANTIS CORE FACTORS:
     Book-to-Price:      0.85
     Cash Profitability: 18.5% (OCF / Book Equity)

   SIZE & VALUATION:
     Market Cap:         $850,000,000
     FCF/Price:          12.5%

   QUALITY METRICS:
     ROA:                8.2%
     ROE:                15.3%
     Profitable:         ✓ Yes
     Reinvestment Quality: ✓ Good

...
```

---

## Key Metrics Explained

### Book-to-Price (Value Factor)

```
Book-to-Price = Book Equity / Market Cap
              = Total Assets - Total Liabilities / Market Cap
```

**What it measures**: How cheaply you're buying the company's net assets

**Threshold**: ≥ 0.40 means you're paying $1 for at least $0.40 of book value

**Avantis uses this**: Primary value metric (better than P/E for small caps)

### Cash Profitability (Profitability Factor)

```
Cash Profitability = Operating Cash Flow / Book Equity
```

**What it measures**: Cash return on equity (not accounting profits)

**Threshold**: ≥ 10% means the company generates $0.10 cash per $1 of equity

**Why Avantis uses this**:
- Cash is harder to manipulate than earnings
- Better predictor of returns than ROE
- Based on research by Novy-Marx (2013)

### FCF/Price (Your Edge Metric)

```
FCF/Price = Free Cash Flow / Market Cap
          = (Operating Cash Flow - CapEx) / Market Cap
```

**What it measures**: Free cash flow yield to shareholders

**Your threshold**: ≥ 3% for Avantis screening (vs 5% for Multibagger)

**Why it's your edge**: Yartseva found this is the **strongest** multibagger predictor (coefficients 46-82)

---

## Comparison to Multibagger Strategy

| Aspect | Avantis TSX | Multibagger |
|--------|-------------|-------------|
| **Philosophy** | Diversified factor exposure | Concentrated 10x bets |
| **Holdings** | 15-25 stocks | 5-10 stocks |
| **Primary Metric** | Cash profitability | FCF/Price |
| **FCF Threshold** | 3% (quality screen) | 5% (core filter) |
| **Entry Timing** | No | Yes (near lows) |
| **Rebalancing** | Quarterly | Opportunistic |
| **Risk Level** | Lower (diversified) | Higher (concentrated) |
| **Expected Return** | Consistent factor premium | Potential 10x home runs |
| **Portfolio Role** | Core (60-70%) | Satellite (30-40%) |

---

## Research Support

### Avantis's Academic Foundation

1. **Fama-French (1992)**: Size and Value factors
2. **Fama-French (2015)**: Added Profitability factor
3. **Novy-Marx (2013)**: Gross profitability predicts returns
4. **Ball et al. (2015)**: Cash-based profitability > accrual-based

### Your Enhancements

1. **Yartseva (2025)**: FCF/Price strongest multibagger predictor
2. **Your screen**: Adds FCF quality filter to Avantis's methodology

---

## Automated GitHub Actions

The Avantis-style screening runs automatically via GitHub Actions:

### Daily (9:30 AM & 4 PM EST)
- **Multibagger screening** with Claude analysis

### To Add Avantis Screening

You could create a separate workflow:

```yaml
# .github/workflows/avantis-tsx-screening.yml
on:
  schedule:
    - cron: '0 14 1 * *'  # 1st of month at 9 AM EST

jobs:
  avantis-screening:
    runs-on: ubuntu-latest
    steps:
      - name: Run Avantis TSX screening
        run: |
          cd backend
          python scripts/screen-avantis-tsx.py portfolio
```

Or just run it manually monthly when rebalancing.

---

## When to Use Each Strategy

### Use Avantis TSX When:
- ✅ You want diversified, lower-risk exposure
- ✅ Building core portfolio holdings
- ✅ You prefer systematic factor investing
- ✅ You want to mimic institutional-grade methodology
- ✅ You value consistency over home runs

### Use Multibagger When:
- ✅ You want concentrated, high-conviction picks
- ✅ Building satellite/tactical positions
- ✅ You're willing to accept higher volatility
- ✅ You're seeking potential 10x returns
- ✅ You want Claude's AI analysis on each pick

### Use Both (Recommended):
- ✅ 60-70% in Avantis TSX (stable base)
- ✅ 30-40% in Multibagger (upside potential)
- ✅ ~25-30 total holdings
- ✅ Balanced risk/reward profile

---

## Next Steps

1. **Wait for fundamental data**: The weekly workflow needs to fetch data first
   - Run manually: Actions → "Weekly Fundamental Data Update"
   - Takes ~40 minutes for 37 stocks

2. **Run comparison**: See which approach fits your style
   ```bash
   docker-compose run --rm backend python scripts/compare-strategies.py
   ```

3. **Test Avantis screening**:
   ```bash
   docker-compose run --rm backend python scripts/screen-avantis-tsx.py portfolio
   ```

4. **Decide portfolio mix**: Core/satellite allocation based on risk tolerance

5. **Set up rebalancing**: Quarterly for Avantis, opportunistic for Multibagger

---

## Bottom Line

You now have **two complementary strategies**:

1. **Avantis TSX**: Your TSX version of institutional-grade factor investing
   - Like building your own AVUV/AVDV for Canadian stocks
   - Proven academic methodology
   - Diversified, consistent returns

2. **Multibagger**: Your high-conviction 10x hunting strategy
   - Based on Yartseva's specific research
   - FCF-focused with entry timing
   - Concentrated, higher risk/reward

**Combined**, you have a sophisticated, research-backed portfolio that balances diversification with conviction.
