import React, { useState, useEffect, useRef } from 'react';
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
import { api } from '../../api';

export function DashboardPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [overview, setOverview] = useState(null);
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
      const [ovData, projData] = await Promise.all([
        api.getOverview().catch(() => null),
        api.getProjects().catch(() => [])
      ]);
      if (ovData) setOverview(ovData);
      if (projData) {
        setProjects(projData);
        if (!selectedProject && projData.length > 0) {
          setSelectedProject(projData[0]);
        }
      }
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
        {/* Navigation Tabs Bar with Chevrons (User requested horizontal scrollbar fix) */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
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
            </ul>
            <button className="nav-scroll-btn" onClick={() => scrollTabs(1)} title="Scroll Right">›</button>
          </div>
        </div>

        {/* Live Demo Sandbox Banner */}
        <div className="env-banner">
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
        </div>

        {/* Tab Contents */}
        {activeTab === 'overview' && (
          <TabOverview
            overview={overview}
            projects={projects}
            onSwitchTab={(t) => setActiveTab(t)}
          />
        )}

        {activeTab === 'projects' && (
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
      </main>

      <Footer />

      <ModalNewProject
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onProjectCreated={(newProj) => {
          setProjects((prev) => [newProj, ...prev]);
          setSelectedProject(newProj);
        }}
      />
    </>
  );
}
