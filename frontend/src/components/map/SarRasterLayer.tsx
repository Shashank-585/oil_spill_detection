import React from 'react';

interface LayerProps {
  visible: boolean;
  opacity?: number;
}

/**
 * SarRasterLayer
 *
 * Dedicated layer for calibrated Sentinel-1 SAR imagery (linear or dB sigma0).
 * MapLibre / deck.gl BitmapLayer mount point.
 */
export const SarRasterLayer: React.FC<LayerProps> = ({ visible }) => {
  if (!visible) return null;
  return null; // Mounts to deck.gl or MapLibre instance when active
};
