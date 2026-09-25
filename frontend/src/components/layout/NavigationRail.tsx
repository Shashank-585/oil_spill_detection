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
  // 1. OBSERVE
  { id: 'overview', label: 'Overview', category: 'OBSERVE', icon: Compass },
  { id: 'sar', label: 'SAR Imagery', category: 'OBSERVE', icon: Radio, domainTerm: 'SAR' },
  { id: 'ais', label: 'AIS Traffic', category: 'OBSERVE', icon: Ship, domainTerm: 'AIS' },

  // 2. INVESTIGATE
  { id: 'drift', label: 'Lagrangian Drift', category: 'INVESTIGATE', icon: Wind },

  // 3. ATTRIBUTE
  { id: 'candidates', label: 'Candidates', category: 'ATTRIBUTE', icon: Users },
  { id: 'evidence', label: 'Evidence Matrix', category: 'ATTRIBUTE', icon: BarChart3 },
  { id: 'uncertainty', label: 'Uncertainty', category: 'ATTRIBUTE', icon: HelpCircle, domainTerm: 'Uncertainty' },

  // 4. REPORT & NOTIFY
  { id: 'audit', label: 'Investigation Report & Audit', category: 'REPORT', icon: FileText },
  { id: 'alerts', label: 'Authority Notifications & Alerts', category: 'REPORT', icon: Bell },
];

export const NavigationRail: React.FC = () => {
  const activeWorkspace = useInvestigationStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useInvestigationStore((s) => s.setActiveWorkspace);

  return (
    <nav
      aria-label="Investigation Workspaces"
      style={{
        width: 'var(--nav-rail-width)',
        height: '100%',
        backgroundColor: 'var(--color-bg-surface)',
        borderRight: '1px solid var(--color-border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '12px 0',
        zIndex: 20,
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', width: '100%', alignItems: 'center' }}>
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
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: isActive ? 'var(--color-bg-surface-active)' : 'transparent',
                color: isActive ? 'var(--color-accent-blue)' : 'var(--color-text-secondary)',
                borderLeft: isActive ? '3px solid var(--color-accent-blue)' : '3px solid transparent',
                transition: 'all 0.15s ease',
                cursor: 'pointer',
              }}
            >
              <Icon size={20} />
            </button>
          );

          return (
            <React.Fragment key={item.id}>
              {showSeparator && (
                <div
                  role="separator"
                  style={{
                    width: '28px',
                    height: '1px',
                    backgroundColor: 'var(--color-border-subtle)',
                    margin: '4px 0',
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
