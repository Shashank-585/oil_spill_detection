import React, { useEffect } from 'react';
import { TopHeader } from './components/layout/TopHeader';
import { NavigationRail } from './components/layout/NavigationRail';
import { InspectorDrawer } from './components/layout/InspectorDrawer';
import { GeospatialViewport } from './components/map/GeospatialViewport';
import { MasterTimelineScrubber } from './components/timeline/MasterTimelineScrubber';
import { CandidateRankingTable } from './components/attribution/CandidateRankingTable';
import { UncertaintyView } from './components/attribution/UncertaintyView';
import { CounterfactualViewer } from './components/attribution/CounterfactualViewer';
import { SarView } from './components/observation/SarView';
import { AisView } from './components/observation/AisView';
import { DriftView } from './components/observation/DriftView';
import { InvestigationReportView } from './components/report/InvestigationReportView';
import { AuthorityNotificationView } from './components/notifications/AuthorityNotificationView';
import { HistoricalReplayBar } from './components/timeline/HistoricalReplayBar';
import { useInvestigationStore, type WorkspaceView } from './store/investigationStore';
import './styles/globals.css';

export const App: React.FC = () => {
  const activeCaseId = useInvestigationStore((s) => s.activeCaseId);
  const activeStage = useInvestigationStore((s) => s.activeStage);
  const activeWorkspace = useInvestigationStore((s) => s.activeWorkspace);
  const isReplayMode = useInvestigationStore((s) => s.isReplayMode);
  const setActiveCaseId = useInvestigationStore((s) => s.setActiveCaseId);
  const setActiveWorkspace = useInvestigationStore((s) => s.setActiveWorkspace);

  // 1. Synchronize URL route (pathname or hash) with activeCaseId and activeWorkspace
  useEffect(() => {
    const handleLocationChange = () => {
      // Priority A: Check pathname /cases/:case_id/:view
      const pathname = window.location.pathname;
      const pathParts = pathname.split('/').filter(Boolean);
      if (pathParts[0] === 'cases' && pathParts[1]) {
        const caseParam = pathParts[1];
        setActiveCaseId(caseParam);
        if (pathParts[2]) {
          const rawView = pathParts[2].toLowerCase();
          let mappedView: WorkspaceView = 'overview';
          if (rawView === 'attribution' || rawView === 'attribute' || rawView === 'candidates') {
            mappedView = 'candidates';
          } else if (rawView === 'observe') {
            mappedView = 'overview';
          } else if (rawView === 'investigate') {
            mappedView = 'drift';
          } else if (rawView === 'report') {
            mappedView = 'audit';
          } else if (rawView === 'alerts' || rawView === 'notifications') {
            mappedView = 'alerts';
          } else {
            mappedView = rawView as WorkspaceView;
          }
          setActiveWorkspace(mappedView);
          return;
        }
      }

      // Priority B: Check URL hash #case=...&view=...
      const hash = window.location.hash.replace(/^#/, '');
      const params = new URLSearchParams(hash);
      const caseParam = params.get('case');
      const viewParam = params.get('view') as WorkspaceView;
      if (caseParam) {
        setActiveCaseId(caseParam);
      }
      if (viewParam) {
        let mappedView: WorkspaceView = viewParam;
        const raw = String(viewParam).toLowerCase();
        if (raw === 'attribution' || raw === 'attribute') mappedView = 'candidates';
        else if (raw === 'observe') mappedView = 'overview';
        else if (raw === 'investigate') mappedView = 'drift';
        else if (raw === 'report') mappedView = 'audit';
        else if (raw === 'alerts' || raw === 'notifications') mappedView = 'alerts';
        setActiveWorkspace(mappedView);
      }
    };

    handleLocationChange();
    window.addEventListener('popstate', handleLocationChange);
    window.addEventListener('hashchange', handleLocationChange);
    return () => {
      window.removeEventListener('popstate', handleLocationChange);
      window.removeEventListener('hashchange', handleLocationChange);
    };
  }, [setActiveCaseId, setActiveWorkspace]);

  // 2. Update URL when activeCaseId or activeWorkspace changes
  useEffect(() => {
    const currentPath = window.location.pathname;
    const pathParts = currentPath.split('/').filter(Boolean);
    if (pathParts[0] === 'cases') {
      const viewSlug = activeWorkspace === 'candidates' ? 'attribution' : activeWorkspace;
      const targetPath = `/cases/${encodeURIComponent(activeCaseId)}/${viewSlug}`;
      if (currentPath !== targetPath) {
        window.history.replaceState(null, '', targetPath);
      }
    } else {
      const newHash = `case=${encodeURIComponent(activeCaseId)}&view=${encodeURIComponent(activeWorkspace)}`;
      if (window.location.hash !== `#${newHash}`) {
        window.history.replaceState(null, '', `#${newHash}`);
      }
    }
  }, [activeCaseId, activeWorkspace]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        backgroundColor: 'var(--color-bg-base)',
      }}
    >
      {/* Top Header */}
      <TopHeader />

      {/* Main Workspace Body */}
      <div style={{ display: 'flex', flex: 1, height: 'calc(100vh - var(--header-height))', overflow: 'hidden' }}>
        {/* Left Navigation Rail */}
        <NavigationRail />

        {/* Center Investigation Workspace (Map + Overlays + Timeline) */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, position: 'relative', overflow: 'hidden' }}>
          {/* Active Workflow Stage & Workspace Badge */}
          <div
            style={{
              position: 'absolute',
              top: '16px',
              right: '56px',
              zIndex: 10,
              backgroundColor: 'rgba(17, 22, 32, 0.88)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              padding: '4px 10px',
              fontSize: 'var(--text-2xs)',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <span style={{ color: 'var(--color-accent-blue)' }}>STAGE: {activeStage}</span>
            <span style={{ color: 'var(--color-text-muted)' }}>·</span>
            <span style={{ color: 'var(--color-text-secondary)' }}>VIEW: {activeWorkspace}</span>
          </div>

          {/* Geospatial Viewport (Dominates 80%+ of view) */}
          <main style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
            <GeospatialViewport />

            {/* Modal / Overlay Workspaces */}
            {activeWorkspace === 'sar' && (
              <SarView onClose={() => setActiveWorkspace('overview')} />
            )}
            {activeWorkspace === 'ais' && (
              <AisView onClose={() => setActiveWorkspace('overview')} />
            )}
            {activeWorkspace === 'drift' && (
              <DriftView onClose={() => setActiveWorkspace('overview')} />
            )}
            {activeWorkspace === 'candidates' && (
              <CandidateRankingTable onClose={() => setActiveWorkspace('overview')} />
            )}
            {activeWorkspace === 'evidence' && (
              <CounterfactualViewer onClose={() => setActiveWorkspace('overview')} />
            )}
            {activeWorkspace === 'uncertainty' && (
              <UncertaintyView onClose={() => setActiveWorkspace('overview')} />
            )}
            {activeWorkspace === 'audit' && (
              <InvestigationReportView onClose={() => setActiveWorkspace('overview')} />
            )}
            {activeWorkspace === 'alerts' && (
              <AuthorityNotificationView onClose={() => setActiveWorkspace('overview')} />
            )}
          </main>

          {/* Historical Event Replay Floating HUD (Phase 22) */}
          {isReplayMode && <HistoricalReplayBar />}

          {/* Master Timeline Scrubber */}
          <MasterTimelineScrubber />
        </div>

        {/* Right Forensic Inspector Drawer */}
        <InspectorDrawer />
      </div>
    </div>
  );
};

export default App;
