"""
AIS Ingestion and High-Recall Candidate Generation.

Connects Phase 4 reconstructed source location × time hypotheses to real maritime
traffic (NOAA MarineCadastre AIS) using a 5-stage high-recall filtration funnel.
Identifies all vessels that could plausibly have been in a high-source-plausibility
region during a plausible release time, strictly avoiding premature over-filtering.
"""

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.ais.normalizer import AISNormalizer
from src.ais.track_builder import AISTrackBuilder
from src.common.case_loader import load_case_config
from src.common.config import load_config
from src.common.geo import haversine_distance_km
from src.common.logging import get_logger
from src.common.paths import (
    AIS_PROCESSED_DIR,
    DRIFT_PROCESSED_DIR,
    ensure_dir_exists,
    resolve_path,
)
from src.common.time_utils import parse_utc_timestamp

logger = get_logger(__name__)


class AISCandidateGenerator:
    """
    Ingests normalized AIS trajectories, matches them against Phase 4 source
    hypotheses, and generates candidate vessels under high-recall guarantees.
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

        ais_cfg = self.default_cfg.get("ais_candidate_generation", {})
        if config_override:
            ais_cfg.update(config_override)

        self.spatial_search_buffer_km = float(ais_cfg.get("spatial_search_buffer_km", 15.0))
        self.temporal_search_window_minutes = float(ais_cfg.get("temporal_search_window_minutes", 60.0))
        self.max_interpolation_gap_seconds = float(ais_cfg.get("max_interpolation_gap_seconds", 3600.0))
        self.max_speed_knots = float(ais_cfg.get("max_ship_speed_knots", 50.0))
        self.min_pings_per_track = int(ais_cfg.get("min_positions_per_track", 3))
        self.plausibility_distance_threshold_km = float(ais_cfg.get("plausibility_distance_threshold_km", 10.0))

        # Output directory and paths
        self.output_dir = ensure_dir_exists(output_dir if output_dir is not None else AIS_PROCESSED_DIR)
        self.normalized_csv_path = self.output_dir / f"{case_id}_ais_normalized.csv"
        self.candidate_vessels_csv_path = self.output_dir / f"{case_id}_candidate_vessels.csv"
        self.summary_json_path = self.output_dir / f"{case_id}_candidate_generation_summary.json"
        self.diagnostic_png_path = self.output_dir / f"{case_id}_candidate_generation_diagnostic.png"

        # Observation timestamp
        self.obs_timestamp = parse_utc_timestamp(self.case_cfg["satellite"]["observation_timestamp_utc"])

    def run_candidate_generation(
        self,
        ais_input_path: Optional[Union[str, Path]] = None,
        hypotheses_csv_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the complete 5-stage high-recall candidate generation pipeline.
        """
        # Resolve input paths
        if ais_input_path is None:
            ais_input_path = self.case_cfg["ais"]["files"]["filtered_csv"]
        ais_path = resolve_path(ais_input_path)

        if hypotheses_csv_path is None:
            hypotheses_csv_path = DRIFT_PROCESSED_DIR / f"{self.case_id}_source_hypotheses.csv"
        hyp_path = resolve_path(hypotheses_csv_path)

        if not hyp_path.exists():
            raise FileNotFoundError(f"Source hypotheses CSV not found: {hyp_path}")

        # 1. AIS Normalization
        normalizer = AISNormalizer(max_speed_knots=self.max_speed_knots)
        df_normalized, norm_report = normalizer.normalize(ais_path)

        # Save normalized CSV if not already present
        df_normalized.to_csv(self.normalized_csv_path, index=False)
        logger.info(f"Saved normalized AIS data to {self.normalized_csv_path}")

        # 2. Track Building and Gap Detection
        track_builder = AISTrackBuilder(
            df_normalized=df_normalized,
            max_interpolation_gap_seconds=self.max_interpolation_gap_seconds,
            min_pings_per_track=self.min_pings_per_track,
        )

        # 3. Load Phase 4 Source Hypotheses
        df_hypotheses = pd.read_csv(hyp_path)
        logger.info(f"Loaded {len(df_hypotheses)} source hypotheses from {hyp_path}")

        # Funnel tracking statistics
        funnel_stats = {
            "total_ais_records": norm_report["total_input_records"],
            "total_unique_vessels": norm_report["initial_unique_vessels"],
            "valid_unique_vessels": norm_report["final_unique_vessels"],
            "vessels_with_usable_tracks": len(track_builder.vessel_tracks),
            "temporally_compatible_vessels": 0,
            "spatially_compatible_vessels": 0,
            "final_retained_candidates": 0,
        }

        # Source envelope bounding box across all hypotheses
        env_lat_min = df_hypotheses["bbox_south"].min()
        env_lat_max = df_hypotheses["bbox_north"].max()
        env_lon_min = df_hypotheses["bbox_west"].min()
        env_lon_max = df_hypotheses["bbox_east"].max()

        retained_candidates: List[Dict[str, Any]] = []
        candidate_idx = 1

        # Track vessel IDs at each funnel stage for deduplicated counting
        temporal_vessel_set = set()
        spatial_vessel_set = set()
        final_candidate_vessel_set = set()

        rejection_counts: Dict[str, int] = {
            "INSUFFICIENT_PINGS": norm_report["final_unique_vessels"] - len(track_builder.vessel_tracks),
            "NO_DEFENSIBLE_POSITION_AT_TIME": 0,
            "SPATIALLY_OUT_OF_BOUNDS": 0,
            "EXCEEDS_DISTANCE_THRESHOLD": 0,
        }

        # Match vessels against each hypothesis
        for _, hyp in df_hypotheses.iterrows():
            hyp_id = hyp["hypothesis_id"]
            cand_slick_id = hyp["candidate_id"]
            source_age = float(hyp["source_age_hours"])
            rel_time = parse_utc_timestamp(hyp["estimated_release_time_utc"])
            c_lat = float(hyp["centroid_lat"])
            c_lon = float(hyp["centroid_lon"])
            dispersion = float(hyp["dispersion_std_km"])
            plausibility = float(hyp["source_plausibility"])

            # Maximum allowable distance for this hypothesis (plausibility distance + 2 * dispersion)
            dist_threshold = self.plausibility_distance_threshold_km + 2.0 * dispersion

            # Evaluate each vessel with usable tracks
            for mmsi, meta in track_builder.vessel_metadata.items():
                # Check defensible position at or near release time
                pos = track_builder.get_vessel_position_at_time(
                    mmsi=mmsi,
                    target_time=rel_time,
                    near_boundary_tolerance_seconds=600.0,  # 10 min tolerance
                )

                if pos is None:
                    rejection_counts["NO_DEFENSIBLE_POSITION_AT_TIME"] += 1
                    continue

                temporal_vessel_set.add(mmsi)

                v_lat = pos["latitude"]
                v_lon = pos["longitude"]

                # Spatial compatibility: within envelope search buffer
                # Geodesic distance to hypothesis centroid
                dist_km = haversine_distance_km(c_lat, c_lon, v_lat, v_lon)

                # Envelope check
                in_envelope = (
                    (env_lat_min - 0.15 <= v_lat <= env_lat_max + 0.15) and
                    (env_lon_min - 0.15 <= v_lon <= env_lon_max + 0.15)
                )
                if not in_envelope and dist_km > self.spatial_search_buffer_km:
                    rejection_counts["SPATIALLY_OUT_OF_BOUNDS"] += 1
                    continue

                spatial_vessel_set.add(mmsi)

                # Source-plausibility compatibility
                if dist_km > dist_threshold:
                    rejection_counts["EXCEEDS_DISTANCE_THRESHOLD"] += 1
                    continue

                # RETAIN CANDIDATE
                final_candidate_vessel_set.add(mmsi)

                cand_record = {
                    "candidate_id": f"VC_{candidate_idx:04d}",
                    "mmsi": mmsi,
                    "vessel_name": meta["vessel_name"] or "UNKNOWN",
                    "imo": meta["imo"] or "UNKNOWN",
                    "vessel_type": meta["vessel_type"] or "UNKNOWN",
                    "candidate_position_lat": round(v_lat, 6),
                    "candidate_position_lon": round(v_lon, 6),
                    "candidate_sog_knots": pos["sog_knots"],
                    "candidate_cog_deg": pos["cog_deg"],
                    "candidate_timestamp_utc": pos["timestamp_utc"],
                    "distance_to_source_km": round(dist_km, 3),
                    "distance_threshold_km": round(dist_threshold, 3),
                    "source_plausibility": round(plausibility, 4),
                    "source_hypothesis_id": hyp_id,
                    "source_slick_id": cand_slick_id,
                    "source_age_hours": source_age,
                    "ais_track_quality": pos["quality"],
                    "ais_gap_seconds": pos["gap_seconds"],
                    "retention_reason": (
                        f"Vessel within {dist_km:.2f} km of hypothesis {hyp_id} centroid "
                        f"(threshold {dist_threshold:.2f} km) at estimated release time"
                    ),
                }
                retained_candidates.append(cand_record)
                candidate_idx += 1

        funnel_stats["temporally_compatible_vessels"] = len(temporal_vessel_set)
        funnel_stats["spatially_compatible_vessels"] = len(spatial_vessel_set)
        funnel_stats["final_retained_candidates"] = len(final_candidate_vessel_set)
        funnel_stats["total_candidate_records"] = len(retained_candidates)

        # Save candidate vessels CSV
        df_candidates = pd.DataFrame(retained_candidates)
        df_candidates.to_csv(self.candidate_vessels_csv_path, index=False)
        logger.info(
            f"Saved {len(df_candidates)} candidate records ({len(final_candidate_vessel_set)} unique vessels) "
            f"to {self.candidate_vessels_csv_path}"
        )

        # Build diagnostic summary
        summary = {
            "case_id": self.case_id,
            "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "funnel_statistics": funnel_stats,
            "rejection_statistics": rejection_counts,
            "unique_candidate_mmsis": sorted(list(final_candidate_vessel_set)),
            "top_candidates": (
                df_candidates.sort_values(by=["distance_to_source_km", "source_plausibility"], ascending=[True, False])
                .head(10)
                .to_dict(orient="records") if not df_candidates.empty else []
            ),
            "files": {
                "normalized_csv": str(self.normalized_csv_path.relative_to(self.output_dir.parent.parent)),
                "candidate_vessels_csv": str(self.candidate_vessels_csv_path.relative_to(self.output_dir.parent.parent)),
                "diagnostic_png": str(self.diagnostic_png_path.relative_to(self.output_dir.parent.parent)),
            },
        }

        with open(self.summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved candidate generation summary to {self.summary_json_path}")

        # 4. Generate Diagnostic Visualization
        self._generate_diagnostic_visualization(
            df_normalized=df_normalized,
            df_hypotheses=df_hypotheses,
            df_candidates=df_candidates,
            funnel_stats=funnel_stats,
        )

        return summary

    def _generate_diagnostic_visualization(
        self,
        df_normalized: pd.DataFrame,
        df_hypotheses: pd.DataFrame,
        df_candidates: pd.DataFrame,
        funnel_stats: Dict[str, Any],
    ) -> None:
        """
        Generate 4-panel publication-grade candidate generation diagnostic map.
        """
        fig = plt.figure(figsize=(20, 12), dpi=150)
        gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], hspace=0.25, wspace=0.22)

        # External pipeline reference marker (Huntington Beach rupture point)
        ref_lat = float(self.case_cfg.get("spatial", {}).get("incident_point", {}).get("latitude", 33.60))
        ref_lon = float(self.case_cfg.get("spatial", {}).get("incident_point", {}).get("longitude", -118.05))

        # Panel 1: Case 001 Overview: AIS Traffic vs Source Region
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_title("Panel 1: Regional AIS Traffic & Reconstructed Source Envelopes", fontsize=11, fontweight="bold")

        # Plot subsampled AIS pings as background traffic density
        sample_ais = df_normalized.sample(n=min(15000, len(df_normalized)), random_state=42)
        ax1.scatter(
            sample_ais["longitude"], sample_ais["latitude"],
            s=1, color="#7f8c8d", alpha=0.25, label="Background AIS Traffic (sampled)"
        )

        aoi = self.case_cfg["spatial"]["aoi_bounding_box"]

        # Reconstructed source hypotheses centroids and bounding envelope
        ax1.scatter(
            df_hypotheses["centroid_lon"], df_hypotheses["centroid_lat"],
            color="#e74c3c", marker="o", s=80, edgecolors="black", zorder=5, label="Phase 4 Source Hypotheses"
        )

        # Plot external reference marker
        ax1.scatter(
            [ref_lon], [ref_lat],
            color="red", marker="x", s=110, linewidth=2.5, zorder=6, label="Incident point (reference ONLY — NOT USED)"
        )

        ax1.set_xlim([aoi["west"] - 0.05, aoi["east"] + 0.05])
        ax1.set_ylim([aoi["south"] - 0.05, aoi["north"] + 0.05])
        ax1.set_xlabel("Longitude (°)")
        ax1.set_ylabel("Latitude (°)")
        ax1.legend(loc="upper right", fontsize=8, framealpha=0.85)
        ax1.grid(True, linestyle="--", alpha=0.4)

        # Panel 2: Source Region & Retained Candidate Vessels
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_title("Panel 2: Source Region & Candidate Vessels at Release Time", fontsize=11, fontweight="bold")

        # Plot hypothesis centroids
        for _, hyp in df_hypotheses.iterrows():
            ax2.scatter(hyp["centroid_lon"], hyp["centroid_lat"], color="#e74c3c", s=70, marker="o", edgecolors="black", zorder=4)
            # Add distance circle (e.g. 10 km)
            circle = plt.Circle((hyp["centroid_lon"], hyp["centroid_lat"]), 10.0 / 111.0, color="#e74c3c", fill=False, linestyle=":", alpha=0.3)
            ax2.add_patch(circle)

        # Plot candidate vessels
        if not df_candidates.empty:
            unique_cand = df_candidates.drop_duplicates(subset=["mmsi"])
            colors = plt.cm.tab20(np.linspace(0, 1, len(unique_cand)))
            for idx, (_, cand) in enumerate(unique_cand.iterrows()):
                v_name = cand["vessel_name"] if cand["vessel_name"] != "UNKNOWN" else f"MMSI {cand['mmsi']}"
                ax2.scatter(
                    cand["candidate_position_lon"], cand["candidate_position_lat"],
                    color=colors[idx], s=90, edgecolors="black", zorder=6,
                    label=f"{v_name} ({cand['distance_to_source_km']:.1f} km)"
                )
                ax2.text(
                    cand["candidate_position_lon"] + 0.003, cand["candidate_position_lat"],
                    v_name[:12], fontsize=7, color="#2c3e50"
                )

        ax2.scatter([ref_lon], [ref_lat], color="red", marker="x", s=110, linewidth=2.5, zorder=7, label="Incident (reference — NOT USED)")
        ax2.set_xlim([aoi["west"] - 0.05, aoi["east"] + 0.05])
        ax2.set_ylim([aoi["south"] - 0.05, aoi["north"] + 0.05])
        ax2.set_xlabel("Longitude (°)")
        ax2.set_ylabel("Latitude (°)")
        ax2.legend(loc="upper left", fontsize=7, framealpha=0.85, ncol=2)
        ax2.grid(True, linestyle="--", alpha=0.4)

        # Panel 3: Funnel Attrition / Retention
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_title("Panel 3: High-Recall Candidate Generation Funnel", fontsize=11, fontweight="bold")

        stages = [
            "All Vessels\n(Raw Ingest)",
            "Valid Tracks\n(>=3 pings)",
            "Temporal\nCompatibility",
            "Spatial\nCompatibility",
            "Retained\nCandidates",
        ]
        counts = [
            funnel_stats["total_unique_vessels"],
            funnel_stats["vessels_with_usable_tracks"],
            funnel_stats["temporally_compatible_vessels"],
            funnel_stats["spatially_compatible_vessels"],
            funnel_stats["final_retained_candidates"],
        ]
        bar_colors = ["#34495e", "#2980b9", "#16a085", "#f39c12", "#27ae60"]
        bars = ax3.bar(stages, counts, color=bar_colors, width=0.55, edgecolor="black")

        for bar, count in zip(bars, counts):
            yval = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width() / 2.0, yval + 10, f"{count}", ha="center", va="bottom", fontsize=10, fontweight="bold")

        ax3.set_ylabel("Unique Vessel Count (MMSI)", fontsize=10)
        ax3.set_ylim([0, max(counts) * 1.15])
        ax3.grid(True, axis="y", linestyle="--", alpha=0.4)

        # Panel 4: Candidate Distance vs Source Plausibility
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_title("Panel 4: Candidate Proximity vs Source Plausibility", fontsize=11, fontweight="bold")

        if not df_candidates.empty:
            scatter = ax4.scatter(
                df_candidates["distance_to_source_km"],
                df_candidates["source_plausibility"],
                c=df_candidates["source_age_hours"],
                cmap="plasma",
                s=70,
                edgecolors="black",
                alpha=0.85,
            )
            cbar = fig.colorbar(scatter, ax=ax4, fraction=0.046, pad=0.04)
            cbar.set_label("Source Age Prior (hours)", fontsize=9)

            ax4.set_xlabel("Distance to Reconstructed Source Centroid (km)", fontsize=10)
            ax4.set_ylabel("Source Plausibility [0, 1]", fontsize=10)
            ax4.grid(True, linestyle="--", alpha=0.4)
        else:
            ax4.text(0.5, 0.5, "No candidates generated", ha="center", va="center", transform=ax4.transAxes)

        plt.suptitle(
            f"SIH26143 Phase 5: AIS Ingestion & High-Recall Candidate Generation — {self.case_id}\n"
            f"Raw vessels: {funnel_stats['total_unique_vessels']} | Usable tracks: {funnel_stats['vessels_with_usable_tracks']} | "
            f"Retained candidates: {funnel_stats['final_retained_candidates']} unique vessels ({funnel_stats.get('total_candidate_records', 0)} associations)",
            fontsize=13,
            fontweight="bold",
            y=0.98,
        )

        plt.savefig(self.diagnostic_png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved candidate generation diagnostic to {self.diagnostic_png_path}")
