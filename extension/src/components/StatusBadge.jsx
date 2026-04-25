import React from 'react';

const StatusBadge = ({ status }) => {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
      {status.toUpperCase()}
    </span>
  );
};

export default StatusBadge;