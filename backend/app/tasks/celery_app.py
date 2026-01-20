from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tsx_trader",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.market_data_tasks",
        "app.tasks.sentiment_tasks",
        "app.tasks.trading_tasks",
        "app.tasks.stock_discovery_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Toronto",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    # Update market data every hour during trading hours
    "update-market-data-hourly": {
        "task": "app.tasks.market_data_tasks.update_market_data",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Update sentiment data every 30 minutes
    "update-sentiment-data": {
        "task": "app.tasks.sentiment_tasks.update_sentiment_data",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    # Run trading analysis at market open (9:30 AM EST)
    "trading-analysis-morning": {
        "task": "app.tasks.trading_tasks.run_trading_analysis",
        "schedule": crontab(hour=9, minute=30, day_of_week="1-5"),  # Weekdays at 9:30 AM
    },
    # Run trading analysis at market close (4:00 PM EST)
    "trading-analysis-close": {
        "task": "app.tasks.trading_tasks.run_trading_analysis",
        "schedule": crontab(hour=16, minute=0, day_of_week="1-5"),  # Weekdays at 4:00 PM
    },
    # Monitor stop losses every 5 minutes during trading hours
    "monitor-stop-losses": {
        "task": "app.tasks.trading_tasks.monitor_stop_losses",
        "schedule": crontab(minute="*/5", hour="9-16", day_of_week="1-5"),  # Every 5 min, 9 AM-4 PM
    },
    # Update fundamental data weekly (slow - ~1 min per stock)
    "update-fundamental-data-weekly": {
        "task": "app.tasks.market_data_tasks.update_fundamental_data",
        "schedule": crontab(hour=2, minute=0, day_of_week=6),  # Saturdays at 2 AM
    },
    # Review existing stocks monthly (check if still in range)
    "review-stocks-monthly": {
        "task": "app.tasks.stock_discovery_tasks.review_existing_stocks",
        "schedule": crontab(hour=3, minute=0, day_of_month=1),  # 1st of month at 3 AM
    },
    # Discover new stocks monthly (add new candidates)
    "discover-new-stocks-monthly": {
        "task": "app.tasks.stock_discovery_tasks.discover_new_stocks",
        "schedule": crontab(hour=4, minute=0, day_of_month=1),  # 1st of month at 4 AM
    },
}
