import React, { useState } from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { CausalTagPill } from './CausalTagPill';
import { CandidateComparisonModal } from './CandidateComparisonModal';
import type { VesselAttributionItem } from '../../api/casesApi';
import {
  Users,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  X,
  GitCompare,
  HelpCircle,
} from 'lucide-react';

export const CandidateRankingTable: React.FC<{ onClose?: () => void }> = ({ onClose }) => {
  const selectedMmsi = useInvestigationStore((s) => s.selectedMmsi);
  const setSelectedMmsi = useInvestigationStore((s) => s.setSelectedMmsi);
  const setSelectedHypothesisId = useInvestigationStore((s) => s.setSelectedHypothesisId);
  const setActiveWorkspace = useInvestigationStore((s) => s.setActiveWorkspace);
  const inspectorOpen = useInvestigationStore((s) => s.inspectorOpen);
  const toggleInspector = useInvestigationStore((s) => s.toggleInspector);

  const {
    activeCase,
    attributionRanking,
    isLoadingAttribution,
    isAttributionUnavailable,
    candidateCount,
  } = useActiveCase();

  // Explainability & Comparison Modal State
  const [comparisonModalOpen, setComparisonModalOpen] = useState(false);
  const [compareTarget, setCompareTarget] = useState<VesselAttributionItem | undefined>();
  const [expandedMmsi, setExpandedMmsi] = useState<Set<number>>(new Set());

  const toggleExpand = (mmsi: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedMmsi((prev) => {
      const next = new Set(prev);
      if (next.has(mmsi)) {
        next.delete(mmsi);
      } else {
        next.add(mmsi);
      }
      return next;
    });
  };

  const handleSelectCandidate = (candidate: { mmsi: number; best_hypothesis_id?: string }) => {
    setSelectedMmsi(candidate.mmsi);
    if (candidate.best_hypothesis_id) {
      setSelectedHypothesisId(candidate.best_hypothesis_id);
    }
    if (!inspectorOpen) {
      toggleInspector();
    }
  };

  const handleOpenComparison = (candidate?: VesselAttributionItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setCompareTarget(candidate);
    setComparisonModalOpen(true);
  };

  const formatDistance = (m?: number | null) => {
    if (m === undefined || m === null) return '—';
    if (m >= 1000) return `${(m / 1000).toFixed(2)} km`;
    return `${m.toFixed(1)} m`;
  };

  const topCandidate = attributionRanking?.find((c) => c.vessel_rank === 1);

  return (
    <>
      <div
        style={{
          position: 'absolute',
          top: '60px',
          left: '20px',
          right: '20px',
          maxHeight: 'calc(100% - 120px)',
          backgroundColor: 'rgba(10, 13, 19, 0.96)',
          backdropFilter: 'blur(8px)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-xl)',
          zIndex: 25,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header Bar */}
        <div
          style={{
            padding: '12px 18px',
            borderBottom: '1px solid var(--color-border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: 'var(--color-bg-base)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Users size={16} color="var(--color-accent-blue)" />
            <div>
              <span
                style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                }}
              >
                CANDIDATE VESSEL ATTRIBUTION RANKINGS
              </span>
              <span
                style={{
                  fontSize: 'var(--text-2xs)',
                  color: 'var(--color-text-muted)',
                  marginLeft: '12px',
                }}
              >
                {candidateCount > 0 ? `${candidateCount} Evaluated Candidates · Backend Deterministic Order` : ''}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {attributionRanking && attributionRanking.length > 1 && (
              <button
                onClick={(e) => handleOpenComparison(undefined, e)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: 'rgba(56, 189, 248, 0.12)',
                  border: '1px solid rgba(56, 189, 248, 0.35)',
                  borderRadius: 'var(--radius-xs)',
                  color: 'var(--color-accent-cyan)',
                  padding: '5px 12px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease',
                }}
                title="Compare Top Candidate with another candidate side-by-side"
              >
                <GitCompare size={13} />
                <span>Compare Candidates</span>
              </button>
            )}

            {onClose && (
              <button
                onClick={onClose}
                style={{
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  background: 'none',
                  border: 'none',
                  padding: '4px',
                }}
                title="Close Table"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Table Content */}
        <div style={{ overflowY: 'auto', flex: 1, padding: '12px 18px' }}>
          {isAttributionUnavailable ? (
            <div
              style={{
                padding: '24px',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <AlertTriangle size={28} color="var(--color-accent-amber)" />
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                AIS ATTRIBUTION DATA UNAVAILABLE FOR THIS CASE
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', maxWidth: '480px', lineHeight: 1.5 }}>
                Case <strong style={{ color: 'var(--color-text-primary)' }}>{activeCase?.name || activeCase?.case_id}</strong> is configured as a physical validation or infrastructure incident. Verified candidate vessel AIS telemetry was not acquired for this incident benchmark.
              </div>
            </div>
          ) : isLoadingAttribution ? (
            <div style={{ padding: '36px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
              <RefreshCw size={18} className="animate-spin" style={{ display: 'inline', marginRight: '8px' }} />
              Loading forensic attribution rankings...
            </div>
          ) : attributionRanking && attributionRanking.length > 0 ? (
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 'var(--text-xs)',
                textAlign: 'left',
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: '1px solid var(--color-border-subtle)',
                    color: 'var(--color-text-muted)',
                    fontSize: 'var(--text-2xs)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  <th style={{ padding: '8px 10px', width: '50px' }}>Rank</th>
                  <th style={{ padding: '8px 10px' }}>Vessel Name</th>
                  <th style={{ padding: '8px 10px' }}>MMSI</th>
                  <th style={{ padding: '8px 10px' }}>Type</th>
                  <th style={{ padding: '8px 10px' }}>Best Hypothesis</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Compatibility</th>
                  <th style={{ padding: '8px 10px' }}>Causal Status</th>
                  <th style={{ padding: '8px 10px' }}>Support State</th>
                  <th style={{ padding: '8px 10px', textAlign: 'center' }}>Explain</th>
                  <th style={{ padding: '8px 10px', textAlign: 'center' }}>Actions</th>
                  <th style={{ padding: '8px 10px', width: '30px' }}></th>
                </tr>
              </thead>
              <tbody>
                {attributionRanking.map((cand) => {
                  const isSelected = cand.mmsi === selectedMmsi;
                  const isExpanded = expandedMmsi.has(cand.mmsi);
                  const metrics = cand.underlying_metrics;
                  const breakdown = cand.evidence_breakdown;

                  return (
                    <React.Fragment key={cand.mmsi}>
                      <tr
                        onClick={() => handleSelectCandidate(cand)}
                        style={{
                          borderBottom: isExpanded ? 'none' : '1px solid rgba(36, 48, 66, 0.4)',
                          backgroundColor: isSelected ? 'rgba(56, 139, 253, 0.12)' : isExpanded ? 'rgba(255, 255, 255, 0.02)' : 'transparent',
                          cursor: 'pointer',
                          transition: 'background-color 0.12s ease',
                        }}
                        onMouseEnter={(e) => {
                          if (!isSelected && !isExpanded) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected && !isExpanded) e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                      >
                        <td style={{ padding: '10px', fontWeight: 800, color: cand.vessel_rank === 1 ? 'var(--color-accent-blue)' : 'var(--color-text-secondary)' }}>
                          #{cand.vessel_rank}
                        </td>
                        <td style={{ padding: '10px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {cand.vessel_name}
                        </td>
                        <td style={{ padding: '10px' }}>
                          <MonospaceValue value={cand.mmsi} />
                        </td>
                        <td style={{ padding: '10px', color: 'var(--color-text-secondary)', fontSize: 'var(--text-2xs)' }}>
                          {cand.vessel_type || 'UNKNOWN'}
                        </td>
                        <td style={{ padding: '10px' }}>
                          <span className="font-mono" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-monospace)' }}>
                            {cand.best_hypothesis_id || '—'}
                          </span>
                        </td>
                        <td style={{ padding: '10px', textAlign: 'right', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                          <span style={{ color: cand.vessel_rank === 1 ? 'var(--color-accent-blue)' : 'var(--color-text-primary)' }}>
                            {typeof cand.best_evidence_score === 'number' ? cand.best_evidence_score.toFixed(4) : '—'}
                          </span>
                        </td>
                        <td style={{ padding: '10px' }}>
                          <CausalTagPill status={cand.causal_precedence_status || 'UNKNOWN'} />
                        </td>
                        <td style={{ padding: '10px' }}>
                          <StatusBadge
                            label={cand.vessel_evidence_state ? cand.vessel_evidence_state.replace(/_/g, ' ') : 'UNCLASSIFIED'}
                            tone={
                              cand.vessel_evidence_state === 'HIGH_SUPPORT'
                                ? 'emerald'
                                : cand.vessel_evidence_state === 'MODERATE_SUPPORT'
                                ? 'amber'
                                : 'neutral'
                            }
                            size="sm"
                          />
                        </td>

                        {/* Explain Toggle Column */}
                        <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                          <button
                            onClick={(e) => toggleExpand(cand.mmsi, e)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              backgroundColor: isExpanded ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                              border: `1px solid ${isExpanded ? 'rgba(56, 189, 248, 0.4)' : 'var(--color-border-subtle)'}`,
                              borderRadius: 'var(--radius-xs)',
                              color: isExpanded ? 'var(--color-accent-cyan)' : 'var(--color-text-secondary)',
                              padding: '3px 8px',
                              fontSize: '10px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                            title="Expand Why / Why-Not Evidence Breakdown"
                          >
                            <HelpCircle size={11} />
                            <span>Why?</span>
                            {isExpanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                          </button>
                        </td>

                        {/* Actions (Test Run + Compare) */}
                        <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectCandidate(cand);
                                setActiveWorkspace('evidence');
                              }}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                backgroundColor: 'rgba(56, 189, 248, 0.12)',
                                border: '1px solid rgba(56, 189, 248, 0.35)',
                                borderRadius: 'var(--radius-xs)',
                                color: 'var(--color-accent-cyan)',
                                padding: '3px 7px',
                                fontSize: '10px',
                                fontWeight: 600,
                                cursor: 'pointer',
                              }}
                              title={`Run Counterfactual Forward Simulation for ${cand.vessel_name}`}
                            >
                              <GitCompare size={10} />
                              <span>Simulate</span>
                            </button>

                            <button
                              onClick={(e) => handleOpenComparison(cand, e)}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                border: '1px solid var(--color-border-subtle)',
                                borderRadius: 'var(--radius-xs)',
                                color: 'var(--color-text-secondary)',
                                padding: '3px 7px',
                                fontSize: '10px',
                                fontWeight: 600,
                                cursor: 'pointer',
                              }}
                              title={`Compare ${cand.vessel_name} side-by-side with top candidate`}
                            >
                              <span>Compare</span>
                            </button>
                          </div>
                        </td>

                        <td style={{ padding: '10px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                          {isSelected ? <CheckCircle2 size={14} color="var(--color-accent-blue)" /> : <ChevronRight size={14} />}
                        </td>
                      </tr>

                      {/* Expandable Why / Why-Not Evidence Row */}
                      {isExpanded && (
                        <tr style={{ backgroundColor: 'rgba(17, 24, 39, 0.75)', borderBottom: '1px solid rgba(36, 48, 66, 0.6)' }}>
                          <td colSpan={11} style={{ padding: '12px 18px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.2fr 0.8fr', gap: '14px' }}>
                              {/* Why Ranked Highly */}
                              <div
                                style={{
                                  padding: '10px 12px',
                                  backgroundColor: 'rgba(34, 197, 94, 0.04)',
                                  borderRadius: 'var(--radius-sm)',
                                  border: '1px solid rgba(34, 197, 94, 0.2)',
                                }}
                              >
                                <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-accent-emerald)', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <CheckCircle2 size={12} />
                                  <span>WHY THIS HYPOTHESIS?</span>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                                  {breakdown?.why_ranked_highly && breakdown.why_ranked_highly.length > 0 ? (
                                    breakdown.why_ranked_highly.map((item, idx) => (
                                      <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '5px', lineHeight: 1.35 }}>
                                        <span style={{ color: 'var(--color-accent-emerald)', fontWeight: 700 }}>✓</span>
                                        <span>{item}</span>
                                      </div>
                                    ))
                                  ) : (
                                    <span>Consistent backward drift and spatiotemporal alignment.</span>
                                  )}
                                  {cand.primary_strength && (
                                    <div style={{ marginTop: '4px', fontSize: '10px', color: 'var(--color-text-primary)' }}>
                                      <strong style={{ color: 'var(--color-accent-emerald)' }}>Strength:</strong> {cand.primary_strength}
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Why Not Ranked Higher / Limiting Evidence */}
                              <div
                                style={{
                                  padding: '10px 12px',
                                  backgroundColor: 'rgba(210, 153, 34, 0.04)',
                                  borderRadius: 'var(--radius-sm)',
                                  border: '1px solid rgba(210, 153, 34, 0.2)',
                                }}
                              >
                                <div style={{ fontSize: '10px', fontWeight: 700, color: cand.vessel_rank === 1 ? 'var(--color-text-muted)' : 'var(--color-accent-amber)', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <AlertTriangle size={12} />
                                  <span>{cand.vessel_rank === 1 ? 'LIMITING FACTORS' : 'WHY NOT HIGHER? (LIMITING FACTORS)'}</span>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                                  {breakdown?.limiting_factors && breakdown.limiting_factors.length > 0 ? (
                                    breakdown.limiting_factors.map((lf, idx) => (
                                      <div
                                        key={idx}
                                        style={{
                                          padding: '4px 6px',
                                          backgroundColor: lf.severity === 'DISQUALIFYING' ? 'rgba(248, 81, 73, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                                          borderLeft: `2px solid ${lf.severity === 'DISQUALIFYING' ? 'var(--color-accent-red)' : 'var(--color-accent-amber)'}`,
                                          borderRadius: 'var(--radius-2xs)',
                                          lineHeight: 1.3,
                                        }}
                                      >
                                        <div style={{ fontWeight: 700, color: lf.severity === 'DISQUALIFYING' ? 'var(--color-accent-red)' : 'var(--color-accent-amber)', fontSize: '10px' }}>
                                          {lf.label}
                                        </div>
                                        <div style={{ fontSize: '10px' }}>{lf.detail}</div>
                                      </div>
                                    ))
                                  ) : cand.primary_weakness ? (
                                    <div>• {cand.primary_weakness}</div>
                                  ) : (
                                    <div style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>
                                      No disqualifying factors. Best-supported hypothesis overall.
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Snapshot Metrics & Compare CTA */}
                              <div
                                style={{
                                  padding: '10px 12px',
                                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                  borderRadius: 'var(--radius-sm)',
                                  border: '1px solid var(--color-border-subtle)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  justifyContent: 'space-between',
                                  gap: '8px',
                                }}
                              >
                                <div>
                                  <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                                    UNDERLYING METRICS
                                  </div>
                                  <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)', display: 'flex', flexDirection: 'column', gap: '3px', fontFamily: 'var(--font-mono)' }}>
                                    <div>Source Dist: <span style={{ color: 'var(--color-text-primary)' }}>{formatDistance(metrics?.vessel_source_distance_m)}</span></div>
                                    <div>Centroid Err: <span style={{ color: 'var(--color-text-primary)' }}>{metrics?.centroid_error_m !== undefined && metrics?.centroid_error_m !== null ? `${metrics.centroid_error_m.toFixed(1)} m` : '—'}</span></div>
                                    <div>AIS Quality: <span style={{ color: 'var(--color-text-primary)' }}>{metrics?.ais_track_quality || 'continuous'}</span></div>
                                    <div>Causal Status: <span style={{ color: 'var(--color-text-primary)' }}>{cand.causal_precedence_status || 'UNKNOWN'}</span></div>
                                  </div>
                                </div>

                                <button
                                  onClick={(e) => handleOpenComparison(cand, e)}
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '6px',
                                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                                    border: '1px solid rgba(56, 189, 248, 0.3)',
                                    borderRadius: 'var(--radius-xs)',
                                    color: 'var(--color-accent-cyan)',
                                    padding: '5px 8px',
                                    fontSize: '10px',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                  }}
                                >
                                  <GitCompare size={12} />
                                  <span>Side-by-Side Compare</span>
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
              No evaluated candidates found in the attribution repository.
            </div>
          )}
        </div>

        {/* Mandatory Scientific Notice Footer */}
        <div
          style={{
            padding: '8px 18px',
            borderTop: '1px solid var(--color-border-subtle)',
            backgroundColor: 'var(--color-bg-base)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: 'var(--text-2xs)',
            color: 'var(--color-text-muted)',
          }}
        >
          <span>
            <strong style={{ color: 'var(--color-accent-amber)' }}>SCIENTIFIC NOTICE:</strong> Compatibility is a physical concordance index derived from backward/forward Lagrangian drift models.
          </span>
          <span>Ranking order reflects backend evaluation with causal consistency rules enabled.</span>
        </div>
      </div>

      {/* Candidate Comparison Modal */}
      {comparisonModalOpen && attributionRanking && attributionRanking.length > 0 && (
        <CandidateComparisonModal
          candidates={attributionRanking}
          initialCandidateA={topCandidate}
          initialCandidateB={compareTarget}
          onClose={() => setComparisonModalOpen(false)}
        />
      )}
    </>
  );
};
