"""
Unit and integration tests for Phase 9: Explainable Multi-Evidence Attribution Engine.
Validates:
- Evidence mapping and calculation (source, space, time, drift, AIS quality)
- Weight normalization and linear combination
- Conflict detection and explanation synthesis
- Evidence quality states (HIGH_SUPPORT, MODERATE_SUPPORT, LOW_SUPPORT, INSUFFICIENT_EVIDENCE)
- Hypothesis ranking and vessel-level aggregation
- Deterministic reproducibility
- Synthetic known correct vs weak candidate separation
- Case 001 real data attribution output integrity
"""

import math
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.attribution.attribution_engine import (
    AttributionEngine,
    EvidenceQualityState,
    HypothesisEvidence,
    VesselSummary,
)


@pytest.fixture
def engine():
    return AttributionEngine("case_001")


def test_source_evidence_mapping(engine):
    """Test source plausibility mapping into [0, 1] bounds."""
    # Test valid normal value
    score = engine.compute_source_evidence({"source_plausibility": 0.85})
    assert 0.0 <= score <= 1.0
    assert pytest.approx(score) == 0.85

    # Test clamping on out-of-range inputs
    assert engine.compute_source_evidence({"source_plausibility": 1.5}) == 1.0
    assert engine.compute_source_evidence({"source_plausibility": -0.2}) == 0.0

    # Test fallback on missing or NaN
    assert engine.compute_source_evidence({}) == 0.5
    assert engine.compute_source_evidence({"source_plausibility": float("nan")}) == 0.5


def test_spatial_evidence_calculation(engine):
    """Test spatial compatibility exponential decay exp(-d / R_s)."""
    # At d = 0, score = 1.0
    score_0 = engine.compute_spatial_evidence({"geodesic_distance_m": 0.0})
    assert pytest.approx(score_0) == 1.0

    # At d = 5000 m (R_s), score = exp(-1) ≈ 0.367879
    score_5k = engine.compute_spatial_evidence({"geodesic_distance_m": 5000.0})
    assert pytest.approx(score_5k, abs=1e-4) == math.exp(-1.0)

    # Monotonic decrease: greater distance yields lower score
    score_10k = engine.compute_spatial_evidence({"geodesic_distance_m": 10000.0})
    assert score_10k < score_5k
    assert 0.0 <= score_10k <= 1.0

    # Fallback on negative or NaN
    assert engine.compute_spatial_evidence({"geodesic_distance_m": -100.0}) == 0.0
    assert engine.compute_spatial_evidence({}) == 0.0


def test_temporal_evidence_calculation(engine):
    """Test temporal compatibility exponential decay exp(-dt / T_s)."""
    # At dt = 0, score = 1.0
    score_0 = engine.compute_temporal_evidence({"time_gap_seconds": 0.0})
    assert pytest.approx(score_0) == 1.0

    # At dt = 600 s (T_s), score = exp(-1) ≈ 0.367879
    score_600 = engine.compute_temporal_evidence({"time_gap_seconds": 600.0})
    assert pytest.approx(score_600, abs=1e-4) == math.exp(-1.0)

    # Monotonic decrease
    score_1800 = engine.compute_temporal_evidence({"time_gap_seconds": 1800.0})
    assert score_1800 < score_600
    assert 0.0 <= score_1800 <= 1.0


def test_drift_evidence_aggregation(engine):
    """Test multi-metric physical drift consistency aggregation."""
    # Perfect simulation match: 0 m centroid error, 0 m particle distance, 1.0 coverage, 1.0 IoU
    perfect_match = {
        "centroid_error_m": 0.0,
        "mean_particle_distance_m": 0.0,
        "coverage_ratio": 1.0,
        "iou": 1.0,
    }
    score_perf = engine.compute_drift_evidence(perfect_match)
    assert pytest.approx(score_perf, abs=1e-3) == 1.0

    # Poor simulation match: large errors, 0 overlap
    poor_match = {
        "centroid_error_m": 20000.0,
        "mean_particle_distance_m": 20000.0,
        "coverage_ratio": 0.0,
        "iou": 0.0,
    }
    score_poor = engine.compute_drift_evidence(poor_match)
    assert score_poor < 0.05

    # Intermediate realistic match
    real_match = {
        "centroid_error_m": 136.2,
        "mean_particle_distance_m": 350.0,
        "coverage_ratio": 0.65,
        "iou": 0.30,
    }
    score_real = engine.compute_drift_evidence(real_match)
    assert 0.6 < score_real < 0.9


