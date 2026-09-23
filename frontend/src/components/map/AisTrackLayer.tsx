import React from 'react';

interface LayerProps {
  visible: boolean;
  opacity?: number;
}

/**
 * AisTrackLayer
 *
 * Dedicated GPU-accelerated polyline and vessel position layer.
 * deck.gl PathLayer / ScatterplotLayer mount point for 100,000+ AIS pings.
 */
export const AisTrackLayer: React.FC<LayerProps> = ({ visible }) => {
  if (!visible) return null;
  return null;
};
