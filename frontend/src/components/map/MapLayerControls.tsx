import React from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { Layers, Eye, EyeOff } from 'lucide-react';

export const MapLayerControls: React.FC = () => {
  const mapLayers = useInvestigationStore((s) => s.mapLayers);
  const setMapLayerVisibility = useInvestigationStore((s) => s.setMapLayerVisibility);

  const layers = [
    { key: 'sarRaster' as const, label: 'SAR Imagery (S-1 σ°)' },
    { key: 'slickPolygons' as const, label: 'Segmented Slicks' },
    { key: 'aisTracks' as const, label: 'AIS Vessel Tracks' },
    { key: 'driftParticles' as const, label: 'Lagrangian Particles' },
    { key: 'candidateMarkers' as const, label: 'Hypothesis Locations' },
  ];

  return (
    <div
      style={{
        position: 'absolute',
        top: '16px',
        left: '16px',
        zIndex: 10,
        backgroundColor: 'rgba(17, 22, 32, 0.90)',
        backdropFilter: 'blur(4px)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-sm)',
        padding: '8px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        boxShadow: 'var(--shadow-md)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: 'var(--text-2xs)',
          fontWeight: 700,
          color: 'var(--color-text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          borderBottom: '1px solid var(--color-border-subtle)',
          paddingBottom: '4px',
        }}
      >
        <Layers size={12} color="var(--color-accent-blue)" />
        Map Layers
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {layers.map(({ key, label }) => {
          const visible = mapLayers[key];
          return (
            <button
              key={key}
              role="switch"
              aria-checked={visible}
              aria-label={`Toggle ${label}`}
              onClick={() => setMapLayerVisibility(key, !visible)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
                fontSize: 'var(--text-xs)',
                color: visible ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                padding: '2px 0',
                cursor: 'pointer',
              }}
            >
              <span>{label}</span>
              {visible ? <Eye size={12} color="var(--color-accent-blue)" /> : <EyeOff size={12} color="var(--color-text-muted)" />}
            </button>
          );
        })}
      </div>
    </div>
  );
};
