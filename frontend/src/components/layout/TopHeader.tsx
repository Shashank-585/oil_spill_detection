import React from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { Anchor, Compass, Clock, CheckCircle2, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';

import { InvestigationStepper } from '../workflow/InvestigationStepper';

export const TopHeader: React.FC = () => {
  const causalConsistencyEnabled = useInvestigationStore((s) => s.causalConsistencyEnabled);
  const setCausalConsistencyEnabled = useInvestigationStore((s) => s.setCausalConsistencyEnabled);
  const {
    activeCaseId,
    setActiveCaseId,
    cases,
    isLoadingCases,
    activeCase,
    isLoadingCaseDetail,
    caseDetailError,
  } = useActiveCase();

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

        {/* Subordinate System & Project Attribution */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', opacity: 0.75 }}>
          <Anchor size={14} color="var(--color-text-muted)" />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', letterSpacing: '0.04em' }}>
            MARINE INTEL / SIH26143
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
      </div>
    </header>
  );
};
