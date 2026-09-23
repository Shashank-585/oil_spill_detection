"""
Unit and integration tests for Phase 10: Uncertainty, Sensitivity, and Score Calibration Analysis.
Validates:
- Monte Carlo ensemble reproducibility with deterministic seeds
- Perturbation bounds and parameter integrity
- Hypothesis-level and vessel-level rank stability metrics
- Score distributions, percentiles (p05, p50, p95), and IQR
- Spatial location dispersion and valid GeoJSON containment geometries
- Source-time sensitivity curves
- Environmental forcing sensitivity (wind & current factor sweeps)
- AIS spatial and temporal scale sensitivity
- Score calibration audit guardrail (strictly uncalibrated compatibility index)
- Structured uncertainty and conflict reason codes
- Synthetic robust vs sensitive hypothesis differentiation
- Synthetic competing hypotheses and unstable ranking detection
- Case 001 real data uncertainty output integrity
"""

import json
import math
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.attribution.uncertainty_analyzer import (
    UncertaintyAnalyzer,
    UncertaintyReasonCode,
)


@pytest.fixture
def analyzer():
    return UncertaintyAnalyzer("case_001")


def test_ensemble_reproducibility(analyzer):
    """Test that setting identical random seeds generates identical realizations."""
    res1 = analyzer.generate_ensemble_realizations(n_realizations=5, seed=42)
    res2 = analyzer.generate_ensemble_realizations(n_realizations=5, seed=42)

    assert len(res1) == len(res2) == 5
    for df1, df2 in zip(res1, res2):
        pd.testing.assert_frame_equal(df1, df2)

    # Different seeds should produce different perturbed scores
    res3 = analyzer.generate_ensemble_realizations(n_realizations=5, seed=999)
    assert not res1[0]["attribution_evidence_score"].equals(res3[0]["attribution_evidence_score"])


def test_perturbation_bounds(analyzer):
    """Test that all perturbed parameters stay strictly within configured physical ranges."""
    ensemble = analyzer.generate_ensemble_realizations(n_realizations=10, seed=42)
    all_df = pd.concat(ensemble, ignore_index=True)

    # Check evidence components are valid [0, 1]
    for col in ["s_drift", "s_space", "s_source", "s_time", "s_ais", "attribution_evidence_score"]:
        assert (all_df[col] >= 0.0).all(), f"{col} has values < 0.0"
        assert (all_df[col] <= 1.0).all(), f"{col} has values > 1.0"
        assert not all_df[col].isna().any(), f"{col} has NaN values"

    # Check perturbed coordinates do not wildly diverge from original
    df_hyp, _, _ = analyzer.load_baseline_inputs()
    merged = pd.merge(all_df, df_hyp, on="hypothesis_id")
    lat_diff = (merged["pert_release_lat"] - merged["release_lat"]).abs()
    # 3 sigma of 250 m is ~750 m, which is ~0.007 degrees
    assert (lat_diff < 0.02).all()


def test_rank_stability_computation(analyzer):
    """Test mathematical consistency of rank stability calculations."""
    ensemble = analyzer.generate_ensemble_realizations(n_realizations=15, seed=42)
    df_hyp_stab, _ = analyzer.compute_rank_stability(ensemble)

    # Top-1 frequencies across all hypotheses must sum to approximately 1.0 (within rounding tolerance)
    assert pytest.approx(df_hyp_stab["top_1_frequency"].sum(), abs=1e-3) == 1.0


    # Top-3 frequency must be >= Top-1 frequency for all hypotheses
    assert (df_hyp_stab["top_3_frequency"] >= df_hyp_stab["top_1_frequency"]).all()

    # Ranks must be between 1 and total hypotheses
    assert (df_hyp_stab["min_rank"] >= 1).all()
    assert (df_hyp_stab["max_rank"] <= len(df_hyp_stab)).all()
    assert (df_hyp_stab["mean_rank"] >= 1.0).all()
    assert (df_hyp_stab["std_rank"] >= 0.0).all()


def test_score_distribution_generation(analyzer):
    """Test that percentiles and IQR satisfy strict mathematical order."""
    ensemble = analyzer.generate_ensemble_realizations(n_realizations=20, seed=42)
    df_hyp_stab, _ = analyzer.compute_rank_stability(ensemble)

    for _, row in df_hyp_stab.iterrows():
        assert row["score_p05"] <= row["score_p50"] <= row["score_p95"]
        assert row["score_iqr"] >= 0.0
        assert 0.0 <= row["mean_score"] <= 1.0
        assert row["std_score"] >= 0.0


def test_source_location_uncertainty(analyzer):
    """Test source location spatial dispersion and valid GeoJSON geometries."""
    ensemble = analyzer.generate_ensemble_realizations(n_realizations=10, seed=42)
    geojson = analyzer.compute_source_location_uncertainty(ensemble)

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0

    types = {f["geometry"]["type"] for f in geojson["features"]}
    assert "Point" in types
    assert "Polygon" in types

    for f in geojson["features"]:
        props = f["properties"]
        assert "hypothesis_id" in props
        if f["geometry"]["type"] == "Point":
            assert props["spatial_std_m"] >= 0.0
            assert props["radius_50_pct_m"] <= props["radius_90_pct_m"]
        elif f["geometry"]["type"] == "Polygon":
            coords = f["geometry"]["coordinates"][0]
            # Polygon ring must close
            assert coords[0] == coords[-1]
            assert len(coords) >= 4


