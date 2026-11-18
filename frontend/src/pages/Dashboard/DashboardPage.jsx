import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../../components/Navbar';
import { Footer } from '../../components/Footer';
import { ModalNewProject } from '../../components/ModalNewProject';
import { TabOverview } from './TabOverview';
import { TabProjects } from './TabProjects';
import { TabDeployments } from './TabDeployments';
import { TabReadiness } from './TabReadiness';
import { TabEnvValidator } from './TabEnvValidator';
import { TabSecurity } from './TabSecurity';
import { TabFinOps } from './TabFinOps';
import { TabDiagnostics } from './TabDiagnostics';
import { TabConsole } from './TabConsole';
import { AdminDashboard } from './AdminDashboard';
import { api } from '../../api';

export function DashboardPage() {
  const [activeTab, setActiveTab] = useState('projects');
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [overview, setOverview] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const tabsListRef = useRef(null);

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'projects', label: 'Projects' },
    { id: 'deployments', label: 'Deployments' },
    { id: 'readiness', label: 'Readiness' },
    { id: 'env', label: 'Env Validator' },
    { id: 'security', label: 'Security' },
    { id: 'costs', label: 'FinOps' },
    { id: 'diagnostics', label: 'Diagnostics & Webhooks' },
    { id: 'console', label: 'API Console' }
  ];

  const loadData = async () => {
    try {
      const [ovData, projData, userData] = await Promise.all([
        api.getOverview().catch(() => null),
        api.getProjects().catch(() => []),
        api.getCurrentUser().catch(() => null)
      ]);
      if (ovData) setOverview(ovData);
      if (projData) {
        setProjects(projData);
        if (!selectedProject && projData.length > 0) {
          setSelectedProject(projData[0]);
        }
      }
      setCurrentUser(userData);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const scrollTabs = (direction) => {
    if (tabsListRef.current) {
      tabsListRef.current.scrollBy({ left: direction * 160, behavior: 'smooth' });
    }
  };

  return (
    <>
      <div className="ambient-glow"></div>
      <Navbar onOpenNewProject={() => setIsModalOpen(true)} />

      <main>
        {projects.length === 0 && (
          <section className="telemetry-card" style={{ margin: '1rem auto 1.5rem', maxWidth: '900px', textAlign: 'center', padding: '2rem' }}>
            <h1 style={{ marginBottom: '0.75rem' }}>Start with a GitHub repository</h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem' }}>Paste a repository link. DeployEasy will check the repository and required workflow files before showing deployment setup. No service telemetry is available until a project is connected and deployed.</p>
            {currentUser?.role === 'demo' ? <p>Demo accounts are read-only. <Link to="/register">Create your account</Link> to connect a repository.</p> : <button className="btn-primary" onClick={() => setIsModalOpen(true)}>Connect GitHub Repository</button>}
          </section>
        )}
        {/* Navigation Tabs Bar with Chevrons (User requested horizontal scrollbar fix) */}
        {(projects.length > 0 || currentUser?.role === 'admin') && <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
          <div className="nav-tabs-wrapper" style={{ maxWidth: '900px' }}>
            <button className="nav-scroll-btn" onClick={() => scrollTabs(-1)} title="Scroll Left">‹</button>
            <ul className="nav-tabs" ref={tabsListRef}>
              {tabs.map((t) => (
                <li key={t.id}>
                  <button
                    className={`nav-tab-btn ${activeTab === t.id ? 'active' : ''}`}
                    onClick={() => setActiveTab(t.id)}
                  >
                    {t.label}
                  </button>
                </li>
              ))}
              {currentUser?.role === 'admin' && <li><button className={`nav-tab-btn ${activeTab === 'admin' ? 'active' : ''}`} onClick={() => setActiveTab('admin')}>Admin</button></li>}
            </ul>
            <button className="nav-scroll-btn" onClick={() => scrollTabs(1)} title="Scroll Right">›</button>
          </div>
        </div>}

        {currentUser?.role === 'demo' && <div className="env-banner">
          <div className="env-banner-left">
            <span className="env-banner-icon">⚡</span>
            <div>
              <span className="env-banner-title">LIVE DEMO SANDBOX</span> &mdash;{' '}
              <span className="env-banner-desc">Interactive dummy environment pre-loaded with sample fleet, deployment history, and live telemetry.</span>
            </div>
          </div>
          <div className="env-banner-actions">
            <span className="demo-badge-tag">⚡ Dummy Data Active</span>
          </div>
        </div>}

        {/* Tab Contents */}
        {projects.length > 0 && activeTab === 'overview' && (
          <TabOverview
            overview={overview}
            projects={projects}
            onSwitchTab={(t) => setActiveTab(t)}
          />
        )}

        {(projects.length === 0 || activeTab === 'projects') && (
          <TabProjects
            projects={projects}
            onRefreshProjects={loadData}
            onOpenNewProject={() => setIsModalOpen(true)}
          />
        )}

        {activeTab === 'deployments' && (
          <TabDeployments
            projects={projects}
            selectedProject={selectedProject}
            onSelectProject={(p) => setSelectedProject(p)}
          />
        )}

        {activeTab === 'readiness' && (
          <TabReadiness
            projects={projects}
            selectedProject={selectedProject}
          />
        )}

        {activeTab === 'env' && (
          <TabEnvValidator />
        )}

        {activeTab === 'security' && (
          <TabSecurity
            projects={projects}
            selectedProject={selectedProject}
          />
        )}

        {activeTab === 'costs' && (
          <TabFinOps
            projects={projects}
            selectedProject={selectedProject}
          />
        )}

        {activeTab === 'diagnostics' && (
          <TabDiagnostics
            projects={projects}
            selectedProject={selectedProject}
          />
        )}

        {activeTab === 'console' && (
          <TabConsole />
        )}

        {activeTab === 'admin' && currentUser?.role === 'admin' && <AdminDashboard />}
      </main>

      <Footer />

      <ModalNewProject
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onProjectCreated={(newProj) => {
          setProjects((prev) => [newProj, ...prev]);
          setSelectedProject(newProj);
          setActiveTab('projects');
        }}
      />
    </>
  );
}
