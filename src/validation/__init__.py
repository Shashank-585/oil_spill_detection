"""Phase 11 & Phase 12 — Historical Validation & Case Onboarding Framework."""

from src.validation.case_schema import (
    SourceType,
    GroundTruthQuality,
    CaseQualityLevel,
    ValidationEligibility,
    CaseStatus,
    ValidationRole,
    FailureCategory,
    GroundTruth,
    AlgorithmInputs,
    ValidationCase,
    CaseValidationMetrics,
    extract_blind_algorithm_inputs,
)
from src.validation.case_completeness import (
    CaseCompletenessEvaluator,
    CaseCompletenessRecord,
)
from src.validation.case_onboarding import CaseOnboardingWorkflow
from src.validation.case_registry import ValidationCaseRegistry
from src.validation.validation_runner import BlindValidationRunner
from src.validation.validation_aggregator import (
    ValidationAggregator,
    run_historical_validation,
)

__all__ = [
    "SourceType",
    "GroundTruthQuality",
    "CaseQualityLevel",
    "ValidationEligibility",
    "CaseStatus",
    "ValidationRole",
    "FailureCategory",
    "GroundTruth",
    "AlgorithmInputs",
    "ValidationCase",
    "CaseValidationMetrics",
    "extract_blind_algorithm_inputs",
    "CaseCompletenessEvaluator",
    "CaseCompletenessRecord",
    "CaseOnboardingWorkflow",
    "ValidationCaseRegistry",
    "BlindValidationRunner",
    "ValidationAggregator",
    "run_historical_validation",
]
