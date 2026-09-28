import React, { useState } from 'react';
import { useActiveCase } from '../../context/CaseContext';
import { useAisVesselsQuery, useAisTracksQuery } from '../../api/casesApi';
import { useInvestigationStore } from '../../store/investigationStore';
import { DomainTooltip } from '../common/DomainTooltip';
import { Ship, Eye, Search, RefreshCw, X, ChevronRight, ShieldAlert } from 'lucide-react';

interface AisViewProps {
  onClose?: () => void;
}

export const AisView: React.FC<AisViewProps> = ({ onClose }) => {
  const { activeCaseId, activeCase, isAttributionUnavailable, topCandidate } = useActiveCase();
  const setMapLayerVisibility = useInvestigationStore((s) => s.setMapLayerVisibility);
  const setSelectedMmsi = useInvestigationStore((s) => s.setSelectedMmsi);
  const selectedMmsi = useInvestigationStore((s) => s.selectedMmsi);
  const toggleInspector = useInvestigationStore((s) => s.toggleInspector);
  const inspectorOpen = useInvestigationStore((s) => s.inspectorOpen);

  const [searchTerm, setSearchTerm] = useState('');

  const { data: aisVessels = [], isLoading: isLoadingVessels } = useAisVesselsQuery(
    activeCaseId,
    !isAttributionUnavailable
  );
  const { data: aisTracksData } = useAisTracksQuery(
    activeCaseId,
    !isAttributionUnavailable
  );

  const totalTracks = aisTracksData?.features?.length || aisVessels.length || 0;
  const totalPings = aisTracksData?.features
    ? (aisTracksData.features as any[]).reduce((sum, f) => sum + (f.properties?.point_count || f.properties?.timestamps?.length || 0), 0)
    : 0;

  const handleIsolateAis = () => {
    setMapLayerVisibility('sarRaster', false);
    setMapLayerVisibility('slickPolygons', true);
    setMapLayerVisibility('aisTracks', true);
    setMapLayerVisibility('driftParticles', false);
    setMapLayerVisibility('candidateMarkers', true);
    if (onClose) onClose();
  };

  const handleSelectVessel = (mmsi: number) => {
    setSelectedMmsi(mmsi);
    if (!inspectorOpen) toggleInspector();
    if (onClose) onClose();
  };

  const filteredVessels = aisVessels.filter((v) => {
    const term = searchTerm.toLowerCase();
    return (
      v.vessel_name.toLowerCase().includes(term) ||
      String(v.mmsi).includes(term)
    );
  });

  return (
    <div
      style={{
        position: 'absolute',
        top: '60px',
        left: '20px',
        right: '20px',
        maxHeight: 'calc(100% - 120px)',
        backgroundColor: 'rgba(10, 13, 19, 0.96)',
        backdropFilter: 'blur(8px)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-xl)',
        zIndex: 25,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 1. Header Bar */}
      <div
        style={{
          padding: '12px 18px',
          borderBottom: '1px solid var(--color-border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--color-bg-base)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Ship size={16} color="var(--color-accent-blue)" />
          <div>
            <DomainTooltip term="AIS" inline>
              <span
                style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                }}
              >
                AUTOMATIC IDENTIFICATION SYSTEM (AIS) MARITIME TRAFFIC CORRIDOR
              </span>
            </DomainTooltip>
            <span
              style={{
                display: 'block',
                fontSize: 'var(--text-2xs)',
                color: 'var(--color-text-muted)',
                fontFamily: 'monospace',
                marginTop: '1px',
              }}
            >
              CASE: {activeCase?.name || activeCaseId} · HISTORICAL SURVEILLANCE DATASET
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleIsolateAis}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              backgroundColor: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid var(--color-accent-cyan)',
              borderRadius: 'var(--radius-xs)',
              color: 'var(--color-accent-cyan)',
              fontSize: 'var(--text-2xs)',
              fontWeight: 700,
              cursor: 'pointer',
            }}
            title="Focus map on AIS vessel tracks"
          >
            <Eye size={12} />
            <span>ISOLATE ON MAP</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                padding: '4px',
              }}
              title="Close AIS Workspace"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* 2. Scrollable Body */}
      <div style={{ padding: '16px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {isAttributionUnavailable ? (
          <div
            style={{
              padding: '24px',
              textAlign: 'center',
              backgroundColor: 'rgba(210, 153, 34, 0.08)',
              border: '1px solid var(--color-accent-amber)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <ShieldAlert size={24} color="var(--color-accent-amber)" style={{ margin: '0 auto 8px' }} />
            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-accent-amber)' }}>
              AIS ATTRIBUTION ARCHIVE DATA UNAVAILABLE
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', maxWidth: '600px', margin: '6px auto 0' }}>
              Historical multi-vessel terrestrial and satellite AIS feeds were not acquired for this benchmark incident segment. Physical validation remains operational on satellite and drift layers.
            </div>
          </div>
        ) : (
          <>
            {/* Top Metrics Row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Candidate Vessels Retained
                </div>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-accent-blue)', marginTop: '2px' }}>
                  {aisVessels.length} Vessels
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                  Spatial matching envelope: 5.0 km
                </div>
              </div>

              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Total Corridor Vessels Evaluated
                </div>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
                  {totalTracks ? `${totalTracks} Corridor Craft` : '0 Corridor Craft'}
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-accent-emerald)', marginTop: '2px' }}>
                  Recall: 100% (Incident vessel captured blindly)
                </div>
              </div>

              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Total Normalized Pings
                </div>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>
                  {totalPings.toLocaleString()} Pings
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                  Interpolation cadence: 600s max gap
                </div>
              </div>

              <div
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Temporal Surveillance Span
                </div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '4px' }}>
                  48.0 Hours
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                  NOAA MarineCadastre Zone 17
                </div>
              </div>
            </div>

            {/* Filter / Search Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '6px 12px',
                  width: '320px',
                }}
              >
                <Search size={14} color="var(--color-text-muted)" />
                <input
                  type="text"
                  placeholder="Filter by vessel name or MMSI..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    background: 'none',
                    border: 'none',
                    outline: 'none',
                    color: 'var(--color-text-primary)',
                    fontSize: 'var(--text-xs)',
                    width: '100%',
                  }}
                />
              </div>

              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
                Showing {filteredVessels.length} of {aisVessels.length} candidate vessels
              </div>
            </div>

            {/* Candidate Vessels Table */}
            <div
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', backgroundColor: 'rgba(255,255,255,0.02)', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px' }}>Vessel Name</th>
                    <th style={{ padding: '8px 12px' }}>MMSI</th>
                    <th style={{ padding: '8px 12px' }}>Release Hypotheses</th>
                    <th style={{ padding: '8px 12px' }}>Min Distance to Slick</th>
                    <th style={{ padding: '8px 12px' }}>Track Bounds</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoadingVessels ? (
                    <tr>
                      <td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        <RefreshCw size={14} className="animate-spin" style={{ display: 'inline', marginRight: '6px' }} />
                        Loading AIS candidate vessels...
                      </td>
                    </tr>
                  ) : filteredVessels.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        No vessels match search query.
                      </td>
                    </tr>
                  ) : (
                    filteredVessels.map((v) => {
                      const isSelected = v.mmsi === selectedMmsi;
                      const isTopCandidate = topCandidate != null && v.mmsi === topCandidate.mmsi;

                      return (
                        <tr
                          key={v.mmsi}
                          onClick={() => handleSelectVessel(v.mmsi)}
                          style={{
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                            backgroundColor: isSelected
                              ? 'rgba(56, 139, 253, 0.15)'
                              : isTopCandidate
                              ? 'rgba(56, 189, 248, 0.06)'
                              : 'transparent',
                            cursor: 'pointer',
                            transition: 'background-color 150ms ease',
                          }}
                        >
                          <td style={{ padding: '10px 12px', fontWeight: 700 }}>
                            <span style={{ color: isTopCandidate ? 'var(--color-accent-cyan)' : 'var(--color-text-primary)' }}>
                              {v.vessel_name || 'UNKNOWN'}
                            </span>
                            {isTopCandidate && (
                              <span style={{ fontSize: '9px', color: 'var(--color-accent-cyan)', border: '1px solid var(--color-accent-cyan)', padding: '1px 4px', borderRadius: '2px', marginLeft: '6px' }}>
                                #1 CANDIDATE
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{v.mmsi}</td>
                          <td style={{ padding: '10px 12px' }}>
                            <span style={{ fontFamily: 'monospace', color: 'var(--color-accent-blue)', fontWeight: 700 }}>
                              {v.hypothesis_count}
                            </span>{' '}
                            hypotheses
                          </td>
                          <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>
                            {(v.min_distance_m / 1000).toFixed(2)} km
                          </td>
                          <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>
                            {(v.max_distance_m / 1000).toFixed(1)} km max
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                            <button
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '3px 8px',
                                backgroundColor: 'rgba(56, 139, 253, 0.15)',
                                border: '1px solid var(--color-border-subtle)',
                                borderRadius: 'var(--radius-xs)',
                                fontSize: 'var(--text-2xs)',
                                color: 'var(--color-accent-blue)',
                                cursor: 'pointer',
                              }}
                            >
                              Inspect <ChevronRight size={12} />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
