import React, { useState } from 'react';
import { useCaseReadinessQuery, type ReadinessStatus, type ReadinessCheckItem, type DatasetProvenanceRecord } from '../../api/casesApi';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from './MonospaceValue';
import {
  ShieldCheck,
  AlertTriangle,
  Database,
  Satellite,
  Wind,
  Ship,
  Clock,
  Layers,
  CheckCircle2,
  XCircle,
  MinusCircle,
  Copy,
  Check,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface DataReadinessPanelProps {
  caseId?: string;
  compact?: boolean;
  showHeader?: boolean;
  showProvenance?: boolean;
  onOpenFullModal?: () => void;
}

type IconComponent = React.ComponentType<{ size?: number; color?: string; style?: React.CSSProperties; className?: string }>;

const STATUS_CONFIG: Record<
  ReadinessStatus,
  { label: string; bg: string; border: string; text: string; icon: IconComponent }
> = {
  READY: {
    label: 'READY',
    bg: 'rgba(46, 160, 67, 0.14)',
    border: '1px solid rgba(46, 160, 67, 0.4)',
    text: '#3fb950',
    icon: CheckCircle2,
  },
  LIMITED: {
    label: 'LIMITED',
    bg: 'rgba(210, 153, 34, 0.14)',
    border: '1px solid rgba(210, 153, 34, 0.4)',
    text: '#d29922',
    icon: AlertTriangle,
  },
  UNAVAILABLE: {
    label: 'UNAVAILABLE',
    bg: 'rgba(248, 81, 73, 0.14)',
    border: '1px solid rgba(248, 81, 73, 0.4)',
    text: '#f85149',
    icon: XCircle,
  },
  'NOT REQUIRED': {
    label: 'NOT REQUIRED',
    bg: 'rgba(110, 118, 129, 0.14)',
    border: '1px solid rgba(110, 118, 129, 0.3)',
    text: '#8b949e',
    icon: MinusCircle,
  },
};

const CHECK_ICONS: Record<string, IconComponent> = {
  Satellite: Satellite,
  Environmental: Wind,
  AIS: Ship,
  'Temporal overlap': Clock,
  'Spatial coverage': Layers,
  'Ground truth where applicable': CheckCircle2,
  'Artifact availability': Database,
};

export const DataReadinessPanel: React.FC<DataReadinessPanelProps> = ({
  caseId,
  compact = false,
  showHeader = true,
  showProvenance = true,
  onOpenFullModal,
}) => {
  const { activeCaseId } = useActiveCase();
  const targetCaseId = caseId || activeCaseId;

  const { data: readiness, isLoading, isError } = useCaseReadinessQuery(targetCaseId);

  const [copiedSha, setCopiedSha] = useState<string | null>(null);
  const [provenanceExpanded, setProvenanceExpanded] = useState<boolean>(!compact);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSha(id);
    setTimeout(() => setCopiedSha(null), 2500);
  };

  if (isLoading) {
    return (
      <div style={{ padding: '16px', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div className="animate-spin" style={{ width: '12px', height: '12px', border: '2px solid var(--color-accent-blue)', borderTopColor: 'transparent', borderRadius: '50%' }} />
        Auditing data readiness & reproducible provenance...
      </div>
    );
  }

  if (isError || !readiness) {
    return (
      <div style={{ padding: '12px', backgroundColor: 'rgba(248, 81, 73, 0.1)', border: '1px solid var(--color-accent-crimson)', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-xs)', color: 'var(--color-accent-crimson)' }}>
        Unable to load data readiness audit for case {targetCaseId}.
      </div>
    );
  }

  const overallCfg = STATUS_CONFIG[readiness.overall_status as ReadinessStatus] || STATUS_CONFIG.LIMITED;
  const OverallIcon = overallCfg.icon;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: compact ? '10px' : '14px',
        backgroundColor: 'var(--color-bg-surface)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--color-border-subtle)',
        padding: compact ? '12px' : '16px',
      }}
    >
      {/* Header Bar */}
      {showHeader && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={15} color="var(--color-accent-cyan)" />
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-text-primary)' }}>
              DATA READINESS & PROVENANCE
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '2px 8px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: overallCfg.bg,
                border: overallCfg.border,
                color: overallCfg.text,
                fontSize: '11px',
                fontWeight: 800,
                letterSpacing: '0.04em',
              }}
            >
              <OverallIcon size={12} />
              {overallCfg.label}
            </span>

            {onOpenFullModal && (
              <button
                onClick={onOpenFullModal}
                style={{
                  background: 'none',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--text-2xs)',
                  padding: '2px 6px',
                  cursor: 'pointer',
                }}
              >
                Full Audit
              </button>
            )}
          </div>
        </div>
      )}

      {/* Case-specific Readiness Highlight Banner */}
      {readiness.case_id === 'case_001_california' && (
        <div
          style={{
            padding: '8px 10px',
            backgroundColor: 'rgba(56, 139, 253, 0.08)',
            border: '1px solid rgba(56, 139, 253, 0.3)',
            borderRadius: 'var(--radius-xs)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: 'var(--text-2xs)',
            color: 'var(--color-accent-blue)',
          }}
        >
          <ShieldCheck size={14} style={{ flexShrink: 0 }} />
          <span>
            <strong>Negative-Control Readiness:</strong> Benign verified slick reference active. System will validate non-attribution behavior.
          </span>
        </div>
      )}

      {readiness.case_id === 'case_002_wakashio' && (
        <div
          style={{
            padding: '8px 10px',
            backgroundColor: 'rgba(210, 153, 34, 0.08)',
            border: '1px solid rgba(210, 153, 34, 0.3)',
            borderRadius: 'var(--radius-xs)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: 'var(--text-2xs)',
            color: 'var(--color-accent-amber)',
          }}
        >
          <AlertTriangle size={14} style={{ flexShrink: 0 }} />
          <span>
            <strong>AIS Archive Limitation:</strong> 2020 Indian Ocean AIS data is paywalled/unavailable in public open catalogs. Physical drift benchmark validation is active.
          </span>
        </div>
      )}

      {readiness.case_id === 'case_003_mediterranean' && (
        <div
          style={{
            padding: '8px 10px',
            backgroundColor: 'rgba(46, 160, 67, 0.08)',
            border: '1px solid rgba(46, 160, 67, 0.3)',
            borderRadius: 'var(--radius-xs)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: 'var(--text-2xs)',
            color: '#3fb950',
          }}
        >
          <CheckCircle2 size={14} style={{ flexShrink: 0 }} />
          <span>
            <strong>Full AIS Availability:</strong> Complete spatiotemporal AIS stream available with 12 candidate vessels tracked in eastern Mediterranean shipping lane.
          </span>
        </div>
      )}

      {/* 7 Checks Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          DATA AVAILABILITY AUDIT (7 PILLARS)
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fit, minmax(280px, 1fr))', gap: '6px' }}>
          {readiness.checks.map((chk: ReadinessCheckItem) => {
            const statusKey = chk.status as ReadinessStatus;
            const cfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG.LIMITED;
            const ItemIcon = CHECK_ICONS[chk.name] || Database;

            return (
              <div
                key={chk.name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  backgroundColor: 'var(--color-bg-base)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                  <ItemIcon size={14} color="var(--color-text-secondary)" style={{ flexShrink: 0 }} />
                  <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {chk.name}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }} title={chk.details}>
                      {chk.details}
                    </span>
                  </div>
                </div>

                <span
                  style={{
                    flexShrink: 0,
                    padding: '2px 6px',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: cfg.bg,
                    border: cfg.border,
                    color: cfg.text,
                    fontSize: '10px',
                    fontWeight: 800,
                    letterSpacing: '0.03em',
                  }}
                >
                  {cfg.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Compact "Data limitations" Section */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          padding: '10px 12px',
          backgroundColor: 'rgba(210, 153, 34, 0.05)',
          border: '1px solid rgba(210, 153, 34, 0.25)',
          borderRadius: 'var(--radius-xs)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <AlertTriangle size={13} color="var(--color-accent-amber)" />
          <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-amber)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            DATA LIMITATIONS
          </span>
        </div>

        <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
          {readiness.data_limitations.map((lim, idx) => (
            <li key={idx} style={{ color: 'var(--color-text-secondary)' }}>
              {lim}
            </li>
          ))}
        </ul>
      </div>

      {/* Reproducible Provenance Section */}
      {showProvenance && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '10px' }}>
          <div
            onClick={() => setProvenanceExpanded(!provenanceExpanded)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={14} color="#3fb950" />
              <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                REPRODUCIBLE PROVENANCE
              </span>
              <span style={{ fontSize: '10px', color: 'var(--color-text-tertiary)' }}>
                ({readiness.provenance_records.length} records)
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-text-muted)' }}>
              {provenanceExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
          </div>

          <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Info size={11} style={{ flexShrink: 0 }} />
            <span>Scientific reproducible provenance metadata for simulation audit. Does not claim legal chain-of-custody.</span>
          </div>

          {provenanceExpanded && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '2px' }}>
              {readiness.provenance_records.map((rec: DatasetProvenanceRecord, idx: number) => {
                const isCopied = copiedSha === rec.dataset_name;
                return (
                  <div
                    key={idx}
                    style={{
                      padding: '8px 10px',
                      backgroundColor: 'var(--color-bg-base)',
                      border: '1px solid var(--color-border-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      fontSize: '11px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>{rec.dataset_name}</span>
                      <span style={{ color: 'var(--color-accent-cyan)', fontSize: '10px', fontFamily: 'monospace' }}>
                        ver {rec.processing_version}
                      </span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-secondary)', fontSize: '10px' }}>
                      <span>Source: <strong style={{ color: 'var(--color-text-primary)' }}>{rec.source}</strong></span>
                      {rec.acquisition_time && (
                        <span>Acq: <MonospaceValue value={rec.acquisition_time.replace('T', ' ')} /></span>
                      )}
                    </div>

                    {rec.sha256_checksum && (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          backgroundColor: 'rgba(10, 13, 19, 0.8)',
                          padding: '3px 6px',
                          borderRadius: 'var(--radius-2xs)',
                          border: '1px solid var(--color-border-subtle)',
                          marginTop: '2px',
                        }}
                      >
                        <span style={{ fontSize: '9px', fontFamily: 'monospace', color: 'var(--color-text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '85%' }}>
                          SHA-256: {rec.sha256_checksum}
                        </span>

                        <button
                          onClick={() => copyToClipboard(rec.sha256_checksum!, rec.dataset_name)}
                          title="Copy SHA-256 Checksum"
                          style={{
                            background: 'none',
                            border: 'none',
                            color: isCopied ? '#3fb950' : 'var(--color-text-secondary)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px',
                            fontSize: '9px',
                            padding: '1px 3px',
                          }}
                        >
                          {isCopied ? <Check size={10} /> : <Copy size={10} />}
                          <span>{isCopied ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
