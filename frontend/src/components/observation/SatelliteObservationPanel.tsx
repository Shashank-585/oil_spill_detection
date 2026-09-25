import React from 'react';
import { useCaseSatelliteObservationsQuery } from '../../api/casesApi';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import { StatusBadge } from '../common/StatusBadge';
import { DomainTooltip } from '../common/DomainTooltip';
import {
  Radio,
  Clock,
  Info,
  Calendar,
  Compass,
  Activity,
  Sun,
} from 'lucide-react';

interface SatelliteObservationPanelProps {
  caseId?: string;
  compact?: boolean;
}

export const SatelliteObservationPanel: React.FC<SatelliteObservationPanelProps> = ({
  caseId,
  compact = false,
}) => {
  const { activeCaseId } = useActiveCase();
  const targetCaseId = caseId || activeCaseId;

  const { data: satPkg, isLoading, isError } = useCaseSatelliteObservationsQuery(targetCaseId);

  if (isLoading) {
    return (
      <div style={{ padding: '20px', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div className="animate-spin" style={{ width: '12px', height: '12px', border: '2px solid var(--color-accent-blue)', borderTopColor: 'transparent', borderRadius: '50%' }} />
        Synchronizing satellite observation metadata & acquisition timeline...
      </div>
    );
  }

  if (isError || !satPkg) {
    return (
      <div style={{ padding: '14px', backgroundColor: 'rgba(248, 81, 73, 0.1)', border: '1px solid var(--color-accent-crimson)', borderRadius: 'var(--radius-xs)', fontSize: 'var(--text-xs)', color: 'var(--color-accent-crimson)' }}>
        Unable to load satellite observation package for case {targetCaseId}.
      </div>
    );
  }

  const { sentinel1, sentinel2, timeline, revisit_context } = satPkg;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: compact ? '12px' : '18px' }}>
      {/* 1. Sentinel-1 Operational SAR Panel */}
      <div
        style={{
          backgroundColor: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: compact ? '12px' : '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Radio size={16} color="var(--color-accent-blue)" />
            <DomainTooltip term="SAR" inline>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-text-primary)' }}>
                SENTINEL-1 OPERATIONAL SAR METADATA
              </span>
            </DomainTooltip>
            <span style={{ fontSize: '10px', backgroundColor: 'rgba(56, 139, 253, 0.15)', color: 'var(--color-accent-blue)', padding: '2px 6px', borderRadius: 'var(--radius-2xs)', fontWeight: 700 }}>
              OPERATIONAL DETECTION
            </span>
          </div>

          <StatusBadge
            label={sentinel1.processing_status.replace(/_/g, ' ')}
            tone={sentinel1.processing_status === 'CALIBRATED_AND_DETECTED' ? 'emerald' : 'blue'}
            size="sm"
          />
        </div>

        {/* Operational Channel Callout Box */}
        <div
          style={{
            padding: '10px 12px',
            backgroundColor: 'rgba(46, 160, 67, 0.08)',
            border: '1px solid rgba(46, 160, 67, 0.3)',
            borderRadius: 'var(--radius-xs)',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Activity size={14} color="#3fb950" />
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: '#3fb950', letterSpacing: '0.04em' }}>
              OPERATIONAL DETECTOR CHANNEL: {sentinel1.polarization_used} (CO-POLARIZED)
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '11px', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
            {sentinel1.polarization_explanation}
          </p>
        </div>

        {/* Sentinel-1 Metadata Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px' }}>
          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Platform & Sensor</div>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {sentinel1.platform} · {sentinel1.sensor}
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Acquisition Timestamp (T_obs)</div>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>
              <MonospaceValue value={sentinel1.acquisition_time_utc.replace('T', ' ')} />
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Mode & Product Type</div>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {sentinel1.mode} · {sentinel1.product_type}
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Orbit Direction & Track</div>
            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Compass size={12} color="var(--color-accent-blue)" />
              <span>{sentinel1.orbit_direction || 'DESCENDING'} {sentinel1.relative_orbit ? `(Rel. Orbit ${sentinel1.relative_orbit})` : ''}</span>
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Spatial Resolution</div>
            <div style={{ fontSize: 'var(--text-xs)', fontFamily: 'monospace', color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {sentinel1.spatial_resolution || '10.0 m × 10.0 m pixel spacing'}
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Scene Dimensions & Footprint</div>
            <div style={{ fontSize: 'var(--text-xs)', fontFamily: 'monospace', color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {sentinel1.scene_dimensions || 'Full SAR Scene raster'}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Sentinel-2 Supporting Optical Panel */}
      <div
        style={{
          backgroundColor: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: compact ? '12px' : '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sun size={16} color="var(--color-accent-amber)" />
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-text-primary)' }}>
              SENTINEL-2 OPTICAL OBSERVATION
            </span>
          </div>

          <StatusBadge
            label={sentinel2?.available ? 'SUPPORTING OPTICAL AVAILABLE' : 'NOT ACTIVE FOR CASE'}
            tone={sentinel2?.available ? 'amber' : 'neutral'}
            size="sm"
          />
        </div>

        {sentinel2?.available ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Non-operational disclaimer notice */}
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'rgba(210, 153, 34, 0.08)',
                border: '1px solid rgba(210, 153, 34, 0.3)',
                borderRadius: 'var(--radius-xs)',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                fontSize: '11px',
                color: 'var(--color-accent-amber)',
              }}
            >
              <Info size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Role: Supporting Optical Observation</strong>
                <p style={{ margin: '2px 0 0 0', color: 'var(--color-text-secondary)', fontSize: '11px' }}>
                  {sentinel2.pipeline_usage_disclaimer}
                </p>
              </div>
            </div>

            {/* Optical Details Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Platform & Instrument</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                  {sentinel2.platform} · {sentinel2.sensor}
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Acquisition Timestamp</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-accent-amber)', marginTop: '2px' }}>
                  <MonospaceValue value={sentinel2.acquisition_time_utc ? sentinel2.acquisition_time_utc.replace('T', ' ') : 'N/A'} />
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Cloud Cover</div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: '#3fb950', marginTop: '2px' }}>
                  {sentinel2.cloud_cover_text || `${(sentinel2.cloud_cover_percentage || 0).toFixed(2)}%`}
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
                <div style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>Available Bands & Product</div>
                <div style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                  {sentinel2.available_bands.join(', ')}
                </div>
              </div>
            </div>

            {sentinel2.details && (
              <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontStyle: 'italic', padding: '0 4px' }}>
                Note: {sentinel2.details}
              </div>
            )}
          </div>
        ) : (
          <div
            style={{
              padding: '10px 12px',
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '11px',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.5,
            }}
          >
            <p style={{ margin: '0 0 4px 0', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              No supporting Sentinel-2 optical data active for this case.
            </p>
            <span>
              {sentinel2?.pipeline_usage_disclaimer ||
                'The operational detection and attribution pipeline relies exclusively on calibrated Sentinel-1 C-SAR radar backscatter.'}
            </span>
          </div>
        )}
      </div>

      {/* 3. Observation Timeline */}
      <div
        style={{
          backgroundColor: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: compact ? '12px' : '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calendar size={16} color="var(--color-accent-cyan)" />
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-text-primary)' }}>
            OBSERVATION & INCIDENT TIMELINE
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', position: 'relative', paddingLeft: '8px' }}>
          {timeline.events.map((evt, idx) => {
            const isT0 = evt.event_type === 'INCIDENT_REFERENCE';
            const isSar = evt.event_type === 'OPERATIONAL_SAR';
            const isOptical = evt.event_type === 'SUPPORTING_OPTICAL';

            const dotColor = isT0 ? 'var(--color-accent-crimson)' : isSar ? 'var(--color-accent-blue)' : isOptical ? 'var(--color-accent-amber)' : 'var(--color-text-muted)';

            return (
              <div
                key={evt.event_id || idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  backgroundColor: 'var(--color-bg-base)',
                  border: isSar ? '1px solid rgba(56, 139, 253, 0.4)' : '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '10px 12px',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '60px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      fontWeight: 800,
                      color: evt.relative_to_incident_hours === 0 ? 'var(--color-accent-crimson)' : evt.relative_to_incident_hours > 0 ? 'var(--color-accent-cyan)' : 'var(--color-text-muted)',
                    }}
                  >
                    {evt.relative_to_incident_hours === 0 ? 'T₀' : evt.relative_to_incident_hours > 0 ? `+${evt.relative_to_incident_hours}h` : `${evt.relative_to_incident_hours}h`}
                  </span>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: dotColor, marginTop: '4px' }} />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '4px' }}>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      {evt.label}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', fontFamily: 'monospace' }}>
                      <MonospaceValue value={evt.timestamp_utc ? evt.timestamp_utc.replace('T', ' ') : 'N/A'} />
                    </span>
                  </div>

                  <p style={{ margin: 0, fontSize: '11px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                    {evt.description}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', fontSize: '10px', color: 'var(--color-text-muted)' }}>
                    <span>Platform: <strong style={{ color: 'var(--color-text-secondary)' }}>{evt.platform || 'N/A'}</strong></span>
                    <span>·</span>
                    <span
                      style={{
                        padding: '1px 5px',
                        borderRadius: '2px',
                        backgroundColor: evt.observation_nature === 'ACTUAL_OBSERVATION' ? 'rgba(46, 160, 67, 0.15)' : 'rgba(110, 118, 129, 0.15)',
                        color: evt.observation_nature === 'ACTUAL_OBSERVATION' ? '#3fb950' : 'var(--color-text-secondary)',
                        fontSize: '9px',
                        fontWeight: 700,
                      }}
                    >
                      {evt.observation_nature.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Revisit / Acquisition Context */}
      <div
        style={{
          padding: '12px 14px',
          backgroundColor: 'rgba(56, 139, 253, 0.05)',
          border: '1px solid rgba(56, 139, 253, 0.25)',
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Clock size={14} color="var(--color-accent-blue)" />
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 800, color: 'var(--color-accent-blue)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            REVISIT / ACQUISITION CONTEXT
          </span>
        </div>

        <div
          style={{
            padding: '8px 10px',
            backgroundColor: 'rgba(10, 13, 19, 0.6)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-xs)',
            fontSize: '11px',
            color: 'var(--color-text-secondary)',
            lineHeight: 1.45,
          }}
        >
          <strong style={{ color: 'var(--color-accent-cyan)' }}>Operational Distinction: </strong>
          {revisit_context.revisit_distinction_notice}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : '1fr 1fr', gap: '8px', fontSize: '11px' }}>
          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '6px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Nominal Repeat Cycle: </span>
            <strong style={{ color: 'var(--color-text-primary)' }}>{revisit_context.constellation_nominal_repeat_days} days (12d exact repeat, 6d constellation)</strong>
          </div>
          <div style={{ backgroundColor: 'var(--color-bg-base)', padding: '6px 10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--color-border-subtle)' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Cross-Track Revisit Opportunity: </span>
            <strong style={{ color: 'var(--color-text-primary)' }}>{revisit_context.sub_cycle_revisit_opportunity_hours}</strong>
          </div>
        </div>

        <p style={{ margin: 0, fontSize: '11px', color: 'var(--color-text-tertiary)', fontStyle: 'italic' }}>
          {revisit_context.case_revisit_audit}
        </p>
      </div>
    </div>
  );
};
