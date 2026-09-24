import React from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { INVESTIGATION_STAGES, type InvestigationStage } from '../../types/workflow';
import {
  ChevronRight,
  ChevronLeft,
  Check,
  Eye,
  Compass,
  Users,
  FileText,
} from 'lucide-react';

const STAGE_ICONS: Record<InvestigationStage, React.ComponentType<{ size: number; color?: string }>> = {
  observe: Eye,
  investigate: Compass,
  attribute: Users,
  report: FileText,
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
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        backgroundColor: 'rgba(13, 17, 23, 0.95)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-sm)',
        padding: '3px 8px',
        boxShadow: 'var(--shadow-sm)',
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
          width: '24px',
          height: '24px',
          borderRadius: 'var(--radius-xs)',
          backgroundColor: 'transparent',
          border: 'none',
          color: currentIndex === 0 ? 'var(--color-text-muted)' : 'var(--color-text-secondary)',
          cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
          opacity: currentIndex === 0 ? 0.35 : 1,
          transition: 'all 0.15s ease',
        }}
        title="Previous investigation stage"
        aria-label="Previous investigation stage"
      >
        <ChevronLeft size={16} />
      </button>

      {/* 4 Stages */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
        {INVESTIGATION_STAGES.map((stage, idx) => {
          const isActive = activeStage === stage.id;
          const isPassed = idx < currentIndex;
          const Icon = STAGE_ICONS[stage.id];

          return (
            <React.Fragment key={stage.id}>
              {idx > 0 && (
                <div
                  style={{
                    color: isPassed ? 'var(--color-accent-emerald)' : 'var(--color-border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    margin: '0 1px',
                    opacity: 0.6,
                  }}
                >
                  <ChevronRight size={12} />
                </div>
              )}

              <button
                onClick={() => setActiveStage(stage.id)}
                title={`${stage.stageNumber} ${stage.name} — ${stage.purpose}`}
                aria-current={isActive ? 'step' : undefined}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 9px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: isActive
                    ? 'rgba(56, 139, 253, 0.18)'
                    : isPassed
                    ? 'rgba(46, 160, 67, 0.08)'
                    : 'transparent',
                  border: isActive
                    ? '1px solid var(--color-accent-blue)'
                    : isPassed
                    ? '1px solid rgba(46, 160, 67, 0.35)'
                    : '1px solid transparent',
                  color: isActive
                    ? 'var(--color-accent-blue)'
                    : isPassed
                    ? 'var(--color-accent-emerald)'
                    : 'var(--color-text-tertiary)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  position: 'relative',
                }}
              >
                {/* Stage Indicator / Icon */}
                <div
                  style={{
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: isActive
                      ? 'var(--color-accent-blue)'
                      : isPassed
                      ? 'var(--color-accent-emerald)'
                      : 'rgba(255, 255, 255, 0.06)',
                    color: isActive || isPassed ? '#0a0d13' : 'var(--color-text-muted)',
                    fontSize: '10px',
                    fontWeight: 800,
                  }}
                >
                  {isPassed ? <Check size={11} strokeWidth={3} /> : <Icon size={10} />}
                </div>

                {/* Stage Title */}
                <div style={{ textAlign: 'left', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span
                      style={{
                        fontSize: 'var(--text-2xs)',
                        fontWeight: 700,
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        color: isActive ? 'var(--color-text-primary)' : 'inherit',
                      }}
                    >
                      {stage.name}
                    </span>
                  </div>
                </div>
              </button>
            </React.Fragment>
          );
        })}
      </div>

      {/* Next Stage Button */}
      <button
        onClick={nextStage}
        disabled={currentIndex === stageOrder.length - 1}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '3px 8px',
          borderRadius: 'var(--radius-xs)',
          backgroundColor:
            currentIndex === stageOrder.length - 1 ? 'transparent' : 'rgba(56, 139, 253, 0.12)',
          border:
            currentIndex === stageOrder.length - 1
              ? 'none'
              : '1px solid rgba(56, 139, 253, 0.3)',
          color:
            currentIndex === stageOrder.length - 1
              ? 'var(--color-text-muted)'
              : 'var(--color-accent-blue)',
          cursor: currentIndex === stageOrder.length - 1 ? 'not-allowed' : 'pointer',
          opacity: currentIndex === stageOrder.length - 1 ? 0.35 : 1,
          fontSize: 'var(--text-2xs)',
          fontWeight: 700,
          letterSpacing: '0.04em',
          transition: 'all 0.15s ease',
        }}
        title="Advance to next investigation stage"
        aria-label="Advance to next investigation stage"
      >
        <span>NEXT</span>
        <ChevronRight size={14} />
      </button>
    </div>
  );
};