def test_ais_quality_evidence(engine):
    """Test AIS track quality mapping across observational conditions."""
    assert engine.compute_ais_quality_evidence({"track_quality": "HIGH"}) == 1.0
    assert engine.compute_ais_quality_evidence({"track_quality": "GOOD"}) == 0.85
    assert engine.compute_ais_quality_evidence({"track_quality": "MODERATE"}) == 0.70
    assert engine.compute_ais_quality_evidence({"track_quality": "INTERPOLATED"}) == 0.50
    assert engine.compute_ais_quality_evidence({"track_quality": "POOR"}) == 0.30
    assert engine.compute_ais_quality_evidence({"track_quality": "UNKNOWN"}) == 0.50


def test_evidence_vector_schema(engine):
    """Test that all evidence components produce valid [0, 1] finite scores."""
    hypo = {
        "source_plausibility": 0.72,
        "geodesic_distance_m": 1250.0,
        "time_gap_seconds": 120.0,
        "track_quality": "HIGH",
    }
    comp = {
        "centroid_error_m": 150.0,
        "mean_particle_distance_m": 280.0,
        "coverage_ratio": 0.70,
        "iou": 0.45,
    }
    s_drift = engine.compute_drift_evidence(comp)
    s_space = engine.compute_spatial_evidence(hypo)
    s_source = engine.compute_source_evidence(hypo)
    s_time = engine.compute_temporal_evidence(hypo)
    s_ais = engine.compute_ais_quality_evidence(hypo)

    for name, s in [
        ("s_drift", s_drift),
        ("s_space", s_space),
        ("s_source", s_source),
        ("s_time", s_time),
        ("s_ais", s_ais),
    ]:
        assert isinstance(s, float)
        assert not math.isnan(s)
        assert 0.0 <= s <= 1.0, f"{name} out of bounds: {s}"


def test_weight_normalization(engine):
    """Test that evidence weights sum to 1.0."""
    total_w = sum(engine.weights.values())
    assert pytest.approx(total_w, abs=1e-5) == 1.0

    # Test error raised if weights do not sum to 1.0
    bad_weights = {"w_drift": 0.5, "w_space": 0.5, "w_source": 0.5, "w_time": 0.1, "w_ais": 0.1}
    with pytest.raises(ValueError, match="Evidence weights must sum to 1.0"):
        engine.compute_combined_score(0.8, 0.8, 0.8, 0.8, 0.8, custom_weights=bad_weights)


def test_combined_score_calculation(engine):
    """Test weighted linear combination of evidence components."""
    # Equal 0.5 across all components gives 0.5
    score = engine.compute_combined_score(0.5, 0.5, 0.5, 0.5, 0.5)
    assert pytest.approx(score) == 0.5

    # All 1.0 gives 1.0
    assert pytest.approx(engine.compute_combined_score(1.0, 1.0, 1.0, 1.0, 1.0)) == 1.0

    # Custom calculation check with weights: 0.30, 0.25, 0.20, 0.15, 0.10
    # 0.3*0.8 + 0.25*0.6 + 0.2*0.7 + 0.15*0.9 + 0.10*0.5
    # = 0.24 + 0.15 + 0.14 + 0.135 + 0.05 = 0.715
    res = engine.compute_combined_score(0.8, 0.6, 0.7, 0.9, 0.5)
    assert pytest.approx(res, abs=1e-5) == 0.715


