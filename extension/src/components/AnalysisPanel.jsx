import React from 'react';

const AnalysisPanel = ({ answer }) => {
  return (
    <div className="bg-white border rounded-lg p-4 mb-4">
      <h2 className="font-semibold text-lg mb-2">Analysis Summary</h2>
      <div className="prose prose-sm max-w-none">
        <pre className="whitespace-pre-wrap text-sm">{answer}</pre>
      </div>
    </div>
  );
};

export default AnalysisPanel;