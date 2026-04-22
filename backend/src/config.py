from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.types import KalshiEnvironment


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kalshi_key_id: str = ""
    kalshi_private_key_path: Path = Path("~/.config/kalshi/private_key.pem")
    kalshi_environment: KalshiEnvironment = KalshiEnvironment.DEMO

    odds_api_key: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/bot.db"

    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    env: str = "dev"
    admin_password_hash: str = ""
    session_secret: str = ""
    session_max_age_days: int = 30
    session_cookie_name: str = "lutz_session"

    scoreboard_live_poll_interval_s: float = 10.0
    scoreboard_pregame_poll_interval_s: float = 300.0
    scoreboard_idle_poll_interval_s: float = 43200.0
    odds_poll_interval_s: float = 43200.0
    events_poll_interval_s: float = 15.0
    kalshi_market_cache_ttl_s: float = 300.0
    paper_bankroll_start_cents: int = 100000
    paper_trade_min_confidence: float = 0.35
    paper_trade_min_deviation: float = 0.08
    paper_trade_max_open_per_market: int = 3
    paper_trade_reentry_min_price_move_cents: int = 5

    @field_validator("kalshi_private_key_path")
    @classmethod
    def expand_key_path(cls, v: Path) -> Path:
        return v.expanduser()

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"


settings = Settings()
