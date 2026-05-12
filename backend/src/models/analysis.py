from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Insight(Base):
    """A finding about the bot's behaviour or strategy. Stores both
    auto-generated insights from the analysis pipeline (e.g. edge_validated,
    edge_degraded) and manually-curated findings the operator writes down
    from the sport-overview page. The `type` field distinguishes them;
    `sport` is nullable so cross-sport meta-findings stay representable."""

    __tablename__ = "insights"
    __table_args__ = (Index("ix_insights_sport_created", "sport", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport: Mapped[str | None] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column()
    recommendation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
