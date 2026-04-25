from __future__ import annotations

import json
from typing import Any, Literal, TypeAlias, TypedDict

from .data_models import ToolName

TOOL_SEQUENCE: tuple[ToolName, ...] = (
    "fetch_stock_data",
    "fetch_news",
    "align_news_with_price",
)


class ToolCallStep(TypedDict):
    type: Literal["tool_call"]
    thought: str
    tool: ToolName
    input: dict[str, Any]


class ToolResultStep(TypedDict):
    type: Literal["tool_result"]
    tool: ToolName
    output: Any


class FinalAnswerStep(TypedDict):
    type: Literal["final_answer"]
    thought: str
    answer: str
    confidence: str


HistoryEntry: TypeAlias = ToolCallStep | ToolResultStep | FinalAnswerStep
AgentResponse: TypeAlias = ToolCallStep | FinalAnswerStep


class AnalysisRequest(TypedDict):
    symbol: str
    range: str
    history: list[HistoryEntry]


def build_tool_call(thought: str, tool: ToolName, tool_input: dict[str, Any]) -> ToolCallStep:
    """Return a UI-ready tool call response."""

    return {
        "type": "tool_call",
        "thought": thought,
        "tool": tool,
        "input": tool_input,
    }


def build_final_answer(thought: str, answer: str, confidence: str) -> FinalAnswerStep:
    """Return a UI-ready final answer response."""

    return {
        "type": "final_answer",
        "thought": thought,
        "answer": answer,
        "confidence": confidence,
    }


def dumps_response(response: AgentResponse) -> str:
    """Serialize responses in the JSON-only format expected by the extension UI."""

    return json.dumps(response, ensure_ascii=True, separators=(",", ":"))
