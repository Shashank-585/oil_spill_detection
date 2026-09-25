/**
 * frontend/src/api/casesApi.ts
 *
 * Case registry and scientific artifact queries via TanStack Query.
 * Interacts strictly with the read-only FastAPI Data Bridge.
 */

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './apiClient';

export interface LocationInfo {
  latitude: number;
  longitude: number;
  description?: string | null;
}

export interface DatasetsAvailable {
  sar: boolean;
  slicks: boolean;
  ais: boolean;
  backward_drift: boolean;
  forward_drift: boolean;
  attribution: boolean;
  uncertainty: boolean;
}

export interface CaseSummaryItem {
  case_id: string;
  name: string;
  incident_type?: string | null;
  location_name?: string | null;
  location?: LocationInfo | null;
  event_time_utc?: string | null;
  observation_time_utc?: string | null;
  validation_role?: string | null;
  ground_truth_quality?: string | null;
  datasets_available: DatasetsAvailable;
}

export interface EventInfo {
  incident_type?: string | null;
  estimated_start_utc?: string | null;
  estimated_end_utc?: string | null;
  search_start_utc?: string | null;
  search_end_utc?: string | null;
}

export interface ObservationInfo {
  platform?: string | null;
  instrument?: string | null;
  sensor_mode?: string | null;
  scene_id?: string | null;
  timestamp_utc?: string | null;
  orbit_direction?: string | null;
}

export interface CaseDetailResponse {
  case_id: string;
  name: string;
  location_name?: string | null;
  location?: LocationInfo | null;
  bounding_box?: {
    west: number;
    south: number;
    east: number;
    north: number;
  } | null;
  event?: EventInfo | null;
  observation?: ObservationInfo | null;
  validation_role?: string | null;
  ground_truth_quality?: string | null;
  ground_truth_source?: string | null;
  datasets: DatasetsAvailable;
}

export interface VesselCandidateItem {
  mmsi: number;
  vessel_name: string;
  hypothesis_count: number;
  hypothesis_ids: string[];
  min_distance_m: number;
  max_distance_m: number;
}

export interface EvidenceComponents {
  drift_consistency: number;
  spatial_compatibility: number;
  source_plausibility: number;
  temporal_compatibility: number;
  ais_track_quality: number;
}

export interface UnderlyingMetrics {
  centroid_error_m?: number | null;
  mean_particle_distance_m?: number | null;
  vessel_source_distance_m?: number | null;
  release_timestamp?: string | null;
  ais_gap_seconds?: number | null;
  ais_track_quality?: string | null;
  coverage?: number | null;
  iou?: number | null;
  causal_precedence_status?: string | null;
  causal_eligibility?: boolean | null;
  has_conflict?: boolean | null;
  conflict_description?: string | null;
  source_score?: number | null;
  spatial_score?: number | null;
  temporal_score?: number | null;
  drift_score?: number | null;
  ais_quality_score?: number | null;
}

export interface LimitingFactor {
  dimension: string;
  label: string;
  severity: 'DISQUALIFYING' | 'HIGH_LIMITING' | 'MODERATE_LIMITING' | string;
  detail: string;
  underlying_value?: string | null;
}

export interface EvidenceBreakdown {
  why_ranked_highly: string[];
  why_not_ranked_higher: string[];
  limiting_factors: LimitingFactor[];
}

export interface VesselAttributionItem {
  mmsi: number;
  vessel_name: string;
  vessel_type: string;
  vessel_rank: number;
  best_evidence_score: number;
  mean_evidence_score: number;
  vessel_evidence_state: string;
  causal_precedence_status?: string | null;
  best_hypothesis_id: string;
  best_associated_slick?: string | null;
  compatible_hypotheses_count: number;
  evidence_components?: EvidenceComponents | null;
  best_hypothesis_explanation?: string | null;
  primary_strength?: string | null;
  primary_weakness?: string | null;
  underlying_metrics?: UnderlyingMetrics | null;
  evidence_breakdown?: EvidenceBreakdown | null;
}

