import React, { useState } from 'react';
import StatusBadge from './StatusBadge';

const ReasoningChain = ({ steps = [] }) => {
  const [expanded, setExpanded] = useState({});

  const toggleStep = (index) => {
    setExpanded((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const filteredSteps = steps.filter((step) => step?.action);

  return (
    <div className="space-y-3">
      <h2 className="font-semibold text-lg">Agent Reasoning</h2>
      {filteredSteps.map((step, index) => {
        const isExpanded = expanded[index] || false;
        const hasError = step?.result?.error;

        return (
          <div key={index} className="border rounded">
            <button
              className="w-full flex justify-between items-center p-3 bg-gray-100"
              onClick={() => toggleStep(index)}
            >
              <div className="flex items-center gap-2">
                <span>Step {step.step + 1}</span>
                <StatusBadge status={hasError ? 'error' : 'success'} />
              </div>
              <span>{isExpanded ? '▼' : '▶'}</span>
            </button>
            {isExpanded && (
              <div className="p-3 space-y-2 text-sm">
                <div>
                  <strong>Thought:</strong> {step.thought}
                </div>
                <div>
                  <strong>Action:</strong> {step.action}
                </div>
                <div>
                  <strong>Input:</strong>
                  <pre className="mt-1 bg-gray-50 p-2 rounded overflow-x-auto">
                    {JSON.stringify(step.input, null, 2)}
                  </pre>
                </div>
                <div>
                  <strong>Result:</strong>
                  <div className={`mt-1 ${hasError ? 'text-red-500' : ''}`}>
                    {hasError
                      ? step.result.error
                      : JSON.stringify(step.result, null, 2).slice(0, 500) +
                        (JSON.stringify(step.result, null, 2).length > 500 ? '...' : '')}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default ReasoningChain;