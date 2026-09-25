import React from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useUncertaintyQuery } from '../../api/casesApi';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { DomainTooltip } from '../common/DomainTooltip';
import { HelpCircle, AlertTriangle, ShieldAlert, RefreshCw, X } from 'lucide-react';

export const UncertaintyView: React.FC<{ onClose?: () => void }> = ({ onClose }) => {
  const { activeCaseId, activeCase } = useActiveCase();
  const {
    data: uncertainty,
    isLoading,
    isError,
  } = useUncertaintyQuery(activeCaseId);

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
          <HelpCircle size={16} color="var(--color-accent-amber)" />
          <div>
            <DomainTooltip term="Uncertainty" inline>
              <span
                style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                }}
              >
                MONTE CARLO UNCERTAINTY & RANK STABILITY ANALYSIS
              </span>
            </DomainTooltip>
            <span
              style={{
                fontSize: 'var(--text-2xs)',
                color: 'var(--color-text-muted)',
                marginLeft: '12px',
              }}
            >
              {uncertainty ? `Ensemble N=${uncertainty.ensemble_size} Perturbations · Seed ${uncertainty.random_seed}` : ''}
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
            title="Close View"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Body Content */}
      <div style={{ overflowY: 'auto', flex: 1, padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {isError || !uncertainty ? (
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
              UNCERTAINTY ENSEMBLE DATA UNAVAILABLE FOR THIS CASE
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', maxWidth: '480px', lineHeight: 1.5 }}>
              Case <strong style={{ color: 'var(--color-text-primary)' }}>{activeCase?.name || activeCaseId}</strong> does not possess Monte Carlo uncertainty perturbation artifacts.
            </div>
          </div>
        ) : isLoading ? (
          <div style={{ padding: '36px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
            <RefreshCw size={18} className="animate-spin" style={{ display: 'inline', marginRight: '8px' }} />
            Loading Monte Carlo uncertainty metrics...
          </div>
        ) : (
          <>
            {/* Calibration Audit Alert Banner */}
            <div
              style={{
                padding: '12px 16px',
                backgroundColor: 'rgba(210, 153, 34, 0.08)',
                border: '1px solid rgba(210, 153, 34, 0.35)',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                gap: '12px',
                alignItems: 'flex-start',
              }}
            >
              <ShieldAlert size={20} color="var(--color-accent-amber)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-amber)', textTransform: 'uppercase' }}>
                  CALIBRATION AUDIT: {uncertainty.calibration_audit.calibration_status}
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                  {uncertainty.calibration_audit.mandatory_scientific_notice}
                </div>
              </div>
            </div>

            {/* Rank Stability Distribution Table */}
            <div>
              <div
                style={{
                  fontSize: 'var(--text-2xs)',
                  fontWeight: 700,
                  color: 'var(--color-text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  marginBottom: '8px',
                }}
              >
                CANDIDATE HYPOTHESIS RANK STABILITY UNDER ENVIRONMENTAL PERTURBATION
              </div>

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
                    <th style={{ padding: '8px 10px' }}>Hypothesis ID</th>
                    <th style={{ padding: '8px 10px' }}>Vessel Name</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Top-1 Frequency</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Top-3 Frequency</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Mean Rank</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Std Dev</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Mean Score</th>
                    <th style={{ padding: '8px 10px' }}>Stability Classification</th>
                  </tr>
                </thead>
                <tbody>
                  {uncertainty.rank_stability_top_hypotheses.map((item, idx) => (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid rgba(36, 48, 66, 0.4)',
                      }}
                    >
                      <td style={{ padding: '8px 10px' }}>
                        <MonospaceValue value={item.hypothesis_id || 'N/A'} />
                      </td>
                      <td style={{ padding: '8px 10px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                        {item.vessel_name || 'UNKNOWN'}
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {((item.top_1_frequency || 0) * 100).toFixed(1)}%
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {((item.top_3_frequency || 0) * 100).toFixed(1)}%
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                        {item.mean_rank?.toFixed(2) || '—'}
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                        ±{item.std_rank?.toFixed(2) || '0.00'}
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {item.mean_score?.toFixed(4) || '—'}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <StatusBadge
                          label={item.rank_stability_category || 'MODERATE'}
                          tone={
                            item.rank_stability_category === 'HIGH_STABILITY'
                              ? 'emerald'
                              : item.rank_stability_category === 'MODERATE_STABILITY'
                              ? 'amber'
                              : 'neutral'
                          }
                          size="sm"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Scientific Notice Footer */}
      <div
        style={{
          padding: '8px 18px',
          borderTop: '1px solid var(--color-border-subtle)',
          backgroundColor: 'var(--color-bg-base)',
          fontSize: 'var(--text-2xs)',
          color: 'var(--color-text-muted)',
        }}
      >
        <span>
          <strong style={{ color: 'var(--color-accent-amber)' }}>METHODOLOGY NOTE:</strong> Monte Carlo uncertainty models environmental current/wind perturbations to audit rank stability across stochastic physical realizations.
        </span>
      </div>
    </div>
  );
};
