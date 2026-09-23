export type CaseStatus = 'VERIFIED_AVAILABLE' | 'POTENTIALLY_AVAILABLE' | 'INELIGIBLE_MISSING_DATA';
export type ValidationRole = 'NEGATIVE_NON_VESSEL_CASE' | 'POSITIVE_VESSEL_CASE';
export type SourceType = 'pipeline' | 'vessel' | 'natural_seep' | 'unknown';

export interface IncidentLocation {
  latitude: number;
  longitude: number;
  description?: string;
}

export interface CaseMetadata {
  case_id: string;
  incident_name: string;
  incident_date: string;
  source_type: SourceType;
  ground_truth_quality: string;
  ground_truth_source: string;
  satellite_available: boolean;
  ais_available: boolean;
  currents_available: boolean;
  wind_available: boolean;
  source_location_available: boolean;
  source_time_available: boolean;
  culprit_vessel_available: boolean;
  case_status: CaseStatus;
  validation_eligibility: string;
  validation_role: ValidationRole;
  is_synthetic: boolean;
  reference_vessel_mmsi?: number | null;
  reference_vessel_name?: string | null;
  incident_location?: IncidentLocation;
  bounding_box?: {
    west: number;
    south: number;
    east: number;
    north: number;
  };
  observation_time_utc?: string;
  incident_start_utc?: string;
}
