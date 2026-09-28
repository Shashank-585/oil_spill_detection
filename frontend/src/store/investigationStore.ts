import { create } from 'zustand';
import { getStageForWorkspace, INVESTIGATION_STAGES, type InvestigationStage } from '../types/workflow';

export type WorkspaceView =
  | 'overview'
  | 'sar'
  | 'ais'
  | 'drift'
  | 'candidates'
  | 'evidence'
  | 'uncertainty'
  | 'audit'
  | 'alerts';

export interface MapLayerVisibility {
  sarRaster: boolean;
  slickPolygons: boolean;
  aisTracks: boolean;
  driftParticles: boolean;
  candidateMarkers: boolean;
  incidentPoint: boolean;
  satelliteFootprint: boolean;
}

interface InvestigationState {
  // Case context
  activeCaseId: string;
  activeStage: InvestigationStage;
  activeWorkspace: WorkspaceView;
  causalConsistencyEnabled: boolean;

  // Selected entities
  selectedMmsi: number | null;
  selectedHypothesisId: string | null;

  // Temporal navigation
  currentTimeUtc: string;

  // Historical Replay Mode
  isReplayMode: boolean;
  isPlaying: boolean;
  playbackSpeed: number; // 0.5, 1, 2, 5, 10

  // Layout & Visibility
  inspectorOpen: boolean;
  focusSelectedHypothesis: boolean;
  mapLayers: MapLayerVisibility;

  // Actions
  setActiveCaseId: (caseId: string) => void;
  setActiveStage: (stage: InvestigationStage) => void;
  setActiveWorkspace: (workspace: WorkspaceView) => void;
  setCausalConsistencyEnabled: (enabled: boolean) => void;
  setSelectedMmsi: (mmsi: number | null) => void;
  setSelectedHypothesisId: (hypId: string | null) => void;
  setCurrentTimeUtc: (timeUtc: string) => void;
  setReplayMode: (active: boolean) => void;
  setIsPlaying: (playing: boolean) => void;
  togglePlayPause: () => void;
  setPlaybackSpeed: (speed: number) => void;
  toggleInspector: () => void;
  setFocusSelectedHypothesis: (focus: boolean) => void;
  setMapLayerVisibility: (layer: keyof MapLayerVisibility, visible: boolean) => void;
  nextStage: () => void;
  prevStage: () => void;
}

export const useInvestigationStore = create<InvestigationState>((set, get) => ({
  activeCaseId: 'case_003_golden_ray',
  activeStage: 'observe',
  activeWorkspace: 'overview',
  causalConsistencyEnabled: true,

  selectedMmsi: null,
  selectedHypothesisId: null,

  currentTimeUtc: '2019-09-08T05:46:00Z',

  isReplayMode: false,
  isPlaying: false,
  playbackSpeed: 1.0,

  inspectorOpen: true,
  focusSelectedHypothesis: true,
  mapLayers: {
    sarRaster: true,
    slickPolygons: true,
    aisTracks: true,
    driftParticles: true,
    candidateMarkers: true,
    incidentPoint: true,
    satelliteFootprint: true,
  },

  setActiveCaseId: (caseId) =>
    set({
      activeCaseId: caseId,
      selectedMmsi: null,
      selectedHypothesisId: null,
      activeStage: 'observe',
      activeWorkspace: 'overview',
    }),

  setActiveStage: (stage) => {
    const stageDef = INVESTIGATION_STAGES.find((s) => s.id === stage);
    const targetWorkspace = stageDef ? stageDef.defaultWorkspace : 'overview';

    // Auto-configure optimal map layers per stage without hiding key context
    let layerConfig: Partial<MapLayerVisibility> = {};
    if (stage === 'observe') {
      layerConfig = {
        sarRaster: true,
        slickPolygons: true,
        aisTracks: true,
        driftParticles: false,
        candidateMarkers: false,
      };
    } else if (stage === 'investigate') {
      layerConfig = {
        sarRaster: false,
        slickPolygons: true,
        aisTracks: false,
        driftParticles: true,
        candidateMarkers: true,
      };
    } else if (stage === 'attribute') {
      layerConfig = {
        sarRaster: false,
        slickPolygons: true,
        aisTracks: true,
        driftParticles: true,
        candidateMarkers: true,
      };
    } else if (stage === 'report') {
      layerConfig = {
        sarRaster: true,
        slickPolygons: true,
        aisTracks: true,
        driftParticles: true,
        candidateMarkers: true,
      };
    }

    set((state) => ({
      activeStage: stage,
      activeWorkspace: targetWorkspace,
      mapLayers: { ...state.mapLayers, ...layerConfig },
    }));
  },

  setActiveWorkspace: (workspace) => {
    const inferredStage = getStageForWorkspace(workspace);
    set({
      activeWorkspace: workspace,
      activeStage: inferredStage,
    });
  },

  nextStage: () => {
    const { activeStage, setActiveStage } = get();
    const order: InvestigationStage[] = ['observe', 'investigate', 'attribute', 'report'];
    const idx = order.indexOf(activeStage);
    if (idx < order.length - 1) {
      setActiveStage(order[idx + 1]);
    }
  },

  prevStage: () => {
    const { activeStage, setActiveStage } = get();
    const order: InvestigationStage[] = ['observe', 'investigate', 'attribute', 'report'];
    const idx = order.indexOf(activeStage);
    if (idx > 0) {
      setActiveStage(order[idx - 1]);
    }
  },

  setCausalConsistencyEnabled: (enabled) => set({ causalConsistencyEnabled: enabled }),
  setSelectedMmsi: (mmsi) => set({ selectedMmsi: mmsi }),
  setSelectedHypothesisId: (hypId) => set({ selectedHypothesisId: hypId }),
  setCurrentTimeUtc: (timeUtc) => set({ currentTimeUtc: timeUtc }),
  setReplayMode: (active) => set({ isReplayMode: active, isPlaying: active ? get().isPlaying : false }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  togglePlayPause: () => set((state) => ({ isPlaying: !state.isPlaying })),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),
  toggleInspector: () => set((state) => ({ inspectorOpen: !state.inspectorOpen })),
  setFocusSelectedHypothesis: (focus) => set({ focusSelectedHypothesis: focus }),
  setMapLayerVisibility: (layer, visible) =>
    set((state) => ({
      mapLayers: { ...state.mapLayers, [layer]: visible },
    })),
}));
