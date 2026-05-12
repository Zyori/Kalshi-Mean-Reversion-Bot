from datetime import datetime

from sqlalchemy import DateTime, Enum, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.types import Sport, SportMode


def _enum_values(enum_cls):
    """Store StrEnum *values* (e.g. "nhl"), not member names (e.g. "NHL"),
    so every table in the schema agrees on a single source of truth for
    sport/mode strings. Without this, SQLAlchemy defaults to member names
    and round-trips fail when other tables already use the lowercase value."""
    return [e.value for e in enum_cls]


class SportConfig(Base):
    """Per-sport engagement mode — the single source of truth that drives
    ingestion, paper trading, and UI visibility for each sport."""

    __tablename__ = "sport_configs"

    sport: Mapped[Sport] = mapped_column(
        Enum(
            Sport,
            name="sport",
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        primary_key=True,
    )
    mode: Mapped[SportMode] = mapped_column(
        Enum(
            SportMode,
            name="sport_mode",
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
