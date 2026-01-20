from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "TSX Trader"
    DEBUG: bool = True
    SECRET_KEY: str = ""  # Optional for migrations, required for JWT operations

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API Keys (optional for migrations, required for runtime)
    CLAUDE_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "TSXTrader/1.0"

    # Questrade
    QUESTRADE_CLIENT_ID: str = ""
    QUESTRADE_CLIENT_SECRET: str = ""
    QUESTRADE_REDIRECT_URI: str = "http://localhost:8000/api/v1/questrade/callback"
    QUESTRADE_API_URL: str = "https://api01.iq.questrade.com"
    QUESTRADE_LOGIN_URL: str = "https://login.questrade.com"

    # Trading Parameters
    PAPER_TRADING_MODE: bool = True
    DEFAULT_POSITION_SIZE_PCT: float = 20.0
    DEFAULT_STOP_LOSS_PCT: float = 5.0
    DAILY_LOSS_LIMIT_PCT: float = 5.0
    MAX_OPEN_POSITIONS: int = 10
    MIN_CASH_RESERVE_PCT: float = 10.0
    MIN_RISK_REWARD_RATIO: float = 2.0

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Claude
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    CLAUDE_MAX_TOKENS: int = 4096

    # Market Data
    ALPHA_VANTAGE_RATE_LIMIT: int = 5  # calls per minute
    MARKET_DATA_UPDATE_INTERVAL: int = 3600  # seconds

    # Sentiment Analysis
    SENTIMENT_UPDATE_INTERVAL: int = 1800  # 30 minutes
    SENTIMENT_SUBREDDITS: list[str] = ["CanadianInvestor", "Baystreetbets"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
