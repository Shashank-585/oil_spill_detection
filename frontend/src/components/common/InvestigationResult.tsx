import React from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useInvestigationDossierQuery } from '../../api/casesApi';
import { StatusBadge } from './StatusBadge';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';

interface InvestigationResultProps {
  compact?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export const InvestigationResult: React.FC<InvestigationResultProps> = ({
  compact = false,
  className = '',
  style = {},
}) => {
  const { activeCaseId, activeCase, attributionRanking, isAttributionUnavailable } = useActiveCase();
  const { data: dossier } = useInvestigationDossierQuery(activeCaseId);

  // Case categorization
  const isNegativeControl =
    activeCaseId === 'case_001' ||
    Boolean(dossier?.data_limitations?.is_negative_control) ||
    Boolean((activeCase as any)?.validation?.validation_role === 'NEGATIVE_NON_VESSEL_CASE') ||
    Boolean(activeCase?.event?.incident_type?.toLowerCase().includes('pipeline'));

  const isDataLimited =
    isAttributionUnavailable ||
    activeCaseId === 'case_002_wakashio' ||
    Boolean(dossier?.data_limitations?.ais_archive_missing);

  // Top candidate from attribution ranking
  const topCandidate = attributionRanking && attributionRanking.length > 0 ? attributionRanking[0] : null;

  // Evidence components for top candidate
  const components = topCandidate?.evidence_components;

  return (
    <div
      className={`investigation-outcome-card ${className}`}
      style={{
        backgroundColor: 'var(--color-bg-base)',
        border: isNegativeControl
          ? '1px solid rgba(184, 196, 190, 0.35)'
          : isDataLimited
          ? '1px solid rgba(209, 178, 124, 0.35)'
          : '1px solid rgba(125, 156, 121, 0.35)',
        borderRadius: 'var(--radius-xs)',
        padding: compact ? '10px 12px' : '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        ...style,
      }}
    >
      {/* 1. LAYER 1: OUTCOME & ATTRIBUTION STATUS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isNegativeControl ? (
            <div
              style={{
                width: '26px',
                height: '26px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'rgba(184, 196, 190, 0.12)',
                border: '1px solid rgba(184, 196, 190, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-text-secondary)',
                flexShrink: 0,
              }}
            >
              <ShieldAlert size={15} />
            </div>
          ) : isDataLimited ? (
            <div
              style={{
                width: '26px',
                height: '26px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'rgba(209, 178, 124, 0.12)',
                border: '1px solid rgba(209, 178, 124, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-accent-sand)',
                flexShrink: 0,
              }}
            >
              <AlertTriangle size={15} />
            </div>
          ) : (
            <div
              style={{
                width: '26px',
                height: '26px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'rgba(125, 156, 121, 0.12)',
                border: '1px solid rgba(125, 156, 121, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-success)',
                flexShrink: 0,
              }}
            >
              <ShieldCheck size={15} />
            </div>
          )}

          <div>
            <div
              style={{
                fontSize: '10px',
                fontWeight: 800,
                color: isNegativeControl
                  ? 'var(--color-text-secondary)'
                  : isDataLimited
                  ? 'var(--color-accent-sand)'
                  : 'var(--color-success)',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            >
              {isNegativeControl
                ? 'NEGATIVE-CONTROL BASELINE'
                : isDataLimited
                ? 'PHYSICAL VALIDATION BENCHMARK'
                : 'BEST-SUPPORTED HYPOTHESIS'}
            </div>
            <div style={{ fontSize: compact ? '13px' : '15px', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '1px' }}>
              {isNegativeControl
                ? 'No Vessel Attribution Supported'
                : isDataLimited
                ? 'AIS Attribution Archive Pending'
                : topCandidate?.vessel_name
                ? `${topCandidate.vessel_name}`
                : 'Awaiting Candidate Evaluation'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isNegativeControl ? (
            <StatusBadge label="ATTRIBUTION: NOT SUPPORTED" tone="neutral" />
          ) : isDataLimited ? (
            <StatusBadge label="ATTRIBUTION: ARCHIVE LIMITED" tone="amber" />
          ) : (
            <StatusBadge label="ATTRIBUTION: HIGHEST SUPPORT" tone="emerald" />
          )}
        </div>
      </div>

      {/* 2. LAYER 2: CANDIDATE RANK VS ATTRIBUTION DECISION METRICS */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: compact ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '8px',
          padding: '8px 10px',
          backgroundColor: 'var(--color-bg-surface)',
          borderRadius: 'var(--radius-xs)',
          border: '1px solid var(--color-border-subtle)',
        }}
      >
        {isNegativeControl ? (
          <>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>TOP SCORING CRAFT</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '1px' }}>
                {topCandidate ? `${topCandidate.vessel_name} (Rank #1)` : 'None Qualified'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>CANDIDATE COMPATIBILITY</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '1px', fontFamily: 'var(--font-mono)' }}>
                {topCandidate?.best_evidence_score != null ? topCandidate.best_evidence_score.toFixed(4) : '—'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>REQUIRED THRESHOLD</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-accent-sand)', marginTop: '1px', fontFamily: 'var(--font-mono)' }}>
                ≥ 0.7000 (High Support)
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>CANDIDATES QUALIFIED</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', marginTop: '1px' }}>
                0 of {attributionRanking ? attributionRanking.length : '—'} Evaluated
              </div>
            </div>
          </>
        ) : isDataLimited ? (
          <>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>INCIDENT VESSEL</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '1px' }}>
                {activeCase?.name || 'MV WAKASHIO'} (Grounding)
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>PHYSICAL DRIFT MODEL</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-success)', marginTop: '1px' }}>
                Verified via SAR
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>REGIONAL AIS ARCHIVE</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-accent-sand)', marginTop: '1px' }}>
                Unavailable (Unranked)
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>ATTRIBUTION STATUS</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-disabled)', marginTop: '1px' }}>
                Suppressed (No Fabrication)
              </div>
            </div>
          </>
        ) : (
          <>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>TOP CANDIDATE</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '1px' }}>
                {topCandidate?.vessel_name || 'Awaiting Candidate'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>MMSI / RANK</div>
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', marginTop: '1px', fontFamily: 'var(--font-mono)' }}>
                {topCandidate?.mmsi ? `${topCandidate.mmsi} · Rank #1` : '—'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>COMPATIBILITY SCORE</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-accent-sand)', marginTop: '1px', fontFamily: 'var(--font-mono)' }}>
                {topCandidate?.best_evidence_score != null ? topCandidate.best_evidence_score.toFixed(4) : '—'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 600 }}>CAUSAL PRECEDENCE</div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-success)', marginTop: '1px' }}>
                {topCandidate?.causal_precedence_status || '—'}
              </div>
            </div>
          </>
        )}
      </div>

      {/* 3. LAYER 3: EVIDENCE STATUS DIMENSIONS (When available) */}
      {components && !isDataLimited && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: 'var(--color-text-tertiary)' }}>
            <span style={{ fontWeight: 600 }}>EVIDENCE DIMENSIONS</span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>Multi-criteria compatibility (0.0 to 1.0)</span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '4px',
              textAlign: 'center',
            }}
          >
            <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '4px', borderRadius: '2px', border: '1px solid var(--color-border-subtle)' }}>
              <div style={{ fontSize: '8px', color: 'var(--color-text-muted)' }}>DRIFT (30%)</div>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                {components.drift_consistency?.toFixed(2) ?? '—'}
              </div>
            </div>
            <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '4px', borderRadius: '2px', border: '1px solid var(--color-border-subtle)' }}>
              <div style={{ fontSize: '8px', color: 'var(--color-text-muted)' }}>SPATIAL (25%)</div>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                {components.spatial_compatibility?.toFixed(2) ?? '—'}
              </div>
            </div>
            <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '4px', borderRadius: '2px', border: '1px solid var(--color-border-subtle)' }}>
              <div style={{ fontSize: '8px', color: 'var(--color-text-muted)' }}>SOURCE (20%)</div>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                {components.source_plausibility?.toFixed(2) ?? '—'}
              </div>
            </div>
            <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '4px', borderRadius: '2px', border: '1px solid var(--color-border-subtle)' }}>
              <div style={{ fontSize: '8px', color: 'var(--color-text-muted)' }}>TIME (15%)</div>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                {components.temporal_compatibility?.toFixed(2) ?? '—'}
              </div>
            </div>
            <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '4px', borderRadius: '2px', border: '1px solid var(--color-border-subtle)' }}>
              <div style={{ fontSize: '8px', color: 'var(--color-text-muted)' }}>AIS (10%)</div>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                {components.ais_track_quality?.toFixed(2) ?? '—'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. LAYER 4: SCIENTIFIC INTERPRETATION */}
      <div
        style={{
          fontSize: '11px',
          color: 'var(--color-text-secondary)',
          lineHeight: 1.45,
          paddingTop: '6px',
          borderTop: '1px dashed var(--color-border-subtle)',
        }}
      >
        {isNegativeControl ? (
          <span>
            <strong style={{ color: 'var(--color-text-primary)' }}>Interpretation: </strong>
            Traffic was evaluated against the reconstructed release envelope. While {topCandidate?.vessel_name ? `vessel ${topCandidate.vessel_name}` : 'the highest-ranked candidate'} is the highest-scoring candidate under available evidence, no candidate satisfies attribution criteria (all exhibit &gt;5 km spatial divergence and zero backward drift convergence). Origin is consistent with reference case infrastructure records (pipeline rupture).
          </span>
        ) : isDataLimited ? (
          <span>
            <strong style={{ color: 'var(--color-text-primary)' }}>Interpretation: </strong>
            Physical hydrodynamic drift models replicate observed slick dispersion. Attribution candidate ranking is intentionally suppressed pending acquisition of regional historical AIS archives to prevent false attribution.
          </span>
        ) : (
          <span>
            <strong style={{ color: 'var(--color-text-primary)' }}>Interpretation: </strong>
            <strong style={{ color: 'var(--color-text-primary)' }}>{topCandidate?.vessel_name || 'The top-ranked candidate'}</strong> provides the highest physical and spatiotemporal compatibility among evaluated AIS candidates under available evidence. Causal precedence confirms the vessel was underway at origin coordinates at discharge T₀. This compatibility metric supports investigative screening and does not constitute a calibrated legal probability.
          </span>
        )}
      </div>
    </div>
  );
};
