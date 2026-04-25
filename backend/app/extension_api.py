from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.agent.marketmind_agent import MarketMindAgent
from backend.app.models.data_models import ToolName
from backend.app.services.tool_service import RealToolService, SUPPORTED_TOOLS, tool_catalog

# Load environment variables from .env if present (local dev)
env_path = Path(__file__).resolve().parents[3] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class AnalyzeRequestModel(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    range: str = Field(default="5d", min_length=1, max_length=4)
    history: list[dict[str, Any]] = Field(default_factory=list)


app = FastAPI(
    title="MarketMind AI Extension API",
    version="0.1.0",
    description=(
        "FastAPI backend for the MarketMind AI Chrome extension. "
        "Serves real stock data (Alpha Vantage) and news (NewsAPI/GNews) with live correlation."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = MarketMindAgent()
tool_service = RealToolService()


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "MarketMind AI Extension API",
        "status": "ok",
        "mode": "live",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "live",
        "tools": tool_catalog(),
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequestModel) -> dict[str, Any]:
    normalized_request = {
        "symbol": request.symbol.upper(),
        "range": request.range.lower(),
        "history": request.history,
    }
    return agent.next_step(normalized_request)


@app.post("/tools/{tool_name}")
def execute_tool(tool_name: ToolName, payload: dict[str, Any]) -> dict[str, Any]:
    if tool_name not in SUPPORTED_TOOLS:
        raise HTTPException(status_code=404, detail=f"Unsupported tool: {tool_name}")

    return tool_service.execute(tool_name, payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.extension_api:app", host="127.0.0.1", port=8000, reload=True)
