import React from 'react';
import { useInvestigationStore, type WorkspaceView } from '../../store/investigationStore';
import {
  Compass,
  Radio,
  Ship,
  Wind,
  Users,
  BarChart3,
  HelpCircle,
  FileText,
} from 'lucide-react';

interface NavItem {
  id: WorkspaceView;
  label: string;
  category: 'OBSERVE' | 'ATTRIBUTE' | 'DOCUMENT';
  icon: React.ComponentType<{ size: number; color?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  // OBSERVE
  { id: 'overview', label: 'Overview', category: 'OBSERVE', icon: Compass },
  { id: 'sar', label: 'SAR Imagery', category: 'OBSERVE', icon: Radio },
  { id: 'ais', label: 'AIS Traffic', category: 'OBSERVE', icon: Ship },
  { id: 'drift', label: 'Lagrangian Drift', category: 'OBSERVE', icon: Wind },

  // ATTRIBUTE
  { id: 'candidates', label: 'Candidates', category: 'ATTRIBUTE', icon: Users },
  { id: 'evidence', label: 'Evidence Matrix', category: 'ATTRIBUTE', icon: BarChart3 },
  { id: 'uncertainty', label: 'Uncertainty', category: 'ATTRIBUTE', icon: HelpCircle },

  // DOCUMENT
  { id: 'audit', label: 'Audit & Export', category: 'DOCUMENT', icon: FileText },
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
          const showSeparator = index === 4 || index === 7;

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
            </React.Fragment>
          );
        })}
      </div>
    </nav>
  );
};
