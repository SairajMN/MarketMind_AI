import React, { useState, useEffect } from 'react';
import AnalysisPanel from './AnalysisPanel';
import ReasoningChain from './ReasoningChain';
import ChartView from './ChartView';
import StatusBadge from './StatusBadge';
import ErrorDisplay from './ErrorDisplay';
import api from '../utils/api';
import '../index.css';

const App = () => {
  const [symbol, setSymbol] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [steps, setSteps] = useState([]);
  const [chart, setChart] = useState(null);
  const [finalAnswer, setFinalAnswer] = useState(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.analyze(symbol);
      setAnalysis(data);
      setSteps(data.memory || []);
      
      // Find chart step
      const chartStep = data.memory?.find(m => m.result?.chart);
      if (chartStep) {
        setChart(chartStep.result.chart);
      }
      
      // Find final answer
      const finalStep = data.memory?.find(m => m.final_answer);
      if (finalStep) {
        setFinalAnswer(finalStep.final_answer);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = (stepIndex) => {
    // Optional: resend from that step
    // For now, we can skip implementation
    console.log('Retry from step:', stepIndex);
  };

  const handleExportJSON = () => {
    if (!analysis) return;
    const dataStr = JSON.stringify(analysis, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `marketmind-analysis-${symbol || 'unknown'}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-4 bg-gray-50 w-96 min-h-screen">
      <h1 className="text-2xl font-bold mb-4">MarketMind AI 🧠</h1>
      
      <div className="mb-4">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Enter stock symbol (e.g., AAPL)"
          className="w-full p-2 border border-gray-300 rounded mb-2"
          disabled={loading}
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !symbol}
          className="w-full bg-blue-500 text-white py-2 rounded disabled:bg-blue-300"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
      
      {error && <ErrorDisplay message={error} />}
      
      {loading && !error && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <p className="text-gray-600">Analyzing...</p>
        </div>
      )}
      
      {!loading && steps.length > 0 && (
        <ReasoningChain steps={steps} onRetry={handleRetry} />
      )}
      
      {chart && <ChartView chartData={chart} />}
      
      {finalAnswer && <AnalysisPanel answer={finalAnswer} />}
      
      {analysis && (
        <button
          onClick={handleExportJSON}
          className="w-full mt-4 bg-green-500 text-white py-2 rounded disabled:bg-green-300"
        >
          Export JSON
        </button>
      )}
    </div>
  );
};

export default App;