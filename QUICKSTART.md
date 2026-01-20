# Quick Start Guide

## Prerequisites

Before starting, obtain these API keys:

1. **Claude API Key**: https://console.anthropic.com/
2. **Alpha Vantage API Key**: https://www.alphavantage.co/support/#api-key (free tier available)
3. **Reddit API Credentials**: https://www.reddit.com/prefs/apps
4. **Questrade Practice Account**: https://www.questrade.com/api/home (for testing)

## Setup Steps

### 1. Configure Environment

```bash
cd tsx-trader
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
SECRET_KEY=your-secret-key-here
CLAUDE_API_KEY=your-claude-key
ALPHA_VANTAGE_API_KEY=your-av-key
REDDIT_CLIENT_ID=your-reddit-id
REDDIT_CLIENT_SECRET=your-reddit-secret
QUESTRADE_CLIENT_ID=your-questrade-id
QUESTRADE_CLIENT_SECRET=your-questrade-secret
```

### 2. Run Setup Script

```bash
./scripts/setup.sh
```

This will:
- Start PostgreSQL and Redis
- Run database migrations
- Start all services

### 3. Initialize Sample Data

```bash
docker-compose exec backend python scripts/init-db.py
```

### 4. Access Application

- **API Documentation**: http://localhost:8000/docs
- **Backend API**: http://localhost:8000

### 5. Create Account

```bash
# Register via API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your-password"}'

# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your-password"}'
```

### 6. Connect Questrade (Optional)

```bash
# Get OAuth URL
curl http://localhost:8000/api/v1/questrade/authorize-url

# Visit the URL in browser to complete OAuth flow
```

### 7. Test Market Data Update

```bash
# Trigger manual market data update
docker-compose exec backend python -c "
from app.database import get_db_context
from app.tasks.market_data_tasks import update_market_data
update_market_data()
"
```

### 8. Test Trading Analysis

```bash
# Run Claude analysis for a user
docker-compose exec backend python -c "
from app.database import get_db_context
from app.models import User
from app.services.chat import ClaudeTrader
import json

with get_db_context() as db:
    user = db.query(User).first()
    if user:
        trader = ClaudeTrader(db, user)
        decision = trader.analyze_symbol('TD.TO')
        print(f'Symbol: TD.TO')
        print(f'Decision: {decision.decision}')
        print(f'Confidence: {decision.confidence}')
        print(f'Reasoning: {decision.reasoning}')
        if decision.suggested_action:
            action = json.loads(decision.suggested_action)
            print(f'Suggested: Buy {action.get(\"quantity\")} shares at \${action.get(\"entry_price\")}')
"
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
```

### Check Celery Tasks

```bash
# View active tasks
docker-compose exec celery_worker celery -A app.tasks.celery_app inspect active

# View scheduled tasks
docker-compose exec celery_beat celery -A app.tasks.celery_app inspect scheduled
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d tsx_trader

# Common queries
SELECT symbol, name FROM stocks;
SELECT * FROM users;
SELECT decision, confidence, reasoning FROM trading_decisions ORDER BY created_at DESC LIMIT 5;
```

## Viewing Recommendations

### Get Latest Recommendations via API

```bash
# Get your auth token first (after registering/logging in)
TOKEN="your-jwt-token-here"

# Latest recommendations
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/recommendations/latest

# High-confidence actionable recommendations
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/recommendations/actionable
```

### Trigger Analysis Manually

```bash
docker-compose exec backend python -c "
from app.database import get_db_context
from app.models import TradingDecision, Stock, User
from app.services.chat import ClaudeTrader

with get_db_context() as db:
    user = db.query(User).first()
    if user:
        trader = ClaudeTrader(db, user)
        decisions = trader.analyze_portfolio()
        print(f'Analyzed {len(decisions)} positions')
"
```

### View Recommendations in Database

```bash
docker-compose exec backend python -c "
from app.database import get_db_context
from app.models import TradingDecision, Stock
from sqlalchemy import desc
import json

with get_db_context() as db:
    decisions = (
        db.query(TradingDecision, Stock)
        .join(Stock)
        .filter(TradingDecision.action_taken == False)
        .order_by(desc(TradingDecision.confidence))
        .limit(5)
        .all()
    )

    for decision, stock in decisions:
        print(f'\n{'='*60}')
        print(f'Symbol: {stock.symbol}')
        print(f'Decision: {decision.decision.upper()}')
        print(f'Confidence: {decision.confidence:.1%}')
        print(f'Reasoning: {decision.reasoning[:200]}...')

        if decision.suggested_action:
            action = json.loads(decision.suggested_action)
            print(f'\nSuggested Action:')
            print(f'  Quantity: {action.get(\"quantity\")} shares')
            print(f'  Entry: \${action.get(\"entry_price\"):.2f}')
            print(f'  Stop Loss: \${action.get(\"stop_loss_price\"):.2f}')
            print(f'  Take Profit: \${action.get(\"take_profit_price\"):.2f}')
"
```

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose ps

# Restart specific service
docker-compose restart backend

# Full restart
docker-compose down
docker-compose up -d
```

### Database Issues

```bash
# Reset database (WARNING: Deletes all data)
docker-compose down -v
docker-compose up -d postgres redis
sleep 5
docker-compose run --rm backend alembic upgrade head
```

### Celery Tasks Not Running

```bash
# Check Redis connection
docker-compose exec backend python -c "
import redis
from app.config import get_settings
settings = get_settings()
r = redis.from_url(settings.REDIS_URL)
r.ping()
print('Redis connection: OK')
"

# Restart workers
docker-compose restart celery_worker celery_beat
```

## Next Steps

1. **Add More Stocks**: Edit `scripts/init-db.py` and add symbols
2. **Adjust Risk Parameters**: Modify settings in user dashboard
3. **Review Claude Recommendations**: Use API or check trading_decisions table
4. **Execute Trades Manually**: Review suggestions and place orders in Questrade
5. **Monitor Performance**: Track portfolio_snapshots table

## Daily Workflow

1. **Morning** (9:30 AM EST): Check recommendations from morning analysis
2. **Review**: Read Claude's reasoning and suggested action
3. **Execute**: Place orders manually in Questrade if you agree
4. **Afternoon** (4:00 PM EST): Check closing analysis
5. **Track**: Monitor positions and adjust stops in Questrade

## Support

- Check logs: `docker-compose logs -f`
- Review API docs: http://localhost:8000/docs
- Database inspection: `docker-compose exec postgres psql -U postgres -d tsx_trader`
