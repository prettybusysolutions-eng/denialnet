from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID: Optional[str] = None
    ADMIN_API_KEY: Optional[str] = None  # Admin auth for /admin/* endpoints
    LEARN_DOMAIN: str = "https://denialnet.onrender.com"
    QUERY_COST_CENTS: int = 75  # $0.75 default unlock
    MIN_CREDITS_CENTS: int = 500  # $5 minimum topup
    CONTRIBUTOR_SPLIT: float = 0.70  # 70% to contributor
    NETWORK_SPLIT: float = 0.30  # 30% to network ops
    MIN_SAMPLE_SIZE: int = 3  # patterns with fewer samples auto-deactivated
    RATE_LIMIT_SEARCH: int = 20      # max search queries per window
    RATE_LIMIT_SUBMIT: int = 10      # max pattern submissions per window
    RATE_LIMIT_WINDOW_MINUTES: int = 60  # rolling window

    class Config:
        env_prefix = "DENIALNET_"
        extra = "ignore"


settings = Settings()
