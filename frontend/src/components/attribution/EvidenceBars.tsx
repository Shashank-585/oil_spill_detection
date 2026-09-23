import React from 'react';
import type { EvidenceComponents } from '../../types/attribution';
import { MonospaceValue } from '../common/MonospaceValue';

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
      {ROWS.map(({ key, label, weight }) => {
        const val = components[key] ?? 0;
        const pct = Math.min(Math.max(val * 100, 0), 100);

        return (
          <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                fontSize: 'var(--text-xs)',
              }}
            >
              <span style={{ color: 'var(--color-text-secondary)' }}>
                {label} <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-2xs)' }}>({weight})</span>
              </span>
              <MonospaceValue value={val.toFixed(2)} />
            </div>

            <div
              style={{
                width: '100%',
                height: '4px',
                backgroundColor: 'var(--color-bg-base)',
                borderRadius: 'var(--radius-xs)',
                overflow: 'hidden',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  backgroundColor: val >= 0.7 ? 'var(--color-accent-blue)' : val >= 0.5 ? 'var(--color-accent-cyan)' : 'var(--color-text-muted)',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
