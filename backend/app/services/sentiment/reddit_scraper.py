import praw
import re
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.config import get_settings
from app.models.sentiment import SentimentPost, SentimentStockMention
from app.models.stock import Stock

settings = get_settings()


class RedditScraper:
    """Scrape Reddit posts for stock mentions and sentiment"""

    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

        # Common TSX ticker patterns
        self.ticker_pattern = re.compile(
            r"\b([A-Z]{1,5})\.(TO|TSX)\b|\$([A-Z]{1,5})"
        )

    def extract_tickers(self, text: str) -> List[str]:
        """Extract TSX ticker symbols from text

        Args:
            text: Text to search for tickers

        Returns:
            List of normalized ticker symbols (e.g., ['TD.TO', 'SHOP.TO'])
        """
        matches = self.ticker_pattern.findall(text.upper())
        tickers = []

        for match in matches:
            if match[0]:  # Format: TICKER.TO or TICKER.TSX
                tickers.append(f"{match[0]}.TO")
            elif match[2]:  # Format: $TICKER
                tickers.append(f"{match[2]}.TO")

        return list(set(tickers))  # Remove duplicates

    def calculate_sentiment(self, text: str) -> Dict[str, float]:
        """Calculate sentiment scores for text

        Returns:
            Dictionary with compound, positive, negative, neutral scores
        """
        scores = self.sentiment_analyzer.polarity_scores(text)
        return {
            "compound": scores["compound"],
            "positive": scores["pos"],
            "negative": scores["neg"],
            "neutral": scores["neu"],
        }

    def scrape_subreddit(
        self, db: Session, subreddit_name: str, limit: int = 100
    ) -> int:
        """Scrape posts from a subreddit

        Args:
            db: Database session
            subreddit_name: Name of subreddit (e.g., 'CanadianInvestor')
            limit: Number of posts to fetch

        Returns:
            Number of new posts processed
        """
        subreddit = self.reddit.subreddit(subreddit_name)
        new_posts = 0

        # Fetch hot and new posts
        posts = list(subreddit.hot(limit=limit // 2)) + list(
            subreddit.new(limit=limit // 2)
        )

        for submission in posts:
            # Check if already processed
            existing = (
                db.query(SentimentPost)
                .filter(SentimentPost.source_id == submission.id)
                .first()
            )
            if existing:
                continue

            # Combine title and selftext
            full_text = f"{submission.title} {submission.selftext}"

            # Extract tickers
            tickers = self.extract_tickers(full_text)
            if not tickers:
                continue  # Skip posts without stock mentions

            # Calculate sentiment
            sentiment = self.calculate_sentiment(full_text)

            # Create post record
            post = SentimentPost(
                source="reddit",
                source_id=submission.id,
                title=submission.title,
                content=submission.selftext[:5000],  # Limit content length
                author=str(submission.author) if submission.author else None,
                url=f"https://reddit.com{submission.permalink}",
                published_at=datetime.fromtimestamp(submission.created_utc),
                sentiment_compound=sentiment["compound"],
                sentiment_positive=sentiment["positive"],
                sentiment_negative=sentiment["negative"],
                sentiment_neutral=sentiment["neutral"],
                upvotes=submission.score,
                comments=submission.num_comments,
            )
            db.add(post)
            db.flush()

            # Create stock mention records
            for ticker in tickers:
                # Get or create stock
                stock = db.query(Stock).filter(Stock.symbol == ticker).first()
                if not stock:
                    stock = Stock(symbol=ticker, name=ticker, exchange="TSX")
                    db.add(stock)
                    db.flush()

                # Count mentions
                mention_count = full_text.upper().count(ticker.replace(".TO", ""))

                mention = SentimentStockMention(
                    post_id=post.id,
                    stock_id=stock.id,
                    mention_count=mention_count,
                    sentiment_score=sentiment["compound"],
                )
                db.add(mention)

            new_posts += 1

        db.commit()
        print(f"Scraped {new_posts} new posts from r/{subreddit_name}")
        return new_posts

    def scrape_all_subreddits(self, db: Session) -> Dict[str, int]:
        """Scrape all configured subreddits

        Returns:
            Dictionary mapping subreddit name to number of new posts
        """
        results = {}

        for subreddit_name in settings.SENTIMENT_SUBREDDITS:
            try:
                count = self.scrape_subreddit(db, subreddit_name)
                results[subreddit_name] = count
            except Exception as e:
                print(f"Error scraping r/{subreddit_name}: {e}")
                results[subreddit_name] = 0

        return results

    def get_stock_sentiment_summary(
        self, db: Session, symbol: str, days: int = 7
    ) -> Dict:
        """Get sentiment summary for a stock

        Args:
            db: Database session
            symbol: Stock symbol (e.g., 'TD.TO')
            days: Number of days to look back

        Returns:
            Dictionary with sentiment metrics
        """
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            return {
                "mention_count": 0,
                "avg_sentiment": 0.0,
                "bullish_ratio": 0.0,
            }

        # Get mentions from last N days
        since_date = datetime.utcnow() - timedelta(days=days)

        mentions = (
            db.query(SentimentStockMention)
            .join(SentimentPost)
            .filter(
                SentimentStockMention.stock_id == stock.id,
                SentimentPost.published_at >= since_date,
            )
            .all()
        )

        if not mentions:
            return {
                "mention_count": 0,
                "avg_sentiment": 0.0,
                "bullish_ratio": 0.0,
            }

        # Calculate metrics
        total_mentions = sum(m.mention_count for m in mentions)
        avg_sentiment = sum(m.sentiment_score or 0 for m in mentions) / len(mentions)
        bullish_count = sum(1 for m in mentions if (m.sentiment_score or 0) > 0.05)
        bullish_ratio = bullish_count / len(mentions) if mentions else 0

        return {
            "mention_count": total_mentions,
            "avg_sentiment": round(avg_sentiment, 3),
            "bullish_ratio": round(bullish_ratio, 3),
            "post_count": len(mentions),
        }
