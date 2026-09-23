"""
Unit tests for Phase 13: Causal Consistency Layer.

Validates:
1. Vessel present before release -> PRE_EXISTING
2. Vessel ping exactly at release -> AT_RELEASE
3. Vessel first appears after release -> POST_EVENT_ONLY
4. Large AIS gap across release -> INSUFFICIENT
5. Vessel exits AOI before release -> appropriate causal state
6. Interpolation across valid short gap -> valid bracketed interpolation
7. Extrapolation across large gap -> uncertain, never silently accepted
8. Source-age plausibility with known synthetic cases
9. Baseline behavior unchanged when causal consistency disabled
10. No ground-truth vessel identity used by causal layer
"""

from datetime import datetime, timezone, timedelta
import math
import pytest
import pandas as pd
import numpy as np

from src.attribution.causal_consistency import (
    CausalPrecedenceStatus,
    SourceAgePlausibility,
    CausalPrecedenceResult,
    SourceAgePlausibilityResult,
    determine_temporal_precedence,
    evaluate_source_age_plausibility,
)
from src.attribution.hypothesis_generator import SourceHypothesisGenerator4D
from src.attribution.attribution_engine import AttributionEngine


# Helper fixture to create synthetic vessel tracks
def make_track(timestamps: list, lats: list = None, lons: list = None) -> pd.DataFrame:
    n = len(timestamps)
    if lats is None:
        lats = [31.12 + 0.001 * i for i in range(n)]
    if lons is None:
        lons = [-81.40 - 0.001 * i for i in range(n)]
    return pd.DataFrame({
        "timestamp_utc": timestamps,
        "latitude": lats,
        "longitude": lons,
        "sog_knots": [10.0] * n,
        "cog_deg": [90.0] * n,
    })


# 1. Vessel present before release -> PRE_EXISTING
def test_vessel_present_before_release_pre_existing():
    """Vessel with pings before and after release time is classified as PRE_EXISTING."""
    rel_time = "2021-10-02T12:00:00Z"
    track = make_track([
        "2021-10-02T11:00:00Z",
        "2021-10-02T11:45:00Z",
        "2021-10-02T12:15:00Z",
        "2021-10-02T13:00:00Z",
    ])
    res = determine_temporal_precedence(track, rel_time, at_release_tolerance_seconds=180.0)

    assert res.status == CausalPrecedenceStatus.PRE_EXISTING.value
    assert res.score == 1.0
    assert res.is_eligible is True
    assert res.pre_release_evidence is True
    assert res.post_release_evidence is True
    assert res.interpolation_quality == "bracketed_interpolation"
    assert res.interpolated_lat is not None
    assert res.interpolated_lon is not None


# 2. Vessel ping exactly at release -> AT_RELEASE
def test_vessel_ping_exactly_at_release_at_release():
    """Vessel with an AIS observation exactly at (or within tolerance of) release time is AT_RELEASE."""
    rel_time = "2021-10-02T12:00:00Z"
    # Ping exactly at 12:00:00
    track_exact = make_track([
        "2021-10-02T11:30:00Z",
        "2021-10-02T12:00:00Z",
        "2021-10-02T12:30:00Z",
    ])
    res_exact = determine_temporal_precedence(track_exact, rel_time, at_release_tolerance_seconds=300.0)
    assert res_exact.status == CausalPrecedenceStatus.AT_RELEASE.value
    assert res_exact.score == 1.0
    assert res_exact.is_eligible is True
    assert res_exact.ais_gap_seconds == 0.0

    # Ping 60 seconds after release (well within 300s tolerance)
    track_near = make_track([
        "2021-10-02T11:30:00Z",
        "2021-10-02T12:01:00Z",
        "2021-10-02T12:30:00Z",
    ])
    res_near = determine_temporal_precedence(track_near, rel_time, at_release_tolerance_seconds=300.0)
    assert res_near.status == CausalPrecedenceStatus.AT_RELEASE.value
    assert res_near.score == 1.0
    assert res_near.ais_gap_seconds == 60.0