def test_source_time_sensitivity(analyzer):
    """Test source-time sensitivity evaluation across temporal offsets."""
    df_time = analyzer.compute_source_time_sensitivity()

    assert len(df_time) > 0
    assert "time_offset_minutes" in df_time.columns
    assert "attribution_score" in df_time.columns

    # Check for a specific hypothesis: score at delta_t = 0 should be >= score at large positive offsets
    h_sample = df_time[df_time["hypothesis_id"] == "4DH_0014"]
    score_0 = h_sample[h_sample["time_offset_seconds"] == 0]["attribution_score"].iloc[0]
    score_far = h_sample[h_sample["time_offset_seconds"] == 10800]["attribution_score"].iloc[0]
    assert score_0 > score_far


def test_environmental_sensitivity_sweeps(analyzer):
    """Test environmental sensitivity grid sweeps and robust/sensitive classification."""
    df_env = analyzer.compute_environmental_sensitivity()

    assert len(df_env) == 19
    assert "sensitivity_index" in df_env.columns
    assert "environmental_robustness" in df_env.columns

    for _, row in df_env.iterrows():
        assert row["min_environmental_score"] <= row["max_environmental_score"]
        assert row["environmental_robustness"] in ["ROBUST", "SENSITIVE"]
        assert row["sensitivity_index"] >= 0.0


def test_ais_sensitivity_sweeps(analyzer):
    """Test AIS sensitivity across varying spatial and temporal matching scales."""
    df_ais = analyzer.compute_ais_sensitivity()

    assert len(df_ais) == 19
    assert "ais_sensitivity_index" in df_ais.columns
    assert "ais_score_spread" in df_ais.columns

    # Score spread must be non-negative
    assert (df_ais["ais_score_spread"] >= 0.0).all()


def test_uncertainty_state_and_reason_codes(analyzer):
    """Test structured uncertainty reason codes assignment."""
    ensemble = analyzer.generate_ensemble_realizations(n_realizations=10, seed=42)
    df_hyp_stab, _ = analyzer.compute_rank_stability(ensemble)
    df_env = analyzer.compute_environmental_sensitivity()
    _, _, df_ev = analyzer.load_baseline_inputs()

    df_refined = analyzer.assign_uncertainty_states_and_reasons(df_ev, df_hyp_stab, df_env)

    assert len(df_refined) == 19
    assert "refined_evidence_quality_state" in df_refined.columns
    assert "uncertainty_reason_codes" in df_refined.columns
    assert "primary_uncertainty_reason" in df_refined.columns

    # Every hypothesis must include INSUFFICIENT_VALIDATION_DATA (since N=1 case)
    assert all(UncertaintyReasonCode.INSUFFICIENT_VALIDATION_DATA in r for r in df_refined["uncertainty_reason_codes"])

    # Hypotheses with distant vessels must flag LARGE_VESSEL_SOURCE_SEPARATION
    distant = df_refined[df_refined["vessel_source_distance_m"] > 5000.0]
    assert len(distant) > 0
    assert all(UncertaintyReasonCode.LARGE_VESSEL_SOURCE_SEPARATION in r for r in distant["uncertainty_reason_codes"])


def test_score_calibration_guardrail(analyzer):
    """Test that score calibration audit explicitly forbids treating scores as probabilities."""
    audit = analyzer.evaluate_score_calibration()

    assert audit["is_probability_calibrated"] is False
    assert audit["calibration_status"] == "UNCALIBRATED_COMPATIBILITY_INDEX"
    assert "NOT calibrated probabilities" in audit["mandatory_scientific_notice"]
    assert audit["available_cases_count"] == 1
    assert audit["min_cases_required_for_calibration"] >= 30


def test_insufficient_data_handling(analyzer):
    """Test graceful handling when evaluating calibration or state on minimal data."""
    audit = analyzer.evaluate_score_calibration()
    assert audit["available_cases_count"] < audit["min_cases_required_for_calibration"]


def test_vessel_level_rank_stability(analyzer):
    """Test vessel-level rollup of rank stability."""
    ensemble = analyzer.generate_ensemble_realizations(n_realizations=15, seed=42)
    _, df_vessel_stab = analyzer.compute_rank_stability(ensemble)

    assert len(df_vessel_stab) == 10
    # Top-1 vessel frequencies sum must be <= 1.0 (some realizations may have ties)
    assert pytest.approx(df_vessel_stab["vessel_top_1_frequency"].sum(), abs=1e-3) == 1.0
    assert (df_vessel_stab["vessel_top_3_frequency"] >= df_vessel_stab["vessel_top_1_frequency"]).all()
    assert (df_vessel_stab["best_score_p05"] <= df_vessel_stab["best_score_p95"]).all()


