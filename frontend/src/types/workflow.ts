/**
 * frontend/src/types/workflow.ts
 *
 * SIH26143 — Marine Oil Spill Attribution Decision-Support System
 * Phase 19 Investigation Workflow Stage Definitions:
 * OBSERVE → INVESTIGATE → ATTRIBUTE → REPORT
 */

import type { WorkspaceView } from '../store/investigationStore';

export type InvestigationStage = 'observe' | 'investigate' | 'attribute' | 'report';

export interface StageDefinition {
  id: InvestigationStage;
  stageNumber: string;
  name: string;
  tagline: string;
  purpose: string;
  defaultWorkspace: WorkspaceView;
  associatedWorkspaces: WorkspaceView[];
}

export const INVESTIGATION_STAGES: StageDefinition[] = [
  {
    id: 'observe',
    stageNumber: '01',
    name: 'OBSERVE',
    tagline: 'Satellite & Maritime Baseline',
    purpose: 'Establish what the satellite radar observation, slick geometry, and environmental data show.',
    defaultWorkspace: 'overview',
    associatedWorkspaces: ['overview', 'sar', 'ais'],
  },
  {
    id: 'investigate',
    stageNumber: '02',
    name: 'INVESTIGATE',
    tagline: 'Backward Source Reconstruction',
    purpose: 'Determine where and when the spill could have originated using Lagrangian hindcasts.',
    defaultWorkspace: 'drift',
    associatedWorkspaces: ['drift'],
  },
  {
    id: 'attribute',
    stageNumber: '03',
    name: 'ATTRIBUTE',
    tagline: 'Candidate Causal Evidence',
    purpose: 'Evaluate vessel hypotheses with counterfactual forward drift and causal consistency.',
    defaultWorkspace: 'candidates',
    associatedWorkspaces: ['candidates', 'evidence', 'uncertainty'],
  },
  {
    id: 'report',
    stageNumber: '04',
    name: 'REPORT',
    tagline: 'Forensic Findings & Provenance',
    purpose: 'Produce an investigator-facing summary with evidence breakdown, limitations, and court-admissible exports.',
    defaultWorkspace: 'audit',
    associatedWorkspaces: ['audit'],
  },
];

export function getStageForWorkspace(workspace: WorkspaceView): InvestigationStage {
  switch (workspace) {
    case 'sar':
    case 'ais':
    case 'overview':
      return 'observe';
    case 'drift':
      return 'investigate';
    case 'candidates':
    case 'evidence':
    case 'uncertainty':
      return 'attribute';
    case 'audit':
      return 'report';
    default:
      return 'observe';
  }
}