export interface UncertaintySummaryResponse {
  case_id: string;
  timestamp_utc: string;
  ensemble_size: number;
  random_seed: number;
  calibration_audit: {
    is_probability_calibrated: boolean;
    calibration_status: string;
    available_cases_count?: number;
    verified_culprit_cases_count?: number;
    mandatory_scientific_notice: string;
  };
  rank_stability_top_hypotheses: Array<{
    hypothesis_id?: string;
    vessel_name?: string;
    top_1_frequency: number;
    top_3_frequency: number;
    mean_rank: number;
    std_rank: number;
    mean_score?: number;
    rank_stability_category: string;
  }>;
}

// ============================================================================
// API Fetch Functions
// ============================================================================

export async function fetchCases(): Promise<CaseSummaryItem[]> {
  return apiFetch<CaseSummaryItem[]>('/api/cases');
}

export async function fetchCaseDetail(caseId: string): Promise<CaseDetailResponse> {
  return apiFetch<CaseDetailResponse>(`/api/cases/${encodeURIComponent(caseId)}`);
}

export async function fetchSarStats(caseId: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/api/cases/${encodeURIComponent(caseId)}/sar/stats`);
}

export interface GeoJsonFeatureCollection {
  type: 'FeatureCollection';
  features: Array<{
    type: string;
    geometry: {
      type: string;
      coordinates: unknown;
    };
    properties: Record<string, unknown>;
  }>;
  metadata?: Record<string, unknown>;
}

export async function fetchSlicksGeoJson(caseId: string): Promise<GeoJsonFeatureCollection> {
  return apiFetch<GeoJsonFeatureCollection>(`/api/cases/${encodeURIComponent(caseId)}/slicks`);
}

export async function fetchAisVessels(caseId: string): Promise<VesselCandidateItem[]> {
  return apiFetch<VesselCandidateItem[]>(`/api/cases/${encodeURIComponent(caseId)}/ais/vessels`);
}

export async function fetchAttributionRanking(caseId: string): Promise<VesselAttributionItem[]> {
  return apiFetch<VesselAttributionItem[]>(`/api/cases/${encodeURIComponent(caseId)}/attribution/ranking`);
}

export async function fetchAttributionUncertainty(caseId: string): Promise<UncertaintySummaryResponse> {
  return apiFetch<UncertaintySummaryResponse>(`/api/cases/${encodeURIComponent(caseId)}/attribution/uncertainty`);
}

export interface SarRasterInfo {
  case_id: string;
  source_scientific_raster: string;
  visualization_derivative_url: string;
  is_visualization_derivative: boolean;
  bounds: {
    west: number;
    south: number;
    east: number;
    north: number;
  };
  coordinates: [number, number][];
}

export async function fetchSarRaster(caseId: string): Promise<SarRasterInfo> {
  return apiFetch<SarRasterInfo>(`/api/cases/${encodeURIComponent(caseId)}/sar/raster`);
}

export async function fetchAisTracks(caseId: string): Promise<GeoJsonFeatureCollection> {
  return apiFetch<GeoJsonFeatureCollection>(`/api/cases/${encodeURIComponent(caseId)}/ais/tracks`);
}

export async function fetchDriftTrajectories(caseId: string): Promise<GeoJsonFeatureCollection> {
  return apiFetch<GeoJsonFeatureCollection>(`/api/cases/${encodeURIComponent(caseId)}/drift/trajectories`);
}

export async function fetchHypotheses(caseId: string): Promise<GeoJsonFeatureCollection> {
  return apiFetch<GeoJsonFeatureCollection>(`/api/cases/${encodeURIComponent(caseId)}/hypotheses`);
}

// ============================================================================
// TanStack Query Hooks
// ============================================================================

export const queryKeys = {
  cases: ['cases'] as const,
  caseDetail: (caseId: string) => ['case', caseId] as const,
  sarStats: (caseId: string) => ['case', caseId, 'sarStats'] as const,
  sarRaster: (caseId: string) => ['case', caseId, 'sarRaster'] as const,
  slicks: (caseId: string) => ['case', caseId, 'slicks'] as const,
  aisVessels: (caseId: string) => ['case', caseId, 'aisVessels'] as const,
  aisTracks: (caseId: string) => ['case', caseId, 'aisTracks'] as const,
  driftTrajectories: (caseId: string) => ['case', caseId, 'driftTrajectories'] as const,
  hypotheses: (caseId: string) => ['case', caseId, 'hypotheses'] as const,
  attributionRanking: (caseId: string) => ['case', caseId, 'attributionRanking'] as const,
  attributionUncertainty: (caseId: string) => ['case', caseId, 'attributionUncertainty'] as const,
};

export function useCasesQuery() {
  return useQuery({
    queryKey: queryKeys.cases,
    queryFn: fetchCases,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

export function useCaseDetailQuery(caseId: string | null) {
  return useQuery({
    queryKey: queryKeys.caseDetail(caseId || ''),
    queryFn: () => fetchCaseDetail(caseId!),
    enabled: Boolean(caseId),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useAttributionRankingQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.attributionRanking(caseId || ''),
    queryFn: () => fetchAttributionRanking(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useAisVesselsQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.aisVessels(caseId || ''),
    queryFn: () => fetchAisVessels(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useSarStatsQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.sarStats(caseId || ''),
    queryFn: () => fetchSarStats(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useSarRasterQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.sarRaster(caseId || ''),
    queryFn: () => fetchSarRaster(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useSlicksQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.slicks(caseId || ''),
    queryFn: () => fetchSlicksGeoJson(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useAisTracksQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.aisTracks(caseId || ''),
    queryFn: () => fetchAisTracks(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useDriftTrajectoriesQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.driftTrajectories(caseId || ''),
    queryFn: () => fetchDriftTrajectories(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useHypothesesQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.hypotheses(caseId || ''),
    queryFn: () => fetchHypotheses(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useUncertaintyQuery(caseId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.attributionUncertainty(caseId || ''),
    queryFn: () => fetchAttributionUncertainty(caseId!),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export interface SpillComparisonItem {
  hypothesis_id: string;
  candidate_id?: string;
  mmsi: number;
  vessel_name?: string;
  observed_slick_id: string;
  release_timestamp: string;
  observation_timestamp: string;
  release_lat?: number;
  release_lon?: number;
  simulation_duration_hours?: number;
  particle_count?: number;
  active_particle_count?: number;
  active_particle_fraction?: number;
  simulation_status?: string;
  predicted_centroid_lat?: number;
  predicted_centroid_lon?: number;
  observed_centroid_lat?: number;
  observed_centroid_lon?: number;
  centroid_error_m?: number;
  mean_particle_distance_m?: number;
  median_particle_distance_m?: number;
  p90_particle_distance_m?: number;
  coverage?: number;
  in_slick_fraction?: number;
  intersection_area_m2?: number;
  union_area_m2?: number;
  iou: number;
  predicted_area_m2?: number;
  observed_area_m2?: number;
  predicted_length_m?: number;
  predicted_width_m?: number;
  predicted_aspect_ratio?: number;
  predicted_orientation_deg?: number;
  observed_length_m?: number;
  observed_width_m?: number;
  observed_aspect_ratio?: number;
  observed_orientation_deg?: number;
  delta_length_m?: number;
  delta_width_m?: number;
  delta_aspect_ratio?: number;
  delta_orientation_deg?: number;
  norm_centroid_score?: number;
  norm_particle_score?: number;
  norm_coverage_score?: number;
  norm_iou_score?: number;
}

export interface SimulationParticle {
  particle_id: number;
  lat: number;
  lon: number;
  status: string;
}

export interface SimulationTrajectory {
  track_index: number;
  coordinates: [number, number][];
}

export interface SimulationDetailResponse {
  case_id: string;
  hypothesis_id: string;
  metadata: SpillComparisonItem | Record<string, any>;
  particles: SimulationParticle[];
  trajectories: SimulationTrajectory[];
}

export async function fetchSpillComparisons(caseId: string, hypothesisId?: string): Promise<SpillComparisonItem[]> {
  const query = hypothesisId ? `?hypothesis_id=${encodeURIComponent(hypothesisId)}` : '';
  return apiFetch<SpillComparisonItem[]>(`/api/cases/${encodeURIComponent(caseId)}/attribution/spill-comparisons${query}`);
}

export function useSpillComparisonsQuery(caseId: string | null, hypothesisId?: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['case', caseId, 'spillComparisons', hypothesisId || 'all'] as const,
    queryFn: () => fetchSpillComparisons(caseId!, hypothesisId),
    enabled: Boolean(caseId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export async function fetchSimulationDetail(caseId: string, hypothesisId: string): Promise<SimulationDetailResponse> {
  return apiFetch<SimulationDetailResponse>(
    `/api/cases/${encodeURIComponent(caseId)}/attribution/simulations/${encodeURIComponent(hypothesisId)}`
  );
}

export function useSimulationDetailQuery(caseId: string | null, hypothesisId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['case', caseId, 'simulationDetail', hypothesisId] as const,
    queryFn: () => fetchSimulationDetail(caseId!, hypothesisId!),
    enabled: Boolean(caseId) && Boolean(hypothesisId) && enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

// ============================================================================
// PHASE 23: INVESTIGATION DOSSIER & EXPORT TYPES & HOOKS
// ============================================================================

export interface ExecutiveQAItem {
  question: string;
  answer: string;
  status: string;
  key_metric?: string | null;
}

export interface Section1CaseIdentification {
  case_id: string;
  name: string;
  incident_type: string;
  location_name?: string | null;
  origin_coordinates?: { latitude: number; longitude: number } | null;
  incident_t0_utc: string;
  observation_timestamp_utc: string;
  validation_role: string;
  ground_truth_source?: string | null;
  status_category: string;
}

export interface Section2ExecutiveSummary {
  core_questions: ExecutiveQAItem[];
  summary_narrative: string;
}

export interface Section3SatelliteObservation {
  platform: string;
  instrument: string;
  sensor_mode: string;
  scene_id?: string | null;
  timestamp_utc: string;
  orbit_direction?: string | null;
  calibrated_file?: string | null;
}

export interface Section4DetectedSlick {
  slicks_count: number;
  total_area_m2: number;
  total_area_hectares: number;
  mean_backscatter_sigma0_db?: number | null;
  damping_ratio_db?: number | null;
  segmentation_algorithm: string;
}

export interface Section5EnvironmentalConditions {
  ocean_currents_source: string;
  ocean_currents_file?: string | null;
  wind_source: string;
  wind_file?: string | null;
  spatial_coverage?: Record<string, number> | null;
  temporal_coverage?: Record<string, any> | null;
}

export interface Section6SourceReconstruction {
  model_name: string;
  integration_scheme: string;
  leeway_factor: string;
  wind_deflection_deg: string;
  turbulent_diffusion_dh: string;
  release_horizons_hours: number[];
  candidate_slicks_evaluated: number;
  total_source_hypotheses: number;
}

export interface Section7AisCoverage {
  spatial_window?: Record<string, number> | null;
  temporal_window?: Record<string, any> | null;
  archive_available: boolean;
  total_candidate_mmsis: number;
  track_quality_notes: string;
}

export interface Section8CandidateVessels {
  total_vessels_in_corridor: number;
  candidate_vessels_count: number;
  filtering_criteria: string;
  top_candidates_preview: Record<string, any>[];
}

export interface Section9Hypotheses4D {
  total_hypotheses_count: number;
  dimensions: string[];
  generation_method: string;
}

export interface Section10CounterfactualSimulation {
  simulation_engine: string;
  particle_count_per_run: number;
  total_simulations_run: number;
  evaluation_metric: string;
  mean_iou?: number | null;
  top_hypothesis_iou?: number | null;
}

export interface Section11EvidenceRanking {
  ranking_count: number;
  top_vessel_name?: string | null;
  top_vessel_mmsi?: number | null;
  top_vessel_score?: number | null;
  candidates: Record<string, any>[];
}

export interface Section12CausalConsistency {
  enforced: boolean;
  causal_status_top_candidate?: string | null;
  disqualified_post_release_count: number;
  notes: string;
}

export interface Section13Uncertainty {
  ensemble_size: number;
  random_seed: number;
  rank_stability_score?: number | null;
  margin_to_rank_2?: number | null;
  confidence_category: string;
}

export interface Section14DataLimitations {
  limitations: string[];
  is_negative_control: boolean;
  ais_archive_missing: boolean;
}

export interface Section15Conclusion {
  best_supported_hypothesis: string;
  synthesis_statement: string;
  decision_support_role: string;
}

export interface Section16Provenance {
  sha256_checksum: string;
  generated_at_utc: string;
  system_version: string;
  non_deceptive_statement: string;
}

export interface InvestigationDossier {
  dossier_version: string;
  case_id: string;
  case_identification: Section1CaseIdentification;
  executive_summary: Section2ExecutiveSummary;
  satellite_observation: Section3SatelliteObservation;
  detected_slick: Section4DetectedSlick;
  environmental_conditions: Section5EnvironmentalConditions;
  source_reconstruction: Section6SourceReconstruction;
  ais_coverage: Section7AisCoverage;
  candidate_vessels: Section8CandidateVessels;
  hypotheses_4d: Section9Hypotheses4D;
  counterfactual_simulation: Section10CounterfactualSimulation;
  evidence_ranking: Section11EvidenceRanking;
  causal_consistency: Section12CausalConsistency;
  uncertainty: Section13Uncertainty;
  data_limitations: Section14DataLimitations;
  conclusion: Section15Conclusion;
  provenance: Section16Provenance;
}

export async function fetchInvestigationDossier(caseId: string): Promise<InvestigationDossier> {
  return apiFetch<InvestigationDossier>(`/api/cases/${encodeURIComponent(caseId)}/dossier`);
}

export function useInvestigationDossierQuery(caseId: string | null) {
  return useQuery({
    queryKey: ['case', caseId, 'dossier'] as const,
    queryFn: () => fetchInvestigationDossier(caseId!),
    enabled: Boolean(caseId),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

// ============================================================================
// Phase 24: Authority Notification & Alert Workflow
// ============================================================================

export interface AuthorityAlert {
  alert_id: string;
  case_id: string;
  alert_type: string;
  timestamp_utc: string;
  severity: 'INFO' | 'NOTICE' | 'ACTION_REQUIRED' | string;
  subject: string;
  summary: string;
  body_markdown: string;
  case_name: string;
  observation_time_utc?: string | null;
  satellite_platform?: string | null;
  investigation_status: string;
  slick_count: number;
  slick_total_area_ha: number;
  candidate_vessel_count: number;
  attribution_status: string;
  top_supported_hypothesis?: string | null;
  key_limitations: string[];
  dossier_link: string;
  recommended_authority_actions: string[];
}

export interface NotificationFeedResponse {
  case_id: string;
  alerts: AuthorityAlert[];
  total_alerts: number;
  latest_attribution_alert?: AuthorityAlert | null;
}

export async function fetchCaseNotifications(caseId: string): Promise<NotificationFeedResponse> {
  return apiFetch<NotificationFeedResponse>(`/api/cases/${encodeURIComponent(caseId)}/notifications`);
}

export function useCaseNotificationsQuery(caseId: string | null) {
  return useQuery({
    queryKey: ['case', caseId, 'notifications'] as const,
    queryFn: () => fetchCaseNotifications(caseId!),
    enabled: Boolean(caseId),
    staleTime: 60 * 1000,
    retry: 1,
  });
}

export async function fetchAllNotifications(): Promise<AuthorityAlert[]> {
  return apiFetch<AuthorityAlert[]>(`/api/notifications`);
}

export function useAllNotificationsQuery() {
  return useQuery({
    queryKey: ['notifications', 'all'] as const,
    queryFn: () => fetchAllNotifications(),
    staleTime: 60 * 1000,
    retry: 1,
  });
}

// ==============================================================================
// Phase 25: Data Readiness & Reproducible Provenance
// ==============================================================================

export type ReadinessStatus = 'READY' | 'LIMITED' | 'UNAVAILABLE' | 'NOT REQUIRED';

export interface ReadinessCheckItem {
  name: string;
  status: ReadinessStatus;
  details: string;
  source?: string | null;
}

export interface DatasetProvenanceRecord {
  dataset_name: string;
  source: string;
  acquisition_time?: string | null;
  processing_version: string;
  sha256_checksum?: string | null;
  artifact_timestamp?: string | null;
  record_type: string;
}

export interface DataReadinessReport {
  case_id: string;
  case_name: string;
  validation_role: string;
  overall_status: ReadinessStatus;
  checks: ReadinessCheckItem[];
  data_limitations: string[];
  provenance_records: DatasetProvenanceRecord[];
  summary_notes: string;
}

export async function fetchCaseReadiness(caseId: string): Promise<DataReadinessReport> {
  return apiFetch<DataReadinessReport>(`/api/cases/${encodeURIComponent(caseId)}/readiness`);
}

export function useCaseReadinessQuery(caseId: string | null) {
  return useQuery({
    queryKey: ['case', caseId, 'readiness'] as const,
    queryFn: () => fetchCaseReadiness(caseId!),
    enabled: Boolean(caseId),
    staleTime: 60 * 1000,
    retry: 1,
  });
}

export async function fetchCaseProvenance(caseId: string): Promise<DatasetProvenanceRecord[]> {
  return apiFetch<DatasetProvenanceRecord[]>(`/api/cases/${encodeURIComponent(caseId)}/provenance`);
}

export function useCaseProvenanceQuery(caseId: string | null) {
  return useQuery({
    queryKey: ['case', caseId, 'provenance'] as const,
    queryFn: () => fetchCaseProvenance(caseId!),
    enabled: Boolean(caseId),
    staleTime: 60 * 1000,
    retry: 1,
  });
}

// ==============================================================================
// Phase 26: Satellite Observation Metadata Upgrade
// ==============================================================================

export interface Sentinel1Metadata {
  platform: string;
  sensor: string;
  acquisition_time_utc: string;
  mode: string;
  product_type: string;
  polarization_used: string;
  polarization_explanation: string;
  polarizations_available: string[];
  orbit_direction?: string | null;
  relative_orbit?: number | null;
  spatial_resolution?: string | null;
  scene_dimensions?: string | null;
  scene_coverage?: string | null;
  processing_status: string;
  speckle_filter?: string | null;
  cfar_detector_info?: string | null;
}

export interface Sentinel2Metadata {
  available: boolean;
  platform?: string | null;
  sensor?: string | null;
  acquisition_time_utc?: string | null;
  cloud_cover_percentage?: number | null;
  cloud_cover_text?: string | null;
  available_bands: string[];
  product_type?: string | null;
  role: string;
  pipeline_usage_disclaimer: string;
  details?: string | null;
}

export interface TimelineObservationEvent {
  event_id: string;
  label: string;
  event_type: 'PRE_EVENT' | 'INCIDENT_REFERENCE' | 'OPERATIONAL_SAR' | 'SUPPORTING_OPTICAL' | 'POST_EVENT' | string;
  timestamp_utc: string;
  platform?: string | null;
  observation_nature: 'ACTUAL_OBSERVATION' | 'INCIDENT_REFERENCE' | 'REVISIT_OPPORTUNITY' | string;
  relative_to_incident_hours: number;
  description: string;
}

export interface ObservationTimeline {
  incident_time_utc: string;
  operational_observation_time_utc: string;
  events: TimelineObservationEvent[];
}

export interface RevisitContext {
  constellation_nominal_repeat_days: number;
  constellation_dual_repeat_days: number;
  sub_cycle_revisit_opportunity_hours: string;
  revisit_distinction_notice: string;
  case_revisit_audit: string;
}

export interface SatelliteObservationPackage {
  case_id: string;
  case_name: string;
  sentinel1: Sentinel1Metadata;
  sentinel2?: Sentinel2Metadata | null;
  timeline: ObservationTimeline;
  revisit_context: RevisitContext;
}

export async function fetchCaseSatelliteObservations(caseId: string): Promise<SatelliteObservationPackage> {
  return apiFetch<SatelliteObservationPackage>(`/api/cases/${encodeURIComponent(caseId)}/satellite/observations`);
}

export function useCaseSatelliteObservationsQuery(caseId: string | null) {
  return useQuery({
    queryKey: ['case', caseId, 'satellite-observations'] as const,
    queryFn: () => fetchCaseSatelliteObservations(caseId!),
    enabled: Boolean(caseId),
    staleTime: 60 * 1000,
    retry: 1,
  });
}






