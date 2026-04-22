from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class TradeDecision(Base):
    __tablename__ = "trade_decisions"
    __table_args__ = (
        Index("ix_trade_decisions_entered_at", "entered_at"),
        Index("ix_trade_decisions_action", "action"),
        Index("ix_trade_decisions_market_category", "market_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_event_id: Mapped[int | None] = mapped_column(ForeignKey("game_events.id"))
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id"))
    sport: Mapped[str] = mapped_column(String(20), nullable=False)
    market_category: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str | None] = mapped_column(String(10))
    confidence_score: Mapped[float | None] = mapped_column()
    deviation: Mapped[float | None] = mapped_column()
    entry_price: Mapped[int | None] = mapped_column(Integer)
    skip_reason: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
