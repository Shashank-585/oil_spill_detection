"""
Causal Consistency Engine for Maritime Oil Spill Attribution.

Provides generic, incident-independent physical and observational consistency checks:
1. Vessel Temporal Precedence: Evaluates whether AIS evidence exists prior to or at
   the hypothesized release time, classifying vessels into:
   - PRE_EXISTING: Active prior to release time.
   - AT_RELEASE: Observed at or near release time.
   - POST_EVENT_ONLY: First appeared strictly after release time (ineligible for source credit).
   - INSUFFICIENT: Inadequate AIS track data to establish precedence.
2. Defensible AIS Interpolation: Safely brackets positions across release times,
   tracking temporal gaps and marking extrapolated positions uncertain.
3. Source-Age Plausibility: Applies physical spreading mechanics (Fay spreading bounds)
   to evaluate whether an observed slick area could physically have formed within the
   hypothesized source age, categorizing hypotheses as HIGH, MEDIUM, LOW, or UNKNOWN.

Scientific Guardrails:
- Zero hardcoded vessel identities, MMSIs, or case-specific timestamps.
- Completely generic across all maritime incidents and search envelopes.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.common.logging import get_logger
from src.common.time_utils import parse_utc_timestamp

logger = get_logger(__name__)


class CausalPrecedenceStatus(str, Enum):
    """Categorical states of vessel temporal precedence relative to hypothesized release."""
    PRE_EXISTING = "PRE_EXISTING"
    AT_RELEASE = "AT_RELEASE"
    POST_EVENT_ONLY = "POST_EVENT_ONLY"
    INSUFFICIENT = "INSUFFICIENT"


class SourceAgePlausibility(str, Enum):
    """Categorical states of physical source-age plausibility based on slick spreading."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class CausalPrecedenceResult:
    """Detailed outcome of vessel temporal precedence evaluation."""
    status: str
    score: float
    is_eligible: bool
    pre_release_evidence: bool
    post_release_evidence: bool
    ais_gap_seconds: float
    bracket_prev_utc: Optional[str]
    bracket_next_utc: Optional[str]
    interpolated_lat: Optional[float]
    interpolated_lon: Optional[float]
    interpolation_quality: str
    explanation: str


@dataclass
class SourceAgePlausibilityResult:
    """Detailed outcome of physical source-age plausibility evaluation."""
    plausibility: str
    score: float
    min_spreading_time_hours: float
    observed_area_km2: float
    hypothesized_age_hours: float
    explanation: str


