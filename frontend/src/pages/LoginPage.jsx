import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoAccess = async () => {
    setError(null);
    setLoading(true);
    try {
      await demoLogin();
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Demo login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="ambient-glow"></div>
      <Navbar />
      <div style={{ minHeight: 'calc(100vh - 80px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem 1.5rem' }}>
        <div className="modal-card" style={{ maxWidth: '440px', padding: '2.25rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div className="logo-badge" style={{ margin: '0 auto 1rem', width: '44px', height: '44px' }}>
              <svg viewBox="0 0 24 24" style={{ width: '24px', height: '24px' }}>
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" fill="#fff" />
              </svg>
            </div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff', marginBottom: '0.35rem' }}>
              Sign In to DeployEasy
            </h1>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
              Developer-First Cloud CI/CD & Deployment Observatory
            </p>
          </div>

          {error && (
            <div style={{ padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', color: '#fca5a5', fontSize: '0.84rem', marginBottom: '1.25rem' }}>
              {error}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="developer"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                required
                className="form-input"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '0.75rem', marginTop: '0.5rem', fontSize: '0.95rem' }}
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>

          <div style={{ margin: '1.5rem 0', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>OR</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
          </div>

          <button
            type="button"
            onClick={handleDemoAccess}
            disabled={loading}
            className="btn-demo-hero"
            style={{ width: '100%', justifyContent: 'center', padding: '0.7rem', fontSize: '0.9rem' }}
          >
            ⚡ Instant Demo Access (Pre-loaded Fleet)
          </button>

          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Don't have an account? <Link to="/register" style={{ color: 'var(--primary)', fontWeight: 600 }}>Create an account</Link>
          </div>
        </div>
      </div>
    </>
  );
}
