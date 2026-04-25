from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ToolName = Literal["fetch_stock_data", "fetch_news", "align_news_with_price"]
HistoryEntryType = Literal["tool_call", "tool_result", "final_answer"]


@dataclass(slots=True)
class PricePoint:
    """One price candle returned by the stock data tool."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StockDataPayload:
    """Normalized output expected from fetch_stock_data."""

    symbol: str
    range: str
    prices: list[PricePoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NewsArticle:
    """One article returned by the news tool."""

    title: str
    published_at: str
    source: str
    url: str
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NewsDataPayload:
    """Normalized output expected from fetch_news."""

    query: str
    range: str
    articles: list[NewsArticle] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NewsCorrelation:
    """A news item linked to a concrete price move."""

    title: str
    published_at: str
    source: str
    url: str
    summary: str = ""
    impact: str = ""
    relevance_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AlignedPriceMove:
    """A price movement window annotated with correlated news."""

    timestamp: str
    direction: Literal["up", "down", "flat"]
    price_change_percent: float
    price_context: str = ""
    correlated_news: list[NewsCorrelation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AlignmentPayload:
    """Normalized output expected from align_news_with_price."""

    symbol: str
    range: str
    aligned_moves: list[AlignedPriceMove] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
