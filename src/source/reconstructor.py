"""
Backward Lagrangian Source Reconstructor.

Reconstructs plausible candidate oil release locations and times by backtracking
Lagrangian particle ensembles from observed SAR candidate slicks under combined
ocean currents and surface wind forcing.
"""

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import scipy.stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import rasterio

from src.common.case_loader import load_case_config
from src.common.config import load_config
from src.common.geo import haversine_distance_km
from src.common.logging import get_logger
from src.common.paths import (
    DRIFT_PROCESSED_DIR,
    SATELLITE_PROCESSED_DIR,
    ensure_dir_exists,
    resolve_path,
)
from src.common.time_utils import parse_utc_timestamp
from src.drift.integrator import LagrangianIntegrator
from src.drift.particle_seeder import seed_particles_from_polygon, seed_particles_from_bbox
from src.environmental.interpolator import EnvironmentalForcingInterpolator

logger = get_logger(__name__)


class BackwardSourceReconstructor:
    """
    Orchestrates the backward reconstruction of candidate oil spill sources
    from observed candidate slicks and physical environmental forcing.
    """

    def __init__(
        self,
        case_id: str = "case_001",
        config_override: Optional[Dict[str, Any]] = None,
    ):
        self.case_id = case_id
        self.case_cfg = load_case_config(case_id)
        self.default_cfg = load_config()

        # Merge drift configurations
        drift_cfg = self.default_cfg.get("lagrangian_drift", {})
        reconstruction_cfg = self.default_cfg.get("backward_source_reconstruction", {})

        physics_cfg = drift_cfg.get("physics", {})
        sim_cfg = drift_cfg.get("simulation", {})

        self.wind_drift_factor = float(physics_cfg.get("wind_drift_factor", 0.031))
        self.wind_deflection_angle_deg = float(physics_cfg.get("wind_deflection_angle_deg", 0.0))
        self.current_factor = float(physics_cfg.get("current_factor", 1.0))
        self.diffusion_coefficient_m2s = float(physics_cfg.get("diffusion_coefficient_m2s", 1.0))

        self.time_step_seconds = float(reconstruction_cfg.get("time_step_seconds", sim_cfg.get("time_step_seconds", 600.0)))
        self.particle_count = int(reconstruction_cfg.get("particle_count", sim_cfg.get("particle_count", 500)))
        self.source_ages_hours = [float(h) for h in reconstruction_cfg.get("source_ages_hours", [2, 4, 6, 8, 12, 18, 24])]
        self.random_seed = int(reconstruction_cfg.get("random_seed", 42))

        # Output directory
        self.output_dir = ensure_dir_exists(DRIFT_PROCESSED_DIR)

        # Output paths
        self.hypotheses_csv_path = self.output_dir / f"{case_id}_source_hypotheses.csv"
        self.trajectories_json_path = self.output_dir / f"{case_id}_source_trajectories.json"
        self.summary_json_path = self.output_dir / f"{case_id}_source_reconstruction_summary.json"
        self.diagnostic_png_path = self.output_dir / f"{case_id}_source_reconstruction_diagnostic.png"

        # Observation timestamp
        self.obs_timestamp = parse_utc_timestamp(self.case_cfg["satellite"]["observation_timestamp_utc"])

        # Initialize environmental interpolator
        hycom_path = self.case_cfg["environmental"]["ocean_currents"]["file_path"]
        era5_path = self.case_cfg["environmental"]["wind"]["files"]["csv_path"]
        self.interpolator = EnvironmentalForcingInterpolator(
            hycom_netcdf_path=hycom_path,
            era5_wind_csv_path=era5_path,
            boundary_buffer_deg=0.15,
        )

        # Initialize Lagrangian integrator
        self.integrator = LagrangianIntegrator(
            interpolator=self.interpolator,
            wind_drift_factor=self.wind_drift_factor,
            wind_deflection_angle_deg=self.wind_deflection_angle_deg,
            current_factor=self.current_factor,
            diffusion_coefficient_m2s=self.diffusion_coefficient_m2s,
            time_step_seconds=self.time_step_seconds,
        )

    def load_candidate_slicks(self) -> List[Dict[str, Any]]:
        """Load accepted candidate slicks from Phase 3 GeoJSON."""
        geojson_path = resolve_path(self.case_cfg["satellite"]["files"]["candidate_slicks_geojson"])
        if not geojson_path.exists():
            raise FileNotFoundError(f"Candidate slicks GeoJSON not found: {geojson_path}")

        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        candidates = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            if props.get("status") == "ACCEPTED":
                candidates.append({
                    "candidate_id": props.get("candidate_id", feat.get("id")),
                    "area_km2": props.get("area_km2"),
                    "length_km": props.get("length_km"),
                    "aspect_ratio": props.get("aspect_ratio"),
                    "candidate_score": props.get("candidate_score"),
                    "centroid_lat": props.get("centroid_lat"),
                    "centroid_lon": props.get("centroid_lon"),
                    "geometry": feat.get("geometry"),
                })

        logger.info(f"Loaded {len(candidates)} accepted candidate slicks for source reconstruction.")
        return candidates

    def run_reconstruction(self) -> Dict[str, Any]:
        """
        Execute full backward Lagrangian source reconstruction across all accepted candidates.
        """
        candidates = self.load_candidate_slicks()
        if not candidates:
            raise ValueError("No accepted candidate slicks found for source reconstruction.")

        all_hypotheses: List[Dict[str, Any]] = []
        all_trajectories: Dict[str, Any] = {}
        candidate_results: Dict[str, Any] = {}

        # Spatial bounds accumulator for density grid
        all_particle_lats: List[float] = []
        all_particle_lons: List[float] = []

        hyp_idx = 1
        for cand in candidates:
            cand_id = cand["candidate_id"]
            geom = cand["geometry"]

            # Seed particles across the candidate geometry
            if geom and geom.get("type") == "Polygon":
                coords = geom["coordinates"][0]  # exterior ring: [[lon, lat], ...]
                particles = seed_particles_from_polygon(
                    polygon_coords=coords,
                    num_particles=self.particle_count,
                    random_seed=self.random_seed,
                )
            else:
                # Fallback to centroid bounding box
                c_lat = cand["centroid_lat"]
                c_lon = cand["centroid_lon"]
                particles = seed_particles_from_bbox(
                    bbox=[c_lon - 0.005, c_lat - 0.005, c_lon + 0.005, c_lat + 0.005],
                    num_particles=self.particle_count,
                    random_seed=self.random_seed,
                )

            logger.info(f"Backtracking {len(particles)} particles for candidate {cand_id}...")

            # Run backward Lagrangian ensemble
            sim_res = self.integrator.backtrack_ensemble(
                initial_particles=particles,
                start_time=self.obs_timestamp,
                source_ages_hours=self.source_ages_hours,
                random_seed=self.random_seed,
            )

            all_trajectories[cand_id] = sim_res["trajectories"]

            # Compute hypothesis metrics at each source age snapshot
            cand_hypotheses = []
            snapshots = sim_res["snapshots"]

            for age_hours in self.source_ages_hours:
                snap_particles = snapshots.get(age_hours, [])
                if not snap_particles:
                    continue

                active_particles = [p for p in snap_particles if p["status"] == "active"]
                total_snap = len(snap_particles)
                active_fraction = len(active_particles) / float(total_snap) if total_snap > 0 else 0.0

                if active_particles:
                    p_lats = np.array([p["lat"] for p in active_particles])
                    p_lons = np.array([p["lon"] for p in active_particles])
                    all_particle_lats.extend(p_lats.tolist())
                    all_particle_lons.extend(p_lons.tolist())

                    mean_lat = float(np.mean(p_lats))
                    mean_lon = float(np.mean(p_lons))
                    min_lat, max_lat = float(np.min(p_lats)), float(np.max(p_lats))
                    min_lon, max_lon = float(np.min(p_lons)), float(np.max(p_lons))

                    # Dispersion in km (standard deviation of distance from centroid)
                    dists_km = [haversine_distance_km(mean_lat, mean_lon, lat, lon) for lat, lon in zip(p_lats, p_lons)]
                    dispersion_km = float(np.std(dists_km))
                else:
                    mean_lat = cand["centroid_lat"]
                    mean_lon = cand["centroid_lon"]
                    min_lat = max_lat = mean_lat
                    min_lon = max_lon = mean_lon
                    dispersion_km = 0.0

                release_time = self.obs_timestamp - timedelta(hours=age_hours)

                # Plausibility score decays gently with backward age and active particle fraction
                # (older hypotheses carry higher dispersion and temporal uncertainty)
                temporal_factor = math.exp(-0.03 * age_hours)
                plausibility = float(cand["candidate_score"] * active_fraction * temporal_factor)

                hyp_record = {
                    "hypothesis_id": f"SH_{hyp_idx:04d}",
                    "candidate_id": cand_id,
                    "source_age_hours": age_hours,
                    "estimated_release_time_utc": release_time.isoformat(),
                    "centroid_lat": round(mean_lat, 6),
                    "centroid_lon": round(mean_lon, 6),
                    "bbox_west": round(min_lon, 6),
                    "bbox_south": round(min_lat, 6),
                    "bbox_east": round(max_lon, 6),
                    "bbox_north": round(max_lat, 6),
                    "dispersion_std_km": round(dispersion_km, 3),
                    "active_particle_fraction": round(active_fraction, 3),
                    "particle_count": total_snap,
                    "source_plausibility": round(plausibility, 4),
                }
                all_hypotheses.append(hyp_record)
                cand_hypotheses.append(hyp_record)
                hyp_idx += 1

            candidate_results[cand_id] = {
                "candidate": cand,
                "hypotheses": cand_hypotheses,
            }

        # Save hypotheses CSV
        df_hyp = pd.DataFrame(all_hypotheses)
        df_hyp.to_csv(self.hypotheses_csv_path, index=False)
        logger.info(f"Saved {len(df_hyp)} source hypotheses to {self.hypotheses_csv_path}")

        # Save trajectories JSON
        trajectories_output = {
            "case_id": self.case_id,
            "observation_timestamp_utc": self.obs_timestamp.isoformat(),
            "parameters": {
                "wind_drift_factor": self.wind_drift_factor,
                "wind_deflection_angle_deg": self.wind_deflection_angle_deg,
                "current_factor": self.current_factor,
                "diffusion_coefficient_m2s": self.diffusion_coefficient_m2s,
                "time_step_seconds": self.time_step_seconds,
                "particle_count_per_slick": self.particle_count,
                "source_ages_hours": self.source_ages_hours,
            },
            "candidate_ids": [c["candidate_id"] for c in candidates],
            "trajectories_by_candidate": all_trajectories,
        }
        with open(self.trajectories_json_path, "w", encoding="utf-8") as f:
            json.dump(trajectories_output, f, indent=2)
        logger.info(f"Saved source trajectories to {self.trajectories_json_path}")

        # Compute 2D KDE source plausibility field
        kde_grid_res = self._compute_source_plausibility_field(all_particle_lons, all_particle_lats)

        # Generate diagnostic visualization
        self._generate_diagnostic_plot(candidates, all_trajectories, all_hypotheses, kde_grid_res)

        # Save summary JSON
        summary = {
            "case_id": self.case_id,
            "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "observation_timestamp_utc": self.obs_timestamp.isoformat(),
            "candidate_slicks_count": len(candidates),
            "candidate_slicks": [c["candidate_id"] for c in candidates],
            "total_hypotheses_generated": len(all_hypotheses),
            "source_ages_hours_evaluated": self.source_ages_hours,
            "top_plausible_hypotheses": df_hyp.sort_values(by="source_plausibility", ascending=False).head(5).to_dict(orient="records"),
            "spatial_envelope": {
                "lat_min": float(min(all_particle_lats)) if all_particle_lats else None,
                "lat_max": float(max(all_particle_lats)) if all_particle_lats else None,
                "lon_min": float(min(all_particle_lons)) if all_particle_lons else None,
                "lon_max": float(max(all_particle_lons)) if all_particle_lons else None,
            },
            "files": {
                "hypotheses_csv": str(self.hypotheses_csv_path.relative_to(self.output_dir.parent.parent)),
                "trajectories_json": str(self.trajectories_json_path.relative_to(self.output_dir.parent.parent)),
                "diagnostic_png": str(self.diagnostic_png_path.relative_to(self.output_dir.parent.parent)),
            },
        }
        with open(self.summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved reconstruction summary to {self.summary_json_path}")

        return summary

    def _compute_source_plausibility_field(
        self,
        particle_lons: List[float],
        particle_lats: List[float],
    ) -> Dict[str, Any]:
        """Compute 2D KDE source plausibility density field normalized to [0, 1]."""
        if not particle_lons or not particle_lats:
            return {}

        lons = np.array(particle_lons)
        lats = np.array(particle_lats)

        w = float(np.min(lons)) - 0.02
        e = float(np.max(lons)) + 0.02
        s = float(np.min(lats)) - 0.02
        n = float(np.max(lats)) + 0.02

        grid_x, grid_y = np.mgrid[w:e:100j, s:n:100j]
        positions = np.vstack([grid_x.ravel(), grid_y.ravel()])
        values = np.vstack([lons, lats])

        kde = scipy.stats.gaussian_kde(values)
        density = np.reshape(kde(positions).T, grid_x.shape)

        max_d = np.max(density)
        norm_density = (density / max_d) if max_d > 0 else density

        return {
            "grid_lon": grid_x,
            "grid_lat": grid_y,
            "source_plausibility": norm_density,
            "extent": [w, e, s, n],
        }

    def _generate_diagnostic_plot(
        self,
        candidates: List[Dict[str, Any]],
        trajectories: Dict[str, Any],
        hypotheses: List[Dict[str, Any]],
        kde_grid_res: Dict[str, Any],
    ) -> None:
        """
        Generate 5-panel publication-grade diagnostic visualization.
        """
        fig = plt.figure(figsize=(20, 12), dpi=150)
        gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1.0], hspace=0.28, wspace=0.25)

        # External reference marker (pipeline rupture point)
        ref_lat = float(self.case_cfg.get("spatial", {}).get("incident_point", {}).get("latitude", 33.60))
        ref_lon = float(self.case_cfg.get("spatial", {}).get("incident_point", {}).get("longitude", -118.05))

        # Color palette for source ages
        age_cmap = plt.cm.plasma
        norm_age = plt.Normalize(vmin=0, vmax=max(self.source_ages_hours))

        # Panel 1: Observed Candidate Slicks on SAR backscatter
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_title("Panel 1: Observed SAR Candidate Slicks (t_obs)", fontsize=11, fontweight="bold")

        # Background sigma0 crop
        sigma0_path = resolve_path(self.case_cfg["satellite"]["files"]["sigma0_db"])
        if sigma0_path.exists():
            with rasterio.open(sigma0_path) as src:
                # Read coarse downsample for display
                ov = max(1, src.width // 600)
                img = src.read(1, out_shape=(src.height // ov, src.width // ov))
                bounds = src.bounds
                extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
                vmin, vmax = -28.0, -10.0
                ax1.imshow(img, extent=extent, cmap="gray", vmin=vmin, vmax=vmax, origin="upper", aspect="auto")

        # Plot candidate slick centroids and outlines
        colors = ["#00ffff", "#ff007f"]
        for i, cand in enumerate(candidates):
            c_color = colors[i % len(colors)]
            geom = cand.get("geometry", {})
            if geom and geom.get("type") == "Polygon":
                coords = np.array(geom["coordinates"][0])
                ax1.plot(coords[:, 0], coords[:, 1], color=c_color, linewidth=2.0, label=f"{cand['candidate_id']} ({cand['area_km2']:.3f} km²)")
            ax1.scatter([cand["centroid_lon"]], [cand["centroid_lat"]], color=c_color, marker="o", s=60, edgecolors="white", zorder=5)

        aoi = self.case_cfg["spatial"]["aoi_bounding_box"]

        # Plot external reference marker
        ax1.scatter([ref_lon], [ref_lat], color="red", marker="x", s=100, linewidth=2.5, zorder=6, label="Incident point (reference ONLY — NOT USED)")
        ax1.set_xlim([aoi["west"] - 0.02, aoi["east"] + 0.02])
        ax1.set_ylim([aoi["south"] - 0.02, aoi["north"] + 0.02])
        ax1.set_xlabel("Longitude (°)")
        ax1.set_ylabel("Latitude (°)")
        ax1.legend(loc="upper right", fontsize=8, framealpha=0.85)
        ax1.grid(True, linestyle="--", alpha=0.4)

        # Panel 2: Backward Lagrangian Particle Trajectories
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_title("Panel 2: Backward Lagrangian Drift Trajectories", fontsize=11, fontweight="bold")

        for cand_id, cand_trajs in trajectories.items():
            # Subsample 40 trajectories for display clarity
            step = max(1, len(cand_trajs) // 40)
            for traj in cand_trajs[::step]:
                t_lons = [pt["lon"] for pt in traj]
                t_lats = [pt["lat"] for pt in traj]
                ax2.plot(t_lons, t_lats, color="#3498db", alpha=0.35, linewidth=0.8)

        # Plot hypothesis centroids color-coded by age
        sc = None
        for hyp in hypotheses:
            age = hyp["source_age_hours"]
            color = age_cmap(norm_age(age))
            sc = ax2.scatter([hyp["centroid_lon"]], [hyp["centroid_lat"]], color=color, s=80, edgecolors="black", zorder=5)
            ax2.text(hyp["centroid_lon"] + 0.003, hyp["centroid_lat"], f"-{age:.0f}h", fontsize=7, color="#2c3e50")

        # Initial slick locations
        for cand in candidates:
            ax2.scatter([cand["centroid_lon"]], [cand["centroid_lat"]], color="#2ecc71", marker="s", s=70, edgecolors="black", zorder=6, label=f"Observed {cand['candidate_id']}")

        ax2.scatter([ref_lon], [ref_lat], color="red", marker="x", s=100, linewidth=2.5, zorder=7, label="Incident (reference — NOT USED)")
        ax2.set_xlim([aoi["west"] - 0.05, aoi["east"] + 0.02])
        ax2.set_ylim([aoi["south"] - 0.02, aoi["north"] + 0.02])
        ax2.set_xlabel("Longitude (°)")
        ax2.set_ylabel("Latitude (°)")
        ax2.legend(loc="lower right", fontsize=8, framealpha=0.85)
        ax2.grid(True, linestyle="--", alpha=0.4)

        # Panel 3: Source Plausibility Density Field
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.set_title("Panel 3: Reconstructed Source Plausibility Field", fontsize=11, fontweight="bold")

        if kde_grid_res and "source_plausibility" in kde_grid_res:
            gx = kde_grid_res["grid_lon"]
            gy = kde_grid_res["grid_lat"]
            sp = kde_grid_res["source_plausibility"]
            cs = ax3.contourf(gx, gy, sp, levels=15, cmap="YlOrRd", alpha=0.85)
            cbar = fig.colorbar(cs, ax=ax3, fraction=0.046, pad=0.04)
            cbar.set_label("Relative Source Plausibility [0, 1]", fontsize=9)

        # Mark slick centroids
        for cand in candidates:
            ax3.scatter([cand["centroid_lon"]], [cand["centroid_lat"]], color="blue", marker="o", s=50, label=f"Observed {cand['candidate_id']}")

        ax3.scatter([ref_lon], [ref_lat], color="black", marker="x", s=100, linewidth=2.5, label="Incident (reference — NOT USED)")
        ax3.set_xlim([aoi["west"] - 0.05, aoi["east"] + 0.02])
        ax3.set_ylim([aoi["south"] - 0.02, aoi["north"] + 0.02])
        ax3.set_xlabel("Longitude (°)")
        ax3.set_ylabel("Latitude (°)")
        ax3.legend(loc="upper left", fontsize=8, framealpha=0.85)
        ax3.grid(True, linestyle="--", alpha=0.4)

        # Panel 4: Source-Age Timeline & Dispersion
        ax4 = fig.add_subplot(gs[1, 0:2])
        ax4.set_title("Panel 4: Source-Age Dispersion and Plausibility Evolution", fontsize=11, fontweight="bold")

        df_hyp = pd.DataFrame(hypotheses)
        for cand_id, group in df_hyp.groupby("candidate_id"):
            sorted_g = group.sort_values(by="source_age_hours")
            ax4.plot(sorted_g["source_age_hours"], sorted_g["dispersion_std_km"], marker="o", linewidth=2.0, label=f"{cand_id} Cloud Dispersion (km)")

        ax4.set_xlabel("Source Age Prior to Observation (hours)", fontsize=10)
        ax4.set_ylabel("Spatial Dispersion Std (km)", fontsize=10, color="#2980b9")
        ax4.tick_params(axis="y", labelcolor="#2980b9")
        ax4.grid(True, linestyle="--", alpha=0.4)

        # Secondary y-axis for plausibility
        ax4_twin = ax4.twinx()
        for cand_id, group in df_hyp.groupby("candidate_id"):
            sorted_g = group.sort_values(by="source_age_hours")
            ax4_twin.plot(sorted_g["source_age_hours"], sorted_g["source_plausibility"], marker="s", linestyle="--", linewidth=1.5, label=f"{cand_id} Plausibility")
        ax4_twin.set_ylabel("Relative Source Plausibility [0, 1]", fontsize=10, color="#d35400")
        ax4_twin.tick_params(axis="y", labelcolor="#d35400")

        # Combine legends
        lines1, labels1 = ax4.get_legend_handles_labels()
        lines2, labels2 = ax4_twin.get_legend_handles_labels()
        ax4.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9, framealpha=0.85)

        # Panel 5: Environmental Forcing at Observation Time
        ax5 = fig.add_subplot(gs[1, 2])
        ax5.set_title(f"Panel 5: Environmental Vectors at t_obs ({self.obs_timestamp.strftime('%H:%M UTC')})", fontsize=11, fontweight="bold")

        # Sample coarse grid of points across AOI
        aoi = self.case_cfg["spatial"]["aoi_bounding_box"]
        aoi_lons = np.linspace(aoi["west"], aoi["east"], 7)
        aoi_lats = np.linspace(aoi["south"], aoi["north"], 6)
        lon_grid, lat_grid = np.meshgrid(aoi_lons, aoi_lats)

        curr_u_arr = np.zeros_like(lon_grid)
        curr_v_arr = np.zeros_like(lat_grid)
        wind_u_arr = np.zeros_like(lon_grid)
        wind_v_arr = np.zeros_like(lat_grid)

        for r in range(lon_grid.shape[0]):
            for c in range(lon_grid.shape[1]):
                la = lat_grid[r, c]
                lo = lon_grid[r, c]
                cu, cv = self.interpolator.get_ocean_current(la, lo, self.obs_timestamp)
                wu, wv = self.interpolator.get_wind(la, lo, self.obs_timestamp)
                curr_u_arr[r, c] = cu
                curr_v_arr[r, c] = cv
                wind_u_arr[r, c] = wu
                wind_v_arr[r, c] = wv

        # Scale wind vectors for display (divide by 20 to visually compare with currents)
        ax5.quiver(lon_grid, lat_grid, wind_u_arr * 0.05, wind_v_arr * 0.05, color="#e67e22", scale=1.5, alpha=0.85, label="10m Wind (leeway scale)")
        ax5.quiver(lon_grid, lat_grid, curr_u_arr, curr_v_arr, color="#2980b9", scale=1.5, alpha=0.85, label="Ocean Current (HYCOM)")

        ax5.set_xlim([aoi["west"] - 0.02, aoi["east"] + 0.02])
        ax5.set_ylim([aoi["south"] - 0.02, aoi["north"] + 0.02])
        ax5.set_xlabel("Longitude (°)")
        ax5.set_ylabel("Latitude (°)")
        ax5.legend(loc="upper right", fontsize=8, framealpha=0.85)
        ax5.grid(True, linestyle="--", alpha=0.4)

        plt.suptitle(
            f"SIH26143 Phase 4: Backward Lagrangian Source Reconstruction — {self.case_id}\n"
            f"Observation: {self.obs_timestamp.isoformat()} | Evaluated backward ages: {self.source_ages_hours}h | Particles/slick: {self.particle_count}",
            fontsize=13,
            fontweight="bold",
            y=0.98,
        )

        plt.savefig(self.diagnostic_png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved diagnostic visualization to {self.diagnostic_png_path}")
