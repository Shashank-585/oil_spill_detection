import React, { useState } from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useCaseNotificationsQuery, type AuthorityAlert } from '../../api/casesApi';
import { useInvestigationStore } from '../../store/investigationStore';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import {
  Bell,
  CheckCircle,
  Copy,
  Download,
  FileText,
  AlertTriangle,
  Info,
  Compass,
  X,
  ExternalLink,
} from 'lucide-react';

interface AuthorityNotificationViewProps {
  onClose?: () => void;
}

export const AuthorityNotificationView: React.FC<AuthorityNotificationViewProps> = ({ onClose }) => {
  const { activeCaseId, activeCase } = useActiveCase();
  const setActiveWorkspace = useInvestigationStore((s) => s.setActiveWorkspace);

  const { data: feed, isLoading, isError } = useCaseNotificationsQuery(activeCaseId);

  const alerts = feed?.alerts || [];
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  // Auto-select latest or first alert
  const activeAlert: AuthorityAlert | undefined =
    alerts.find((a) => a.alert_id === selectedAlertId) ||
    alerts.find((a) => a.alert_type === 'STRONGLY_SUPPORTED_HYPOTHESIS') ||
    alerts.find((a) => a.alert_type === 'INSUFFICIENT_EVIDENCE') ||
    alerts.find((a) => a.alert_type === 'AIS_DATA_UNAVAILABLE') ||
    alerts[alerts.length - 1];

  const handleCopyMemo = () => {
    if (!activeAlert) return;
    const memoText = [
      `======================================================================`,
      `MARITIME POLLUTION INVESTIGATION — AUTHORITY DISPATCH MEMO`,
      `======================================================================`,
      `SUBJECT: ${activeAlert.subject}`,
      `DATE (UTC): ${activeAlert.timestamp_utc}`,
      `CASE ID: ${activeAlert.case_id} (${activeAlert.case_name})`,
      `ALERT TYPE: ${activeAlert.alert_type}`,
      `SEVERITY: ${activeAlert.severity}`,
      `ATTRIBUTION STATUS: ${activeAlert.attribution_status}`,
      `----------------------------------------------------------------------`,
      `TOP FINDING:`,
      activeAlert.top_supported_hypothesis || 'Preliminary observation.',
      `----------------------------------------------------------------------`,
      `DETAILS:`,
      activeAlert.summary,
      `\nRECOMMENDED ACTIONS:`,
      ...activeAlert.recommended_authority_actions.map((act, i) => `${i + 1}. ${act}`),
      `\nLIMITATIONS:`,
      ...activeAlert.key_limitations.map((lim) => `- ${lim}`),
      `----------------------------------------------------------------------`,
      `FULL DOSSIER REFERENCE: ${activeAlert.dossier_link}`,
      `NOTICE: Prototype authority notification preview. Decision-support only.`,
      `======================================================================`,
    ].join('\n');

    navigator.clipboard.writeText(memoText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadTxt = () => {
    if (!activeAlert) return;
    const memoText = [
      `======================================================================`,
      `MARITIME POLLUTION INVESTIGATION — AUTHORITY DISPATCH MEMO`,
      `======================================================================`,
      `SUBJECT: ${activeAlert.subject}`,
      `DATE (UTC): ${activeAlert.timestamp_utc}`,
      `CASE: ${activeAlert.case_id} - ${activeAlert.case_name}`,
      `ALERT TYPE: ${activeAlert.alert_type}`,
      `SEVERITY: ${activeAlert.severity}`,
      `ATTRIBUTION STATUS: ${activeAlert.attribution_status}`,
      `----------------------------------------------------------------------`,
      activeAlert.body_markdown,
      `----------------------------------------------------------------------`,
      `NOTICE: Decision-support finding. No external transmission performed.`,
      `======================================================================`,
    ].join('\n');

    const blob = new Blob([memoText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `authority_dispatch_memo_${activeAlert.case_id}_${activeAlert.alert_id}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExportNotice('Authority Dispatch Memo downloaded (.TXT).');
    setTimeout(() => setExportNotice(null), 3500);
  };

  const handleDownloadJson = () => {
    if (!activeAlert) return;
    const blob = new Blob([JSON.stringify(activeAlert, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `authority_alert_${activeAlert.alert_id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExportNotice('Alert JSON artifact exported.');
    setTimeout(() => setExportNotice(null), 3500);
  };

  if (isLoading) {
    return (
      <div
        style={{
          position: 'absolute',
          top: '60px',
          left: '20px',
          right: '20px',
          maxHeight: 'calc(100% - 120px)',
          backgroundColor: 'rgba(10, 13, 19, 0.98)',
          backdropFilter: 'blur(10px)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-xl)',
          zIndex: 25,
          padding: '40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: '12px',
          color: 'var(--color-text-secondary)',
        }}
      >
        <Bell size={32} color="var(--color-accent-amber)" />
        <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>Loading Authority Alerts...</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)' }}>
          Retrieving decision-support notifications for {activeCase?.name || activeCaseId}.
        </div>
      </div>
    );
  }

  if (isError || !feed) {
    return (
      <div
        style={{
          position: 'absolute',
          top: '60px',
          left: '20px',
          right: '20px',
          maxHeight: 'calc(100% - 120px)',
          backgroundColor: 'rgba(10, 13, 19, 0.98)',
          border: '1px solid var(--color-accent-crimson)',
          borderRadius: 'var(--radius-md)',
          zIndex: 25,
          padding: '40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <AlertTriangle size={32} color="var(--color-accent-crimson)" />
        <div style={{ color: 'var(--color-text-primary)', fontWeight: 600 }}>Failed to Load Authority Alerts</div>
        <button
          onClick={onClose}
          style={{
            padding: '6px 14px',
            backgroundColor: 'var(--color-bg-surface-raised)',
            border: '1px solid var(--color-border-subtle)',
            color: 'var(--color-text-secondary)',
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer',
          }}
        >
          Return to Workspace
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: '60px',
        left: '20px',
        right: '20px',
        maxHeight: 'calc(100% - 120px)',
        backgroundColor: 'rgba(10, 13, 19, 0.98)',
        backdropFilter: 'blur(12px)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-xl)',
        zIndex: 25,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Top Header Bar */}
      <div
        style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--color-border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--color-bg-surface)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(217, 119, 6, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-accent-amber)',
            }}
          >
            <Bell size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                Authority Notification & Alert Dispatch
              </span>
              <StatusBadge label="PHASE 24" tone="amber" size="sm" />
              <StatusBadge label={`${alerts.length} ALERTS`} tone="neutral" size="sm" />
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
              Case: <MonospaceValue value={activeCaseId} /> · {feed.case_id}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {exportNotice && (
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-accent-emerald)', fontWeight: 500 }}>
              {exportNotice}
            </span>
          )}

          <button
            onClick={() => setActiveWorkspace('audit')}
            style={{
              padding: '6px 12px',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              borderRadius: 'var(--radius-xs)',
              backgroundColor: 'var(--color-bg-surface-raised)',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border-subtle)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            title="Open complete 16-section investigation dossier"
          >
            <FileText size={14} /> OPEN DOSSIER
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--color-text-tertiary)',
                cursor: 'pointer',
              }}
              title="Close Notification Preview"
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Prototype Authority Notification System Disclaiming Banner */}
      <div
        style={{
          padding: '8px 20px',
          backgroundColor: 'rgba(217, 119, 6, 0.08)',
          borderBottom: '1px solid rgba(217, 119, 6, 0.2)',
          fontSize: 'var(--text-xs)',
          color: 'var(--color-accent-amber)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <Info size={14} style={{ flexShrink: 0 }} />
        <span>
          <strong>PROTOTYPE AUTHORITY NOTIFICATION SYSTEM:</strong> Formats and previews official dispatch memos
          generated from verified investigation findings. Zero external email transmission or simulated external
          delivery claims are performed.
        </span>
      </div>

      {/* Main Split Layout: Inbox Feed List (Left) + Dispatch Memo Detail (Right) */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Left: Alert List */}
        <div
          style={{
            width: '360px',
            borderRight: '1px solid var(--color-border-subtle)',
            backgroundColor: 'var(--color-bg-surface)',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
          }}
        >
          <div
            style={{
              padding: '10px 16px',
              borderBottom: '1px solid var(--color-border-subtle)',
              fontSize: 'var(--text-2xs)',
              fontWeight: 700,
              color: 'var(--color-text-tertiary)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}
          >
            INVESTIGATION DISPATCH FEED ({alerts.length})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {alerts.map((alert) => {
              const isSelected = activeAlert?.alert_id === alert.alert_id;
              const isStrong = alert.alert_type === 'STRONGLY_SUPPORTED_HYPOTHESIS';
              const isInsufficient = alert.alert_type === 'INSUFFICIENT_EVIDENCE';
              const isAisUnavail = alert.alert_type === 'AIS_DATA_UNAVAILABLE';

              let badgeColor = 'var(--color-text-secondary)';
              let badgeBg = 'rgba(255, 255, 255, 0.05)';
              let badgeText = alert.alert_type.replace(/_/g, ' ');

              if (isStrong) {
                badgeColor = '#10b981';
                badgeBg = 'rgba(16, 185, 129, 0.15)';
              } else if (isInsufficient) {
                badgeColor = '#f59e0b';
                badgeBg = 'rgba(245, 158, 11, 0.15)';
              } else if (isAisUnavail) {
                badgeColor = '#64748b';
                badgeBg = 'rgba(100, 116, 139, 0.15)';
              }

              return (
                <div
                  key={alert.alert_id}
                  onClick={() => setSelectedAlertId(alert.alert_id)}
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid var(--color-border-subtle)',
                    backgroundColor: isSelected ? 'var(--color-bg-surface-active)' : 'transparent',
                    borderLeft: isSelected ? '3px solid var(--color-accent-amber)' : '3px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                    <span
                      style={{
                        fontSize: 'var(--text-2xs)',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: 'var(--radius-2xs)',
                        backgroundColor: badgeBg,
                        color: badgeColor,
                      }}
                    >
                      {badgeText}
                    </span>
                    <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
                      <MonospaceValue value={alert.timestamp_utc?.slice(11, 19) || ''} />
                    </span>
                  </div>

                  <div
                    style={{
                      fontSize: 'var(--text-xs)',
                      fontWeight: 600,
                      color: isSelected ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                      marginTop: '6px',
                      lineHeight: 1.3,
                    }}
                  >
                    {alert.subject}
                  </div>

                  <div
                    style={{
                      fontSize: 'var(--text-2xs)',
                      color: 'var(--color-text-tertiary)',
                      marginTop: '4px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {alert.summary}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Selected Dispatch Memo Preview */}
        {activeAlert ? (
          <div
            style={{
              flex: 1,
              backgroundColor: 'var(--color-bg-base)',
              overflowY: 'auto',
              padding: '24px 32px',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
            }}
          >
            {/* Memo Action Bar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '16px',
                borderBottom: '1px solid var(--color-border-subtle)',
              }}
            >
              <div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  DISPATCH MEMORANDUM · ID: <MonospaceValue value={activeAlert.alert_id} />
                </div>
                <div style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                  {activeAlert.subject}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={handleCopyMemo}
                  style={{
                    padding: '6px 12px',
                    fontSize: 'var(--text-xs)',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'var(--color-bg-surface-raised)',
                    border: '1px solid var(--color-border-subtle)',
                    color: 'var(--color-text-secondary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  title="Copy formatted memorandum text to clipboard"
                >
                  {copied ? <CheckCircle size={14} color="#10b981" /> : <Copy size={14} />}
                  {copied ? 'COPIED' : 'COPY MEMO'}
                </button>

                <button
                  onClick={handleDownloadTxt}
                  style={{
                    padding: '6px 12px',
                    fontSize: 'var(--text-xs)',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'var(--color-bg-surface-raised)',
                    border: '1px solid var(--color-border-subtle)',
                    color: 'var(--color-text-secondary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  title="Download memo as plaintext file"
                >
                  <Download size={14} /> EXPORT TXT
                </button>

                <button
                  onClick={handleDownloadJson}
                  style={{
                    padding: '6px 12px',
                    fontSize: 'var(--text-xs)',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'var(--color-accent-amber)',
                    border: 'none',
                    color: '#0a0d13',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  title="Export alert artifact as JSON"
                >
                  <Download size={14} /> EXPORT JSON
                </button>
              </div>
            </div>

            {/* Structured Top Finding Callout Box */}
            <div
              style={{
                backgroundColor:
                  activeAlert.alert_type === 'STRONGLY_SUPPORTED_HYPOTHESIS'
                    ? 'rgba(16, 185, 129, 0.08)'
                    : activeAlert.alert_type === 'INSUFFICIENT_EVIDENCE'
                    ? 'rgba(245, 158, 11, 0.08)'
                    : 'rgba(100, 116, 139, 0.08)',
                border: `1px solid ${
                  activeAlert.alert_type === 'STRONGLY_SUPPORTED_HYPOTHESIS'
                    ? '#10b981'
                    : activeAlert.alert_type === 'INSUFFICIENT_EVIDENCE'
                    ? '#f59e0b'
                    : '#64748b'
                }`,
                borderRadius: 'var(--radius-sm)',
                padding: '16px 20px',
              }}
            >
              <div
                style={{
                  fontSize: 'var(--text-2xs)',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color:
                    activeAlert.alert_type === 'STRONGLY_SUPPORTED_HYPOTHESIS'
                      ? '#10b981'
                      : activeAlert.alert_type === 'INSUFFICIENT_EVIDENCE'
                      ? '#f59e0b'
                      : '#94a3b8',
                }}
              >
                ATTRIBUTION STATUS: {activeAlert.attribution_status.replace(/_/g, ' ')}
              </div>

              <div
                style={{
                  fontSize: 'var(--text-sm)',
                  fontWeight: 600,
                  color: 'var(--color-text-primary)',
                  marginTop: '8px',
                  lineHeight: 1.5,
                }}
              >
                {activeAlert.top_supported_hypothesis || activeAlert.summary}
              </div>

              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--color-text-secondary)',
                  marginTop: '6px',
                  lineHeight: 1.4,
                }}
              >
                {activeAlert.summary}
              </div>
            </div>

            {/* Quick Metrics Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '12px',
              }}
            >
              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>OBSERVATION TIME</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                  <MonospaceValue value={activeAlert.observation_time_utc || 'N/A'} />
                </div>
              </div>

              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>SLICK COVERAGE</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                  {activeAlert.slick_count} Slicks · {activeAlert.slick_total_area_ha.toFixed(2)} ha
                </div>
              </div>

              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>CANDIDATE VESSELS</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                  {activeAlert.candidate_vessel_count} Evaluated
                </div>
              </div>

              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>RADAR SENSOR</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                  {activeAlert.satellite_platform || 'Sentinel-1 C-SAR'}
                </div>
              </div>
            </div>

            {/* Recommended Authority Actions */}
            {activeAlert.recommended_authority_actions && activeAlert.recommended_authority_actions.length > 0 && (
              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                <div
                  style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginBottom: '10px',
                  }}
                >
                  <Compass size={14} color="var(--color-accent-blue)" /> Recommended Investigative Actions
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {activeAlert.recommended_authority_actions.map((act, idx) => (
                    <div
                      key={idx}
                      style={{
                        fontSize: 'var(--text-xs)',
                        color: 'var(--color-text-secondary)',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                      }}
                    >
                      <span
                        style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          backgroundColor: 'rgba(56, 139, 253, 0.15)',
                          color: 'var(--color-accent-blue)',
                          fontSize: 'var(--text-2xs)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          fontWeight: 700,
                        }}
                      >
                        {idx + 1}
                      </span>
                      <span>{act}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Key Data Limitations Section */}
            {activeAlert.key_limitations && activeAlert.key_limitations.length > 0 && (
              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                <div
                  style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginBottom: '10px',
                  }}
                >
                  <AlertTriangle size={14} color="var(--color-accent-amber)" /> Crucial Data Limitations
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {activeAlert.key_limitations.map((lim, idx) => (
                    <div
                      key={idx}
                      style={{
                        fontSize: 'var(--text-xs)',
                        color: 'var(--color-text-secondary)',
                        lineHeight: 1.4,
                      }}
                    >
                      • {lim}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Navigation to Full Dossier */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 20px',
                backgroundColor: 'rgba(56, 139, 253, 0.08)',
                border: '1px solid rgba(56, 139, 253, 0.25)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              <div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  Complete 16-Section Investigation Dossier Available
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                  Detailed radar calibration, backward Lagrangian source plumes, counterfactual forward runs, and
                  provenance checksums.
                </div>
              </div>
              <button
                onClick={() => setActiveWorkspace('audit')}
                style={{
                  padding: '8px 16px',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  backgroundColor: 'var(--color-accent-blue)',
                  color: '#0a0d13',
                  border: 'none',
                  borderRadius: 'var(--radius-xs)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                VIEW FULL DOSSIER <ExternalLink size={14} />
              </button>
            </div>
          </div>
        ) : (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-text-muted)',
              fontSize: 'var(--text-sm)',
            }}
          >
            Select a notification from the dispatch feed on the left.
          </div>
        )}
      </div>
    </div>
  );
};
