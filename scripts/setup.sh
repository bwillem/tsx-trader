#!/bin/bash

# TSX Trader Setup Script

echo "=== TSX Trader Setup ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your API keys:"
    echo "   - CLAUDE_API_KEY"
    echo "   - ALPHA_VANTAGE_API_KEY"
    echo "   - REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET"
    echo "   - QUESTRADE_CLIENT_ID and QUESTRADE_CLIENT_SECRET"
    echo "   - SECRET_KEY (generate a random string)"
    echo ""
    echo "Then run this script again."
    exit 0
fi

# Check if database is already initialized
if docker-compose exec -T postgres psql -U postgres -d tsx_trader -c "SELECT 1 FROM users LIMIT 1;" 2>/dev/null; then
    echo "✓ Database already initialized"
else
    echo "Step 1: Starting database services..."
    docker-compose up -d postgres redis

    echo "Step 2: Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
            echo "✓ PostgreSQL is ready"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""

    echo "Step 3: Running database migrations..."
    docker-compose run --rm backend alembic upgrade head

    if [ $? -eq 0 ]; then
        echo "✓ Database migrations completed"
    else
        echo "✗ Database migration failed"
        exit 1
    fi

    echo "Step 4: Initializing sample stocks..."
    docker-compose run --rm backend python scripts/init-db.py
fi

# Start all services
echo "Step 5: Starting all services..."
docker-compose up -d

# Wait a bit for services to start
sleep 5

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services:"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo ""
echo "Celery Services:"
echo "  Worker:  Processing tasks"
echo "  Beat:    Scheduling tasks"
echo ""
echo "Scheduled Tasks:"
echo "  - Market data:  Every hour"
echo "  - Sentiment:    Every 30 minutes"
echo "  - Analysis:     9:30 AM & 4:00 PM EST (weekdays)"
echo ""
echo "Next steps:"
echo "  1. Register a user: POST http://localhost:8000/api/v1/auth/register"
echo "  2. View API docs: http://localhost:8000/docs"
echo "  3. Check Celery logs: docker-compose logs -f celery_worker celery_beat"
echo "  4. View recommendations: GET /api/v1/recommendations/latest"
echo ""
echo "Commands:"
echo "  View logs:    docker-compose logs -f [service]"
echo "  Stop:         docker-compose down"
echo "  Restart:      docker-compose restart [service]"
echo ""