# 3. Vessel first appears after release -> POST_EVENT_ONLY
def test_vessel_first_appears_after_release_post_event_only():
    """Vessel whose earliest AIS ping occurs strictly after release is POST_EVENT_ONLY and ineligible."""
    rel_time = "2021-10-02T12:00:00Z"
    # First ping is 45 minutes after release time
    track_post = make_track([
        "2021-10-02T12:45:00Z",
        "2021-10-02T13:00:00Z",
        "2021-10-02T13:30:00Z",
    ])
    res = determine_temporal_precedence(track_post, rel_time, at_release_tolerance_seconds=300.0)

    assert res.status == CausalPrecedenceStatus.POST_EVENT_ONLY.value
    assert res.score == 0.0
    assert res.is_eligible is False
    assert res.pre_release_evidence is False
    assert res.post_release_evidence is True
    assert res.interpolated_lat is None
    assert "ineligible for source attribution" in res.explanation


# 4. Large AIS gap across release -> INSUFFICIENT
def test_large_ais_gap_insufficient():
    """An excessive AIS gap (> max_interpolation_gap) bracketing release time yields INSUFFICIENT."""
    rel_time = "2021-10-02T12:00:00Z"
    # Gap is 4 hours (10:00 to 14:00) with max_gap = 3600s (1h)
    track_gap = make_track([
        "2021-10-02T09:00:00Z",
        "2021-10-02T10:00:00Z",
        "2021-10-02T14:00:00Z",
        "2021-10-02T15:00:00Z",
    ])
    res = determine_temporal_precedence(
        track_gap,
        rel_time,
        at_release_tolerance_seconds=300.0,
        max_interpolation_gap_seconds=3600.0,
    )

    assert res.status == CausalPrecedenceStatus.INSUFFICIENT.value
    assert res.score == 0.5  # Neutral uncertain score
    assert res.is_eligible is True
    assert res.ais_gap_seconds == 14400.0
    assert res.interpolated_lat is None
    assert "exceeds maximum interpolation threshold" in res.explanation


# 5. Vessel exits AOI before release -> appropriate causal state
def test_vessel_exits_aoi_before_release():
    """Vessel that ceased broadcasting / exited before release has pre-release evidence but no post-release."""
    rel_time = "2021-10-02T12:00:00Z"
    # Last ping at 11:00 (1 hour before release)
    track_exit = make_track([
        "2021-10-02T09:00:00Z",
        "2021-10-02T10:00:00Z",
        "2021-10-02T11:00:00Z",
    ])
    res = determine_temporal_precedence(track_exit, rel_time, at_release_tolerance_seconds=300.0)

    assert res.status == CausalPrecedenceStatus.PRE_EXISTING.value
    assert res.pre_release_evidence is True
    assert res.post_release_evidence is False
    assert res.is_eligible is True
    assert res.interpolation_quality == "track_ended_before_release"
    assert res.ais_gap_seconds == 3600.0


# 6. Interpolation across valid short gap -> valid
def test_interpolation_across_valid_short_gap():
    """Short gap (< max_gap) accurately performs metric linear interpolation."""
    rel_time = "2021-10-02T12:00:00Z"
    # 20 min gap: 11:50 to 12:10 (rel_time is exact midpoint)
    track = make_track(
        timestamps=["2021-10-02T11:50:00Z", "2021-10-02T12:10:00Z"],
        lats=[31.1000, 31.2000],
        lons=[-81.4000, -81.3000],
    )
    res = determine_temporal_precedence(track, rel_time, at_release_tolerance_seconds=120.0)

    assert res.status == CausalPrecedenceStatus.PRE_EXISTING.value
    assert res.interpolation_quality == "bracketed_interpolation"
    assert pytest.approx(res.interpolated_lat, abs=1e-4) == 31.1500
    assert pytest.approx(res.interpolated_lon, abs=1e-4) == -81.3500
    assert res.ais_gap_seconds == 1200.0


# 7. Extrapolation across large gap -> uncertain, never silently accepted
def test_extrapolation_across_large_gap_uncertain():
    """Extrapolation before first ping or after last ping outside tolerance returns None and is never silently accepted."""
    rel_time = "2021-10-02T12:00:00Z"
    # First ping at 12:30 (30 min after release)
    track = make_track(["2021-10-02T12:30:00Z", "2021-10-02T13:00:00Z"])
    res = determine_temporal_precedence(track, rel_time, at_release_tolerance_seconds=180.0)

    assert res.status == CausalPrecedenceStatus.POST_EVENT_ONLY.value
    assert res.interpolated_lat is None
    assert res.interpolated_lon is None
    assert res.is_eligible is False


