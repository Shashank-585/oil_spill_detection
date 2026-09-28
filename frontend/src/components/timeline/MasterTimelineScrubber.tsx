import React, { useMemo, useRef, useEffect } from 'react';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import { MonospaceValue } from '../common/MonospaceValue';
import {
  Play,
  Pause,
  RotateCcw,
  SkipBack,
  SkipForward,
  Radio,
  Clock,
} from 'lucide-react';

export const MasterTimelineScrubber: React.FC = () => {
  const {
    currentTimeUtc,
    setCurrentTimeUtc,
    isReplayMode,
    isPlaying,
    setIsPlaying,
    togglePlayPause,
    playbackSpeed,
    setPlaybackSpeed,
  } = useInvestigationStore();
  const { activeCase } = useActiveCase();

  // Dynamic T0 and SAR timestamps based on active case
  const t0Str = activeCase?.event?.estimated_start_utc || activeCase?.event?.search_start_utc || '2019-09-08T05:46:00Z';
  const sarStr = activeCase?.observation?.timestamp_utc || '2019-09-08T11:25:31Z';

  const t0Epoch = useMemo(() => new Date(t0Str).getTime(), [t0Str]);
  const sarEpoch = useMemo(() => new Date(sarStr).getTime(), [sarStr]);

  // Dynamic analytical window
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

  const totalDuration = Math.max(endEpoch - startEpoch, 3600 * 1000);

  // Sync timeline to new case T0 on case change
  useEffect(() => {
    if (t0Str) {
      setCurrentTimeUtc(t0Str);
    }
  }, [t0Str, setCurrentTimeUtc]);

  // Keyboard shortcut: Spacebar to toggle Play/Pause
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement as HTMLElement)?.tagName;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(activeTag)) {
        return;
      }
      if (e.code === 'Space') {
        e.preventDefault();
        togglePlayPause();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePlayPause]);

  // Animation Loop via requestAnimationFrame
  const lastTimeRef = useRef<number | null>(null);
  const animFrameIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isPlaying) {
      lastTimeRef.current = null;
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
        animFrameIdRef.current = null;
      }
      return;
    }

    const baseAdvancePerSec = 600 * 1000; // 10 min simulated per 1 real sec at 1x

    const step = (now: number) => {
      if (lastTimeRef.current !== null) {
        const deltaMs = now - lastTimeRef.current;
        const safeDeltaSec = Math.min(deltaMs / 1000, 0.1);
        const advanceSimMs = safeDeltaSec * baseAdvancePerSec * playbackSpeed;

        const currEpoch = new Date(useInvestigationStore.getState().currentTimeUtc).getTime();
        const nextEpoch = currEpoch + advanceSimMs;

        if (nextEpoch >= endEpoch) {
          setCurrentTimeUtc(new Date(endEpoch).toISOString());
          setIsPlaying(false);
          return;
        } else {
          setCurrentTimeUtc(new Date(nextEpoch).toISOString());
        }
      }
      lastTimeRef.current = now;
      animFrameIdRef.current = requestAnimationFrame(step);
    };

    animFrameIdRef.current = requestAnimationFrame(step);

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
        animFrameIdRef.current = null;
      }
      lastTimeRef.current = null;
    };
  }, [isPlaying, playbackSpeed, endEpoch, setCurrentTimeUtc, setIsPlaying]);

  const currentEpoch = new Date(currentTimeUtc).getTime();
  const currentPct = Math.min(Math.max(((currentEpoch - startEpoch) / totalDuration) * 100, 0), 100);

  // Key Physical Milestones
  const t0Pct = Math.min(Math.max(((t0Epoch - startEpoch) / totalDuration) * 100, 0), 100);
  const sarPct = Math.min(Math.max(((sarEpoch - startEpoch) / totalDuration) * 100, 0), 100);
  const aisStartPct = Math.max(t0Pct - 4, 0);
  const aisWidthPct = Math.min(Math.max(sarPct - aisStartPct + 4, 10), 100 - aisStartPct);

  // Offset from T0
  const diffFromT0Ms = currentEpoch - t0Epoch;
  const isNegative = diffFromT0Ms < 0;
  const absMs = Math.abs(diffFromT0Ms);
  const hrs = Math.floor(absMs / (3600 * 1000));
  const mins = Math.floor((absMs % (3600 * 1000)) / (60 * 1000));
  const offsetStr = `T ${isNegative ? '-' : '+'} ${hrs.toString().padStart(2, '0')}h ${mins.toString().padStart(2, '0')}m`;

  // Step milestone handlers
  const handleStep = (forward: boolean) => {
    const stepDelta = (forward ? 30 : -30) * 60 * 1000; // 30 min step
    const target = Math.max(startEpoch, Math.min(endEpoch, currentEpoch + stepDelta));
    setCurrentTimeUtc(new Date(target).toISOString());
  };

  const handleScrubberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    const newEpoch = startEpoch + (val / 100) * totalDuration;
    setCurrentTimeUtc(new Date(newEpoch).toISOString());
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderTop: '1px solid var(--color-border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 15,
        flexShrink: 0,
        userSelect: 'none',
      }}
    >
      {/* Main Single-Deck 42px Replay Bar */}
      <div
        style={{
          height: '42px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '0 12px',
        }}
      >
        {/* 1. Left: Replay Title, Transport & Snap Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 800,
              letterSpacing: '0.05em',
              color: isReplayMode || isPlaying ? 'var(--color-accent-seafoam)' : 'var(--color-text-secondary)',
              textTransform: 'uppercase',
              marginRight: '2px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            4D REPLAY
          </span>

          <button
            onClick={togglePlayPause}
            style={{
              width: '26px',
              height: '26px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: isPlaying ? 'var(--color-accent-seafoam)' : 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              color: isPlaying ? 'var(--color-bg-deep)' : 'var(--color-text-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'background-color 0.12s ease',
            }}
            title={isPlaying ? 'Pause Simulation (Space)' : 'Play Simulation (Space)'}
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause size={12} /> : <Play size={12} style={{ marginLeft: '1px' }} />}
          </button>

          <button
            onClick={() => handleStep(false)}
            style={{
              width: '24px',
              height: '26px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              color: 'var(--color-text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
            title="Step Back 30 Minutes"
            aria-label="Step back"
          >
            <SkipBack size={12} />
          </button>

          <button
            onClick={() => handleStep(true)}
            style={{
              width: '24px',
              height: '26px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              color: 'var(--color-text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
            title="Step Forward 30 Minutes"
            aria-label="Step forward"
          >
            <SkipForward size={12} />
          </button>

          {/* Snap T0 (Warm Sand) */}
          <button
            onClick={() => setCurrentTimeUtc(t0Str)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '2px',
              padding: '2px 5px',
              height: '26px',
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              color: 'var(--color-accent-sand)',
              cursor: 'pointer',
            }}
            title={`Snap to Incident T₀ (${t0Str})`}
          >
            <RotateCcw size={10} />
            <span>T₀</span>
          </button>

          {/* Snap Tobs (Pale Sand) */}
          <button
            onClick={() => setCurrentTimeUtc(sarStr)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '2px',
              padding: '2px 5px',
              height: '26px',
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              color: 'var(--color-accent-sand-pale)',
              cursor: 'pointer',
            }}
            title={`Snap to Observation T_obs (${sarStr})`}
          >
            <Radio size={10} />
            <span>Tobs</span>
          </button>
        </div>

        {/* 2. Center: Timeline Scrubber Track with High Visibility */}
        <div style={{ flex: 1, position: 'relative', height: '22px', display: 'flex', alignItems: 'center' }}>
          {/* Base track */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              height: '6px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              borderRadius: '3px',
              border: '1px solid rgba(255, 255, 255, 0.12)',
            }}
          />

          {/* AIS Window band */}
          <div
            style={{
              position: 'absolute',
              left: `${aisStartPct}%`,
              width: `${aisWidthPct}%`,
              height: '6px',
              backgroundColor: 'rgba(95, 145, 138, 0.25)',
              borderRadius: '2px',
              pointerEvents: 'none',
            }}
            title="AIS Surveillance Envelope"
          />

          {/* T0 Marker (Warm Sand) */}
          <div
            style={{
              position: 'absolute',
              left: `${t0Pct}%`,
              top: '0px',
              bottom: '0px',
              width: '2px',
              backgroundColor: 'var(--color-accent-sand)',
              zIndex: 2,
              pointerEvents: 'none',
            }}
            title={`Incident T₀: ${t0Str}`}
          />

          {/* SAR / Tobs Marker (Pale Sand) */}
          <div
            style={{
              position: 'absolute',
              left: `${sarPct}%`,
              top: '0px',
              bottom: '0px',
              width: '2px',
              backgroundColor: 'var(--color-accent-sand-pale)',
              zIndex: 2,
              pointerEvents: 'none',
            }}
            title={`Observation Tobs: ${sarStr}`}
          />

          {/* Range input slider */}
          <input
            type="range"
            min="0"
            max="100"
            step="0.05"
            value={currentPct}
            onChange={handleScrubberChange}
            style={{
              position: 'absolute',
              left: 0,
              width: '100%',
              height: '22px',
              margin: 0,
              opacity: 0,
              cursor: 'pointer',
              zIndex: 5,
            }}
            aria-label="Investigation timeline scrubber"
          />

          {/* Current playhead marker (Seafoam, no neon glow) */}
          <div
            style={{
              position: 'absolute',
              left: `${currentPct}%`,
              transform: 'translateX(-50%)',
              width: '10px',
              height: '16px',
              backgroundColor: 'var(--color-accent-seafoam)',
              borderRadius: '2px',
              border: '1.5px solid #ffffff',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.5)',
              zIndex: 4,
              pointerEvents: 'none',
            }}
          />
        </div>

        {/* 3. Right: Offset Badge, Timestamp & Speed Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          {/* Relative Offset badge */}
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 700,
              color: isNegative ? 'var(--color-accent-seafoam)' : 'var(--color-accent-sand)',
              backgroundColor: 'var(--color-bg-base)',
              padding: '2px 6px',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid var(--color-border-subtle)',
              whiteSpace: 'nowrap',
            }}
          >
            {offsetStr}
          </div>

          {/* Absolute Timestamp */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px', whiteSpace: 'nowrap' }}>
            <Clock size={11} color="var(--color-text-muted)" />
            <MonospaceValue value={currentTimeUtc ? currentTimeUtc.replace('T', ' ').substring(0, 19) + 'Z' : 'N/A'} />
          </div>

          {/* Speed Pills: 0.5× 1× 2× 5× */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1px',
              backgroundColor: 'var(--color-bg-base)',
              padding: '2px',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid var(--color-border-subtle)',
            }}
          >
            {[0.5, 1, 2, 5].map((spd) => (
              <button
                key={spd}
                onClick={() => setPlaybackSpeed(spd)}
                style={{
                  padding: '1px 5px',
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  backgroundColor: playbackSpeed === spd ? 'var(--color-accent-seafoam)' : 'transparent',
                  color: playbackSpeed === spd ? 'var(--color-bg-deep)' : 'var(--color-text-muted)',
                  borderRadius: '2px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: 'none',
                  lineHeight: '14px',
                }}
              >
                {spd}×
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
