import React from 'react';
import { useInvestigationStore, type WorkspaceView } from '../../store/investigationStore';
import { DomainTooltip, type DomainTerm } from '../common/DomainTooltip';
import {
  Compass,
  Radio,
  Ship,
  Wind,
  Users,
  BarChart3,
  HelpCircle,
  FileText,
  Bell,
} from 'lucide-react';

interface NavItem {
  id: WorkspaceView;
  label: string;
  category: 'OBSERVE' | 'INVESTIGATE' | 'ATTRIBUTE' | 'REPORT';
  icon: React.ComponentType<{ size: number; color?: string }>;
  domainTerm?: DomainTerm;
}

const NAV_ITEMS: NavItem[] = [
  // 1. OBSERVATION TOOLS
  { id: 'overview', label: 'Overview & Basemap', category: 'OBSERVE', icon: Compass },
  { id: 'sar', label: 'SAR Radar Imagery', category: 'OBSERVE', icon: Radio, domainTerm: 'SAR' },
  { id: 'ais', label: 'AIS Traffic Corridors', category: 'OBSERVE', icon: Ship, domainTerm: 'AIS' },

  // 2. HYDRODYNAMIC DRIFT
  { id: 'drift', label: 'Lagrangian Drift Trajectories', category: 'INVESTIGATE', icon: Wind },

  // 3. FORENSIC ATTRIBUTION
  { id: 'candidates', label: 'Candidate Vessels', category: 'ATTRIBUTE', icon: Users },
  { id: 'evidence', label: 'Counterfactual & Evidence Matrix', category: 'ATTRIBUTE', icon: BarChart3 },
  { id: 'uncertainty', label: 'Uncertainty & Sensitivity', category: 'ATTRIBUTE', icon: HelpCircle, domainTerm: 'Uncertainty' },

  // 4. REPORTS & DISPATCH
  { id: 'audit', label: 'Investigation Dossier & Audit', category: 'REPORT', icon: FileText },
  { id: 'alerts', label: 'Authority Notifications & Alerts', category: 'REPORT', icon: Bell },
];

export const NavigationRail: React.FC = () => {
  const activeWorkspace = useInvestigationStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useInvestigationStore((s) => s.setActiveWorkspace);

  return (
    <nav
      aria-label="Investigation Tools"
      style={{
        width: 'var(--nav-rail-width)',
        height: '100%',
        backgroundColor: 'var(--color-bg-surface)',
        borderRight: '1px solid var(--color-border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '8px 0',
        zIndex: 20,
        flexShrink: 0,
        userSelect: 'none',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', width: '100%', alignItems: 'center' }}>
        {NAV_ITEMS.map((item, index) => {
          const isActive = activeWorkspace === item.id;
          const Icon = item.icon;
          // Separator after OBSERVE (index 2), after INVESTIGATE (index 3), and after ATTRIBUTE (index 6)
          const showSeparator = index === 3 || index === 4 || index === 7;

          const buttonElement = (
            <button
              onClick={() => setActiveWorkspace(item.id)}
              title={item.label}
              aria-label={item.label}
              aria-current={isActive ? 'page' : undefined}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-xs)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: isActive ? 'rgba(95, 145, 138, 0.16)' : 'transparent',
                color: isActive ? 'var(--color-accent-seafoam)' : 'var(--color-text-secondary)',
                border: isActive ? '1px solid rgba(95, 145, 138, 0.4)' : '1px solid transparent',
                transition: 'all 0.12s ease',
                cursor: 'pointer',
                position: 'relative',
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <Icon size={15} />
              {isActive && (
                <div
                  style={{
                    position: 'absolute',
                    left: '-8px',
                    top: '7px',
                    bottom: '7px',
                    width: '3px',
                    backgroundColor: 'var(--color-accent-seafoam)',
                    borderRadius: '0 2px 2px 0',
                  }}
                />
              )}
            </button>
          );

          return (
            <React.Fragment key={item.id}>
              {showSeparator && (
                <div
                  role="separator"
                  style={{
                    width: '20px',
                    height: '1px',
                    backgroundColor: 'var(--color-border-subtle)',
                    margin: '3px 0',
                  }}
                />
              )}
              {item.domainTerm ? (
                <DomainTooltip
                  term={item.domainTerm}
                  placement="right"
                  inline={false}
                  underline={false}
                >
                  {buttonElement}
                </DomainTooltip>
              ) : (
                buttonElement
              )}
            </React.Fragment>
          );
        })}
      </div>
    </nav>
  );
};
