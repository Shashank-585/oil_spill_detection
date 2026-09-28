import React from 'react';
import type { EvidenceComponents } from '../../types/attribution';

interface EvidenceBarsProps {
  components: EvidenceComponents;
}

interface EvidenceRowConfig {
  key: keyof EvidenceComponents;
  label: string;
  weight: string;
}

const ROWS: EvidenceRowConfig[] = [
  { key: 'drift_consistency', label: 'Drift Consistency', weight: '30%' },
  { key: 'spatial_compatibility', label: 'Spatial Compatibility', weight: '25%' },
  { key: 'source_plausibility', label: 'Source Plausibility', weight: '20%' },
  { key: 'temporal_compatibility', label: 'Temporal Alignment', weight: '15%' },
  { key: 'ais_track_quality', label: 'AIS Track Quality', weight: '10%' },
];

export const EvidenceBars: React.FC<EvidenceBarsProps> = ({ components }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '9px', marginTop: '6px' }}>
      {ROWS.map(({ key, label, weight }) => {
        const val = components[key] ?? 0;
        const pct = Math.min(Math.max(val * 100, 0), 100);

        return (
          <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                fontSize: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                <span style={{ color: 'var(--color-text-primary)', fontWeight: 500 }}>
                  {label}
                </span>
                <span
                  style={{
                    color: 'var(--color-text-muted)',
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)',
                    backgroundColor: 'rgba(255, 255, 255, 0.04)',
                    padding: '0 4px',
                    borderRadius: '2px',
                  }}
                >
                  {weight}
                </span>
              </div>
              <span
                className="font-mono"
                style={{
                  fontSize: '13px',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  letterSpacing: '0.02em',
                }}
              >
                {val.toFixed(2)}
              </span>
            </div>

            {/* Consistent Evidence Dimension Bar */}
            <div
              style={{
                width: '100%',
                height: '4px',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                borderRadius: '2px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  backgroundColor: val >= 0.7 ? 'var(--color-accent-sand)' : val >= 0.5 ? 'var(--color-accent-teal)' : 'var(--color-border)',
                  borderRadius: '2px',
                  transition: 'width 0.25s ease',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