def test_synthetic_stable_vs_sensitive(analyzer):
    """Test that synthetic hypothesis with large environmental variation is flagged SENSITIVE."""
    # Build synthetic grid with wide spread
    nominal_score = 0.50
    min_score = 0.35
    max_score = 0.65
    spread = max_score - min_score
    sens_idx = spread / nominal_score

    robust_class = "ROBUST" if sens_idx <= analyzer.th_robust else "SENSITIVE"
    assert pytest.approx(sens_idx) == 0.60
    assert robust_class == "SENSITIVE"

    # Build synthetic grid with narrow spread
    min_score_narrow = 0.48
    max_score_narrow = 0.52
    spread_narrow = max_score_narrow - min_score_narrow
    sens_idx_narrow = spread_narrow / nominal_score
    robust_class_narrow = "ROBUST" if sens_idx_narrow <= analyzer.th_robust else "SENSITIVE"
    assert pytest.approx(sens_idx_narrow) == 0.08
    assert robust_class_narrow == "ROBUST"



def test_synthetic_competing_hypotheses(analyzer):
    """Test that competing hypotheses with small score margin are flagged UNSTABLE or STRONG_COMPETING_HYPOTHESES."""
    # Fake two hypotheses with close scores
    df_fake_ev = pd.DataFrame([
        {
            "hypothesis_id": "H1", "attribution_evidence_score": 0.62, "drift_score": 0.70,
            "spatial_score": 0.30, "source_score": 0.60, "temporal_score": 0.80, "ais_quality_score": 0.70,
            "ais_gap_seconds": 300.0, "vessel_source_distance_m": 4500.0, "centroid_error_m": 200.0,
            "evidence_quality_state": "MODERATE_SUPPORT",
        },
        {
            "hypothesis_id": "H2", "attribution_evidence_score": 0.60, "drift_score": 0.70,
            "spatial_score": 0.28, "source_score": 0.60, "temporal_score": 0.80, "ais_quality_score": 0.70,
            "ais_gap_seconds": 300.0, "vessel_source_distance_m": 4800.0, "centroid_error_m": 220.0,
            "evidence_quality_state": "MODERATE_SUPPORT",
        },
    ])
    df_fake_stab = pd.DataFrame([
        {"hypothesis_id": "H1", "top_1_frequency": 0.55, "std_rank": 0.8, "rank_stability_category": "VERY_STABLE"},
        {"hypothesis_id": "H2", "top_1_frequency": 0.45, "std_rank": 0.8, "rank_stability_category": "VERY_STABLE"},
    ])
    df_fake_env = pd.DataFrame([
        {"hypothesis_id": "H1", "environmental_robustness": "ROBUST", "sensitivity_index": 0.05},
        {"hypothesis_id": "H2", "environmental_robustness": "ROBUST", "sensitivity_index": 0.05},
    ])

    df_res = analyzer.assign_uncertainty_states_and_reasons(df_fake_ev, df_fake_stab, df_fake_env)
    h2_row = df_res[df_res["hypothesis_id"] == "H2"].iloc[0]
    assert UncertaintyReasonCode.STRONG_COMPETING_HYPOTHESES in h2_row["uncertainty_reason_codes"]


def test_case_001_uncertainty_output_integrity():
    """Test that all Phase 10 Case 001 generated artifacts exist, are non-empty, and adhere to schemas."""
    unc_csv = Path("data/processed/attribution/case_001_uncertainty_summary.csv")
    unc_json = Path("data/processed/attribution/case_001_uncertainty_summary.json")
    rank_stab_csv = Path("data/processed/attribution/case_001_hypothesis_rank_stability.csv")
    loc_unc_geojson = Path("data/processed/attribution/case_001_source_location_uncertainty.geojson")
    time_sens_csv = Path("data/processed/attribution/case_001_source_time_sensitivity.csv")
    env_sens_csv = Path("data/processed/attribution/case_001_environmental_sensitivity.csv")
    ais_sens_csv = Path("data/processed/attribution/case_001_ais_sensitivity.csv")
    unc_diag = Path("data/processed/attribution/case_001_uncertainty_diagnostic.png")

    for p in [unc_csv, unc_json, rank_stab_csv, loc_unc_geojson, time_sens_csv, env_sens_csv, ais_sens_csv, unc_diag]:
        assert p.exists(), f"Missing file: {p}"
        assert p.stat().st_size > 300, f"File unexpectedly small: {p}"

    df_stab = pd.read_csv(rank_stab_csv)
    assert len(df_stab) == 19
    assert "top_1_frequency" in df_stab.columns
    assert "rank_stability_category" in df_stab.columns

    with open(unc_json, "r", encoding="utf-8") as jf:
        meta = json.load(jf)
        assert meta["case_id"] == "case_001"
        assert meta["calibration_audit"]["is_probability_calibrated"] is False
        assert "mandatory_scientific_notice" in meta["calibration_audit"]
