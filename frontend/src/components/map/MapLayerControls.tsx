import React, { useState } from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { Layers, ChevronDown, ChevronUp, CheckSquare, Square } from 'lucide-react';

export const MapLayerControls: React.FC = () => {
  const mapLayers = useInvestigationStore((s) => s.mapLayers);
  const setMapLayerVisibility = useInvestigationStore((s) => s.setMapLayerVisibility);
  const [isOpen, setIsOpen] = useState(false);

  const layers = [
    { key: 'sarRaster' as const, label: 'SAR Imagery' },
    { key: 'slickPolygons' as const, label: 'Detected Slicks' },
    { key: 'aisTracks' as const, label: 'AIS Vessel Tracks' },
    { key: 'driftParticles' as const, label: 'Lagrangian Particles' },
    { key: 'candidateMarkers' as const, label: 'Hypothesis Locations' },
  ];

  return (
    <div
      style={{
        position: 'absolute',
        top: '12px',
        left: '12px',
        zIndex: 10,
        backgroundColor: 'rgba(10, 13, 19, 0.92)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-xs)',
        boxShadow: 'var(--shadow-md)',
        userSelect: 'none',
        backdropFilter: 'blur(6px)',
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 8px',
          fontSize: '11px',
          fontWeight: 700,
          color: isOpen ? 'var(--color-accent-blue)' : 'var(--color-text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          cursor: 'pointer',
          background: 'none',
          border: 'none',
          borderRadius: 'var(--radius-xs)',
        }}
        title="Toggle Map Layers Panel"
      >
        <Layers size={13} color="var(--color-accent-blue)" />
        <span>LAYERS</span>
        {isOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {isOpen && (
        <div
          style={{
            padding: '4px 6px 6px 6px',
            borderTop: '1px solid var(--color-border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
            minWidth: '176px',
          }}
        >
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
                  gap: '8px',
                  fontSize: '11px',
                  color: visible ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                  padding: '3px 6px',
                  cursor: 'pointer',
                  background: 'none',
                  border: 'none',
                  borderRadius: '2px',
                  textAlign: 'left',
                  transition: 'background-color 0.12s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                {visible ? (
                  <CheckSquare size={13} color="var(--color-accent-blue)" style={{ flexShrink: 0 }} />
                ) : (
                  <Square size={13} color="var(--color-text-muted)" style={{ flexShrink: 0 }} />
                )}
                <span style={{ fontWeight: visible ? 500 : 400 }}>{label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
