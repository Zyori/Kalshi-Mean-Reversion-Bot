from datetime import datetime

from sqlalchemy import DateTime, Enum, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.types import Sport, SportMode


class SportConfig(Base):
    """Per-sport engagement mode — the single source of truth that drives
    ingestion, paper trading, and UI visibility for each sport."""

    __tablename__ = "sport_configs"

    sport: Mapped[Sport] = mapped_column(
        Enum(Sport, name="sport", native_enum=False, length=20),
        primary_key=True,
    )
    mode: Mapped[SportMode] = mapped_column(
        Enum(SportMode, name="sport_mode", native_enum=False, length=20),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
