from __future__ import annotations

from typing import Any

from backend.app.models.data_models import ToolName
from backend.app.models.schemas import (
    AgentResponse,
    AnalysisRequest,
    HistoryEntry,
    TOOL_SEQUENCE,
    build_final_answer,
    build_tool_call,
)


class MarketMindAgent:
    """History-aware step planner for the MarketMind tool loop."""

    def next_step(self, request: AnalysisRequest) -> AgentResponse:
        history = request.get("history", [])
        symbol = request["symbol"]
        range_value = request["range"]

        pending_call = self._pending_tool_call(history)
        if pending_call is not None:
            return pending_call

        if self._tool_result(history, "fetch_stock_data") is None:
            return build_tool_call(
                thought="Fetching stock data first so I can anchor the analysis to real price moves.",
                tool="fetch_stock_data",
                tool_input={"symbol": symbol, "range": range_value},
            )

        if self._tool_result(history, "fetch_news") is None:
            return build_tool_call(
                thought="I have prices, so next I need recent news to explain why those moves happened.",
                tool="fetch_news",
                tool_input={"query": f"{symbol} stock", "range": range_value},
            )

        if self._tool_result(history, "align_news_with_price") is None:
            return build_tool_call(
                thought="I now have both datasets and need to align news with price moves before explaining causality.",
                tool="align_news_with_price",
                tool_input={
                    "news": self._tool_result(history, "fetch_news"),
                    "prices": self._tool_result(history, "fetch_stock_data"),
                },
            )

        alignment = self._tool_result(history, "align_news_with_price")
        explanation = self._explain_alignment(symbol, alignment)
        confidence = self._confidence_from_alignment(alignment)
        return build_final_answer(
            thought="I now have price data, news, and aligned evidence to explain the move.",
            answer=explanation,
            confidence=confidence,
        )

    def _pending_tool_call(self, history: list[HistoryEntry]) -> AgentResponse | None:
        if not history:
            return None

        last_entry = history[-1]
        if last_entry["type"] != "tool_call":
            return None

        tool = last_entry["tool"]
        if self._tool_result(history, tool) is None:
            return last_entry

        return None

    def _tool_result(self, history: list[HistoryEntry], tool: ToolName) -> Any | None:
        for entry in reversed(history):
            if entry["type"] == "tool_result" and entry["tool"] == tool:
                return entry["output"]
        return None

    def _extract_aligned_moves(self, alignment: Any) -> list[dict[str, Any]]:
        if isinstance(alignment, dict):
            candidate = (
                alignment.get("aligned_moves")
                or alignment.get("matches")
                or alignment.get("correlations")
                or []
            )
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
            return []

        if isinstance(alignment, list):
            return [item for item in alignment if isinstance(item, dict)]

        return []

    def _explain_alignment(self, symbol: str, alignment: Any) -> str:
        aligned_moves = self._extract_aligned_moves(alignment)
        if not aligned_moves:
            return (
                f"I have the alignment step completed for {symbol}, but the returned payload does not "
                "contain a normalized list of correlated moves, so I cannot safely claim a causal explanation yet."
            )

        sentences: list[str] = []
        for move in aligned_moves[:3]:
            timestamp = str(move.get("timestamp", "an unknown time"))
            direction = str(move.get("direction", "moved"))
            change = move.get("price_change_percent")
            price_context = str(move.get("price_context", "")).strip()
            related_news = move.get("correlated_news") or move.get("matched_news") or move.get("news") or []
            news_titles = [
                article.get("title")
                for article in related_news
                if isinstance(article, dict) and article.get("title")
            ]

            move_fragment = f"On {timestamp}, {symbol} moved {direction}"
            if change is not None:
                move_fragment += f" by {change}%"

            if news_titles:
                joined_titles = "; ".join(news_titles[:2])
                move_fragment += f" alongside news such as {joined_titles}"

            if price_context:
                move_fragment += f". {price_context}"
            else:
                move_fragment += "."

            sentences.append(move_fragment)

        return " ".join(sentences)

    def _confidence_from_alignment(self, alignment: Any) -> str:
        aligned_moves = self._extract_aligned_moves(alignment)
        if not aligned_moves:
            return "35%"

        supported_moves = 0
        for move in aligned_moves:
            related_news = move.get("correlated_news") or move.get("matched_news") or move.get("news") or []
            if related_news:
                supported_moves += 1

        confidence_value = min(95, 55 + supported_moves * 10)
        return f"{confidence_value}%"


def expected_tool_sequence() -> tuple[ToolName, ...]:
    """Expose the mandatory tool order to callers and tests."""

    return TOOL_SEQUENCE
