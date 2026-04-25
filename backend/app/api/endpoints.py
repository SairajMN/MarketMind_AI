from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from app.models.schemas import AnalysisRequest
from app.agents.orchestrator import AgentOrchestrator

app = FastAPI(title="MarketMind AI API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    orchestrator = AgentOrchestrator()
    result = await orchestrator.run(request.query, request.session_id)
    return result

@app.get("/health")
async def health_check() -> Dict:
    return {"status": "healthy"}

# Optional tool-specific endpoints (for debugging)
@app.post("/tool/stock_data")
async def tool_stock_data(symbol: str, start_date: str, end_date: str):
    # Import here to avoid circular imports if needed
    from app.tools.stock_data import get_stock_data
    try:
        result = await get_stock_data(symbol, start_date, end_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool/news")
async def tool_news(query: str, date_from: str, date_to: str, max_results: int = 10):
    from app.tools.news import get_news
    try:
        result = await get_news(query, date_from, date_to, max_results)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool/align")
async def tool_align(news_data: dict, price_data: dict):
    from app.tools.align import align_data
    try:
        result = await align_data(news_data, price_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool/sentiment")
async def tool_sentiment(news_articles: list):
    from app.tools.sentiment import analyze_sentiment
    try:
        result = await analyze_sentiment(news_articles)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool/visualize")
async def tool_visualize(aligned_data: dict):
    from app.tools.visualize import generate_visualization
    try:
        result = await generate_visualization(aligned_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))