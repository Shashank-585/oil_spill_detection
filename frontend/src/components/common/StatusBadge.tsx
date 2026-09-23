import React from 'react';

export type StatusTone = 'emerald' | 'amber' | 'crimson' | 'blue' | 'neutral';

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
  size?: 'sm' | 'md';
}

const TONE_STYLES: Record<StatusTone, { bg: string; border: string; text: string }> = {
  emerald: {
    bg: 'rgba(46, 160, 67, 0.15)',
    border: 'rgba(46, 160, 67, 0.4)',
    text: 'var(--color-accent-emerald)',
  },
  amber: {
    bg: 'rgba(210, 153, 34, 0.15)',
    border: 'rgba(210, 153, 34, 0.4)',
    text: 'var(--color-accent-amber)',
  },
  crimson: {
    bg: 'rgba(248, 81, 73, 0.15)',
    border: 'rgba(248, 81, 73, 0.4)',
    text: 'var(--color-accent-crimson)',
  },
  blue: {
    bg: 'rgba(56, 139, 253, 0.15)',
    border: 'rgba(56, 139, 253, 0.4)',
    text: 'var(--color-accent-blue)',
  },
  neutral: {
    bg: 'var(--tag-neutral-bg)',
    border: 'var(--tag-neutral-border)',
    text: 'var(--tag-neutral-text)',
  },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ label, tone = 'neutral', size = 'sm' }) => {
  const styles = TONE_STYLES[tone];
  const isSm = size === 'sm';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: isSm ? '1px 6px' : '2px 8px',
        fontSize: isSm ? 'var(--text-2xs)' : 'var(--text-xs)',
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        borderRadius: 'var(--radius-xs)',
        backgroundColor: styles.bg,
        border: `1px solid ${styles.border}`,
        color: styles.text,
        lineHeight: 1.2,
      }}
    >
      {label}
    </span>
  );
};
