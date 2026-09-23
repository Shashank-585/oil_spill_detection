import type { CaseMetadata } from '../types/case';
import type { CandidateVessel } from '../types/attribution';
import type { TimelineMarker } from '../types/timeline';

/**
 * DEVELOPMENT ONLY MOCK DATA
 *
 * Clearly isolated mock models reflecting frozen validated data from Case 001 and Case 003.
 * Used strictly for UI scaffolding prior to live FastAPI endpoint connection.
 * NEVER mix into production analytical pipelines.
 */

export const MOCK_CASES: Record<string, CaseMetadata> = {
  case_003_golden_ray: {
    case_id: 'case_003_golden_ray',
    incident_name: 'M/V Golden Ray Capsizing & Bunker Spill',
    incident_date: '2019-09-08',
    source_type: 'vessel',
    ground_truth_quality: 'A (NTSB / USCG MAR-21/03)',
    ground_truth_source: 'NTSB Marine Accident Report MAR-21/03',
    satellite_available: true,
    ais_available: true,
    currents_available: true,
    wind_available: true,
    source_location_available: true,
    source_time_available: true,
    culprit_vessel_available: true,
    case_status: 'VERIFIED_AVAILABLE',
    validation_eligibility: 'ELIGIBLE',
    validation_role: 'POSITIVE_VESSEL_CASE',
    is_synthetic: false,
    reference_vessel_mmsi: 538007762,
    reference_vessel_name: 'GOLDEN RAY',
    incident_location: {
      latitude: 31.129,
      longitude: -81.406,
      description: 'St. Simons Sound entrance channel',
    },
    bounding_box: {
      west: -81.60,
      south: 31.00,
      east: -81.10,
      north: 31.30,
    },
    incident_start_utc: '2019-09-08T05:46:00Z',
    observation_time_utc: '2019-09-08T11:25:31Z',
  },
  case_001: {
    case_id: 'case_001',
    incident_name: 'Huntington Beach Pipeline Leak',
    incident_date: '2021-10-02',
    source_type: 'pipeline',
    ground_truth_quality: 'A (NTSB DCA22FM001)',
    ground_truth_source: 'NTSB Pipeline Accident Report',
    satellite_available: true,
    ais_available: true,
    currents_available: true,
    wind_available: true,
    source_location_available: true,
    source_time_available: true,
    culprit_vessel_available: false,
    case_status: 'VERIFIED_AVAILABLE',
    validation_eligibility: 'ELIGIBLE',
    validation_role: 'NEGATIVE_NON_VESSEL_CASE',
    is_synthetic: false,
    reference_vessel_mmsi: null,
    reference_vessel_name: null,
    incident_location: {
      latitude: 33.68,
      longitude: -118.05,
      description: 'San Pedro Bay subsea pipeline corridor',
    },
    bounding_box: {
      west: -118.35,
      south: 33.45,
      east: -117.80,
      north: 33.80,
    },
    incident_start_utc: '2021-10-01T18:00:00Z',
    observation_time_utc: '2021-10-02T01:49:00Z',
  },
};

export const MOCK_TOP_CANDIDATE: CandidateVessel = {
  mmsi: 538007762,
  vessel_name: 'GOLDEN RAY',
  vessel_type: 'Cargo / Car Carrier',
  imo: 9775816,
  best_hypothesis_id: '4DH_0022',
  best_evidence_score: 0.6891,
  mean_evidence_score: 0.6095,
  compatible_hypotheses_count: 14,
  best_associated_slick: 'CS_0035',
  vessel_evidence_state: 'HIGH_SUPPORT',
  causal_status: 'VALID_PRE_EVENT',
  vessel_rank: 1,
  evidence_components: {
    drift_consistency: 0.8,
    spatial_compatibility: 0.68,
    source_plausibility: 0.53,
    temporal_compatibility: 0.86,
    ais_track_quality: 0.6,
  },
  best_hypothesis_explanation:
    'GOLDEN RAY: Physical drift is strong (0.80), spatial compatibility is moderate (0.68), source plausibility is moderate (0.53), temporal alignment is strong (0.86), and AIS track quality is moderate (0.60).',
};

export const MOCK_TIMELINE_MARKERS: TimelineMarker[] = [
  {
    id: 'm1',
    type: 'SPILL_EVENT',
    timestamp_utc: '2019-09-08T05:46:00Z',
    label: 'Incident Event (Capsizing)',
    description: 'Outbound transit capsizing at Sound Buoy 19',
    color: 'var(--color-accent-crimson)',
  },
  {
    id: 'm2',
    type: 'SAR_OBSERVATION',
    timestamp_utc: '2019-09-08T11:25:31Z',
    label: 'Sentinel-1 Primary Observation',
    description: 'S1A descending pass over St. Simons Sound',
    color: 'var(--color-accent-cyan)',
  },
  {
    id: 'm3',
    type: 'SOURCE_WINDOW_START',
    timestamp_utc: '2019-09-07T12:00:00Z',
    label: 'Source Search Window Start',
    color: 'var(--color-accent-purple)',
  },
  {
    id: 'm4',
    type: 'VESSEL_INTERCEPT',
    timestamp_utc: '2019-09-08T05:35:00Z',
    label: 'Channel Transit Intercept',
    color: 'var(--color-accent-blue)',
  },
];
