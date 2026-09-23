import React from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useSpillComparisonsQuery, type SpillComparisonItem } from '../../api/casesApi';
import { useInvestigationStore } from '../../store/investigationStore';
import { MonospaceValue } from '../common/MonospaceValue';
import { GitCompare, AlertTriangle, RefreshCw, CheckCircle2, ChevronRight, X, Clock } from 'lucide-react';

export const CounterfactualViewer: React.FC<{ onClose?: () => void }> = ({ onClose }) => {
  const { activeCaseId, activeCase, isAttributionUnavailable } = useActiveCase();
  const selectedHypothesisId = useInvestigationStore((s) => s.selectedHypothesisId);
  const setSelectedHypothesisId = useInvestigationStore((s) => s.setSelectedHypothesisId);
  const setSelectedMmsi = useInvestigationStore((s) => s.setSelectedMmsi);
  const inspectorOpen = useInvestigationStore((s) => s.inspectorOpen);
  const toggleInspector = useInvestigationStore((s) => s.toggleInspector);

  const {
    data: comparisons,
    isLoading,
    isError,
  } = useSpillComparisonsQuery(activeCaseId, undefined, !isAttributionUnavailable);

  const handleSelectComparison = (comp: SpillComparisonItem) => {
    setSelectedHypothesisId(comp.hypothesis_id);
    if (comp.mmsi) {
      setSelectedMmsi(comp.mmsi);
    }
    if (!inspectorOpen) {
      toggleInspector();
    }
  };

  // Group or prioritize selected hypothesis comparison, or find top IoU
  const selectedComp = comparisons?.find((c) => c.hypothesis_id === selectedHypothesisId) || comparisons?.[0];

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
          <GitCompare size={16} color="var(--color-accent-cyan)" />
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
              FORWARD SIMULATION & COUNTERFACTUAL COMPARISONS
            </span>
            <span
              style={{
                fontSize: 'var(--text-2xs)',
                color: 'var(--color-text-muted)',
                marginLeft: '12px',
              }}
            >
              {comparisons ? `${comparisons.length} Forward Simulations vs Observed SAR Slicks` : ''}
            </span>
          </div>
        </div>

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
            title="Close Viewer"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Body Content */}
      <div style={{ overflowY: 'auto', flex: 1, padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
              FORWARD SIMULATIONS UNAVAILABLE FOR THIS CASE
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', maxWidth: '480px', lineHeight: 1.5 }}>
              Case <strong style={{ color: 'var(--color-text-primary)' }}>{activeCase?.name || activeCase?.case_id}</strong> is configured as a physical validation benchmark. Forward hydrodynamic counterfactual spill comparisons were not computed for this scenario.
            </div>
          </div>
        ) : isLoading ? (
          <div style={{ padding: '36px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
            <RefreshCw size={18} className="animate-spin" style={{ display: 'inline', marginRight: '8px' }} />
            Loading forward simulation comparison metrics...
          </div>
        ) : isError || !comparisons || comparisons.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
            No forward simulation comparison artifacts found for this case.
          </div>
        ) : (
          <>
            {/* Top Detail Card for Selected / Top Comparison */}
            {selectedComp && (
              <div
                style={{
                  backgroundColor: 'rgba(17, 22, 32, 0.75)',
                  border: '1px solid var(--color-border-strong)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '14px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-cyan)' }}>
                      HYPOTHESIS {selectedComp.hypothesis_id}
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                      Vessel: <strong>{selectedComp.vessel_name || 'N/A'}</strong> (MMSI <MonospaceValue value={selectedComp.mmsi} />)
                    </span>
                  </div>
                  <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                    Observed Slick: <strong style={{ color: 'var(--color-accent-amber)' }}>{selectedComp.observed_slick_id}</strong>
                  </span>
                </div>

                {/* Metric Badges Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Intersection over Union (IoU)
                    </div>
                    <div className="font-mono" style={{ fontSize: 'var(--text-lg)', fontWeight: 800, color: selectedComp.iou > 0.1 ? 'var(--color-accent-emerald)' : 'var(--color-accent-blue)' }}>
                      {(selectedComp.iou * 100).toFixed(2)}%
                    </div>
                    <div style={{ width: '100%', height: '4px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.min(selectedComp.iou * 100 * 2, 100)}%`, height: '100%', backgroundColor: 'var(--color-accent-blue)' }} />
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Centroid Displacement
                    </div>
                    <div className="font-mono" style={{ fontSize: 'var(--text-lg)', fontWeight: 800, color: (selectedComp.centroid_error_m ?? 999) < 200 ? 'var(--color-accent-emerald)' : 'var(--color-text-primary)' }}>
                      {typeof selectedComp.centroid_error_m === 'number' ? `${selectedComp.centroid_error_m.toFixed(1)} m` : 'N/A'}
                    </div>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                      Mean Particle Dist: {typeof selectedComp.mean_particle_distance_m === 'number' ? `${selectedComp.mean_particle_distance_m.toFixed(1)} m` : 'N/A'}
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Slick Area Envelope
                    </div>
                    <div className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-primary)' }}>
                      Pred: {selectedComp.predicted_area_m2 ? `${(selectedComp.predicted_area_m2 / 1000).toFixed(1)}k m²` : 'N/A'}
                    </div>
                    <div className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-accent-amber)', marginTop: '2px' }}>
                      Obs: {selectedComp.observed_area_m2 ? `${(selectedComp.observed_area_m2 / 1000).toFixed(1)}k m²` : 'N/A'}
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Simulation Window
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                      <Clock size={12} />
                      <span>{selectedComp.simulation_duration_hours ?? 2.0} hours</span>
                    </div>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                      Particles: {selectedComp.particle_count ?? 500} (Coverage: {((selectedComp.coverage ?? 0) * 100).toFixed(0)}%)
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Comparison Records Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', color: 'var(--color-text-muted)', fontSize: 'var(--text-2xs)', textTransform: 'uppercase' }}>
                    <th style={{ padding: '8px 10px' }}>Hypothesis</th>
                    <th style={{ padding: '8px 10px' }}>Vessel</th>
                    <th style={{ padding: '8px 10px' }}>MMSI</th>
                    <th style={{ padding: '8px 10px' }}>Obs Slick</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>IoU</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Centroid Error</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Coverage</th>
                    <th style={{ padding: '8px 10px' }}>Release Time (UTC)</th>
                    <th style={{ padding: '8px 10px', width: '40px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {comparisons.slice(0, 30).map((comp, idx) => {
                    const isSelected = comp.hypothesis_id === selectedHypothesisId;
                    return (
                      <tr
                        key={`${comp.hypothesis_id}-${idx}`}
                        onClick={() => handleSelectComparison(comp)}
                        style={{
                          borderBottom: '1px solid rgba(36, 48, 66, 0.4)',
                          backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => {
                          if (!isSelected) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                      >
                        <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-accent-cyan)' }}>
                          {comp.hypothesis_id}
                        </td>
                        <td style={{ padding: '8px 10px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {comp.vessel_name || 'N/A'}
                        </td>
                        <td style={{ padding: '8px 10px' }}>
                          <MonospaceValue value={comp.mmsi} />
                        </td>
                        <td style={{ padding: '8px 10px', color: 'var(--color-accent-amber)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-2xs)' }}>
                          {comp.observed_slick_id}
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700, color: comp.iou > 0.1 ? 'var(--color-accent-emerald)' : 'var(--color-text-primary)' }}>
                          {(comp.iou * 100).toFixed(2)}%
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                          {typeof comp.centroid_error_m === 'number' ? `${comp.centroid_error_m.toFixed(1)} m` : '—'}
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                          {typeof comp.coverage === 'number' ? `${(comp.coverage * 100).toFixed(0)}%` : '—'}
                        </td>
                        <td style={{ padding: '8px 10px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
                          <MonospaceValue value={comp.release_timestamp ? comp.release_timestamp.split('.')[0].replace('T', ' ') : 'N/A'} />
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                          {isSelected ? <CheckCircle2 size={14} color="var(--color-accent-cyan)" /> : <ChevronRight size={14} />}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Footer */}
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
          <strong style={{ color: 'var(--color-accent-cyan)' }}>PHYSICAL FIDELITY:</strong> Forward simulation runs forward 500-particle Lagrangian dispersion from each candidate release point to observation time.
        </span>
        <span>Showing top evaluated counterfactuals.</span>
      </div>
    </div>
  );
};
