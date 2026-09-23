"""
Phase 6: 4D Source Hypothesis Generation Engine.

Converts Phase 5 candidate-vessel/source-time relationships into explicit
4D source hypotheses:
    H = (vessel, release_location, release_time) = (v, x_r, y_r, t_r)

Preserves the complete multidimensional relationship without collapsing into
a single scalar score or assigning responsibility.
Prepares structured inputs for downstream forward counterfactual simulations (Phase 7).

Scientific Guardrails:
- No guilt or attribution ranking is computed in this phase.
- Both AIS vessel position and hypothesized release location are independently preserved.
- All spatial separations use geodesic metric calculations in meters.
- The known pipeline rupture point is strictly excluded from hypothesis generation.
"""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.common.case_loader import load_case_config
from src.common.config import load_config
from src.common.geo import haversine_distance_m, haversine_distance_km, validate_coordinates
from src.common.logging import get_logger
from src.common.paths import (
    AIS_PROCESSED_DIR,
    DRIFT_PROCESSED_DIR,
    HYPOTHESES_PROCESSED_DIR,
    SATELLITE_PROCESSED_DIR,
    ensure_dir_exists,
    resolve_path,
)
from src.common.time_utils import parse_utc_timestamp
from src.attribution.causal_consistency import (
    determine_temporal_precedence,
    evaluate_source_age_plausibility,
    CausalPrecedenceStatus,
    SourceAgePlausibility,
)

logger = get_logger(__name__)


