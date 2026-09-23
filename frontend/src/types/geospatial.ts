export interface Coordinate2D {
  latitude: number;
  longitude: number;
}

export interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface SlickFeatureProperties {
  slick_id: string;
  area_km2: number;
  contrast_db: number;
  aspect_ratio: number;
  detection_confidence: number;
}

export interface AisTrackPoint {
  mmsi: number;
  timestamp_utc: string;
  latitude: number;
  longitude: number;
  sog_knots: number;
  cog_degrees: number;
  nav_status?: string;
}

export interface DriftParticlePoint {
  particle_id: number;
  timestamp_utc: string;
  latitude: number;
  longitude: number;
  depth_m?: number;
}
