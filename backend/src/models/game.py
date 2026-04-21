from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.market import Market, OpeningLine
    from src.models.trade import PaperTrade


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport: Mapped[str] = mapped_column(String(20), nullable=False)
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    espn_id: Mapped[str | None] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    opening_line_home_prob: Mapped[float | None] = mapped_column()
    opening_line_source: Mapped[str | None] = mapped_column(String(50))
    latest_home_score: Mapped[int | None] = mapped_column(Integer)
    latest_away_score: Mapped[int | None] = mapped_column(Integer)
    final_home_score: Mapped[int | None] = mapped_column(Integer)
    final_away_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    events: Mapped[list["GameEvent"]] = relationship(back_populates="game")
    markets: Mapped[list["Market"]] = relationship(back_populates="game")
    opening_lines: Mapped[list["OpeningLine"]] = relationship(back_populates="game")


class GameEvent(Base):
    __tablename__ = "game_events"
    __table_args__ = (
        Index("ix_game_events_game_id", "game_id"),
        Index("ix_game_events_detected_at", "detected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    period: Mapped[str | None] = mapped_column(String(20))
    clock: Mapped[str | None] = mapped_column(String(20))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    estimated_real_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    espn_data: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[str | None] = mapped_column(String(30))
    confidence_score: Mapped[float | None] = mapped_column()
    kalshi_price_at: Mapped[int | None] = mapped_column(Integer)
    baseline_prob: Mapped[float | None] = mapped_column()
    deviation: Mapped[float | None] = mapped_column()

    game: Mapped["Game"] = relationship(back_populates="events")
    trades: Mapped[list["PaperTrade"]] = relationship(back_populates="game_event")
