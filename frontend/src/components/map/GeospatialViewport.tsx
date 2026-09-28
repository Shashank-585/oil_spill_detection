import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as maplibregl from 'maplibre-gl';
import { MapboxOverlay } from '@deck.gl/mapbox';
import { GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import {
  useSarRasterQuery,
  useSlicksQuery,
  useAisTracksQuery,
  useDriftTrajectoriesQuery,
  useHypothesesQuery,
  useSimulationDetailQuery,
  useSpillComparisonsQuery,
} from '../../api/casesApi';
import { MapLayerControls } from './MapLayerControls';
import { MapLegend } from './MapLegend';
import { ZoomIn, ZoomOut, Compass, X, Target } from 'lucide-react';

// Esri Dark Gray Canvas basemap: free, reliable, official, zero watermark, dark nautical aesthetic
const ESRI_DARK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'esri-dark-base': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    },
    'esri-dark-ref': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
    },
  },
  layers: [
    {
      id: 'esri-dark-base-layer',
      type: 'raster',
      source: 'esri-dark-base',
      minzoom: 0,
      maxzoom: 16,
    },
    {
      id: 'esri-dark-ref-layer',
      type: 'raster',
      source: 'esri-dark-ref',
      minzoom: 0,
      maxzoom: 16,
    },
  ],
};

interface SelectedFeatureDetail {
  type: 'slick' | 'vessel' | 'drift' | 'hypothesis';
  title: string;
  properties: Record<string, unknown>;
}

function getPointAtTimeFast(
  coords: [number, number][],
  epochs: number[],
  targetEpoch: number
): [number, number] | null {
  const n = epochs.length;
  if (n === 0 || coords.length !== n) {
    return null;
  }
  const first = epochs[0];
  const last = epochs[n - 1];

  // Allow 20-minute window outside track boundaries for temporal persistence
  if (targetEpoch < first - 20 * 60 * 1000 || targetEpoch > last + 20 * 60 * 1000) {
    return null;
  }
  if (targetEpoch <= first) return coords[0];
  if (targetEpoch >= last) return coords[n - 1];

  // Binary search: find interval [epochs[low], epochs[high]]
  let low = 0;
  let high = n - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (epochs[mid] <= targetEpoch) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  const i = Math.max(0, Math.min(high, n - 2));
  const t0 = epochs[i];
  const t1 = epochs[i + 1];
  const span = t1 - t0;
  if (span <= 0) return coords[i];

  const frac = (targetEpoch - t0) / span;
  return [
    coords[i][0] + frac * (coords[i + 1][0] - coords[i][0]),
    coords[i][1] + frac * (coords[i + 1][1] - coords[i][1]),
  ];
}

