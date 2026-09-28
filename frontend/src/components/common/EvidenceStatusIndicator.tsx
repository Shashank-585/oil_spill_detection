import React from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useInvestigationStore } from '../../store/investigationStore';
import { type InvestigationStage } from '../../types/workflow';
import { type VesselAttributionItem } from '../../api/casesApi';

export type EvidenceStatusLabel =
  | 'DATA READY'
  | 'PROCESSING'
  | 'EVIDENCE AVAILABLE'
  | 'INVESTIGATION ACTIVE'
  | 'ATTRIBUTION SUPPORTED'
  | 'ATTRIBUTION INCONCLUSIVE'
  | 'NEGATIVE CONTROL'
  | 'REPORT READY';

export interface EvidenceStatusResult {
  label: EvidenceStatusLabel;
  tone: 'emerald' | 'cyan' | 'blue' | 'amber' | 'muted';
  detail: string;
}

export function computeEvidenceStatus(params: {
  activeStage: InvestigationStage;
  activeCaseId: string;
  validationRole?: string | null;
  isAttributionUnavailable?: boolean;
  topCandidate?: VesselAttributionItem;
  hasSar?: boolean;
  hasSlicks?: boolean;
}): EvidenceStatusResult {
  const {
    activeStage,
    activeCaseId,
    validationRole,
    isAttributionUnavailable,
    topCandidate,
    hasSar,
    hasSlicks,
  } = params;

  // 1. Report Stage takes top workflow precedence
  if (activeStage === 'report') {
    return {
      label: 'REPORT READY',
      tone: 'emerald',
      detail: '16-Section Forensic Investigation Dossier Compiled',
    };
  }

  // 2. Negative Control Benchmark (Case 001)
  if (activeCaseId.includes('001') || validationRole === 'negative_control') {
    return {
      label: 'NEGATIVE CONTROL',
      tone: 'blue',
      detail: 'Negative-Control Baseline: No Vessel Attribution Supported',
    };
  }

  // 3. Attribution Data Limitation (Case 002)
  if (isAttributionUnavailable) {
    if (activeStage === 'attribute') {
      return {
        label: 'ATTRIBUTION INCONCLUSIVE',
        tone: 'amber',
        detail: 'Candidate Attribution Suppressed (AIS Archive Pending)',
      };
    }
    return {
      label: 'EVIDENCE AVAILABLE',
      tone: 'cyan',
      detail: 'Satellite Observation & Physical Drift Reconstructed',
    };
  }

  // 4. Attribution Stage (Case 003 / positive benchmark)
  if (activeStage === 'attribute') {
    if (
      topCandidate?.vessel_evidence_state === 'HIGH_SUPPORT' ||
      (topCandidate?.best_evidence_score != null && topCandidate.best_evidence_score >= 0.7)
    ) {
      return {
        label: 'ATTRIBUTION SUPPORTED',
        tone: 'emerald',
        detail: `${topCandidate.vessel_name || 'Rank #1'} Exceeds Attribution Threshold (≥ 0.7000)`,
      };
    }
    if (topCandidate?.best_evidence_score != null && topCandidate.best_evidence_score >= 0.5) {
      return {
        label: 'INVESTIGATION ACTIVE',
        tone: 'cyan',
        detail: 'Moderate Compatibility Under Multi-Horizon Investigation',
      };
    }
    return {
      label: 'ATTRIBUTION INCONCLUSIVE',
      tone: 'amber',
      detail: 'Candidate Compatibility Below Attribution Threshold',
    };
  }

  // 5. Investigation Stage
  if (activeStage === 'investigate') {
    return {
      label: 'INVESTIGATION ACTIVE',
      tone: 'cyan',
      detail: 'Lagrangian Drift Advection & AIS Vessel Correlation Active',
    };
  }

  // 6. Observe Stage
  if (hasSar && hasSlicks) {
    return {
      label: 'EVIDENCE AVAILABLE',
      tone: 'cyan',
      detail: 'SAR Dark-Spot Polygons & Initial AIS Tracks Synchronized',
    };
  }

  return {
    label: 'DATA READY',
    tone: 'muted',
    detail: 'Copernicus Sentinel-1 Observation Stream Synchronized',
  };
}

export const EvidenceStatusIndicator: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const activeStage = useInvestigationStore((s) => s.activeStage);
  const {
    activeCaseId,
    activeCase,
    isAttributionUnavailable,
    topCandidate,
    hasSar,
    hasSlicks,
  } = useActiveCase();

  const status = computeEvidenceStatus({
    activeStage,
    activeCaseId,
    validationRole: activeCase?.validation_role,
    isAttributionUnavailable,
    topCandidate,
    hasSar,
    hasSlicks,
  });

  const toneColors = {
    emerald: {
      bg: 'rgba(125, 156, 121, 0.15)',
      border: 'rgba(125, 156, 121, 0.40)',
      text: '#7D9C79',
      dot: '#7D9C79',
    },
    cyan: {
      bg: 'rgba(120, 175, 165, 0.15)',
      border: 'rgba(120, 175, 165, 0.40)',
      text: '#78AFA5',
      dot: '#78AFA5',
    },
    blue: {
      bg: 'rgba(184, 196, 190, 0.12)',
      border: 'rgba(184, 196, 190, 0.35)',
      text: '#B8C4BE',
      dot: '#D1B27C',
    },
    amber: {
      bg: 'rgba(209, 178, 124, 0.15)',
      border: 'rgba(209, 178, 124, 0.40)',
      text: '#D1B27C',
      dot: '#D1B27C',
    },
    muted: {
      bg: 'rgba(125, 156, 121, 0.12)',
      border: 'rgba(125, 156, 121, 0.30)',
      text: '#7D9C79',
      dot: '#7D9C79',
    },
  }[status.tone];

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: compact ? '2px 6px' : '3px 8px',
        height: '24px',
        backgroundColor: toneColors.bg,
        border: `1px solid ${toneColors.border}`,
        borderRadius: 'var(--radius-xs)',
        fontSize: '10px',
        fontFamily: 'var(--font-mono)',
        whiteSpace: 'nowrap',
        userSelect: 'none',
        boxSizing: 'border-box',
      }}
      title={`Investigation Status: ${status.label} — ${status.detail}`}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: toneColors.dot,
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontWeight: 700,
          letterSpacing: '0.04em',
          color: toneColors.text,
        }}
      >
        {status.label}
      </span>
    </div>
  );
};
