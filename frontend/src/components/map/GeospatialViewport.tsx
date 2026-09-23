import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as maplibregl from 'maplibre-gl';
import { MapboxOverlay } from '@deck.gl/mapbox';
import { GeoJsonLayer } from '@deck.gl/layers';
import { useInvestigationStore } from '../../store/investigationStore';
import { useActiveCase } from '../../context/CaseContext';
import {
  useSarRasterQuery,
  useSlicksQuery,
  useAisTracksQuery,
  useDriftTrajectoriesQuery,
  useHypothesesQuery,
} from '../../api/casesApi';
import { MapLayerControls } from './MapLayerControls';
import { MapLegend } from './MapLegend';
import { ZoomIn, ZoomOut, Compass, X } from 'lucide-react';

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

  const { activeCaseId, activeCase } = useActiveCase();

  // Queries for real scientific geospatial artifacts
  const { data: sarRasterData } = useSarRasterQuery(activeCaseId);
  const { data: slicksData } = useSlicksQuery(activeCaseId);
  const { data: aisTracksData } = useAisTracksQuery(activeCaseId);
  const { data: driftData } = useDriftTrajectoriesQuery(activeCaseId);
  const { data: hypothesesData } = useHypothesesQuery(activeCaseId);

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
        visible: mapLayers.slickPolygons && Boolean(slicksData?.features?.length),
        pickable: true,
        filled: true,
        stroked: true,
        lineWidthUnits: 'pixels',
        getFillColor: [210, 153, 34, 150],
        getLineColor: [250, 190, 50, 255],
        getLineWidth: 2,
        lineWidthMinPixels: 1.5,
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

      // 4B. Backward Drift Trajectories
      new GeoJsonLayer({
        id: 'drift-trajectories-layer',
        data: (driftData as any) || [],
        visible: mapLayers.driftParticles && Boolean(driftData?.features?.length),
        pickable: true,
        stroked: true,
        filled: false,
        lineWidthUnits: 'pixels',
        getLineColor: [168, 85, 247, 180],
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

      // 4C. AIS Vessel Trajectories
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
          const isSelected = feat?.properties?.mmsi === selectedMmsi;
          return isSelected ? [56, 189, 248, 255] : [56, 139, 253, 200];
        },
        getLineWidth: (f: unknown) => {
          const feat = f as any;
          return feat?.properties?.mmsi === selectedMmsi ? 4.5 : 2;
        },
        lineWidthMinPixels: 1.5,
        updateTriggers: {
          getLineColor: [selectedMmsi],
          getLineWidth: [selectedMmsi],
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

      // 4D. Real-Time Drift Particles at currentTimeUtc
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
        getFillColor: [217, 70, 239, 230],
        getLineColor: [255, 255, 255, 220],
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

      // 4E. Real-Time Vessel Locations at currentTimeUtc
      new GeoJsonLayer({
        id: 'current-vessels-layer',
        data: (currentVesselsGeoJson as any) || [],
        visible: mapLayers.aisTracks && Boolean(currentVesselsGeoJson?.features?.length),
        pickable: true,
        pointType: 'circle',
        pointRadiusUnits: 'pixels',
        getPointRadius: (f: unknown) => {
          const feat = f as any;
          return feat?.properties?.mmsi === selectedMmsi ? 9 : 6;
        },
        pointRadiusMinPixels: 4,
        pointRadiusMaxPixels: 16,
        getFillColor: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.mmsi === selectedMmsi;
          return isSelected ? [56, 189, 248, 255] : [56, 139, 253, 235];
        },
        getLineColor: [255, 255, 255, 255],
        getLineWidth: 2,
        lineWidthUnits: 'pixels',
        updateTriggers: {
          getPointRadius: [selectedMmsi],
          getFillColor: [selectedMmsi],
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

      // 4F. 4D Source Hypothesis Locations
      new GeoJsonLayer({
        id: 'hypotheses-layer',
        data: (preprocessedHypotheses as any),
        visible: mapLayers.candidateMarkers && Boolean(preprocessedHypotheses?.features?.length),
        pickable: true,
        pointType: 'circle',
        pointRadiusUnits: 'pixels',
        getPointRadius: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.hypothesis_id === selectedHypothesisId;
          const releaseEpoch = feat?.properties?._releaseEpoch;
          const isProximate = releaseEpoch && Math.abs(releaseEpoch - currentEpoch) < 30 * 60 * 1000;
          return isSelected ? 9 : isProximate ? 7 : 4.5;
        },
        pointRadiusMinPixels: 3.5,
        pointRadiusMaxPixels: 16,
        getFillColor: (f: unknown) => {
          const feat = f as any;
          const isSelected = feat?.properties?.hypothesis_id === selectedHypothesisId;
          const releaseEpoch = feat?.properties?._releaseEpoch;
          const isProximate = releaseEpoch && Math.abs(releaseEpoch - currentEpoch) < 30 * 60 * 1000;
          return isSelected
            ? [248, 81, 73, 255]
            : isProximate
            ? [251, 146, 60, 240]
            : [248, 81, 73, 175];
        },
        getLineColor: [255, 255, 255, 230],
        getLineWidth: 1.2,
        lineWidthUnits: 'pixels',
        updateTriggers: {
          getPointRadius: [selectedHypothesisId, currentEpoch],
          getFillColor: [selectedHypothesisId, currentEpoch],
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
        backgroundColor: '#070b12',
        overflow: 'hidden',
      }}
    >
      {/* MapLibre WebGL Canvas Container */}
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Layer Visibility Toggles */}
      <MapLayerControls />

      {/* Map Legend */}
      <MapLegend />

      {/* SAR Derivative Metadata Indicator */}
      {sarRasterData && mapLayers.sarRaster && (
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '200px',
            zIndex: 10,
            backgroundColor: 'rgba(10, 13, 19, 0.90)',
            border: '1px solid rgba(56, 139, 253, 0.4)',
            borderRadius: 'var(--radius-xs)',
            padding: '4px 8px',
            fontSize: '9px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--color-accent-blue)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#388bfd' }} />
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
          gap: '4px',
          backgroundColor: 'rgba(17, 22, 32, 0.92)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px',
          boxShadow: 'var(--shadow-md)',
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
            color: 'var(--color-accent-blue)',
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
