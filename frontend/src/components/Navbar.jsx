import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function Navbar({ onOpenNewProject }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const isDashboard = location.pathname.startsWith('/dashboard');
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register' || location.pathname === '/signup';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header>
      <div className="header-container">
        <Link to="/" className="brand" title="DeployEasy Homepage">
          <div className="logo-badge">
            <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          </div>
          <span className="brand-text">Deploy<span>Easy</span></span>
        </Link>

        {isAuthPage ? (
          /* Clean Auth Header: Back to Landing Page only */
          <div className="header-actions">
            <Link
              to="/"
              className="btn-secondary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.45rem 1rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: 'var(--text-main)',
                textDecoration: 'none',
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
              }}
            >
              ← Back to Landing Page
            </Link>
          </div>
        ) : !isDashboard ? (
          <>
            <ul className="nav-links" style={{ display: 'flex', gap: '1.75rem', listStyle: 'none' }}>
              <li><a href="#pipeline" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.88rem' }}>Workflow</a></li>
              <li><a href="#features" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.88rem' }}>Features</a></li>
              <li><a href="#comparison" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.88rem' }}>Why DeployEasy</a></li>
              <li><a href="/docs" target="_blank" rel="noreferrer" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.88rem' }}>Docs</a></li>
            </ul>

            <div className="header-actions">
              {user ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <div className="user-badge" title={`Logged in as ${user.username}`}>
                    <span className="user-avatar-dot">{user.username ? user.username[0].toUpperCase() : 'U'}</span>
                    <span>{user.username}</span>
                  </div>
                  <button className="btn-logout" onClick={handleLogout} title="Log out" style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}>
                    Log out
                  </button>
                  <Link to="/dashboard" className="btn-primary">
                    Dashboard →
                  </Link>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Link
                    to="/login"
                    className="btn-ghost"
                    style={{
                      fontWeight: 600,
                      color: 'var(--text-main)',
                      padding: '0.45rem 1rem',
                      borderRadius: '8px',
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    Log In
                  </Link>
                  <Link
                    to="/register"
                    className="btn-primary"
                    style={{
                      padding: '0.45rem 1.15rem',
                      fontSize: '0.88rem',
                      fontWeight: 600,
                      borderRadius: '8px',
                    }}
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="header-actions">
            {onOpenNewProject && (
              <button className="btn-sm-primary" onClick={onOpenNewProject}>
                <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3.5a.5.5 0 0 1-.5-.5v-4A.5.5 0 0 1 8 4z"/><path d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/></svg>
                New Project
              </button>
            )}
            <div className="status-pill">
              <span className="pulse-dot"></span>
              <span>99.97% Operational</span>
            </div>
            <Link to="/" className="btn-ghost" style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}>
              Home
            </Link>
            <div className="user-menu-group">
              <div className="user-badge" title="Active Account">
                <span className="user-avatar-dot">{user?.username ? user.username[0].toUpperCase() : 'D'}</span>
                <span>{user?.username || 'developer'}</span>
              </div>
              <button className="btn-logout" onClick={handleLogout} title="Logout">
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
