import React from 'react';
import type { VesselAttributionItem } from '../../api/casesApi';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { CausalTagPill } from './CausalTagPill';
import { EvidenceBars } from './EvidenceBars';

interface CandidatePreviewProps {
  vessel: VesselAttributionItem;
}

export const CandidatePreview: React.FC<CandidatePreviewProps> = ({ vessel }) => {
  const causalStatus = vessel.causal_precedence_status || 'UNKNOWN';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Primary Candidate Identity & Key Score Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          paddingBottom: '10px',
          borderBottom: '1px solid var(--color-border-subtle)',
        }}
      >
        <div>
          <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '0.02em' }}>
            {vessel.vessel_name}
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '2px', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            <span>MMSI <MonospaceValue value={vessel.mmsi} /></span>
            <span>• Type: {vessel.vessel_type || 'UNKNOWN'}</span>
          </div>
        </div>

        {/* Rank & Compatibility Score */}
        <div style={{ textAlign: 'right' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', justifyContent: 'flex-end' }}>
            <span className="font-mono" style={{ fontSize: 'var(--text-xl)', fontWeight: 800, color: 'var(--color-accent-blue)' }}>
              #{vessel.vessel_rank}
            </span>
            <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              RANK
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', justifyContent: 'flex-end', marginTop: '2px' }}>
            <span className="font-mono" style={{ fontSize: 'var(--text-md)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {typeof vessel.best_evidence_score === 'number' ? vessel.best_evidence_score.toFixed(4) : '—'}
            </span>
            <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              COMPATIBILITY
            </span>
          </div>
        </div>
      </div>

      {/* Causal Status & Classification Alignment */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          padding: '8px 0',
          borderBottom: '1px solid var(--color-border-subtle)',
        }}
      >
        <div>
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
            CAUSAL PRECEDENCE
          </div>
          <CausalTagPill status={causalStatus} />
        </div>
        <div>
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
            SUPPORT CLASSIFICATION
          </div>
          <StatusBadge
            label={vessel.vessel_evidence_state ? vessel.vessel_evidence_state.replace(/_/g, ' ') : 'UNCLASSIFIED'}
            tone={
              vessel.vessel_evidence_state === 'HIGH_SUPPORT'
                ? 'emerald'
                : vessel.vessel_evidence_state === 'MODERATE_SUPPORT'
                ? 'amber'
                : 'neutral'
            }
          />
        </div>
      </div>

      {/* Multi-Evidence Breakdown Rows */}
      {vessel.evidence_components && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            EVIDENCE COMPONENTS
          </div>
          <EvidenceBars components={vessel.evidence_components} />
        </div>
      )}

      {/* Mandatory Calibration Notice */}
      <div
        style={{
          marginTop: '6px',
          padding: '8px',
          backgroundColor: 'rgba(210, 153, 34, 0.06)',
          borderLeft: '2px solid var(--color-accent-amber)',
          fontSize: 'var(--text-2xs)',
          color: 'var(--color-text-secondary)',
          lineHeight: 1.35,
        }}
      >
        <span style={{ fontWeight: 600, color: 'var(--color-accent-amber)' }}>SCIENTIFIC NOTICE:</span> Attribution evidence score is a physical compatibility index under the calibrated Lagrangian drift model. It is not a calibrated legal probability of culpability.
      </div>
    </div>
  );
};
