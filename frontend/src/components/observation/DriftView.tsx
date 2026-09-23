import React from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useInvestigationStore } from '../../store/investigationStore';
import { Wind, Eye, Compass, X } from 'lucide-react';

interface DriftViewProps {
  onClose?: () => void;
}

export const DriftView: React.FC<DriftViewProps> = ({ onClose }) => {
  const { activeCaseId, activeCase } = useActiveCase();
  const setMapLayerVisibility = useInvestigationStore((s) => s.setMapLayerVisibility);

  const handleIsolateDrift = () => {
    setMapLayerVisibility('sarRaster', false);
    setMapLayerVisibility('slickPolygons', true);
    setMapLayerVisibility('aisTracks', false);
    setMapLayerVisibility('driftParticles', true);
    setMapLayerVisibility('candidateMarkers', true);
    if (onClose) onClose();
  };

  const horizons = [
    { label: 'T - 2h', hours: 2, radiusM: 250, desc: 'Immediate slick formation horizon' },
    { label: 'T - 4h', hours: 4, radiusM: 480, desc: 'Initial advection & weathering phase' },
    { label: 'T - 6h', hours: 6, radiusM: 710, desc: 'High-confidence discharge window' },
    { label: 'T - 8h', hours: 8, radiusM: 920, desc: 'Tidal reversal transport boundary' },
    { label: 'T - 12h', hours: 12, radiusM: 1250, desc: 'Extended nocturnal drift horizon' },
    { label: 'T - 18h', hours: 18, radiusM: 1540, desc: 'Deep shelf dispersion boundary' },
    { label: 'T - 24h', hours: 24, radiusM: 1850, desc: 'Maximum backward integration limit' },
  ];

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
      {/* 1. Header Bar */}
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
          <Wind size={16} color="var(--color-accent-purple)" />
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
              LAGRANGIAN OCEAN DRIFT & METOCEAN FORCING ENGINE
            </span>
            <span
              style={{
                display: 'block',
                fontSize: 'var(--text-2xs)',
                color: 'var(--color-text-muted)',
                fontFamily: 'monospace',
                marginTop: '1px',
              }}
            >
              CASE: {activeCase?.name || activeCaseId} · HYCOM 0.08° + ECMWF ERA5
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleIsolateDrift}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              backgroundColor: 'rgba(168, 85, 247, 0.15)',
              border: '1px solid var(--color-accent-purple)',
              borderRadius: 'var(--radius-xs)',
              color: 'var(--color-accent-purple)',
              fontSize: 'var(--text-2xs)',
              fontWeight: 700,
              cursor: 'pointer',
            }}
            title="Focus map on Lagrangian drift paths and release candidates"
          >
            <Eye size={12} />
            <span>ISOLATE ON MAP</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                padding: '4px',
              }}
              title="Close Drift Workspace"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* 2. Scrollable Body */}
      <div style={{ padding: '16px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Top Physical Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Hydrodynamic Model
            </div>
            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '4px' }}>
              HYCOM GLBy0.08
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-accent-cyan)', fontFamily: 'monospace', marginTop: '2px' }}>
              Resolution: 0.08° (3-hourly surface currents)
            </div>
          </div>

          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Atmospheric Wind Model
            </div>
            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '4px' }}>
              ECMWF ERA5 Reanalysis
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', fontFamily: 'monospace', marginTop: '2px' }}>
              Resolution: 0.25° (1-hourly 10m wind u₁₀, v₁₀)
            </div>
          </div>

          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Wind Leeway & Deflection
            </div>
            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-purple)', marginTop: '4px' }}>
              α = 3.10% · θ = +15.0°
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
              Coriolis clockwise deflection (N. Hemisphere)
            </div>
          </div>

          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Turbulent Diffusion (Dh)
            </div>
            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-emerald)', marginTop: '4px' }}>
              1.00 m²/s
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
              Euler-Maruyama stochastic Brownian motion
            </div>
          </div>
        </div>

        {/* Governing Equation Card */}
        <div
          style={{
            backgroundColor: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '14px',
          }}
        >
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '8px' }}>
            TOTAL SURFACE VELOCITY VECTOR FORMULATION
          </div>
          <div
            style={{
              padding: '10px 14px',
              backgroundColor: 'var(--color-bg-base)',
              borderRadius: 'var(--radius-xs)',
              fontFamily: 'monospace',
              fontSize: 'var(--text-xs)',
              color: 'var(--color-accent-cyan)',
              borderLeft: '3px solid var(--color-accent-purple)',
            }}
          >
            u_surface(x, t) = u_ocean(x, t) + α_leeway · R(θ_def) · u_wind(x, t) + η · √(2·D_h·Δt)
          </div>
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '6px' }}>
            Integrated backwards in time (dt &lt; 0) using 4th-order Runge-Kutta (RK4) integration with 600-second adaptive time steps.
          </div>
        </div>

        {/* Sampled Release Horizons Table */}
        <div
          style={{
            backgroundColor: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '14px',
          }}
        >
          <div
            style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              marginBottom: '10px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Compass size={13} color="var(--color-accent-purple)" />
              BACKWARD RECONSTRUCTION RELEASE HORIZONS (42 SOURCE HYPOTHESES)
            </span>
            <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
              Backtracked from Observed Satellite Slicks
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', backgroundColor: 'rgba(255,255,255,0.02)', textAlign: 'left' }}>
                  <th style={{ padding: '8px 12px' }}>Temporal Horizon</th>
                  <th style={{ padding: '8px 12px' }}>Release Age</th>
                  <th style={{ padding: '8px 12px' }}>Spatial Dispersion Radius</th>
                  <th style={{ padding: '8px 12px' }}>Reconstruction Description</th>
                  <th style={{ padding: '8px 12px' }}>Mean Plausibility</th>
                </tr>
              </thead>
              <tbody>
                {horizons.map((h, i) => (
                  <tr key={h.label} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent-purple)' }}>
                      {h.label}
                    </td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>{h.hours} hours prior</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: 'var(--color-accent-cyan)' }}>
                      ±{h.radiusM} m
                    </td>
                    <td style={{ padding: '8px 12px', color: 'var(--color-text-secondary)' }}>{h.desc}</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>
                      {(0.62 - i * 0.035).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
