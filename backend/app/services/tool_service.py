from __future__ import annotations

import os
import re
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any
import math

import httpx

from backend.app.models.data_models import (
    AlignedPriceMove,
    AlignmentPayload,
    NewsArticle,
    NewsCorrelation,
    NewsDataPayload,
    PricePoint,
    StockDataPayload,
    ToolName,
)

SUPPORTED_TOOLS: tuple[ToolName, ...] = (
    "fetch_stock_data",
    "fetch_news",
    "align_news_with_price",
)

ARCHETYPES = (
    {
        "direction": "up",
        "base_price": 128.0,
        "moves": (0.0, 0.7, 1.8, 3.2, 4.9, 5.7, 6.4, 7.0),
        "theme": "product momentum and stronger guidance tone",
        "headlines": (
            "Demo: upbeat guidance tone lifts sentiment",
            "Demo: product launch momentum stays in focus",
            "Demo: analysts lean more constructive on demand",
        ),
    },
    {
        "direction": "down",
        "base_price": 214.0,
        "moves": (0.0, -0.8, -1.7, -2.9, -4.1, -5.0, -5.8, -6.2),
        "theme": "margin pressure and cooling demand chatter",
        "headlines": (
            "Demo: margin pressure concerns hit the tape",
            "Demo: demand cooling chatter weighs on the name",
            "Demo: cautious analyst tone extends the slide",
        ),
    },
    {
        "direction": "flat",
        "base_price": 87.0,
        "moves": (0.0, 0.9, -0.4, 1.4, 0.2, -0.6, 0.7, 0.4),
        "theme": "mixed signals with no single dominant catalyst",
        "headlines": (
            "Demo: mixed commentary keeps conviction low",
            "Demo: macro crosscurrents cloud the session",
            "Demo: investors stay selective despite rebounds",
        ),
    },
)

RANGE_CONFIG = {
    "1d": {"points": 4, "spacing": timedelta(hours=2)},
    "5d": {"points": 5, "spacing": timedelta(days=1)},
    "1m": {"points": 6, "spacing": timedelta(days=5)},
    "3m": {"points": 8, "spacing": timedelta(days=12)},
}


# =============================================================================
# DEMO SERVICE (kept for reference / local testing)
# =============================================================================

