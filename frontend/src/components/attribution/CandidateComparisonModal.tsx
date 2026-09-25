import React, { useState } from 'react';
import type { VesselAttributionItem } from '../../api/casesApi';
import { MonospaceValue } from '../common/MonospaceValue';
import { CausalTagPill } from './CausalTagPill';
import { DomainTooltip } from '../common/DomainTooltip';
import {
  X,
  GitCompare,
  CheckCircle2,
  AlertTriangle,
  Compass,
  Clock,
  Radio,
  Activity,
  Layers,
  ShieldAlert,
} from 'lucide-react';

interface CandidateComparisonModalProps {
  candidates: VesselAttributionItem[];
  initialCandidateA?: VesselAttributionItem;
  initialCandidateB?: VesselAttributionItem;
  onClose: () => void;
}

export const CandidateComparisonModal: React.FC<CandidateComparisonModalProps> = ({
  candidates,
  initialCandidateA,
  initialCandidateB,
  onClose,
}) => {
  // Candidate A defaults to Rank 1 (best-supported hypothesis)
  const defaultA = initialCandidateA || candidates.find((c) => c.vessel_rank === 1) || candidates[0];
  // Candidate B defaults to initialCandidateB or Rank 2 or a lower-ranked candidate
  const defaultB =
    initialCandidateB && initialCandidateB.mmsi !== defaultA?.mmsi
      ? initialCandidateB
      : candidates.find((c) => c.mmsi !== defaultA?.mmsi) || candidates[1] || candidates[0];

  const [mmsiA, setMmsiA] = useState<number>(defaultA?.mmsi || 0);
  const [mmsiB, setMmsiB] = useState<number>(defaultB?.mmsi || 0);

  const candA = candidates.find((c) => c.mmsi === mmsiA) || defaultA;
  const candB = candidates.find((c) => c.mmsi === mmsiB) || defaultB;

  if (!candA || !candB) return null;

  const metricsA = candA.underlying_metrics;
  const metricsB = candB.underlying_metrics;

  const formatDistance = (m?: number | null) => {
    if (m === undefined || m === null) return '—';
    if (m >= 1000) return `${(m / 1000).toFixed(2)} km`;
    return `${m.toFixed(1)} m`;
  };

  const formatScore = (val?: number | null) => {
    if (val === undefined || val === null) return '—';
    return val.toFixed(4);
  };

  const getMetricDiffColor = (valA?: number | null, valB?: number | null, higherIsBetter = true) => {
    if (valA === undefined || valA === null || valB === undefined || valB === null) return 'var(--color-text-secondary)';
    if (valA === valB) return 'var(--color-text-secondary)';
    const aBetter = higherIsBetter ? valA > valB : valA < valB;
    return aBetter ? 'var(--color-accent-emerald)' : 'var(--color-accent-amber)';
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 8, 14, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '1020px',
          maxHeight: '90vh',
          backgroundColor: 'var(--color-bg-base)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-2xl)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid var(--color-border-subtle)',
            backgroundColor: 'rgba(17, 24, 39, 0.95)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(56, 189, 248, 0.12)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-accent-cyan)',
              }}
            >
              <GitCompare size={18} />
            </div>
            <div>
              <div
                style={{
                  fontSize: 'var(--text-sm)',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                }}
              >
                HEAD-TO-HEAD CANDIDATE EVIDENCE COMPARISON
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                Factual spatiotemporal compatibility breakdown · Strict artifact metrics
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-xs)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ overflowY: 'auto', flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Candidate Selection Bar */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 60px 1fr',
              alignItems: 'center',
              gap: '14px',
              padding: '12px 16px',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border-subtle)',
            }}
          >
            {/* Candidate A Selector */}
            <div>
              <label style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                HYPOTHESIS A (Primary Benchmark)
              </label>
              <select
                value={mmsiA}
                onChange={(e) => setMmsiA(Number(e.target.value))}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  backgroundColor: 'var(--color-bg-base)',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  outline: 'none',
                }}
              >
                {candidates.map((c) => (
                  <option key={c.mmsi} value={c.mmsi}>
                    #{c.vessel_rank} · {c.vessel_name} (MMSI: {c.mmsi}) — Score: {c.best_evidence_score.toFixed(4)}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', fontWeight: 700 }}>
              VS
            </div>

            {/* Candidate B Selector */}
            <div>
              <label style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                HYPOTHESIS B (Comparative Candidate)
              </label>
              <select
                value={mmsiB}
                onChange={(e) => setMmsiB(Number(e.target.value))}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  backgroundColor: 'var(--color-bg-base)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  outline: 'none',
                }}
              >
                {candidates.map((c) => (
                  <option key={c.mmsi} value={c.mmsi}>
                    #{c.vessel_rank} · {c.vessel_name} (MMSI: {c.mmsi}) — Score: {c.best_evidence_score.toFixed(4)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Side-by-Side Top Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* Card A */}
            <div
              style={{
                padding: '14px 18px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(56, 189, 248, 0.04)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 800,
                      color: 'var(--color-accent-blue)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    #{candA.vessel_rank}
                  </span>
                  <span style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                    {candA.vessel_name}
                  </span>
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '4px', display: 'flex', gap: '8px' }}>
                  <span>MMSI: <MonospaceValue value={candA.mmsi} /></span>
                  <span>• Type: {candA.vessel_type}</span>
                  <span>• Hyp: {candA.best_hypothesis_id}</span>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 800, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                  {candA.best_evidence_score.toFixed(4)}
                </div>
                <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  COMPATIBILITY SCORE
                </div>
              </div>
            </div>

            {/* Card B */}
            <div
              style={{
                padding: '14px 18px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--color-border-subtle)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 800,
                      color: 'var(--color-text-secondary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    #{candB.vessel_rank}
                  </span>
                  <span style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                    {candB.vessel_name}
                  </span>
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '4px', display: 'flex', gap: '8px' }}>
                  <span>MMSI: <MonospaceValue value={candB.mmsi} /></span>
                  <span>• Type: {candB.vessel_type}</span>
                  <span>• Hyp: {candB.best_hypothesis_id}</span>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 800, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                  {candB.best_evidence_score.toFixed(4)}
                </div>
                <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  COMPATIBILITY SCORE
                </div>
              </div>
            </div>
          </div>

          {/* Side-by-Side Underlying Physical Metric Comparison Table */}
          <div
            style={{
              backgroundColor: 'rgba(10, 13, 19, 0.6)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border-subtle)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '10px 16px',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderBottom: '1px solid var(--color-border-subtle)',
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-text-secondary)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}
            >
              PHYSICAL EVIDENCE COMPATIBILITY BREAKDOWN
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', color: 'var(--color-text-muted)', fontSize: '10px', textTransform: 'uppercase' }}>
                  <th style={{ padding: '8px 14px', textAlign: 'left', width: '28%' }}>Evidence Dimension</th>
                  <th style={{ padding: '8px 14px', textAlign: 'left', width: '36%', color: 'var(--color-accent-cyan)' }}>
                    {candA.vessel_name} (Rank #{candA.vessel_rank})
                  </th>
                  <th style={{ padding: '8px 14px', textAlign: 'left', width: '36%' }}>
                    {candB.vessel_name} (Rank #{candB.vessel_rank})
                  </th>
                </tr>
              </thead>
              <tbody>
                {/* 1. Spatial Distance */}
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Compass size={13} color="var(--color-accent-blue)" />
                    <span>Source Distance</span>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                    <div style={{ fontWeight: 700, color: getMetricDiffColor(metricsA?.vessel_source_distance_m, metricsB?.vessel_source_distance_m, false) }}>
                      {formatDistance(metricsA?.vessel_source_distance_m)}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                      Spatial Score: {formatScore(metricsA?.spatial_score)}
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                    <div style={{ fontWeight: 700, color: getMetricDiffColor(metricsB?.vessel_source_distance_m, metricsA?.vessel_source_distance_m, false) }}>
                      {formatDistance(metricsB?.vessel_source_distance_m)}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                      Spatial Score: {formatScore(metricsB?.spatial_score)}
                    </div>
                  </td>
                </tr>

                {/* 2. Drift Centroid Error */}
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Activity size={13} color="var(--color-accent-cyan)" />
                    <span>Drift Centroid Error</span>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                    <div style={{ fontWeight: 700, color: getMetricDiffColor(metricsA?.centroid_error_m, metricsB?.centroid_error_m, false) }}>
                      {metricsA?.centroid_error_m !== undefined && metricsA?.centroid_error_m !== null ? `${metricsA.centroid_error_m.toFixed(2)} m` : '—'}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                      Drift Score: {formatScore(metricsA?.drift_score)}
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                    <div style={{ fontWeight: 700, color: getMetricDiffColor(metricsB?.centroid_error_m, metricsA?.centroid_error_m, false) }}>
                      {metricsB?.centroid_error_m !== undefined && metricsB?.centroid_error_m !== null ? `${metricsB.centroid_error_m.toFixed(2)} m` : '—'}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                      Drift Score: {formatScore(metricsB?.drift_score)}
                    </div>
                  </td>
                </tr>

                {/* 3. Temporal Alignment */}
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Clock size={13} color="var(--color-accent-amber)" />
                    <span>Hypothesized Release</span>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-primary)' }}>
                      {metricsA?.release_timestamp ? new Date(metricsA.release_timestamp).toUTCString().replace('GMT', 'UTC') : '—'}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Temporal Score: {formatScore(metricsA?.temporal_score)}
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-primary)' }}>
                      {metricsB?.release_timestamp ? new Date(metricsB.release_timestamp).toUTCString().replace('GMT', 'UTC') : '—'}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Temporal Score: {formatScore(metricsB?.temporal_score)}
                    </div>
                  </td>
                </tr>

                {/* 4. AIS Telemetry Quality */}
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Radio size={13} color="var(--color-accent-purple)" />
                    <DomainTooltip term="AIS" inline>
                      <span>AIS Trajectory Quality</span>
                    </DomainTooltip>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {metricsA?.ais_track_quality || 'continuous'}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Gap: {metricsA?.ais_gap_seconds !== undefined && metricsA?.ais_gap_seconds !== null ? `${metricsA.ais_gap_seconds.toFixed(0)} s` : '0 s'} · Score: {formatScore(metricsA?.ais_quality_score)}
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {metricsB?.ais_track_quality || 'continuous'}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Gap: {metricsB?.ais_gap_seconds !== undefined && metricsB?.ais_gap_seconds !== null ? `${metricsB.ais_gap_seconds.toFixed(0)} s` : '0 s'} · Score: {formatScore(metricsB?.ais_quality_score)}
                    </div>
                  </td>
                </tr>

                {/* 5. Causal Precedence */}
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ShieldAlert size={13} color="var(--color-accent-emerald)" />
                    <DomainTooltip term="Causal consistency" inline>
                      <span>Causal Status</span>
                    </DomainTooltip>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CausalTagPill status={candA.causal_precedence_status || 'UNKNOWN'} />
                      <span style={{ fontSize: '10px', color: candA.causal_precedence_status === 'AT_RELEASE' ? 'var(--color-accent-emerald)' : 'var(--color-text-muted)' }}>
                        {candA.causal_precedence_status === 'AT_RELEASE' ? 'Eligible' : 'Evaluated'}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CausalTagPill status={candB.causal_precedence_status || 'UNKNOWN'} />
                      <span style={{ fontSize: '10px', color: candB.causal_precedence_status === 'AT_RELEASE' ? 'var(--color-accent-emerald)' : 'var(--color-text-muted)' }}>
                        {candB.causal_precedence_status === 'AT_RELEASE' ? 'Eligible' : 'Evaluated'}
                      </span>
                    </div>
                  </td>
                </tr>

                {/* 6. Forward Simulation Overlap */}
                {(metricsA?.iou !== undefined || metricsB?.iou !== undefined) && (
                  <tr>
                    <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Layers size={13} color="var(--color-accent-cyan)" />
                      <DomainTooltip term="IoU" inline>
                        <span>Forward Slick IoU</span>
                      </DomainTooltip>
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                      <div style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>
                        {metricsA?.iou !== undefined && metricsA?.iou !== null ? metricsA.iou.toFixed(4) : '—'}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                        Coverage: {metricsA?.coverage !== undefined && metricsA?.coverage !== null ? `${(metricsA.coverage * 100).toFixed(1)}%` : '—'}
                      </div>
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>
                      <div style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>
                        {metricsB?.iou !== undefined && metricsB?.iou !== null ? metricsB.iou.toFixed(4) : '—'}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                        Coverage: {metricsB?.coverage !== undefined && metricsB?.coverage !== null ? `${(metricsB.coverage * 100).toFixed(1)}%` : '—'}
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Side-by-Side Why Highly vs Limiting Factors */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* Candidate A Evidence Summary */}
            <div
              style={{
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--color-border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-accent-emerald)', display: 'flex', alignItems: 'center', gap: '6px', textTransform: 'uppercase' }}>
                <CheckCircle2 size={13} />
                <span>WHY {candA.vessel_name} IS RANKED HIGHLY</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: 'var(--text-xs)' }}>
                {candA.evidence_breakdown?.why_ranked_highly && candA.evidence_breakdown.why_ranked_highly.length > 0 ? (
                  candA.evidence_breakdown.why_ranked_highly.map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                      <span style={{ color: 'var(--color-accent-emerald)', marginTop: '1px' }}>✓</span>
                      <span>{item}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: 'var(--color-text-muted)', fontSize: '11px' }}>
                    Sufficient physical compatibility across evaluation dimensions.
                  </div>
                )}
              </div>

              {candA.evidence_breakdown?.limiting_factors && candA.evidence_breakdown.limiting_factors.length > 0 && (
                <div style={{ marginTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '8px' }}>
                  <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-accent-amber)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    LIMITING FACTORS
                  </div>
                  {candA.evidence_breakdown.limiting_factors.map((lf, idx) => (
                    <div key={idx} style={{ fontSize: '11px', color: 'var(--color-text-muted)', lineHeight: 1.35, marginBottom: '4px' }}>
                      • {lf.detail}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Candidate B Limiting Factors */}
            <div
              style={{
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--color-border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ fontSize: '11px', fontWeight: 700, color: candB.vessel_rank === 1 ? 'var(--color-accent-emerald)' : 'var(--color-accent-amber)', display: 'flex', alignItems: 'center', gap: '6px', textTransform: 'uppercase' }}>
                <AlertTriangle size={13} />
                <span>
                  {candB.vessel_rank === 1 ? `WHY ${candB.vessel_name} IS RANKED HIGHLY` : `WHY NOT ${candB.vessel_name} (LIMITING FACTORS)`}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: 'var(--text-xs)' }}>
                {candB.evidence_breakdown?.limiting_factors && candB.evidence_breakdown.limiting_factors.length > 0 ? (
                  candB.evidence_breakdown.limiting_factors.map((lf, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '6px 10px',
                        backgroundColor: lf.severity === 'DISQUALIFYING' ? 'rgba(248, 81, 73, 0.08)' : 'rgba(210, 153, 34, 0.08)',
                        borderLeft: `2px solid ${lf.severity === 'DISQUALIFYING' ? 'var(--color-accent-red)' : 'var(--color-accent-amber)'}`,
                        borderRadius: 'var(--radius-xs)',
                        color: 'var(--color-text-secondary)',
                        lineHeight: 1.4,
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: '11px', color: lf.severity === 'DISQUALIFYING' ? 'var(--color-accent-red)' : 'var(--color-accent-amber)', marginBottom: '2px' }}>
                        {lf.label}
                      </div>
                      <div style={{ fontSize: '11px' }}>{lf.detail}</div>
                    </div>
                  ))
                ) : candB.evidence_breakdown?.why_not_ranked_higher && candB.evidence_breakdown.why_not_ranked_higher.length > 0 ? (
                  candB.evidence_breakdown.why_not_ranked_higher.map((item, idx) => (
                    <div key={idx} style={{ color: 'var(--color-text-secondary)', fontSize: '11px' }}>
                      • {item}
                    </div>
                  ))
                ) : (
                  <div style={{ color: 'var(--color-text-muted)', fontSize: '11px' }}>
                    Ranked as compatible hypothesis (#{candB.vessel_rank}) with overall score {candB.best_evidence_score.toFixed(4)}.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Forensic Comparative Summary */}
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: 'rgba(56, 189, 248, 0.06)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            <div style={{ fontSize: '10px', fontWeight: 800, color: 'var(--color-accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              FORENSIC INVESTIGATOR DELTA SUMMARY
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-primary)', lineHeight: 1.5 }}>
              Candidate <strong style={{ color: 'var(--color-accent-blue)' }}>{candA.vessel_name}</strong> (Rank #{candA.vessel_rank}, score {candA.best_evidence_score.toFixed(4)}) is the best-supported hypothesis because it exhibits higher physical compatibility than candidate <strong style={{ color: 'var(--color-text-primary)' }}>{candB.vessel_name}</strong> (Rank #{candB.vessel_rank}, score {candB.best_evidence_score.toFixed(4)}), specifically across source distance ({formatDistance(metricsA?.vessel_source_distance_m)} vs {formatDistance(metricsB?.vessel_source_distance_m)}) and drift centroid error ({metricsA?.centroid_error_m ? `${metricsA.centroid_error_m.toFixed(1)} m` : '—'} vs {metricsB?.centroid_error_m ? `${metricsB.centroid_error_m.toFixed(1)} m` : '—'}).
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--color-border-subtle)',
            backgroundColor: 'rgba(17, 24, 39, 0.95)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
            Scores quantify physical and spatiotemporal compatibility under the calibrated Lagrangian model.
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '6px 14px',
              backgroundColor: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--color-text-primary)',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  );
};
