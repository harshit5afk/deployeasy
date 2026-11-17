import React, { useEffect, useState } from 'react';
import { api } from '../../api';

export function TabSecurity({ projects, selectedProject }) {
  const projectId = selectedProject?.id || projects?.[0]?.id;
  const [scans, setScans] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!projectId) { setScans([]); return; }
    api.getSecurityScans(projectId).then(setScans).catch((e) => { setError(e.message); setScans([]); });
  }, [projectId]);
  if (!projectId) return <div className="telemetry-card">Select a project to view its recorded security scans.</div>;
  const latest = Object.values(scans.reduce((acc, scan) => {
    if (!acc[scan.scan_type] || new Date(scan.scanned_at) > new Date(acc[scan.scan_type].scanned_at)) acc[scan.scan_type] = scan;
    return acc;
  }, {}));
  return <div className="card-table-wrapper">
    <div className="table-header-bar"><div><h3>Recorded security scans</h3><p>Findings reflect scan records returned by the connected project.</p></div></div>
    {error && <p role="alert">Could not load scans: {error}</p>}
    {!error && latest.length === 0 && <p style={{ padding: '1rem' }}>No security scan records are available yet.</p>}
    {latest.length > 0 && <table className="custom-table"><thead><tr><th>Scanner</th><th>Scanned</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Result</th></tr></thead><tbody>
      {latest.map((scan) => <tr key={scan.id}><td>{scan.scan_type}</td><td>{scan.scanned_at ? new Date(scan.scanned_at).toLocaleString() : '—'}</td><td>{scan.critical_count}</td><td>{scan.high_count}</td><td>{scan.medium_count}</td><td>{scan.low_count}</td><td>{scan.passed ? 'Passed' : 'Findings detected'}</td></tr>)}
    </tbody></table>}
  </div>;
}
