import React from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { INVESTIGATION_STAGES, type InvestigationStage } from '../../types/workflow';
import { ChevronRight, ChevronLeft, Check } from 'lucide-react';

const STAGE_LABELS: Record<InvestigationStage, { num: string; label: string }> = {
  observe: { num: '01', label: 'OBSERVE' },
  investigate: { num: '02', label: 'INVESTIGATE' },
  attribute: { num: '03', label: 'ATTRIBUTE' },
  report: { num: '04', label: 'REPORT' },
};

export const InvestigationStepper: React.FC = () => {
  const activeStage = useInvestigationStore((s) => s.activeStage);
  const setActiveStage = useInvestigationStore((s) => s.setActiveStage);
  const nextStage = useInvestigationStore((s) => s.nextStage);
  const prevStage = useInvestigationStore((s) => s.prevStage);

  const stageOrder: InvestigationStage[] = ['observe', 'investigate', 'attribute', 'report'];
  const currentIndex = stageOrder.indexOf(activeStage);

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        backgroundColor: 'var(--color-bg-base)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-xs)',
        padding: '2px',
        gap: '2px',
      }}
      role="navigation"
      aria-label="Investigation Workflow Stages"
    >
      {/* Prev Stage Button */}
      <button
        onClick={prevStage}
        disabled={currentIndex === 0}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '22px',
          height: '24px',
          borderRadius: 'var(--radius-xs)',
          backgroundColor: 'transparent',
          color: currentIndex === 0 ? 'var(--color-text-disabled)' : 'var(--color-text-secondary)',
          cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
          opacity: currentIndex === 0 ? 0.3 : 1,
          transition: 'all 0.15s ease',
        }}
        title="Previous investigation stage"
        aria-label="Previous investigation stage"
      >
        <ChevronLeft size={14} />
      </button>

      {/* 4 Compact Segmented Stages with Directional Connectors */}
      {INVESTIGATION_STAGES.map((stage, idx) => {
        const isActive = activeStage === stage.id;
        const isPassed = idx < currentIndex;
        const meta = STAGE_LABELS[stage.id];

        return (
          <React.Fragment key={stage.id}>
            {idx > 0 && (
              <span
                style={{
                  color: isPassed ? 'var(--color-accent-teal)' : 'var(--color-text-disabled)',
                  opacity: 0.6,
                  fontSize: '9px',
                  userSelect: 'none',
                  padding: '0 1px',
                }}
              >
                →
              </span>
            )}
            <button
              onClick={() => setActiveStage(stage.id)}
              title={`${meta.num} ${meta.label}: ${stage.purpose}`}
              aria-current={isActive ? 'step' : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '3px 8px',
                height: '24px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: isActive
                  ? 'rgba(209, 178, 124, 0.14)'
                  : isPassed
                  ? 'rgba(95, 145, 138, 0.12)'
                  : 'transparent',
                border: isActive
                  ? '1px solid var(--color-accent-sand)'
                  : isPassed
                  ? '1px solid rgba(95, 145, 138, 0.35)'
                  : '1px solid transparent',
                color: isActive
                  ? 'var(--color-accent-sand)'
                  : isPassed
                  ? 'var(--color-accent-teal)'
                  : 'var(--color-text-muted)',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: isActive ? 700 : 600,
                letterSpacing: '0.04em',
                transition: 'all 0.12s ease',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10px',
                  opacity: isActive ? 1 : 0.85,
                  color: isPassed ? 'var(--color-accent-teal)' : 'inherit',
                }}
              >
                {isPassed ? <Check size={11} strokeWidth={2.5} style={{ display: 'inline', verticalAlign: '-1px' }} /> : meta.num}
              </span>
              <span>{meta.label}</span>
            </button>
          </React.Fragment>
        );
      })}

      {/* Next Stage Button */}
      <button
        onClick={nextStage}
        disabled={currentIndex === stageOrder.length - 1}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '22px',
          height: '24px',
          borderRadius: 'var(--radius-xs)',
          backgroundColor: 'transparent',
          color: currentIndex === stageOrder.length - 1 ? 'var(--color-text-disabled)' : 'var(--color-text-secondary)',
          cursor: currentIndex === stageOrder.length - 1 ? 'not-allowed' : 'pointer',
          opacity: currentIndex === stageOrder.length - 1 ? 0.3 : 1,
          transition: 'all 0.15s ease',
        }}
        title="Next investigation stage"
        aria-label="Next investigation stage"
      >
        <ChevronRight size={14} />
      </button>
    </div>
  );
};