export const GeospatialViewport: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const incidentMarkerRef = useRef<maplibregl.Marker | null>(null);

  const [mapLoaded, setMapLoaded] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState<SelectedFeatureDetail | null>(null);

  // Atomic selectors for store properties to prevent unrelated re-renders
  const mapLayers = useInvestigationStore((s) => s.mapLayers);
  const selectedMmsi = useInvestigationStore((s) => s.selectedMmsi);
  const selectedHypothesisId = useInvestigationStore((s) => s.selectedHypothesisId);
  const setSelectedMmsi = useInvestigationStore((s) => s.setSelectedMmsi);
  const setSelectedHypothesisId = useInvestigationStore((s) => s.setSelectedHypothesisId);
  const inspectorOpen = useInvestigationStore((s) => s.inspectorOpen);
  const toggleInspector = useInvestigationStore((s) => s.toggleInspector);
  const currentTimeUtc = useInvestigationStore((s) => s.currentTimeUtc);
  const activeWorkspace = useInvestigationStore((s) => s.activeWorkspace);
  const focusSelectedHypothesis = useInvestigationStore((s) => s.focusSelectedHypothesis);
  const setFocusSelectedHypothesis = useInvestigationStore((s) => s.setFocusSelectedHypothesis);

  const { activeCaseId, activeCase, topCandidate } = useActiveCase();

  // Active target candidate (explicitly selected or default top-ranked candidate)
  const activeTargetMmsi = selectedMmsi ?? topCandidate?.mmsi;
  const activeTargetHypothesisId = selectedHypothesisId ?? topCandidate?.best_hypothesis_id;

  // Queries for real scientific geospatial artifacts
  const { data: sarRasterData } = useSarRasterQuery(activeCaseId);
  const { data: slicksData } = useSlicksQuery(activeCaseId);
  const { data: aisTracksData } = useAisTracksQuery(activeCaseId);
  const { data: driftData } = useDriftTrajectoriesQuery(activeCaseId);
  const { data: hypothesesData } = useHypothesesQuery(activeCaseId);
  const { data: spillComparisons } = useSpillComparisonsQuery(activeCaseId);
  const { data: simulationDetail } = useSimulationDetailQuery(
    activeCaseId,
    selectedHypothesisId,
    Boolean(selectedHypothesisId)
  );

  const activeComparison = useMemo(() => {
    if (!spillComparisons || !spillComparisons.length) return null;
    if (selectedHypothesisId) {
      return spillComparisons.find((c) => c.hypothesis_id === selectedHypothesisId) || null;
    }
    return null;
  }, [spillComparisons, selectedHypothesisId]);

  const currentEpoch = useMemo(() => new Date(currentTimeUtc).getTime(), [currentTimeUtc]);

  // Pre-index numeric epochs once per dataset load to eliminate string parsing on scrub
  const indexedAisTracks = useMemo(() => {
    if (!aisTracksData?.features) return [];
    return (aisTracksData.features as any[]).map((feat) => {
      const coords = (feat.geometry?.coordinates as [number, number][]) || [];
      const timestamps = (feat.properties?.timestamps as string[]) || [];
      const epochs = timestamps.map((ts) => new Date(ts).getTime());
      return {
        properties: feat.properties,
        coords,
        epochs,
      };
    });
  }, [aisTracksData]);

  const indexedDriftTrajectories = useMemo(() => {
    if (!driftData?.features) return [];
    return (driftData.features as any[]).map((feat) => {
      const coords = (feat.geometry?.coordinates as [number, number][]) || [];
      const timestamps = (feat.properties?.timestamps as string[]) || [];
      const epochs = timestamps.map((ts) => new Date(ts).getTime());
      return {
        properties: feat.properties,
        coords,
        epochs,
      };
    });
  }, [driftData]);

  const preprocessedHypotheses = useMemo(() => {
    if (!hypothesesData?.features) return { type: 'FeatureCollection', features: [] };
    const features = (hypothesesData.features as any[]).map((feat) => {
      const releaseTime = feat.properties?.release_timestamp || feat.properties?.source_time_utc;
      const releaseEpoch = releaseTime ? new Date(releaseTime).getTime() : 0;
      return {
        ...feat,
        properties: {
          ...feat.properties,
          _releaseEpoch: releaseEpoch,
        },
      };
    });
    return { type: 'FeatureCollection', features };
  }, [hypothesesData]);

  // Compute real-time vessel positions via O(log N) binary search
  const currentVesselsGeoJson = useMemo(() => {
    if (!indexedAisTracks.length || !mapLayers.aisTracks) return { type: 'FeatureCollection', features: [] };
    const pts: any[] = [];
    for (let i = 0; i < indexedAisTracks.length; i++) {
      const item = indexedAisTracks[i];
      const pos = getPointAtTimeFast(item.coords, item.epochs, currentEpoch);
      if (pos) {
        pts.push({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: pos },
          properties: item.properties,
        });
      }
    }
    return { type: 'FeatureCollection', features: pts };
  }, [indexedAisTracks, mapLayers.aisTracks, currentEpoch]);

  // Compute real-time drift particle positions via O(log N) binary search
  const currentDriftGeoJson = useMemo(() => {
    if (!indexedDriftTrajectories.length || !mapLayers.driftParticles) return { type: 'FeatureCollection', features: [] };
    const pts: any[] = [];
    for (let i = 0; i < indexedDriftTrajectories.length; i++) {
      const item = indexedDriftTrajectories[i];
      const pos = getPointAtTimeFast(item.coords, item.epochs, currentEpoch);
      if (pos) {
        pts.push({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: pos },
          properties: item.properties,
        });
      }
    }
    return { type: 'FeatureCollection', features: pts };
  }, [indexedDriftTrajectories, mapLayers.driftParticles, currentEpoch]);

  // Geospatial vectors for Counterfactual Simulation Visualization
  const simulationTrajectoriesGeoJson = useMemo(() => {
    if (!simulationDetail?.trajectories || !simulationDetail.trajectories.length) {
      return { type: 'FeatureCollection', features: [] };
    }
    const features = simulationDetail.trajectories.map((traj) => ({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: traj.coordinates,
      },
      properties: {
        track_index: traj.track_index,
      },
    }));
    return { type: 'FeatureCollection', features };
  }, [simulationDetail]);

  const counterfactualSourceGeoJson = useMemo(() => {
    const relLat = activeComparison?.release_lat ?? (simulationDetail?.metadata as any)?.release_lat;
    const relLon = activeComparison?.release_lon ?? (simulationDetail?.metadata as any)?.release_lon;
    if (relLat == null || relLon == null) {
      return { type: 'FeatureCollection', features: [] };
    }
    return {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [relLon, relLat],
          },
          properties: {
            hypothesis_id: selectedHypothesisId,
            mmsi: activeComparison?.mmsi,
            release_time: activeComparison?.release_timestamp,
            label: 'HYPOTHESIS RELEASE SOURCE POINT',
          },
        },
      ],
    };
  }, [activeComparison, simulationDetail, selectedHypothesisId]);

  const centroidOffsetVectorGeoJson = useMemo(() => {
    const predLat = activeComparison?.predicted_centroid_lat;
    const predLon = activeComparison?.predicted_centroid_lon;
    const obsLat = activeComparison?.observed_centroid_lat;
    const obsLon = activeComparison?.observed_centroid_lon;
    if (predLat == null || predLon == null || obsLat == null || obsLon == null) {
      return { type: 'FeatureCollection', features: [] };
    }
    return {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: [
              [predLon, predLat],
              [obsLon, obsLat],
            ],
          },
          properties: {
            centroid_error_m: activeComparison?.centroid_error_m,
            label: `Centroid Error: ${activeComparison?.centroid_error_m?.toFixed(1) ?? 'N/A'} m`,
          },
        },
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [predLon, predLat],
          },
          properties: {
            type: 'predicted_centroid',
            label: 'Predicted Slick Centroid',
          },
        },
      ],
    };
  }, [activeComparison]);

  // Smoothly center the map view on the counterfactual simulation when active
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded || activeWorkspace !== 'evidence' || !activeComparison) return;
    const pLat = activeComparison.predicted_centroid_lat;
    const pLon = activeComparison.predicted_centroid_lon;

    if (pLat != null && pLon != null) {
      const oLat = activeComparison.observed_centroid_lat ?? pLat;
      const oLon = activeComparison.observed_centroid_lon ?? pLon;
      const rLat = activeComparison.release_lat ?? pLat;
      const rLon = activeComparison.release_lon ?? pLon;

      const minLon = Math.min(pLon, oLon, rLon);
      const maxLon = Math.max(pLon, oLon, rLon);
      const minLat = Math.min(pLat, oLat, rLat);
      const maxLat = Math.max(pLat, oLat, rLat);

      if (isFinite(minLon) && isFinite(maxLon) && isFinite(minLat) && isFinite(maxLat)) {
        const pad = 0.02;
        map.fitBounds(
          [
            [minLon - pad, minLat - pad],
            [maxLon + pad, maxLat + pad],
          ],
          { padding: { top: 70, bottom: 70, left: 70, right: 540 }, duration: 900 }
        );
      }
    }
  }, [activeWorkspace, activeComparison?.hypothesis_id, mapLoaded]);

  // 1. Initialize MapLibre Map and deck.gl MapboxOverlay
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const initialLng = activeCase?.location?.longitude ?? -81.418;
    const initialLat = activeCase?.location?.latitude ?? 31.132;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: ESRI_DARK_STYLE,
      center: [initialLng, initialLat],
      zoom: 10,
      attributionControl: false,
    });

    const overlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
    });

    map.addControl(overlay as unknown as maplibregl.IControl);

    map.on('load', () => {
      setMapLoaded(true);
    });

    mapRef.current = map;
    overlayRef.current = overlay;

    return () => {
      overlay.finalize();
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
      setMapLoaded(false);
    };
  }, []);

  // 2. Handle Case Switching: Camera bounds, Incident Marker, and AOI
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    // Reset feature popup on case switch
    setSelectedFeature(null);

    // Update AOI boundary
    const aoiSourceId = 'case-aoi-source';
    const aoiLayerId = 'case-aoi-layer';

    if (map.getLayer(aoiLayerId)) {
      map.removeLayer(aoiLayerId);
    }
    if (map.getSource(aoiSourceId)) {
      map.removeSource(aoiSourceId);
    }

    if (activeCase?.bounding_box) {
      const bb = activeCase.bounding_box;
      const aoiGeoJson: GeoJSON.Feature<GeoJSON.Polygon> = {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [bb.west, bb.north],
              [bb.east, bb.north],
              [bb.east, bb.south],
              [bb.west, bb.south],
              [bb.west, bb.north],
            ],
          ],
        },
        properties: { name: 'AOI Surveillance Extent' },
      };

      map.addSource(aoiSourceId, {
        type: 'geojson',
        data: aoiGeoJson,
      });

      map.addLayer({
        id: aoiLayerId,
        type: 'line',
        source: aoiSourceId,
        paint: {
          'line-color': '#388bfd',
          'line-width': 1.5,
          'line-dasharray': [4, 4],
          'line-opacity': 0.8,
        },
      });

      // Fit bounds to case AOI
      map.fitBounds(
        [
          [bb.west, bb.south],
          [bb.east, bb.north],
        ],
        { padding: 60, duration: 800 }
      );
    } else if (activeCase?.location) {
      map.flyTo({
        center: [activeCase.location.longitude, activeCase.location.latitude],
        zoom: 11,
        duration: 800,
      });
    }

    // Update Incident Location Marker
    if (incidentMarkerRef.current) {
      incidentMarkerRef.current.remove();
      incidentMarkerRef.current = null;
    }

    if (activeCase?.location) {
      const el = document.createElement('div');
      el.className = 'incident-marker-node';
      el.style.display = 'flex';
      el.style.flexDirection = 'column';
      el.style.alignItems = 'center';
      el.style.cursor = 'pointer';

      el.innerHTML = `
        <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background-color: rgba(248, 81, 73, 0.3); animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
          <div style="position: relative; width: 14px; height: 14px; border-radius: 50%; background-color: #f85149; border: 2.5px solid #ffffff; box-shadow: 0 0 10px rgba(248, 81, 73, 0.9);"></div>
        </div>
        <div style="background: rgba(10, 13, 19, 0.94); border: 1px solid rgba(248, 81, 73, 0.5); border-radius: 3px; padding: 2px 6px; font-size: 9px; font-weight: 700; color: #f85149; font-family: monospace; white-space: nowrap; margin-top: 2px; box-shadow: 0 2px 6px rgba(0,0,0,0.6);">
          INCIDENT T₀
        </div>
      `;

      el.addEventListener('click', () => {
        setSelectedFeature({
          type: 'slick',
          title: 'Incident Origin Point (T₀)',
          properties: {
            latitude: activeCase.location?.latitude,
            longitude: activeCase.location?.longitude,
            description: activeCase.location?.description,
            incident_type: activeCase.event?.incident_type,
            estimated_start: activeCase.event?.estimated_start_utc,
          },
        });
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([activeCase.location.longitude, activeCase.location.latitude])
        .addTo(map);

      incidentMarkerRef.current = marker;
    }
  }, [activeCaseId, activeCase, mapLoaded]);

  // Synchronize Incident Marker and Satellite Footprint visibility
  useEffect(() => {
    if (incidentMarkerRef.current) {
      incidentMarkerRef.current.getElement().style.display = mapLayers.incidentPoint ? 'flex' : 'none';
    }
    const map = mapRef.current;
    if (map && mapLoaded && map.getLayer('case-aoi-layer')) {
      map.setLayoutProperty('case-aoi-layer', 'visibility', mapLayers.satelliteFootprint ? 'visible' : 'none');
    }
  }, [mapLayers.incidentPoint, mapLayers.satelliteFootprint, mapLoaded]);

  // 3. Render Georeferenced SAR Visualization Derivative Layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const layerId = 'sar-raster-layer';
    const sourceId = 'sar-raster-source';

    // Remove old SAR layer & source if switching cases or if unavailable
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }

    if (sarRasterData && mapLayers.sarRaster) {
      try {
        map.addSource(sourceId, {
          type: 'image',
          url: sarRasterData.visualization_derivative_url,
          coordinates: sarRasterData.coordinates as [
            [number, number],
            [number, number],
            [number, number],
            [number, number],
          ],
        });

        map.addLayer({
          id: layerId,
          type: 'raster',
          source: sourceId,
          paint: {
            'raster-opacity': 0.75,
            'raster-fade-duration': 150,
          },
        });
      } catch (err) {
        console.warn('SAR raster layer mount warning:', err);
      }
    }
  }, [sarRasterData, mapLayers.sarRaster, activeCaseId, mapLoaded]);

  // 4. Update deck.gl High-Volume Scientific Vector Layers
  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay || !mapLoaded) return;

    const layers = [
      // 4A. Oil Slick Polygons
      new GeoJsonLayer({
        id: 'slicks-layer',
        data: (slicksData as any) || [],
        visible: (activeWorkspace === 'evidence' || mapLayers.slickPolygons) && Boolean(slicksData?.features?.length),
        pickable: true,
        filled: true,
        stroked: true,
        lineWidthUnits: 'pixels',
        getFillColor: (f: any) => {
          const props = f?.properties || {};
          const isCompared = activeComparison && (props.slick_id === activeComparison.observed_slick_id || props.id === activeComparison.observed_slick_id);
          return isCompared ? [224, 201, 148, 190] : [209, 178, 124, 155];
        },
        getLineColor: (f: any) => {
          const props = f?.properties || {};
          const isCompared = activeComparison && (props.slick_id === activeComparison.observed_slick_id || props.id === activeComparison.observed_slick_id);
          return isCompared ? [232, 227, 213, 255] : [209, 178, 124, 240];
        },
        getLineWidth: (f: any) => {
          const props = f?.properties || {};
          const isCompared = activeComparison && (props.slick_id === activeComparison.observed_slick_id || props.id === activeComparison.observed_slick_id);
          return isCompared ? 3.0 : 2;
        },
        lineWidthMinPixels: 1.5,
        updateTriggers: {
          getFillColor: [activeComparison?.observed_slick_id],
          getLineColor: [activeComparison?.observed_slick_id],
          getLineWidth: [activeComparison?.observed_slick_id],
        },
        onClick: (info) => {
          if (info.object) {
            const props = (info.object as any).properties || {};
            setSelectedFeature({
              type: 'slick',
              title: `Slick Polygon #${props.slick_id || props.id || 'N/A'}`,
              properties: props,
            });
          }
        },
      }),

      // 4B. Backward Drift Trajectories (Muted Teal)
      new GeoJsonLayer({
        id: 'drift-trajectories-layer',
        data: (driftData as any) || [],
        visible: mapLayers.driftParticles && Boolean(driftData?.features?.length),
        pickable: true,
        stroked: true,
        filled: false,
        lineWidthUnits: 'pixels',
        getLineColor: [95, 145, 138, 160],
        getLineWidth: 1.5,
        lineWidthMinPixels: 1,
        onClick: (info) => {
          if (info.object) {
            const props = (info.object as any).properties || {};
            setSelectedFeature({
              type: 'drift',
              title: `Drift Particle #${props.particle_index ?? ''} (${props.candidate_slick_id || ''})`,
              properties: props,
            });
          }
        },
      }),

      // 4C. AIS Vessel Trajectories (Desaturated Teal / Warm Sand Highlight)
      new GeoJsonLayer({
        id: 'ais-tracks-layer',
        data: (aisTracksData as any) || [],
        visible: mapLayers.aisTracks && Boolean(aisTracksData?.features?.length),
        pickable: true,
        stroked: true,
        filled: false,
        lineWidthUnits: 'pixels',
        getLineColor: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.mmsi === activeTargetMmsi;
          if (focusSelectedHypothesis) {
            return isSelected ? [209, 178, 124, 255] : [78, 107, 105, 50];
          }
          return isSelected ? [209, 178, 124, 255] : [78, 107, 105, 140];
        },
        getLineWidth: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.mmsi === activeTargetMmsi;
          if (focusSelectedHypothesis) {
            return isSelected ? 3.5 : 1.0;
          }
          return isSelected ? 3.5 : 1.5;
        },
        lineWidthMinPixels: 1,
        updateTriggers: {
          getLineColor: [selectedMmsi, activeTargetMmsi, focusSelectedHypothesis],
          getLineWidth: [selectedMmsi, activeTargetMmsi, focusSelectedHypothesis],
        },
        onClick: (info) => {
          if (info.object) {
            const props = (info.object as any).properties || {};
            if (props.mmsi) {
              setSelectedMmsi(Number(props.mmsi));
              if (!inspectorOpen) toggleInspector();
            }
            setSelectedFeature({
              type: 'vessel',
              title: `AIS Vessel: ${props.vessel_name || 'UNKNOWN'}`,
              properties: props,
            });
          }
        },
      }),

      // 4D. Real-Time Drift Particles at currentTimeUtc (Muted Seafoam)
      new GeoJsonLayer({
        id: 'current-drift-particles-layer',
        data: (currentDriftGeoJson as any) || [],
        visible: mapLayers.driftParticles && Boolean(currentDriftGeoJson?.features?.length),
        pickable: true,
        pointType: 'circle',
        pointRadiusUnits: 'pixels',
        getPointRadius: 4,
        pointRadiusMinPixels: 2.5,
        pointRadiusMaxPixels: 8,
        getFillColor: [120, 175, 165, 220],
        getLineColor: [232, 227, 213, 200],
        getLineWidth: 1,
        lineWidthUnits: 'pixels',
        onClick: (info) => {
          if (info.object) {
            const props = (info.object as any).properties || {};
            setSelectedFeature({
              type: 'drift',
              title: `Particle Position at Active Epoch (${props.candidate_slick_id || ''})`,
              properties: props,
            });
          }
        },
      }),

      // 4E. Real-Time Vessel Locations at currentTimeUtc (Warm Sand Selected)
      new GeoJsonLayer({
        id: 'current-vessels-layer',
        data: (currentVesselsGeoJson as any) || [],
        visible: mapLayers.aisTracks && Boolean(currentVesselsGeoJson?.features?.length),
        pickable: true,
        pointType: 'circle',
        pointRadiusUnits: 'pixels',
        getPointRadius: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.mmsi === activeTargetMmsi;
          return isSelected ? 8 : 4.5;
        },
        pointRadiusMinPixels: 3,
        pointRadiusMaxPixels: 14,
        getFillColor: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.mmsi === activeTargetMmsi;
          if (focusSelectedHypothesis) {
            return isSelected ? [209, 178, 124, 255] : [78, 107, 105, 80];
          }
          return isSelected ? [209, 178, 124, 255] : [78, 107, 105, 200];
        },
        getLineColor: [232, 227, 213, 230],
        getLineWidth: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.mmsi === activeTargetMmsi;
          return isSelected ? 2 : 1;
        },
        lineWidthUnits: 'pixels',
        updateTriggers: {
          getPointRadius: [selectedMmsi, activeTargetMmsi, focusSelectedHypothesis],
          getFillColor: [selectedMmsi, activeTargetMmsi, focusSelectedHypothesis],
          getLineWidth: [selectedMmsi, activeTargetMmsi, focusSelectedHypothesis],
        },
        onClick: (info) => {
          if (info.object) {
            const props = (info.object as any).properties || {};
            if (props.mmsi) {
              setSelectedMmsi(Number(props.mmsi));
              if (!inspectorOpen) toggleInspector();
            }
            setSelectedFeature({
              type: 'vessel',
              title: `Vessel: ${props.vessel_name || 'UNKNOWN'}`,
              properties: props,
            });
          }
        },
      }),

      // 4F. 4D Source Hypothesis Locations & Vectors (Warm Sand / Rust Origin)
      new GeoJsonLayer({
        id: 'hypotheses-layer',
        data: (preprocessedHypotheses as any),
        visible: mapLayers.candidateMarkers && Boolean(preprocessedHypotheses?.features?.length),
        pickable: true,
        pointType: 'circle',
        pointRadiusUnits: 'pixels',
        getPointRadius: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.hypothesis_id === activeTargetHypothesisId || (feat?.properties?.mmsi && feat?.properties?.mmsi === activeTargetMmsi);
          if (focusSelectedHypothesis) {
            return isSelected ? 8 : 3.0;
          }
          const releaseEpoch = feat?.properties?._releaseEpoch;
          const isProximate = releaseEpoch && Math.abs(releaseEpoch - currentEpoch) < 30 * 60 * 1000;
          return isSelected ? 8 : isProximate ? 6 : 4.0;
        },
        pointRadiusMinPixels: 2.5,
        pointRadiusMaxPixels: 14,
        getFillColor: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.hypothesis_id === activeTargetHypothesisId || (feat?.properties?.mmsi && feat?.properties?.mmsi === activeTargetMmsi);
          if (focusSelectedHypothesis) {
            return isSelected
              ? [209, 178, 124, 255] // Warm Sand selected
              : [130, 150, 146, 30]; // Restrained background
          }
          const releaseEpoch = feat?.properties?._releaseEpoch;
          const isProximate = releaseEpoch && Math.abs(releaseEpoch - currentEpoch) < 30 * 60 * 1000;
          return isSelected
            ? [209, 178, 124, 255]
            : isProximate
            ? [224, 201, 148, 230]
            : [184, 111, 82, 180]; // Rust origin
        },
        getLineColor: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.hypothesis_id === activeTargetHypothesisId || (feat?.properties?.mmsi && feat?.properties?.mmsi === activeTargetMmsi);
          if (focusSelectedHypothesis) {
            return isSelected
              ? [209, 178, 124, 255]
              : [78, 107, 105, 25];
          }
          return isSelected ? [209, 178, 124, 255] : [130, 150, 146, 100];
        },
        getLineWidth: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.hypothesis_id === activeTargetHypothesisId || (feat?.properties?.mmsi && feat?.properties?.mmsi === activeTargetMmsi);
          if (focusSelectedHypothesis) {
            return isSelected ? 2.5 : 0.8;
          }
          return isSelected ? 2.5 : 1.0;
        },
        lineWidthUnits: 'pixels',
        updateTriggers: {
          getPointRadius: [selectedHypothesisId, activeTargetHypothesisId, activeTargetMmsi, focusSelectedHypothesis, currentEpoch],
          getFillColor: [selectedHypothesisId, activeTargetHypothesisId, activeTargetMmsi, focusSelectedHypothesis, currentEpoch],
          getLineColor: [selectedHypothesisId, activeTargetHypothesisId, activeTargetMmsi, focusSelectedHypothesis],
          getLineWidth: [selectedHypothesisId, activeTargetHypothesisId, activeTargetMmsi, focusSelectedHypothesis],
        },
        onClick: (info) => {
          if (info.object) {
            const props = (info.object as any).properties || {};
            if (props.hypothesis_id) {
              setSelectedHypothesisId(String(props.hypothesis_id));
            }
            if (props.mmsi) {
              setSelectedMmsi(Number(props.mmsi));
            }
            if (!inspectorOpen) toggleInspector();
            setSelectedFeature({
              type: 'hypothesis',
              title: `Hypothesis ${props.hypothesis_id} (${props.vessel_name || 'Vessel'})`,
              properties: props,
            });
          }
        },
      }),

      // 4G. Counterfactual Forward Simulation Particle Plume (Muted Seafoam)
      new ScatterplotLayer({
        id: 'counterfactual-particles-layer',
        data: simulationDetail?.particles || [],
        visible: Boolean(simulationDetail?.particles?.length),
        pickable: true,
        opacity: 0.85,
        getPosition: (d: any) => [d.lon, d.lat],
        getRadius: 5,
        radiusMinPixels: 3.5,
        radiusMaxPixels: 12,
        getFillColor: [120, 175, 165, 215], // Muted Seafoam
        getLineColor: [232, 227, 213, 200],
        getLineWidth: 1,
        lineWidthUnits: 'pixels',
        updateTriggers: {
          getPosition: [simulationDetail?.hypothesis_id],
        },
        onClick: (info) => {
          if (info.object) {
            setSelectedFeature({
              type: 'drift',
              title: `Forward Simulated Particle #${(info.object as any).particle_id}`,
              properties: info.object as any,
            });
          }
        },
      }),

      // 4H. Counterfactual Trajectories (Muted Teal)
      new GeoJsonLayer({
        id: 'counterfactual-trajectories-layer',
        data: simulationTrajectoriesGeoJson as any,
        visible: Boolean(simulationTrajectoriesGeoJson.features.length),
        pickable: false,
        stroked: true,
        filled: false,
        lineWidthUnits: 'pixels',
        getLineColor: [95, 145, 138, 140],
        getLineWidth: 1.5,
        lineWidthMinPixels: 1,
        updateTriggers: {
          data: [simulationDetail?.hypothesis_id],
        },
      }),

      // 4I. Counterfactual Release Source Point (Rust Origin)
      new GeoJsonLayer({
        id: 'counterfactual-source-layer',
        data: counterfactualSourceGeoJson as any,
        visible: Boolean(counterfactualSourceGeoJson.features.length),
        pickable: true,
        pointType: 'circle',
        pointRadiusUnits: 'pixels',
        getPointRadius: 7,
        pointRadiusMinPixels: 5,
        pointRadiusMaxPixels: 14,
        getFillColor: [184, 111, 82, 255], // Rust release point
        getLineColor: [232, 227, 213, 255],
        getLineWidth: 2,
        lineWidthUnits: 'pixels',
        updateTriggers: {
          data: [activeComparison?.hypothesis_id],
        },
        onClick: (info) => {
          if (info.object) {
            const props = (info.object as any).properties || {};
            setSelectedFeature({
              type: 'hypothesis',
              title: 'Hypothesis Release Origin Point (T_release)',
              properties: props,
            });
          }
        },
      }),

      // 4J. Simulated vs Observed Centroid Offset Vector (Rust Vector / Warm Sand Point)
      new GeoJsonLayer({
        id: 'counterfactual-centroid-offset-layer',
        data: centroidOffsetVectorGeoJson as any,
        visible: (activeWorkspace === 'evidence') && Boolean(centroidOffsetVectorGeoJson.features.length),
        pickable: true,
        stroked: true,
        filled: true,
        lineWidthUnits: 'pixels',
        getLineColor: [184, 111, 82, 230], // Rust offset line
        getLineWidth: 2,
        lineWidthMinPixels: 1.5,
        pointType: 'circle',
        pointRadiusUnits: 'pixels',
        getPointRadius: 5.0,
        getFillColor: [209, 178, 124, 255], // Warm Sand predicted centroid point
        getLineColor2: [232, 227, 213, 255],
        updateTriggers: {
          data: [activeComparison?.hypothesis_id],
        },
        onClick: (info) => {
          if (info.object) {
            setSelectedFeature({
              type: 'drift',
              title: 'Centroid Displacement Vector',
              properties: (info.object as any).properties || {},
            });
          }
        },
      }),
    ];

    overlay.setProps({ layers });
  }, [
    mapLoaded,
    mapLayers,
    slicksData,
    aisTracksData,
    driftData,
    preprocessedHypotheses,
    currentVesselsGeoJson,
    currentDriftGeoJson,
    currentEpoch,
    selectedMmsi,
    selectedHypothesisId,
    inspectorOpen,
    activeWorkspace,
    activeComparison,
    simulationDetail,
    simulationTrajectoriesGeoJson,
    counterfactualSourceGeoJson,
    centroidOffsetVectorGeoJson,
    setSelectedMmsi,
    setSelectedHypothesisId,
    toggleInspector,
  ]);

  // Navigation handlers
  const handleZoomIn = useCallback(() => {
    mapRef.current?.zoomIn({ duration: 250 });
  }, []);

  const handleZoomOut = useCallback(() => {
    mapRef.current?.zoomOut({ duration: 250 });
  }, []);

  const handleResetNorth = useCallback(() => {
    mapRef.current?.resetNorth({ duration: 250 });
  }, []);

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        backgroundColor: 'var(--color-bg-deep)',
        overflow: 'hidden',
      }}
    >
      {/* MapLibre WebGL Canvas Container */}
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Layer Visibility Toggles */}
      <MapLayerControls />

      {/* Hypothesis Focus / Exploration Segmented Toggle (Phase 3 Core Control) */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          left: '108px',
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-xs)',
          padding: '2px',
          boxShadow: 'var(--shadow-md)',
          userSelect: 'none',
        }}
      >
        <button
          onClick={() => setFocusSelectedHypothesis(true)}
          style={{
            padding: '4px 8px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.04em',
            borderRadius: '2px',
            border: 'none',
            backgroundColor: focusSelectedHypothesis ? 'rgba(95, 145, 138, 0.22)' : 'transparent',
            color: focusSelectedHypothesis ? 'var(--color-accent-seafoam)' : 'var(--color-text-muted)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Focus Selected: Highlight selected candidate trajectory and release point; dim all background hypothesis lines"
        >
          FOCUS SELECTED
        </button>
        <button
          onClick={() => setFocusSelectedHypothesis(false)}
          style={{
            padding: '4px 8px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.04em',
            borderRadius: '2px',
            border: 'none',
            backgroundColor: !focusSelectedHypothesis ? 'rgba(95, 145, 138, 0.22)' : 'transparent',
            color: !focusSelectedHypothesis ? 'var(--color-accent-seafoam)' : 'var(--color-text-muted)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Show All Hypotheses: Display complete spider-web spatiotemporal candidate vector network"
        >
          SHOW ALL HYPOTHESES
        </button>
      </div>

      {/* Map Legend */}
      <MapLegend />

      {/* SAR Derivative Metadata Indicator */}
      {sarRasterData && mapLayers.sarRaster && (
        <div
          style={{
            position: 'absolute',
            top: '12px',
            left: '385px',
            zIndex: 10,
            backgroundColor: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-xs)',
            padding: '4px 8px',
            fontSize: '9px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--color-accent-teal)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--color-accent-teal)' }} />
          <span>VISUALIZATION DERIVATIVE · SAR S-1 σ° GEOREFERENCED</span>
        </div>
      )}

      {/* Navigation Controls */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
          backgroundColor: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-xs)',
          padding: '2px',
          boxShadow: 'var(--shadow-md)',
          backdropFilter: 'blur(6px)',
        }}
      >
        <button
          onClick={handleResetNorth}
          style={{
            width: '28px',
            height: '28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-accent-teal)',
            cursor: 'pointer',
          }}
          title="Reset True North (000°)"
        >
          <Compass size={16} />
        </button>
        <div style={{ height: '1px', backgroundColor: 'var(--color-border-subtle)' }} />
        <button
          onClick={handleZoomIn}
          style={{
            width: '28px',
            height: '28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
          }}
          title="Zoom In (+)"
        >
          <ZoomIn size={15} />
        </button>
        <button
          onClick={handleZoomOut}
          style={{
            width: '28px',
            height: '28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
          }}
          title="Zoom Out (-)"
        >
          <ZoomOut size={15} />
        </button>
      </div>

      {/* Dedicated Counterfactual Legend Overlay */}
      {activeWorkspace === 'evidence' && (
        <div
          style={{
            position: 'absolute',
            bottom: '48px',
            left: '16px',
            zIndex: 15,
            backgroundColor: 'rgba(16, 35, 38, 0.94)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-xs)',
            padding: '10px 14px',
            boxShadow: 'var(--shadow-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            minWidth: '240px',
            backdropFilter: 'blur(6px)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
            <span
              style={{
                fontSize: 'var(--text-2xs)',
                fontWeight: 700,
                color: 'var(--color-accent-seafoam)',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            >
              Counterfactual Map Legend
            </span>
            {activeComparison && (
              <button
                onClick={() => {
                  const pLat = activeComparison.predicted_centroid_lat;
                  const pLon = activeComparison.predicted_centroid_lon;
                  if (mapRef.current && pLat && pLon) {
                    mapRef.current.flyTo({ center: [pLon, pLat], zoom: 12.5, duration: 800 });
                  }
                }}
                style={{
                  fontSize: '9px',
                  color: 'var(--color-accent-teal)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px',
                }}
                title="Focus on Simulation Plume"
              >
                <Target size={11} />
                Focus
              </button>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
            <div style={{ width: '12px', height: '12px', backgroundColor: 'rgba(209, 178, 124, 0.6)', border: '1.5px solid var(--color-text-primary)', borderRadius: '2px' }} />
            <span>Observed SAR Slick ({activeComparison?.observed_slick_id || 'CS_0035'})</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
            <div style={{ width: '8px', height: '8px', backgroundColor: '#78AFA5', borderRadius: '50%' }} />
            <span>Simulated Particle Plume ({simulationDetail?.particles?.length ?? 500} pts)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
            <div style={{ width: '10px', height: '10px', backgroundColor: '#B86F52', border: '1.5px solid #ffffff', borderRadius: '2px', transform: 'rotate(45deg)' }} />
            <span>Hypothesis Release Point (T₀)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
            <div style={{ width: '16px', height: '2px', backgroundColor: '#5F918A' }} />
            <span>Forward Drift Trajectory</span>
          </div>
          {activeComparison?.centroid_error_m != null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--text-2xs)', color: 'var(--color-text-secondary)' }}>
              <div style={{ width: '16px', height: '2px', backgroundColor: '#B86F52' }} />
              <span>Centroid Error: <strong className="font-mono" style={{ color: 'var(--color-text-primary)' }}>{activeComparison.centroid_error_m.toFixed(1)} m</strong></span>
            </div>
          )}
        </div>
      )}

      {/* Telemetry Footer */}
      <div
        style={{
          position: 'absolute',
          bottom: '12px',
          left: '16px',
          zIndex: 10,
          backgroundColor: 'rgba(10, 13, 19, 0.90)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-xs)',
          padding: '5px 10px',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          fontSize: 'var(--text-2xs)',
          color: 'var(--color-text-muted)',
        }}
      >
        <span>
          DATUM: <strong style={{ color: 'var(--color-text-secondary)' }}>WGS84</strong>
        </span>
        <span>
          PROJECTION: <strong style={{ color: 'var(--color-text-secondary)' }}>EPSG:4326</strong>
        </span>
        <span>
          BASEMAP: <strong style={{ color: 'var(--color-text-secondary)' }}>ESRI DARK CANVAS</strong>
        </span>
        <span>
          ACTIVE CASE:{' '}
          <strong style={{ color: 'var(--color-accent-blue)', fontFamily: 'var(--font-mono)' }}>
            {activeCaseId}
          </strong>
        </span>
      </div>

      {/* Interactive Feature Inspection Popup Card */}
      {selectedFeature && (
        <div
          style={{
            position: 'absolute',
            bottom: '48px',
            left: '16px',
            zIndex: 20,
            width: '320px',
            maxHeight: '240px',
            backgroundColor: 'rgba(13, 17, 23, 0.95)',
            border: '1px solid var(--color-border-strong)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px',
            boxShadow: 'var(--shadow-lg)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            backdropFilter: 'blur(4px)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span
              style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 700,
                color: 'var(--color-text-primary)',
              }}
            >
              {selectedFeature.title}
            </span>
            <button
              onClick={() => setSelectedFeature(null)}
              style={{ color: 'var(--color-text-muted)', cursor: 'pointer' }}
            >
              <X size={14} />
            </button>
          </div>

          <div
            className="font-mono"
            style={{
              overflowY: 'auto',
              fontSize: '10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '3px',
              color: 'var(--color-text-monospace)',
            }}
          >
            {Object.entries(selectedFeature.properties).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>{k}:</span>
                <span style={{ color: 'var(--color-text-primary)', textAlign: 'right' }}>
                  {typeof v === 'number' ? v.toFixed(4) : String(v)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
