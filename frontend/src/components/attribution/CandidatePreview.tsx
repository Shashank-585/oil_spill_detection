import React from 'react';
import type { VesselAttributionItem } from '../../api/casesApi';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { CausalTagPill } from './CausalTagPill';
import { EvidenceBars } from './EvidenceBars';
import {
  CheckCircle2,
  AlertTriangle,
  GitCompare,
} from 'lucide-react';

interface CandidatePreviewProps {
  vessel: VesselAttributionItem;
  onOpenComparison?: (vessel: VesselAttributionItem) => void;
}

export const CandidatePreview: React.FC<CandidatePreviewProps> = ({ vessel, onOpenComparison }) => {
  const causalStatus = vessel.causal_precedence_status || 'UNKNOWN';
  const metrics = vessel.underlying_metrics;
  const breakdown = vessel.evidence_breakdown;

  const formatDistance = (m?: number | null) => {
    if (m === undefined || m === null) return null;
    if (m >= 1000) return `${(m / 1000).toFixed(2)} km`;
    return `${m.toFixed(1)} m`;
  };

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
            <span className="font-mono" style={{ fontSize: 'var(--text-xl)', fontWeight: 800, color: vessel.vessel_rank === 1 ? 'var(--color-accent-blue)' : 'var(--color-text-secondary)' }}>
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

      {/* "Compare Candidates" Quick Action Trigger */}
      {onOpenComparison && (
        <button
          onClick={() => onOpenComparison(vessel)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            backgroundColor: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: 'var(--radius-sm)',
            padding: '7px 12px',
            color: 'var(--color-accent-cyan)',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'background-color 0.15s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(56, 189, 248, 0.16)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'rgba(56, 189, 248, 0.08)')}
        >
          <GitCompare size={14} />
          <span>Compare With Other Candidates</span>
        </button>
      )}

      {/* SECTION 1: WHY THIS HYPOTHESIS? */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          padding: '12px',
          backgroundColor: 'rgba(34, 197, 94, 0.04)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(34, 197, 94, 0.2)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: 'var(--text-2xs)',
            fontWeight: 700,
            color: 'var(--color-accent-emerald)',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          <CheckCircle2 size={13} />
          <span>WHY THIS HYPOTHESIS?</span>
        </div>

        {/* Concrete Underlying Metrics Evidence Rows */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: 'var(--text-xs)' }}>
          {/* Drift Compatibility */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: 'var(--color-text-secondary)', lineHeight: 1.35 }}>
            <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 700 }}>✓</span>
            <div>
              <strong style={{ color: 'var(--color-text-primary)' }}>Drift compatibility:</strong>
              {metrics?.centroid_error_m !== undefined && metrics?.centroid_error_m !== null ? (
                <span> Centroid error: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent-cyan)' }}>{metrics.centroid_error_m.toFixed(2)} m</span></span>
              ) : (
                <span> Consistent backward drift</span>
              )}
              {metrics?.mean_particle_distance_m !== undefined && metrics?.mean_particle_distance_m !== null && (
                <span> · Particle mean: <span style={{ fontFamily: 'var(--font-mono)' }}>{metrics.mean_particle_distance_m.toFixed(1)} m</span></span>
              )}
            </div>
          </div>

          {/* Spatial Compatibility */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: 'var(--color-text-secondary)', lineHeight: 1.35 }}>
            <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 700 }}>✓</span>
            <div>
              <strong style={{ color: 'var(--color-text-primary)' }}>Spatial compatibility:</strong>
              {metrics?.vessel_source_distance_m !== undefined && metrics?.vessel_source_distance_m !== null ? (
                <span> Source distance: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent-cyan)' }}>{formatDistance(metrics.vessel_source_distance_m)}</span></span>
              ) : (
                <span> Candidate inside search corridor</span>
              )}
              {metrics?.spatial_score !== undefined && metrics?.spatial_score !== null && (
                <span> (score: <span style={{ fontFamily: 'var(--font-mono)' }}>{metrics.spatial_score.toFixed(2)}</span>)</span>
              )}
            </div>
          </div>

          {/* Temporal Compatibility */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: 'var(--color-text-secondary)', lineHeight: 1.35 }}>
            <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 700 }}>✓</span>
            <div>
              <strong style={{ color: 'var(--color-text-primary)' }}>Temporal compatibility:</strong>
              {metrics?.release_timestamp ? (
                <span> Release time: <span style={{ fontFamily: 'var(--font-mono)' }}>{new Date(metrics.release_timestamp).toUTCString().replace('GMT', 'UTC')}</span></span>
              ) : (
                <span> Coincides with estimated release window</span>
              )}
            </div>
          </div>

          {/* Source Plausibility */}
          {metrics?.source_score !== undefined && metrics?.source_score !== null && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: 'var(--color-text-secondary)', lineHeight: 1.35 }}>
              <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 700 }}>✓</span>
              <div>
                <strong style={{ color: 'var(--color-text-primary)' }}>Source plausibility:</strong>
                <span> Plausibility score: <span style={{ fontFamily: 'var(--font-mono)' }}>{metrics.source_score.toFixed(2)}</span></span>
              </div>
            </div>
          )}

          {/* AIS Trajectory Compatibility */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: 'var(--color-text-secondary)', lineHeight: 1.35 }}>
            <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 700 }}>✓</span>
            <div>
              <strong style={{ color: 'var(--color-text-primary)' }}>AIS trajectory compatibility:</strong>
              <span> Track quality: <span style={{ fontFamily: 'var(--font-mono)' }}>{metrics?.ais_track_quality || 'continuous'}</span></span>
              {metrics?.ais_gap_seconds !== undefined && metrics?.ais_gap_seconds !== null && (
                <span> ({metrics.ais_gap_seconds.toFixed(0)}s gap)</span>
              )}
            </div>
          </div>

          {/* Causal Consistency */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', color: 'var(--color-text-secondary)', lineHeight: 1.35 }}>
            <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 700 }}>✓</span>
            <div>
              <strong style={{ color: 'var(--color-text-primary)' }}>Causal consistency:</strong>
              <span> Status: <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{causalStatus}</span></span>
              {metrics?.causal_eligibility !== undefined && metrics?.causal_eligibility !== null && (
                <span> · Eligible: <span style={{ color: metrics.causal_eligibility ? 'var(--color-accent-emerald)' : 'var(--color-accent-red)' }}>{metrics.causal_eligibility ? 'Yes' : 'No'}</span></span>
              )}
            </div>
          </div>

          {/* Primary Strength Callout */}
          {vessel.primary_strength && (
            <div
              style={{
                marginTop: '4px',
                padding: '6px 8px',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderRadius: 'var(--radius-xs)',
                fontSize: '11px',
                color: 'var(--color-text-primary)',
              }}
            >
              <strong style={{ color: 'var(--color-accent-emerald)' }}>Primary Strength:</strong> {vessel.primary_strength}
            </div>
          )}
        </div>
      </div>

      {/* SECTION 2: WHY NOT THIS HYPOTHESIS? (Limiting Evidence) */}
      {(breakdown?.limiting_factors && breakdown.limiting_factors.length > 0) || vessel.vessel_rank > 1 ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            padding: '12px',
            backgroundColor: 'rgba(210, 153, 34, 0.04)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(210, 153, 34, 0.2)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: 'var(--text-2xs)',
              fontWeight: 700,
              color: 'var(--color-accent-amber)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            <AlertTriangle size={13} />
            <span>WHY NOT THIS HYPOTHESIS? (LIMITING FACTORS)</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {breakdown?.limiting_factors && breakdown.limiting_factors.length > 0 ? (
              breakdown.limiting_factors.map((lf, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '8px 10px',
                    backgroundColor: lf.severity === 'DISQUALIFYING' ? 'rgba(248, 81, 73, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                    borderLeft: `2px solid ${lf.severity === 'DISQUALIFYING' ? 'var(--color-accent-red)' : 'var(--color-accent-amber)'}`,
                    borderRadius: 'var(--radius-xs)',
                    fontSize: 'var(--text-xs)',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.4,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '11px', color: lf.severity === 'DISQUALIFYING' ? 'var(--color-accent-red)' : 'var(--color-accent-amber)', marginBottom: '2px' }}>
                    {lf.label}
                  </div>
                  <div>{lf.detail}</div>
                </div>
              ))
            ) : vessel.primary_weakness ? (
              <div
                style={{
                  padding: '8px 10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  borderLeft: '2px solid var(--color-accent-amber)',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 1.4,
                }}
              >
                <div style={{ fontWeight: 700, fontSize: '11px', color: 'var(--color-accent-amber)', marginBottom: '2px' }}>
                  Relative Weakness
                </div>
                <div>{vessel.primary_weakness}</div>
              </div>
            ) : (
              <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                No disqualifying factors; ranked #{vessel.vessel_rank} based on relative spatiotemporal score.
              </div>
            )}
          </div>
        </div>
      ) : null}

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
          marginTop: '4px',
          padding: '8px 10px',
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
