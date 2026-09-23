"""
Attribution, 4D Source Hypothesis Generation, and Forward Counterfactual Simulation.
"""

from src.attribution.hypothesis_generator import SourceHypothesisGenerator4D
from src.attribution.forward_simulator import ForwardCounterfactualSimulator
from src.attribution.spill_comparator import SpillComparator
from src.attribution.attribution_engine import AttributionEngine
from src.attribution.uncertainty_analyzer import UncertaintyAnalyzer
from src.attribution.causal_consistency import (
    CausalPrecedenceStatus,
    SourceAgePlausibility,
    CausalPrecedenceResult,
    SourceAgePlausibilityResult,
    determine_temporal_precedence,
    evaluate_source_age_plausibility,
)

__all__ = [
    "SourceHypothesisGenerator4D",
    "ForwardCounterfactualSimulator",
    "SpillComparator",
    "AttributionEngine",
    "UncertaintyAnalyzer",
    "CausalPrecedenceStatus",
    "SourceAgePlausibility",
    "CausalPrecedenceResult",
    "SourceAgePlausibilityResult",
    "determine_temporal_precedence",
    "evaluate_source_age_plausibility",
]


