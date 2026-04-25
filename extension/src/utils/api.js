async function analyze(symbol) {
  const response = await fetch('https://marketmind-ai-api.vercel.app/analyze', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      query: `Analyze stock "${symbol}" and explain price movements based on news over the last month.`,
      session_id: 'user-session'
    })
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  return await response.json();
}

// Optional: direct tool call functions for debugging (not required)
// Example:
// async function fetchStockData(symbol) { ... }
// async function fetchNews(symbol) { ... }

export { analyze };