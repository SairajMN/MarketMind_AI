import React from 'react';

const ChartView = ({ chartData, alignedData }) => {
  if (chartData) {
    return (
      <div className="my-4">
        <h2 className="font-semibold text-lg mb-2">Price Chart with News Events</h2>
        <img src={`data:image/png;base64,${chartData}`} alt="Stock analysis chart" className="w-full border rounded" />
      </div>
    );
  }
  return null;
};

export default ChartView;
