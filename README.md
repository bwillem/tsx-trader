# TSX Multibagger Stock Trader

An AI-powered stock analysis system for finding multibagger stocks on the Toronto Stock Exchange (TSX). Based on peer-reviewed research: *"The Alchemy of Multibagger Stocks"* (Yartseva, 2025).

## 🚀 100% Automated Mode

**Set it and forget it.** This system runs completely automatically via GitHub Actions:

- ✅ **Daily**: Screens stocks using Yartseva's multibagger filters (FCF/Price, Book/Market, ROA)
- ✅ **Daily**: Claude AI analyzes top candidates and generates buy/hold/sell recommendations
- ✅ **Weekly**: Updates fundamental data (quarterly financials)
- ✅ **Monthly**: Discovers new TSX small caps ($300M-$2B range)

**See [AUTOMATION_SETUP.md](AUTOMATION_SETUP.md) for one-time setup (5 minutes) → never run scripts again!**

## ⚠️ ANALYSIS-ONLY MODE (Questrade Compliant)

This system operates in **analysis-only mode**. Claude provides trading recommendations with detailed reasoning, but **does NOT execute trades automatically**. You review and execute each trade manually through your broker.

See [ANALYSIS_ONLY_MODE.md](ANALYSIS_ONLY_MODE.md) for details.

## Features

### 🎯 Multibagger Screening (Yartseva 2025)
- **FCF/Price ratio** (free cash flow yield) - strongest predictor of 10x returns
- **Book-to-Market ratio** > 0.40 - value factor
- **Small cap focus** ($300M-$2B) - sweet spot for multibaggers
- **Reinvestment quality** - asset growth ≤ EBITDA growth
- **Entry timing** - near 52-week lows with negative momentum

### 🤖 AI Trading Analysis
- **Hybrid approach**: Fundamental + Technical + Sentiment analysis
- **Claude Sonnet 4.5**: Analyzes top candidates with detailed reasoning
- **Risk management**: Position sizing, stop-loss calculations, risk validation
- **Automated screening**: Runs 2x daily (market open & close)

### 📊 Data Collection
- **Alpha Vantage**: Quarterly financials, market data, technical indicators
- **Reddit sentiment**: r/CanadianInvestor, r/Baystreetbets
- **Stock discovery**: Automated monthly updates to stock universe

### 📈 Portfolio Integration
- **Questrade API**: OAuth authentication, portfolio monitoring
- **Manual execution**: Review recommendations, execute trades yourself
- **REST API**: Programmatic access to all data

## Architecture

- **Backend**: Python, FastAPI, SQLAlchemy, Celery
- **Database**: PostgreSQL with Redis for caching/queues
- **AI**: Claude API (Sonnet 4.5) for trading analysis
- **Broker**: Questrade API

## Deployment Options

### Option 1: 🤖 Fully Automated via GitHub Actions (Recommended)

**Zero ongoing work required.** Run everything in the cloud - never touch a script again.

**What runs automatically:**
- Hourly: Market data updates
- Every 30 min: Sentiment analysis
- 2x daily: Multibagger screening + Claude analysis
- Weekly: Fundamental data updates
- Monthly: Stock discovery

**Prerequisites:**
- GitHub account (free)
- Neon PostgreSQL database (free tier - already set up)
- API keys (Claude, Alpha Vantage, Reddit)

**Cost:** ~$1-2/month (Claude API only)

**Setup time:** 5 minutes

**See [AUTOMATION_SETUP.md](AUTOMATION_SETUP.md) for complete guide.**

### Option 2: Local Docker (Development/Testing)

Run everything on your laptop for development or testing.

**Prerequisites**:
- Docker and Docker Compose
- API Keys:
  - Claude API key (from Anthropic)
  - Alpha Vantage API key (free tier available)
  - Reddit API credentials
  - Questrade API credentials

**Note**: Your laptop must be running at 9:30 AM and 4:00 PM EST for scheduled analysis.

### Setup

1. Clone the repository:
   ```bash
   cd tsx-trader
   ```

2. Copy environment template:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your API keys

4. Start services:
   ```bash
   docker-compose up -d
   ```

5. Run database migrations:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

6. Access the application:
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Initial Database Setup

```bash
# Create initial migration
docker-compose exec backend alembic revision --autogenerate -m "initial schema"

# Apply migrations
docker-compose exec backend alembic upgrade head
```

## Configuration

### Risk Parameters (in `.env`)

```env
# Position Sizing
DEFAULT_POSITION_SIZE_PCT=20          # 20% of portfolio per position
MAX_OPEN_POSITIONS=10                 # Maximum concurrent positions

# Risk Management
DEFAULT_STOP_LOSS_PCT=5               # 5% stop loss
MIN_CASH_RESERVE_PCT=10               # Keep 10% in cash
MIN_RISK_REWARD_RATIO=2.0             # Minimum 2:1 risk/reward

# Circuit Breakers
DAILY_LOSS_LIMIT_PCT=5                # Halt trading if down 5% in a day

# Trading Mode
PAPER_TRADING_MODE=True               # Start in paper trading mode
```

## Usage

### Connecting Questrade

1. Get the OAuth URL from the API:
   ```bash
   curl http://localhost:8000/api/v1/questrade/authorize-url
   ```
2. Visit the URL to complete OAuth flow
3. Your account will be synced automatically

### Reviewing Trading Recommendations

