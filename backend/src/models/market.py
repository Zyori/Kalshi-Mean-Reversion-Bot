from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    kalshi_ticker: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    market_type: Mapped[str | None] = mapped_column(String(50))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    game = relationship("Game", back_populates="markets")
    snapshots: Mapped[list["MarketSnapshot"]] = relationship(back_populates="market")
    trades = relationship("PaperTrade", back_populates="market")


class OpeningLine(Base):
    __tablename__ = "opening_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    home_prob: Mapped[float] = mapped_column(nullable=False)
    away_prob: Mapped[float] = mapped_column(nullable=False)
    home_spread: Mapped[float | None] = mapped_column()
    away_spread: Mapped[float | None] = mapped_column()
    total_points: Mapped[float | None] = mapped_column()
    home_team_total: Mapped[float | None] = mapped_column()
    away_team_total: Mapped[float | None] = mapped_column()
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    odds_raw: Mapped[str | None] = mapped_column(Text)

    game = relationship("Game", back_populates="opening_lines")


class MarketSnapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (Index("ix_snapshots_market_captured", "market_id", "captured_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), nullable=False)
    kalshi_bid: Mapped[int | None] = mapped_column(Integer)
    kalshi_ask: Mapped[int | None] = mapped_column(Integer)
    kalshi_volume: Mapped[int | None] = mapped_column(Integer)
    bid_depth: Mapped[int | None] = mapped_column(Integer)
    ask_depth: Mapped[int | None] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    market: Mapped["Market"] = relationship(back_populates="snapshots")
