"""
Phase 7: Forward Counterfactual Simulation Engine.

Tests each Phase 6 4D source hypothesis H = (v, x_r, y_r, t_r) physically:
    "If this candidate vessel released oil at this location and time,
     would the resulting oceanographic drift plausibly reproduce the observed
     satellite slick at observation time t_obs?"

Scientific Guardrails:
- This is a physical consistency test, NOT a proof of responsibility or guilt.
- Reuses the existing Phase 4 LagrangianIntegrator and EnvironmentalForcingInterpolator.
- Uses compact physical particle seeding at the release location.
- Respects temporal ordering: rejects any hypothesis where release_time >= observation_time.
- The known pipeline rupture point is strictly excluded from simulation inputs.
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
from src.common.geo import haversine_distance_m, haversine_distance_km
from src.common.logging import get_logger
from src.common.paths import (
    ATTRIBUTION_PROCESSED_DIR,
    DRIFT_PROCESSED_DIR,
    HYPOTHESES_PROCESSED_DIR,
    SATELLITE_PROCESSED_DIR,
    ensure_dir_exists,
    resolve_path,
)
from src.common.time_utils import parse_utc_timestamp
from src.drift.integrator import LagrangianIntegrator
from src.drift.particle_seeder import seed_particles_from_point
from src.environmental.interpolator import EnvironmentalForcingInterpolator

logger = get_logger(__name__)


class ForwardCounterfactualSimulator:
    """
    Simulates forward Lagrangian advection + diffusion for explicit 4D source hypotheses.
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

        # Physics & simulation configuration
        drift_cfg = self.default_cfg.get("lagrangian_drift", {})
        physics_cfg = drift_cfg.get("physics", {})
        sim_cfg = drift_cfg.get("simulation", {})
        fwd_cfg = self.default_cfg.get("forward_counterfactual_simulation", {})

        if config_override:
            physics_cfg.update(config_override.get("physics", {}))
            fwd_cfg.update(config_override.get("forward", {}))

        self.wind_drift_factor = float(physics_cfg.get("wind_drift_factor", 0.031))
        self.wind_deflection_angle_deg = float(physics_cfg.get("wind_deflection_angle_deg", 0.0))
        self.current_factor = float(physics_cfg.get("current_factor", 1.0))
        self.diffusion_coefficient_m2s = float(physics_cfg.get("diffusion_coefficient_m2s", 1.0))

        self.time_step_seconds = float(fwd_cfg.get("time_step_seconds", sim_cfg.get("time_step_seconds", 600.0)))
        self.particle_count = int(fwd_cfg.get("particle_count", 500))
        self.release_radius_m = float(fwd_cfg.get("release_radius_m", 50.0))
        self.random_seed = int(fwd_cfg.get("random_seed", 42))

        # Output paths
        self.output_dir = ensure_dir_exists(
            output_dir if output_dir is not None else ATTRIBUTION_PROCESSED_DIR
        )
        self.simulations_dir = ensure_dir_exists(self.output_dir / "simulations")
        self.summary_csv_path = self.output_dir / f"{case_id}_forward_simulations.csv"
        self.summary_json_path = self.output_dir / f"{case_id}_forward_simulations_summary.json"
        self.diagnostic_png_path = self.output_dir / f"{case_id}_forward_simulation_diagnostic.png"

        # Canonical paths
        self.canonical_csv_path = self.output_dir / "forward_simulations.csv"

        # Satellite observation timestamp
        self.obs_timestamp = parse_utc_timestamp(self.case_cfg["satellite"]["observation_timestamp_utc"])

        # Initialize environmental interpolator (shared physics interface)
        hycom_path = self.case_cfg["environmental"]["ocean_currents"]["file_path"]
        era5_path = self.case_cfg["environmental"]["wind"]["files"]["csv_path"]
        self.interpolator = EnvironmentalForcingInterpolator(
            hycom_netcdf_path=hycom_path,
            era5_wind_csv_path=era5_path,
            boundary_buffer_deg=0.15,
        )

        # Initialize shared Lagrangian integrator
        self.integrator = LagrangianIntegrator(
            interpolator=self.interpolator,
            wind_drift_factor=self.wind_drift_factor,
            wind_deflection_angle_deg=self.wind_deflection_angle_deg,
            current_factor=self.current_factor,
            diffusion_coefficient_m2s=self.diffusion_coefficient_m2s,
            time_step_seconds=self.time_step_seconds,
        )

    def load_observed_slicks(self) -> Dict[str, Dict[str, Any]]:
        """
        Load Phase 3 accepted candidate slicks for predicted vs observed comparison.
        """
        slicks_geojson_path = SATELLITE_PROCESSED_DIR / f"{self.case_id}_candidate_slicks.geojson"
        slicks_csv_path = SATELLITE_PROCESSED_DIR / f"{self.case_id}_candidate_slicks.csv"

        slick_dict: Dict[str, Dict[str, Any]] = {}
        if slicks_csv_path.exists():
            df_slicks = pd.read_csv(slicks_csv_path)
            # Retain only verified accepted candidate slicks
            if "status" in df_slicks.columns:
                df_slicks = df_slicks[df_slicks["status"] == "ACCEPTED"]
            for _, row in df_slicks.iterrows():
                cid = row["candidate_id"]
                slick_dict[cid] = {
                    "candidate_id": cid,
                    "centroid_lat": float(row["centroid_lat"]),
                    "centroid_lon": float(row["centroid_lon"]),
                    "area_km2": float(row.get("area_km2", 0.0)),
                    "status": str(row.get("status", "ACCEPTED")),
                }
        return slick_dict

    def run_simulation_for_hypothesis(
        self,
        hyp: Dict[str, Any],
        observed_slicks: Optional[Dict[str, Dict[str, Any]]] = None,
        save_individual: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute forward simulation for an individual 4D hypothesis.
        """
        hyp_id = hyp["hypothesis_id"]
        rel_lat = float(hyp["release_lat"])
        rel_lon = float(hyp["release_lon"])
        rel_time = parse_utc_timestamp(hyp["release_timestamp"])

        # Temporal validation: release time must be strictly before observation time
        if rel_time >= self.obs_timestamp:
            logger.warning(
                f"Hypothesis {hyp_id} rejected: release time {rel_time} >= observation time {self.obs_timestamp}"
            )
            return {
                "hypothesis_id": hyp_id,
                "simulation_status": "REJECTED_TIME_ORDER",
                "error": "Release time is at or after observation time",
            }

        # Seed compact particle ensemble at hypothetical release location
        initial_particles = seed_particles_from_point(
            lat=rel_lat,
            lon=rel_lon,
            radius_m=self.release_radius_m,
            num_particles=self.particle_count,
            random_seed=self.random_seed,
        )

        # Run forward integration
        sim_result = self.integrator.simulate_forward(
            initial_particles=initial_particles,
            start_time=rel_time,
            end_time=self.obs_timestamp,
            random_seed=self.random_seed,
        )

        pred_centroid = sim_result["predicted_centroid"]

        # Link to observed slick if available
        obs_slick_id = hyp.get("source_slick_id", "")
        obs_centroid_lat = None
        obs_centroid_lon = None
        pred_to_obs_dist_m = None

        if observed_slicks and obs_slick_id in observed_slicks:
            obs_slick = observed_slicks[obs_slick_id]
            obs_centroid_lat = obs_slick["centroid_lat"]
            obs_centroid_lon = obs_slick["centroid_lon"]
            pred_to_obs_dist_m = round(
                haversine_distance_m(
                    pred_centroid["lat"],
                    pred_centroid["lon"],
                    obs_centroid_lat,
                    obs_centroid_lon,
                ),
                2,
            )

        # Build individual hypothesis simulation metadata
        metadata = {
            "hypothesis_id": hyp_id,
            "candidate_id": hyp.get("candidate_id", ""),
            "mmsi": hyp.get("mmsi"),
            "vessel_name": hyp.get("vessel_name", "UNKNOWN"),
            "release_lat": rel_lat,
            "release_lon": rel_lon,
            "release_timestamp": rel_time.isoformat(),
            "source_age_hours": float(hyp.get("source_age_hours", 0.0)),
            "observation_timestamp": self.obs_timestamp.isoformat(),
            "duration_hours": sim_result["duration_hours"],
            "particle_count": self.particle_count,
            "timestep_seconds": self.time_step_seconds,
            "environmental_model": "HYCOM_surface_currents + ERA5_10m_wind",
            "wind_coefficient": self.wind_drift_factor,
            "simulation_status": sim_result["status"],
            "active_particle_fraction": sim_result["active_particle_fraction"],
            "predicted_centroid_lat": pred_centroid["lat"],
            "predicted_centroid_lon": pred_centroid["lon"],
            "predicted_bbox": sim_result["predicted_bbox"],
            "dispersion_std_km": sim_result["dispersion_std_km"],
            "observed_slick_id": obs_slick_id,
            "observed_slick_centroid_lat": obs_centroid_lat,
            "observed_slick_centroid_lon": obs_centroid_lon,
            "predicted_to_observed_distance_m": pred_to_obs_dist_m,
            "ais_vessel_lat": hyp.get("ais_lat"),
            "ais_vessel_lon": hyp.get("ais_lon"),
        }

        # Save individual simulation folder if requested
        if save_individual:
            hyp_dir = ensure_dir_exists(self.simulations_dir / hyp_id)
            with open(hyp_dir / "simulation_metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            with open(hyp_dir / "final_particles.json", "w", encoding="utf-8") as f:
                json.dump(sim_result["final_particles"], f, indent=2)
            with open(hyp_dir / "trajectory.json", "w", encoding="utf-8") as f:
                json.dump(sim_result["trajectories"], f, indent=2)

        metadata["_trajectories"] = sim_result["trajectories"]
        metadata["_final_particles"] = sim_result["final_particles"]
        return metadata

    def run_all_simulations(
        self,
        hypotheses_csv_path: Optional[Union[str, Path]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute forward counterfactual simulations for all hypotheses.
        """
        if hypotheses_csv_path is None:
            hyp_path = HYPOTHESES_PROCESSED_DIR / f"{self.case_id}_source_hypotheses_4d.csv"
        else:
            hyp_path = resolve_path(hypotheses_csv_path)

        if not hyp_path.exists():
            raise FileNotFoundError(f"4D source hypotheses CSV not found: {hyp_path}")

        df_hyp = pd.read_csv(hyp_path)
        logger.info(f"Loaded {len(df_hyp)} 4D hypotheses for forward counterfactual simulation.")

        observed_slicks = self.load_observed_slicks()
        sim_records: List[Dict[str, Any]] = []

        for _, hyp_row in df_hyp.iterrows():
            hyp_dict = hyp_row.to_dict()
            res = self.run_simulation_for_hypothesis(
                hyp=hyp_dict,
                observed_slicks=observed_slicks,
                save_individual=True,
            )
            sim_records.append(res)

        # Export consolidated summary table and JSON
        self._export_summaries(sim_records)

        # Generate diagnostic figure
        self._plot_diagnostic_figure(sim_records, observed_slicks)

        return sim_records

    def _export_summaries(self, sim_records: List[Dict[str, Any]]) -> None:
        """
        Save forward_simulations.csv and forward_simulations_summary.json.
        """
        # Exclude raw trajectory/particle lists from tabular CSV
        table_records = []
        for r in sim_records:
            clean_rec = {k: v for k, v in r.items() if not k.startswith("_")}
            # Flatten predicted_bbox dict
            if "predicted_bbox" in clean_rec and isinstance(clean_rec["predicted_bbox"], dict):
                bbox = clean_rec.pop("predicted_bbox")
                clean_rec["predicted_bbox_west"] = bbox.get("west")
                clean_rec["predicted_bbox_south"] = bbox.get("south")
                clean_rec["predicted_bbox_east"] = bbox.get("east")
                clean_rec["predicted_bbox_north"] = bbox.get("north")
            table_records.append(clean_rec)

        df_sim = pd.DataFrame(table_records)
        df_sim.to_csv(self.summary_csv_path, index=False)
        df_sim.to_csv(self.canonical_csv_path, index=False)
        logger.info(f"Saved forward simulations CSV to {self.summary_csv_path}")

        # Summary JSON
        distances = [
            r["predicted_to_observed_distance_m"]
            for r in sim_records
            if r.get("predicted_to_observed_distance_m") is not None
        ]
        dist_stats = {
            "count": len(distances),
            "min_m": float(np.min(distances)) if distances else 0.0,
            "max_m": float(np.max(distances)) if distances else 0.0,
            "mean_m": float(np.mean(distances)) if distances else 0.0,
            "median_m": float(np.median(distances)) if distances else 0.0,
            "p25_m": float(np.percentile(distances, 25)) if distances else 0.0,
            "p75_m": float(np.percentile(distances, 75)) if distances else 0.0,
        }

        durations = [r.get("duration_hours", 0.0) for r in sim_records]

        summary_data = {
            "case_id": self.case_id,
            "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_hypotheses_simulated": len(sim_records),
            "successful_simulations": sum(1 for r in sim_records if r.get("simulation_status") == "completed"),
            "failed_simulations": sum(1 for r in sim_records if r.get("simulation_status") != "completed"),
            "particle_count_per_simulation": self.particle_count,
            "timestep_seconds": self.time_step_seconds,
            "environmental_models": {
                "ocean_currents": "HYCOM 3-hourly 0.08 deg analysis",
                "winds": "ECMWF ERA5 hourly 10m reanalysis",
            },
            "wind_drift_factor": self.wind_drift_factor,
            "simulation_duration_range_hours": {
                "min": float(np.min(durations)) if durations else 0.0,
                "max": float(np.max(durations)) if durations else 0.0,
            },
            "predicted_to_observed_distance_stats": dist_stats,
            "closest_simulations": (
                pd.DataFrame(table_records)
                .sort_values(by="predicted_to_observed_distance_m", ascending=True)
                .head(5)[["hypothesis_id", "vessel_name", "observed_slick_id", "predicted_to_observed_distance_m"]]
                .to_dict(orient="records")
                if not df_sim.empty and "predicted_to_observed_distance_m" in df_sim.columns
                else []
            ),
            "scientific_guardrail_notice": (
                "Forward simulations evaluate physical advective/diffusive consistency only. "
                "A low predicted-to-observed distance does NOT prove the vessel is guilty or caused the spill. "
                "Final attribution scoring is deferred to Phase 8."
            ),
            "reference_pipeline_notice": "Pipeline rupture coordinates were strictly excluded from simulation inputs.",
        }

        with open(self.summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        logger.info(f"Saved forward simulations summary JSON to {self.summary_json_path}")

    def _plot_diagnostic_figure(
        self,
        sim_records: List[Dict[str, Any]],
        observed_slicks: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Generate a multi-panel publication-grade diagnostic figure:
        VESSEL TRACK -> HYPOTHETICAL RELEASE POINT -> PREDICTED DRIFT -> OBSERVED SLICK.
        """
        fig = plt.figure(figsize=(19, 12))
        gs = fig.add_gridspec(2, 2, hspace=0.30, wspace=0.36)

        # Panel 1: Overview of All Forward Simulations & Observed Slicks
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_title(
            "Panel 1: Regional Forward Drift — Hypothetical Releases to Observed Slicks",
            fontsize=12,
            fontweight="bold",
        )

        # Plot observed slicks
        if observed_slicks:
            for idx, (s_id, s_data) in enumerate(observed_slicks.items()):
                ax1.scatter(
                    s_data["centroid_lon"],
                    s_data["centroid_lat"],
                    color="#2ecc71",
                    s=220,
                    marker="s",
                    edgecolor="black",
                    linewidth=2.0,
                    zorder=8,
                    label=f"Observed Slick Centroid ({s_id})" if idx == 0 else "",
                )
                ax1.annotate(
                    f"Observed {s_id}",
                    xy=(s_data["centroid_lon"], s_data["centroid_lat"]),
                    xytext=(s_data["centroid_lon"] + 0.005, s_data["centroid_lat"] - 0.008),
                    fontsize=9,
                    fontweight="bold",
                    color="#196f3d",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#d5f5e3", ec="#2ecc71", alpha=0.9),
                    zorder=9,
                )

        # Plot hypothetical release points, drift trajectories, and predicted centroids
        for r in sim_records:
            if r.get("simulation_status") != "completed":
                continue

            r_lat, r_lon = r["release_lat"], r["release_lon"]
            p_lat, p_lon = r["predicted_centroid_lat"], r["predicted_centroid_lon"]

            # Sub-sampled trajectory line
            if "_trajectories" in r and r["_trajectories"]:
                sample_traj = r["_trajectories"][0]  # First particle trajectory
                t_lons = [pt["lon"] for pt in sample_traj]
                t_lats = [pt["lat"] for pt in sample_traj]
                ax1.plot(t_lons, t_lats, color="#3498db", alpha=0.3, linewidth=1.0, zorder=3)

            # Connect release to predicted centroid
            ax1.plot([r_lon, p_lon], [r_lat, p_lat], color="#2980b9", linestyle="--", alpha=0.5, zorder=4)

            # Hypothetical release point
            ax1.scatter(r_lon, r_lat, color="#f39c12", s=70, marker="o", edgecolor="black", linewidth=1.0, zorder=5)

            # Predicted centroid
            ax1.scatter(p_lon, p_lat, color="#9b59b6", s=90, marker="D", edgecolor="black", linewidth=1.2, zorder=6)

        # Custom Legend elements for clarity
        ax1.scatter([], [], color="#f39c12", s=70, marker="o", edgecolor="black", label="Hypothetical Release Point (x_r, y_r)")
        ax1.plot([], [], color="#3498db", linestyle="--", label="Forward Particle Drift")
        ax1.scatter([], [], color="#9b59b6", s=90, marker="D", edgecolor="black", label="Predicted Distribution Centroid")

        # Known Pipeline Corridor (REFERENCE ONLY)
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
            label="REFERENCE ONLY — Pipeline Corridor (NOT USED BY ALGORITHM)",
            zorder=10,
        )

        ax1.set_xlabel("Longitude (°W)", fontsize=10)
        ax1.set_ylabel("Latitude (°N)", fontsize=10)
        ax1.grid(True, linestyle=":", alpha=0.6)
        ax1.legend(loc="lower right", fontsize=8, framealpha=0.9)

        # Panel 2: Detailed Case Study — 4D Progression for Selected Hypotheses
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_title(
            "Panel 2: 4D Physical Progression (Vessel Track -> Release -> Drift -> Slick)",
            fontsize=12,
            fontweight="bold",
        )

        # Pick top 2 closest hypotheses for detailed progression display
        df_sim = pd.DataFrame(sim_records)
        if not df_sim.empty and "predicted_to_observed_distance_m" in df_sim.columns:
            top_cases = df_sim.sort_values(by="predicted_to_observed_distance_m", ascending=True).head(3)

            for _, row in top_cases.iterrows():
                v_lat, v_lon = row.get("ais_vessel_lat"), row.get("ais_vessel_lon")
                r_lat, r_lon = row["release_lat"], row["release_lon"]
                p_lat, p_lon = row["predicted_centroid_lat"], row["predicted_centroid_lon"]
                obs_lat, obs_lon = row.get("observed_slick_centroid_lat"), row.get("observed_slick_centroid_lon")

                # 1. Vessel to Release Point (spatial separation)
                if v_lat is not None and v_lon is not None:
                    ax2.plot([v_lon, r_lon], [v_lat, r_lat], color="gray", linestyle=":", linewidth=1.5)
                    ax2.scatter(v_lon, v_lat, color="#e74c3c", s=100, marker="^", edgecolor="black", zorder=5)
                    ax2.annotate(f"AIS: {row['vessel_name']}", (v_lon, v_lat), fontsize=8, xytext=(4, 4), textcoords="offset points")

                # 2. Release Point
                ax2.scatter(r_lon, r_lat, color="#f39c12", s=100, marker="o", edgecolor="black", zorder=6)

                # 3. Drift trajectory to Predicted Centroid
                ax2.plot([r_lon, p_lon], [r_lat, p_lat], color="#2980b9", linestyle="-", linewidth=2.0, zorder=4)
                ax2.scatter(p_lon, p_lat, color="#9b59b6", s=120, marker="D", edgecolor="black", zorder=7)
                ax2.annotate(f"Pred {row['hypothesis_id']}", (p_lon, p_lat), fontsize=8, xytext=(4, 4), textcoords="offset points")

                # 4. Connection to Observed Slick
                if obs_lat is not None and obs_lon is not None:
                    ax2.plot([p_lon, obs_lon], [p_lat, obs_lat], color="red", linestyle="--", linewidth=1.2, alpha=0.7)

            if observed_slicks:
                for s_id, s_data in observed_slicks.items():
                    ax2.scatter(s_data["centroid_lon"], s_data["centroid_lat"], color="#2ecc71", s=220, marker="s", edgecolor="black", zorder=8)
                    ax2.annotate(f"Observed {s_id}", (s_data["centroid_lon"], s_data["centroid_lat"]), fontsize=9, fontweight="bold")

        ax2.set_xlabel("Longitude (°W)", fontsize=10)
        ax2.set_ylabel("Latitude (°N)", fontsize=10)
        ax2.grid(True, linestyle=":", alpha=0.6)

        # Panel 3: Distance from Predicted Distribution Centroid to Observed Slick
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_title(
            "Panel 3: Physical Consistency — Predicted Centroid to Observed Slick Distance",
            fontsize=12,
            fontweight="bold",
        )
        if not df_sim.empty and "predicted_to_observed_distance_m" in df_sim.columns:
            df_sorted = df_sim.sort_values(by="predicted_to_observed_distance_m", ascending=True)
            if len(df_sorted) > 20:
                df_sorted = df_sorted.head(20)
            y_pos = np.arange(len(df_sorted))
            bars = ax3.barh(
                y_pos,
                df_sorted["predicted_to_observed_distance_m"] / 1000.0,
                color="#27ae60",
                edgecolor="black",
                alpha=0.85,
            )
            ax3.set_yticks(y_pos)
            labels = [
                f"{row['hypothesis_id']} ({row['vessel_name']}) -> {row['observed_slick_id']}"
                for _, row in df_sorted.iterrows()
            ]
            ax3.set_yticklabels(labels, fontsize=8)
            ax3.set_xlabel("Distance to Observed Slick Centroid (km)", fontsize=10)
            ax3.grid(True, axis="x", linestyle=":", alpha=0.6)

            for bar, dist_m in zip(bars, df_sorted["predicted_to_observed_distance_m"]):
                ax3.text(
                    bar.get_width() + 0.1,
                    bar.get_y() + bar.get_height() / 2.0,
                    f"{dist_m:.0f} m",
                    va="center",
                    fontsize=8,
                )

        # Panel 4: Active Particle Fraction and Dispersion Extent
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_title(
            "Panel 4: Predicted Spill Dispersion (Std Dev km vs Active Particle %)",
            fontsize=12,
            fontweight="bold",
        )
        if not df_sim.empty:
            sc4 = ax4.scatter(
                df_sim["dispersion_std_km"],
                df_sim["active_particle_fraction"] * 100.0,
                c=df_sim["predicted_to_observed_distance_m"] / 1000.0 if "predicted_to_observed_distance_m" in df_sim.columns else [0] * len(df_sim),
                cmap="viridis_r",
                s=160,
                edgecolor="black",
                linewidth=1.2,
            )
            cbar4 = plt.colorbar(sc4, ax=ax4, fraction=0.046, pad=0.04)
            cbar4.set_label("Dist to Slick (km)", fontsize=10)

            for _, row in df_sim.iterrows():
                ax4.annotate(
                    row["hypothesis_id"],
                    xy=(row["dispersion_std_km"], row["active_particle_fraction"] * 100.0),
                    xytext=(4, 4),
                    textcoords="offset points",
                    fontsize=7.5,
                )

            ax4.set_xlabel("Predicted Dispersion Spread (Std Dev km)", fontsize=10)
            ax4.set_ylabel("Active Particle Fraction (%)", fontsize=10)
            ax4.set_ylim(0, 105)
            ax4.grid(True, linestyle=":", alpha=0.6)

        # Overall Figure Title & Watermarks
        fig.suptitle(
            "SIH26143 Phase 7: Forward Counterfactual Simulation Diagnostic\n"
            "Physical Advection + Diffusion Consistency Testing (HYCOM Currents + ERA5 Wind Leeway)",
            fontsize=15,
            fontweight="bold",
            y=0.98,
        )

        fig.text(
            0.5,
            0.01,
            "SCIENTIFIC NOTICE: Physical consistency test only. Does NOT prove responsibility or guilt. "
            "Pipeline corridor coordinates were strictly excluded from algorithm inputs.",
            ha="center",
            fontsize=9,
            color="#555555",
            style="italic",
        )

        fig.subplots_adjust(top=0.92, bottom=0.06, left=0.12, right=0.94, hspace=0.30, wspace=0.36)
        plt.savefig(self.diagnostic_png_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved diagnostic figure to {self.diagnostic_png_path}")

    def run(self) -> Dict[str, Any]:
        """
        End-to-end execution of Phase 7 forward counterfactual simulations.
        """
        logger.info(f"Starting Phase 7 Forward Counterfactual Simulations for {self.case_id}...")
        sim_records = self.run_all_simulations()
        return {
            "case_id": self.case_id,
            "total_simulations": len(sim_records),
            "summary_csv": self.summary_csv_path,
            "summary_json": self.summary_json_path,
            "diagnostic_png": self.diagnostic_png_path,
        }
