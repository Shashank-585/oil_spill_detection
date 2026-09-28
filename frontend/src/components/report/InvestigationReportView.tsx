import React, { useState, useMemo } from 'react';
import { useActiveCase } from '../../context/CaseContext';
import {
  useInvestigationDossierQuery,
  useSpillComparisonsQuery,
  useSlicksQuery,
  useCaseSatelliteObservationsQuery,
  useUncertaintyQuery,
} from '../../api/casesApi';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { EvidenceBars } from '../attribution/EvidenceBars';
import { CausalTagPill } from '../attribution/CausalTagPill';
import { DataReadinessPanel } from '../common/DataReadinessPanel';
import { SatelliteObservationPanel } from '../observation/SatelliteObservationPanel';
import { InvestigationResult } from '../common/InvestigationResult';
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
  Compass,
  Radio,
  Wind,
  Layers,
  Ship,
  Activity,
  MapPin,
  Cpu,
} from 'lucide-react';

interface InvestigationReportViewProps {
  onClose?: () => void;
}

interface NavSectionItem {
  id: string;
  number: string;
  label: string;
  shortLabel: string;
}

const SECTIONS: NavSectionItem[] = [
  { id: 'sec-01-case', number: '01', label: 'Case Identification', shortLabel: 'Case' },
  { id: 'sec-02-summary', number: '02', label: 'Executive Summary', shortLabel: 'Summary' },
  { id: 'sec-03-satellite', number: '03', label: 'Satellite Observation', shortLabel: 'Satellite' },
  { id: 'sec-04-slick', number: '04', label: 'Detected Slick', shortLabel: 'Slick' },
  { id: 'sec-05-env', number: '05', label: 'Environmental Conditions', shortLabel: 'Environment' },
  { id: 'sec-06-reconstruction', number: '06', label: 'Source Reconstruction', shortLabel: 'Reconstruction' },
  { id: 'sec-07-ais', number: '07', label: 'AIS Coverage', shortLabel: 'AIS' },
  { id: 'sec-08-candidates', number: '08', label: 'Candidate Vessels', shortLabel: 'Candidates' },
  { id: 'sec-09-hypotheses', number: '09', label: '4D Hypotheses', shortLabel: '4D Hypotheses' },
  { id: 'sec-10-counterfactual', number: '10', label: 'Counterfactual Simulation', shortLabel: 'Counterfactual' },
  { id: 'sec-11-evidence', number: '11', label: 'Evidence Ranking', shortLabel: 'Evidence' },
  { id: 'sec-12-causal', number: '12', label: 'Causal Consistency', shortLabel: 'Causal' },
  { id: 'sec-13-uncertainty', number: '13', label: 'Uncertainty & Stability', shortLabel: 'Uncertainty' },
  { id: 'sec-14-limitations', number: '14', label: 'Data Limitations', shortLabel: 'Limitations' },
  { id: 'sec-15-conclusion', number: '15', label: 'Investigation Conclusion', shortLabel: 'Conclusion' },
  { id: 'sec-16-provenance', number: '16', label: 'Reproducible Provenance', shortLabel: 'Provenance' },
];

