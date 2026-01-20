from celery import shared_task
from app.database import get_db_context
from app.services.sentiment import RedditScraper


@shared_task(name="app.tasks.sentiment_tasks.update_sentiment_data")
def update_sentiment_data():
    """Scrape Reddit for sentiment data"""
    print("Starting sentiment data update...")

    with get_db_context() as db:
        scraper = RedditScraper()

        try:
            results = scraper.scrape_all_subreddits(db)
            print(f"Sentiment update complete: {results}")
            return {"status": "success", "results": results}
        except Exception as e:
            print(f"Error updating sentiment data: {e}")
            return {"status": "error", "error": str(e)}