class DemoToolService:
    """Execute the MarketMind tools with deterministic demo data."""

    def execute(self, tool_name: ToolName, payload: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "fetch_stock_data":
            return self.fetch_stock_data(
                symbol=self._normalize_symbol(payload.get("symbol", "")),
                range_value=self._normalize_range(payload.get("range", "5d")),
            ).to_dict()

        if tool_name == "fetch_news":
            return self.fetch_news(
                query=str(payload.get("query", "")),
                range_value=self._normalize_range(payload.get("range", "5d")),
            ).to_dict()

        return self.align_news_with_price(
            news_payload=payload.get("news"),
            stock_payload=payload.get("prices"),
        ).to_dict()

    def fetch_stock_data(self, symbol: str, range_value: str) -> StockDataPayload:
        symbol = self._normalize_symbol(symbol) or "MARKET"
        range_value = self._normalize_range(range_value)
        archetype = self._archetype_for_symbol(symbol)
        timestamps = self._time_windows(range_value)

        prices: list[PricePoint] = []
        previous_close = archetype["base_price"]
        move_series = archetype["moves"][: len(timestamps)]

        for index, (window, move) in enumerate(zip(timestamps, move_series, strict=False)):
            close = round(archetype["base_price"] * (1 + move / 100), 2)
            open_price = round(previous_close + math.sin(index + 1) * 0.42, 2)
            high = round(max(open_price, close) + 0.86 + index * 0.04, 2)
            low = round(min(open_price, close) - 0.78 - index * 0.03, 2)
            volume = 1_200_000 + index * 175_000 + (self._symbol_seed(symbol) % 90_000)
            prices.append(
                PricePoint(
                    timestamp=window.isoformat(),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )
            previous_close = close

        return StockDataPayload(symbol=symbol, range=range_value, prices=prices)

    def fetch_news(self, query: str, range_value: str) -> NewsDataPayload:
        symbol = self._extract_symbol_from_query(query) or "MARKET"
        range_value = self._normalize_range(range_value)
        archetype = self._archetype_for_symbol(symbol)
        time_windows = self._time_windows(range_value)

        article_windows = self._article_windows(time_windows)
        articles: list[NewsArticle] = []
        for index, (headline, published_at) in enumerate(zip(archetype["headlines"], article_windows, strict=False)):
            articles.append(
                NewsArticle(
                    title=f"{headline} for {symbol}",
                    published_at=published_at.isoformat(),
                    source="Demo Feed",
                    url=f"https://example.com/marketmind/{symbol.lower()}/{index + 1}",
                    summary=(
                        f"Synthetic demo article for {symbol} around {archetype['theme']}. "
                        "Replace this tool with a real news provider when you wire production data."
                    ),
                )
            )

        return NewsDataPayload(query=query or f"{symbol} stock", range=range_value, articles=articles)

    def align_news_with_price(self, news_payload: Any, stock_payload: Any) -> AlignmentPayload:
        stock_data = self._coerce_stock_payload(stock_payload)
        news_data = self._coerce_news_payload(news_payload)
        symbol = stock_data.symbol
        range_value = stock_data.range

        if len(stock_data.prices) < 2:
            return AlignmentPayload(symbol=symbol, range=range_value, aligned_moves=[])

        article_records = []
        for article in news_data.articles:
            article_records.append((article, self._parse_timestamp(article.published_at)))

        move_candidates: list[tuple[float, AlignedPriceMove]] = []
        previous_close = stock_data.prices[0].close

        for price in stock_data.prices[1:]:
            current_time = self._parse_timestamp(price.timestamp)
            change_percent = round(((price.close - previous_close) / previous_close) * 100, 2)
            previous_close = price.close

            direction: str
            if change_percent > 0.35:
                direction = "up"
            elif change_percent < -0.35:
                direction = "down"
            else:
                direction = "flat"

            correlated = self._best_matching_articles(
                article_records=article_records,
                current_time=current_time,
                direction=direction,
            )
            price_context = self._build_price_context(change_percent, direction, correlated)
            move = AlignedPriceMove(
                timestamp=price.timestamp,
                direction=direction,
                price_change_percent=change_percent,
                price_context=price_context,
                correlated_news=correlated,
            )
            move_candidates.append((abs(change_percent), move))

        move_candidates.sort(key=lambda item: item[0], reverse=True)
        top_moves = [move for _, move in move_candidates[:3]]

        return AlignmentPayload(symbol=symbol, range=range_value, aligned_moves=top_moves)

    def _coerce_stock_payload(self, payload: Any) -> StockDataPayload:
        if not isinstance(payload, dict):
            return StockDataPayload(symbol="MARKET", range="5d", prices=[])

        price_points = []
        for raw_price in payload.get("prices", []):
            if not isinstance(raw_price, dict):
                continue
            price_points.append(
                PricePoint(
                    timestamp=str(raw_price.get("timestamp", "")),
                    open=float(raw_price.get("open", 0.0)),
                    high=float(raw_price.get("high", 0.0)),
                    low=float(raw_price.get("low", 0.0)),
                    close=float(raw_price.get("close", 0.0)),
                    volume=int(raw_price["volume"]) if raw_price.get("volume") is not None else None,
                )
            )

        return StockDataPayload(
            symbol=self._normalize_symbol(payload.get("symbol", "")) or "MARKET",
            range=self._normalize_range(payload.get("range", "5d")),
            prices=price_points,
        )

    def _coerce_news_payload(self, payload: Any) -> NewsDataPayload:
        if not isinstance(payload, dict):
            return NewsDataPayload(query="MARKET stock", range="5d", articles=[])

        articles = []
        for raw_article in payload.get("articles", []):
            if not isinstance(raw_article, dict):
                continue
            articles.append(
                NewsArticle(
                    title=str(raw_article.get("title", "")),
                    published_at=str(raw_article.get("published_at", "")),
                    source=str(raw_article.get("source", "Demo Feed")),
                    url=str(raw_article.get("url", "https://example.com/marketmind")),
                    summary=str(raw_article.get("summary", "")),
                )
            )

        return NewsDataPayload(
            query=str(payload.get("query", "MARKET stock")),
            range=self._normalize_range(payload.get("range", "5d")),
            articles=articles,
        )

    def _best_matching_articles(
        self,
        article_records: list[tuple[NewsArticle, datetime]],
        current_time: datetime,
        direction: str,
    ) -> list[NewsCorrelation]:
        ranked: list[tuple[float, NewsCorrelation]] = []
        for article, article_time in article_records:
            hours_apart = abs((current_time - article_time).total_seconds()) / 3600
            relevance = max(0.35, round(1.0 / (1 + hours_apart / 10), 2))
            ranked.append(
                (
                    relevance,
                    NewsCorrelation(
                        title=article.title,
                        published_at=article.published_at,
                        source=article.source,
                        url=article.url,
                        summary=article.summary,
                        impact=self._impact_label(direction),
                        relevance_score=relevance,
                    ),
                )
            )

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in ranked[:2]]

    def _build_price_context(
        self,
        change_percent: float,
        direction: str,
        correlated_news: list[NewsCorrelation],
    ) -> str:
        if not correlated_news:
            return "The move window completed without a closely matched demo headline."

        lead_source = correlated_news[0].source
        if direction == "up":
            return (
                f"The price window strengthened by {change_percent}% as the {lead_source} catalyst cluster "
                "arrived near the move."
            )

        if direction == "down":
            return (
                f"The price window weakened by {abs(change_percent)}% as the {lead_source} catalyst cluster "
                "coincided with softer sentiment."
            )

        return (
            f"The price window stayed relatively balanced, suggesting the {lead_source} headlines did not create "
            "a decisive directional break."
        )

    def _time_windows(self, range_value: str) -> list[datetime]:
        config = RANGE_CONFIG[self._normalize_range(range_value)]
        anchor = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        total_points = config["points"]
        spacing = config["spacing"]
        start = anchor - spacing * (total_points - 1)
        return [start + spacing * index for index in range(total_points)]

    def _article_windows(self, time_windows: list[datetime]) -> list[datetime]:
        if not time_windows:
            return []

        indexes = sorted({min(len(time_windows) - 1, 1), len(time_windows) // 2, len(time_windows) - 1})
        return [time_windows[index] - timedelta(minutes=45 - idx * 10) for idx, index in enumerate(indexes)]

    def _archetype_for_symbol(self, symbol: str) -> dict[str, Any]:
        return ARCHETYPES[self._symbol_seed(symbol) % len(ARCHETYPES)]

    def _symbol_seed(self, symbol: str) -> int:
        return sum(ord(character) for character in symbol)

    def _normalize_symbol(self, symbol: str) -> str:
        normalized = re.sub(r"[^A-Z.-]", "", str(symbol).upper())
        return normalized[:10]

    def _normalize_range(self, range_value: str) -> str:
        normalized = str(range_value).lower()
        if normalized in RANGE_CONFIG:
            return normalized
        return "5d"

    def _extract_symbol_from_query(self, query: str) -> str:
        match = re.search(r"\b([A-Za-z.-]{1,10})\b", query)
        if not match:
            return ""
        return self._normalize_symbol(match.group(1))

    def _parse_timestamp(self, value: str) -> datetime:
        if not value:
            return datetime.now(UTC)

        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(UTC)

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _impact_label(self, direction: str) -> str:
        if direction == "up":
            return "positive"
        if direction == "down":
            return "negative"
        return "mixed"


# =============================================================================
# REAL DATA SERVICE (Alpha Vantage + NewsAPI / GNews)
# =============================================================================

class RealToolService:
    """Execute MarketMind tools using live external APIs."""

    def __init__(self) -> None:
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.newsapi_key = os.getenv("NEWSAPI_KEY", "")
        self.gnews_key = os.getenv("GNEWS_API_KEY", "")
        self.http = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # Public execute
    # ------------------------------------------------------------------

    def execute(self, tool_name: ToolName, payload: dict[str, Any]) -> dict[str, Any]:
        # Synchronous wrapper for the async internals
        import asyncio
        return asyncio.run(self._execute_async(tool_name, payload))

    async def _execute_async(self, tool_name: ToolName, payload: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "fetch_stock_data":
            result = await self.fetch_stock_data(
                symbol=self._normalize_symbol(payload.get("symbol", "")),
                range_value=self._normalize_range(payload.get("range", "5d")),
            )
            return result.to_dict()

        if tool_name == "fetch_news":
            result = await self.fetch_news(
                query=str(payload.get("query", "")),
                range_value=self._normalize_range(payload.get("range", "5d")),
            )
            return result.to_dict()

        result = self.align_news_with_price(
            news_payload=payload.get("news"),
            stock_payload=payload.get("prices"),
        )
        return result.to_dict()

    # ------------------------------------------------------------------
    # Stock data (Alpha Vantage)
    # ------------------------------------------------------------------

    async def fetch_stock_data(self, symbol: str, range_value: str) -> StockDataPayload:
        if not self.alpha_vantage_key:
            raise RuntimeError("ALPHA_VANTAGE_API_KEY is not configured.")

        symbol = self._normalize_symbol(symbol) or "MARKET"
        range_value = self._normalize_range(range_value)

        # Determine required days based on range
        days_needed = self._days_for_range(range_value)

        url = (
            "https://www.alphavantage.co/query"
            f"?function=TIME_SERIES_DAILY"
            f"&symbol={symbol}"
            f"&apikey={self.alpha_vantage_key}"
            f"&outputsize=compact"
        )

        response = await self.http.get(url)
        response.raise_for_status()
        data = response.json()

        time_series = data.get("Time Series (Daily)", {})
        if not time_series:
            meta = data.get("Meta Data", {})
            note = data.get("Note", data.get("Information", "Unknown error from Alpha Vantage"))
            raise RuntimeError(f"Alpha Vantage error for {symbol}: {note}")

        # Sort newest first, then trim to requested window
        sorted_dates = sorted(time_series.keys(), reverse=True)
        selected_dates = sorted_dates[:days_needed]
        # Return oldest -> newest for charting
        selected_dates.reverse()

        prices: list[PricePoint] = []
        for date_str in selected_dates:
            daily = time_series[date_str]
            prices.append(
                PricePoint(
                    timestamp=f"{date_str}T00:00:00+00:00",
                    open=float(daily["1. open"]),
                    high=float(daily["2. high"]),
                    low=float(daily["3. low"]),
                    close=float(daily["4. close"]),
                    volume=int(daily["5. volume"]),
                )
            )

        return StockDataPayload(symbol=symbol, range=range_value, prices=prices)

    # ------------------------------------------------------------------
    # News (NewsAPI primary, GNews fallback)
    # ------------------------------------------------------------------

    async def fetch_news(self, query: str, range_value: str) -> NewsDataPayload:
        symbol = self._extract_symbol_from_query(query) or self._normalize_symbol(query) or "MARKET"
        range_value = self._normalize_range(range_value)

        # Compute date window
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=self._days_for_range(range_value))

        articles: list[NewsArticle] = []
        error_messages: list[str] = []

        # Try NewsAPI first
        if self.newsapi_key:
            try:
                articles = await self._fetch_newsapi(query, start_date, end_date)
            except Exception as exc:
                error_messages.append(f"NewsAPI: {exc}")

        # Fallback to GNews
        if not articles and self.gnews_key:
            try:
                articles = await self._fetch_gnews(query, start_date, end_date)
            except Exception as exc:
                error_messages.append(f"GNews: {exc}")

        if not articles:
            raise RuntimeError(
                f"Could not fetch news for '{query}'. Errors: {'; '.join(error_messages)}"
            )

        return NewsDataPayload(query=query or f"{symbol} stock", range=range_value, articles=articles)

    async def _fetch_newsapi(self, query: str, start_date: datetime.date, end_date: datetime.date) -> list[NewsArticle]:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": str(start_date),
            "to": str(end_date),
            "sortBy": "publishedAt",
            "pageSize": 15,
            "apiKey": self.newsapi_key,
        }
        response = await self.http.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            raise RuntimeError(data.get("message", "NewsAPI unknown error"))

        articles: list[NewsArticle] = []
        for item in data.get("articles", []):
            articles.append(
                NewsArticle(
                    title=item.get("title", "No title"),
                    published_at=item.get("publishedAt", ""),
                    source=item.get("source", {}).get("name", "NewsAPI"),
                    url=item.get("url", ""),
                    summary=item.get("description") or item.get("content", "")[:200],
                )
            )
        return articles

    async def _fetch_gnews(self, query: str, start_date: datetime.date, end_date: datetime.date) -> list[NewsArticle]:
        url = "https://gnews.io/api/v4/search"
        params = {
            "q": query,
            "from": str(start_date),
            "to": str(end_date),
            "max": 15,
            "apikey": self.gnews_key,
        }
        response = await self.http.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))

        articles: list[NewsArticle] = []
        for item in data.get("articles", []):
            articles.append(
                NewsArticle(
                    title=item.get("title", "No title"),
                    published_at=item.get("publishedAt", ""),
                    source=item.get("source", {}).get("name", "GNews"),
                    url=item.get("url", ""),
                    summary=item.get("description", "")[:200],
                )
            )
        return articles

    # ------------------------------------------------------------------
    # Alignment (same deterministic logic as demo — no external call)
    # ------------------------------------------------------------------

    def align_news_with_price(self, news_payload: Any, stock_payload: Any) -> AlignmentPayload:
        stock_data = self._coerce_stock_payload(stock_payload)
        news_data = self._coerce_news_payload(news_payload)
        symbol = stock_data.symbol
        range_value = stock_data.range

        if len(stock_data.prices) < 2:
            return AlignmentPayload(symbol=symbol, range=range_value, aligned_moves=[])

        article_records = []
        for article in news_data.articles:
            article_records.append((article, self._parse_timestamp(article.published_at)))

        move_candidates: list[tuple[float, AlignedPriceMove]] = []
        previous_close = stock_data.prices[0].close

        for price in stock_data.prices[1:]:
            current_time = self._parse_timestamp(price.timestamp)
            change_percent = round(((price.close - previous_close) / previous_close) * 100, 2)
            previous_close = price.close

            direction: str
            if change_percent > 0.35:
                direction = "up"
            elif change_percent < -0.35:
                direction = "down"
            else:
                direction = "flat"

            correlated = self._best_matching_articles(
                article_records=article_records,
                current_time=current_time,
                direction=direction,
            )
            price_context = self._build_price_context(change_percent, direction, correlated)
            move = AlignedPriceMove(
                timestamp=price.timestamp,
                direction=direction,
                price_change_percent=change_percent,
                price_context=price_context,
                correlated_news=correlated,
            )
            move_candidates.append((abs(change_percent), move))

        move_candidates.sort(key=lambda item: item[0], reverse=True)
        top_moves = [move for _, move in move_candidates[:3]]

        return AlignmentPayload(symbol=symbol, range=range_value, aligned_moves=top_moves)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _days_for_range(self, range_value: str) -> int:
        mapping = {"1d": 1, "5d": 5, "1m": 22, "3m": 66}
        return mapping.get(range_value, 5)

    def _coerce_stock_payload(self, payload: Any) -> StockDataPayload:
        if not isinstance(payload, dict):
            return StockDataPayload(symbol="MARKET", range="5d", prices=[])

        price_points = []
        for raw_price in payload.get("prices", []):
            if not isinstance(raw_price, dict):
                continue
            price_points.append(
                PricePoint(
                    timestamp=str(raw_price.get("timestamp", "")),
                    open=float(raw_price.get("open", 0.0)),
                    high=float(raw_price.get("high", 0.0)),
                    low=float(raw_price.get("low", 0.0)),
                    close=float(raw_price.get("close", 0.0)),
                    volume=int(raw_price["volume"]) if raw_price.get("volume") is not None else None,
                )
            )

        return StockDataPayload(
            symbol=self._normalize_symbol(payload.get("symbol", "")) or "MARKET",
            range=self._normalize_range(payload.get("range", "5d")),
            prices=price_points,
        )

    def _coerce_news_payload(self, payload: Any) -> NewsDataPayload:
        if not isinstance(payload, dict):
            return NewsDataPayload(query="MARKET stock", range="5d", articles=[])

        articles = []
        for raw_article in payload.get("articles", []):
            if not isinstance(raw_article, dict):
                continue
            articles.append(
                NewsArticle(
                    title=str(raw_article.get("title", "")),
                    published_at=str(raw_article.get("published_at", "")),
                    source=str(raw_article.get("source", "News Feed")),
                    url=str(raw_article.get("url", "")),
                    summary=str(raw_article.get("summary", "")),
                )
            )

        return NewsDataPayload(
            query=str(payload.get("query", "MARKET stock")),
            range=self._normalize_range(payload.get("range", "5d")),
            articles=articles,
        )

    def _best_matching_articles(
        self,
        article_records: list[tuple[NewsArticle, datetime]],
        current_time: datetime,
        direction: str,
    ) -> list[NewsCorrelation]:
        ranked: list[tuple[float, NewsCorrelation]] = []
        for article, article_time in article_records:
            hours_apart = abs((current_time - article_time).total_seconds()) / 3600
            relevance = max(0.35, round(1.0 / (1 + hours_apart / 10), 2))
            ranked.append(
                (
                    relevance,
                    NewsCorrelation(
                        title=article.title,
                        published_at=article.published_at,
                        source=article.source,
                        url=article.url,
                        summary=article.summary,
                        impact=self._impact_label(direction),
                        relevance_score=relevance,
                    ),
                )
            )

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in ranked[:2]]

    def _build_price_context(
        self,
        change_percent: float,
        direction: str,
        correlated_news: list[NewsCorrelation],
    ) -> str:
        if not correlated_news:
            return "The move window completed without closely matched news headlines."

        lead_source = correlated_news[0].source
        lead_title = correlated_news[0].title
        if direction == "up":
            return (
                f"The price window strengthened by {change_percent}% as news from {lead_source} "
                f"({lead_title}) arrived near the move."
            )

        if direction == "down":
            return (
                f"The price window weakened by {abs(change_percent)}% as news from {lead_source} "
                f"({lead_title}) coincided with softer sentiment."
            )

        return (
            f"The price window stayed relatively balanced, suggesting the {lead_source} headlines did not create "
            "a decisive directional break."
        )

    def _parse_timestamp(self, value: str) -> datetime:
        if not value:
            return datetime.now(UTC)

        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(UTC)

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _impact_label(self, direction: str) -> str:
        if direction == "up":
            return "positive"
        if direction == "down":
            return "negative"
        return "mixed"

    def _normalize_symbol(self, symbol: str) -> str:
        normalized = re.sub(r"[^A-Z.-]", "", str(symbol).upper())
        return normalized[:10]

    def _normalize_range(self, range_value: str) -> str:
        normalized = str(range_value).lower()
        if normalized in RANGE_CONFIG:
            return normalized
        return "5d"

    def _extract_symbol_from_query(self, query: str) -> str:
        match = re.search(r"\b([A-Za-z.-]{1,10})\b", query)
        if not match:
            return ""
        return self._normalize_symbol(match.group(1))


def tool_catalog() -> list[dict[str, str]]:
    """Return a small machine-readable tool catalog for the frontend."""

    return [
        {
            "name": tool_name,
            "mode": "live",
            "description": {
                "fetch_stock_data": "Fetch real daily OHLCV candles from Alpha Vantage for a symbol and range.",
                "fetch_news": "Fetch real news articles from NewsAPI/GNews for a symbol and range.",
                "align_news_with_price": "Correlate real price windows with nearby news headlines.",
            }[tool_name],
        }
        for tool_name in SUPPORTED_TOOLS
    ]
