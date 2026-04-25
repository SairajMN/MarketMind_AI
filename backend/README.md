# MarketMind AI Backend

## Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload --port 8000
```

## API Endpoints
- `POST /analyze` - Run agent analysis
- `GET /health` - Health check
- `POST /tool/fetch_stock_data` - Direct tool call
- `POST /tool/fetch_news` - Direct tool call
- `POST /tool/align_news_with_price` - Direct tool call
- `POST /tool/analyze_sentiment` - Direct tool call
- `POST /tool/generate_visualization` - Direct tool call

## Tools
Describe each tool briefly.

- **fetch_stock_data**: Retrieves historical stock price data for a given symbol and time range.
- **fetch_news**: Fetches recent news articles related to a given stock symbol or topic.
- **align_news_with_price**: Aligns news articles with stock price movements to identify correlations.
- **analyze_sentiment**: Performs sentiment analysis on news articles or text data.
- **generate_visualization**: Creates charts and visualizations for stock data and analysis results.

## Configuration
List all environment variables.

- `OPENAI_API_KEY`: API key for OpenAI services (used for LLM and embeddings)
- `FINNHUB_API_KEY`: API key for Finnhub stock data
- `NEWSAPI_ORG_API_KEY`: API key for NewsAPI.org
- `REDIS_URL`: Connection string for Redis cache (optional, defaults to localhost:6379)
- `TRANSFORMERS_CACHE`: Directory for caching Hugging Face transformers models
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT`: Deployment environment (development, production)

## Troubleshooting
- Redis connection errors: app falls back to in-memory cache
- Transformers slow: first run downloads model (~500MB); subsequent runs use cache
- API rate limits: adjust caching TTL, implement queuing