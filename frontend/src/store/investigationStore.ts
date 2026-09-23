import { create } from 'zustand';

export type WorkspaceView =
  | 'overview'
  | 'sar'
  | 'ais'
  | 'drift'
  | 'candidates'
  | 'evidence'
  | 'uncertainty'
  | 'audit';

export interface MapLayerVisibility {
  sarRaster: boolean;
  slickPolygons: boolean;
  aisTracks: boolean;
  driftParticles: boolean;
  candidateMarkers: boolean;
}

interface InvestigationState {
  // Case context
  activeCaseId: string;
  activeWorkspace: WorkspaceView;
  causalConsistencyEnabled: boolean;

  // Selected entities
  selectedMmsi: number | null;
  selectedHypothesisId: string | null;

  // Temporal navigation
  currentTimeUtc: string;

  // Layout & Visibility
  inspectorOpen: boolean;
  mapLayers: MapLayerVisibility;

  // Actions
  setActiveCaseId: (caseId: string) => void;
  setActiveWorkspace: (workspace: WorkspaceView) => void;
  setCausalConsistencyEnabled: (enabled: boolean) => void;
  setSelectedMmsi: (mmsi: number | null) => void;
  setSelectedHypothesisId: (hypId: string | null) => void;
  setCurrentTimeUtc: (timeUtc: string) => void;
  toggleInspector: () => void;
  setMapLayerVisibility: (layer: keyof MapLayerVisibility, visible: boolean) => void;
}

export const useInvestigationStore = create<InvestigationState>((set) => ({
  activeCaseId: 'case_003_golden_ray',
  activeWorkspace: 'overview',
  causalConsistencyEnabled: true,

  selectedMmsi: null,
  selectedHypothesisId: null,

  currentTimeUtc: '2019-09-08T05:46:00Z',

  inspectorOpen: true,
  mapLayers: {
    sarRaster: true,
    slickPolygons: true,
    aisTracks: true,
    driftParticles: true,
    candidateMarkers: true,
  },

  setActiveCaseId: (caseId) => set({ activeCaseId: caseId, selectedMmsi: null, selectedHypothesisId: null }),
  setActiveWorkspace: (workspace) => set({ activeWorkspace: workspace }),
  setCausalConsistencyEnabled: (enabled) => set({ causalConsistencyEnabled: enabled }),
  setSelectedMmsi: (mmsi) => set({ selectedMmsi: mmsi }),
  setSelectedHypothesisId: (hypId) => set({ selectedHypothesisId: hypId }),
  setCurrentTimeUtc: (timeUtc) => set({ currentTimeUtc: timeUtc }),
  toggleInspector: () => set((state) => ({ inspectorOpen: !state.inspectorOpen })),
  setMapLayerVisibility: (layer, visible) =>
    set((state) => ({
      mapLayers: { ...state.mapLayers, [layer]: visible },
    })),
}));
