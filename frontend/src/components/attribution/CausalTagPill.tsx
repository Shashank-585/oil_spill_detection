import React from 'react';
import type { CausalPrecedenceStatus } from '../../types/attribution';

interface CausalTagPillProps {
  status: CausalPrecedenceStatus;
}

export const CausalTagPill: React.FC<CausalTagPillProps> = ({ status }) => {
  let bg = 'var(--tag-neutral-bg)';
  let border = 'var(--tag-neutral-border)';
  let color = 'var(--tag-neutral-text)';
  let text = status;

  if (status === 'VALID_PRE_EVENT' || status === 'VALID_ACTIVE_WINDOW' || status === 'AT_RELEASE') {
    bg = 'var(--tag-pre-event-bg)';
    border = 'var(--tag-pre-event-border)';
    color = 'var(--tag-pre-event-text)';
  } else if (status === 'INELIGIBLE_POST_EVENT' || status === 'AFTER_EVENT' || status === 'INCOMPATIBLE') {
    bg = 'var(--tag-post-event-bg)';
    border = 'var(--tag-post-event-border)';
    color = 'var(--tag-post-event-text)';
  }

  return (
    <span
      className="font-mono"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 6px',
        fontSize: 'var(--text-2xs)',
        fontWeight: 700,
        borderRadius: 'var(--radius-xs)',
        backgroundColor: bg,
        border: `1px solid ${border}`,
        color: color,
        letterSpacing: '0.02em',
      }}
    >
      {text}
    </span>
  );
};
