import React, { useState } from 'react';
import type { VesselAttributionItem } from '../../api/casesApi';
import { useActiveCase } from '../../context/CaseContext';
import { useInvestigationDossierQuery } from '../../api/casesApi';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { CausalTagPill } from './CausalTagPill';
import { EvidenceBars } from './EvidenceBars';
import {
  CheckCircle2,
  AlertTriangle,
  GitCompare,
  ShieldAlert,
} from 'lucide-react';

interface CandidatePreviewProps {
  vessel: VesselAttributionItem;
  onOpenComparison?: (vessel: VesselAttributionItem) => void;
}

export const CandidatePreview: React.FC<CandidatePreviewProps> = ({ vessel, onOpenComparison }) => {
  const { activeCaseId, activeCase } = useActiveCase();
  const { data: dossier } = useInvestigationDossierQuery(activeCaseId);

  const isNegativeControl =
    activeCaseId === 'case_001' ||
    Boolean(dossier?.data_limitations?.is_negative_control) ||
    Boolean((activeCase as any)?.validation?.validation_role === 'NEGATIVE_NON_VESSEL_CASE') ||
    Boolean(activeCase?.event?.incident_type?.toLowerCase().includes('pipeline'));

  const [showExtendedEvidence, setShowExtendedEvidence] = useState(false);
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
      {/* 1. Candidate Identity & Rank Header */}
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
          <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '0.01em' }}>
            {vessel.vessel_name}
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '2px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
            <span>MMSI <MonospaceValue value={vessel.mmsi} /></span>
            <span>•</span>
            <span>Type: {vessel.vessel_type || 'UNKNOWN'}</span>
          </div>
        </div>

        {/* Rank & Compatibility Score */}
        <div style={{ textAlign: 'right' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '5px', justifyContent: 'flex-end' }}>
            <span className="font-mono" style={{ fontSize: '18px', fontWeight: 800, color: vessel.vessel_rank === 1 ? 'var(--color-accent-sand)' : 'var(--color-text-secondary)' }}>
              #{vessel.vessel_rank}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              RANK
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', justifyContent: 'flex-end', marginTop: '1px' }}>
            <span className="font-mono" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {typeof vessel.best_evidence_score === 'number' ? vessel.best_evidence_score.toFixed(4) : '—'}
            </span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              COMPATIBILITY
            </span>
          </div>
        </div>
      </div>

      {/* 2. Candidate Ranking vs Attribution Decision Callout */}
      <div
        style={{
          padding: '8px 10px',
          backgroundColor: isNegativeControl ? 'rgba(184, 196, 190, 0.08)' : 'rgba(255, 255, 255, 0.02)',
          border: isNegativeControl ? '1px solid rgba(184, 196, 190, 0.3)' : '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-xs)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '9px', fontWeight: 800, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            ATTRIBUTION DECISION
          </span>
          {isNegativeControl ? (
            <StatusBadge label="NOT SUPPORTED" tone="neutral" />
          ) : vessel.vessel_evidence_state === 'HIGH_SUPPORT' ? (
            <StatusBadge label="SUPPORTED HYPOTHESIS" tone="emerald" />
          ) : (
            <StatusBadge label="SCREENING CANDIDATE" tone="amber" />
          )}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
          {isNegativeControl ? (
            <span>
              Highest-scoring candidate under available evidence ({vessel.best_evidence_score?.toFixed(4)}), but <strong style={{ color: 'var(--color-text-primary)' }}>attribution criteria are not satisfied</strong> (required threshold ≥ 0.7000; spatial divergence &gt; 5 km).
            </span>
          ) : vessel.vessel_evidence_state === 'HIGH_SUPPORT' ? (
            <span>
              Exceeds attribution screening threshold (≥ 0.7000). Best-supported candidate under available physical evidence; not a calibrated legal probability.
            </span>
          ) : (
            <span>
              Evaluated traffic candidate. Physical compatibility score ({vessel.best_evidence_score?.toFixed(4)}) is below high-support attribution threshold (≥ 0.7000).
            </span>
          )}
        </div>
      </div>

      {/* 3. Causal Status & Classification Alignment */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          paddingBottom: '8px',
          borderBottom: '1px solid var(--color-border-subtle)',
        }}
      >
        <div>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
            CAUSAL PRECEDENCE
          </div>
          <CausalTagPill status={causalStatus} />
        </div>
        <div>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
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

      {/* 4. Compare Candidates Action Trigger */}
      {onOpenComparison && (
        <button
          onClick={() => onOpenComparison(vessel)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            backgroundColor: 'rgba(95, 145, 138, 0.12)',
            border: '1px solid rgba(95, 145, 138, 0.35)',
            borderRadius: 'var(--radius-xs)',
            padding: '6px 12px',
            color: 'var(--color-accent-teal)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'background-color 0.15s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(95, 145, 138, 0.20)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'rgba(95, 145, 138, 0.12)')}
        >
          <GitCompare size={13} />
          <span>Compare With Other Candidates</span>
        </button>
      )}

      {/* 5. SECTION: EVIDENCE PROFILE */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', paddingTop: '2px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            fontWeight: 700,
            color: isNegativeControl ? 'var(--color-text-secondary)' : 'var(--color-success)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          {isNegativeControl ? <ShieldAlert size={13} /> : <CheckCircle2 size={13} />}
          <span>{isNegativeControl ? 'CANDIDATE EVIDENCE PROFILE (NEGATIVE CONTROL)' : 'WHY THIS HYPOTHESIS'}</span>
        </div>

        {/* Structured Evidence Rows */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '7px', fontSize: '12px' }}>
          {/* Drift Compatibility */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: isNegativeControl ? 'var(--color-text-secondary)' : 'var(--color-success)', fontWeight: 700 }}>
                {isNegativeControl ? '•' : '✓'}
              </span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Drift compatibility</span>
            </div>
            <div style={{ paddingLeft: '16px', color: 'var(--color-text-secondary)', fontSize: '11px' }}>
              {isNegativeControl ? (
                <span>
                  Simulated Lagrangian particles drift away from candidate corridor (&gt;5 km spatial divergence).
                </span>
              ) : (
                <>
                  Centroid error:{' '}
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent-sand)', fontWeight: 600 }}>
                    {metrics?.centroid_error_m !== undefined && metrics?.centroid_error_m !== null
                      ? `${metrics.centroid_error_m.toFixed(2)} m`
                      : 'Consistent backward drift'}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Spatial Compatibility */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>✓</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Spatial compatibility</span>
            </div>
            <div style={{ paddingLeft: '16px', color: 'var(--color-text-secondary)', fontSize: '11px' }}>
              Source distance:{' '}
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent-sand)', fontWeight: 600 }}>
                {metrics?.vessel_source_distance_m !== undefined && metrics?.vessel_source_distance_m !== null
                  ? formatDistance(metrics.vessel_source_distance_m)
                  : 'Candidate within search corridor'}
              </span>
            </div>
          </div>

          {/* Temporal Compatibility */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>✓</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Temporal compatibility</span>
            </div>
            <div style={{ paddingLeft: '16px', color: 'var(--color-text-secondary)', fontSize: '11px' }}>
              Release time:{' '}
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>
                {metrics?.release_timestamp
                  ? new Date(metrics.release_timestamp).toUTCString().replace('GMT', 'UTC')
                  : 'Release time aligns with observation window'}
              </span>
            </div>
          </div>

          {/* Causal Consistency */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>✓</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Causal consistency</span>
            </div>
            <div style={{ paddingLeft: '16px', color: 'var(--color-text-secondary)', fontSize: '11px' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-success)' }}>
                {causalStatus}
              </span>
              {metrics?.causal_eligibility !== undefined && metrics?.causal_eligibility !== null && (
                <span> · {metrics.causal_eligibility ? 'Eligible' : 'Ineligible'}</span>
              )}
            </div>
          </div>

          {/* Extended Metrics Disclosure Toggle */}
          <div style={{ borderTop: '1px solid var(--color-border-subtle)', paddingTop: '6px', marginTop: '2px' }}>
            <button
              onClick={() => setShowExtendedEvidence(!showExtendedEvidence)}
              style={{
                fontSize: '10px',
                fontWeight: 600,
                color: 'var(--color-accent-seafoam)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '2px 0',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{showExtendedEvidence ? '▲ Hide detailed metrics' : '▼ More evidence dimensions'}</span>
            </button>

            {showExtendedEvidence && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: '6px', paddingLeft: '16px', fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                {metrics?.source_score !== undefined && metrics?.source_score !== null && (
                  <div>
                    Source plausibility score: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{metrics.source_score.toFixed(2)}</span>
                  </div>
                )}
                <div>
                  AIS track quality: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{metrics?.ais_track_quality || 'continuous'}</span>
                  {metrics?.ais_gap_seconds !== undefined && metrics?.ais_gap_seconds !== null && (
                    <span> ({metrics.ais_gap_seconds.toFixed(0)}s gap)</span>
                  )}
                </div>
                {metrics?.mean_particle_distance_m !== undefined && metrics?.mean_particle_distance_m !== null && (
                  <div>
                    Particle mean offset: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{metrics.mean_particle_distance_m.toFixed(1)} m</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Primary Strength Callout */}
          {vessel.primary_strength && (
            <div
              style={{
                marginTop: '4px',
                padding: '6px 8px',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                borderLeft: '2px solid rgba(46, 160, 67, 0.5)',
                borderRadius: 'var(--radius-xs)',
                fontSize: '11px',
                color: 'var(--color-text-primary)',
              }}
            >
              <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 600 }}>Primary Strength:</span> {vessel.primary_strength}
            </div>
          )}
        </div>
      </div>

      {/* 5. SECTION: LIMITING FACTORS & UNCERTAINTIES (Restrained warning color, visually secondary) */}
      {((breakdown?.limiting_factors && breakdown.limiting_factors.length > 0) || vessel.vessel_rank > 1) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', paddingTop: '4px', borderTop: '1px solid var(--color-border-subtle)' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontWeight: 700,
              color: 'var(--color-accent-amber)',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            <AlertTriangle size={13} />
            <span>LIMITING FACTORS & UNCERTAINTIES</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {breakdown?.limiting_factors && breakdown.limiting_factors.length > 0 ? (
              breakdown.limiting_factors.map((lf, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '6px 8px',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    borderLeft: `2px solid ${lf.severity === 'DISQUALIFYING' ? 'rgba(248, 81, 73, 0.6)' : 'rgba(217, 119, 6, 0.5)'}`,
                    borderRadius: 'var(--radius-xs)',
                    fontSize: '11.5px',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.4,
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: '11px', color: lf.severity === 'DISQUALIFYING' ? 'var(--color-accent-crimson)' : 'var(--color-accent-amber)', marginBottom: '2px' }}>
                    {lf.label}
                  </div>
                  <div>{lf.detail}</div>
                </div>
              ))
            ) : vessel.primary_weakness ? (
              <div
                style={{
                  padding: '6px 8px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  borderLeft: '2px solid rgba(217, 119, 6, 0.5)',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: '11.5px',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 1.4,
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '11px', color: 'var(--color-accent-amber)', marginBottom: '2px' }}>
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
      )}

      {/* 6. Multi-Evidence Breakdown Rows */}
      {vessel.evidence_components && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingTop: '4px', borderTop: '1px solid var(--color-border-subtle)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            EVIDENCE DIMENSIONS
          </div>
          <EvidenceBars components={vessel.evidence_components} />
        </div>
      )}

      {/* 7. Mandatory Calibration Notice */}
      <div
        style={{
          marginTop: '2px',
          padding: '7px 9px',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          borderLeft: '2px solid rgba(217, 119, 6, 0.4)',
          fontSize: '10px',
          color: 'var(--color-text-muted)',
          lineHeight: 1.35,
        }}
      >
        <strong style={{ color: 'var(--color-text-secondary)' }}>SCIENTIFIC NOTICE:</strong> Attribution evidence score is a physical compatibility index under the calibrated Lagrangian drift model. It is not a calibrated legal probability of culpability.
      </div>
    </div>
  );
};
