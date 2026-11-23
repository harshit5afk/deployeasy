import React from 'react';
import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer>
      <div className="footer-container">
        <div>
          <div style={{ fontWeight: 800, color: 'var(--text-heading)', fontSize: '1rem', marginBottom: '0.35rem' }}>
            Deploy<span style={{ color: 'var(--brand-color, var(--primary))' }}>Easy</span>
          </div>
          <div>Developer-First Cloud CI/CD & Deployment Observatory. MIT Licensed.</div>
        </div>
        <div className="footer-links">
          <Link to="/">Home</Link>
          <Link to="/dashboard">Dashboard</Link>
          <a href="/demo" target="_blank" rel="noreferrer">⚡ Live Demo Sandbox</a>
        </div>
      </div>
    </footer>
  );
}