def test_conflicting_evidence_preservation(engine):
    """Test that divergence between evidence categories is explicitly flagged and described."""
    # Scenario: high drift consistency (0.85) but vessel was far away (space: 0.15)
    hypo = {"geodesic_distance_m": 9500.0, "time_gap_seconds": 100.0}
    comp = {}
    conflict = engine.detect_conflicts(
        s_drift=0.85,
        s_space=0.15,
        s_source=0.60,
        s_time=0.85,
        s_ais=0.70,
        hypo=hypo,
        comp=comp,
    )
    assert conflict is not None
    assert "Physical drift model strongly matches" in conflict
    assert "9.5 km away" in conflict


def test_insufficient_evidence_state(engine):
    """Test evidence quality state classification."""
    # High support: overall >= 0.75, s_drift >= 0.65, s_space >= 0.65
    assert engine.classify_evidence_state(0.80, 0.75, 0.70, 0.80, 0.85, 0.70) == EvidenceQualityState.HIGH_SUPPORT

    # Moderate support
    assert engine.classify_evidence_state(0.60, 0.75, 0.35, 0.60, 0.80, 0.70) == EvidenceQualityState.MODERATE_SUPPORT

    # Low support
    assert engine.classify_evidence_state(0.40, 0.40, 0.30, 0.40, 0.50, 0.50) == EvidenceQualityState.LOW_SUPPORT

    # Insufficient evidence: very low score or poor data
    assert engine.classify_evidence_state(0.20, 0.10, 0.10, 0.20, 0.20, 0.20) == EvidenceQualityState.INSUFFICIENT_EVIDENCE
    assert engine.classify_evidence_state(0.50, 0.50, 0.50, 0.50, 0.50, 0.20) == EvidenceQualityState.INSUFFICIENT_EVIDENCE


def test_hypothesis_ranking(engine):
    """Test that evaluate_all produces hypotheses strictly sorted in descending score order."""
    hypotheses, _ = engine.evaluate_all()
    assert len(hypotheses) > 0

    scores = [h.attribution_evidence_score for h in hypotheses]
    assert scores == sorted(scores, reverse=True)
    assert all(h.rank == i + 1 for i, h in enumerate(hypotheses))


def test_vessel_level_aggregation(engine):
    """Test vessel-level rollup preserves best score, hypothesis count, and correct ranking."""
    hypotheses, vessel_summaries = engine.evaluate_all()
    assert len(vessel_summaries) > 0

    # Ensure vessel summaries are sorted descending by best_evidence_score
    v_scores = [v.best_evidence_score for v in vessel_summaries]
    assert v_scores == sorted(v_scores, reverse=True)

    # Validate each vessel summary against its constituent hypotheses
    for v in vessel_summaries:
        v_hypos = [h for h in hypotheses if h.mmsi == v.mmsi]
        assert len(v_hypos) == v.hypothesis_count
        assert pytest.approx(v.best_evidence_score) == max(h.attribution_evidence_score for h in v_hypos)
        assert pytest.approx(v.mean_evidence_score, abs=1e-3) == float(np.mean([h.attribution_evidence_score for h in v_hypos]))
        assert v.best_hypothesis_id in [h.hypothesis_id for h in v_hypos]


def test_deterministic_reproducibility(engine):
    """Test that repeated runs produce bitwise identical scores and rankings."""
    h1, v1 = engine.evaluate_all()
    h2, v2 = engine.evaluate_all()

    assert len(h1) == len(h2)
    assert len(v1) == len(v2)

    for a, b in zip(h1, h2):
        assert a.hypothesis_id == b.hypothesis_id
        assert a.rank == b.rank
        assert pytest.approx(a.attribution_evidence_score) == b.attribution_evidence_score
        assert pytest.approx(a.s_drift) == b.s_drift
        assert pytest.approx(a.s_space) == b.s_space

    for a, b in zip(v1, v2):
        assert a.mmsi == b.mmsi
        assert pytest.approx(a.best_evidence_score) == b.best_evidence_score


