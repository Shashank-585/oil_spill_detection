"""
Phase 9: Explainable Multi-Evidence Attribution Engine.

Evaluates each 4D source hypothesis H = (vessel, release_location, release_time)
across multiple independent evidence categories:
1. Source Plausibility (from Phase 4 backward drift density field)
2. Spatial Compatibility (geodesic distance from vessel to release location)
3. Temporal Compatibility (temporal closeness of AIS observations to release time)
4. Physical Drift Consistency (from Phase 8 forward simulation comparison metrics)
5. AIS Track Quality (observational reliability and track continuity)

Produces:
- Ranked Source Hypotheses (with uncollapsed evidence vectors and normalized scores)
- Vessel-Level Aggregation Summaries
- Evidence-Quality States (HIGH_SUPPORT, MODERATE_SUPPORT, LOW_SUPPORT, INSUFFICIENT_EVIDENCE)
- Human-Readable Explanations with Explicit Conflict Detection
- Publication-Grade Attribution Diagnostic Visualization

Scientific Guardrails:
- The output is an attribution evidence score, NOT a probability of guilt.
- High score does NOT prove a vessel discharged oil or is liable.
- Conflicts between evidence categories are strictly preserved, not hidden.
- AIS gaps represent observational uncertainty, NOT evidence of suspicious behavior.
- The known pipeline rupture point is strictly excluded from score calculations.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.common.case_loader import load_case_config
from src.common.config import load_config
from src.common.geo import haversine_distance_m, haversine_distance_km
from src.common.logging import get_logger
from src.common.paths import (
    ATTRIBUTION_PROCESSED_DIR,
    HYPOTHESES_PROCESSED_DIR,
    ensure_dir_exists,
    resolve_path,
)

logger = get_logger(__name__)


class EvidenceQualityState:
    """Standardized categorical states for attribution evidence support."""
    HIGH_SUPPORT = "HIGH_SUPPORT"
    MODERATE_SUPPORT = "MODERATE_SUPPORT"
    LOW_SUPPORT = "LOW_SUPPORT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class HypothesisEvidence:
    hypothesis_id: str
    rank: int
    mmsi: int
    vessel_name: str
    observed_slick_id: str
    attribution_evidence_score: float
    evidence_quality_state: str
    s_drift: float
    s_space: float
    s_source: float
    s_time: float
    s_ais: float
    primary_strength: str
    primary_weakness: str
    explanation: str
    has_conflict: bool
    conflict_description: str


@dataclass
class VesselSummary:
    mmsi: int
    vessel_name: str
    vessel_rank: int
    best_hypothesis_id: str
    best_evidence_score: float
    mean_evidence_score: float
    hypothesis_count: int
    evidence_quality_state: str
    primary_strength: str
    primary_weakness: str
    explanation: str


def parse_gap_seconds(gap_str: Any) -> float:
    """Parse gap duration string (e.g. '553.0s', '120s') into float seconds."""
    if isinstance(gap_str, (int, float)):
        return float(gap_str)
    if not isinstance(gap_str, str):
        return 600.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", gap_str)
    if match:
        return float(match.group(1))
    return 600.0


def rating_label(score: float) -> str:
    """Convert a [0, 1] normalized score into an interpretable categorical rating."""
    if score >= 0.75:
        return "strong"
    if score >= 0.50:
        return "moderate"
    if score >= 0.25:
        return "weak"
    return "poor"


class AttributionEngine:

    """
    Explainable multi-evidence attribution engine evaluating physical,
    spatial, temporal, and observational evidence for candidate source hypotheses.
    """

    def __init__(
        self,
        case_id: str = "case_001",
        config_override: Optional[Dict[str, Any]] = None,
        output_dir: Optional[Union[str, Path]] = None,
    ):
        self.case_id = case_id
        self.case_cfg = load_case_config(case_id)
        self.default_cfg = load_config()

        if config_override:
            attr_cfg = config_override.get("attribution_scoring", {})
        else:
            attr_cfg = self.default_cfg.get("attribution_scoring", {})

        # Evidence category weights
        weights_dict = attr_cfg.get("weights", {})
        self.w_drift = float(weights_dict.get("drift_consistency", 0.30))
        self.w_space = float(weights_dict.get("spatial_compatibility", 0.25))
        self.w_source = float(weights_dict.get("source_plausibility", 0.20))
        self.w_time = float(weights_dict.get("temporal_compatibility", 0.15))
        self.w_ais = float(weights_dict.get("ais_track_quality", 0.10))

        # Validate weights sum to 1.0 (within numerical tolerance)
        total_w = self.w_drift + self.w_space + self.w_source + self.w_time + self.w_ais
        if not math.isclose(total_w, 1.0, rel_tol=1e-3):
            raise ValueError(f"Attribution weights must sum to 1.0, got {total_w:.4f}")

        # Scale parameters
        self.spatial_scale_m = float(attr_cfg.get("spatial_scale_m", 5000.0))
        self.temporal_scale_seconds = float(attr_cfg.get("temporal_scale_seconds", 600.0))

        # Drift sub-weights
        drift_sub = attr_cfg.get("drift_subweights", {})
        self.w_sub_centroid = float(drift_sub.get("centroid", 0.30))
        self.w_sub_particle = float(drift_sub.get("particle", 0.30))
        self.w_sub_coverage = float(drift_sub.get("coverage", 0.20))
        self.w_sub_iou = float(drift_sub.get("iou", 0.20))

        # Thresholds
        thresh = attr_cfg.get("thresholds", {})
        self.th_high = float(thresh.get("high_support", 0.70))
        self.th_mod = float(thresh.get("moderate_support", 0.50))
        self.th_low = float(thresh.get("low_support", 0.30))
        self.th_conflict_spread = float(thresh.get("conflict_spread", 0.40))

        # Causal consistency configuration
        causal_cfg = self.default_cfg.get("causal_consistency", {})
        if config_override and "causal_consistency" in config_override:
            causal_cfg.update(config_override["causal_consistency"])
        elif config_override and "causal_consistency_enabled" in config_override:
            causal_cfg["enabled"] = config_override["causal_consistency_enabled"]

        self.causal_consistency_enabled = bool(causal_cfg.get("enabled", False))
        self.ineligible_post_event_score = float(causal_cfg.get("ineligible_post_event_score", 0.0))
        self.enable_source_age_plausibility = bool(causal_cfg.get("enable_source_age_plausibility", True))

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = resolve_path(ATTRIBUTION_PROCESSED_DIR)
        ensure_dir_exists(self.output_dir)

        # Input file paths
        self.hypotheses_4d_csv = resolve_path(f"data/processed/hypotheses/{self.case_id}_source_hypotheses_4d.csv")
        self.spill_comparisons_csv = resolve_path(f"data/processed/attribution/{self.case_id}_spill_comparisons.csv")

    def load_inputs(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load Phase 6 4D hypotheses and Phase 8 spill comparisons."""
        if not self.hypotheses_4d_csv.exists():
            raise FileNotFoundError(f"Hypotheses 4D CSV not found: {self.hypotheses_4d_csv}")
        if not self.spill_comparisons_csv.exists():
            raise FileNotFoundError(f"Spill comparisons CSV not found: {self.spill_comparisons_csv}")

        df_hyp = pd.read_csv(self.hypotheses_4d_csv)
        df_comp = pd.read_csv(self.spill_comparisons_csv)

        logger.info(
            "Loaded %d 4D hypotheses and %d spill comparisons for Case %s.",
            len(df_hyp),
            len(df_comp),
            self.case_id,
        )
        return df_hyp, df_comp

    @property
    def weights(self) -> Dict[str, float]:
        """Evidence category weights dictionary."""
        return {
            "w_drift": self.w_drift,
            "w_space": self.w_space,
            "w_source": self.w_source,
            "w_time": self.w_time,
            "w_ais": self.w_ais,
        }

    def compute_source_evidence(self, val: Any) -> float:
        """Convenience method to compute source plausibility evidence."""
        if isinstance(val, dict):
            p = val.get("source_plausibility", 0.5)
        else:
            p = val
        if not isinstance(p, (int, float)) or not math.isfinite(p):
            return 0.5
        return self.evaluate_source_evidence(float(p))

    def compute_spatial_evidence(self, val: Any) -> float:
        """Convenience method to compute spatial compatibility evidence."""
        if isinstance(val, dict):
            d = val.get("geodesic_distance_m", val.get("vessel_source_distance_m", None))
        else:
            d = val
        if d is None or not isinstance(d, (int, float)) or not math.isfinite(d):
            return 0.0
        return self.evaluate_spatial_evidence(float(d))


    def compute_temporal_evidence(self, val: Any) -> float:
        """Convenience method to compute temporal compatibility evidence."""
        if isinstance(val, dict):
            gap = val.get("time_gap_seconds", val.get("gap_status", 600.0))
        else:
            gap = val
        gap_sec = parse_gap_seconds(gap)
        return self.evaluate_temporal_evidence(gap_sec)

    def compute_drift_evidence(self, val: Any) -> float:
        """Convenience method to compute drift consistency evidence."""
        if isinstance(val, dict):
            if "norm_centroid_score" in val:
                cen = float(val["norm_centroid_score"])
                part = float(val["norm_particle_score"])
                cov = float(val["coverage"])
                iou = float(val["iou"])
            else:
                cen_err = float(val.get("centroid_error_m", 1000.0))
                cen = math.exp(-cen_err / 1000.0)
                part_dist = float(val.get("mean_particle_distance_m", 1000.0))
                part = math.exp(-part_dist / 1000.0)
                cov = float(val.get("coverage_ratio", val.get("coverage", 0.0)))
                iou = float(val.get("iou", 0.0))
            return self.evaluate_drift_evidence(cen, part, cov, iou)
        return float(val)

    def compute_ais_quality_evidence(self, val: Any) -> float:
        """Convenience method to compute AIS track quality evidence."""
        if isinstance(val, dict):
            quality = str(val.get("track_quality", val.get("ais_track_quality", "GOOD")))
            gap = parse_gap_seconds(val.get("time_gap_seconds", val.get("gap_status", 0.0)))
        else:
            quality = str(val)
            gap = 0.0

        q_upper = quality.upper()
        mapping = {
            "HIGH": 1.0,
            "EXACT_PING": 1.0,
            "GOOD": 0.85,
            "MODERATE": 0.70,
            "NEAR_BOUNDARY_FIRST_PING": 0.70,
            "INTERPOLATED": 0.50,
            "POOR": 0.30,
            "UNKNOWN": 0.50,
        }
        score = mapping.get(q_upper, 0.50)
        if gap > 1200.0:
            score *= 0.75
        elif gap > 600.0:
            score *= 0.90
        return float(max(0.0, min(1.0, score)))

    def compute_combined_score(
        self,
        s_drift: float,
        s_space: float,
        s_source: float,
        s_time: float,
        s_ais: float,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Compute combined attribution evidence score."""
        if custom_weights is not None:
            total = sum(custom_weights.values())
            if not math.isclose(total, 1.0, rel_tol=1e-3):
                raise ValueError(f"Evidence weights must sum to 1.0, got {total}")
            w_d = custom_weights.get("w_drift", 0.0)
            w_sp = custom_weights.get("w_space", 0.0)
            w_so = custom_weights.get("w_source", 0.0)
            w_t = custom_weights.get("w_time", 0.0)
            w_a = custom_weights.get("w_ais", 0.0)
        else:
            w_d = self.w_drift
            w_sp = self.w_space
            w_so = self.w_source
            w_t = self.w_time
            w_a = self.w_ais

        score = w_d * s_drift + w_sp * s_space + w_so * s_source + w_t * s_time + w_a * s_ais
        return float(max(0.0, min(1.0, score)))

    def classify_evidence_state(
        self,
        overall_score: float,
        s_drift: float,
        s_space: float,
        s_source: float,
        s_time: float,
        s_ais: float,
    ) -> str:
        """Classify evidence quality state."""
        if s_ais < 0.30 or overall_score < self.th_low:
            return EvidenceQualityState.INSUFFICIENT_EVIDENCE
        if overall_score >= self.th_high and s_drift >= 0.45 and s_space >= 0.45:
            return EvidenceQualityState.HIGH_SUPPORT
        if overall_score >= self.th_mod:
            return EvidenceQualityState.MODERATE_SUPPORT
        if overall_score >= self.th_low:
            return EvidenceQualityState.LOW_SUPPORT
        return EvidenceQualityState.INSUFFICIENT_EVIDENCE

    def detect_conflicts(
        self,
        s_drift: float,
        s_space: float,
        s_source: float,
        s_time: float,
        s_ais: float,
        hypo: Dict[str, Any],
        comp: Dict[str, Any],
    ) -> Optional[str]:
        """Detect and describe evidence conflicts."""
        d_m = float(hypo.get("geodesic_distance_m", hypo.get("vessel_source_distance_m", 5000.0)))
        c_err = float(comp.get("centroid_error_m", 500.0))
        vname = str(hypo.get("vessel_name", "Vessel"))
        has_conf, conf_desc, _, _, _ = self.detect_conflicts_and_explain(
            s_drift, s_space, s_source, s_time, s_ais, d_m, c_err, vname
        )
        return conf_desc if (has_conf and conf_desc != "None") else None

    def evaluate_all(self) -> Tuple[List[HypothesisEvidence], List[VesselSummary]]:
        """Evaluate all hypotheses and return typed dataclass objects."""
        df_hyp, df_comp = self.load_inputs()
        merged = pd.merge(df_hyp, df_comp, on="hypothesis_id", suffixes=("", "_comp"))

        hyp_evidence_list = []
        for _, row in merged.iterrows():
            eval_res = self.evaluate_hypothesis(row.to_dict(), row.to_dict())
            hyp_evidence_list.append(eval_res)

        df_hyp_ev = pd.DataFrame(hyp_evidence_list)
        df_hyp_ev = df_hyp_ev.sort_values(
            by=["attribution_evidence_score", "drift_score", "spatial_score"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
        df_hyp_ev["hypothesis_rank"] = np.arange(1, len(df_hyp_ev) + 1)

        df_vessel_ev = self.aggregate_vessel_summaries(df_hyp_ev)

        hypos = []
        for _, r in df_hyp_ev.iterrows():
            hypos.append(HypothesisEvidence(
                hypothesis_id=str(r["hypothesis_id"]),
                rank=int(r["hypothesis_rank"]),
                mmsi=int(r["mmsi"]),
                vessel_name=str(r["vessel_name"]),
                observed_slick_id=str(r["observed_slick_id"]),
                attribution_evidence_score=float(r["attribution_evidence_score"]),
                evidence_quality_state=str(r["evidence_quality_state"]),
                s_drift=float(r["drift_score"]),
                s_space=float(r["spatial_score"]),
                s_source=float(r["source_score"]),
                s_time=float(r["temporal_score"]),
                s_ais=float(r["ais_quality_score"]),
                primary_strength=str(r["primary_strength"]),
                primary_weakness=str(r["primary_weakness"]),
                explanation=str(r["explanation"]),
                has_conflict=bool(r["has_conflict"]),
                conflict_description=str(r["conflict_description"]),
            ))

        vessels = []
        for _, r in df_vessel_ev.iterrows():
            vessels.append(VesselSummary(
                mmsi=int(r["mmsi"]),
                vessel_name=str(r["vessel_name"]),
                vessel_rank=int(r["vessel_rank"]),
                best_hypothesis_id=str(r["best_hypothesis_id"]),
                best_evidence_score=float(r["best_evidence_score"]),
                mean_evidence_score=float(r["mean_evidence_score"]),
                hypothesis_count=int(r["compatible_hypotheses_count"]),
                evidence_quality_state=str(r["vessel_evidence_state"]),
                primary_strength=str(r["best_hypothesis_strength"]),
                primary_weakness=str(r["best_hypothesis_weakness"]),
                explanation=str(r["best_hypothesis_explanation"]),
            ))

        return hypos, vessels

    def evaluate_source_evidence(self, plausibility: float) -> float:
        """Evaluate source plausibility evidence [0, 1]."""
        return max(0.0, min(1.0, float(plausibility)))

    def evaluate_spatial_evidence(self, distance_m: float) -> float:
        """
        Evaluate spatial compatibility between vessel and release point [0, 1].
        S_space = exp(-d / R_s).
        """
        if not math.isfinite(distance_m) or distance_m < 0.0:
            return 0.0
        return float(math.exp(-distance_m / self.spatial_scale_m))

    def evaluate_temporal_evidence(self, gap_seconds: float) -> float:
        """
        Evaluate temporal compatibility between AIS observation and release time [0, 1].
        S_time = exp(-gap / T_s).
        """
        if not math.isfinite(gap_seconds) or gap_seconds < 0.0:
            return 0.0
        return float(math.exp(-gap_seconds / self.temporal_scale_seconds))

    def evaluate_drift_evidence(
        self,
        norm_centroid: float,
        norm_particle: float,
        coverage: float,
        iou: float,
    ) -> float:
        """
        Evaluate physical drift consistency by aggregating Phase 8 metrics [0, 1].
        """
        score = (
            self.w_sub_centroid * max(0.0, min(1.0, norm_centroid)) +
            self.w_sub_particle * max(0.0, min(1.0, norm_particle)) +
            self.w_sub_coverage * max(0.0, min(1.0, coverage)) +
            self.w_sub_iou * max(0.0, min(1.0, iou))
        )
        return float(max(0.0, min(1.0, score)))

    def evaluate_ais_quality_evidence(self, track_quality: str, gap_seconds: float) -> float:
        """
        Evaluate observational reliability of the AIS track [0, 1].
        Strictly measures telemetry confidence, NEVER used as evidence of guilt.
        """
        base_scores = {
            "exact_ping": 1.00,
            "interpolated": 0.85,
            "near_boundary_first_ping": 0.70,
        }
        base = base_scores.get(str(track_quality).lower(), 0.60)
        # Moderate penalty for long gaps
        if gap_seconds > 1200.0:  # > 20 min
            base *= 0.75
        elif gap_seconds > 600.0:  # > 10 min
            base *= 0.90
        return float(max(0.0, min(1.0, base)))

    def determine_evidence_state(
        self,
        overall_score: float,
        s_drift: float,
        s_space: float,
        has_severe_conflict: bool,
    ) -> str:
        """Determine evidence-quality classification state."""
        if overall_score >= self.th_high and s_drift >= 0.45 and s_space >= 0.45 and not has_severe_conflict:
            return "HIGH_SUPPORT"
        if overall_score >= self.th_mod:
            return "MODERATE_SUPPORT"
        if overall_score >= self.th_low:
            return "LOW_SUPPORT"
        return "INSUFFICIENT_EVIDENCE"

    def detect_conflicts_and_explain(
        self,
        s_drift: float,
        s_space: float,
        s_source: float,
        s_time: float,
        s_ais: float,
        d_vessel_source_m: float,
        centroid_error_m: float,
        vessel_name: str,
    ) -> Tuple[bool, str, str, str, str]:
        """
        Identify conflicting evidence lines and generate human-readable explanations.

        Returns:
        --------
        Tuple[bool, str, str, str, str]:
            (has_conflict, conflict_description, primary_strength, primary_weakness, full_explanation)
        """
        scores_dict = {
            "Physical Drift Consistency": s_drift,
            "Spatial Compatibility": s_space,
            "Source Plausibility": s_source,
            "Temporal Compatibility": s_time,
            "AIS Track Quality": s_ais,
        }

        max_comp = max(scores_dict.items(), key=lambda x: x[1])
        min_comp = min(scores_dict.items(), key=lambda x: x[1])
        spread = max_comp[1] - min_comp[1]

        has_conflict = spread >= self.th_conflict_spread

        conflict_desc = "None"
        if has_conflict:
            if s_drift >= 0.60 and s_space < 0.35:
                conflict_desc = (
                    f"Physical drift model strongly matches observed slick, but candidate vessel was "
                    f"{d_vessel_source_m/1000.0:.1f} km away from release point at hypothesized release time."
                )
            elif s_space >= 0.60 and s_drift < 0.35:
                conflict_desc = (
                    f"Candidate vessel was in close proximity to release location, but forward drift simulation "
                    f"fails to reproduce the observed slick (centroid error {centroid_error_m:.0f} m)."
                )
            elif s_drift >= 0.60 and s_ais < 0.50:
                conflict_desc = (
                    "Strong physical consistency, but sparse/boundary AIS track limits observational certainty."
                )
            else:
                conflict_desc = (
                    f"Substantial divergence across evidence dimensions ({max_comp[0]}: {max_comp[1]:.2f} vs "
                    f"{min_comp[0]}: {min_comp[1]:.2f})."
                )

        primary_strength = f"{max_comp[0]} ({rating_label(max_comp[1])}, {max_comp[1]:.2f})"
        primary_weakness = f"{min_comp[0]} ({rating_label(min_comp[1])}, {min_comp[1]:.2f})"

        full_explanation = (
            f"{vessel_name}: Physical drift is {rating_label(s_drift)} ({s_drift:.2f}), "
            f"spatial compatibility is {rating_label(s_space)} ({s_space:.2f}), "
            f"source plausibility is {rating_label(s_source)} ({s_source:.2f}), "
            f"temporal alignment is {rating_label(s_time)} ({s_time:.2f}), and "
            f"AIS track quality is {rating_label(s_ais)} ({s_ais:.2f})."
        )
        if has_conflict:
            full_explanation += f" Notable discrepancy: {conflict_desc}"

        return has_conflict, conflict_desc, primary_strength, primary_weakness, full_explanation

    def evaluate_hypothesis(
        self,
        hyp_row: Dict[str, Any],
        comp_row: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate a single 4D source hypothesis across all evidence categories.
        """
        hyp_id = hyp_row["hypothesis_id"]
        vessel_name = str(hyp_row["vessel_name"])
        mmsi = int(hyp_row["mmsi"])

        # 1. Source Plausibility Evidence
        source_plaus = float(hyp_row.get("source_plausibility", 0.5))
        s_source = self.evaluate_source_evidence(source_plaus)

        # 2. Spatial Compatibility Evidence
        vessel_dist_m = float(hyp_row.get("vessel_source_distance_m", hyp_row.get("geodesic_distance_m", 5000.0)))
        s_space = self.evaluate_spatial_evidence(vessel_dist_m)

        # 3. Temporal Compatibility Evidence
        gap_sec = parse_gap_seconds(hyp_row.get("gap_status", hyp_row.get("time_gap_seconds", 600.0)))
        s_time = self.evaluate_temporal_evidence(gap_sec)

        # 4. Physical Drift Consistency Evidence
        if "norm_centroid_score" in comp_row:
            norm_cen = float(comp_row["norm_centroid_score"])
            norm_part = float(comp_row["norm_particle_score"])
            cov = float(comp_row.get("coverage", comp_row.get("coverage_ratio", 0.0)))
            iou = float(comp_row.get("iou", 0.0))
        else:
            cen_err = float(comp_row.get("centroid_error_m", 1000.0))
            norm_cen = math.exp(-cen_err / 1000.0)
            part_dist = float(comp_row.get("mean_particle_distance_m", 1000.0))
            norm_part = math.exp(-part_dist / 1000.0)
            cov = float(comp_row.get("coverage_ratio", comp_row.get("coverage", 0.0)))
            iou = float(comp_row.get("iou", 0.0))
        s_drift = self.evaluate_drift_evidence(norm_cen, norm_part, cov, iou)

        # 5. AIS Track Quality Evidence
        track_quality = str(hyp_row.get("ais_track_quality", "unknown"))
        s_ais = self.evaluate_ais_quality_evidence(track_quality, gap_sec)

        # Causal consistency metadata
        prec_status = str(hyp_row.get("causal_precedence_status", "PRE_EXISTING"))
        prec_score = float(hyp_row.get("causal_precedence_score", 1.0))
        prec_eligible = bool(hyp_row.get("causal_eligibility", True))
        age_plaus = str(hyp_row.get("source_age_plausibility", "HIGH"))
        age_score = float(hyp_row.get("source_age_score", 1.0))

        if self.causal_consistency_enabled:
            # Check causal temporal precedence
            if prec_status == "POST_EVENT_ONLY" or not prec_eligible:
                overall_score = self.ineligible_post_event_score
                evidence_state = "INELIGIBLE_POST_EVENT"
                prim_str = "None"
                prim_weak = "Causal Temporal Precedence (POST_EVENT_ONLY, 0.00)"
                explanation = (
                    f"{vessel_name}: INELIGIBLE for source attribution. "
                    f"Vessel first appeared after hypothesized release time ({hyp_row.get('causal_explanation', 'post-event presence only')})."
                )
                has_conflict = False
                conflict_desc = "None"
            else:
                # Modulate source plausibility by physical source-age spreading plausibility
                if self.enable_source_age_plausibility:
                    s_source = max(0.0, min(1.0, s_source * age_score))

                # Combined Evidence Score
                overall_score = (
                    self.w_drift * s_drift +
                    self.w_space * s_space +
                    self.w_source * s_source +
                    self.w_time * s_time +
                    self.w_ais * s_ais
                )
                overall_score = float(max(0.0, min(1.0, overall_score)))

                # Conflict Detection & Narrative Explanation
                has_conflict, conflict_desc, prim_str, prim_weak, explanation = self.detect_conflicts_and_explain(
                    s_drift=s_drift,
                    s_space=s_space,
                    s_source=s_source,
                    s_time=s_time,
                    s_ais=s_ais,
                    d_vessel_source_m=vessel_dist_m,
                    centroid_error_m=float(comp_row["centroid_error_m"]),
                    vessel_name=vessel_name,
                )

                evidence_state = self.determine_evidence_state(
                    overall_score=overall_score,
                    s_drift=s_drift,
                    s_space=s_space,
                    has_severe_conflict=(has_conflict and (s_space < 0.25 or s_drift < 0.25)),
                )
        else:
            # Baseline scoring
            overall_score = (
                self.w_drift * s_drift +
                self.w_space * s_space +
                self.w_source * s_source +
                self.w_time * s_time +
                self.w_ais * s_ais
            )
            overall_score = float(max(0.0, min(1.0, overall_score)))

            # Conflict Detection & Narrative Explanation
            has_conflict, conflict_desc, prim_str, prim_weak, explanation = self.detect_conflicts_and_explain(
                s_drift=s_drift,
                s_space=s_space,
                s_source=s_source,
                s_time=s_time,
                s_ais=s_ais,
                d_vessel_source_m=vessel_dist_m,
                centroid_error_m=float(comp_row["centroid_error_m"]),
                vessel_name=vessel_name,
            )

            evidence_state = self.determine_evidence_state(
                overall_score=overall_score,
                s_drift=s_drift,
                s_space=s_space,
                has_severe_conflict=(has_conflict and (s_space < 0.25 or s_drift < 0.25)),
            )

        return {
            "hypothesis_id": hyp_id,
            "candidate_id": hyp_row.get("candidate_id", ""),
            "mmsi": mmsi,
            "vessel_name": vessel_name,
            "vessel_type": hyp_row.get("vessel_type", ""),
            "observed_slick_id": str(hyp_row.get("source_slick_id", hyp_row.get("observed_slick_id", ""))),
            "release_timestamp": str(hyp_row.get("release_timestamp", hyp_row.get("estimated_release_time_utc", ""))),
            "release_lat": float(hyp_row.get("release_lat", hyp_row.get("estimated_release_lat", 0.0))),
            "release_lon": float(hyp_row.get("release_lon", hyp_row.get("estimated_release_lon", 0.0))),
            "vessel_lat": float(hyp_row.get("ais_lat", 0.0)),
            "vessel_lon": float(hyp_row.get("ais_lon", 0.0)),
            "vessel_source_distance_m": round(vessel_dist_m, 2),
            "ais_gap_seconds": round(gap_sec, 1),
            "ais_track_quality": track_quality,
            "centroid_error_m": float(comp_row.get("centroid_error_m", 0.0)),
            "mean_particle_distance_m": float(comp_row.get("mean_particle_distance_m", 0.0)),
            "coverage": float(comp_row.get("coverage", comp_row.get("coverage_ratio", 0.0))),
            "iou": float(comp_row.get("iou", 0.0)),
            # Normalized Evidence Vector E(H)
            "source_score": round(s_source, 4),
            "spatial_score": round(s_space, 4),
            "temporal_score": round(s_time, 4),
            "drift_score": round(s_drift, 4),
            "ais_quality_score": round(s_ais, 4),
            # Overall Attribution Evidence Score
            "attribution_evidence_score": round(overall_score, 4),
            "evidence_quality_state": evidence_state,
            "has_conflict": bool(has_conflict),
            "conflict_description": conflict_desc,
            "primary_strength": prim_str,
            "primary_weakness": prim_weak,
            "explanation": explanation,
            # Causal Consistency Metadata
            "causal_precedence_status": prec_status,
            "causal_precedence_score": prec_score,
            "causal_eligibility": prec_eligible,
            "source_age_plausibility": age_plaus,
            "source_age_score": age_score,
        }

    def aggregate_vessel_summaries(self, df_hyp_evidence: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate hypothesis-level evidence into vessel-level summaries without
        collapsing distinct releases prematurely.
        """
        vessel_records = []
        for mmsi, group in df_hyp_evidence.groupby("mmsi"):
            if self.causal_consistency_enabled and "causal_eligibility" in group.columns:
                eligible_group = group[group["causal_eligibility"] == True]
                target_group = eligible_group if len(eligible_group) > 0 else group
            else:
                target_group = group

            best_idx = target_group["attribution_evidence_score"].idxmax()
            best_row = target_group.loc[best_idx]

            vessel_records.append({
                "mmsi": int(mmsi),
                "vessel_name": str(best_row["vessel_name"]),
                "vessel_type": str(best_row["vessel_type"]),
                "best_hypothesis_id": str(best_row["hypothesis_id"]),
                "best_evidence_score": float(best_row["attribution_evidence_score"]),
                "mean_evidence_score": round(float(group["attribution_evidence_score"].mean()), 4),
                "compatible_hypotheses_count": int(len(group)),
                "best_associated_slick": str(best_row["observed_slick_id"]),
                "vessel_evidence_state": str(best_row["evidence_quality_state"]),
                "release_time_min_utc": str(group["release_timestamp"].min()),
                "release_time_max_utc": str(group["release_timestamp"].max()),
                "source_lat_min": round(float(group["release_lat"].min()), 6),
                "source_lat_max": round(float(group["release_lat"].max()), 6),
                "source_lon_min": round(float(group["release_lon"].min()), 6),
                "source_lon_max": round(float(group["release_lon"].max()), 6),
                "best_hypothesis_strength": str(best_row["primary_strength"]),
                "best_hypothesis_weakness": str(best_row["primary_weakness"]),
                "best_hypothesis_explanation": str(best_row["explanation"]),
            })

        df_vessel = pd.DataFrame(vessel_records)
        df_vessel = df_vessel.sort_values(
            by=["best_evidence_score", "mean_evidence_score"],
            ascending=[False, False],
        ).reset_index(drop=True)
        df_vessel["vessel_rank"] = np.arange(1, len(df_vessel) + 1)
        return df_vessel

    def run(self) -> Dict[str, Any]:
        """
        Execute Phase 9 Explainable Multi-Evidence Attribution Engine across Case 001.
        """
        logger.info("Starting Phase 9 Multi-Evidence Attribution Engine for %s...", self.case_id)
        df_hyp, df_comp = self.load_inputs()

        # Merge Phase 6 hypotheses with Phase 8 comparison metrics
        merged = pd.merge(df_hyp, df_comp, on="hypothesis_id", suffixes=("", "_comp"))

        hyp_evidence_list: List[Dict[str, Any]] = []
        for _, row in merged.iterrows():
            eval_res = self.evaluate_hypothesis(row.to_dict(), row.to_dict())
            hyp_evidence_list.append(eval_res)

        df_hyp_ev = pd.DataFrame(hyp_evidence_list)
        # Rank hypotheses descending by attribution_evidence_score
        df_hyp_ev = df_hyp_ev.sort_values(
            by=["attribution_evidence_score", "drift_score", "spatial_score"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
        df_hyp_ev["hypothesis_rank"] = np.arange(1, len(df_hyp_ev) + 1)

        # Aggregate vessel summaries
        df_vessel_ev = self.aggregate_vessel_summaries(df_hyp_ev)

        # Save outputs
        # 1. Hypothesis Evidence CSV & JSON
        hyp_csv_path = self.output_dir / f"{self.case_id}_hypothesis_evidence.csv"
        df_hyp_ev.to_csv(hyp_csv_path, index=False)
        logger.info("Saved hypothesis evidence CSV to %s (%d records)", hyp_csv_path, len(df_hyp_ev))

        hyp_json_path = self.output_dir / f"{self.case_id}_hypothesis_evidence.json"
        with open(hyp_json_path, "w", encoding="utf-8") as jf:
            json.dump(df_hyp_ev.to_dict(orient="records"), jf, indent=2)
        logger.info("Saved hypothesis evidence JSON to %s", hyp_json_path)

        # 2. Vessel Summary CSV & JSON
        vessel_csv_path = self.output_dir / f"{self.case_id}_vessel_summary.csv"
        df_vessel_ev.to_csv(vessel_csv_path, index=False)
        logger.info("Saved vessel summary CSV to %s (%d vessels)", vessel_csv_path, len(df_vessel_ev))

        vessel_json_path = self.output_dir / f"{self.case_id}_vessel_summary.json"
        with open(vessel_json_path, "w", encoding="utf-8") as vf:
            json.dump(df_vessel_ev.to_dict(orient="records"), vf, indent=2)
        logger.info("Saved vessel summary JSON to %s", vessel_json_path)

        # 3. Evidence Explanation Report (Markdown)
        report_path = self.output_dir / f"{self.case_id}_evidence_explanation_report.md"
        self._write_explanation_report(df_hyp_ev, df_vessel_ev, report_path)

        # 4. Publication-Grade Diagnostic Visualization
        diag_path = self.output_dir / f"{self.case_id}_attribution_diagnostic.png"
        self._plot_attribution_diagnostic(df_hyp_ev, df_vessel_ev, diag_path)

        summary = {
            "case_id": self.case_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_hypotheses_evaluated": len(df_hyp_ev),
            "total_vessels_evaluated": len(df_vessel_ev),
            "evidence_weights": {
                "drift_consistency": self.w_drift,
                "spatial_compatibility": self.w_space,
                "source_plausibility": self.w_source,
                "temporal_compatibility": self.w_time,
                "ais_track_quality": self.w_ais,
            },
            "top_hypotheses": df_hyp_ev.head(5)[
                ["hypothesis_rank", "hypothesis_id", "vessel_name", "observed_slick_id", "attribution_evidence_score", "evidence_quality_state"]
            ].to_dict(orient="records"),
            "top_vessels": df_vessel_ev.head(5)[
                ["vessel_rank", "mmsi", "vessel_name", "best_hypothesis_id", "best_evidence_score", "vessel_evidence_state"]
            ].to_dict(orient="records"),
            "evidence_quality_distribution": df_hyp_ev["evidence_quality_state"].value_counts().to_dict(),
            "conflict_count": int(df_hyp_ev["has_conflict"].sum()),
            "scientific_guardrail_notice": (
                "Attribution evidence scores evaluate physical and spatiotemporal compatibility only. "
                "Scores do NOT represent probabilities of guilt or liability. No vessel is confirmed as responsible."
            ),
            "reference_pipeline_notice": "Pipeline rupture coordinates were strictly excluded from attribution calculations.",
        }

        logger.info("Phase 9 Multi-Evidence Attribution Engine execution complete.")
        return summary

    def _write_explanation_report(
        self,
        df_hyp_ev: pd.DataFrame,
        df_vessel_ev: pd.DataFrame,
        save_path: Path,
    ) -> None:
        """Write human-readable narrative explanation report in Markdown."""
        lines = [
            "# SIH26143 Phase 9: Multi-Evidence Attribution Report",
            "",
            f"**Case**: `{self.case_id}`  ",
            f"**Generated UTC**: `{datetime.now(timezone.utc).isoformat()}`  ",
            f"**Evaluated**: {len(df_hyp_ev)} 4D Source Hypotheses across {len(df_vessel_ev)} Unique Vessels  ",
            "",
            "> [!IMPORTANT]",
            "> **Scientific Notice**: Attribution evidence scores quantify physical and spatiotemporal compatibility. ",
            "> They do NOT represent calibrated probabilities of guilt or legal culpability. ",
            "> Pipeline corridor coordinates were strictly excluded from algorithm inputs.",
            "",
            "---",
            "",
            "## 1. Top Ranked Hypotheses",
            "",
            "| Rank | Hypothesis ID | Vessel Name | Observed Slick | Score | State | Drift | Space | Source | Time | AIS Quality | Primary Strength | Primary Weakness |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for _, r in df_hyp_ev.iterrows():
            lines.append(
                f"| {r['hypothesis_rank']} | **{r['hypothesis_id']}** | {r['vessel_name']} | `{r['observed_slick_id']}` | "
                f"**{r['attribution_evidence_score']:.4f}** | `{r['evidence_quality_state']}` | "
                f"{r['drift_score']:.2f} | {r['spatial_score']:.2f} | {r['source_score']:.2f} | "
                f"{r['temporal_score']:.2f} | {r['ais_quality_score']:.2f} | "
                f"{r['primary_strength']} | {r['primary_weakness']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 2. Vessel-Level Aggregated Summaries",
            "",
            "| Vessel Rank | MMSI | Vessel Name | Best Hypothesis | Best Score | Mean Score | Compatible Count | Evidence State | Best Strength | Best Weakness |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for _, v in df_vessel_ev.iterrows():
            lines.append(
                f"| {v['vessel_rank']} | `{v['mmsi']}` | **{v['vessel_name']}** | {v['best_hypothesis_id']} | "
                f"**{v['best_evidence_score']:.4f}** | {v['mean_evidence_score']:.4f} | {v['compatible_hypotheses_count']} | "
                f"`{v['vessel_evidence_state']}` | {v['best_hypothesis_strength']} | {v['best_hypothesis_weakness']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 3. Explanations & Conflict Analysis",
            "",
        ])

        for _, r in df_hyp_ev.head(5).iterrows():
            lines.append(f"### Rank {r['hypothesis_rank']}: {r['hypothesis_id']} ({r['vessel_name']})")
            lines.append(f"- **Evidence Quality State**: `{r['evidence_quality_state']}`")
            lines.append(f"- **Narrative**: {r['explanation']}")
            if r["has_conflict"]:
                lines.append(f"- **Evidence Conflict**: {r['conflict_description']}")
            lines.append("")

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Saved evidence explanation report to %s", save_path)

    def _plot_attribution_diagnostic(
        self,
        df_hyp_ev: pd.DataFrame,
        df_vessel_ev: pd.DataFrame,
        save_path: Path,
    ) -> None:
        """Render 4-panel publication-quality diagnostic figure."""
        fig, axes = plt.subplots(2, 2, figsize=(20, 14), dpi=200)
        fig.suptitle(
            "SIH26143 Phase 9: Explainable Multi-Evidence Attribution Diagnostic\n"
            "Hypothesis Ranking, Evidence Decomposition, and Vessel Aggregation",
            fontsize=15,
            fontweight="bold",
            y=0.98,
        )

        # -------------------------------------------------------------------
        # Panel 1: Horizontal Stacked Evidence Breakdown for Top 10 Hypotheses
        # -------------------------------------------------------------------
        ax1 = axes[0, 0]
        ax1.set_title("Panel 1: Ranked 4D Hypotheses — Evidence Decomposition", fontsize=11, fontweight="bold")

        top_hyp = df_hyp_ev.head(10).iloc[::-1]  # Invert so rank 1 is at top
        y_pos = np.arange(len(top_hyp))
        labels = [f"#{r['hypothesis_rank']} {r['hypothesis_id']} ({r['vessel_name'][:9]})" for _, r in top_hyp.iterrows()]

        w_drift_val = top_hyp["drift_score"] * self.w_drift
        w_space_val = top_hyp["spatial_score"] * self.w_space
        w_source_val = top_hyp["source_score"] * self.w_source
        w_time_val = top_hyp["temporal_score"] * self.w_time
        w_ais_val = top_hyp["ais_quality_score"] * self.w_ais

        ax1.barh(y_pos, w_drift_val, color="#00C853", label=f"Drift Consistency (w={self.w_drift})")
        ax1.barh(y_pos, w_space_val, left=w_drift_val, color="#29B6F6", label=f"Spatial Compat (w={self.w_space})")
        ax1.barh(y_pos, w_source_val, left=w_drift_val + w_space_val, color="#FFB300", label=f"Source Plaus (w={self.w_source})")
        ax1.barh(y_pos, w_time_val, left=w_drift_val + w_space_val + w_source_val, color="#AB47BC", label=f"Temporal Compat (w={self.w_time})")
        ax1.barh(y_pos, w_ais_val, left=w_drift_val + w_space_val + w_source_val + w_time_val, color="#78909C", label=f"AIS Quality (w={self.w_ais})")

        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(labels, fontsize=8)
        ax1.set_xlabel("Attribution Evidence Score [0, 1]", fontsize=10)
        ax1.set_xlim(0, 1.0)
        ax1.axvline(self.th_high, color="darkgreen", linestyle="--", lw=1.2, label=f"High Support ({self.th_high})")
        ax1.axvline(self.th_mod, color="goldenrod", linestyle=":", lw=1.2, label=f"Moderate Support ({self.th_mod})")
        ax1.grid(True, linestyle="--", alpha=0.4, axis="x")
        ax1.legend(loc="lower right", fontsize=7.5)

        # -------------------------------------------------------------------
        # Panel 2: Vessel-Level Aggregated Summary Rankings
        # -------------------------------------------------------------------
        ax2 = axes[0, 1]
        ax2.set_title("Panel 2: Vessel Summary — Best Evidence Score & Hypothesis Count", fontsize=11, fontweight="bold")

        top_vessels = df_vessel_ev.head(10).iloc[::-1]
        y_v = np.arange(len(top_vessels))
        v_labels = [f"#{r['vessel_rank']} {r['vessel_name']} (MMSI {r['mmsi']})" for _, r in top_vessels.iterrows()]

        colors = ["#00E676" if s == "HIGH_SUPPORT" else "#FFD54F" if s == "MODERATE_SUPPORT" else "#FF8A80"
                  for s in top_vessels["vessel_evidence_state"]]

        bars = ax2.barh(y_v, top_vessels["best_evidence_score"], color=colors, height=0.55, edgecolor="black")
        ax2.set_yticks(y_v)
        ax2.set_yticklabels(v_labels, fontsize=8)
        ax2.set_xlabel("Best Hypothesis Attribution Score", fontsize=10)
        ax2.set_xlim(0, 1.0)
        ax2.grid(True, linestyle="--", alpha=0.4, axis="x")

        # Annotate count
        for bar, (_, r) in zip(bars, top_vessels.iterrows()):
            ax2.text(
                bar.get_width() + 0.015, bar.get_y() + bar.get_height() / 2,
                f"Score: {r['best_evidence_score']:.3f} ({r['compatible_hypotheses_count']} hyps) [{r['vessel_evidence_state']}]",
                va="center", fontsize=8, fontweight="bold",
            )

        # -------------------------------------------------------------------
        # Panel 3: Evidence Conflict Analysis (Spatial vs Drift Scatter)
        # -------------------------------------------------------------------
        ax3 = axes[1, 0]
        ax3.set_title("Panel 3: Evidence Conflict Space (Spatial Proximity vs Physical Drift)", fontsize=11, fontweight="bold")

        scatter = ax3.scatter(
            df_hyp_ev["spatial_score"],
            df_hyp_ev["drift_score"],
            c=df_hyp_ev["attribution_evidence_score"],
            s=df_hyp_ev["temporal_score"] * 280,
            cmap="viridis",
            alpha=0.85,
            edgecolors="black",
            linewidth=1.2,
        )
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label("Overall Attribution Evidence Score", fontsize=9)

        # Label points for top candidates
        for _, r in df_hyp_ev.head(15).iterrows():
            ax3.text(
                r["spatial_score"] + 0.01,
                r["drift_score"] + 0.01,
                f"{r['hypothesis_id']} ({r['vessel_name'][:6]})",
                fontsize=7.5,
                alpha=0.85,
            )

        ax3.set_xlabel("Spatial Compatibility Score [0, 1]", fontsize=10)
        ax3.set_ylabel("Physical Drift Consistency Score [0, 1]", fontsize=10)
        ax3.set_xlim(0, 1.05)
        ax3.set_ylim(0, 1.05)
        ax3.plot([0, 1], [0, 1], color="gray", linestyle=":", alpha=0.5, label="Concordance Diagonal")
        ax3.grid(True, linestyle="--", alpha=0.4)
        ax3.legend(loc="upper left", fontsize=8)

        # -------------------------------------------------------------------
        # Panel 4: Radar / Profile Chart of Top Candidate Hypotheses
        # -------------------------------------------------------------------
        ax4 = axes[1, 1]
        ax4.set_title("Panel 4: Evidence Profiles of Top 3 Candidate Hypotheses", fontsize=11, fontweight="bold")

        categories = ["Drift", "Spatial", "Source", "Temporal", "AIS Quality"]
        top_3 = df_hyp_ev.head(3)
        x_indices = np.arange(len(categories))
        width = 0.25

        palette = ["#2979FF", "#FF6D00", "#00C853"]
        for i, (_, r) in enumerate(top_3.iterrows()):
            vals = [
                r["drift_score"],
                r["spatial_score"],
                r["source_score"],
                r["temporal_score"],
                r["ais_quality_score"],
            ]
            offset = (i - 1) * width
            ax4.bar(
                x_indices + offset, vals, width=width,
                color=palette[i % len(palette)], alpha=0.85, edgecolor="black",
                label=f"#{r['hypothesis_rank']}: {r['hypothesis_id']} ({r['vessel_name'][:8]}, {r['attribution_evidence_score']:.3f})"
            )

        ax4.set_xticks(x_indices)
        ax4.set_xticklabels(categories, fontsize=9, fontweight="bold")
        ax4.set_ylabel("Normalized Evidence Value [0, 1]", fontsize=10)
        ax4.set_ylim(0, 1.15)
        ax4.grid(True, linestyle="--", alpha=0.4, axis="y")
        ax4.legend(loc="upper right", fontsize=8)

        # Watermark notice
        fig.text(
            0.5, 0.01,
            "SCIENTIFIC NOTICE: Attribution evidence scores evaluate physical and spatiotemporal compatibility only. "
            "Does NOT prove guilt or responsibility. Pipeline corridor coordinates were strictly excluded from algorithm inputs.",
            ha="center", fontsize=9, style="italic", color="#424242",
        )

        plt.tight_layout(rect=[0, 0.02, 1, 0.95])
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
        logger.info("Saved attribution diagnostic figure to %s", save_path)
