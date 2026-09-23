import React from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { CausalTagPill } from './CausalTagPill';
import { Users, AlertTriangle, RefreshCw, CheckCircle2, ChevronRight, X } from 'lucide-react';

export const CandidateRankingTable: React.FC<{ onClose?: () => void }> = ({ onClose }) => {
  const selectedMmsi = useInvestigationStore((s) => s.selectedMmsi);
  const setSelectedMmsi = useInvestigationStore((s) => s.setSelectedMmsi);
  const setSelectedHypothesisId = useInvestigationStore((s) => s.setSelectedHypothesisId);
  const inspectorOpen = useInvestigationStore((s) => s.inspectorOpen);
  const toggleInspector = useInvestigationStore((s) => s.toggleInspector);

  const {
    activeCase,
    attributionRanking,
    isLoadingAttribution,
    isAttributionUnavailable,
    candidateCount,
  } = useActiveCase();

  const handleSelectCandidate = (candidate: { mmsi: number; best_hypothesis_id?: string }) => {
    setSelectedMmsi(candidate.mmsi);
    if (candidate.best_hypothesis_id) {
      setSelectedHypothesisId(candidate.best_hypothesis_id);
    }
    if (!inspectorOpen) {
      toggleInspector();
    }
  };

  return (
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
                <th style={{ padding: '8px 10px', width: '60px' }}>Rank</th>
                <th style={{ padding: '8px 10px' }}>Vessel Name</th>
                <th style={{ padding: '8px 10px' }}>MMSI</th>
                <th style={{ padding: '8px 10px' }}>Type</th>
                <th style={{ padding: '8px 10px' }}>Best Hypothesis</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Compatibility</th>
                <th style={{ padding: '8px 10px' }}>Causal Status</th>
                <th style={{ padding: '8px 10px' }}>Support State</th>
                <th style={{ padding: '8px 10px', width: '40px' }}></th>
              </tr>
            </thead>
            <tbody>
              {attributionRanking.map((cand) => {
                const isSelected = cand.mmsi === selectedMmsi;
                return (
                  <tr
                    key={cand.mmsi}
                    onClick={() => handleSelectCandidate(cand)}
                    style={{
                      borderBottom: '1px solid rgba(36, 48, 66, 0.4)',
                      backgroundColor: isSelected ? 'rgba(56, 139, 253, 0.12)' : 'transparent',
                      cursor: 'pointer',
                      transition: 'background-color 0.12s ease',
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
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
                    <td style={{ padding: '10px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                      {isSelected ? <CheckCircle2 size={14} color="var(--color-accent-blue)" /> : <ChevronRight size={14} />}
                    </td>
                  </tr>
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
  );
};
