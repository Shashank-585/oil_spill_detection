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
  simulation_duration_hours?: number;
  particle_count?: number;
  active_particle_count?: number;
  predicted_centroid_lat?: number;
  predicted_centroid_lon?: number;
  observed_centroid_lat?: number;
  observed_centroid_lon?: number;
  centroid_error_m?: number;
  mean_particle_distance_m?: number;
  coverage?: number;
  in_slick_fraction?: number;
  intersection_area_m2?: number;
  union_area_m2?: number;
  iou: number;
  predicted_area_m2?: number;
  observed_area_m2?: number;
  predicted_length_m?: number;
  predicted_width_m?: number;
  observed_length_m?: number;
  observed_width_m?: number;
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


