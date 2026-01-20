from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as VaderAnalyzer
from typing import Dict


class SentimentAnalyzer:
    """Wrapper for sentiment analysis using VADER"""

    def __init__(self):
        self.analyzer = VaderAnalyzer()

    def analyze(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores:
            - compound: Overall sentiment (-1 to 1)
            - positive: Positive score (0 to 1)
            - negative: Negative score (0 to 1)
            - neutral: Neutral score (0 to 1)
        """
        scores = self.analyzer.polarity_scores(text)
        return {
            "compound": scores["compound"],
            "positive": scores["pos"],
            "negative": scores["neg"],
            "neutral": scores["neu"],
        }

    def classify(self, compound_score: float) -> str:
        """Classify sentiment based on compound score

        Args:
            compound_score: Compound sentiment score (-1 to 1)

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if compound_score >= 0.05:
            return "bullish"
        elif compound_score <= -0.05:
            return "bearish"
        else:
            return "neutral"
