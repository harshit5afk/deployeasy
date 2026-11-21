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
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api';

export function DashboardPage() {
  const { user: authUser } = useAuth();
  const [currentUser, setCurrentUser] = useState(null);
  const activeUser = authUser || currentUser;
  const isAdmin = activeUser?.role === 'admin';

  const [activeTab, setActiveTab] = useState(() => {
    if (isAdmin) return 'admin';
    const saved = sessionStorage.getItem('deployeasy_active_tab');
    return saved && saved !== 'admin' ? saved : 'projects';
  });
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [overview, setOverview] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projectToEdit, setProjectToEdit] = useState(null);
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

  const handleTabChange = (newTab) => {
    setActiveTab(newTab);
    if (!isAdmin) {
      sessionStorage.setItem('deployeasy_active_tab', newTab);
    }
  };

  const handleSelectProject = (proj) => {
    setSelectedProject(proj);
    if (proj?.id) {
      sessionStorage.setItem('deployeasy_selected_project_id', String(proj.id));
    }
  };

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
        const savedProjId = sessionStorage.getItem('deployeasy_selected_project_id');
        const match = projData.find((p) => String(p.id) === savedProjId);
        setSelectedProject((prev) => prev || match || (projData.length > 0 ? projData[0] : null));
      }
      setCurrentUser(userData);
      if (userData?.role === 'admin') {
        setActiveTab('admin');
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (isAdmin) {
      setActiveTab('admin');
    }
  }, [isAdmin]);

  const scrollTabs = (direction) => {
    if (tabsListRef.current) {
      tabsListRef.current.scrollBy({ left: direction * 160, behavior: 'smooth' });
    }
  };

  const openNewProject = () => {
    setProjectToEdit(null);
    setIsModalOpen(true);
  };

  const openProjectSettings = (project) => {
    setProjectToEdit(project);
    setIsModalOpen(true);
  };

  return (
    <>
      <div className="ambient-glow"></div>
      <Navbar onOpenNewProject={isAdmin ? null : openNewProject} />

      <main>
        {!isAdmin && projects.length === 0 && (
          <section className="telemetry-card" style={{ margin: '1rem auto 1.5rem', maxWidth: '900px', textAlign: 'center', padding: '2rem' }}>
            <h1 style={{ marginBottom: '0.75rem' }}>Start with a GitHub repository</h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem' }}>Paste a repository link. DeployEasy will check the repository and required workflow files before showing deployment setup. No service telemetry is available until a project is connected and deployed.</p>
            {activeUser?.role === 'demo' ? <p>Demo accounts are read-only. <Link to="/register">Create your account</Link> to connect a repository.</p> : <button className="btn-primary" onClick={openNewProject}>Connect GitHub Repository</button>}
          </section>
        )}

        {/* Navigation Tabs Bar: Admin gets only Admin tab; developers get standard suite */}
        {(projects.length > 0 || isAdmin) && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
            {isAdmin ? (
              <div className="nav-tabs-wrapper" style={{ maxWidth: '220px', justifyContent: 'center' }}>
                <ul className="nav-tabs" style={{ justifyContent: 'center' }}>
                  <li>
                    <button className="nav-tab-btn active">
                      Admin
                    </button>
                  </li>
                </ul>
              </div>
            ) : (
              <div className="nav-tabs-wrapper" style={{ maxWidth: '900px' }}>
                <button className="nav-scroll-btn" onClick={() => scrollTabs(-1)} title="Scroll Left">‹</button>
                <ul className="nav-tabs" ref={tabsListRef}>
                  {tabs.map((t) => (
                    <li key={t.id}>
                      <button
                        className={`nav-tab-btn ${activeTab === t.id ? 'active' : ''}`}
                        onClick={() => handleTabChange(t.id)}
                      >
                        {t.label}
                      </button>
                    </li>
                  ))}
                </ul>
                <button className="nav-scroll-btn" onClick={() => scrollTabs(1)} title="Scroll Right">›</button>
              </div>
            )}
          </div>
        )}

        {activeUser?.role === 'demo' && (
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
        )}

        {/* Tab Contents: Admin sees strictly Administrator dashboard; developers see observatory suite */}
        {isAdmin ? (
          <AdminDashboard />
        ) : (
          <>
            {projects.length > 0 && activeTab === 'overview' && (
              <TabOverview
                overview={overview}
                projects={projects}
                onSwitchTab={handleTabChange}
              />
            )}

            {(projects.length === 0 || activeTab === 'projects') && (
              <TabProjects
                projects={projects}
                onRefreshProjects={loadData}
                onOpenNewProject={activeUser?.role === 'demo' ? undefined : openNewProject}
                onEditProject={activeUser?.role === 'demo' ? undefined : openProjectSettings}
              />
            )}

            {activeTab === 'deployments' && (
              <TabDeployments
                projects={projects}
                selectedProject={selectedProject}
                onSelectProject={handleSelectProject}
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
          </>
        )}
      </main>

      <Footer />

      {!isAdmin && (
        <ModalNewProject
          isOpen={isModalOpen}
          project={projectToEdit}
          onClose={() => { setIsModalOpen(false); setProjectToEdit(null); }}
          onProjectCreated={(newProj) => {
            setProjects((prev) => [newProj, ...prev]);
            setSelectedProject(newProj);
            setActiveTab('projects');
          }}
          onProjectUpdated={(updated) => {
            setProjects((prev) => prev.map((project) => project.id === updated.id ? updated : project));
            setSelectedProject(updated);
          }}
        />
      )}
    </>
  );
}