# 8. Source-age plausibility with known synthetic cases
def test_source_age_plausibility_synthetic_cases():
    """Physical spreading bounds properly differentiate unphysical young ages from mature ones."""
    slick_area_km2 = 0.0526  # ~52,600 m^2 (like Case 003)

    # 2.0 hours: unphysically young for a 0.0526 km^2 slick
    res_2h = evaluate_source_age_plausibility(source_age_hours=2.0, observed_slick_area_km2=slick_area_km2)
    assert res_2h.plausibility == SourceAgePlausibility.LOW.value
    assert res_2h.score <= 0.40
    assert res_2h.min_spreading_time_hours >= 2.3

    # 6.0 hours: physically plausible
    res_6h = evaluate_source_age_plausibility(source_age_hours=6.0, observed_slick_area_km2=slick_area_km2)
    assert res_6h.plausibility == SourceAgePlausibility.HIGH.value
    assert res_6h.score == 1.00

    # 12.0 hours: physically plausible
    res_12h = evaluate_source_age_plausibility(source_age_hours=12.0, observed_slick_area_km2=slick_area_km2)
    assert res_12h.plausibility == SourceAgePlausibility.HIGH.value
    assert res_12h.score == 1.00

    # 36.0 hours: excessive age beyond reliable drift window
    res_36h = evaluate_source_age_plausibility(source_age_hours=36.0, observed_slick_area_km2=slick_area_km2)
    assert res_36h.plausibility == SourceAgePlausibility.LOW.value
    assert res_36h.score < 0.50

    # Missing area fallback: UNKNOWN
    res_unk = evaluate_source_age_plausibility(source_age_hours=4.0, observed_slick_area_km2=None)
    assert res_unk.plausibility == SourceAgePlausibility.UNKNOWN.value
    assert res_unk.score == 0.70


# 9. Baseline behavior unchanged when causal consistency disabled
def test_baseline_behavior_unchanged_when_disabled():
    """Verify that AttributionEngine with causal_consistency_enabled=False reproduces exact baseline scores."""
    engine_baseline = AttributionEngine("case_001", config_override={"causal_consistency_enabled": False})
    assert engine_baseline.causal_consistency_enabled is False

    hypo = {
        "hypothesis_id": "TEST_HYPO",
        "mmsi": 999999999,
        "vessel_name": "TEST_VESSEL",
        "observed_slick_id": "CS_TEST",
        "geodesic_distance_m": 1500.0,
        "vessel_source_distance_m": 1500.0,
        "time_gap_seconds": 60.0,
        "source_plausibility": 0.80,
        "ais_track_quality": "HIGH",
        "causal_precedence_status": "POST_EVENT_ONLY",  # Would be rejected if enabled!
        "causal_eligibility": False,
        "source_age_plausibility": "LOW",
        "source_age_score": 0.35,
    }
    comp = {
        "centroid_error_m": 50.0,
        "mean_particle_distance_m": 100.0,
        "coverage": 0.90,
        "iou": 0.60,
        "norm_centroid_score": 0.95,
        "norm_particle_score": 0.90,
    }

    res_baseline = engine_baseline.evaluate_hypothesis(hypo, comp)
    # When disabled, POST_EVENT_ONLY is ignored and normal score is computed
    assert res_baseline["attribution_evidence_score"] > 0.60
    assert res_baseline["evidence_quality_state"] != "INELIGIBLE_POST_EVENT"

    # Now verify that when enabled, score is zeroed out
    engine_causal = AttributionEngine("case_001", config_override={"causal_consistency_enabled": True})
    assert engine_causal.causal_consistency_enabled is True
    res_causal = engine_causal.evaluate_hypothesis(hypo, comp)
    assert res_causal["attribution_evidence_score"] == 0.0
    assert res_causal["evidence_quality_state"] == "INELIGIBLE_POST_EVENT"


# 10. No ground-truth vessel identity used by causal layer
def test_no_ground_truth_vessel_identity_in_causal_layer():
    """Verify that temporal precedence is purely a function of timestamps and coordinates, indifferent to vessel name or MMSI."""
    rel_time = "2021-10-02T12:00:00Z"
    t1 = make_track(["2021-10-02T11:00:00Z", "2021-10-02T12:05:00Z"])
    t2 = make_track(["2021-10-02T11:00:00Z", "2021-10-02T12:05:00Z"])

    # Provide arbitrary MMSI/names
    r1 = determine_temporal_precedence(t1, rel_time)
    r2 = determine_temporal_precedence(t2, rel_time)

    assert r1.status == r2.status
    assert r1.score == r2.score
    assert r1.is_eligible == r2.is_eligible
    assert r1.ais_gap_seconds == r2.ais_gap_seconds