class SourceHypothesisGenerator4D:
    """
    Engine for generating explicit 4D source hypotheses H = (v, x_r, y_r, t_r).
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

        hyp_cfg = self.default_cfg.get("source_hypothesis_generation", {})
        causal_cfg = self.default_cfg.get("causal_consistency", {})
        if config_override:
            hyp_cfg.update(config_override.get("source_hypothesis_generation", config_override))
            if "causal_consistency" in config_override:
                causal_cfg.update(config_override["causal_consistency"])

        self.spatial_compatibility_radius_m = float(
            hyp_cfg.get("spatial_compatibility_radius_m", 15000.0)
        )
        self.min_source_plausibility = float(
            hyp_cfg.get("min_source_plausibility", 0.10)
        )
        dedup_cfg = hyp_cfg.get("deduplication_precision", {})
        self.dedup_coord_decimals = int(dedup_cfg.get("coord_decimals", 5))
        self.dedup_time_seconds = int(dedup_cfg.get("time_seconds", 60))

        # Causal consistency parameters
        self.causal_enabled = bool(causal_cfg.get("enabled", False))
        self.causal_tol_seconds = float(causal_cfg.get("at_release_tolerance_seconds", 300.0))
        self.causal_max_gap_seconds = float(causal_cfg.get("max_interpolation_gap_seconds", 3600.0))
        self.causal_min_positions = int(causal_cfg.get("min_positions_for_precedence", 2))

        # Output directory & file paths
        self.output_dir = ensure_dir_exists(
            output_dir if output_dir is not None else HYPOTHESES_PROCESSED_DIR
        )
        self.hypotheses_csv_path = self.output_dir / f"{case_id}_source_hypotheses_4d.csv"
        self.hypotheses_json_path = self.output_dir / f"{case_id}_source_hypotheses_4d.json"
        self.hypotheses_geojson_path = self.output_dir / f"{case_id}_source_hypotheses_4d.geojson"
        self.summary_json_path = self.output_dir / f"{case_id}_source_hypotheses_summary.json"
        self.diagnostic_png_path = self.output_dir / f"{case_id}_source_hypotheses_diagnostic.png"

        # Canonical generic paths
        self.canonical_csv_path = self.output_dir / "source_hypotheses.csv"
        self.canonical_json_path = self.output_dir / "source_hypotheses.json"
        self.canonical_geojson_path = self.output_dir / "source_hypotheses.geojson"

    def generate_hypotheses(
        self,
        candidate_vessels_csv: Optional[Union[str, Path]] = None,
        source_hypotheses_csv: Optional[Union[str, Path]] = None,
        ais_normalized_csv: Optional[Union[str, Path]] = None,
        candidate_slicks_csv: Optional[Union[str, Path]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute 4D hypothesis generation from Phase 5 candidate vessels
        and Phase 4 backward drift source hypotheses.
        """
        # Resolve candidate vessels path
        if candidate_vessels_csv is None:
            cand_path = AIS_PROCESSED_DIR / f"{self.case_id}_candidate_vessels.csv"
        else:
            cand_path = resolve_path(candidate_vessels_csv)

        if not cand_path.exists():
            raise FileNotFoundError(f"Candidate vessels CSV not found: {cand_path}")

        # Resolve Phase 4 source hypotheses path
        if source_hypotheses_csv is None:
            src_hyp_path = DRIFT_PROCESSED_DIR / f"{self.case_id}_source_hypotheses.csv"
        else:
            src_hyp_path = resolve_path(source_hypotheses_csv)

        if not src_hyp_path.exists():
            raise FileNotFoundError(f"Source hypotheses CSV not found: {src_hyp_path}")

        df_candidates = pd.read_csv(cand_path)
        df_src_hypotheses = pd.read_csv(src_hyp_path)

        # Load normalized AIS for causal precedence checking if available
        vessel_tracks: Dict[int, pd.DataFrame] = {}
        if ais_normalized_csv is not None:
            ais_path = resolve_path(ais_normalized_csv)
        else:
            ais_path = AIS_PROCESSED_DIR / f"{self.case_id}_ais_normalized.csv"

        if ais_path.exists():
            try:
                df_ais = pd.read_csv(ais_path)
                for mmsi_val, grp in df_ais.groupby("mmsi"):
                    vessel_tracks[int(mmsi_val)] = grp
                logger.debug(f"Loaded {len(vessel_tracks)} vessel tracks for causal precedence.")
            except Exception as e:
                logger.warning(f"Could not load normalized AIS for causal precedence: {e}")

        # Load candidate slicks for physical age plausibility checking if available
        slicks_dict: Dict[str, Dict[str, Any]] = {}
        if candidate_slicks_csv is not None:
            slicks_path = resolve_path(candidate_slicks_csv)
        else:
            slicks_path = SATELLITE_PROCESSED_DIR / f"{self.case_id}_candidate_slicks.csv"

        if slicks_path.exists():
            try:
                df_slicks = pd.read_csv(slicks_path)
                for _, s_row in df_slicks.iterrows():
                    slicks_dict[str(s_row["candidate_id"])] = s_row.to_dict()
                logger.debug(f"Loaded {len(slicks_dict)} candidate slicks for age plausibility.")
            except Exception as e:
                logger.warning(f"Could not load candidate slicks for age plausibility: {e}")

        logger.info(
            f"Loaded {len(df_candidates)} candidate associations and "
            f"{len(df_src_hypotheses)} source hypotheses."
        )

        # Index Phase 4 source hypotheses by hypothesis_id
        src_hyp_dict = {}
        for _, row in df_src_hypotheses.iterrows():
            src_hyp_dict[row["hypothesis_id"]] = row.to_dict()

        raw_hypotheses: List[Dict[str, Any]] = []

        # Iterate over retained candidate vessels
        for _, cand in df_candidates.iterrows():
            cand_id = cand["candidate_id"]
            mmsi = int(cand["mmsi"])
            v_name = str(cand.get("vessel_name", "UNKNOWN"))
            imo = str(cand.get("imo", "UNKNOWN"))
            v_type = str(cand.get("vessel_type", "UNKNOWN"))
            v_lat = float(cand["candidate_position_lat"])
            v_lon = float(cand["candidate_position_lon"])
            v_time_str = str(cand["candidate_timestamp_utc"])
            v_track_qual = str(cand.get("ais_track_quality", "unknown"))
            v_gap = cand.get("ais_gap_seconds", 0.0)

            src_hyp_id = cand.get("source_hypothesis_id")
            if src_hyp_id not in src_hyp_dict:
                logger.warning(f"Candidate {cand_id} referenced unknown source hypothesis {src_hyp_id}")
                continue

            src_hyp = src_hyp_dict[src_hyp_id]
            r_lat = float(src_hyp["centroid_lat"])
            r_lon = float(src_hyp["centroid_lon"])
            r_time_str = str(src_hyp["estimated_release_time_utc"])
            src_age = float(src_hyp["source_age_hours"])
            src_plausibility = float(src_hyp["source_plausibility"])

            # Filter non-negligible source plausibility
            if src_plausibility < self.min_source_plausibility:
                logger.debug(
                    f"Candidate {cand_id} skipped: source plausibility {src_plausibility:.3f} < {self.min_source_plausibility}"
                )
                continue

            # Compute geodesic distance in meters (strict geodesic requirement)
            dist_m = haversine_distance_m(v_lat, v_lon, r_lat, r_lon)

            # Spatial compatibility check
            if dist_m > self.spatial_compatibility_radius_m:
                logger.debug(
                    f"Candidate {cand_id} skipped: distance {dist_m:.1f} m > {self.spatial_compatibility_radius_m} m"
                )
                continue

            # 1. Causal temporal precedence evaluation
            track_df = vessel_tracks.get(mmsi)
            prec_res = determine_temporal_precedence(
                vessel_track=track_df,
                release_time=r_time_str,
                at_release_tolerance_seconds=self.causal_tol_seconds,
                max_interpolation_gap_seconds=self.causal_max_gap_seconds,
                min_pings_for_precedence=self.causal_min_positions,
            )

            # 2. Source-age physical plausibility evaluation
            cand_slick_ref = str(src_hyp.get("candidate_id", ""))
            slick_info = slicks_dict.get(cand_slick_ref, {})
            slick_area = float(slick_info["area_km2"]) if (slick_info and "area_km2" in slick_info) else None
            aspect_ratio = float(slick_info["aspect_ratio"]) if (slick_info and "aspect_ratio" in slick_info) else None
            age_res = evaluate_source_age_plausibility(
                source_age_hours=src_age,
                observed_slick_area_km2=slick_area,
                aspect_ratio=aspect_ratio,
            )

            # Construct raw hypothesis tuple (strictly preserving original schema)
            raw_hypotheses.append({
                "candidate_id": cand_id,
                "mmsi": mmsi,
                "vessel_name": v_name,
                "imo": imo,
                "vessel_type": v_type,
                "release_lat": round(r_lat, 6),
                "release_lon": round(r_lon, 6),
                "release_timestamp": r_time_str,
                "source_age_hours": src_age,
                "source_plausibility": round(src_plausibility, 4),
                "ais_lat": round(v_lat, 6),
                "ais_lon": round(v_lon, 6),
                "vessel_source_distance_m": round(dist_m, 2),
                "ais_track_quality": v_track_qual,
                "gap_status": f"{float(v_gap):.1f}s" if pd.notna(v_gap) else "0.0s",
                "compatibility_status": "COMPATIBLE",
                "source_hypothesis_id": src_hyp_id,
                "source_slick_id": str(src_hyp.get("candidate_id", "")),
                # Causal consistency fields
                "causal_precedence_status": prec_res.status,
                "causal_precedence_score": prec_res.score,
                "causal_eligibility": prec_res.is_eligible,
                "pre_release_evidence": prec_res.pre_release_evidence,
                "post_release_evidence": prec_res.post_release_evidence,
                "source_age_plausibility": age_res.plausibility,
                "source_age_score": age_res.score,
                "source_age_explanation": age_res.explanation,
                "causal_explanation": prec_res.explanation,
            })

        # Deduplicate identical (vessel, release_location, release_time) tuples
        deduplicated = self._deduplicate_hypotheses(raw_hypotheses)

        # Assign unique 4D hypothesis IDs
        for idx, hyp in enumerate(deduplicated, start=1):
            hyp["hypothesis_id"] = f"4DH_{idx:04d}"

        logger.info(
            f"Generated {len(deduplicated)} explicit 4D source hypotheses "
            f"across {len({h['mmsi'] for h in deduplicated})} unique vessels."
        )

        return deduplicated

    def _deduplicate_hypotheses(
        self, hypotheses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate exact duplicates without merging hypotheses that differ in
        vessel, release location, or release time.
        """
        seen_signatures = set()
        deduped = []

        for hyp in hypotheses:
            mmsi = hyp["mmsi"]
            r_lat_round = round(hyp["release_lat"], self.dedup_coord_decimals)
            r_lon_round = round(hyp["release_lon"], self.dedup_coord_decimals)

            # Quantize release time by dedup_time_seconds
            dt = parse_utc_timestamp(hyp["release_timestamp"])
            epoch_sec = int(dt.timestamp())
            time_bin = epoch_sec // self.dedup_time_seconds

            signature = (mmsi, r_lat_round, r_lon_round, time_bin)
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                deduped.append(hyp)

        return deduped

    def export_artifacts(
        self,
        hypotheses: List[Dict[str, Any]],
        candidate_vessels_csv: Optional[Union[str, Path]] = None,
        source_hypotheses_csv: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Path]:
        """
        Export hypothesis artifacts to CSV, JSON, GeoJSON, summary JSON,
        and generate a diagnostic map figure.
        """
        # 1. Export CSV
        df = pd.DataFrame(hypotheses)
        cols_order = [
            "hypothesis_id",
            "candidate_id",
            "mmsi",
            "vessel_name",
            "imo",
            "vessel_type",
            "release_lat",
            "release_lon",
            "release_timestamp",
            "source_age_hours",
            "source_plausibility",
            "ais_lat",
            "ais_lon",
            "vessel_source_distance_m",
            "ais_track_quality",
            "gap_status",
            "compatibility_status",
        ]
        # Include optional source linkage columns if present
        extra_cols = [c for c in df.columns if c not in cols_order]
        final_cols = cols_order + extra_cols
        df = df[final_cols]

        df.to_csv(self.hypotheses_csv_path, index=False)
        df.to_csv(self.canonical_csv_path, index=False)
        logger.info(f"Saved 4D hypotheses CSV to {self.hypotheses_csv_path}")

        # 2. Export JSON
        with open(self.hypotheses_json_path, "w", encoding="utf-8") as f:
            json.dump(hypotheses, f, indent=2)
        with open(self.canonical_json_path, "w", encoding="utf-8") as f:
            json.dump(hypotheses, f, indent=2)
        logger.info(f"Saved 4D hypotheses JSON to {self.hypotheses_json_path}")

        # 3. Export GeoJSON
        geojson_data = self._build_geojson(hypotheses)
        with open(self.hypotheses_geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2)
        with open(self.canonical_geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2)
        logger.info(f"Saved 4D hypotheses GeoJSON to {self.hypotheses_geojson_path}")

        # 4. Export Summary JSON
        summary_data = self._build_summary(hypotheses)
        with open(self.summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        logger.info(f"Saved summary JSON to {self.summary_json_path}")

        # 5. Export Diagnostic Plot
        self._plot_diagnostic_figure(hypotheses)

        return {
            "csv": self.hypotheses_csv_path,
            "json": self.hypotheses_json_path,
            "geojson": self.hypotheses_geojson_path,
            "summary": self.summary_json_path,
            "diagnostic": self.diagnostic_png_path,
        }

    def _build_geojson(self, hypotheses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build GeoJSON FeatureCollection containing:
        1. Hypothesized Release Location points.
        2. Geodesic displacement vector lines connecting vessel position to release point.
        """
        features = []

        for hyp in hypotheses:
            props = dict(hyp)

            # Feature 1: Hypothesized release point
            point_feature = {
                "type": "Feature",
                "id": f"{hyp['hypothesis_id']}_release_point",
                "geometry": {
                    "type": "Point",
                    "coordinates": [hyp["release_lon"], hyp["release_lat"]],
                },
                "properties": {
                    **props,
                    "feature_type": "hypothesized_release_location",
                },
            }
            features.append(point_feature)

            # Feature 2: Displacement vector (LineString from vessel to release location)
            line_feature = {
                "type": "Feature",
                "id": f"{hyp['hypothesis_id']}_displacement_vector",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [hyp["ais_lon"], hyp["ais_lat"]],
                        [hyp["release_lon"], hyp["release_lat"]],
                    ],
                },
                "properties": {
                    "hypothesis_id": hyp["hypothesis_id"],
                    "candidate_id": hyp["candidate_id"],
                    "mmsi": hyp["mmsi"],
                    "vessel_name": hyp["vessel_name"],
                    "vessel_source_distance_m": hyp["vessel_source_distance_m"],
                    "feature_type": "vessel_to_source_vector",
                },
            }
            features.append(line_feature)

        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
            },
            "features": features,
        }

    def _build_summary(self, hypotheses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Construct structured summary statistics for Case 001.
        """
        df = pd.DataFrame(hypotheses)
        total_hypotheses = len(hypotheses)
        unique_vessels = df["mmsi"].nunique() if not df.empty else 0

        hypotheses_per_vessel = {}
        if not df.empty:
            for mmsi, grp in df.groupby("mmsi"):
                v_name = grp["vessel_name"].iloc[0]
                hypotheses_per_vessel[str(mmsi)] = {
                    "vessel_name": v_name,
                    "hypothesis_count": int(len(grp)),
                    "hypothesis_ids": grp["hypothesis_id"].tolist(),
                    "min_distance_m": float(grp["vessel_source_distance_m"].min()),
                    "max_distance_m": float(grp["vessel_source_distance_m"].max()),
                }

        # Temporal & spatial distributions
        time_dist = df["release_timestamp"].value_counts().to_dict() if not df.empty else {}
        age_dist = df["source_age_hours"].value_counts().to_dict() if not df.empty else {}
        qual_dist = df["ais_track_quality"].value_counts().to_dict() if not df.empty else {}

        # Distance statistics
        distances = df["vessel_source_distance_m"].tolist() if not df.empty else []
        dist_stats = {
            "count": len(distances),
            "min_m": float(np.min(distances)) if distances else 0.0,
            "max_m": float(np.max(distances)) if distances else 0.0,
            "mean_m": float(np.mean(distances)) if distances else 0.0,
            "median_m": float(np.median(distances)) if distances else 0.0,
            "p25_m": float(np.percentile(distances, 25)) if distances else 0.0,
            "p75_m": float(np.percentile(distances, 75)) if distances else 0.0,
        }

        # Closest vessel to source
        closest_records = (
            df.sort_values(by="vessel_source_distance_m", ascending=True)
            .head(5)[["hypothesis_id", "vessel_name", "mmsi", "vessel_source_distance_m", "source_plausibility"]]
            .to_dict(orient="records")
            if not df.empty
            else []
        )

        return {
            "case_id": self.case_id,
            "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_candidates": int(df["candidate_id"].nunique()) if not df.empty else 0,
            "total_hypotheses": total_hypotheses,
            "unique_vessels": unique_vessels,
            "hypotheses_per_vessel": hypotheses_per_vessel,
            "source_time_distribution": time_dist,
            "source_age_distribution": age_dist,
            "ais_quality_distribution": qual_dist,
            "distance_statistics": dist_stats,
            "closest_hypotheses": closest_records,
            "scientific_guardrail_notice": (
                "Hypotheses represent descriptive 4D physical pairings (vessel, release location, release time). "
                "They do NOT constitute attribution or guilt rankings. Forward counterfactual simulation "
                "will evaluate hypothesis viability in Phase 7."
            ),
            "reference_pipeline_notice": "Pipeline rupture coordinates were strictly excluded from hypothesis generation.",
        }

    def _plot_diagnostic_figure(self, hypotheses: List[Dict[str, Any]]) -> None:
        """
        Generate a multi-panel publication-grade diagnostic figure.
        Distinguishes:
        - VESSEL POSITION
        - SOURCE LOCATION
        - SOURCE TIME
        Labels known pipeline rupture point as REFERENCE ONLY.
        """
        df = pd.DataFrame(hypotheses)
        fig = plt.figure(figsize=(19, 12))
        gs = fig.add_gridspec(2, 2, hspace=0.30, wspace=0.36)

        # Panel 1: 2D Spatial Overview (Vessel Positions vs Release Locations)
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_title(
            "Panel 1: Spatial Map — Hypothesized Release Locations vs Vessel Positions",
            fontsize=12,
            fontweight="bold",
        )

        if not df.empty:
            # Plot displacement vectors
            for _, row in df.iterrows():
                ax1.plot(
                    [row["ais_lon"], row["release_lon"]],
                    [row["ais_lat"], row["release_lat"]],
                    color="gray",
                    linestyle="--",
                    alpha=0.6,
                    linewidth=1.2,
                    zorder=2,
                )

            # Plot Hypothesized Release Locations
            sc_rel = ax1.scatter(
                df["release_lon"],
                df["release_lat"],
                c=df["source_plausibility"],
                cmap="viridis",
                s=140,
                marker="o",
                edgecolor="black",
                linewidth=1.5,
                zorder=4,
                label="Hypothesized Release Location (x_r, y_r)",
            )
            cbar = plt.colorbar(sc_rel, ax=ax1, fraction=0.046, pad=0.04)
            cbar.set_label("Source Plausibility", fontsize=10)

            # Plot Vessel Positions
            ax1.scatter(
                df["ais_lon"],
                df["ais_lat"],
                color="#e74c3c",
                s=100,
                marker="^",
                edgecolor="black",
                linewidth=1.2,
                zorder=5,
                label="AIS Vessel Position at Release Time (x_v, y_v)",
            )

            # Annotate vessel names (first 15 unique to avoid clutter)
            seen_annotated = set()
            for _, row in df.iterrows():
                v_name = row['vessel_name']
                if v_name not in seen_annotated and len(seen_annotated) < 15:
                    seen_annotated.add(v_name)
                    ax1.annotate(
                        f"{v_name}\n({row['vessel_source_distance_m']:.0f}m)",
                        xy=(row["ais_lon"], row["ais_lat"]),
                        xytext=(row["ais_lon"] + 0.005, row["ais_lat"] + 0.005),
                        fontsize=8,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec="gray"),
                        zorder=6,
                    )

        # Reference Incident Point (EXPLICITLY LABELED AS REFERENCE ONLY)
        pipe_lat = self.case_cfg.get("spatial", {}).get("incident_point", {}).get("latitude", 33.60)
        pipe_lon = self.case_cfg.get("spatial", {}).get("incident_point", {}).get("longitude", -118.05)
        ax1.plot(
            pipe_lon,
            pipe_lat,
            marker="X",
            color="magenta",
            markersize=14,
            markeredgewidth=2,
            markeredgecolor="black",
            linestyle="None",
            label="REFERENCE ONLY — Incident Corridor (NOT USED BY ALGORITHM)",
            zorder=10,
        )

        ax1.set_xlabel("Longitude (°W)", fontsize=10)
        ax1.set_ylabel("Latitude (°N)", fontsize=10)
        ax1.grid(True, linestyle=":", alpha=0.6)
        ax1.legend(loc="lower right", fontsize=8, framealpha=0.9)

        # Panel 2: Geodesic Distance by Hypothesis & Vessel
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_title(
            "Panel 2: Geodesic Separation Distance (Vessel to Source Location)",
            fontsize=12,
            fontweight="bold",
        )
        if not df.empty:
            df_sorted = df.sort_values(by="vessel_source_distance_m", ascending=True)
            if len(df_sorted) > 20:
                df_sorted = df_sorted.head(20)
            y_pos = np.arange(len(df_sorted))
            bars = ax2.barh(
                y_pos,
                df_sorted["vessel_source_distance_m"] / 1000.0,
                color="#3498db",
                edgecolor="black",
                alpha=0.85,
            )
            ax2.set_yticks(y_pos)
            labels = [
                f"{row['hypothesis_id']} - {row['vessel_name']}"
                for _, row in df_sorted.iterrows()
            ]
            ax2.set_yticklabels(labels, fontsize=8)
            ax2.set_xlabel("Geodesic Distance (km)", fontsize=10)
            ax2.grid(True, axis="x", linestyle=":", alpha=0.6)

            # Add metric distance text labels
            for bar, dist_m in zip(bars, df_sorted["vessel_source_distance_m"]):
                ax2.text(
                    bar.get_width() + 0.1,
                    bar.get_y() + bar.get_height() / 2.0,
                    f"{dist_m:.0f} m",
                    va="center",
                    fontsize=8,
                )

        # Panel 3: Temporal & Source Age Distribution
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_title(
            "Panel 3: 4D Temporal Grid — Release Timestamp & Source Age per Vessel",
            fontsize=12,
            fontweight="bold",
        )
        if not df.empty:
            vessels = sorted(df["vessel_name"].unique())
            y_map = {v: i for i, v in enumerate(vessels)}
            
            # Group hypotheses per vessel to avoid text overlap
            for v_name, grp in df.groupby("vessel_name"):
                y_coord = y_map[v_name]
                hyp_ids = ", ".join(grp["hypothesis_id"].tolist())
                mean_age = grp["source_age_hours"].mean()
                mean_plaus = grp["source_plausibility"].mean()
                
                ax3.scatter(
                    grp["source_age_hours"],
                    [y_coord] * len(grp),
                    c=grp["source_plausibility"],
                    cmap="viridis",
                    s=180,
                    edgecolor="black",
                    linewidth=1.2,
                )
                ax3.text(
                    mean_age + 0.12,
                    y_coord,
                    hyp_ids,
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                )
            ax3.set_yticks(range(len(vessels)))
            ax3.set_yticklabels(vessels, fontsize=9)
            ax3.set_xlabel("Source Age (hours before observation)", fontsize=10)
            ax3.set_ylabel("Candidate Vessel", fontsize=10)
            max_age = max(float(df["source_age_hours"].max()) + 1.0, 5.0)
            ax3.set_xlim(0, max_age)
            ax3.grid(True, linestyle=":", alpha=0.6)

        # Panel 4: Quality Analysis (Plausibility vs Distance vs Track Quality)
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_title(
            "Panel 4: Hypothesis Feature Space (Plausibility vs Separation Distance)",
            fontsize=12,
            fontweight="bold",
        )
        if not df.empty:
            sc4 = ax4.scatter(
                df["vessel_source_distance_m"] / 1000.0,
                df["source_plausibility"],
                c=df["source_age_hours"],
                cmap="plasma",
                s=160,
                edgecolor="black",
                linewidth=1.2,
                alpha=0.9,
            )
            cbar4 = plt.colorbar(sc4, ax=ax4, fraction=0.046, pad=0.04)
            cbar4.set_label("Source Age (h)", fontsize=10)

            # Stagger annotation text positions for top 15 closest
            top_for_ann = df.sort_values(by="vessel_source_distance_m").head(15)
            for i, (_, row) in enumerate(top_for_ann.iterrows()):
                y_off = 6 if i % 2 == 0 else -12
                x_off = 4 if i % 3 != 0 else -18
                ax4.annotate(
                    row["vessel_name"],
                    xy=(row["vessel_source_distance_m"] / 1000.0, row["source_plausibility"]),
                    xytext=(x_off, y_off),
                    textcoords="offset points",
                    fontsize=7.5,
                )

            ax4.set_xlabel("Vessel-to-Source Geodesic Distance (km)", fontsize=10)
            ax4.set_ylabel("Source Plausibility", fontsize=10)
            ax4.set_ylim(0.0, 1.0)
            ax4.grid(True, linestyle=":", alpha=0.6)

        # Overall Title and Watermark Guardrails
        fig.suptitle(
            "SIH26143 Phase 6: 4D Source Hypotheses Diagnostic\n"
            "H = (vessel, release_location, release_time) — Explicit Multi-Dimensional Hypotheses",
            fontsize=15,
            fontweight="bold",
            y=0.98,
        )

        fig.text(
            0.5,
            0.01,
            "SCIENTIFIC NOTICE: Hypotheses are candidate physical pairings for downstream counterfactual modeling (Phase 7). "
            "No vessel attribution or guilt ranking is implied. Reference pipeline location is strictly excluded from algorithm inputs.",
            ha="center",
            fontsize=9,
            color="#555555",
            style="italic",
        )

        fig.subplots_adjust(top=0.92, bottom=0.06, left=0.09, right=0.94, hspace=0.30, wspace=0.36)
        plt.savefig(self.diagnostic_png_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved diagnostic figure to {self.diagnostic_png_path}")

    def run(self) -> Dict[str, Any]:
        """
        End-to-end execution of Phase 6 hypothesis generation and export.
        """
        logger.info(f"Starting Phase 6 4D Source Hypothesis Generation for {self.case_id}...")
        hypotheses = self.generate_hypotheses()
        artifacts = self.export_artifacts(hypotheses)
        summary = self._build_summary(hypotheses)

        return {
            "case_id": self.case_id,
            "total_hypotheses": len(hypotheses),
            "artifacts": artifacts,
            "summary": summary,
        }
