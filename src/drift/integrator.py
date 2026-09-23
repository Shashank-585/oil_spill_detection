"""
Lagrangian Drift Integrator.

Simulates the transport and diffusion of surface particles under ocean currents,
wind forcing (leeway), and turbulent random walk diffusion.
Supports forward counterfactual simulation and backward source reconstruction.
"""

from datetime import datetime, timedelta
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.common.logging import get_logger
from src.environmental.interpolator import EnvironmentalForcingInterpolator

logger = get_logger(__name__)

# Geodetic constants (WGS84 spherical approximation)
METERS_PER_DEGREE_LAT = 111195.0


def meters_to_degrees(
    dx_m: float,
    dy_m: float,
    lat_deg: float,
) -> Tuple[float, float]:
    """
    Convert displacement in meters (dx eastward, dy northward)
    to displacement in degrees (dlon, dlat) at a given latitude.
    """
    dlat = dy_m / METERS_PER_DEGREE_LAT
    cos_lat = math.cos(math.radians(lat_deg))
    # Protect against division by zero at poles
    cos_lat = max(abs(cos_lat), 1e-6)
    dlon = dx_m / (METERS_PER_DEGREE_LAT * cos_lat)
    return float(dlon), float(dlat)


class LagrangianIntegrator:
    """
    Integrates particle trajectories through time and space using Euler-Maruyama
    numerical integration for advection + diffusion.
    """

    def __init__(
        self,
        interpolator: EnvironmentalForcingInterpolator,
        wind_drift_factor: float = 0.031,
        wind_deflection_angle_deg: float = 0.0,
        current_factor: float = 1.0,
        diffusion_coefficient_m2s: float = 1.0,
        time_step_seconds: float = 600.0,
    ):
        self.interpolator = interpolator
        self.wind_drift_factor = float(wind_drift_factor)
        self.wind_deflection_angle_deg = float(wind_deflection_angle_deg)
        self.current_factor = float(current_factor)
        self.diffusion_coefficient_m2s = float(diffusion_coefficient_m2s)
        self.time_step_seconds = float(time_step_seconds)

    def step(
        self,
        lat: float,
        lon: float,
        dt: datetime,
        direction: str = "backward",
        rng: Optional[np.random.RandomState] = None,
    ) -> Tuple[float, float, str]:
        """
        Perform a single time step integration from (lat, lon) at time dt.

        Parameters
        ----------
        lat, lon : float
            Current particle position in degrees.
        dt : datetime
            Current time (UTC).
        direction : str
            "forward" (+dt) or "backward" (-dt).
        rng : Optional[np.random.RandomState]
            Random number generator for diffusion.

        Returns
        -------
        Tuple[float, float, str]
            (new_lat, new_lon, status)
        """
        sign = -1.0 if direction == "backward" else 1.0

        try:
            u_oil, v_oil = self.interpolator.get_total_surface_velocity(
                lat=lat,
                lon=lon,
                dt=dt,
                wind_drift_factor=self.wind_drift_factor,
                wind_deflection_angle_deg=self.wind_deflection_angle_deg,
                current_factor=self.current_factor,
            )
        except ValueError as e:
            # Particle stepped out of environmental bounds
            return lat, lon, "boundary_exit"

        # Advective displacement in meters
        dx_adv = sign * u_oil * self.time_step_seconds
        dy_adv = sign * v_oil * self.time_step_seconds

        # Turbulent diffusion displacement in meters (Euler-Maruyama)
        if self.diffusion_coefficient_m2s > 0.0 and rng is not None:
            sigma = math.sqrt(2.0 * self.diffusion_coefficient_m2s * self.time_step_seconds)
            eta_x, eta_y = rng.normal(0.0, 1.0, size=2)
            dx_diff = sigma * eta_x
            dy_diff = sigma * eta_y
        else:
            dx_diff = 0.0
            dy_diff = 0.0

        total_dx = dx_adv + dx_diff
        total_dy = dy_adv + dy_diff

        dlon, dlat = meters_to_degrees(total_dx, total_dy, lat)
        new_lat = lat + dlat
        new_lon = lon + dlon

        return new_lat, new_lon, "active"

    def backtrack_ensemble(
        self,
        initial_particles: List[Dict[str, Any]],
        start_time: datetime,
        source_ages_hours: List[float],
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Backtrack an ensemble of particles from start_time over a series of source ages.

        Parameters
        ----------
        initial_particles : List[Dict[str, Any]]
            Particle dictionaries with lat, lon, weight, etc.
        start_time : datetime
            Observation timestamp of the candidate slick.
        source_ages_hours : List[float]
            List of backward elapsed hours (e.g. [2, 4, 6, 8, 12, 18, 24]).
        random_seed : int
            Random seed for reproducible diffusion.

        Returns
        -------
        Dict[str, Any]
            Contains:
            - 'snapshots': dict mapping age_hours to list of particle states
            - 'trajectories': list of particle trajectory histories (lat, lon, time)
        """
        rng = np.random.RandomState(random_seed)
        sorted_ages = sorted(source_ages_hours)
        max_age_hours = sorted_ages[-1]
        total_backward_seconds = max_age_hours * 3600.0

        num_steps = int(math.ceil(total_backward_seconds / self.time_step_seconds))
        dt_step = timedelta(seconds=self.time_step_seconds)

        # Target times to capture snapshots
        target_timestamps = {
            age: start_time - timedelta(hours=age)
            for age in sorted_ages
        }

        # Initialize particle state clones
        current_particles = []
        for p in initial_particles:
            current_particles.append({
                "particle_id": p["particle_id"],
                "lat": float(p["lat"]),
                "lon": float(p["lon"]),
                "weight": float(p.get("weight", 1.0 / len(initial_particles))),
                "status": "active",
            })

        # Trajectory storage: store sub-sampled points per particle
        trajectories: List[List[Dict[str, Any]]] = [
            [{"time": start_time.isoformat(), "lat": p["lat"], "lon": p["lon"]}]
            for p in current_particles
        ]

        snapshots: Dict[float, List[Dict[str, Any]]] = {}
        pending_targets = list(sorted_ages)

        current_time = start_time

        logger.info(
            f"Starting backward Lagrangian integration: {len(initial_particles)} particles, "
            f"{num_steps} steps of {self.time_step_seconds:.0f}s up to {max_age_hours}h backward."
        )

        for step_idx in range(1, num_steps + 1):
            next_time = current_time - dt_step

            for i, p in enumerate(current_particles):
                if p["status"] != "active":
                    continue

                new_lat, new_lon, status = self.step(
                    lat=p["lat"],
                    lon=p["lon"],
                    dt=current_time,
                    direction="backward",
                    rng=rng,
                )
                p["lat"] = new_lat
                p["lon"] = new_lon
                p["status"] = status

                # Store trajectory every 30 minutes (every 3 steps of 600s)
                if step_idx % 3 == 0:
                    trajectories[i].append({
                        "time": next_time.isoformat(),
                        "lat": round(new_lat, 6),
                        "lon": round(new_lon, 6),
                    })

            current_time = next_time

            # Check if we reached or crossed any target snapshot ages
            elapsed_hours = (start_time - current_time).total_seconds() / 3600.0
            new_pending = []
            for age in pending_targets:
                if elapsed_hours >= (age - 1e-4):
                    # Record snapshot at this age
                    snapshot_copy = [
                        {
                            "particle_id": p["particle_id"],
                            "lat": round(p["lat"], 6),
                            "lon": round(p["lon"], 6),
                            "weight": p["weight"],
                            "status": p["status"],
                        }
                        for p in current_particles
                    ]
                    snapshots[age] = snapshot_copy
                else:
                    new_pending.append(age)
            pending_targets = new_pending

        # If any pending target remained due to roundoff, snapshot at final state
        for age in pending_targets:
            snapshots[age] = [
                {
                    "particle_id": p["particle_id"],
                    "lat": round(p["lat"], 6),
                    "lon": round(p["lon"], 6),
                    "weight": p["weight"],
                    "status": p["status"],
                }
                for p in current_particles
            ]

        return {
            "start_time_utc": start_time.isoformat(),
            "source_ages_hours": sorted_ages,
            "snapshots": snapshots,
            "trajectories": trajectories,
        }

    def simulate_forward(
        self,
        initial_particles: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Simulate forward advection and diffusion of particles from start_time (release)
        to end_time (observation).

        Parameters
        ----------
        initial_particles : List[Dict[str, Any]]
            Particle dictionaries with lat, lon, weight, particle_id, etc.
        start_time : datetime
            Hypothesized release timestamp (UTC).
        end_time : datetime
            Satellite observation timestamp (UTC).
        random_seed : int
            Random seed for reproducible diffusion.

        Returns
        -------
        Dict[str, Any]
            Simulation result dictionary.
        """
        if start_time >= end_time:
            raise ValueError(
                f"Invalid temporal ordering: release_time ({start_time.isoformat()}) "
                f"must be strictly earlier than observation_time ({end_time.isoformat()})"
            )

        rng = np.random.RandomState(random_seed)
        total_seconds = (end_time - start_time).total_seconds()
        num_steps = int(math.ceil(total_seconds / self.time_step_seconds))
        dt_step = timedelta(seconds=self.time_step_seconds)

        # Initialize current particle states
        current_particles = []
        for p in initial_particles:
            current_particles.append({
                "particle_id": p["particle_id"],
                "lat": float(p["lat"]),
                "lon": float(p["lon"]),
                "weight": float(p.get("weight", 1.0 / len(initial_particles))),
                "status": "active",
            })

        # Trajectory storage
        trajectories: List[List[Dict[str, Any]]] = [
            [{"time": start_time.isoformat(), "lat": p["lat"], "lon": p["lon"]}]
            for p in current_particles
        ]

        current_time = start_time
        logger.debug(
            f"Forward integration: {len(initial_particles)} particles, {num_steps} steps, "
            f"{total_seconds/3600.0:.2f} hours from {start_time.isoformat()} to {end_time.isoformat()}."
        )

        for step_idx in range(1, num_steps + 1):
            next_time = current_time + dt_step
            if next_time > end_time:
                next_time = end_time

            for i, p in enumerate(current_particles):
                if p["status"] != "active":
                    continue

                new_lat, new_lon, status = self.step(
                    lat=p["lat"],
                    lon=p["lon"],
                    dt=current_time,
                    direction="forward",
                    rng=rng,
                )
                p["lat"] = new_lat
                p["lon"] = new_lon
                p["status"] = status

                # Store trajectory every 3 steps (30 min) or at the final step
                if step_idx % 3 == 0 or step_idx == num_steps:
                    trajectories[i].append({
                        "time": next_time.isoformat(),
                        "lat": round(new_lat, 6),
                        "lon": round(new_lon, 6),
                    })

            current_time = next_time

        # Final particles snapshot
        final_particles = [
            {
                "particle_id": p["particle_id"],
                "lat": round(p["lat"], 6),
                "lon": round(p["lon"], 6),
                "weight": p["weight"],
                "status": p["status"],
            }
            for p in current_particles
        ]

        # Calculate predicted distribution statistics
        active_particles = [p for p in current_particles if p["status"] == "active"]
        active_fraction = float(len(active_particles)) / float(len(current_particles)) if current_particles else 0.0

        if active_particles:
            mean_lat = float(np.mean([p["lat"] for p in active_particles]))
            mean_lon = float(np.mean([p["lon"] for p in active_particles]))
            min_lat = float(np.min([p["lat"] for p in active_particles]))
            max_lat = float(np.max([p["lat"] for p in active_particles]))
            min_lon = float(np.min([p["lon"] for p in active_particles]))
            max_lon = float(np.max([p["lon"] for p in active_particles]))

            # Metric dispersion std (km)
            dists_km = [
                math.sqrt(
                    ((p["lat"] - mean_lat) * 111.195) ** 2 +
                    ((p["lon"] - mean_lon) * 111.195 * math.cos(math.radians(mean_lat))) ** 2
                )
                for p in active_particles
            ]
            dispersion_std_km = float(np.std(dists_km)) if len(dists_km) > 1 else 0.0
        else:
            mean_lat = float(np.mean([p["lat"] for p in current_particles]))
            mean_lon = float(np.mean([p["lon"] for p in current_particles]))
            min_lat, max_lat = mean_lat, mean_lat
            min_lon, max_lon = mean_lon, mean_lon
            dispersion_std_km = 0.0

        return {
            "status": "completed",
            "start_time_utc": start_time.isoformat(),
            "end_time_utc": end_time.isoformat(),
            "duration_hours": round(total_seconds / 3600.0, 4),
            "step_count": num_steps,
            "particle_count": len(current_particles),
            "active_particle_count": len(active_particles),
            "active_particle_fraction": round(active_fraction, 4),
            "predicted_centroid": {
                "lat": round(mean_lat, 6),
                "lon": round(mean_lon, 6),
            },
            "predicted_bbox": {
                "west": round(min_lon, 6),
                "south": round(min_lat, 6),
                "east": round(max_lon, 6),
                "north": round(max_lat, 6),
            },
            "dispersion_std_km": round(dispersion_std_km, 3),
            "final_particles": final_particles,
            "trajectories": trajectories,
        }
