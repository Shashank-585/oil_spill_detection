export type CausalPrecedenceStatus =
  | 'VALID_PRE_EVENT'
  | 'VALID_ACTIVE_WINDOW'
  | 'INELIGIBLE_POST_EVENT'
  | 'AT_RELEASE'
  | 'AFTER_EVENT'
  | 'COMPATIBLE'
  | 'INCOMPATIBLE'
  | 'UNKNOWN'
  | string;

export type VesselEvidenceState =
  | 'HIGH_SUPPORT'
  | 'MODERATE_SUPPORT'
  | 'LOW_SUPPORT'
  | 'INSUFFICIENT_EVIDENCE'
  | string;

export interface EvidenceComponents {
  drift_consistency: number;
  spatial_compatibility: number;
  temporal_compatibility: number;
  source_plausibility: number;
  ais_track_quality: number;
}

export interface CandidateVessel {
  mmsi: number;
  vessel_name: string;
  vessel_type: string;
  imo?: number | null;
  best_hypothesis_id: string;
  best_evidence_score: number;
  mean_evidence_score: number;
  compatible_hypotheses_count: number;
  best_associated_slick: string;
  vessel_evidence_state: VesselEvidenceState;
  causal_status: CausalPrecedenceStatus;
  vessel_rank: number;
  evidence_components?: EvidenceComponents;
  best_hypothesis_explanation?: string;
  release_time_min_utc?: string;
  release_time_max_utc?: string;
}

export interface SourceHypothesis4D {
  hypothesis_id: string;
  vessel_mmsi: number;
  vessel_name: string;
  slick_id: string;
  release_time_utc: string;
  latitude: number;
  longitude: number;
  distance_to_backward_cone_m: number;
  temporal_offset_seconds: number;
  causal_precedence: CausalPrecedenceStatus;
  source_age_hours: number;
}
