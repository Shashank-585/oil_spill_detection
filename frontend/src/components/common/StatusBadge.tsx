import React from 'react';

export type StatusTone = 'emerald' | 'amber' | 'crimson' | 'blue' | 'neutral';

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
  size?: 'sm' | 'md';
}

const TONE_STYLES: Record<StatusTone, { bg: string; border: string; text: string }> = {
  emerald: {
    bg: 'rgba(125, 156, 121, 0.15)',
    border: 'rgba(125, 156, 121, 0.4)',
    text: 'var(--color-success)',
  },
  amber: {
    bg: 'rgba(209, 178, 124, 0.15)',
    border: 'rgba(209, 178, 124, 0.4)',
    text: 'var(--color-accent-sand)',
  },
  crimson: {
    bg: 'rgba(184, 111, 82, 0.15)',
    border: 'rgba(184, 111, 82, 0.4)',
    text: 'var(--color-warning-rust)',
  },
  blue: {
    bg: 'rgba(95, 145, 138, 0.15)',
    border: 'rgba(95, 145, 138, 0.4)',
    text: 'var(--color-accent-teal)',
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
