import React, { useState } from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { Anchor, Compass, Clock, CheckCircle2, ShieldCheck, AlertCircle, RefreshCw, Bell, Database } from 'lucide-react';
import { useCaseNotificationsQuery, useCaseReadinessQuery } from '../../api/casesApi';
import { DataReadinessModal } from '../common/DataReadinessModal';

import { InvestigationStepper } from '../workflow/InvestigationStepper';
import { DomainTooltip } from '../common/DomainTooltip';


export const TopHeader: React.FC = () => {
  const causalConsistencyEnabled = useInvestigationStore((s) => s.causalConsistencyEnabled);
  const setCausalConsistencyEnabled = useInvestigationStore((s) => s.setCausalConsistencyEnabled);
  const activeWorkspace = useInvestigationStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useInvestigationStore((s) => s.setActiveWorkspace);
  const {
    activeCaseId,
    setActiveCaseId,
    cases,
    isLoadingCases,
    activeCase,
    isLoadingCaseDetail,
    caseDetailError,
  } = useActiveCase();

  const [readinessModalOpen, setReadinessModalOpen] = useState(false);
  const { data: readinessData } = useCaseReadinessQuery(activeCaseId);

  const { data: notificationFeed } = useCaseNotificationsQuery(activeCaseId);
  const alertCount = notificationFeed?.total_alerts || 0;


  // Investigation Event T0 derived from active case
  const eventTime =
    activeCase?.event?.estimated_start_utc ||
    activeCase?.event?.search_start_utc ||
    (isLoadingCaseDetail ? 'SYNCING T₀...' : 'T₀ UNRECORDED');

  return (
    <header
      style={{
        height: 'var(--header-height)',
        backgroundColor: 'var(--color-bg-surface)',
        borderBottom: '1px solid var(--color-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        zIndex: 20,
        flexShrink: 0,
      }}
    >
      {/* 1. Left: Prominent Active Incident Title & Switcher */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'var(--color-bg-surface-raised)',
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            border: caseDetailError
              ? '1px solid var(--color-accent-crimson)'
              : '1px solid var(--color-border-subtle)',
          }}
        >
          <Compass size={15} color="var(--color-accent-cyan)" />
          <span
            style={{
              fontSize: 'var(--text-2xs)',
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              fontWeight: 600,
            }}
          >
            INCIDENT:
          </span>

          {isLoadingCases ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '2px 4px' }}>
              <RefreshCw size={12} className="animate-spin" color="var(--color-accent-blue)" />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                DISCOVERING CASES...
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
                fontSize: 'var(--text-sm)',
                fontWeight: 700,
                letterSpacing: '0.02em',
                cursor: 'pointer',
                outline: 'none',
                maxWidth: '420px',
              }}
              title="Select registered investigation case"
            >
              {cases.map((c) => {
                const roleTag = c.validation_role
                  ? ` · [${c.validation_role.replace(/_/g, ' ').toUpperCase()}]`
                  : '';
                return (
                  <option
                    key={c.case_id}
                    value={c.case_id}
                    style={{ backgroundColor: 'var(--color-bg-surface)', color: 'var(--color-text-primary)' }}
                  >
                    {c.case_id.toUpperCase()} · {c.name.toUpperCase()}{roleTag}
                  </option>
                );
              })}
            </select>
          )}
        </div>

        {/* Demo Quick-Selection Pills for Live Jury Presentation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 700, letterSpacing: '0.04em' }}>
            DEMO:
          </span>
          <button
            onClick={() => setActiveCaseId('case_003_golden_ray')}
            style={{
              padding: '2px 8px',
              fontSize: '11px',
              fontWeight: activeCaseId === 'case_003_golden_ray' ? 700 : 500,
              backgroundColor: activeCaseId === 'case_003_golden_ray' ? 'rgba(56, 189, 248, 0.16)' : 'var(--color-bg-surface-raised)',
              border: `1px solid ${activeCaseId === 'case_003_golden_ray' ? 'var(--color-accent-cyan)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-xs)',
              color: activeCaseId === 'case_003_golden_ray' ? 'var(--color-accent-cyan)' : 'var(--color-text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            title="Golden Ray Benchmark Case: Complete 4D end-to-end evidence workflow"
          >
            GOLDEN RAY
          </button>
          <button
            onClick={() => setActiveCaseId('case_001')}
            style={{
              padding: '2px 8px',
              fontSize: '11px',
              fontWeight: activeCaseId === 'case_001' ? 700 : 500,
              backgroundColor: activeCaseId === 'case_001' ? 'rgba(46, 160, 67, 0.16)' : 'var(--color-bg-surface-raised)',
              border: `1px solid ${activeCaseId === 'case_001' ? 'var(--color-accent-emerald)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-xs)',
              color: activeCaseId === 'case_001' ? 'var(--color-accent-emerald)' : 'var(--color-text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            title="Case 001 Negative-Control: Natural seepage baseline with zero false attribution"
          >
            CASE 001 (NEG-CTRL)
          </button>
          <button
            onClick={() => setActiveCaseId('case_002_wakashio')}
            style={{
              padding: '2px 8px',
              fontSize: '11px',
              fontWeight: activeCaseId === 'case_002_wakashio' ? 700 : 500,
              backgroundColor: activeCaseId === 'case_002_wakashio' ? 'rgba(217, 119, 6, 0.16)' : 'var(--color-bg-surface-raised)',
              border: `1px solid ${activeCaseId === 'case_002_wakashio' ? 'var(--color-accent-amber)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-xs)',
              color: activeCaseId === 'case_002_wakashio' ? 'var(--color-accent-amber)' : 'var(--color-text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            title="Case 002 Data-Limitation: Grounded hydrodynamic validation with AIS archive limitation"
          >
            CASE 002 (LIMITATION)
          </button>
        </div>

        {/* Subordinate System & Project Attribution */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', opacity: 0.75 }}>
          <Anchor size={14} color="var(--color-text-muted)" />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', letterSpacing: '0.04em' }}>
            SIH26143 · MARITIME FORENSIC ATTRIBUTION
          </span>
        </div>
      </div>

      {/* 2. Center: Investigation Workflow Stepper & Event T0 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <InvestigationStepper />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'var(--color-bg-base)',
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border-subtle)',
          }}
          title="Incident origin / discharge timestamp (T0)"
        >
          <Clock size={13} color="var(--color-accent-amber)" />
          <span
            style={{
              fontSize: 'var(--text-2xs)',
              color: 'var(--color-text-secondary)',
              textTransform: 'uppercase',
              fontWeight: 600,
            }}
          >
            T₀:
          </span>
          {isLoadingCaseDetail ? (
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-accent-amber)', opacity: 0.8 }}>
              SYNCING...
            </span>
          ) : (
            <MonospaceValue value={eventTime} />
          )}
        </div>
      </div>

      {/* 3. Right: System Operational Readiness & Causal Physics Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* System Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {caseDetailError ? (
            <>
              <AlertCircle size={14} color="var(--color-accent-crimson)" />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-accent-crimson)', fontWeight: 500 }}>
                CASE ERROR:
              </span>
              <StatusBadge label="OFFLINE" tone="crimson" size="sm" />
            </>
          ) : isLoadingCaseDetail ? (
            <>
              <RefreshCw size={13} className="animate-spin" color="var(--color-accent-amber)" />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
                STATUS:
              </span>
              <StatusBadge label="SYNCING" tone="amber" size="sm" />
            </>
          ) : (
            <>
              <CheckCircle2 size={14} color="var(--color-accent-emerald)" />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
                ENGINE:
              </span>
              <StatusBadge label="READY" tone="emerald" size="sm" />
            </>
          )}
        </div>

        {/* Causal Consistency Toggle */}
        <DomainTooltip term="Causal consistency" inline>
          <button
            onClick={() => setCausalConsistencyEnabled(!causalConsistencyEnabled)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              backgroundColor: causalConsistencyEnabled ? 'rgba(46, 160, 67, 0.12)' : 'var(--color-bg-surface-raised)',
              border: `1px solid ${causalConsistencyEnabled ? 'var(--color-accent-emerald)' : 'var(--color-border-subtle)'}`,
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            title="Toggle generic 4D causal consistency temporal pruning"
          >
            <ShieldCheck
              size={14}
              color={causalConsistencyEnabled ? 'var(--color-accent-emerald)' : 'var(--color-text-muted)'}
            />
            <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              CAUSAL LAYER:
            </span>
            <span
              style={{
                fontSize: 'var(--text-2xs)',
                fontWeight: 700,
                color: causalConsistencyEnabled ? 'var(--color-accent-emerald)' : 'var(--color-text-muted)',
              }}
            >
              {causalConsistencyEnabled ? 'ENABLED' : 'DISABLED'}
            </span>
          </button>
        </DomainTooltip>

        {/* Phase 24 Authority Alert / Notification Button */}
        <button
          onClick={() => setActiveWorkspace('alerts')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            backgroundColor: activeWorkspace === 'alerts' ? 'rgba(217, 119, 6, 0.18)' : 'var(--color-bg-surface-raised)',
            border: `1px solid ${activeWorkspace === 'alerts' ? 'var(--color-accent-amber)' : 'var(--color-border-subtle)'}`,
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            color: activeWorkspace === 'alerts' ? 'var(--color-accent-amber)' : 'var(--color-text-secondary)',
            transition: 'all 0.2s ease',
          }}
          title="View Authority Notification & Dispatch Feed"
        >
          <Bell size={14} color={activeWorkspace === 'alerts' ? 'var(--color-accent-amber)' : 'var(--color-text-secondary)'} />
          <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 600, textTransform: 'uppercase' }}>
            ALERTS
          </span>
          {alertCount > 0 && (
            <span
              style={{
                backgroundColor: 'var(--color-accent-amber)',
                color: '#0a0d13',
                fontSize: '9px',
                fontWeight: 800,
                padding: '1px 5px',
                borderRadius: '10px',
              }}
            >
              {alertCount}
            </span>
          )}
        </button>

        {/* Phase 25 Data Readiness & Provenance Button */}
        <button
          onClick={() => setReadinessModalOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            backgroundColor: readinessData?.overall_status === 'READY'
              ? 'rgba(46, 160, 67, 0.12)'
              : readinessData?.overall_status === 'LIMITED'
              ? 'rgba(210, 153, 34, 0.12)'
              : 'var(--color-bg-surface-raised)',
            border: `1px solid ${
              readinessData?.overall_status === 'READY'
                ? 'var(--color-accent-emerald)'
                : readinessData?.overall_status === 'LIMITED'
                ? 'var(--color-accent-amber)'
                : 'var(--color-border-subtle)'
            }`,
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          title="Open Data Readiness & Reproducible Provenance Audit"
        >
          <Database size={14} color="var(--color-accent-cyan)" />
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
            DATA:
          </span>
          <StatusBadge
            label={readinessData?.overall_status || 'CHECKING'}
            tone={readinessData?.overall_status === 'READY' ? 'emerald' : readinessData?.overall_status === 'LIMITED' ? 'amber' : 'neutral'}
            size="sm"
          />
        </button>
      </div>

      {/* Phase 25 Data Readiness & Provenance Modal */}
      <DataReadinessModal
        isOpen={readinessModalOpen}
        onClose={() => setReadinessModalOpen(false)}
        caseId={activeCaseId}
      />
    </header>
  );
};
