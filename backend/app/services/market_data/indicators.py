import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange


class TechnicalIndicators:
    """Calculate technical indicators for market data"""

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators

        Args:
            df: DataFrame with columns [open, high, low, close, volume]

        Returns:
            DataFrame with additional indicator columns
        """
        df = df.copy()

        # Simple Moving Averages
        df["sma_20"] = SMAIndicator(close=df["close"], window=20).sma_indicator()
        df["sma_50"] = SMAIndicator(close=df["close"], window=50).sma_indicator()
        df["sma_200"] = SMAIndicator(close=df["close"], window=200).sma_indicator()

        # Exponential Moving Averages
        df["ema_12"] = EMAIndicator(close=df["close"], window=12).ema_indicator()
        df["ema_26"] = EMAIndicator(close=df["close"], window=26).ema_indicator()

        # RSI
        df["rsi_14"] = RSIIndicator(close=df["close"], window=14).rsi()

        # MACD
        macd = MACD(close=df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        # Bollinger Bands
        bollinger = BollingerBands(close=df["close"], window=20, window_dev=2)
        df["bollinger_upper"] = bollinger.bollinger_hband()
        df["bollinger_middle"] = bollinger.bollinger_mavg()
        df["bollinger_lower"] = bollinger.bollinger_lband()

        # Average True Range
        df["atr_14"] = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=14
        ).average_true_range()

        return df

    @staticmethod
    def get_signal(df: pd.DataFrame) -> str:
        """Generate a simple trading signal based on indicators

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if df.empty or len(df) < 2:
            return "neutral"

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        signals = []

        # RSI signal
        if pd.notna(latest["rsi_14"]):
            if latest["rsi_14"] < 30:
                signals.append("bullish")  # Oversold
            elif latest["rsi_14"] > 70:
                signals.append("bearish")  # Overbought

        # MACD signal
        if pd.notna(latest["macd"]) and pd.notna(previous["macd"]):
            if (
                previous["macd"] < previous["macd_signal"]
                and latest["macd"] > latest["macd_signal"]
            ):
                signals.append("bullish")  # Bullish crossover
            elif (
                previous["macd"] > previous["macd_signal"]
                and latest["macd"] < latest["macd_signal"]
            ):
                signals.append("bearish")  # Bearish crossover

        # Moving average signal
        if pd.notna(latest["sma_20"]) and pd.notna(latest["sma_50"]):
            if latest["close"] > latest["sma_20"] > latest["sma_50"]:
                signals.append("bullish")
            elif latest["close"] < latest["sma_20"] < latest["sma_50"]:
                signals.append("bearish")

        # Count signals
        if not signals:
            return "neutral"

        bullish_count = signals.count("bullish")
        bearish_count = signals.count("bearish")

        if bullish_count > bearish_count:
            return "bullish"
        elif bearish_count > bullish_count:
            return "bearish"
        else:
            return "neutral"