def determine_temporal_precedence(
    vessel_track: pd.DataFrame,
    release_time: Union[str, datetime],
    at_release_tolerance_seconds: float = 300.0,
    max_interpolation_gap_seconds: float = 3600.0,
    min_pings_for_precedence: int = 2,
) -> CausalPrecedenceResult:
    """
    Determine whether a vessel has defensible presence before, at, or after the
    hypothesized spill release time.

    Parameters
    ----------
    vessel_track : pd.DataFrame
        DataFrame containing at least 'timestamp_utc', 'latitude', and 'longitude'.
    release_time : Union[str, datetime]
        Hypothesized spill release timestamp.
    at_release_tolerance_seconds : float
        Tolerance window (in seconds) within which a ping is considered AT_RELEASE (default 300s).
    max_interpolation_gap_seconds : float
        Maximum allowable gap between pings for linear interpolation across release time (default 3600s).
    min_pings_for_precedence : int
        Minimum pings required to determine valid precedence (default 2).

    Returns
    -------
    CausalPrecedenceResult
        Structured causal precedence evaluation.
    """
    rel_dt = parse_utc_timestamp(release_time)
    rel_epoch = int(rel_dt.timestamp())

    if vessel_track is None or len(vessel_track) < min_pings_for_precedence:
        return CausalPrecedenceResult(
            status=CausalPrecedenceStatus.INSUFFICIENT.value,
            score=0.5,
            is_eligible=True,  # Neutral/uncertain treatment
            pre_release_evidence=False,
            post_release_evidence=False,
            ais_gap_seconds=float("inf"),
            bracket_prev_utc=None,
            bracket_next_utc=None,
            interpolated_lat=None,
            interpolated_lon=None,
            interpolation_quality="insufficient_data",
            explanation="Insufficient AIS track pings to determine temporal precedence.",
        )

    # Ensure timestamps are parsed and sorted
    track = vessel_track.copy()
    track["timestamp_dt"] = pd.to_datetime(track["timestamp_utc"], utc=True)
    track = track.sort_values(by="timestamp_dt").reset_index(drop=True)
    times_epoch = track["timestamp_dt"].values.astype("datetime64[s]").astype(np.int64)

    t_first = times_epoch[0]
    t_last = times_epoch[-1]

    # Check for exact or near-release ping within tolerance
    time_diffs = np.abs(times_epoch - rel_epoch)
    min_diff_idx = int(np.argmin(time_diffs))
    min_diff = float(time_diffs[min_diff_idx])

    # 1. POST_EVENT_ONLY: The vessel's FIRST known observation occurs strictly after release time
    # (beyond tolerance window)
    if t_first > (rel_epoch + at_release_tolerance_seconds):
        return CausalPrecedenceResult(
            status=CausalPrecedenceStatus.POST_EVENT_ONLY.value,
            score=0.0,
            is_eligible=False,
            pre_release_evidence=False,
            post_release_evidence=True,
            ais_gap_seconds=float(t_first - rel_epoch),
            bracket_prev_utc=None,
            bracket_next_utc=str(track["timestamp_dt"].iloc[0].isoformat()),
            interpolated_lat=None,
            interpolated_lon=None,
            interpolation_quality="extrapolation_post_event_only",
            explanation=(
                f"Vessel first appeared {float(t_first - rel_epoch):.1f}s after hypothesized release; "
                "ineligible for source attribution."
            ),
        )

    # 2. AT_RELEASE: Ping observed within tolerance of release time
    if min_diff <= at_release_tolerance_seconds:
        closest_row = track.iloc[min_diff_idx]
        has_pre = bool(t_first < rel_epoch)
        has_post = bool(t_last > rel_epoch)
        return CausalPrecedenceResult(
            status=CausalPrecedenceStatus.AT_RELEASE.value,
            score=1.0,
            is_eligible=True,
            pre_release_evidence=has_pre or (min_diff == 0),
            post_release_evidence=has_post or (min_diff == 0),
            ais_gap_seconds=min_diff,
            bracket_prev_utc=str(closest_row["timestamp_dt"].isoformat()),
            bracket_next_utc=str(closest_row["timestamp_dt"].isoformat()),
            interpolated_lat=float(closest_row["latitude"]),
            interpolated_lon=float(closest_row["longitude"]),
            interpolation_quality="exact_or_near_ping",
            explanation=f"Vessel observed within {min_diff:.1f}s of hypothesized release time.",
        )

    # 3. PRE_EXISTING: Vessel track brackets the release time
    if t_first <= rel_epoch <= t_last:
        idx = int(np.searchsorted(times_epoch, rel_epoch))
        idx_prev = idx - 1
        idx_next = idx

        p_prev = track.iloc[idx_prev]
        p_next = track.iloc[idx_next]
        gap = float(times_epoch[idx_next] - times_epoch[idx_prev])

        if gap > max_interpolation_gap_seconds:
            return CausalPrecedenceResult(
                status=CausalPrecedenceStatus.INSUFFICIENT.value,
                score=0.5,
                is_eligible=True,
                pre_release_evidence=True,
                post_release_evidence=True,
                ais_gap_seconds=gap,
                bracket_prev_utc=str(p_prev["timestamp_dt"].isoformat()),
                bracket_next_utc=str(p_next["timestamp_dt"].isoformat()),
                interpolated_lat=None,
                interpolated_lon=None,
                interpolation_quality="gap_exceeds_threshold",
                explanation=f"AIS gap across release time ({gap:.1f}s) exceeds maximum interpolation threshold ({max_interpolation_gap_seconds:.0f}s).",
            )

        # Defensible linear interpolation
        tau = (rel_epoch - times_epoch[idx_prev]) / gap
        lat_interp = float(p_prev["latitude"] + tau * (p_next["latitude"] - p_prev["latitude"]))
        lon_interp = float(p_prev["longitude"] + tau * (p_next["longitude"] - p_prev["longitude"]))

        return CausalPrecedenceResult(
            status=CausalPrecedenceStatus.PRE_EXISTING.value,
            score=1.0,
            is_eligible=True,
            pre_release_evidence=True,
            post_release_evidence=True,
            ais_gap_seconds=gap,
            bracket_prev_utc=str(p_prev["timestamp_dt"].isoformat()),
            bracket_next_utc=str(p_next["timestamp_dt"].isoformat()),
            interpolated_lat=round(lat_interp, 6),
            interpolated_lon=round(lon_interp, 6),
            interpolation_quality="bracketed_interpolation",
            explanation=f"Vessel active across release time with defensible bracketed gap of {gap:.1f}s.",
        )

    # 4. Track ended before release time
    if t_last < rel_epoch:
        delta_after = float(rel_epoch - t_last)
        if delta_after <= at_release_tolerance_seconds:
            last_row = track.iloc[-1]
            return CausalPrecedenceResult(
                status=CausalPrecedenceStatus.AT_RELEASE.value,
                score=1.0,
                is_eligible=True,
                pre_release_evidence=True,
                post_release_evidence=False,
                ais_gap_seconds=delta_after,
                bracket_prev_utc=str(last_row["timestamp_dt"].isoformat()),
                bracket_next_utc=None,
                interpolated_lat=float(last_row["latitude"]),
                interpolated_lon=float(last_row["longitude"]),
                interpolation_quality="near_boundary_last_ping",
                explanation=f"Vessel last observed {delta_after:.1f}s before release time (within tolerance).",
            )
        else:
            # Exited area or ceased broadcasting well before release
            return CausalPrecedenceResult(
                status=CausalPrecedenceStatus.PRE_EXISTING.value,
                score=0.85,
                is_eligible=True,
                pre_release_evidence=True,
                post_release_evidence=False,
                ais_gap_seconds=delta_after,
                bracket_prev_utc=str(track.iloc[-1]["timestamp_dt"].isoformat()),
                bracket_next_utc=None,
                interpolated_lat=None,
                interpolated_lon=None,
                interpolation_quality="track_ended_before_release",
                explanation=f"Vessel present prior to release, but last ping was {delta_after/60.0:.1f} min before release.",
            )

    return CausalPrecedenceResult(
        status=CausalPrecedenceStatus.INSUFFICIENT.value,
        score=0.5,
        is_eligible=True,
        pre_release_evidence=False,
        post_release_evidence=False,
        ais_gap_seconds=float("inf"),
        bracket_prev_utc=None,
        bracket_next_utc=None,
        interpolated_lat=None,
        interpolated_lon=None,
        interpolation_quality="unknown",
        explanation="Unable to determine temporal precedence.",
    )


