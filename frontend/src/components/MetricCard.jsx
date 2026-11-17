import React from 'react';

export function MetricCard({ label, value, icon, subtext, color = 'accent', progress = 100 }) {
  const colorClassMap = {
    purple: 'card-purple',
    cyan: 'card-cyan',
    green: 'card-green',
    amber: 'card-amber'
  };

  return (
    <div className={`stat-card ${colorClassMap[color] || ''}`}>
      <div className="stat-header">
        <span className="stat-label">{label}</span>
        <div className="stat-icon">{icon}</div>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-progress-bar">
        <div
          className="stat-progress-fill"
          style={{
            width: `${Math.min(100, Math.max(0, progress))}%`,
            background: color === 'green' ? 'var(--emerald)' : color === 'cyan' ? 'var(--cyan)' : color === 'purple' ? 'var(--primary)' : 'var(--amber)'
          }}
        />
      </div>
      <div className="stat-subtext">{subtext}</div>
    </div>
  );
}
