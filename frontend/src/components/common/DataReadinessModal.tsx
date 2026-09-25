import React from 'react';
import { DataReadinessPanel } from './DataReadinessPanel';
import { X, ShieldCheck } from 'lucide-react';

interface DataReadinessModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId?: string;
}

export const DataReadinessModal: React.FC<DataReadinessModalProps> = ({
  isOpen,
  onClose,
  caseId,
}) => {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '760px',
          maxHeight: '90vh',
          backgroundColor: 'var(--color-bg-surface-raised)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-subtle)',
          boxShadow: 'var(--shadow-xl)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div
          style={{
            padding: '14px 20px',
            backgroundColor: 'var(--color-bg-base)',
            borderBottom: '1px solid var(--color-border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} color="#3fb950" />
            <span style={{ fontSize: 'var(--text-sm)', fontWeight: 800, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--color-text-primary)' }}>
              INVESTIGATION DATA READINESS & REPRODUCIBLE PROVENANCE AUDIT
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: 'var(--radius-xs)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Content */}
        <div style={{ padding: '20px', overflowY: 'auto' }}>
          <DataReadinessPanel
            caseId={caseId}
            compact={false}
            showHeader={true}
            showProvenance={true}
          />
        </div>
      </div>
    </div>
  );
};