def evaluate_source_age_plausibility(
    source_age_hours: float,
    observed_slick_area_km2: Optional[float] = None,
    aspect_ratio: Optional[float] = None,
    oil_type: Optional[str] = None,
) -> SourceAgePlausibilityResult:
    """
    Evaluate the physical plausibility of a hypothesized source age relative to
    the observed slick geometry under conservative oil spreading physics.

    Parameters
    ----------
    source_age_hours : float
        Hypothesized source release age in hours.
    observed_slick_area_km2 : Optional[float]
        Observed surface area of the satellite-detected oil slick in km^2.
    aspect_ratio : Optional[float]
        Length-to-width aspect ratio of the slick (indicates instantaneous vs continuous line release).
    oil_type : Optional[str]
        Oil classification if known (e.g. 'heavy_fuel', 'diesel', 'crude').

    Returns
    -------
    SourceAgePlausibilityResult
        Structured age plausibility assessment.
    """
    # If slick area is missing or non-positive, plausibility cannot be rigorously constrained
    if observed_slick_area_km2 is None or not math.isfinite(observed_slick_area_km2) or observed_slick_area_km2 <= 0.0:
        return SourceAgePlausibilityResult(
            plausibility=SourceAgePlausibility.UNKNOWN.value,
            score=0.70,
            min_spreading_time_hours=0.0,
            observed_area_km2=0.0,
            hypothesized_age_hours=float(source_age_hours),
            explanation="Observed slick area unknown; source-age plausibility cannot be constrained physically.",
        )

    area = float(observed_slick_area_km2)
    age = float(source_age_hours)

    # Conservative spreading estimate:
    # Based on Fay (1971) gravity-viscous / surface-tension transitions for typical marine hydrocarbons.
    # An oil slick of area A_km2 requires a minimum physical spreading time from a point release:
    # t_min ≈ 1.5 * sqrt(A_km2 / 0.01) hours.
    # To be conservative, t_min_conservative = 1.5 * (A_km2 / 0.01) ** 0.5
    t_min_conservative = float(1.5 * ((area / 0.01) ** 0.5))
    t_min_conservative = max(1.0, min(14.0, t_min_conservative))

    # Adjust for elongated line-source slick (ship leaking underway)
    if aspect_ratio is not None and aspect_ratio > 8.0:
        # A long narrow slick can form faster along a vessel trajectory
        t_min_conservative *= 0.70

    if age < (0.75 * t_min_conservative):
        plausibility = SourceAgePlausibility.LOW.value
        score = 0.35
        explanation = (
            f"Hypothesized source age {age:.1f}h is unphysically young for an observed slick area of "
            f"{area:.4f} km² (estimated physical spreading time ≥ {t_min_conservative:.1f}h)."
        )
    elif age < t_min_conservative:
        plausibility = SourceAgePlausibility.MEDIUM.value
        score = 0.75
        explanation = (
            f"Hypothesized source age {age:.1f}h is on the lower boundary of physical spreading "
            f"for area {area:.4f} km² (nominal minimum {t_min_conservative:.1f}h)."
        )
    elif age <= 18.0:
        plausibility = SourceAgePlausibility.HIGH.value
        score = 1.00
        explanation = (
            f"Hypothesized source age {age:.1f}h is fully compatible with physical spreading "
            f"and Lagrangian drift for area {area:.4f} km²."
        )
    elif age <= 24.0:
        plausibility = SourceAgePlausibility.MEDIUM.value
        score = 0.80
        explanation = (
            f"Hypothesized source age {age:.1f}h is plausible but subject to weathering, dissipation, "
            "and increased backward-trajectory uncertainty."
        )
    else:
        plausibility = SourceAgePlausibility.LOW.value
        score = 0.40
        explanation = f"Hypothesized source age {age:.1f}h exceeds reliable backward drift horizon (> 24h)."

    return SourceAgePlausibilityResult(
        plausibility=plausibility,
        score=score,
        min_spreading_time_hours=round(t_min_conservative, 2),
        observed_area_km2=round(area, 4),
        hypothesized_age_hours=round(age, 2),
        explanation=explanation,
    )
