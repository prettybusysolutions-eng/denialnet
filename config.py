from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID: Optional[str] = None
    LEARN_DOMAIN: str = "https://denialnet.onrender.com"
    QUERY_COST_CENTS: int = 75  # $0.75 default unlock
    MIN_CREDITS_CENTS: int = 500  # $5 minimum topup
    CONTRIBUTOR_SPLIT: float = 0.70  # 70% to contributor
    NETWORK_SPLIT: float = 0.30  # 30% to network ops
    MIN_SAMPLE_SIZE: int = 3  # patterns with fewer samples auto-deactivated

    class Config:
        env_prefix = "DENIALNET_"
        extra = "ignore"


settings = Settings()
