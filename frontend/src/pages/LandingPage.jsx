import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export function LandingPage() {
  const { user } = useAuth();
  return (
    <>
      <div className="ambient-glow"></div>
      <div className="ambient-glow-2"></div>
      <Navbar />

      <main>
        {/* Hero Section */}
        <section className="hero">
          <div className="hero-pill">
            <span>🚀</span> Automated CI/CD • Verified Containers • Instant Rollback
          </div>

          <h1 className="hero-title">
            Stop Guessing.<br />
            <span className="gradient-text">Deploy With Complete Confidence.</span>
          </h1>

          <p className="hero-subtitle">
            The lightweight deployment observatory for engineering teams. Connect your GitHub Actions pipeline, audit container vulnerabilities with Trivy, validate health endpoints, and execute one-click rollbacks.
          </p>

          <div className="hero-actions">
            <a
              href="/demo"
              target="_blank"
              rel="noreferrer"
              className="btn-demo-hero"
              title="Opens Demo Sandbox in a separate tab pre-filled with dummy data"
            >
              ⚡ Try Live Demo Sandbox (Dummy Data) ↗
            </a>
            {user ? (
              <Link
                to="/dashboard"
                className="btn-primary"
                style={{
                  padding: '0.85rem 1.6rem',
                  fontSize: '0.95rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                }}
              >
                Dashboard →
              </Link>
            ) : (
              <Link
                to="/register"
                className="btn-primary"
                style={{
                  padding: '0.85rem 1.6rem',
                  fontSize: '0.95rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                }}
              >
                Sign Up 🚀
              </Link>
            )}
            <a
              href="https://github.com/harshit5afk/deployeasy"
              target="_blank"
              rel="noreferrer"
              className="btn-secondary"
              style={{
                padding: '0.85rem 1.4rem',
                fontSize: '0.95rem',
              }}
            >
              GitHub Repository
            </a>
          </div>

          {/* 6-Stage Pipeline Graphic */}
          <div id="pipeline" className="pipeline-preview-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Build-Once, Verify & Smoke-Test Architecture
              </span>
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#34d399' }}>
                concurrency: production-deploy
              </span>
            </div>

            <div className="pipeline-steps-grid">
              <div className="pipeline-step-node">
                <div className="step-num">STAGE 01</div>
                <div className="step-name">PR & Push</div>
                <div className="step-detail">fetch-depth: 0 (Full Git history)</div>
              </div>
              <div className="pipeline-step-node">
                <div className="step-num">STAGE 02</div>
                <div className="step-name">Test & Lint</div>
                <div className="step-detail">Ruff + Pytest + Gitleaks scan</div>
              </div>
              <div className="pipeline-step-node">
                <div className="step-num">STAGE 03</div>
                <div className="step-name">Build Once</div>
                <div className="step-detail">linux/amd64 immutable image</div>
              </div>
              <div className="pipeline-step-node">
                <div className="step-num">STAGE 04</div>
                <div className="step-name">Trivy Gate</div>
                <div className="step-detail">Blocks on HIGH/CRITICAL CVEs</div>
              </div>
              <div className="pipeline-step-node">
                <div className="step-num">STAGE 05</div>
                <div className="step-name">GHCR Publish</div>
                <div className="step-detail">Tagged by exact commit SHA</div>
              </div>
              <div className="pipeline-step-node">
                <div className="step-num">STAGE 06</div>
                <div className="step-name">Smoke Test</div>
                <div className="step-detail">Polls /version until SHA is live</div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" style={{ maxWidth: '1240px', margin: '0 auto', padding: '4rem 1.5rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--primary)', marginBottom: '0.5rem' }}>
            Capabilities
          </div>
          <h2 style={{ fontSize: 'clamp(1.8rem, 3.5vw, 2.6rem)', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: '1rem' }}>
            Designed for High Reliability, Zero Clutter
          </h2>
          <p style={{ maxWidth: '650px', color: 'var(--text-muted)', fontSize: '1.05rem', marginBottom: '3rem' }}>
            Enterprise observability platforms are bloated and expensive. DeployEasy gives you the essentials small teams need to ship and operate cloud containers.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
            <div className="stat-card">
              <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>⏪</div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.5rem', color: '#fff' }}>Verified 1-Click Rollback</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Trigger instant rollbacks to known-good Git commit SHAs. DeployEasy polls the target service until the old version is proven live.
              </p>
            </div>

            <div className="stat-card">
              <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🛡️</div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.5rem', color: '#fff' }}>Pre-Deploy Readiness Score</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                100-point safety scorecard evaluating CI tests, Trivy CVEs, secret leak audits, and fleet health with hard safety gate blocks.
              </p>
            </div>

            <div className="stat-card">
              <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🔒</div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.5rem', color: '#fff' }}>Trivy & Gitleaks Security Gate</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Automated vulnerability and leaked secret detection before images enter production registry.
              </p>
            </div>

            <div className="stat-card">
              <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>💰</div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.5rem', color: '#fff' }}>FinOps Cloud Cost Estimator</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Real-time estimation of container compute, RAM, registry storage, and CI runner minutes with optimization suggestions.
              </p>
            </div>

            <div className="stat-card">
              <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🩺</div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.5rem', color: '#fff' }}>Health Probing with SSRF Shield</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Active /health polling with sub-30ms latency tracking and DNS rebinding SSRF protection.
              </p>
            </div>

            <div className="stat-card">
              <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🔔</div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.5rem', color: '#fff' }}>Diagnostics & Webhooks</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Automated failure log categorization, incident post-mortem generator, and Slack/Discord notifications.
              </p>
            </div>
          </div>
        </section>

        {/* Comparison Matrix */}
        <section id="comparison" style={{ maxWidth: '1240px', margin: '0 auto', padding: '2rem 1.5rem 4rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--primary)', marginBottom: '0.5rem' }}>
            Comparison
          </div>
          <h2 style={{ fontSize: 'clamp(1.8rem, 3.5vw, 2.6rem)', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: '2rem' }}>
            Why DeployEasy vs Legacy Observability
          </h2>

          <div className="card-table-wrapper">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Capability</th>
                  <th style={{ color: '#f87171' }}>Legacy Enterprise APM</th>
                  <th style={{ color: '#34d399' }}>DeployEasy Platform</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Rollback Speed</strong></td>
                  <td style={{ color: '#fca5a5' }}>Manual shell scripts / 15-30m downtime</td>
                  <td style={{ color: '#a7f3d0', fontWeight: 600 }}>1-Click verified rollback to commit SHA</td>
                </tr>
                <tr>
                  <td><strong>Container Security</strong></td>
                  <td style={{ color: '#fca5a5' }}>External SaaS addon ($$$$)</td>
                  <td style={{ color: '#a7f3d0', fontWeight: 600 }}>Built-in Trivy & Gitleaks safety gate</td>
                </tr>
                <tr>
                  <td><strong>Safety Gates</strong></td>
                  <td style={{ color: '#fca5a5' }}>Deploys blindly on merge</td>
                  <td style={{ color: '#a7f3d0', fontWeight: 600 }}>100-Point Pre-Deploy Readiness Score</td>
                </tr>
                <tr>
                  <td><strong>Cloud Cost Tracking</strong></td>
                  <td style={{ color: '#fca5a5' }}>Separate FinOps dashboard</td>
                  <td style={{ color: '#a7f3d0', fontWeight: 600 }}>Live per-project compute & CI cost models</td>
                </tr>
                <tr>
                  <td><strong>Setup Complexity</strong></td>
                  <td style={{ color: '#fca5a5' }}>Weeks of agent daemon installations</td>
                  <td style={{ color: '#a7f3d0', fontWeight: 600 }}>Zero daemons. Connects to standard HTTP endpoints</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Tech Stack Strip */}
        <section style={{ maxWidth: '1240px', margin: '0 auto', padding: '1rem 1.5rem 4rem' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-start', gap: '2rem', flexWrap: 'wrap', padding: '1.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: '14px' }}>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>⚡ FastAPI 0.115</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>⚛️ React 18</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>🐳 Docker & GHCR</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>🛡️ Trivy & Gitleaks</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>🗄️ PostgreSQL / SQLite</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>🚀 Render Cloud</span>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
