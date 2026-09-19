from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    ENV: str = "development"
    ALLOW_MOCK_PAYMENTS: bool = False
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

    @model_validator(mode="after")
    def production_settings(self):
        if self.ENV not in {"development", "test", "staging", "production"}:
            raise ValueError("DENIALNET_ENV must be development, test, staging, or production")
        if self.ALLOW_MOCK_PAYMENTS and self.ENV != "test":
            raise ValueError("Mock payments require DENIALNET_ENV=test")
        if self.ENV in {"staging", "production"}:
            if not self.DATABASE_URL or not self.DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
                raise ValueError("Production requires DENIALNET_DATABASE_URL with PostgreSQL")
            prefix = "sk_live_" if self.ENV == "production" else "sk_test_"
            if not self.STRIPE_SECRET_KEY or not self.STRIPE_SECRET_KEY.startswith(prefix):
                raise ValueError(f"{self.ENV} requires a {prefix} DENIALNET_STRIPE_SECRET_KEY")
            if not self.STRIPE_WEBHOOK_SECRET or not self.ADMIN_API_KEY:
                raise ValueError("Production requires webhook and admin credentials")
        return self

    class Config:
        env_prefix = "DENIALNET_"
        extra = "ignore"
        env_file = ".env"


settings = Settings()
