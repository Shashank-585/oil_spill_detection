import React, { useState } from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import {
  Compass,
  Film,
  Bell,
  Database,
  ShieldCheck,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  Radio,
} from 'lucide-react';
import { useCaseNotificationsQuery, useCaseReadinessQuery } from '../../api/casesApi';
import { DataReadinessModal } from '../common/DataReadinessModal';
import { InvestigationStepper } from '../workflow/InvestigationStepper';
import { DomainTooltip } from '../common/DomainTooltip';
import { EvidenceStatusIndicator } from '../common/EvidenceStatusIndicator';

export const TopHeader: React.FC = () => {
  const isReplayMode = useInvestigationStore((s) => s.isReplayMode);
  const setReplayMode = useInvestigationStore((s) => s.setReplayMode);
  const causalConsistencyEnabled = useInvestigationStore((s) => s.causalConsistencyEnabled);
  const setCausalConsistencyEnabled = useInvestigationStore((s) => s.setCausalConsistencyEnabled);
  const activeWorkspace = useInvestigationStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useInvestigationStore((s) => s.setActiveWorkspace);
  const inspectorOpen = useInvestigationStore((s) => s.inspectorOpen);
  const toggleInspector = useInvestigationStore((s) => s.toggleInspector);

  const {
    activeCaseId,
    setActiveCaseId,
    cases,
    isLoadingCases,
    caseDetailError,
  } = useActiveCase();

  const [readinessModalOpen, setReadinessModalOpen] = useState(false);
  const { data: readinessData } = useCaseReadinessQuery(activeCaseId);
  const { data: notificationFeed } = useCaseNotificationsQuery(activeCaseId);
  const alertCount = notificationFeed?.total_alerts || 0;

  return (
    <header
      style={{
        height: 'var(--header-height)',
        backgroundColor: 'var(--color-bg-surface)',
        borderBottom: '1px solid var(--color-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 12px',
        zIndex: 20,
        flexShrink: 0,
        userSelect: 'none',
      }}
    >
      {/* 1. LEFT: Incident Switcher & Demo Shortcuts */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'var(--color-bg-base)',
            padding: '3px 8px',
            borderRadius: 'var(--radius-sm)',
            border: caseDetailError
              ? '1px solid var(--color-danger)'
              : '1px solid var(--color-border-subtle)',
          }}
        >
          <Compass size={14} color="var(--color-accent-teal)" />
          {isLoadingCases ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <RefreshCw size={11} className="animate-spin" color="var(--color-accent-teal)" />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                DISCOVERING...
              </span>
            </div>
          ) : (
            <select
              value={activeCaseId}
              onChange={(e) => setActiveCaseId(e.target.value)}
              style={{
                backgroundColor: 'transparent',
                color: 'var(--color-text-primary)',
                border: 'none',
                fontSize: 'var(--text-xs)',
                fontWeight: 700,
                letterSpacing: '0.02em',
                cursor: 'pointer',
                outline: 'none',
                maxWidth: '280px',
              }}
              title="Select registered investigation case"
            >
              {cases.map((c) => (
                <option
                  key={c.case_id}
                  value={c.case_id}
                  style={{ backgroundColor: 'var(--color-bg-surface)', color: 'var(--color-text-primary)' }}
                >
                  {c.case_id.toUpperCase()} · {c.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Rapid Jury Demo Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
          <button
            onClick={() => setActiveCaseId('case_003_golden_ray')}
            style={{
              padding: '2px 6px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: activeCaseId === 'case_003_golden_ray' ? 700 : 500,
              backgroundColor: activeCaseId === 'case_003_golden_ray' ? 'rgba(209, 178, 124, 0.16)' : 'transparent',
              border: `1px solid ${activeCaseId === 'case_003_golden_ray' ? 'var(--color-accent-sand)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-xs)',
              color: activeCaseId === 'case_003_golden_ray' ? 'var(--color-accent-sand)' : 'var(--color-text-muted)',
              cursor: 'pointer',
            }}
            title="Case 003 Golden Ray Benchmark"
          >
            CASE 003
          </button>
          <button
            onClick={() => setActiveCaseId('case_001')}
            style={{
              padding: '2px 6px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: activeCaseId === 'case_001' ? 700 : 500,
              backgroundColor: activeCaseId === 'case_001' ? 'rgba(184, 196, 190, 0.14)' : 'transparent',
              border: `1px solid ${activeCaseId === 'case_001' ? 'var(--color-border)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-xs)',
              color: activeCaseId === 'case_001' ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
              cursor: 'pointer',
            }}
            title="Case 001 Negative-Control"
          >
            CASE 001
          </button>
          <button
            onClick={() => setActiveCaseId('case_002_wakashio')}
            style={{
              padding: '2px 6px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: activeCaseId === 'case_002_wakashio' ? 700 : 500,
              backgroundColor: activeCaseId === 'case_002_wakashio' ? 'rgba(184, 111, 82, 0.16)' : 'transparent',
              border: `1px solid ${activeCaseId === 'case_002_wakashio' ? 'var(--color-warning-rust)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-xs)',
              color: activeCaseId === 'case_002_wakashio' ? 'var(--color-warning-rust)' : 'var(--color-text-muted)',
              cursor: 'pointer',
            }}
            title="Case 002 Data-Limitation"
          >
            CASE 002
          </button>
        </div>
      </div>

      {/* 2. CENTER: Segmented Investigation Stepper & State-Driven Evidence Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <InvestigationStepper />
        <EvidenceStatusIndicator />
      </div>

      {/* 3. RIGHT: Operational System State & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        {/* Data Readiness Indicator */}
        <button
          onClick={() => setReadinessModalOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '2px 7px',
            height: '24px',
            backgroundColor: 'var(--color-bg-base)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer',
            fontSize: '11px',
            color: 'var(--color-text-secondary)',
            transition: 'border-color 0.12s ease',
          }}
          title="Open Data Readiness & Reproducible Provenance Audit"
        >
          <Database size={12} color="var(--color-accent-teal)" />
          <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
            DATA:
          </span>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              fontWeight: 700,
              color: readinessData?.overall_status === 'LIMITED' ? 'var(--color-accent-sand)' : 'var(--color-success)',
            }}
          >
            {readinessData?.overall_status || 'READY'}
          </span>
        </button>

        {/* Operational SAR Pipeline Indicator */}
        <button
          onClick={() => setActiveWorkspace('sar')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '2px 7px',
            height: '24px',
            backgroundColor: activeWorkspace === 'sar' ? 'rgba(95, 145, 138, 0.15)' : 'var(--color-bg-base)',
            border: `1px solid ${activeWorkspace === 'sar' ? 'rgba(95, 145, 138, 0.4)' : 'var(--color-border-subtle)'}`,
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer',
            fontSize: '11px',
            color: 'var(--color-text-secondary)',
            transition: 'all 0.12s ease',
          }}
          title="Open Operational SAR Observation Processing Pipeline Workspace"
        >
          <Radio size={12} color="var(--color-accent-teal)" />
          <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
            SAR:
          </span>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              fontWeight: 700,
              color: 'var(--color-success)',
            }}
          >
            COMPLETE
          </span>
        </button>

        {/* Historical Event Replay Mode Toggle */}
        <button
          onClick={() => setReplayMode(!isReplayMode)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '2px 7px',
            height: '24px',
            backgroundColor: isReplayMode ? 'rgba(95, 145, 138, 0.15)' : 'var(--color-bg-base)',
            border: `1px solid ${isReplayMode ? 'rgba(95, 145, 138, 0.4)' : 'var(--color-border-subtle)'}`,
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer',
            color: isReplayMode ? 'var(--color-accent-seafoam)' : 'var(--color-text-muted)',
            fontSize: '11px',
            fontWeight: 600,
            transition: 'all 0.12s ease',
          }}
          title="Toggle 4D Historical Event Replay Controls"
        >
          <Film size={12} color={isReplayMode ? 'var(--color-accent-seafoam)' : 'var(--color-text-muted)'} />
          <span style={{ fontSize: '10px', letterSpacing: '0.04em' }}>REPLAY</span>
        </button>

        {/* Causal Consistency Pruning Toggle */}
        <DomainTooltip term="Causal consistency" inline>
          <button
            onClick={() => setCausalConsistencyEnabled(!causalConsistencyEnabled)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 7px',
              height: '24px',
              backgroundColor: causalConsistencyEnabled ? 'rgba(125, 156, 121, 0.12)' : 'var(--color-bg-base)',
              border: `1px solid ${causalConsistencyEnabled ? 'rgba(125, 156, 121, 0.35)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-xs)',
              cursor: 'pointer',
              color: causalConsistencyEnabled ? 'var(--color-success)' : 'var(--color-text-muted)',
              fontSize: '11px',
              fontWeight: 600,
              transition: 'all 0.12s ease',
            }}
            title="Toggle generic 4D causal consistency temporal pruning"
          >
            <ShieldCheck size={12} color={causalConsistencyEnabled ? 'var(--color-success)' : 'var(--color-text-muted)'} />
            <span style={{ fontSize: '10px', letterSpacing: '0.04em' }}>CAUSAL</span>
          </button>
        </DomainTooltip>

        {/* Alerts Button */}
        <button
          onClick={() => setActiveWorkspace('alerts')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            height: '26px',
            backgroundColor: activeWorkspace === 'alerts' ? 'rgba(209, 178, 124, 0.16)' : 'var(--color-bg-base)',
            border: `1px solid ${activeWorkspace === 'alerts' ? 'var(--color-accent-sand)' : 'var(--color-border-subtle)'}`,
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer',
            color: activeWorkspace === 'alerts' ? 'var(--color-accent-sand)' : 'var(--color-text-secondary)',
            fontSize: 'var(--text-2xs)',
            fontWeight: 600,
          }}
          title="Authority Notifications & Alert Dispatch Feed"
        >
          <Bell size={13} />
          {alertCount > 0 && (
            <span
              style={{
                backgroundColor: 'var(--color-accent-sand)',
                color: '#0B181A',
                fontSize: '9px',
                fontWeight: 800,
                padding: '0 4px',
                borderRadius: '8px',
                lineHeight: '14px',
              }}
            >
              {alertCount}
            </span>
          )}
        </button>

        {/* Inspector Drawer Toggle Button */}
        <button
          onClick={toggleInspector}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '28px',
            height: '26px',
            backgroundColor: inspectorOpen ? 'var(--color-bg-surface-active)' : 'var(--color-bg-base)',
            border: `1px solid ${inspectorOpen ? 'var(--color-accent-teal)' : 'var(--color-border-subtle)'}`,
            borderRadius: 'var(--radius-xs)',
            color: inspectorOpen ? 'var(--color-accent-teal)' : 'var(--color-text-muted)',
            cursor: 'pointer',
            marginLeft: '4px',
          }}
          title={inspectorOpen ? 'Collapse Forensic Inspector' : 'Expand Forensic Inspector'}
          aria-label="Toggle Forensic Inspector"
        >
          {inspectorOpen ? <PanelRightClose size={15} /> : <PanelRightOpen size={15} />}
        </button>
      </div>

      {/* Data Readiness & Provenance Modal */}
      <DataReadinessModal
        isOpen={readinessModalOpen}
        onClose={() => setReadinessModalOpen(false)}
        caseId={activeCaseId}
      />
    </header>
  );
};
