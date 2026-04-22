from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    __table_args__ = (
        Index("ix_paper_trades_sport", "sport"),
        Index("ix_paper_trades_status", "status"),
        Index("ix_paper_trades_entered_at", "entered_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_event_id: Mapped[int | None] = mapped_column(ForeignKey("game_events.id"))
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), nullable=False)
    sport: Mapped[str] = mapped_column(String(20), nullable=False)
    market_category: Mapped[str] = mapped_column(String(20), nullable=False, default="moneyline")
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_price: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price_adj: Mapped[int] = mapped_column(Integer, nullable=False)
    slippage_cents: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float | None] = mapped_column()
    kelly_fraction: Mapped[float | None] = mapped_column()
    kelly_size_cents: Mapped[int | None] = mapped_column(Integer)
    exit_price: Mapped[int | None] = mapped_column(Integer)
    pnl_cents: Mapped[int | None] = mapped_column(Integer)
    pnl_kelly_cents: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(String(20))
    game_context: Mapped[str | None] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text)
    skip_reason: Mapped[str | None] = mapped_column(String(200))

    game_event = relationship("GameEvent", back_populates="trades")
    market = relationship("Market", back_populates="trades")
