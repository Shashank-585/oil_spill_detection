import React, { useState } from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { useSpillComparisonsQuery } from '../../api/casesApi';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { CandidatePreview } from '../attribution/CandidatePreview';
import { CandidateComparisonModal } from '../attribution/CandidateComparisonModal';
import {
  X,
  ChevronRight,
  FileSearch,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

export const InspectorDrawer: React.FC = () => {
  const inspectorOpen = useInvestigationStore((s) => s.inspectorOpen);
  const toggleInspector = useInvestigationStore((s) => s.toggleInspector);
  const selectedMmsi = useInvestigationStore((s) => s.selectedMmsi);
  const setSelectedMmsi = useInvestigationStore((s) => s.setSelectedMmsi);
  const selectedHypothesisId = useInvestigationStore((s) => s.selectedHypothesisId);
  const setSelectedHypothesisId = useInvestigationStore((s) => s.setSelectedHypothesisId);

  const [comparisonModalOpen, setComparisonModalOpen] = useState(false);

  const {
    activeCaseId,
    activeCase,
    isLoadingCaseDetail,
    caseDetailError,
    hasAttribution,
    isAttributionUnavailable,
    isLoadingAttribution,
    attributionRanking,
    topCandidate,
    candidateCount,
  } = useActiveCase();

  // Find candidate corresponding to selected MMSI, or fallback to top candidate
  const currentCandidate =
    (selectedMmsi
      ? attributionRanking?.find((c) => c.mmsi === selectedMmsi)
      : topCandidate) || topCandidate;

  // Active hypothesis ID for forward simulation lookup
  const currentHypothesisId =
    selectedHypothesisId || currentCandidate?.best_hypothesis_id;

  // Forward simulation comparisons query for the hypothesis
  const { data: comparisons } = useSpillComparisonsQuery(
    activeCaseId,
    currentHypothesisId || undefined,
    Boolean(currentHypothesisId) && !isAttributionUnavailable
  );

  const currentComp = comparisons?.[0];

  if (!inspectorOpen) {
    return (
      <button
        onClick={toggleInspector}
        style={{
          position: 'absolute',
          right: 0,
          top: '60px',
          zIndex: 20,
          backgroundColor: 'var(--color-bg-surface-raised)',
          border: '1px solid var(--color-border-subtle)',
          borderRight: 'none',
          padding: '8px 4px',
          borderTopLeftRadius: 'var(--radius-sm)',
          borderBottomLeftRadius: 'var(--radius-sm)',
          color: 'var(--color-text-secondary)',
          display: 'flex',
          alignItems: 'center',
          boxShadow: 'var(--shadow-md)',
          cursor: 'pointer',
        }}
        title="Open Forensic Inspector"
      >
        <ChevronRight size={16} style={{ transform: 'rotate(180deg)' }} />
      </button>
    );
  }

  return (
    <aside
      style={{
        width: 'var(--inspector-width)',
        height: '100%',
        backgroundColor: 'var(--color-bg-surface)',
        borderLeft: '1px solid var(--color-border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 15,
        boxShadow: 'var(--shadow-panel)',
        flexShrink: 0,
        overflowY: 'auto',
      }}
    >
      {/* Panel Title Bar */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--color-bg-base)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileSearch size={16} color="var(--color-accent-blue)" />
          <span
            style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 700,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--color-text-primary)',
            }}
          >
            FORENSIC INVESTIGATION PANEL
          </span>
        </div>
        <button
          onClick={toggleInspector}
          style={{ color: 'var(--color-text-muted)', cursor: 'pointer', padding: '2px', background: 'none', border: 'none' }}
          title="Collapse Inspector"
        >
          <X size={15} />
        </button>
      </div>

      {/* Continuous Forensic Surface */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {/* SECTION 1: CASE BRIEF */}
        <section style={{ padding: '14px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div
            style={{
              fontSize: 'var(--text-2xs)',
              fontWeight: 700,
              color: 'var(--color-text-muted)',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              marginBottom: '10px',
            }}
          >
            INCIDENT PROFILE
          </div>

          {caseDetailError ? (
            <div
              style={{
                padding: '10px',
                backgroundColor: 'rgba(248, 81, 73, 0.1)',
                border: '1px solid var(--color-accent-crimson)',
                borderRadius: 'var(--radius-xs)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-accent-crimson)',
              }}
            >
              <strong>Error Loading Case:</strong> {caseDetailError.message}
            </div>
          ) : isLoadingCaseDetail ? (
            <div style={{ padding: '10px 0', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              <RefreshCw size={12} className="animate-spin" style={{ display: 'inline', marginRight: '6px' }} />
              Syncing case profile...
            </div>
          ) : activeCase ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: 'var(--text-xs)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>Incident:</span>
                <span style={{ fontWeight: 600, color: 'var(--color-text-primary)', textAlign: 'right', maxWidth: '65%' }}>
                  {activeCase.name}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>Category:</span>
                <span style={{ color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
                  {activeCase.event?.incident_type ? activeCase.event.incident_type.replace(/_/g, ' ') : 'UNKNOWN'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>Estimated Event T₀:</span>
                <MonospaceValue value={activeCase.event?.estimated_start_utc || activeCase.event?.search_start_utc || 'N/A'} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>Observation T_obs:</span>
                <MonospaceValue value={activeCase.observation?.timestamp_utc || 'N/A'} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>Sensor Scene:</span>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-2xs)' }}>
                  {activeCase.observation?.platform
                    ? `${activeCase.observation.platform} (${activeCase.observation.sensor_mode || 'IW'})`
                    : 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>Ground Truth Quality:</span>
                <StatusBadge
                  label={activeCase.ground_truth_quality ? activeCase.ground_truth_quality.replace(/_/g, ' ') : 'UNCLASSIFIED'}
                  tone={activeCase.ground_truth_quality === 'HIGH_CONFIDENCE' ? 'emerald' : 'amber'}
                  size="sm"
                />
              </div>
            </div>
          ) : null}
        </section>

        {/* SECTION 2: ATTRIBUTION LEADERBOARD / SELECTED CANDIDATE */}
        <section style={{ padding: '14px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '12px',
            }}
          >
            <div
              style={{
                fontSize: 'var(--text-2xs)',
                fontWeight: 700,
                color: 'var(--color-text-muted)',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            >
              ATTRIBUTION STATUS
            </div>
            {hasAttribution && candidateCount > 0 && (
              <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
                {candidateCount} CANDIDATES EVALUATED
              </span>
            )}
          </div>

          {/* Sub-state A: Genuine Dataset Absence (e.g. Case 002) */}
          {isAttributionUnavailable ? (
            <div
              style={{
                padding: '12px',
                backgroundColor: 'rgba(210, 153, 34, 0.08)',
                border: '1px solid rgba(210, 153, 34, 0.3)',
                borderRadius: 'var(--radius-xs)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={14} color="var(--color-accent-amber)" />
                <span
                  style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 700,
                    color: 'var(--color-accent-amber)',
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                  }}
                >
                  AIS ATTRIBUTION
                </span>
              </div>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                ARCHIVE DATA UNAVAILABLE
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                This is a physical validation case. Verified vessel telemetry or drift attribution artifacts were not acquired for this incident benchmark.
              </div>
            </div>
          ) : isLoadingAttribution ? (
            <div
              style={{
                padding: '16px',
                textAlign: 'center',
                color: 'var(--color-text-muted)',
                fontSize: 'var(--text-xs)',
              }}
            >
              <RefreshCw size={13} className="animate-spin" style={{ display: 'inline', marginRight: '6px' }} />
              Syncing attribution rankings...
            </div>
          ) : currentCandidate ? (
            <>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  backgroundColor: currentCandidate.vessel_rank === 1 ? 'rgba(56, 139, 253, 0.08)' : 'rgba(255, 255, 255, 0.04)',
                  border: `1px solid ${currentCandidate.vessel_rank === 1 ? 'rgba(56, 139, 253, 0.25)' : 'var(--color-border-subtle)'}`,
                  borderRadius: 'var(--radius-xs)',
                  fontSize: 'var(--text-2xs)',
                  color: 'var(--color-text-primary)',
                  marginBottom: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <ShieldCheck size={13} color="var(--color-accent-blue)" />
                  <span>
                    {selectedMmsi && selectedMmsi !== topCandidate?.mmsi
                      ? `Selected Candidate (#${currentCandidate.vessel_rank})`
                      : 'Highest Concordance Candidate (#1)'}
                  </span>
                </div>
                {selectedMmsi && selectedMmsi !== topCandidate?.mmsi && (
                  <button
                    onClick={() => {
                      setSelectedMmsi(null);
                      setSelectedHypothesisId(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-accent-blue)',
                      fontSize: '9px',
                      cursor: 'pointer',
                      padding: '2px',
                    }}
                  >
                    RESET TO #1
                  </button>
                )}
              </div>

              {/* Candidate Evidentiary Details */}
              <CandidatePreview
                vessel={currentCandidate}
                onOpenComparison={() => setComparisonModalOpen(true)}
              />
            </>
          ) : (
            <div
              style={{
                padding: '12px',
                backgroundColor: 'var(--color-bg-surface-raised)',
                borderRadius: 'var(--radius-xs)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-muted)',
              }}
            >
              No candidate vessels found in candidate generation results.
            </div>
          )}
        </section>

        {/* SECTION 3: 4D HYPOTHESIS INSPECTOR & FORWARD SIMULATION */}
        {currentHypothesisId && !isAttributionUnavailable && (
          <section style={{ padding: '14px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px',
              }}
            >
              <div
                style={{
                  fontSize: 'var(--text-2xs)',
                  fontWeight: 700,
                  color: 'var(--color-text-muted)',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                }}
              >
                4D HYPOTHESIS & FORWARD VALIDATION
              </div>
              <span className="font-mono" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-accent-cyan)', fontWeight: 700 }}>
                {currentHypothesisId}
              </span>
            </div>

            {currentComp ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: 'var(--text-xs)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>Release Origin:</span>
                  <span className="font-mono" style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-2xs)' }}>
                    {currentComp.predicted_centroid_lat?.toFixed(4)}, {currentComp.predicted_centroid_lon?.toFixed(4)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>Release Timestamp:</span>
                  <MonospaceValue value={currentComp.release_timestamp ? currentComp.release_timestamp.split('.')[0].replace('T', ' ') : 'N/A'} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>Observed Slick Ref:</span>
                  <span className="font-mono" style={{ color: 'var(--color-accent-amber)' }}>
                    {currentComp.observed_slick_id}
                  </span>
                </div>

                {/* Physical Validation Metrics Table */}
                <div
                  style={{
                    marginTop: '6px',
                    padding: '8px 10px',
                    backgroundColor: 'rgba(10, 13, 19, 0.7)',
                    border: '1px solid var(--color-border-subtle)',
                    borderRadius: 'var(--radius-xs)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-2xs)' }}>Intersection over Union (IoU):</span>
                    <span className="font-mono" style={{ fontWeight: 700, color: currentComp.iou > 0.1 ? 'var(--color-accent-emerald)' : 'var(--color-accent-cyan)' }}>
                      {(currentComp.iou * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-2xs)' }}>Centroid Displacement:</span>
                    <span className="font-mono" style={{ color: 'var(--color-text-primary)' }}>
                      {typeof currentComp.centroid_error_m === 'number' ? `${currentComp.centroid_error_m.toFixed(1)} m` : 'N/A'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-2xs)' }}>Particle Coverage:</span>
                    <span className="font-mono" style={{ color: 'var(--color-text-primary)' }}>
                      {typeof currentComp.coverage === 'number' ? `${(currentComp.coverage * 100).toFixed(0)}%` : 'N/A'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-2xs)' }}>Area (Pred / Obs):</span>
                    <span className="font-mono" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
                      {currentComp.predicted_area_m2 ? `${(currentComp.predicted_area_m2 / 1000).toFixed(1)}k` : '—'} / {currentComp.observed_area_m2 ? `${(currentComp.observed_area_m2 / 1000).toFixed(1)}k m²` : '—'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', padding: '6px 0' }}>
                Hypothesis <strong style={{ color: 'var(--color-accent-cyan)' }}>{currentHypothesisId}</strong> selected. Forward hydrodynamic simulation metrics syncing...
              </div>
            )}
          </section>
        )}
      </div>

      {/* Candidate Comparison Modal */}
      {comparisonModalOpen && currentCandidate && attributionRanking && (
        <CandidateComparisonModal
          candidates={attributionRanking}
          initialCandidateA={topCandidate}
          initialCandidateB={currentCandidate}
          onClose={() => setComparisonModalOpen(false)}
        />
      )}
    </aside>
  );
};
