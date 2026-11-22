import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';

export function RegisterPage() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { register, login } = useAuth();
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const val = identifier.trim();
      let uname = val;
      let uemail = val;
      if (val.includes('@')) {
        uname = val.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '_') || 'developer';
        if (uname.length < 3) uname = `${uname}_dev`;
        uemail = val;
      } else {
        uname = val;
        uemail = `${val}@deployeasy.local`;
      }
      await register(uname, uemail, password);
      navigate('/dashboard');
    } catch (err) {
      // If user already exists, seamlessly attempt login with provided credentials
      try {
        await login(identifier.trim(), password);
        navigate('/dashboard');
        return;
      } catch (_) {
        setError(err.message || 'An account with this email/username already exists. Please Log In with your password.');
      }
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
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-heading)', marginBottom: '0.35rem' }}>
              Create Developer Account
            </h1>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
              Join DeployEasy to monitor and automate cloud releases
            </p>
          </div>

          {error && (
            <div style={{ padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', color: '#fca5a5', fontSize: '0.84rem', marginBottom: '1.25rem' }}>
              <div>{error}</div>
              {(error.includes('already exists') || error.includes('already registered')) && (
                <div style={{ marginTop: '0.65rem' }}>
                  <Link
                    to="/login"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      color: '#fff',
                      background: 'var(--primary)',
                      borderRadius: '6px',
                      padding: '0.35rem 0.8rem',
                      fontSize: '0.82rem',
                      fontWeight: 600,
                      textDecoration: 'none'
                    }}
                  >
                    → Go to Log In Page
                  </Link>
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label className="form-label">Username or email</label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="Username or email address"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
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
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Already have an account? <Link to="/login" style={{ color: 'var(--primary)', fontWeight: 600 }}>Log In</Link>
          </div>
        </div>
      </div>
    </>
  );
}
