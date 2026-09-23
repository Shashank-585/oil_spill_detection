import React from 'react';
import type { TimelineMarker } from '../../types/timeline';

interface EventMarkersProps {
  markers: TimelineMarker[];
  startEpoch: number;
  totalDuration: number;
}

export const EventMarkers: React.FC<EventMarkersProps> = ({ markers, startEpoch, totalDuration }) => {
  return (
    <>
      {markers.map((marker) => {
        const markerEpoch = new Date(marker.timestamp_utc).getTime();
        const pct = Math.min(Math.max(((markerEpoch - startEpoch) / totalDuration) * 100, 0), 100);

        return (
          <div
            key={marker.id}
            title={`${marker.label}: ${marker.timestamp_utc}`}
            style={{
              position: 'absolute',
              left: `${pct}%`,
              top: 0,
              bottom: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              pointerEvents: 'auto',
              cursor: 'help',
              transform: 'translateX(-50%)',
            }}
          >
            {/* Vertical Marker Line */}
            <div
              style={{
                width: '1px',
                height: '100%',
                backgroundColor: marker.color ?? 'var(--color-text-muted)',
                opacity: 0.7,
              }}
            />

            {/* Marker Indicator Dot */}
            <div
              style={{
                position: 'absolute',
                top: '4px',
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: marker.color ?? 'var(--color-text-muted)',
                boxShadow: `0 0 4px ${marker.color ?? 'var(--color-text-muted)'}`,
              }}
            />
          </div>
        );
      })}
    </>
  );
};
