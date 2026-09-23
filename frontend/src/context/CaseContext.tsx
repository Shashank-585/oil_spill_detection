/**
 * frontend/src/context/CaseContext.tsx
 *
 * Central case context providing active case metadata, dataset availability,
 * and attribution queries across all investigation workspaces without prop drilling.
 */

import React, { createContext, useContext } from 'react';
import { useInvestigationStore } from '../store/investigationStore';
import {
  useCasesQuery,
  useCaseDetailQuery,
  useAttributionRankingQuery,
  type CaseSummaryItem,
  type CaseDetailResponse,
  type VesselAttributionItem,
} from '../api/casesApi';
import { ApiError } from '../api/apiClient';

interface CaseContextValue {
  // Case identifiers & listing
  activeCaseId: string;
  setActiveCaseId: (id: string) => void;
  cases: CaseSummaryItem[];
  isLoadingCases: boolean;
  casesError: ApiError | Error | null;

  // Active case detail
  activeCase: CaseDetailResponse | undefined;
  isLoadingCaseDetail: boolean;
  caseDetailError: ApiError | Error | null;

  // Dataset availability
  hasSar: boolean;
  hasSlicks: boolean;
  hasAis: boolean;
  hasAttribution: boolean;
  hasUncertainty: boolean;

  // Attribution summary
  attributionRanking: VesselAttributionItem[] | undefined;
  isLoadingAttribution: boolean;
  attributionError: ApiError | Error | null;
  isAttributionUnavailable: boolean;
  topCandidate: VesselAttributionItem | undefined;
  candidateCount: number;
}

const CaseContext = createContext<CaseContextValue | null>(null);

export const CaseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const activeCaseId = useInvestigationStore((s) => s.activeCaseId);
  const setActiveCaseId = useInvestigationStore((s) => s.setActiveCaseId);

  // 1. Fetch available cases catalog
  const {
    data: cases = [],
    isLoading: isLoadingCases,
    error: casesError,
  } = useCasesQuery();

  // If initial activeCaseId is not in discovered cases list, default to first available
  React.useEffect(() => {
    if (cases.length > 0 && !cases.some((c) => c.case_id === activeCaseId)) {
      setActiveCaseId(cases[0].case_id);
    }
  }, [cases, activeCaseId, setActiveCaseId]);

  // 2. Fetch active case details
  const {
    data: activeCase,
    isLoading: isLoadingCaseDetail,
    error: caseDetailError,
  } = useCaseDetailQuery(activeCaseId);

  // 3. Fetch attribution ranking (only if case indicates attribution exists or attempt query)
  const shouldFetchAttribution = Boolean(activeCase?.datasets?.attribution ?? true);
  const {
    data: attributionRanking,
    isLoading: isLoadingAttribution,
    error: attributionError,
  } = useAttributionRankingQuery(activeCaseId, shouldFetchAttribution);

  const isAttributionUnavailable =
    Boolean(activeCase && !activeCase.datasets?.attribution) ||
    (attributionError instanceof ApiError && attributionError.errorCode === 'DATASET_NOT_AVAILABLE');

  const topCandidate = attributionRanking && attributionRanking.length > 0 ? attributionRanking[0] : undefined;
  const candidateCount = attributionRanking ? attributionRanking.length : 0;

  const value: CaseContextValue = {
    activeCaseId,
    setActiveCaseId,
    cases,
    isLoadingCases,
    casesError: (casesError as ApiError | Error) || null,

    activeCase,
    isLoadingCaseDetail,
    caseDetailError: (caseDetailError as ApiError | Error) || null,

    hasSar: Boolean(activeCase?.datasets?.sar),
    hasSlicks: Boolean(activeCase?.datasets?.slicks),
    hasAis: Boolean(activeCase?.datasets?.ais),
    hasAttribution: Boolean(activeCase?.datasets?.attribution),
    hasUncertainty: Boolean(activeCase?.datasets?.uncertainty),

    attributionRanking,
    isLoadingAttribution,
    attributionError: (attributionError as ApiError | Error) || null,
    isAttributionUnavailable,
    topCandidate,
    candidateCount,
  };

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
};

export function useActiveCase(): CaseContextValue {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error('useActiveCase must be used within a CaseProvider');
  }
  return context;
}
