import React, { useState } from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useInvestigationDossierQuery } from '../../api/casesApi';
import { useInvestigationStore } from '../../store/investigationStore';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import {
  FileText,
  ShieldCheck,
  Download,
  CheckCircle,
  Copy,
  Printer,
  X,
  FileSpreadsheet,
  AlertTriangle,
  Info,
  Compass,
  Radio,
  Wind,
  Ship,
  Layers,
  HelpCircle,
  Clock,
  MapPin,
  Check,
  ExternalLink,
} from 'lucide-react';

interface InvestigationReportViewProps {
  onClose?: () => void;
}

export const InvestigationReportView: React.FC<InvestigationReportViewProps> = ({ onClose }) => {
  const { activeCaseId } = useActiveCase();
  const setActiveStage = useInvestigationStore((s) => s.setActiveStage);

  const { data: dossier, isLoading, isError } = useInvestigationDossierQuery(activeCaseId);

  const [copied, setCopied] = useState(false);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  // Export JSON Report
  const handleExportJson = () => {
    if (!dossier) return;
    const blob = new Blob([JSON.stringify(dossier, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `marine_spill_investigation_dossier_${activeCaseId}_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExportNotice('Investigation Dossier JSON exported successfully.');
    setTimeout(() => setExportNotice(null), 4000);
  };

  // Export CSV Report
  const handleExportCsv = () => {
    if (!dossier?.evidence_ranking?.candidates || dossier.evidence_ranking.candidates.length === 0) {
      setExportNotice('No candidate vessel rankings available to export for this case.');
      setTimeout(() => setExportNotice(null), 4000);
      return;
    }

    const headers = [
      'Rank',
      'Vessel Name',
      'MMSI',
      'Vessel Type',
      'Best Evidence Score',
      'Evidence State',
      'Compatible Hypotheses Count',
      'Best Hypothesis ID',
    ];

    const rows = dossier.evidence_ranking.candidates.map((c: any) => [
      c.vessel_rank,
      `"${c.vessel_name || 'UNKNOWN'}"`,
      c.mmsi,
      `"${c.vessel_type || 'Cargo'}"`,
      c.best_evidence_score?.toFixed(4) || '0.0000',
      `"${c.vessel_evidence_state || 'UNKNOWN'}"`,
      c.compatible_hypotheses_count || 0,
      c.best_hypothesis_id || 'N/A',
    ]);

    const csvContent = [headers.join(','), ...rows.map((e: any) => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `marine_spill_candidate_evidence_${activeCaseId}_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExportNotice('Candidate Evidence CSV exported successfully.');
    setTimeout(() => setExportNotice(null), 4000);
  };

  const copyChecksum = (checksum: string) => {
    navigator.clipboard.writeText(checksum);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
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
          backgroundColor: 'rgba(10, 13, 19, 0.97)',
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
        <FileText size={32} color="var(--color-accent-blue)" />
        <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>Assembling 16-Section Investigation Dossier...</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)' }}>Synthesizing verified satellite, hydrodynamic, and AIS artifacts.</div>
      </div>
    );
  }

  if (isError || !dossier) {
    return (
      <div
        style={{
          position: 'absolute',
          top: '60px',
          left: '20px',
          right: '20px',
          backgroundColor: 'rgba(10, 13, 19, 0.97)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '30px',
          color: 'var(--color-accent-amber)',
          zIndex: 25,
        }}
      >
        <AlertTriangle size={24} />
        <div style={{ fontWeight: 700, marginTop: '8px' }}>Unable to Load Investigation Dossier</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
          Verification artifacts for case '{activeCaseId}' could not be assembled.
        </div>
      </div>
    );
  }

  const {
    case_identification: sec1,
    executive_summary: sec2,
    satellite_observation: sec3,
    detected_slick: sec4,
    environmental_conditions: sec5,
    source_reconstruction: sec6,
    ais_coverage: sec7,
    candidate_vessels: sec8,
    hypotheses_4d: sec9,
    counterfactual_simulation: sec10,
    evidence_ranking: sec11,
    causal_consistency: sec12,
    uncertainty: sec13,
    data_limitations: sec14,
    conclusion: sec15,
    provenance: sec16,
  } = dossier;

  return (
    <>
      {/* Print Stylesheet for High-Fidelity Printable Export */}
      <style>{`
        @media print {
          body {
            background-color: #ffffff !important;
            color: #111827 !important;
          }
          nav, header, footer, .no-print, button, .action-bar {
            display: none !important;
          }
          .investigation-dossier-container {
            position: static !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            max-height: none !important;
            overflow: visible !important;
            background: #ffffff !important;
            color: #111827 !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
          }
          .dossier-card {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #111827 !important;
            page-break-inside: avoid !important;
            margin-bottom: 16px !important;
          }
          .dossier-table th {
            background-color: #f3f4f6 !important;
            color: #374151 !important;
          }
          .dossier-table td {
            color: #111827 !important;
            border-bottom: 1px solid #e5e7eb !important;
          }
          .metric-cell {
            background-color: #f9fafb !important;
            border: 1px solid #e5e7eb !important;
            color: #111827 !important;
          }
        }
      `}</style>

      <div
        className="investigation-dossier-container"
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
          className="no-print"
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
                backgroundColor: 'rgba(56, 139, 253, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-accent-blue)',
              }}
            >
              <FileText size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    fontSize: 'var(--text-2xs)',
                    fontWeight: 800,
                    color: 'var(--color-accent-blue)',
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                  }}
                >
                  STAGE 04 · REPORT
                </span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>|</span>
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                  Marine Oil Spill Forensic Investigation Dossier
                </span>
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                Verified 16-Section Decision-Support Synthesis (Satellite · Metocean Drift · AIS Telemetry · Causal Physics)
              </div>
            </div>
          </div>

          <div className="action-bar" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => window.print()}
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
              title="Print clean report or save to PDF"
            >
              <Printer size={14} /> PRINT DOSSIER
            </button>

            <button
              onClick={handleExportJson}
              style={{
                padding: '6px 12px',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'var(--color-accent-blue)',
                color: '#0a0d13',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="Export complete 16-section JSON dossier"
            >
              <Download size={14} /> EXPORT JSON
            </button>

            <button
              onClick={handleExportCsv}
              disabled={sec11.ranking_count === 0}
              style={{
                padding: '6px 12px',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                borderRadius: 'var(--radius-xs)',
                backgroundColor: sec11.ranking_count === 0 ? 'var(--color-bg-base)' : 'rgba(16, 185, 129, 0.15)',
                color: sec11.ranking_count === 0 ? 'var(--color-text-tertiary)' : '#10b981',
                border: `1px solid ${sec11.ranking_count === 0 ? 'var(--color-border-subtle)' : '#10b981'}`,
                cursor: sec11.ranking_count === 0 ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="Export candidate ranking evidence table as CSV"
            >
              <FileSpreadsheet size={14} /> EXPORT CSV
            </button>

            {onClose && (
              <button
                onClick={onClose}
                style={{
                  width: '30px',
                  height: '30px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: 'transparent',
                  color: 'var(--color-text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  marginLeft: '4px',
                }}
                title="Close report and return to map overview"
              >
                <X size={18} />
              </button>
            )}
          </div>
        </div>

        {exportNotice && (
          <div
            style={{
              padding: '8px 20px',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              borderBottom: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#10b981',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <CheckCircle size={14} /> {exportNotice}
          </div>
        )}

        {/* Scrollable Report Body */}
        <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* SECTION 1: Case Identification */}
          <div
            className="dossier-card"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.06em' }}>
                  SECTION 01 · CASE IDENTIFICATION:
                </span>
                <MonospaceValue value={sec1.case_id.toUpperCase()} />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <StatusBadge label={sec1.validation_role} tone="blue" />
                <StatusBadge label={sec1.status_category} tone={sec1.status_category.includes('VALIDATED') ? 'emerald' : 'amber'} />
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '14px',
                paddingTop: '10px',
                borderTop: '1px solid var(--color-border-subtle)',
              }}
            >
              <div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>INCIDENT TITLE</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                  {sec1.name}
                </div>
              </div>

              <div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>INCIDENT TYPE</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                  {sec1.incident_type}
                </div>
              </div>

              <div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>ORIGIN COORDINATES (T₀)</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-primary)', marginTop: '2px' }}>
                  {sec1.origin_coordinates
                    ? `${sec1.origin_coordinates.latitude.toFixed(4)}°, ${sec1.origin_coordinates.longitude.toFixed(4)}°`
                    : 'N/A'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>ESTIMATED DISCHARGE TIME (T₀)</div>
                <div style={{ marginTop: '2px' }}>
                  <MonospaceValue value={sec1.incident_t0_utc} />
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 2: Executive Summary & The 7 Core Investigator Questions */}
          <div
            className="dossier-card"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '18px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <div>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.06em' }}>
                SECTION 02 · EXECUTIVE SUMMARY & THE 7 CORE INVESTIGATOR QUESTIONS
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '6px', lineHeight: 1.6 }}>
                {sec2.summary_narrative}
              </div>
            </div>

            {/* The 7 Core Questions Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '12px',
                marginTop: '6px',
              }}
            >
              {sec2.core_questions.map((q: any, idx: number) => (
                <div
                  key={idx}
                  className="metric-cell"
                  style={{
                    backgroundColor: 'var(--color-bg-base)',
                    border: '1px solid var(--color-border-subtle)',
                    borderRadius: 'var(--radius-xs)',
                    padding: '12px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-cyan)' }}>
                      Q{idx + 1}. {q.question}
                    </span>
                    <StatusBadge
                      label={q.status}
                      tone={
                        q.status === 'VERIFIED' || q.status === 'RESOLVED' || q.status === 'IDENTIFIED'
                          ? 'emerald'
                          : q.status.includes('HIGH')
                          ? 'blue'
                          : 'amber'
                      }
                    />
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                    {q.answer}
                  </div>
                  {q.key_metric && (
                    <div
                      style={{
                        marginTop: '4px',
                        fontSize: 'var(--text-2xs)',
                        fontWeight: 600,
                        color: 'var(--color-text-muted)',
                        borderTop: '1px dashed var(--color-border-subtle)',
                        paddingTop: '4px',
                      }}
                    >
                      Key Indicator: <span style={{ color: 'var(--color-text-primary)' }}>{q.key_metric}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* SECTION 3 & 4: Satellite Observation & Detected Slick */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '16px' }}>
            {/* Section 3 */}
            <div
              className="dossier-card"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Radio size={16} color="var(--color-accent-blue)" />
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)', textTransform: 'uppercase' }}>
                  SECTION 03 · SATELLITE OBSERVATION
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Acquisition by <strong style={{ color: 'var(--color-text-primary)' }}>{sec3.platform} {sec3.instrument}</strong> in {sec3.sensor_mode} mode at{' '}
                <MonospaceValue value={sec3.timestamp_utc} />. Orbit orientation: {sec3.orbit_direction}.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>SCENE IDENTIFIER</div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-primary)', wordBreak: 'break-all', marginTop: '2px' }}>
                    {sec3.scene_id || 'N/A'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>CALIBRATED LEVEL-1 GRD</div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', wordBreak: 'break-all', marginTop: '2px' }}>
                    {sec3.calibrated_file || 'Calibrated Sigma0 dB'}
                  </div>
                </div>
              </div>
            </div>

            {/* Section 4 */}
            <div
              className="dossier-card"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={16} color="var(--color-accent-cyan)" />
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-cyan)', textTransform: 'uppercase' }}>
                  SECTION 04 · DETECTED SLICK MORPHOLOGY
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Segmented <strong style={{ color: 'var(--color-text-primary)' }}>{sec4.slicks_count} candidate slicks</strong> via {sec4.segmentation_algorithm}.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>TOTAL SLICK AREA</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec4.total_area_hectares.toFixed(2)} ha
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>MEAN BACKSCATTER</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-accent-amber)', marginTop: '2px' }}>
                    {sec4.mean_backscatter_sigma0_db != null ? `${sec4.mean_backscatter_sigma0_db.toFixed(2)} dB` : 'N/A'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>CFAR DAMPING RATIO</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-accent-emerald)', marginTop: '2px' }}>
                    {sec4.damping_ratio_db != null ? `${sec4.damping_ratio_db.toFixed(1)} dB` : '-3.0 dB'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 5 & 6: Environmental Conditions & Source Reconstruction */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '16px' }}>
            {/* Section 5 */}
            <div
              className="dossier-card"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Wind size={16} color="var(--color-accent-blue)" />
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)', textTransform: 'uppercase' }}>
                  SECTION 05 · ENVIRONMENTAL FORCING (METOCEAN)
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Currents: <strong style={{ color: 'var(--color-text-primary)' }}>{sec5.ocean_currents_source}</strong>. Winds: <strong style={{ color: 'var(--color-text-primary)' }}>{sec5.wind_source}</strong>.
              </div>

              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div><strong>Spatial Domain:</strong> {sec5.spatial_coverage ? `West ${sec5.spatial_coverage.west}°, East ${sec5.spatial_coverage.east}°, South ${sec5.spatial_coverage.south}°, North ${sec5.spatial_coverage.north}°` : 'Regional AOI'}</div>
                <div><strong>Temporal Window:</strong> {sec5.temporal_coverage ? `${sec5.temporal_coverage.start_utc || ''} to ${sec5.temporal_coverage.end_utc || ''}` : 'Surveillance Window'}</div>
              </div>
            </div>

            {/* Section 6 */}
            <div
              className="dossier-card"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Compass size={16} color="var(--color-accent-purple)" />
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-purple)', textTransform: 'uppercase' }}>
                  SECTION 06 · SOURCE RECONSTRUCTION
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Evaluated <strong style={{ color: 'var(--color-text-primary)' }}>{sec6.total_source_hypotheses} backward source hypotheses</strong> across {sec6.release_horizons_hours?.length || 7} temporal release horizons ({sec6.release_horizons_hours?.join(', ')} hours).
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>LEEWAY COEFFICIENT</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>{sec6.leeway_factor}</div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>DIFFUSION COEFFICIENT</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>{sec6.turbulent_diffusion_dh}</div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>INTEGRATION SCHEME</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-accent-emerald)', marginTop: '2px' }}>dt &lt; 0 (Backward)</div>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 7, 8, 9, 10: AIS Coverage, Candidates, Hypotheses, Counterfactual */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {/* Section 7 */}
            <div className="dossier-card" style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)' }}>SECTION 07 · AIS COVERAGE</span>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                {sec7.archive_available ? (
                  <span>Verified regional AIS telemetry. <strong>{sec7.total_candidate_mmsis} candidate vessels</strong> evaluated.</span>
                ) : (
                  <span style={{ color: 'var(--color-accent-amber)' }}>Historical multi-vessel AIS archives unavailable for this incident segment.</span>
                )}
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', marginTop: 'auto' }}>{sec7.track_quality_notes}</div>
            </div>

            {/* Section 8 */}
            <div className="dossier-card" style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)' }}>SECTION 08 · CANDIDATE VESSELS</span>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                <strong>{sec8.candidate_vessels_count} candidate vessels</strong> passed spatiotemporal intersection criteria out of {sec8.total_vessels_in_corridor} corridor transits.
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', marginTop: 'auto' }}>{sec8.filtering_criteria}</div>
            </div>

            {/* Section 9 */}
            <div className="dossier-card" style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)' }}>SECTION 09 · 4D HYPOTHESES</span>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                Formulated <strong>{sec9.total_hypotheses_count} discrete 4D release hypotheses</strong> [x, y, z=0, t].
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', marginTop: 'auto' }}>{sec9.generation_method}</div>
            </div>

            {/* Section 10 */}
            <div className="dossier-card" style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)' }}>SECTION 10 · COUNTERFACTUAL DISPERSION</span>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                Simulated <strong>{sec10.total_simulations_run} forward plume trajectories</strong> ({sec10.particle_count_per_run} particles/run). Top IoU: <strong>{sec10.top_hypothesis_iou?.toFixed(3) || 'N/A'}</strong>.
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', marginTop: 'auto' }}>Evaluated via {sec10.evaluation_metric}.</div>
            </div>
          </div>

          {/* SECTION 11: Evidence Ranking */}
          <div
            className="dossier-card"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.06em' }}>
                SECTION 11 · INVESTIGATION EVIDENCE RANKING TABLE
              </span>
              <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>
                Sorted by Multi-Criteria Composite Evidence Score (0.0 to 1.0)
              </span>
            </div>

            {sec11.candidates && sec11.candidates.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table className="dossier-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', textAlign: 'left', color: 'var(--color-text-tertiary)' }}>
                      <th style={{ padding: '8px' }}>RANK</th>
                      <th style={{ padding: '8px' }}>VESSEL NAME</th>
                      <th style={{ padding: '8px' }}>MMSI</th>
                      <th style={{ padding: '8px' }}>VESSEL TYPE</th>
                      <th style={{ padding: '8px' }}>BEST EVIDENCE SCORE</th>
                      <th style={{ padding: '8px' }}>EVIDENCE STATE</th>
                      <th style={{ padding: '8px' }}>COMPATIBLE HYPOTHESES</th>
                      <th style={{ padding: '8px' }}>BEST HYPOTHESIS ID</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sec11.candidates.map((c: any, i: number) => (
                      <tr
                        key={c.mmsi}
                        style={{
                          borderBottom: '1px solid var(--color-border-subtle)',
                          backgroundColor: i === 0 ? 'rgba(46, 160, 67, 0.08)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '8px', fontWeight: 700, color: i === 0 ? '#10b981' : 'var(--color-text-primary)' }}>
                          #{c.vessel_rank || i + 1}
                        </td>
                        <td style={{ padding: '8px', fontWeight: i === 0 ? 700 : 500, color: i === 0 ? '#10b981' : 'var(--color-text-primary)' }}>
                          {c.vessel_name}
                        </td>
                        <td style={{ padding: '8px' }}><MonospaceValue value={c.mmsi} /></td>
                        <td style={{ padding: '8px' }}>{c.vessel_type || 'Cargo'}</td>
                        <td style={{ padding: '8px', fontWeight: 700, color: i === 0 ? '#10b981' : 'var(--color-text-primary)' }}>
                          {c.best_evidence_score?.toFixed(4) || '0.0000'}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <StatusBadge
                            label={c.vessel_evidence_state || 'EVALUATED'}
                            tone={c.vessel_evidence_state === 'HIGH_SUPPORT' ? 'emerald' : c.vessel_evidence_state === 'MODERATE_SUPPORT' ? 'blue' : 'neutral'}
                          />
                        </td>
                        <td style={{ padding: '8px' }}><MonospaceValue value={c.compatible_hypotheses_count} /></td>
                        <td style={{ padding: '8px', fontSize: 'var(--text-2xs)' }}><MonospaceValue value={c.best_hypothesis_id || 'N/A'} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '14px', backgroundColor: 'var(--color-bg-base)', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                No candidate vessel rankings generated for this case (negative control or missing historical archive). Forced vessel attribution is safely disabled.
              </div>
            )}
          </div>

          {/* SECTION 12 & 13: Causal Consistency & Uncertainty */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '16px' }}>
            {/* Section 12 */}
            <div
              className="dossier-card"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)', textTransform: 'uppercase' }}>
                  SECTION 12 · CAUSAL CONSISTENCY ENFORCEMENT
                </span>
                <StatusBadge label={sec12.enforced ? "CAUSAL PRECEDENCE ACTIVE" : "UNCONSTRAINED"} tone="blue" />
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                {sec12.notes}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>TOP CANDIDATE CAUSAL STATUS</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                    {sec12.causal_status_top_candidate}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>DISQUALIFIED POST-EVENT CRAFT</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-amber)', marginTop: '2px' }}>
                    {sec12.disqualified_post_release_count} Vessels Disqualified
                  </div>
                </div>
              </div>
            </div>

            {/* Section 13 */}
            <div
              className="dossier-card"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)', textTransform: 'uppercase' }}>
                  SECTION 13 · UNCERTAINTY & RANK STABILITY
                </span>
                <StatusBadge label={sec13.confidence_category} tone="emerald" />
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Monte Carlo bootstrap ensemble perturbation ({sec13.ensemble_size} iterations, seed {sec13.random_seed}) under metocean wind leeway and current vector perturbations.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', backgroundColor: 'var(--color-bg-base)', padding: '10px', borderRadius: 'var(--radius-xs)' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>RANK STABILITY SCORE</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                    {(sec13.rank_stability_score * 100).toFixed(0)}% Stable
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>MARGIN TO RANK #2</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec13.margin_to_rank_2 != null ? `+${sec13.margin_to_rank_2.toFixed(3)}` : 'N/A'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>ENSEMBLE SIZE</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec13.ensemble_size} Runs
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 14: Data Limitations */}
          <div
            className="dossier-card"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={16} color="var(--color-accent-amber)" />
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: 'var(--color-accent-amber)', letterSpacing: '0.06em' }}>
                SECTION 14 · DATA LIMITATIONS & SYSTEM BOUNDARIES
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {sec14.limitations.map((lim: string, idx: number) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                  <span style={{ color: 'var(--color-accent-amber)', fontWeight: 700 }}>•</span>
                  <span>{lim}</span>
                </div>
              ))}
            </div>
          </div>

          {/* SECTION 15: Conclusion */}
          <div
            className="dossier-card"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid rgba(56, 139, 253, 0.3)',
              borderRadius: 'var(--radius-sm)',
              padding: '18px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.06em' }}>
                SECTION 15 · INVESTIGATION CONCLUSION & SYNTHESIS
              </span>
              <StatusBadge label={sec15.decision_support_role} tone="blue" />
            </div>

            <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '12px 16px', borderRadius: 'var(--radius-xs)', borderLeft: '3px solid var(--color-accent-blue)' }}>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Best-Supported Hypothesis:
              </div>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                {sec15.best_supported_hypothesis}
              </div>
            </div>

            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              {sec15.synthesis_statement}
            </div>
          </div>

          {/* SECTION 16: Provenance & Cryptographic Audit */}
          <div
            className="dossier-card"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={16} color="#10b981" />
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: '#10b981', letterSpacing: '0.06em' }}>
                  SECTION 16 · PROVENANCE & CRYPTOGRAPHIC ARTIFACT AUDIT
                </span>
              </div>

              <button
                onClick={() => copyChecksum(sec16.sha256_checksum)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: 'var(--text-2xs)',
                }}
              >
                <Copy size={12} /> {copied ? 'COPIED CHECKSUM' : sec16.sha256_checksum}
              </button>
            </div>

            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', lineHeight: 1.5 }}>
              {sec16.non_deceptive_statement}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '8px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
              <span>Generated At: <MonospaceValue value={sec16.generated_at_utc} /></span>
              <span>System: {sec16.system_version}</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