def test_synthetic_correct_outranks_weak(engine):
    """Test that a synthetic hypothesis with strong spatiotemporal and drift agreement outranks a weak/distant one."""
    # Synthetic candidate A: Close vessel, perfectly aligned time, high drift match
    hypo_a = {
        "hypothesis_id": "SYN_A",
        "mmsi": 111111111,
        "vessel_name": "SYNTHETIC_ALPHA",
        "observed_slick_id": "CS_SYN",
        "geodesic_distance_m": 450.0,      # 450 m close
        "time_gap_seconds": 60.0,          # 1 min gap
        "source_plausibility": 0.80,
        "track_quality": "HIGH",
        "estimated_release_lon": -118.1,
        "estimated_release_lat": 33.7,
        "estimated_release_time_utc": "2021-10-02T01:00:00Z",
    }
    comp_a = {
        "centroid_error_m": 85.0,
        "mean_particle_distance_m": 150.0,
        "coverage_ratio": 0.85,
        "iou": 0.55,
    }

    # Synthetic candidate B: Distant vessel, large time gap, poor drift match
    hypo_b = {
        "hypothesis_id": "SYN_B",
        "mmsi": 222222222,
        "vessel_name": "SYNTHETIC_BETA",
        "observed_slick_id": "CS_SYN",
        "geodesic_distance_m": 18500.0,    # 18.5 km far
        "time_gap_seconds": 3600.0,        # 1 hour gap
        "source_plausibility": 0.40,
        "track_quality": "POOR",
        "estimated_release_lon": -118.1,
        "estimated_release_lat": 33.7,
        "estimated_release_time_utc": "2021-10-02T01:00:00Z",
    }
    comp_b = {
        "centroid_error_m": 12000.0,
        "mean_particle_distance_m": 14000.0,
        "coverage_ratio": 0.05,
        "iou": 0.01,
    }

    score_a = engine.compute_combined_score(
        s_drift=engine.compute_drift_evidence(comp_a),
        s_space=engine.compute_spatial_evidence(hypo_a),
        s_source=engine.compute_source_evidence(hypo_a),
        s_time=engine.compute_temporal_evidence(hypo_a),
        s_ais=engine.compute_ais_quality_evidence(hypo_a),
    )

    score_b = engine.compute_combined_score(
        s_drift=engine.compute_drift_evidence(comp_b),
        s_space=engine.compute_spatial_evidence(hypo_b),
        s_source=engine.compute_source_evidence(hypo_b),
        s_time=engine.compute_temporal_evidence(hypo_b),
        s_ais=engine.compute_ais_quality_evidence(hypo_b),
    )

    assert score_a > 0.80
    assert score_b < 0.35
    assert score_a > score_b + 0.45


def test_case_001_attribution_output_integrity():
    """Test that Case 001 generated artifacts exist, are non-empty, and contain expected records."""
    h_csv = Path("data/processed/attribution/case_001_hypothesis_evidence.csv")
    h_json = Path("data/processed/attribution/case_001_hypothesis_evidence.json")
    v_csv = Path("data/processed/attribution/case_001_vessel_summary.csv")
    v_json = Path("data/processed/attribution/case_001_vessel_summary.json")
    rep = Path("data/processed/attribution/case_001_evidence_explanation_report.md")
    diag = Path("data/processed/attribution/case_001_attribution_diagnostic.png")

    assert h_csv.exists() and h_csv.stat().st_size > 500
    assert h_json.exists() and h_json.stat().st_size > 1000
    assert v_csv.exists() and v_csv.stat().st_size > 300
    assert v_json.exists() and v_json.stat().st_size > 500
    assert rep.exists() and rep.stat().st_size > 1000
    assert diag.exists() and diag.stat().st_size > 20000

    df_h = pd.read_csv(h_csv)
    df_v = pd.read_csv(v_csv)

    assert len(df_h) == 19
    assert len(df_v) == 10
    assert "attribution_evidence_score" in df_h.columns
    assert "evidence_quality_state" in df_h.columns
    assert "primary_strength" in df_h.columns
    assert "primary_weakness" in df_h.columns
    assert "best_evidence_score" in df_v.columns
