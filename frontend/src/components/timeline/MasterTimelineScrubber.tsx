import React from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import { RotateCcw, Calendar, Crosshair, Radio, Navigation, Clock } from 'lucide-react';

export const MasterTimelineScrubber: React.FC = () => {
  const { currentTimeUtc, setCurrentTimeUtc } = useInvestigationStore();
  const { activeCase } = useActiveCase();

  // Dynamic T0 and SAR timestamps based on active case
  const t0Str = activeCase?.event?.estimated_start_utc || activeCase?.event?.search_start_utc || '2019-09-08T05:46:00Z';
  const sarStr = activeCase?.observation?.timestamp_utc || '2019-09-08T11:25:31Z';

  const t0Epoch = new Date(t0Str).getTime();
  const sarEpoch = new Date(sarStr).getTime();

  // Dynamic analytical window
  const startEpoch = activeCase?.event?.search_start_utc
    ? new Date(activeCase.event.search_start_utc).getTime()
    : t0Epoch - 18 * 3600 * 1000;
  const endEpoch = activeCase?.event?.search_end_utc
    ? new Date(activeCase.event.search_end_utc).getTime()
    : Math.max(sarEpoch + 12 * 3600 * 1000, t0Epoch + 24 * 3600 * 1000);
  const totalDuration = Math.max(endEpoch - startEpoch, 3600 * 1000);

  // Sync timeline to new case T0 on case change
  React.useEffect(() => {
    if (t0Str) {
      setCurrentTimeUtc(t0Str);
    }
  }, [t0Str, setCurrentTimeUtc]);

  const currentEpoch = new Date(currentTimeUtc).getTime();
  const currentPct = Math.min(Math.max(((currentEpoch - startEpoch) / totalDuration) * 100, 0), 100);

  // Key Physical Milestones
  const t0Pct = Math.min(Math.max(((t0Epoch - startEpoch) / totalDuration) * 100, 0), 100);
  const sarPct = Math.min(Math.max(((sarEpoch - startEpoch) / totalDuration) * 100, 0), 100);

  const aisStartPct = Math.max(t0Pct - 5, 0);
  const aisWidthPct = Math.min(Math.max(sarPct - aisStartPct + 5, 10), 100 - aisStartPct);

  const handleScrubberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    const newEpoch = startEpoch + (val / 100) * totalDuration;
    setCurrentTimeUtc(new Date(newEpoch).toISOString());
  };

  const t0Label = t0Str.includes('T') ? t0Str.split('T')[1].substring(0, 5) : 'T₀';
  const sarLabel = sarStr.includes('T') ? sarStr.split('T')[1].substring(0, 5) : 'T_obs';

  return (
    <div
      style={{
        height: 'var(--timeline-height)',
        backgroundColor: 'var(--color-bg-surface)',
        borderTop: '1px solid var(--color-border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '6px 16px',
        zIndex: 15,
        flexShrink: 0,
      }}
    >
      {/* 1. Header Row: Scientific Timeline Title & Active Epoch */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calendar size={13} color="var(--color-accent-blue)" />
          <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            COORDINATED 4D INVESTIGATION TIMELINE
          </span>
          <button
            onClick={() => setCurrentTimeUtc(t0Str)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 6px',
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: 'var(--text-2xs)',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              marginLeft: '8px',
            }}
            title="Snap to Incident Event T₀"
          >
            <RotateCcw size={10} />
            <span>SNAP TO T₀</span>
          </button>
        </div>

        {/* Current Coordinate Timestamp */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Clock size={12} color="var(--color-accent-amber)" />
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
            ACTIVE EPOCH:
          </span>
          <MonospaceValue value={currentTimeUtc} />
        </div>

        {/* Scientific Interval Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: 'var(--text-2xs)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-text-secondary)' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-accent-crimson)', borderRadius: '1px' }} />
            T₀ Event ({t0Label})
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-text-secondary)' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-accent-cyan)', borderRadius: '1px' }} />
            SAR Pass ({sarLabel})
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-text-secondary)' }}>
            <span style={{ width: '12px', height: '6px', backgroundColor: 'rgba(56, 139, 253, 0.35)', border: '1px solid var(--color-accent-blue)' }} />
            AIS Track Envelope
          </span>
        </div>
      </div>

      {/* 2. Multi-Track Scientific Scrubber Surface */}
      <div style={{ position: 'relative', height: '28px', display: 'flex', alignItems: 'center' }}>
        {/* Base Timeline Track Bar */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            height: '6px',
            backgroundColor: 'var(--color-bg-base)',
            borderRadius: 'var(--radius-xs)',
            border: '1px solid var(--color-border-subtle)',
          }}
        />

        {/* Shaded Interval: AIS Critical Trajectory Activity */}
        <div
          style={{
            position: 'absolute',
            left: `${aisStartPct}%`,
            width: `${aisWidthPct}%`,
            height: '10px',
            backgroundColor: 'rgba(56, 139, 253, 0.20)',
            border: '1px solid rgba(56, 139, 253, 0.40)',
            borderRadius: 'var(--radius-xs)',
            pointerEvents: 'none',
          }}
          title="AIS Encounter & Channel Transit Interval"
        />

        {/* Milestone Pin: Incident Event (T0) */}
        <div
          style={{
            position: 'absolute',
            left: `${t0Pct}%`,
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            transform: 'translateX(-50%)',
            pointerEvents: 'none',
          }}
          title="Incident Event (Capsizing) - 05:46 UTC"
        >
          <Crosshair size={12} color="var(--color-accent-crimson)" style={{ position: 'absolute', top: '-1px' }} />
          <div style={{ width: '1px', height: '100%', backgroundColor: 'var(--color-accent-crimson)', opacity: 0.85 }} />
        </div>

        {/* Milestone Pin: SAR Observation (T_obs) */}
        <div
          style={{
            position: 'absolute',
            left: `${sarPct}%`,
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            transform: 'translateX(-50%)',
            pointerEvents: 'none',
          }}
          title="Sentinel-1 Observation - 11:25 UTC"
        >
          <Radio size={12} color="var(--color-accent-cyan)" style={{ position: 'absolute', top: '-1px' }} />
          <div style={{ width: '1px', height: '100%', backgroundColor: 'var(--color-accent-cyan)', opacity: 0.85 }} />
        </div>

        {/* Milestone Pin: AIS Transit Window Indicator */}
        <div
          style={{
            position: 'absolute',
            left: `${aisStartPct}%`,
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            transform: 'translateX(-50%)',
            pointerEvents: 'none',
          }}
        >
          <Navigation size={10} color="var(--color-accent-blue)" style={{ position: 'absolute', top: '1px' }} />
        </div>

        {/* Native Range Slider Element */}
        <input
          type="range"
          min="0"
          max="100"
          step="0.05"
          value={currentPct}
          onChange={handleScrubberChange}
          style={{
            position: 'relative',
            width: '100%',
            cursor: 'ew-resize',
            opacity: 0.85,
            zIndex: 10,
            accentColor: 'var(--color-accent-blue)',
          }}
        />
      </div>

      {/* 3. Footer Readout: Search Envelope Bounds */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-2xs)', color: 'var(--color-text-muted)' }}>
        <span>SEARCH WINDOW START: <MonospaceValue value={new Date(startEpoch).toISOString().replace('T', ' ').substring(0, 19) + ' UTC'} /></span>
        <span style={{ letterSpacing: '0.04em' }}>[{(totalDuration / 3600000).toFixed(1)} HOURS METOCEAN & AIS CORRIDOR]</span>
        <span>SEARCH WINDOW END: <MonospaceValue value={new Date(endEpoch).toISOString().replace('T', ' ').substring(0, 19) + ' UTC'} /></span>
      </div>
    </div>
  );
};
