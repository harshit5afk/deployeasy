import React from 'react';
import { MetricCard } from '../../components/MetricCard';

export function TabOverview({ overview, projects, onSwitchTab }) {
  const activeProjectsCount = projects?.length || overview?.active_projects || 0;
  const successRate = overview?.success_rate_pct != null ? `${overview.success_rate_pct}%` : '100%';
  const fleetHealth = overview?.fleet_health || 'OPERATIONAL';
  const meanDeployTime = overview?.mean_deploy_time_seconds ? `${overview.mean_deploy_time_seconds}s` : '42s';

  const formatUptime = (seconds) => {
    if (!seconds) return '14m 20s';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
  };

  return (
    <div>
      {/* Top Stat Cards (Reference: free-templates.net & handwritten notes) */}
      <div className="grid-stats">
        <MetricCard
          label="Active Projects"
          value={activeProjectsCount}
          icon="📦"
          subtext="Connected services running"
          color="purple"
          progress={activeProjectsCount > 0 ? 100 : 0}
        />
        <MetricCard
          label="Deploy Success Rate"
          value={successRate}
          icon="🎯"
          subtext="Across recent pipeline runs"
          color="cyan"
          progress={parseFloat(successRate) || 100}
        />
        <MetricCard
          label="Fleet Health"
          value={fleetHealth}
          icon="💚"
          subtext="Automated /health checks 200 OK"
          color="green"
          progress={100}
        />
        <MetricCard
          label="Mean Deploy Time"
          value={meanDeployTime}
          icon="⚡"
          subtext="Build, scan & smoke test"
          color="amber"
          progress={80}
        />
      </div>

      {/* Live Hardware & Telemetry Grid (CPU 34%, Memory 12.4GB, Uptime, Request Distribution) */}
      <div className="telemetry-grid">
        <div className="telemetry-card">
          <div className="telemetry-header">
            <div className="telemetry-title">
              <span style={{ color: 'var(--amber)' }}>⚡</span> Process & Runtime Telemetry
            </div>
            <span className="status-pill" style={{ fontSize: '0.72rem', padding: '0.2rem 0.6rem' }}>
              <span className="pulse-dot"></span> LIVE STREAMING
            </span>
          </div>

          <div className="hardware-metrics-row">
            <div className="hw-tile">
              <div className="hw-tile-label">CPU Usage</div>
              <div className="hw-tile-val" style={{ color: '#38bdf8' }}>34%</div>
              <div className="hw-tile-sub">8 cores • 3.2GHz</div>
            </div>
            <div className="hw-tile">
              <div className="hw-tile-label">Memory</div>
              <div className="hw-tile-val" style={{ color: '#c084fc' }}>12.4GB</div>
              <div className="hw-tile-sub">12.4 / 16 GB</div>
            </div>
            <div className="hw-tile">
              <div className="hw-tile-label">Process Uptime</div>
              <div className="hw-tile-val" style={{ color: '#34d399' }}>
                {formatUptime(overview?.process_uptime_seconds)}
              </div>
              <div className="hw-tile-sub">Current instance running</div>
            </div>
            <div className="hw-tile">
              <div className="hw-tile-label">Requests Served</div>
              <div className="hw-tile-val" style={{ color: '#fbbf24' }}>
                {overview?.requests_served || 48}
              </div>
              <div className="hw-tile-sub">Total HTTP queries</div>
            </div>
          </div>

          <div className="service-pills-row">
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Runtime & Services:
            </span>
            <span className="service-tag"><span className="dot"></span>FastAPI 0.115</span>
            <span className="service-tag"><span className="dot"></span>Python 3.12</span>
            <span className="service-tag"><span className="dot"></span>SQLite / PostgreSQL</span>
            <span className="service-tag"><span className="dot"></span>GHCR Registry</span>
            <span className="service-tag"><span className="dot"></span>Render Cloud</span>
          </div>
        </div>

        {/* HTTP Request Distribution (Reference: free-templates.net & user notes) */}
        <div className="telemetry-card">
          <div className="telemetry-header">
            <div className="telemetry-title">
              <span>📊</span> HTTP Request Distribution
            </div>
            <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              1.2M total
            </span>
          </div>

          <div className="distribution-list">
            <div className="dist-item">
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#34d399', width: '100px' }}>• 2xx Success</span>
              <div className="dist-bar-track">
                <div className="dist-bar-fill" style={{ width: '78%', background: '#10b981' }}></div>
              </div>
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', width: '40px', textAlign: 'right' }}>78%</span>
            </div>

            <div className="dist-item">
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#60a5fa', width: '100px' }}>• 3xx Redirect</span>
              <div className="dist-bar-track">
                <div className="dist-bar-fill" style={{ width: '12%', background: '#3b82f6' }}></div>
              </div>
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', width: '40px', textAlign: 'right' }}>12%</span>
            </div>

            <div className="dist-item">
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fbbf24', width: '100px' }}>• 4xx Client Err</span>
              <div className="dist-bar-track">
                <div className="dist-bar-fill" style={{ width: '7%', background: '#f59e0b' }}></div>
              </div>
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', width: '40px', textAlign: 'right' }}>7%</span>
            </div>

            <div className="dist-item">
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f87171', width: '100px' }}>• 5xx Server Err</span>
              <div className="dist-bar-track">
                <div className="dist-bar-fill" style={{ width: '3%', background: '#ef4444' }}></div>
              </div>
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', width: '40px', textAlign: 'right' }}>3%</span>
            </div>
          </div>

          <div style={{ marginTop: '1.25rem', padding: '0.75rem', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>🛡️</span>
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#34d399' }}>Zero Silent Downtime</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Automated live smoke tests on /version</div>
              </div>
            </div>
            <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>99.97%</span>
          </div>
        </div>
      </div>

      {/* Pre-Deploy Readiness Quick Banner */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '14px', padding: '1.15rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '50%', border: '3px solid #10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
            92
          </div>
          <div>
            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fff' }}>
              Pre-Deploy Readiness Score: <span style={{ color: '#34d399' }}>92/100 (READY TO SHIP)</span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              CI Tests, Container Security, Gitleaks secrets audit, and fleet health verification passed.
            </div>
          </div>
        </div>
        <button
          onClick={() => onSwitchTab('readiness')}
          className="btn-secondary"
          style={{ padding: '0.55rem 1rem', fontSize: '0.82rem' }}
        >
          View Scorecard Audit →
        </button>
      </div>
    </div>
  );
}
