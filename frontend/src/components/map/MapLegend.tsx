import React from 'react';

export const MapLegend: React.FC = () => {
  const items = [
    {
      label: 'Incident (T₀)',
      symbol: (
        <span
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            border: '2px solid var(--color-accent-crimson)',
            backgroundColor: 'rgba(248, 81, 73, 0.3)',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Oil Slick',
      symbol: (
        <span
          style={{
            width: '12px',
            height: '8px',
            borderRadius: '2px',
            border: '1px solid #f0aa28',
            backgroundColor: 'rgba(210, 153, 34, 0.55)',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'AIS Track',
      symbol: (
        <span
          style={{
            width: '14px',
            height: '2px',
            backgroundColor: '#388bfd',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Backward Drift',
      symbol: (
        <span
          style={{
            width: '14px',
            height: '2px',
            backgroundColor: '#a855f7',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Hypothesis (4D)',
      symbol: (
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#f85149',
            border: '1px solid #ffffff',
            display: 'inline-block',
          }}
        />
      ),
    },
  ];

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '12px',
        right: '16px',
        zIndex: 10,
        backgroundColor: 'rgba(10, 13, 19, 0.90)',
        backdropFilter: 'blur(4px)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-xs)',
        padding: '6px 10px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        fontSize: 'var(--text-2xs)',
        boxShadow: 'var(--shadow-md)',
      }}
    >
      <span
        style={{
          fontWeight: 700,
          color: 'var(--color-text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          fontSize: '9px',
        }}
      >
        LEGEND
      </span>
      <div style={{ width: '1px', height: '12px', backgroundColor: 'var(--color-border-subtle)' }} />
      {items.map((item, idx) => (
        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          {item.symbol}
          <span style={{ color: 'var(--color-text-primary)' }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
};