Claude analyzes the market on a schedule and provides recommendations.

**Quick Check** (with cloud database):
```bash
# Set your Neon database URL
export DATABASE_URL='your-neon-connection-string'

# Run the recommendation checker
python scripts/check_recommendations.py
```

**Via API** (when running backend locally):
```bash
# Get latest recommendations
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/recommendations/latest

# Get actionable recommendations (high confidence buy/sell)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/recommendations/actionable
```

**Via SQL** (Neon dashboard or any Postgres client):
```sql
SELECT s.symbol, td.decision, td.confidence, td.reasoning, td.suggested_action
FROM trading_decisions td JOIN stocks s ON td.stock_id = s.id
WHERE td.action_taken = false AND td.created_at > NOW() - INTERVAL '24 hours'
ORDER BY td.confidence DESC;
```

Then **execute manually** in Questrade if you agree with the recommendation.

See [ANALYSIS_ONLY_MODE.md](ANALYSIS_ONLY_MODE.md) for detailed workflow.

### Monitoring

- **API**: Query portfolio, positions, and recommendations via REST API
- **Scripts**: Use `scripts/check_recommendations.py` for quick recommendation views
- **Database**: Query Neon dashboard directly for detailed analysis
- **Logs**: Check backend logs (Docker) or GitHub Actions logs (cloud deployment)

## Background Tasks

Celery workers handle automated tasks:

- **Market Data Update**: Hourly during trading hours
- **Sentiment Analysis**: Every 30 minutes
- **Trading Analysis**: At market open (9:30 AM) and close (4:00 PM) EST
- **Stop-Loss Monitoring**: Every 5 minutes during trading hours

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user

### Portfolio
- `GET /api/v1/portfolio/summary` - Portfolio summary with positions
- `GET /api/v1/portfolio/history` - Historical P&L data

### Trades
- `GET /api/v1/trades/orders` - List orders
- `GET /api/v1/trades/positions` - List positions

### Questrade
- `GET /api/v1/questrade/authorize-url` - Get OAuth URL
- `GET /api/v1/questrade/accounts` - List accounts
- `GET /api/v1/questrade/accounts/{id}/positions` - Get positions

### Settings
- `GET /api/v1/settings` - Get user settings
- `PUT /api/v1/settings` - Update settings

### Recommendations
- `GET /api/v1/recommendations/latest` - Latest trading recommendations
- `GET /api/v1/recommendations/actionable` - High-confidence buy/sell recommendations
- `GET /api/v1/recommendations/{id}` - Recommendation details
- `POST /api/v1/recommendations/{id}/dismiss` - Mark as reviewed

## Development

### Running Tests

```bash
docker-compose exec backend pytest
```

### Database Migrations

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

## Architecture Details

### Trading Recommendation Flow

1. **Celery Beat** triggers trading analysis task (9:30 AM, 4:00 PM EST)
2. **ClaudeTrader** gathers context:
   - Current portfolio state from Questrade
   - Market data with technical indicators
   - Reddit sentiment analysis
3. **Claude API** analyzes data and returns recommendation with reasoning
4. **Risk Manager** validates suggested trade parameters
5. **Decision logged** to database with suggested action
6. **You review** recommendation via API or database
7. **You execute** manually in Questrade if you agree

### Risk Management

All trades go through `RiskManager.validate_trade()`:
- Position size limits
- Cash availability check
- Stop-loss requirement
- Risk/reward ratio validation
- Circuit breaker status
- Max positions limit

### Data Pipeline

1. **Alpha Vantage**: Fetches daily OHLCV data
2. **Technical Indicators**: Calculates SMA, EMA, RSI, MACD, Bollinger Bands, ATR
3. **Reddit Scraper**: Extracts stock mentions and sentiment
4. **VADER Sentiment**: Scores post sentiment (-1 to 1)
5. **Database Storage**: All data timestamped and indexed

## Safety Features

- **Paper Trading**: Test without real money
- **Circuit Breakers**: Automatic trading halt on excessive losses
- **Stop-Loss Enforcement**: Required for all positions
- **Position Size Limits**: Prevent over-concentration
- **Cash Reserves**: Maintain liquidity
- **Decision Logging**: Full audit trail of Claude's reasoning

## Troubleshooting

### Common Issues

1. **Alpha Vantage Rate Limits**: Free tier allows 5 calls/minute. Tasks automatically rate-limit.

2. **Questrade Token Expired**: Tokens auto-refresh. If issues persist, reconnect in settings.

3. **Celery Tasks Not Running**: Check Redis connection and celery worker logs.

4. **Database Connection Issues**: Ensure PostgreSQL is healthy: `docker-compose ps`

## Disclaimer

⚠️ **Analysis Only**: This system provides trading analysis and recommendations. It does NOT execute trades automatically. You are responsible for reviewing all recommendations and making your own trading decisions.

⚠️ **Trading Risk**: Trading stocks involves substantial risk of loss. Past performance does not guarantee future results. Only trade with capital you can afford to lose.

⚠️ **Questrade Compliance**: This system operates in analysis-only mode to comply with Questrade's API Terms of Service. All trades must be executed manually.

⚠️ **No Warranty**: This software is provided "as is" without warranty of any kind. Use at your own risk.

⚠️ **Not Financial Advice**: This is not financial advice. AI recommendations should not be blindly followed. Consult a licensed financial advisor before making investment decisions.

## License

MIT License - see LICENSE file for details.
