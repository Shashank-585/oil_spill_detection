import React from 'react';

interface LayerProps {
  visible: boolean;
  opacity?: number;
}

/**
 * SlickPolygonLayer
 *
 * Dedicated vector layer for candidate oil slick polygons extracted from SAR.
 * MapLibre GeoJSONSource / deck.gl GeoJsonLayer mount point.
 */
export const SlickPolygonLayer: React.FC<LayerProps> = ({ visible }) => {
  if (!visible) return null;
  return null;
};