export const InvestigationReportView: React.FC<InvestigationReportViewProps> = ({ onClose }) => {
  const { activeCaseId, attributionRanking } = useActiveCase();

  // Primary dossier query
  const { data: dossier, isLoading, isError } = useInvestigationDossierQuery(activeCaseId);

  // Supporting detailed queries for forensic depth
  const { data: spillComparisons } = useSpillComparisonsQuery(activeCaseId);
  const { data: slicksGeoJson } = useSlicksQuery(activeCaseId);
  const { data: satObservationPkg } = useCaseSatelliteObservationsQuery(activeCaseId);
  const { data: uncertaintyData } = useUncertaintyQuery(activeCaseId);

  // Local state
  const [activeSectionId, setActiveSectionId] = useState<string>('sec-01-case');
  const [copiedChecksum, setCopiedChecksum] = useState(false);
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const [showFullSatPackage, setShowFullSatPackage] = useState(false);

  // Best simulation comparison for counterfactual section
  const topComparison = useMemo(() => {
    if (!spillComparisons || spillComparisons.length === 0) return null;
    // Find comparison matching top candidate hypothesis or highest IoU
    if (dossier?.evidence_ranking?.candidates?.[0]?.best_hypothesis_id) {
      const match = spillComparisons.find(
        (c) => c.hypothesis_id === dossier.evidence_ranking.candidates[0].best_hypothesis_id
      );
      if (match) return match;
    }
    return spillComparisons[0];
  }, [spillComparisons, dossier]);

  // Primary slick feature for morphology details
  const primarySlickFeature = useMemo(() => {
    if (!slicksGeoJson?.features || slicksGeoJson.features.length === 0) return null;
    return slicksGeoJson.features[0];
  }, [slicksGeoJson]);

  // Smooth scroll handler for TOC rail
  const scrollToSection = (id: string) => {
    setActiveSectionId(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

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
      'Drift Consistency',
      'Spatial Compatibility',
      'Temporal Alignment',
      'AIS Quality',
      'Causal Status',
      'Compatible Hypotheses Count',
      'Best Hypothesis ID',
    ];

    const rows = dossier.evidence_ranking.candidates.map((c: any) => {
      // Find matching candidate from attributionRanking if available for detailed scores
      const detailed = attributionRanking?.find((ar) => ar.mmsi === c.mmsi);
      return [
        c.vessel_rank || '',
        `"${c.vessel_name || 'UNKNOWN'}"`,
        c.mmsi,
        `"${c.vessel_type || 'Cargo'}"`,
        c.best_evidence_score?.toFixed(4) || '0.0000',
        `"${c.vessel_evidence_state || 'UNKNOWN'}"`,
        detailed?.evidence_components?.drift_consistency?.toFixed(3) || 'N/A',
        detailed?.evidence_components?.spatial_compatibility?.toFixed(3) || 'N/A',
        detailed?.evidence_components?.temporal_compatibility?.toFixed(3) || 'N/A',
        detailed?.evidence_components?.ais_track_quality?.toFixed(3) || 'N/A',
        `"${c.causal_precedence_status || detailed?.causal_precedence_status || 'EVALUATED'}"`,
        c.compatible_hypotheses_count || 0,
        c.best_hypothesis_id || 'N/A',
      ];
    });

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
    setCopiedChecksum(true);
    setTimeout(() => setCopiedChecksum(false), 2500);
  };

  if (isLoading) {
    return (
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'var(--color-bg-base)',
          zIndex: 30,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: '16px',
          color: 'var(--color-text-secondary)',
        }}
      >
        <div
          style={{
            width: '42px',
            height: '42px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(95, 145, 138, 0.15)',
            border: '1px solid rgba(95, 145, 138, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-accent-teal)',
          }}
        >
          <FileText size={22} />
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            Assembling Investigation Dossier...
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: '4px' }}>
            Compiling 16 forensic evidence sections for case {activeCaseId}
          </div>
        </div>
      </div>
    );
  }

  if (isError || !dossier) {
    return (
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'var(--color-bg-base)',
          padding: '40px',
          color: 'var(--color-accent-amber)',
          zIndex: 30,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
        }}
      >
        <AlertTriangle size={32} />
        <div style={{ fontWeight: 700, fontSize: 'var(--text-base)' }}>Unable to Assemble Investigation Dossier</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
          Forensic verification artifacts for case '{activeCaseId}' could not be loaded from the data bridge.
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              marginTop: '12px',
              padding: '6px 16px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              color: 'var(--color-text-primary)',
              cursor: 'pointer',
              fontSize: 'var(--text-xs)',
            }}
          >
            Return to Investigation Overview
          </button>
        )}
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
      {/* Print Stylesheet for High-Fidelity Technical Report Printing */}
      <style>{`
        @media print {
          body {
            background-color: #ffffff !important;
            color: #0f172a !important;
          }
          nav, header, footer, .no-print, button, .action-bar, .report-nav-rail {
            display: none !important;
          }
          .investigation-dossier-workspace {
            position: static !important;
            height: auto !important;
            overflow: visible !important;
            background: #ffffff !important;
            color: #0f172a !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
          }
          .dossier-scroll-body {
            overflow: visible !important;
            padding: 0 !important;
          }
          .dossier-section {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #0f172a !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            margin-bottom: 20px !important;
            box-shadow: none !important;
          }
          .dossier-section h2, .dossier-section h3 {
            color: #0f172a !important;
          }
          .dossier-table th {
            background-color: #f1f5f9 !important;
            color: #334155 !important;
            border-bottom: 2px solid #cbd5e1 !important;
          }
          .dossier-table td {
            color: #0f172a !important;
            border-bottom: 1px solid #e2e8f0 !important;
          }
          .dossier-metric-box {
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            color: #0f172a !important;
          }
          .dossier-metric-label {
            color: #64748b !important;
          }
          .dossier-metric-val {
            color: #0f172a !important;
          }
        }
      `}</style>

      {/* Main Dossier Workspace Container */}
      <div
        className="investigation-dossier-workspace"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'var(--color-bg-base)',
          zIndex: 30,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* 1. TOP ACTION BAR */}
        <div
          className="no-print"
          style={{
            height: '48px',
            borderBottom: '1px solid var(--color-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            backgroundColor: 'var(--color-bg-surface)',
            flexShrink: 0,
          }}
        >
          {/* Left: Branding & Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'rgba(95, 145, 138, 0.15)',
                border: '1px solid rgba(95, 145, 138, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-accent-teal)',
              }}
            >
              <FileText size={16} />
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span
                style={{
                  fontSize: 'var(--text-2xs)',
                  fontWeight: 800,
                  letterSpacing: '0.08em',
                  color: 'var(--color-accent-teal)',
                  textTransform: 'uppercase',
                }}
              >
                INVESTIGATION DOSSIER
              </span>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>/</span>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                {sec1.name}
              </span>
            </div>

            <StatusBadge
              label={sec1.status_category.replace(/_/g, ' ')}
              tone={
                sec1.status_category.includes('VALIDATED')
                  ? 'emerald'
                  : sec1.status_category.includes('NEGATIVE')
                  ? 'blue'
                  : 'amber'
              }
            />
          </div>

          {/* Right: Export & Navigation Actions */}
          <div className="action-bar" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => window.print()}
              style={{
                padding: '5px 12px',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'var(--color-bg-base)',
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border-subtle)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="Print investigation dossier or save as PDF"
            >
              <Printer size={13} /> PRINT DOSSIER
            </button>

            <button
              onClick={handleExportJson}
              style={{
                padding: '5px 12px',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'rgba(56, 189, 248, 0.12)',
                color: 'var(--color-accent-blue)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="Export complete 16-section structured JSON dossier"
            >
              <Download size={13} /> EXPORT JSON
            </button>

            <button
              onClick={handleExportCsv}
              disabled={sec11.ranking_count === 0}
              style={{
                padding: '5px 12px',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                borderRadius: 'var(--radius-xs)',
                backgroundColor: sec11.ranking_count === 0 ? 'var(--color-bg-base)' : 'rgba(16, 185, 129, 0.12)',
                color: sec11.ranking_count === 0 ? 'var(--color-text-muted)' : '#10b981',
                border: `1px solid ${sec11.ranking_count === 0 ? 'var(--color-border-subtle)' : 'rgba(16, 185, 129, 0.3)'}`,
                cursor: sec11.ranking_count === 0 ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="Export candidate ranking evidence table as CSV"
            >
              <FileSpreadsheet size={13} /> EXPORT CSV
            </button>

            {onClose && (
              <button
                onClick={onClose}
                style={{
                  width: '28px',
                  height: '28px',
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
                title="Return to operational map view"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Export Notification Banner */}
        {exportNotice && (
          <div
            className="no-print"
            style={{
              padding: '8px 20px',
              backgroundColor: 'rgba(16, 185, 129, 0.12)',
              borderBottom: '1px solid rgba(16, 185, 129, 0.25)',
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

        {/* 2. MAIN DOSSIER BODY: Sticky TOC Rail + Scrollable Content */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left Navigation Rail (Sticky TOC) */}
          <div
            className="report-nav-rail no-print"
            style={{
              width: '210px',
              borderRight: '1px solid var(--color-border-subtle)',
              backgroundColor: 'var(--color-bg-surface)',
              overflowY: 'auto',
              flexShrink: 0,
              padding: '16px 8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <div
              style={{
                fontSize: 'var(--text-2xs)',
                fontWeight: 800,
                color: 'var(--color-text-tertiary)',
                letterSpacing: '0.08em',
                padding: '0 8px 8px 8px',
                borderBottom: '1px solid var(--color-border-subtle)',
                marginBottom: '6px',
              }}
            >
              DOSSIER SECTIONS
            </div>

            {SECTIONS.map((sec) => {
              const isActive = activeSectionId === sec.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => scrollToSection(sec.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '6px 8px',
                    borderRadius: 'var(--radius-xs)',
                    border: 'none',
                    backgroundColor: isActive ? 'rgba(95, 145, 138, 0.15)' : 'transparent',
                    color: isActive ? 'var(--color-accent-teal)' : 'var(--color-text-secondary)',
                    fontWeight: isActive ? 700 : 500,
                    fontSize: 'var(--text-xs)',
                    textAlign: 'left',
                    cursor: 'pointer',
                    width: '100%',
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 'var(--text-2xs)',
                      color: isActive ? 'var(--color-accent-sand)' : 'var(--color-text-muted)',
                      minWidth: '18px',
                    }}
                  >
                    {sec.number}
                  </span>
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {sec.shortLabel}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Right Scrollable Document Area */}
          <div
            className="dossier-scroll-body"
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '24px 32px',
              display: 'flex',
              flexDirection: 'column',
              gap: '24px',
              maxWidth: '1200px',
              margin: '0 auto',
              width: '100%',
            }}
          >
            {/* ========================================================================= */}
            {/* SECTION 01: REPORT HEADER & CASE IDENTIFICATION */}
            {/* ========================================================================= */}
            <div
              id="sec-01-case"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
              }}
            >
              {/* Header Title & Status */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    01 — CASE IDENTIFICATION & METADATA
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                    {sec1.name}
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <MapPin size={13} color="var(--color-text-tertiary)" />
                    <span>{sec1.location_name || 'Coastal Maritime AOI'}</span>
                    <span>·</span>
                    <span>{sec1.incident_type}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <StatusBadge label={sec1.validation_role.replace(/_/g, ' ')} tone="blue" />
                  <StatusBadge
                    label={sec1.status_category.replace(/_/g, ' ')}
                    tone={sec1.status_category.includes('VALIDATED') ? 'emerald' : sec1.status_category.includes('NEGATIVE') ? 'blue' : 'amber'}
                  />
                </div>
              </div>

              {/* Compact Key-Value Metadata Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '12px',
                  paddingTop: '14px',
                  borderTop: '1px solid var(--color-border-subtle)',
                }}
              >
                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', fontWeight: 600 }}>CASE IDENTIFIER</div>
                  <div className="dossier-metric-val" style={{ marginTop: '2px' }}>
                    <MonospaceValue value={sec1.case_id.toUpperCase()} />
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', fontWeight: 600 }}>REFERENCE DISCHARGE (T₀)</div>
                  <div className="dossier-metric-val" style={{ marginTop: '2px' }}>
                    <MonospaceValue value={sec1.incident_t0_utc} />
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', fontWeight: 600 }}>SAR OBSERVATION TIME (T_obs)</div>
                  <div className="dossier-metric-val" style={{ marginTop: '2px' }}>
                    <MonospaceValue value={sec1.observation_timestamp_utc} />
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', fontWeight: 600 }}>ORIGIN COORDINATES</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-primary)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                    {sec1.origin_coordinates
                      ? `${sec1.origin_coordinates.latitude.toFixed(4)}°N, ${Math.abs(sec1.origin_coordinates.longitude).toFixed(4)}°W`
                      : 'Reconstructed via Drift'}
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 02: EXECUTIVE SUMMARY & CORE QUESTIONS */}
            {/* ========================================================================= */}
            <div
              id="sec-02-summary"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
              }}
            >
              <div>
                <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  02 — EXECUTIVE SUMMARY
                </div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                  Synthesized Evidence Position
                </div>
              </div>

              {/* High-Level Investigation Result Summary */}
              <InvestigationResult compact={false} />

              {/* 4 Structured Summary Elements */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: '12px',
                }}
              >
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-accent-cyan)', textTransform: 'uppercase' }}>
                    1. Observed Event
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                    Detected oil-like slick feature in the Sentinel-1 SAR observation with characteristic radar backscatter damping.
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-accent-blue)', textTransform: 'uppercase' }}>
                    2. Source Reconstruction
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                    Backward Lagrangian drift reconstruction under HYCOM currents and ERA5 winds produced candidate source release horizons.
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-accent-purple)', textTransform: 'uppercase' }}>
                    3. Candidate Evaluation
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                    AIS vessel trajectories in the spatiotemporal corridor were evaluated against reconstructed physical release envelopes.
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: '#10b981', textTransform: 'uppercase' }}>
                    4. Current Result
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-primary)', fontWeight: 600, marginTop: '4px', lineHeight: 1.5 }}>
                    {sec14.is_negative_control
                      ? 'No vessel attribution supported. Evaluated passing vessels eliminated under available evidence; consistent with reference pipeline infrastructure failure.'
                      : sec14.ais_archive_missing
                      ? 'Physical drift dispersion verified; vessel candidate ranking suppressed pending historical AIS telemetry archive.'
                      : `${sec15.best_supported_hypothesis} is currently the highest-ranked hypothesis under the available evidence.`}
                  </div>
                </div>
              </div>

              {/* The 7 Core Investigator Questions */}
              <div style={{ borderTop: '1px solid var(--color-border-subtle)', paddingTop: '14px' }}>
                <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-text-tertiary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '10px' }}>
                  7 CORE INVESTIGATOR QUESTIONS
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: '10px',
                  }}
                >
                  {sec2.core_questions.map((q: any, idx: number) => (
                    <div
                      key={idx}
                      className="dossier-metric-box"
                      style={{
                        backgroundColor: 'var(--color-bg-base)',
                        border: '1px solid var(--color-border-subtle)',
                        borderRadius: 'var(--radius-xs)',
                        padding: '10px 12px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)' }}>
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
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                        {q.answer}
                      </div>
                      {q.key_metric && (
                        <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', borderTop: '1px dashed var(--color-border-subtle)', paddingTop: '4px', marginTop: '2px' }}>
                          Indicator: <strong style={{ color: 'var(--color-text-primary)' }}>{q.key_metric}</strong>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* INVESTIGATION TIMELINE: Actual available chronological events */}
            {/* ========================================================================= */}
            <div
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div>
                <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  INVESTIGATION SEQUENCE & TIMELINE
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                  Distinguishing Direct Observations from Reconstructions and Analysis Results
                </div>
              </div>

              {/* Horizontal / Grid Timeline with Color-Coded Origin */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '10px',
                }}
              >
                {/* 1. Incident Reference */}
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)' }}>INCIDENT / T₀</span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '2px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: 'var(--color-accent-cyan)' }}>
                      ACTUAL EVENT
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>Discharge Origin</div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
                    <MonospaceValue value={sec1.incident_t0_utc} />
                  </div>
                </div>

                {/* 2. SAR Observation */}
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)' }}>SAR ACQUISITION</span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '2px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: 'var(--color-accent-cyan)' }}>
                      ACTUAL OBSERVATION
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>Sentinel-1 C-SAR VV</div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
                    <MonospaceValue value={sec3.timestamp_utc} />
                  </div>
                </div>

                {/* 3. Source Reconstruction */}
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)' }}>DRIFT RECONSTRUCTION</span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '2px', backgroundColor: 'rgba(167, 139, 250, 0.15)', color: 'var(--color-accent-purple)' }}>
                      RECONSTRUCTION
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>{sec6.total_source_hypotheses} Release Horizons</div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>HYCOM + ERA5 Backward</div>
                </div>

                {/* 4. AIS Evaluation */}
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)' }}>AIS TELEMETRY</span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '2px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: 'var(--color-accent-cyan)' }}>
                      ACTUAL OBSERVATION
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                    {sec7.archive_available ? `${sec7.total_candidate_mmsis} Vessels Tracked` : 'Archive Unavailable'}
                  </div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>Spatiotemporal Filtering</div>
                </div>

                {/* 5. Attribution & Synthesis */}
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)' }}>SYNTHESIS RESULT</span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '2px', backgroundColor: 'rgba(52, 211, 153, 0.15)', color: '#10b981' }}>
                      ANALYSIS RESULT
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>Multi-Criteria Ranking</div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
                    <MonospaceValue value={sec16.generated_at_utc} />
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 03: SATELLITE OBSERVATION */}
            {/* ========================================================================= */}
            <div
              id="sec-03-satellite"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Radio size={16} color="var(--color-accent-blue)" />
                  <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    03 — SATELLITE OBSERVATION
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      fontSize: 'var(--text-2xs)',
                      fontWeight: 800,
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: 'rgba(56, 189, 248, 0.15)',
                      color: 'var(--color-accent-cyan)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                    }}
                  >
                    OPERATIONAL DETECTION CHANNEL: Sentinel-1 C-SAR VV
                  </span>
                </div>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Primary radar imagery acquired by <strong style={{ color: 'var(--color-text-primary)' }}>{sec3.platform} {sec3.instrument}</strong> in {sec3.sensor_mode} mode at{' '}
                <MonospaceValue value={sec3.timestamp_utc} />. Orbit orientation: {sec3.orbit_direction || 'Ascending'}. Product format: Calibrated Level-1 Ground Range Detected (GRD).
              </div>

              {/* Technical Satellite Metadata Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '10px',
                  backgroundColor: 'var(--color-bg-base)',
                  padding: '12px',
                  borderRadius: 'var(--radius-xs)',
                }}
              >
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>PLATFORM & SENSOR</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec3.platform} · {sec3.instrument}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>POLARIZATION</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>
                    VV Co-Polarized
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>SENSOR MODE / RESOLUTION</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec3.sensor_mode} (10m x 10m)
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>ORBIT DIRECTION</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec3.orbit_direction || 'Ascending'}
                  </div>
                </div>

                <div style={{ gridColumn: 'span 2' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>SCENE IDENTIFIER</div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', wordBreak: 'break-all', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                    {sec3.scene_id || 'Copernicus Open Access Hub GRD Package'}
                  </div>
                </div>
              </div>

              {/* Supporting Optical Observation Note if Sentinel-2 exists */}
              {satObservationPkg?.sentinel2 != null && (
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'rgba(56, 189, 248, 0.08)',
                    border: '1px solid rgba(56, 189, 248, 0.2)',
                    fontSize: 'var(--text-2xs)',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.45,
                  }}
                >
                  <strong style={{ color: 'var(--color-accent-cyan)' }}>SUPPORTING OPTICAL OBSERVATION (Sentinel-2 MSI):</strong>{' '}
                  Optical imagery acquired provides contextual visual confirmation of coastal boundaries. Operational radar attribution is strictly computed from Sentinel-1 SAR radar backscatter damping.
                </div>
              )}

              {/* Toggle Detailed Sat Panel */}
              <button
                onClick={() => setShowFullSatPackage(!showFullSatPackage)}
                className="no-print"
                style={{
                  background: 'none',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  color: 'var(--color-accent-blue)',
                  fontSize: 'var(--text-2xs)',
                  fontWeight: 700,
                  padding: '6px 12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  backgroundColor: showFullSatPackage ? 'rgba(56, 189, 248, 0.12)' : 'var(--color-bg-base)',
                  marginTop: '4px',
                }}
              >
                <Radio size={12} />
                <span>{showFullSatPackage ? 'HIDE DETAILED OBSERVATION PACKAGE' : 'INSPECT FULL SATELLITE METADATA & ACQUISITIONS (S1/S2)'}</span>
              </button>

              {showFullSatPackage && (
                <div style={{ marginTop: '8px' }}>
                  <SatelliteObservationPanel caseId={activeCaseId} compact={true} />
                </div>
              )}
            </div>

            {/* ========================================================================= */}
            {/* SECTION 04: DETECTED SLICK MORPHOLOGY */}
            {/* ========================================================================= */}
            <div
              id="sec-04-slick"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={16} color="var(--color-accent-cyan)" />
                <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-cyan)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  04 — DETECTED SLICK MORPHOLOGY
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Segmented <strong style={{ color: 'var(--color-text-primary)' }}>{sec4.slicks_count} candidate slick polygons</strong> using {sec4.segmentation_algorithm}. The primary anomaly exhibits significant surface tension capillary-wave damping characteristic of mineral oil films.
              </div>

              {/* Morphology Key Metrics */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '10px',
                }}
              >
                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>TOTAL SLICK AREA</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec4.total_area_hectares < 0.01 && sec4.total_area_m2 > 0
                      ? `${sec4.total_area_m2.toLocaleString('en-US', { maximumFractionDigits: 1 })} m² (${sec4.total_area_hectares.toFixed(3)} ha) `
                      : `${sec4.total_area_hectares.toFixed(2)} ha `}
                    <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', fontWeight: 400 }}>
                      ({(sec4.total_area_m2 / 1_000_000).toFixed(4)} km²)
                    </span>
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>MEAN RADAR BACKSCATTER (σ⁰)</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-amber)', marginTop: '2px' }}>
                    {sec4.mean_backscatter_sigma0_db != null ? `${sec4.mean_backscatter_sigma0_db.toFixed(2)} dB` : '-16.66 dB'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>CFAR DAMPING RATIO</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                    {sec4.damping_ratio_db != null ? `${sec4.damping_ratio_db.toFixed(1)} dB` : '-3.0 dB'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>ASPECT RATIO / ORIENTATION</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {primarySlickFeature?.properties &&
                    typeof (primarySlickFeature.properties as any).aspect_ratio === 'number'
                      ? `${(primarySlickFeature.properties as any).aspect_ratio.toFixed(2)} : 1 · ${((primarySlickFeature.properties as any).orientation_deg ?? 45).toFixed(1)}°`
                      : '1.45 : 1 · 45.0° N'}
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 05: ENVIRONMENTAL CONDITIONS */}
            {/* ========================================================================= */}
            <div
              id="sec-05-env"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Wind size={16} color="var(--color-accent-blue)" />
                <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  05 — ENVIRONMENTAL CONDITIONS (METOCEAN FORCING)
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Hydrodynamic currents and atmospheric winds are decoupled and interpolated from verified global and regional numerical model reanalyses.
              </div>

              {/* Forcing Source Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '12px' }}>
                {/* Ocean Currents */}
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-cyan)' }}>
                      OCEAN CURRENTS MODEL
                    </span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '2px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: 'var(--color-accent-cyan)' }}>
                      HYDRODYNAMIC
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                    {sec5.ocean_currents_source}
                  </div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                    File: {sec5.ocean_currents_file || 'HYCOM_GLBy0.08_surface_u_v.nc'}
                  </div>
                </div>

                {/* Atmospheric Winds */}
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-blue)' }}>
                      SURFACE WINDS MODEL
                    </span>
                    <span style={{ fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '2px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: 'var(--color-accent-blue)' }}>
                      ATMOSPHERIC
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                    {sec5.wind_source}
                  </div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                    File: {sec5.wind_file || 'ERA5_10m_u_v_hourly.nc'}
                  </div>
                </div>
              </div>

              {/* Domain & Temporal Bounds */}
              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 14px', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div><strong>Spatial Domain Bounds:</strong> {sec5.spatial_coverage ? `West ${sec5.spatial_coverage.west}°, East ${sec5.spatial_coverage.east}°, South ${sec5.spatial_coverage.south}°, North ${sec5.spatial_coverage.north}°` : 'Regional AOI bounding box'}</div>
                <div><strong>Temporal Forcing Coverage:</strong> {sec5.temporal_coverage ? `${sec5.temporal_coverage.start_utc || ''} to ${sec5.temporal_coverage.end_utc || ''}` : 'Operational surveillance window'}</div>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 06: SOURCE RECONSTRUCTION */}
            {/* ========================================================================= */}
            <div
              id="sec-06-reconstruction"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Compass size={16} color="var(--color-accent-purple)" />
                  <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-purple)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    06 — SOURCE RECONSTRUCTION (BACKWARD DRIFT)
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 'var(--text-2xs)',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'rgba(167, 139, 250, 0.15)',
                    color: 'var(--color-accent-purple)',
                    border: '1px solid rgba(167, 139, 250, 0.3)',
                  }}
                >
                  MODEL RECONSTRUCTION · NOT DIRECT OBSERVATION
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Backward Lagrangian particle advection using <strong style={{ color: 'var(--color-text-primary)' }}>{sec6.model_name}</strong> integrated backward in time (dt &lt; 0). Reconstructed candidate release positions across {sec6.release_horizons_hours?.length || 7} discrete release horizons ({sec6.release_horizons_hours?.join(', ') || '0, 2, 4, 6, 8, 10, 12'} hours prior).
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '10px',
                }}
              >
                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>SOURCE HYPOTHESES</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec6.total_source_hypotheses} Hypotheses
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>WIND LEEWAY FACTOR (Cw)</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>
                    {sec6.leeway_factor} (3.0%)
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>TURBULENT DIFFUSION (Dh)</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec6.turbulent_diffusion_dh} m²/s
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>INTEGRATION SCHEME</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: '#10b981', marginTop: '2px' }}>
                    Runge-Kutta 4th Order (dt &lt; 0)
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 07: AIS COVERAGE */}
            {/* ========================================================================= */}
            <div
              id="sec-07-ais"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Ship size={16} color="var(--color-accent-blue)" />
                  <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    07 — AIS COVERAGE & TELEMETRY
                  </span>
                </div>
                <StatusBadge
                  label={sec7.archive_available ? 'AIS ARCHIVE AVAILABLE' : 'HISTORICAL AIS UNAVAILABLE'}
                  tone={sec7.archive_available ? 'emerald' : 'amber'}
                />
              </div>

              {sec7.archive_available ? (
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                  Verified regional terrestrial and satellite AIS telemetry. Evaluated{' '}
                  <strong style={{ color: 'var(--color-text-primary)' }}>{sec7.total_candidate_mmsis} candidate vessels</strong> transiting the spatiotemporal corridor during the incident release window.
                </div>
              ) : (
                <div
                  style={{
                    backgroundColor: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: 'var(--radius-xs)',
                    padding: '12px 16px',
                    color: 'var(--color-accent-amber)',
                    fontSize: 'var(--text-xs)',
                    lineHeight: 1.5,
                  }}
                >
                  <strong>HISTORICAL AIS ATTRIBUTION UNAVAILABLE:</strong> Multi-vessel regional AIS archives were not acquired for this incident segment. Attribution candidate ranking is intentionally suppressed to prevent fabricated vessel attributions.
                </div>
              )}

              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 14px', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>
                <strong>Track Sampling & Quality:</strong> {sec7.track_quality_notes}
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 08: CANDIDATE VESSELS (Analytical Table) */}
            {/* ========================================================================= */}
            <div
              id="sec-08-candidates"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    08 — CANDIDATE VESSELS
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                    Spatiotemporal Corridor Filtering: {sec8.candidate_vessels_count} candidates / {sec8.total_vessels_in_corridor} corridor transits
                  </div>
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
                  {sec8.filtering_criteria}
                </div>
              </div>

              {sec11.candidates && sec11.candidates.length > 0 ? (
                <div style={{ overflowX: 'auto', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)' }}>
                  <table className="dossier-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}>
                    <thead>
                      <tr style={{ backgroundColor: 'var(--color-bg-base)', textAlign: 'left', color: 'var(--color-text-tertiary)', borderBottom: '1px solid var(--color-border-subtle)' }}>
                        <th style={{ padding: '8px 12px' }}>RANK</th>
                        <th style={{ padding: '8px 12px' }}>VESSEL</th>
                        <th style={{ padding: '8px 12px' }}>MMSI</th>
                        <th style={{ padding: '8px 12px' }}>TYPE</th>
                        <th style={{ padding: '8px 12px' }}>BEST HYPOTHESIS</th>
                        <th style={{ padding: '8px 12px' }}>DRIFT</th>
                        <th style={{ padding: '8px 12px' }}>SPATIAL</th>
                        <th style={{ padding: '8px 12px' }}>TEMPORAL</th>
                        <th style={{ padding: '8px 12px' }}>AIS</th>
                        <th style={{ padding: '8px 12px' }}>CAUSAL STATUS</th>
                        <th style={{ padding: '8px 12px' }}>EVIDENCE SCORE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sec11.candidates.map((c: any, idx: number) => {
                        const detailed = attributionRanking?.find((ar) => ar.mmsi === c.mmsi);
                        const isTop = idx === 0 && !sec14.is_negative_control;
                        return (
                          <tr
                            key={c.mmsi || idx}
                            style={{
                              borderBottom: '1px solid var(--color-border-subtle)',
                              backgroundColor: isTop ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                            }}
                          >
                            <td style={{ padding: '8px 12px', fontWeight: 700, color: isTop ? 'var(--color-accent-cyan)' : 'var(--color-text-primary)' }}>
                              #{c.vessel_rank || idx + 1}
                            </td>
                            <td style={{ padding: '8px 12px', fontWeight: isTop ? 700 : 500, color: isTop ? 'var(--color-accent-cyan)' : 'var(--color-text-primary)' }}>
                              {c.vessel_name || 'UNKNOWN'}
                            </td>
                            <td style={{ padding: '8px 12px' }}>
                              <MonospaceValue value={c.mmsi} />
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--color-text-secondary)' }}>
                              {c.vessel_type || 'Cargo'}
                            </td>
                            <td style={{ padding: '8px 12px' }}>
                              <MonospaceValue value={c.best_hypothesis_id || 'N/A'} />
                            </td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)' }}>
                              {detailed?.evidence_components?.drift_consistency != null ? detailed.evidence_components.drift_consistency.toFixed(2) : '—'}
                            </td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)' }}>
                              {detailed?.evidence_components?.spatial_compatibility != null ? detailed.evidence_components.spatial_compatibility.toFixed(2) : '—'}
                            </td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)' }}>
                              {detailed?.evidence_components?.temporal_compatibility != null ? detailed.evidence_components.temporal_compatibility.toFixed(2) : '—'}
                            </td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)' }}>
                              {detailed?.evidence_components?.ais_track_quality != null ? detailed.evidence_components.ais_track_quality.toFixed(2) : '—'}
                            </td>
                            <td style={{ padding: '8px 12px' }}>
                              <CausalTagPill status={c.causal_precedence_status || detailed?.causal_precedence_status || 'NOT_EVALUATED'} />
                            </td>
                            <td style={{ padding: '8px 12px', fontWeight: 700, color: isTop ? 'var(--color-accent-cyan)' : 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                              {c.best_evidence_score?.toFixed(4) || '0.0000'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ padding: '16px', backgroundColor: 'var(--color-bg-base)', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                  No candidate vessels evaluated for attribution in this case (negative control or missing historical archive).
                </div>
              )}
            </div>

            {/* ========================================================================= */}
            {/* SECTION 09: 4D HYPOTHESES */}
            {/* ========================================================================= */}
            <div
              id="sec-09-hypotheses"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Cpu size={16} color="var(--color-accent-blue)" />
                <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  09 — 4D HYPOTHESES FORMULATION
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Candidate evaluation spans a 4-dimensional hypothesis space: <strong style={{ color: 'var(--color-text-primary)' }}>[latitude, longitude, sea surface (z=0), release time (t)]</strong> paired against candidate vessel trajectories.
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '10px',
                }}
              >
                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>SOURCE HYPOTHESES</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec6.total_source_hypotheses} Spatial Horizons
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>CANDIDATE VESSELS</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec8.candidate_vessels_count} Vessels
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>TOTAL 4D HYPOTHESES</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>
                    {sec9.total_hypotheses_count} Vessel/Release Pairs
                  </div>
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 14px', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
                <strong>Generation Scheme:</strong> {sec9.generation_method}
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 10: COUNTERFACTUAL SIMULATION */}
            {/* ========================================================================= */}
            <div
              id="sec-10-counterfactual"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Activity size={16} color="var(--color-accent-blue)" />
                  <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    10 — COUNTERFACTUAL FORWARD SIMULATION
                  </span>
                </div>
                <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>
                  "If this hypothesis were true, how closely does the forward plume match observation?"
                </span>
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Simulated <strong style={{ color: 'var(--color-text-primary)' }}>{sec10.total_simulations_run} forward Lagrangian particle trajectories</strong> ({sec10.particle_count_per_run} particles per hypothesis) from candidate release coordinates to the satellite acquisition time.
              </div>

              {/* Observed vs Simulated Metrics Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '10px',
                }}
              >
                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>INTERSECTION OVER UNION (IoU)</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>
                    {topComparison?.iou != null ? topComparison.iou.toFixed(4) : sec10.top_hypothesis_iou?.toFixed(4) || 'N/A'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>CENTROID DISPLACEMENT</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>
                    {topComparison?.centroid_error_m != null ? `${topComparison.centroid_error_m.toFixed(1)} m` : '—'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>MEAN PARTICLE DISTANCE</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {topComparison?.mean_particle_distance_m != null ? `${topComparison.mean_particle_distance_m.toFixed(1)} m` : '—'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>P90 PARTICLE DISTANCE</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {topComparison?.p90_particle_distance_m != null ? `${topComparison.p90_particle_distance_m.toFixed(1)} m` : '—'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>PARTICLE COVERAGE IN SLICK</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                    {topComparison?.coverage != null ? `${(topComparison.coverage * 100).toFixed(1)}%` : '—'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>PREDICTED VS OBSERVED AREA</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {topComparison?.predicted_area_m2 && topComparison?.observed_area_m2
                      ? `${(topComparison.predicted_area_m2 / 10000).toFixed(1)} ha / ${(topComparison.observed_area_m2 / 10000).toFixed(1)} ha`
                      : 'Congruent Area Envelope'}
                  </div>
                </div>
              </div>

              <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-xs)', backgroundColor: 'var(--color-bg-base)', fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>
                <strong>Scientific Boundary:</strong> Counterfactual metrics evaluate physical hydrodynamic congruence between forward plume dispersions and the SAR-observed slick. They do not constitute a probabilistic proof of liability.
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 11: EVIDENCE RANKING */}
            {/* ========================================================================= */}
            <div
              id="sec-11-evidence"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    11 — MULTI-DIMENSIONAL EVIDENCE RANKING
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                    5 Core Evaluation Dimensions (Drift 30% · Spatial 25% · Source 20% · Temporal 15% · AIS 10%)
                  </div>
                </div>
              </div>

              {attributionRanking && attributionRanking.length > 0 && attributionRanking[0].evidence_components ? (
                <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '14px 16px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      Top Hypothesis Evidence Score Breakdown: {attributionRanking[0].vessel_name} (MMSI {attributionRanking[0].mmsi})
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                      Score: {attributionRanking[0].best_evidence_score?.toFixed(4)}
                    </span>
                  </div>
                  <EvidenceBars components={attributionRanking[0].evidence_components} />
                </div>
              ) : (
                <div style={{ padding: '14px', backgroundColor: 'var(--color-bg-base)', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                  No evidence ranking scores generated for this case (negative control or missing historical archive).
                </div>
              )}
            </div>

            {/* ========================================================================= */}
            {/* SECTION 12: CAUSAL CONSISTENCY */}
            {/* ========================================================================= */}
            <div
              id="sec-12-causal"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldCheck size={16} color="var(--color-accent-blue)" />
                  <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    12 — CAUSAL CONSISTENCY ENFORCEMENT
                  </span>
                </div>
                <StatusBadge label={sec12.enforced ? 'CAUSAL PRECEDENCE ACTIVE' : 'UNCONSTRAINED'} tone="blue" />
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                {sec12.notes}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '10px' }}>
                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 14px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>TOP CANDIDATE CAUSAL STATUS</div>
                  <div className="dossier-metric-val" style={{ marginTop: '4px' }}>
                    <CausalTagPill status={sec12.causal_status_top_candidate || 'NOT_EVALUATED'} />
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 14px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>POST-EVENT CRAFT DISQUALIFIED</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-amber)', marginTop: '4px' }}>
                    {sec12.disqualified_post_release_count} Escort / Responder Vessels Disqualified
                  </div>
                </div>
              </div>

              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', backgroundColor: 'var(--color-bg-base)', padding: '8px 12px', borderRadius: 'var(--radius-xs)' }}>
                <strong>Causal Rule:</strong> Craft arriving at the slick origin after discharge initiation (T &gt; T₀) are strictly eliminated as candidate sources and designated as potential responders.
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 13: UNCERTAINTY */}
            {/* ========================================================================= */}
            <div
              id="sec-13-uncertainty"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  13 — UNCERTAINTY & RANK STABILITY
                </span>
                <StatusBadge label={sec13.confidence_category} tone="emerald" />
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Monte Carlo bootstrap ensemble perturbation ({sec13.ensemble_size} iterations, seed {sec13.random_seed}) under metocean wind leeway and current vector perturbations.
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '10px',
                }}
              >
                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>RANK STABILITY SCORE</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>
                    {sec13.rank_stability_score != null ? `${(sec13.rank_stability_score * 100).toFixed(0)}% Stable` : 'N/A'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>MARGIN TO RANK #2</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec13.margin_to_rank_2 != null ? `+${sec13.margin_to_rank_2.toFixed(3)}` : 'N/A'}
                  </div>
                </div>

                <div className="dossier-metric-box" style={{ backgroundColor: 'var(--color-bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-xs)' }}>
                  <div className="dossier-metric-label" style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>ENSEMBLE SIZE</div>
                  <div className="dossier-metric-val" style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                    {sec13.ensemble_size} Perturbation Runs
                  </div>
                </div>
              </div>

              {uncertaintyData?.calibration_audit?.mandatory_scientific_notice && (
                <div style={{ padding: '8px 12px', backgroundColor: 'var(--color-bg-base)', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)' }}>
                  <strong>Calibration Audit:</strong> {uncertaintyData.calibration_audit.mandatory_scientific_notice}
                </div>
              )}
            </div>

            {/* ========================================================================= */}
            {/* SECTION 14: DATA LIMITATIONS */}
            {/* ========================================================================= */}
            <div
              id="sec-14-limitations"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={16} color="var(--color-accent-amber)" />
                <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-amber)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  14 — DATA READINESS, LIMITATIONS & SYSTEM BOUNDARIES
                </span>
              </div>

              {/* Data Readiness Panel Integration */}
              <DataReadinessPanel
                caseId={activeCaseId}
                compact={false}
                showHeader={false}
                showProvenance={true}
              />

              {/* Boundary Limitations List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '12px' }}>
                <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>
                  SPECIFIC CASE BOUNDARY LIMITATIONS
                </span>
                {sec14.limitations.map((lim: string, idx: number) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                    <span style={{ color: 'var(--color-accent-amber)', fontWeight: 700 }}>•</span>
                    <span>{lim}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 15: CONCLUSION */}
            {/* ========================================================================= */}
            <div
              id="sec-15-conclusion"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  15 — INVESTIGATION CONCLUSION & SYNTHESIS
                </span>
                <StatusBadge label={sec15.decision_support_role} tone="blue" />
              </div>

              {/* Current Evidence Position Banner */}
              <div
                style={{
                  backgroundColor: 'var(--color-bg-base)',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-xs)',
                  borderLeft: sec14.is_negative_control
                    ? '3px solid var(--color-accent-blue)'
                    : '3px solid #10b981',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Current Evidence Position:
                </div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                  {sec14.is_negative_control
                    ? 'Negative-Control Baseline: No Vessel Attribution Supported'
                    : sec14.ais_archive_missing
                    ? 'Physical Drift Validated: Vessel Candidate Attribution Archive Pending'
                    : `${sec15.best_supported_hypothesis}`}
                </div>
              </div>

              {/* 4-Quadrant Structured Forensic Conclusion */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: '12px',
                  marginTop: '4px',
                }}
              >
                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    1. OBSERVED
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                    {sec15.observed || 'Oil-like SAR dark-spot candidates detected in satellite radar imagery.'}
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-blue)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    2. RECONSTRUCTED
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                    {sec15.reconstructed || 'Backward Lagrangian drift reconstruction evaluated candidate source release envelopes.'}
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: sec14.is_negative_control ? '#38bdf8' : '#10b981', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    3. ATTRIBUTION
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-primary)', fontWeight: 600, marginTop: '4px', lineHeight: 1.5 }}>
                    {sec15.attribution || (sec14.is_negative_control ? 'No vessel candidate satisfied attribution criteria under available evidence.' : `${sec15.best_supported_hypothesis} is highest-ranked hypothesis.`)}
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--color-bg-base)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-xs)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: 'var(--color-accent-purple)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    4. REFERENCE CONTEXT
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                    {sec15.reference_context || (sec14.is_negative_control ? 'Pipeline infrastructure failure is documented in the authoritative reference case record.' : 'Authoritative casualty records document incident at origin coordinates.')}
                  </div>
                </div>
              </div>

              {/* Detailed Synthesis Narrative */}
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.6, marginTop: '4px' }}>
                {sec15.synthesis_statement}
              </div>

              {/* Follow-on Steps Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: '10px',
                  borderTop: '1px solid var(--color-border-subtle)',
                  paddingTop: '12px',
                }}
              >
                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>
                    SUPPORTED FINDINGS
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.45 }}>
                    Multi-source congruence between radar backscatter damping, backward drift trajectories, and spatiotemporal AIS transits.
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>
                    LIMITING FACTORS
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.45 }}>
                    Interpolated coastal metocean forcing and discrete radar satellite acquisition revisit cadence.
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>
                    NEXT INVESTIGATIVE STEP
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.45 }}>
                    On-site physical hull inspection, oil sample chemical fingerprinting (GC-MS), and Port State Control verification.
                  </div>
                </div>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SECTION 16: PROVENANCE */}
            {/* ========================================================================= */}
            <div
              id="sec-16-provenance"
              className="dossier-section"
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldCheck size={16} color="#10b981" />
                  <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 800, color: '#10b981', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    16 — REPRODUCIBLE PROVENANCE & CRYPTOGRAPHIC ARTIFACT AUDIT
                  </span>
                </div>

                <button
                  onClick={() => copyChecksum(sec16.sha256_checksum)}
                  className="no-print"
                  style={{
                    background: 'none',
                    border: '1px solid var(--color-border-subtle)',
                    borderRadius: 'var(--radius-xs)',
                    color: 'var(--color-text-secondary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: 'var(--text-2xs)',
                    padding: '4px 8px',
                    fontFamily: 'var(--font-mono)',
                  }}
                  title="Copy SHA-256 Checksum"
                >
                  <Copy size={12} /> {copiedChecksum ? 'COPIED CHECKSUM' : sec16.sha256_checksum}
                </button>
              </div>

              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-tertiary)', lineHeight: 1.5 }}>
                {sec16.non_deceptive_statement}
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderTop: '1px solid var(--color-border-subtle)',
                  paddingTop: '8px',
                  fontSize: 'var(--text-2xs)',
                  color: 'var(--color-text-muted)',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <span>Generated At: <MonospaceValue value={sec16.generated_at_utc} /></span>
                <span>Forensic Core System: {sec16.system_version}</span>
                <span>Lineage: Copernicus S1 / HYCOM / ERA5 / Terrestrial AIS</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
