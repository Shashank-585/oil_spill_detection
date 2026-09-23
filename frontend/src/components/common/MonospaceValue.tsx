import React from 'react';

interface MonospaceValueProps {
  value: string | number | null | undefined;
  unit?: string;
  className?: string;
}

export const MonospaceValue: React.FC<MonospaceValueProps> = ({ value, unit, className = '' }) => {
  if (value === null || value === undefined || value === '') {
    return <span style={{ color: 'var(--color-text-muted)' }}>—</span>;
  }

  return (
    <span
      className={`font-mono ${className}`}
      style={{
        color: 'var(--color-text-monospace)',
        fontSize: 'inherit',
        letterSpacing: '-0.02em',
      }}
    >
      {value}
      {unit && (
        <span
          style={{
            marginLeft: '4px',
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--text-2xs)',
            textTransform: 'uppercase',
          }}
        >
          {unit}
        </span>
      )}
    </span>
  );
};
