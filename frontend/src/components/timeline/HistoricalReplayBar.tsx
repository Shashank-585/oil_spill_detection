import React, { useMemo } from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import {
  Play,
  Pause,
  RotateCcw,
  SkipBack,
  SkipForward,
  Film,
  Crosshair,
  Radio,
  Ship,
  Wind,
  Layers,
  MapPin,
  AlertTriangle,
  Info,
  X,
} from 'lucide-react';

interface Milestone {
  id: string;
  label: string;
  shortLabel: string;
  epoch: number;
  timeStr: string;
  description: string;
}

export const HistoricalReplayBar: React.FC = () => {
  const {
    currentTimeUtc,
    setCurrentTimeUtc,
    isReplayMode,
    setReplayMode,
    isPlaying,
    togglePlayPause,
    playbackSpeed,
    setPlaybackSpeed,
    mapLayers,
    setMapLayerVisibility,
  } = useInvestigationStore();

  const { activeCase, activeCaseId } = useActiveCase();

  // Dynamic Case Timestamps
  const t0Str = activeCase?.event?.estimated_start_utc || activeCase?.event?.search_start_utc || '2019-09-08T05:46:00Z';
  const sarStr = activeCase?.observation?.timestamp_utc || '2019-09-08T11:25:31Z';

  const t0Epoch = useMemo(() => new Date(t0Str).getTime(), [t0Str]);
  const sarEpoch = useMemo(() => new Date(sarStr).getTime(), [sarStr]);

  const startEpoch = useMemo(() => {
    return activeCase?.event?.search_start_utc
      ? new Date(activeCase.event.search_start_utc).getTime()
      : t0Epoch - 18 * 3600 * 1000;
  }, [activeCase, t0Epoch]);

  const endEpoch = useMemo(() => {
    return activeCase?.event?.search_end_utc
      ? new Date(activeCase.event.search_end_utc).getTime()
      : Math.max(sarEpoch + 12 * 3600 * 1000, t0Epoch + 24 * 3600 * 1000);
  }, [activeCase, sarEpoch, t0Epoch]);

  // Current Epoch and Relative Offset
  const currentEpoch = useMemo(() => new Date(currentTimeUtc).getTime(), [currentTimeUtc]);
  const diffFromT0Ms = currentEpoch - t0Epoch;

  const relativeOffsetStr = useMemo(() => {
    const isNegative = diffFromT0Ms < 0;
    const absMs = Math.abs(diffFromT0Ms);
    const hrs = Math.floor(absMs / (3600 * 1000));
    const mins = Math.floor((absMs % (3600 * 1000)) / (60 * 1000));
    const secs = Math.floor((absMs % (60 * 1000)) / 1000);
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `T ${isNegative ? '-' : '+'} ${pad(hrs)}h ${pad(mins)}m ${pad(secs)}s`;
  }, [diffFromT0Ms]);

  // Define Chronological Milestones
  const milestones: Milestone[] = useMemo(() => {
    // Pre-event midpoint: midway between start and T0
    const preEventEpoch = startEpoch + (t0Epoch - startEpoch) * 0.65;
    // Post-event midpoint: midway between T0 and SAR
    const postEventEpoch = t0Epoch + (sarEpoch - t0Epoch) * 0.45;

    return [
      {
        id: 'start',
        label: 'Search Window Start',
        shortLabel: '1. Start',
        epoch: startEpoch,
        timeStr: new Date(startEpoch).toISOString(),
        description: 'Initial surveillance window boundary',
      },
      {
        id: 'pre-event',
        label: 'Pre-Event Vessel Traffic',
        shortLabel: '2. Pre-Event Traffic',
        epoch: preEventEpoch,
        timeStr: new Date(preEventEpoch).toISOString(),
        description: 'Vessels transiting channel before incident',
      },
      {
        id: 't0',
        label: `Incident Event T₀ (${activeCase?.name || 'T₀'})`,
        shortLabel: '3. Incident T₀',
        epoch: t0Epoch,
        timeStr: t0Str,
        description: activeCase?.event?.incident_type ? `Reported ${activeCase.event.incident_type}` : 'Incident reference time',
      },
      {
        id: 'post-event',
        label: 'Post-Event Traffic & Dispersion',
        shortLabel: '4. Post-Event Response',
        epoch: postEventEpoch,
        timeStr: new Date(postEventEpoch).toISOString(),
        description: 'Subsequent vessel movement & slick dispersion',
      },
      {
        id: 'sar',
        label: 'Satellite SAR Observation',
        shortLabel: '5. Satellite Pass (T_obs)',
        epoch: sarEpoch,
        timeStr: sarStr,
        description: activeCase?.observation?.platform ? `${activeCase.observation.platform} acquisition` : 'Satellite radar capture',
      },
    ];
  }, [startEpoch, t0Epoch, sarEpoch, t0Str, sarStr, activeCase]);

  // Determine Active Phase based on currentEpoch
  const activePhase = useMemo(() => {
    if (currentEpoch < t0Epoch - 30 * 60 * 1000) {
      return { number: 1, title: 'PRE-EVENT VESSEL TRAFFIC', tone: 'cyan' };
    } else if (currentEpoch >= t0Epoch - 30 * 60 * 1000 && currentEpoch <= t0Epoch + 45 * 60 * 1000) {
      return { number: 2, title: 'INCIDENT EVENT T₀ (ORIGIN)', tone: 'crimson' };
    } else if (currentEpoch > t0Epoch + 45 * 60 * 1000 && currentEpoch < sarEpoch) {
      return { number: 3, title: 'POST-EVENT MOVEMENT & RESPONSE', tone: 'amber' };
    } else {
      return { number: 4, title: 'SATELLITE SAR OBSERVATION (T_OBS)', tone: 'emerald' };
    }
  }, [currentEpoch, t0Epoch, sarEpoch]);

  const handleStepMilestone = (direction: 'prev' | 'next') => {
    if (direction === 'prev') {
      const past = milestones.filter((m) => m.epoch < currentEpoch - 60000);
      if (past.length > 0) {
        const target = past[past.length - 1];
        setCurrentTimeUtc(target.timeStr);
      } else {
        setCurrentTimeUtc(new Date(startEpoch).toISOString());
      }
    } else {
      const future = milestones.filter((m) => m.epoch > currentEpoch + 60000);
      if (future.length > 0) {
        const target = future[0];
        setCurrentTimeUtc(target.timeStr);
      } else {
        setCurrentTimeUtc(new Date(endEpoch).toISOString());
      }
    }
  };

  if (!isReplayMode) return null;

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 'calc(var(--timeline-height) + 12px)',
        left: '20px',
        right: '20px',
        backgroundColor: 'rgba(10, 14, 22, 0.96)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: 'var(--radius-md)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.65)',
        zIndex: 22,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 1. Header Toolbar */}
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--color-border-subtle)',
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        {/* Left: Replay Mode Badge & Active Phase */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              borderRadius: 'var(--radius-xs)',
              padding: '3px 8px',
              color: 'var(--color-accent-cyan)',
              fontSize: '11px',
              fontWeight: 800,
              letterSpacing: '0.04em',
            }}
          >
            <Film size={12} />
            <span>HISTORICAL REPLAY</span>
          </div>

          <div
            style={{
              padding: '3px 10px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor:
                activePhase.tone === 'crimson'
                  ? 'rgba(248, 81, 73, 0.15)'
                  : activePhase.tone === 'amber'
                  ? 'rgba(210, 153, 34, 0.15)'
                  : activePhase.tone === 'emerald'
                  ? 'rgba(34, 197, 94, 0.15)'
                  : 'rgba(56, 189, 248, 0.12)',
              border: `1px solid ${
                activePhase.tone === 'crimson'
                  ? 'rgba(248, 81, 73, 0.4)'
                  : activePhase.tone === 'amber'
                  ? 'rgba(210, 153, 34, 0.4)'
                  : activePhase.tone === 'emerald'
                  ? 'rgba(34, 197, 94, 0.4)'
                  : 'rgba(56, 189, 248, 0.3)'
              }`,
              color:
                activePhase.tone === 'crimson'
                  ? 'var(--color-accent-red)'
                  : activePhase.tone === 'amber'
                  ? 'var(--color-accent-amber)'
                  : activePhase.tone === 'emerald'
                  ? 'var(--color-accent-emerald)'
                  : 'var(--color-accent-cyan)',
              fontSize: '11px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ opacity: 0.8 }}>PHASE {activePhase.number}:</span>
            <span>{activePhase.title}</span>
          </div>
        </div>

        {/* Center: Live Relative Offset & Current Timestamp */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--text-xs)',
              fontWeight: 700,
              color: diffFromT0Ms < 0 ? 'var(--color-accent-cyan)' : 'var(--color-accent-amber)',
              backgroundColor: 'rgba(0, 0, 0, 0.4)',
              padding: '3px 8px',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid var(--color-border-subtle)',
            }}
          >
            {relativeOffsetStr}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--text-xs)' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>EPOCH:</span>
            <MonospaceValue value={new Date(currentEpoch).toISOString().replace('T', ' ').substring(0, 19) + ' UTC'} />
          </div>
        </div>

        {/* Right: Exit Replay Mode */}
        <button
          onClick={() => setReplayMode(false)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '11px',
          }}
          title="Exit Historical Replay Mode"
        >
          <X size={15} />
          <span>Exit Replay</span>
        </button>
      </div>

      {/* 2. Primary Playback & Speed Deck */}
      <div
        style={{
          padding: '10px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'rgba(15, 20, 30, 0.98)',
          borderBottom: '1px solid var(--color-border-subtle)',
        }}
      >
        {/* Playback Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Reset to Start */}
          <button
            onClick={() => setCurrentTimeUtc(new Date(startEpoch).toISOString())}
            style={{
              padding: '5px 8px',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Reset to Timeline Start"
          >
            <RotateCcw size={13} />
          </button>

          {/* Previous Milestone */}
          <button
            onClick={() => handleStepMilestone('prev')}
            style={{
              padding: '5px 8px',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Step Back to Previous Milestone"
          >
            <SkipBack size={13} />
          </button>

          {/* PLAY / PAUSE Main Trigger */}
          <button
            onClick={togglePlayPause}
            style={{
              padding: '6px 16px',
              backgroundColor: isPlaying ? 'rgba(248, 81, 73, 0.2)' : 'rgba(56, 189, 248, 0.2)',
              border: `1px solid ${isPlaying ? 'var(--color-accent-red)' : 'var(--color-accent-cyan)'}`,
              borderRadius: 'var(--radius-sm)',
              color: isPlaying ? 'var(--color-accent-red)' : 'var(--color-accent-cyan)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: 'var(--text-xs)',
              fontWeight: 800,
              boxShadow: isPlaying ? '0 0 10px rgba(248, 81, 73, 0.3)' : '0 0 10px rgba(56, 189, 248, 0.3)',
            }}
            title="Play / Pause Timeline (Spacebar)"
          >
            {isPlaying ? <Pause size={14} /> : <Play size={14} fill="currentColor" />}
            <span>{isPlaying ? 'PAUSE' : 'PLAY REPLAY'}</span>
          </button>

          {/* Next Milestone */}
          <button
            onClick={() => handleStepMilestone('next')}
            style={{
              padding: '5px 8px',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Step Forward to Next Milestone"
          >
            <SkipForward size={13} />
          </button>

          {/* Speed Selector Pills */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '3px', marginLeft: '12px' }}>
            <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginRight: '4px', textTransform: 'uppercase' }}>
              SPEED:
            </span>
            {[0.5, 1, 2, 5, 10].map((spd) => {
              const active = playbackSpeed === spd;
              return (
                <button
                  key={spd}
                  onClick={() => setPlaybackSpeed(spd)}
                  style={{
                    padding: '3px 7px',
                    fontSize: '10px',
                    fontWeight: active ? 800 : 500,
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: active ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255, 255, 255, 0.04)',
                    border: `1px solid ${active ? 'var(--color-accent-cyan)' : 'var(--color-border-subtle)'}`,
                    color: active ? 'var(--color-accent-cyan)' : 'var(--color-text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  {spd}x
                </button>
              );
            })}
          </div>
        </div>

        {/* Milestone Quick Jump Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {milestones.map((m) => {
            const isNear = Math.abs(currentEpoch - m.epoch) < 15 * 60 * 1000;
            return (
              <button
                key={m.id}
                onClick={() => setCurrentTimeUtc(m.timeStr)}
                style={{
                  padding: '4px 8px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: isNear ? 'rgba(56, 139, 253, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${isNear ? 'var(--color-accent-blue)' : 'var(--color-border-subtle)'}`,
                  color: isNear ? 'var(--color-accent-blue)' : 'var(--color-text-secondary)',
                  fontSize: '10px',
                  fontWeight: isNear ? 700 : 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
                title={`${m.label}: ${m.description}`}
              >
                {m.shortLabel}
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Layer Toggles Bar & Provenance Notices */}
      <div
        style={{
          padding: '8px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'rgba(10, 13, 19, 0.98)',
          fontSize: '11px',
        }}
      >
        {/* Layer Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
            REPLAY LAYERS:
          </span>

          {/* AIS */}
          <button
            onClick={() => setMapLayerVisibility('aisTracks', !mapLayers.aisTracks)}
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: mapLayers.aisTracks ? 'rgba(56, 139, 253, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${mapLayers.aisTracks ? 'rgba(56, 139, 253, 0.5)' : 'var(--color-border-subtle)'}`,
              color: mapLayers.aisTracks ? 'var(--color-accent-blue)' : 'var(--color-text-muted)',
              fontSize: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <Ship size={11} />
            <span>AIS Telemetry</span>
          </button>

          {/* Incident Point */}
          <button
            onClick={() => setMapLayerVisibility('incidentPoint', !mapLayers.incidentPoint)}
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: mapLayers.incidentPoint ? 'rgba(248, 81, 73, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${mapLayers.incidentPoint ? 'rgba(248, 81, 73, 0.5)' : 'var(--color-border-subtle)'}`,
              color: mapLayers.incidentPoint ? 'var(--color-accent-red)' : 'var(--color-text-muted)',
              fontSize: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <Crosshair size={11} />
            <span>Incident Point (T₀)</span>
          </button>

          {/* Detected Slick */}
          <button
            onClick={() => setMapLayerVisibility('slickPolygons', !mapLayers.slickPolygons)}
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: mapLayers.slickPolygons ? 'rgba(210, 153, 34, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${mapLayers.slickPolygons ? 'rgba(210, 153, 34, 0.5)' : 'var(--color-border-subtle)'}`,
              color: mapLayers.slickPolygons ? 'var(--color-accent-amber)' : 'var(--color-text-muted)',
              fontSize: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <Layers size={11} />
            <span>Observed Slick</span>
          </button>

          {/* Source Hypotheses */}
          <button
            onClick={() => setMapLayerVisibility('candidateMarkers', !mapLayers.candidateMarkers)}
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: mapLayers.candidateMarkers ? 'rgba(163, 113, 247, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${mapLayers.candidateMarkers ? 'rgba(163, 113, 247, 0.5)' : 'var(--color-border-subtle)'}`,
              color: mapLayers.candidateMarkers ? 'var(--color-accent-purple)' : 'var(--color-text-muted)',
              fontSize: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <MapPin size={11} />
            <span>Hypotheses</span>
          </button>

          {/* Drift Trajectories */}
          <button
            onClick={() => setMapLayerVisibility('driftParticles', !mapLayers.driftParticles)}
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: mapLayers.driftParticles ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${mapLayers.driftParticles ? 'rgba(56, 189, 248, 0.5)' : 'var(--color-border-subtle)'}`,
              color: mapLayers.driftParticles ? 'var(--color-accent-cyan)' : 'var(--color-text-muted)',
              fontSize: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <Wind size={11} />
            <span>Lagrangian Drift</span>
          </button>

          {/* Satellite Footprint */}
          <button
            onClick={() => setMapLayerVisibility('satelliteFootprint', !mapLayers.satelliteFootprint)}
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: mapLayers.satelliteFootprint ? 'rgba(34, 197, 94, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${mapLayers.satelliteFootprint ? 'rgba(34, 197, 94, 0.5)' : 'var(--color-border-subtle)'}`,
              color: mapLayers.satelliteFootprint ? 'var(--color-accent-emerald)' : 'var(--color-text-muted)',
              fontSize: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <Radio size={11} />
            <span>SAR Footprint</span>
          </button>
        </div>

        {/* Provenance & Limitation Warnings */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', color: 'var(--color-text-muted)' }}>
          {activeCaseId === 'case_001' ? (
            <span style={{ color: 'var(--color-accent-cyan)' }}>
              Negative-Control Scenario (Pipeline Anchor T₀)
            </span>
          ) : activeCaseId === 'case_002' ? (
            <span style={{ color: 'var(--color-accent-amber)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertTriangle size={11} />
              AIS Telemetry Unavailable (Physical Benchmark)
            </span>
          ) : (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Info size={11} color="var(--color-accent-cyan)" />
              Reconstructed AIS via linear interpolation · Backward drift from Lagrangian metocean model
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
