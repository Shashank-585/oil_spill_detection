import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

export type DomainTerm =
  | 'SAR'
  | 'AIS'
  | '4D hypothesis'
  | 'IoU'
  | 'Causal consistency'
  | 'Uncertainty';

export const DOMAIN_GLOSSARY: Record<
  DomainTerm,
  { title: string; abbreviation?: string; definition: string; practicalContext: string }
> = {
  SAR: {
    title: 'Synthetic Aperture Radar (SAR)',
    abbreviation: 'Sentinel-1 C-band (5.405 GHz)',
    definition:
      'Day/night, cloud-penetrating active microwave satellite sensor. Floating petroleum dampens wind-generated capillary waves, creating distinctive low-backscatter dark patches on the ocean surface.',
    practicalContext:
      'The operational detector runs strictly on VV co-polarization to maximize slick-to-background ocean contrast.',
  },
  AIS: {
    title: 'Automatic Identification System (AIS)',
    abbreviation: 'VHF / Satellite Transponder Network',
    definition:
      'Autonomous marine broadcast system transmitting vessel identity (MMSI), GPS positions, course, speed, and navigational status at regular intervals.',
    practicalContext:
      'Used to reconstruct historical vessel traffic within the spatio-temporal search window surrounding the oil slick.',
  },
  '4D hypothesis': {
    title: '4D Spatiotemporal Release Hypothesis',
    abbreviation: 'Space-Time Trajectory: (x, y, z, t)',
    definition:
      'A candidate release event evaluating whether a vessel at a specific coordinate and historical timestamp could physically produce the detected slick under environmental forces.',
    practicalContext:
      'Simulated via Lagrangian particle tracking forced by hourly HYCOM currents and ERA5 wind vectors.',
  },
  IoU: {
    title: 'Intersection over Union (IoU)',
    abbreviation: 'Spatial Overlap Metric',
    definition:
      'Calculates the area of overlap between forward-simulated dispersed oil particles and the observed satellite slick polygon divided by their total combined union area.',
    practicalContext:
      'IoU > 10% represents strong physical alignment in chaotic open-ocean hydrodynamic environments.',
  },
  'Causal consistency': {
    title: 'Causal Precedence & Temporal Consistency',
    abbreviation: 'Physical Plausibility Filter',
    definition:
      'Prunes physically impossible candidates (e.g. vessels arriving after slick was already observed, or traveling too far downwind to have caused discharge).',
    practicalContext:
      'Enforces strict chronological arrow of time before computing evidence rankings.',
  },
  Uncertainty: {
    title: 'Monte Carlo Uncertainty & Rank Stability',
    abbreviation: '100-Run Ensemble Perturbation',
    definition:
      'Perturbs wind leeway coefficients and current velocity vectors across repeated Monte Carlo runs to test whether the top-ranked vessel remains #1 under metocean forecast noise.',
    practicalContext:
      'Provides decision-makers with a calibrated stability percentage rather than an overconfident single-point estimate.',
  },
};

interface DomainTooltipProps {
  term: DomainTerm;
  children?: React.ReactNode;
  showIcon?: boolean;
  inline?: boolean;
  placement?: 'top' | 'right' | 'bottom' | 'left';
  underline?: boolean;
}

export const DomainTooltip: React.FC<DomainTooltipProps> = ({
  term,
  children,
  showIcon = false,
  inline = true,
  placement = 'top',
  underline = true,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const entry = DOMAIN_GLOSSARY[term];

  if (!entry) return <>{children}</>;

  const getPositionStyles = (): React.CSSProperties => {
    switch (placement) {
      case 'right':
        return {
          top: '50%',
          left: 'calc(100% + 10px)',
          transform: 'translateY(-50%)',
        };
      case 'left':
        return {
          top: '50%',
          right: 'calc(100% + 10px)',
          transform: 'translateY(-50%)',
        };
      case 'bottom':
        return {
          top: 'calc(100% + 6px)',
          left: '50%',
          transform: 'translateX(-50%)',
        };
      case 'top':
      default:
        return {
          bottom: 'calc(100% + 6px)',
          left: '50%',
          transform: 'translateX(-50%)',
        };
    }
  };

  return (
    <span
      style={{
        position: 'relative',
        display: inline ? 'inline-flex' : 'flex',
        alignItems: 'center',
        gap: '4px',
        cursor: 'help',
      }}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
      tabIndex={0}
      role="tooltip"
      aria-label={`${entry.title}: ${entry.definition}`}
    >
      <span
        style={{
          borderBottom: underline && children ? '1px dotted rgba(88, 166, 255, 0.6)' : 'none',
          color: 'inherit',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '3px',
        }}
      >
        {children || term}
      </span>

      {showIcon && (
        <HelpCircle
          size={11}
          color="var(--color-accent-blue)"
          style={{ opacity: 0.8, flexShrink: 0 }}
        />
      )}

      {/* Floating Tooltip Card */}
      {isVisible && (
        <div
          style={{
            position: 'absolute',
            ...getPositionStyles(),
            width: '280px',
            backgroundColor: 'rgba(13, 17, 23, 0.98)',
            border: '1px solid var(--color-accent-blue)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px',
            boxShadow: 'var(--shadow-xl)',
            zIndex: 1000,
            pointerEvents: 'none',
            fontSize: 'var(--text-xs)',
            lineHeight: 1.45,
            color: 'var(--color-text-primary)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
            <strong style={{ color: 'var(--color-accent-cyan)', fontSize: '11px', textTransform: 'uppercase' }}>
              {entry.title}
            </strong>
          </div>

          {entry.abbreviation && (
            <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', fontFamily: 'monospace', marginBottom: '6px' }}>
              {entry.abbreviation}
            </div>
          )}

          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginBottom: '6px' }}>
            {entry.definition}
          </div>

          <div
            style={{
              fontSize: '10px',
              backgroundColor: 'rgba(56, 139, 253, 0.1)',
              padding: '4px 6px',
              borderRadius: 'var(--radius-2xs)',
              borderLeft: '2px solid var(--color-accent-blue)',
              color: 'var(--color-text-primary)',
            }}
          >
            <strong>Investigation Context:</strong> {entry.practicalContext}
          </div>
        </div>
      )}
    </span>
  );
};
