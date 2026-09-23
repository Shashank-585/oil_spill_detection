"""
Tests for Phase 7: Forward Counterfactual Simulation.

Covers:
1. Valid time ordering enforcement (t_r < t_obs required).
2. Particle initialization (compact radius disk seeding).
3. Forward Lagrangian integration (positive time direction advection).
4. Environmental lookup and combined forcing (ocean currents + 3.1% wind leeway).
5. Trajectory generation (chronological sequence of states).
6. Final position generation (state at t_obs).
7. Deterministic reproducibility (fixed random seed guarantee).
8. Environmental bounds handling (graceful deactivation of out-of-bounds particles).
9. Synthetic correct hypothesis recovery (forward simulation of known release recovers observation).
10. Synthetic wrong hypothesis separation (intentionally wrong release fails consistency test).
11. Forward simulation output schema validation.
12. Case 001 simulation integrity and artifact completeness.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.common.geo import haversine_distance_m
from src.drift.integrator import LagrangianIntegrator, meters_to_degrees
from src.drift.particle_seeder import seed_particles_from_point


class MockConstantInterpolator:
    """Mock interpolator providing constant velocity fields for analytical tests."""

    def __init__(self, u_curr: float = 0.5, v_curr: float = 0.2, u_wind: float = 0.0, v_wind: float = 0.0):
        self.u_curr = float(u_curr)
        self.v_curr = float(v_curr)
        self.u_wind = float(u_wind)
        self.v_wind = float(v_wind)

    def get_ocean_current(self, lat: float, lon: float, dt: datetime):
        return self.u_curr, self.v_curr

    def get_wind(self, lat: float, lon: float, dt: datetime):
        return self.u_wind, self.v_wind

    def get_total_surface_velocity(self, lat: float, lon: float, dt: datetime, **kwargs):
        wind_drift_factor = kwargs.get("wind_drift_factor", 0.031)
        current_factor = kwargs.get("current_factor", 1.0)
        u_tot = current_factor * self.u_curr + wind_drift_factor * self.u_wind
        v_tot = current_factor * self.v_curr + wind_drift_factor * self.v_wind
        return u_tot, v_tot


# ---------------------------------------------------------------------------
# Test 1: Valid Time Ordering Enforcement
# ---------------------------------------------------------------------------
def test_valid_time_ordering():
    """Verify that t_r < t_obs is strictly enforced and invalid orderings raise ValueError."""
    mock_interp = MockConstantInterpolator()
    integrator = LagrangianIntegrator(interpolator=mock_interp, time_step_seconds=600.0)

    t_obs = datetime(2021, 10, 2, 2, 0, tzinfo=timezone.utc)
    t_after = datetime(2021, 10, 2, 3, 0, tzinfo=timezone.utc)
    t_equal = t_obs

    particles = seed_particles_from_point(33.5, -118.2, radius_m=50, num_particles=10)

    # t_r > t_obs
    with pytest.raises(ValueError, match="must be strictly earlier"):
        integrator.simulate_forward(particles, start_time=t_after, end_time=t_obs)

    # t_r == t_obs
    with pytest.raises(ValueError, match="must be strictly earlier"):
        integrator.simulate_forward(particles, start_time=t_equal, end_time=t_obs)


# ---------------------------------------------------------------------------
# Test 2: Particle Initialization
# ---------------------------------------------------------------------------
def test_particle_initialization():
    """Verify uniform disk seeding around release point with correct radius and particle count."""
    lat_center = 33.55
    lon_center = -118.15
    radius_m = 50.0
    num_particles = 250

    particles = seed_particles_from_point(
        lat=lat_center,
        lon=lon_center,
        radius_m=radius_m,
        num_particles=num_particles,
        random_seed=42,
    )

    assert len(particles) == num_particles
    assert all(p["status"] == "active" for p in particles)

    distances = [
        haversine_distance_m(lat_center, lon_center, p["lat"], p["lon"])
        for p in particles
    ]

    # All particles within radius (with slight numerical margin of 1m)
    assert max(distances) <= radius_m + 1.0

    # Mean centroid within 5 meters of center
    mean_lat = np.mean([p["lat"] for p in particles])
    mean_lon = np.mean([p["lon"] for p in particles])
    centroid_offset_m = haversine_distance_m(lat_center, lon_center, mean_lat, mean_lon)
    assert centroid_offset_m < 5.0


# ---------------------------------------------------------------------------
# Test 3: Forward Lagrangian Integration
# ---------------------------------------------------------------------------
def test_forward_integration():
    """Verify forward time progression with positive advection."""
    # Constant eastward current 1.0 m/s, zero diffusion
    mock_interp = MockConstantInterpolator(u_curr=1.0, v_curr=0.0)
    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=0.0,
        time_step_seconds=600.0,
    )

    t_start = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2021, 10, 1, 1, 0, tzinfo=timezone.utc)  # 3600 s = 6 steps

    particles = seed_particles_from_point(33.5, -118.2, radius_m=0.0, num_particles=1)
    result = integrator.simulate_forward(particles, start_time=t_start, end_time=t_end, random_seed=42)

    final_p = result["final_particles"][0]
    # Expected displacement: 3600 meters eastward
    dist_m = haversine_distance_m(33.5, -118.2, final_p["lat"], final_p["lon"])
    assert pytest.approx(dist_m, rel=1e-2) == 3600.0
    assert final_p["lon"] > -118.2  # Moved east
    assert pytest.approx(final_p["lat"], abs=1e-5) == 33.5  # No north-south movement


# ---------------------------------------------------------------------------
# Test 4: Environmental Lookup and Total Forcing
# ---------------------------------------------------------------------------
def test_environmental_lookup():
    """Verify ocean current and wind leeway combination (Voil = Vcurr + 0.031 * Vwind)."""
    u_curr, v_curr = 0.2, 0.1
    u_wind, v_wind = 10.0, -5.0
    mock_interp = MockConstantInterpolator(u_curr=u_curr, v_curr=v_curr, u_wind=u_wind, v_wind=v_wind)

    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=0.0,
        wind_drift_factor=0.031,
        time_step_seconds=1000.0,
    )

    t_start = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2021, 10, 1, 0, 16, 40, tzinfo=timezone.utc)  # 1000 s

    particles = seed_particles_from_point(33.5, -118.2, radius_m=0.0, num_particles=1)
    result = integrator.simulate_forward(particles, start_time=t_start, end_time=t_end)

    expected_u = u_curr + 0.031 * u_wind  # 0.2 + 0.31 = 0.51 m/s
    expected_v = v_curr + 0.031 * v_wind  # 0.1 - 0.155 = -0.055 m/s

    final_p = result["final_particles"][0]
    dlon_deg, dlat_deg = meters_to_degrees(
        dx_m=expected_u * 1000.0,
        dy_m=expected_v * 1000.0,
        lat_deg=33.5,
    )

    assert pytest.approx(final_p["lat"], abs=1e-5) == 33.5 + dlat_deg
    assert pytest.approx(final_p["lon"], abs=1e-5) == -118.2 + dlon_deg


# ---------------------------------------------------------------------------
# Test 5: Trajectory Generation
# ---------------------------------------------------------------------------
def test_trajectory_generation():
    """Verify trajectory timestamps are strictly increasing and states are recorded."""
    mock_interp = MockConstantInterpolator(u_curr=0.5, v_curr=0.2)
    integrator = LagrangianIntegrator(interpolator=mock_interp, time_step_seconds=600.0)

    t_start = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2021, 10, 1, 1, 0, tzinfo=timezone.utc)  # 6 steps of 600s

    particles = seed_particles_from_point(33.5, -118.2, radius_m=50, num_particles=20)
    result = integrator.simulate_forward(particles, start_time=t_start, end_time=t_end)

    trajectories = result["trajectories"]
    assert len(trajectories) == 20  # One list per particle
    single_p_traj = trajectories[0]
    assert len(single_p_traj) >= 2

    times = [datetime.fromisoformat(step["time"]) for step in single_p_traj]
    for i in range(len(times) - 1):
        assert times[i + 1] > times[i]

    assert times[0] == t_start
    assert times[-1] == t_end


# ---------------------------------------------------------------------------
# Test 6: Final Position Generation
# ---------------------------------------------------------------------------
def test_final_position_generation():
    """Verify final particle distribution is recorded at t_obs with valid coordinates."""
    mock_interp = MockConstantInterpolator(u_curr=0.3, v_curr=-0.1)
    integrator = LagrangianIntegrator(interpolator=mock_interp, time_step_seconds=600.0)

    t_start = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2021, 10, 1, 2, 0, tzinfo=timezone.utc)

    particles = seed_particles_from_point(33.5, -118.2, radius_m=50, num_particles=50)
    result = integrator.simulate_forward(particles, start_time=t_start, end_time=t_end)

    final_particles = result["final_particles"]
    assert len(final_particles) == 50

    for p in final_particles:
        assert isinstance(p["lat"], float) and not np.isnan(p["lat"])
        assert isinstance(p["lon"], float) and not np.isnan(p["lon"])
        assert -90.0 <= p["lat"] <= 90.0
        assert -180.0 <= p["lon"] <= 180.0

    assert result["active_particle_fraction"] == 1.0
    assert result["dispersion_std_km"] > 0.0


# ---------------------------------------------------------------------------
# Test 7: Deterministic Reproducibility
# ---------------------------------------------------------------------------
def test_deterministic_reproducibility():
    """Verify simulations with identical seed produce bitwise identical outputs."""
    mock_interp = MockConstantInterpolator(u_curr=0.4, v_curr=0.3)
    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=2.0,  # Stochastic diffusion active
        time_step_seconds=600.0,
    )

    t_start = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2021, 10, 1, 1, 0, tzinfo=timezone.utc)

    p1 = seed_particles_from_point(33.5, -118.2, radius_m=50, num_particles=30, random_seed=99)
    res1 = integrator.simulate_forward(p1, start_time=t_start, end_time=t_end, random_seed=99)

    p2 = seed_particles_from_point(33.5, -118.2, radius_m=50, num_particles=30, random_seed=99)
    res2 = integrator.simulate_forward(p2, start_time=t_start, end_time=t_end, random_seed=99)

    for a, b in zip(res1["final_particles"], res2["final_particles"]):
        assert a["lat"] == b["lat"]
        assert a["lon"] == b["lon"]

    assert res1["predicted_centroid"] == res2["predicted_centroid"]


# ---------------------------------------------------------------------------
# Test 8: Environmental Bounds Handling
# ---------------------------------------------------------------------------
def test_environmental_bounds():
    """Verify that particles moving out of bounds are deactivated gracefully without NaN."""
    class BoundedInterpolator:
        def get_total_surface_velocity(self, lat: float, lon: float, dt: datetime, **kwargs):
            if lat > 34.0:
                raise ValueError("Out of bounds")
            return 0.0, 10.0  # High northward velocity

    integrator = LagrangianIntegrator(
        interpolator=BoundedInterpolator(),
        diffusion_coefficient_m2s=0.0,
        time_step_seconds=600.0,
    )

    t_start = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2021, 10, 1, 2, 0, tzinfo=timezone.utc)

    particles = seed_particles_from_point(33.95, -118.2, radius_m=0.0, num_particles=5)
    result = integrator.simulate_forward(particles, start_time=t_start, end_time=t_end)

    # Some or all particles should have crossed 34.0 and been deactivated
    assert result["active_particle_fraction"] < 1.0
    for p in result["final_particles"]:
        assert not np.isnan(p["lat"])


# ---------------------------------------------------------------------------
# Test 9: Synthetic Correct Hypothesis Recovery
# ---------------------------------------------------------------------------
def test_synthetic_correct_hypothesis_recovery():
    """
    Synthetic ground truth recovery test:
    A known slick is at (33.50, -118.20) at t_obs.
    Constant velocity field carries it eastward at 0.5 m/s for 2 hours (7200 s).
    Theoretical release location was 3600 m west of the slick.
    Forward simulation from that release point MUST recover the slick within < 50 m.
    """
    u_mps = 0.5
    v_mps = 0.0
    mock_interp = MockConstantInterpolator(u_curr=u_mps, v_curr=v_mps)

    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=0.0,
        time_step_seconds=600.0,
    )

    t_release = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_obs = datetime(2021, 10, 1, 2, 0, tzinfo=timezone.utc)  # 7200 s

    # Known observation position
    obs_lat = 33.50
    obs_lon = -118.20

    # Release point is 3600 m west
    dlon_deg, _ = meters_to_degrees(-3600.0, 0.0, obs_lat)
    release_lat = obs_lat
    release_lon = obs_lon + dlon_deg

    particles = seed_particles_from_point(release_lat, release_lon, radius_m=20.0, num_particles=100, random_seed=42)
    result = integrator.simulate_forward(particles, start_time=t_release, end_time=t_obs, random_seed=42)

    pred_lat = result["predicted_centroid"]["lat"]
    pred_lon = result["predicted_centroid"]["lon"]
    error_m = haversine_distance_m(pred_lat, pred_lon, obs_lat, obs_lon)

    # Recovery must be within 50 meters
    assert error_m < 50.0


# ---------------------------------------------------------------------------
# Test 10: Synthetic Wrong Hypothesis Separation
# ---------------------------------------------------------------------------
def test_synthetic_wrong_hypothesis_separation():
    """
    Verify that an intentionally wrong release location (e.g. 15 km away)
    results in a predicted distribution clearly separated from the observed slick.
    """
    mock_interp = MockConstantInterpolator(u_curr=0.5, v_curr=0.0)
    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=1.0,
        time_step_seconds=600.0,
    )

    t_release = datetime(2021, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_obs = datetime(2021, 10, 1, 2, 0, tzinfo=timezone.utc)

    obs_lat = 33.50
    obs_lon = -118.20

    # Deliberately wrong hypothesis: released 15 km north
    wrong_lat = 33.635
    wrong_lon = -118.20

    particles = seed_particles_from_point(wrong_lat, wrong_lon, radius_m=50.0, num_particles=50, random_seed=42)
    result = integrator.simulate_forward(particles, start_time=t_release, end_time=t_obs, random_seed=42)

    pred_lat = result["predicted_centroid"]["lat"]
    pred_lon = result["predicted_centroid"]["lon"]
    separation_km = haversine_distance_m(pred_lat, pred_lon, obs_lat, obs_lon) / 1000.0

    # Final positions must remain well-separated from the true observation (> 10 km)
    assert separation_km > 10.0


# ---------------------------------------------------------------------------
# Test 11: Output Schema Validation
# ---------------------------------------------------------------------------
def test_output_schema():
    """Verify that case_001_forward_simulations.csv adheres to required schema."""
    csv_path = Path("data/processed/attribution/case_001_forward_simulations.csv")
    assert csv_path.exists(), "Forward simulations CSV does not exist"

    df = pd.read_csv(csv_path)
    expected_cols = [
        "hypothesis_id",
        "candidate_id",
        "mmsi",
        "vessel_name",
        "release_lat",
        "release_lon",
        "release_timestamp",
        "observation_timestamp",
        "duration_hours",
        "particle_count",
        "predicted_centroid_lat",
        "predicted_centroid_lon",
        "dispersion_std_km",
        "active_particle_fraction",
        "predicted_to_observed_distance_m",
        "observed_slick_id",
    ]

    for col in expected_cols:
        assert col in df.columns, f"Missing expected column '{col}'"

    assert len(df) == 19
    assert df["hypothesis_id"].nunique() == 19
    assert (df["particle_count"] == 500).all()
    assert (df["active_particle_fraction"] == 1.0).all()
    assert (df["predicted_to_observed_distance_m"] >= 0.0).all()


# ---------------------------------------------------------------------------
# Test 12: Case 001 Simulation Integrity
# ---------------------------------------------------------------------------
def test_case_001_simulation_integrity():
    """Verify all 19 Case 001 hypotheses have valid per-hypothesis cached artifacts."""
    sims_dir = Path("data/processed/attribution/simulations")
    assert sims_dir.exists(), "Simulations directory missing"

    summary_json_path = Path("data/processed/attribution/case_001_forward_simulations_summary.json")
    assert summary_json_path.exists(), "Summary JSON missing"

    with open(summary_json_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    assert summary_data["case_id"] == "case_001"
    assert summary_data["total_hypotheses_simulated"] == 19
    assert summary_data["successful_simulations"] == 19
    assert summary_data["failed_simulations"] == 0

    # Check each hypothesis folder
    hyp_ids = [f"4DH_{i:04d}" for i in range(1, 20)]
    for hid in hyp_ids:
        h_dir = sims_dir / hid
        assert h_dir.exists(), f"Missing folder for {hid}"

        traj_file = h_dir / "trajectory.json"
        particles_file = h_dir / "final_particles.json"
        meta_file = h_dir / "simulation_metadata.json"

        assert traj_file.exists(), f"Missing trajectory.json for {hid}"
        assert particles_file.exists(), f"Missing final_particles.json for {hid}"
        assert meta_file.exists(), f"Missing simulation_metadata.json for {hid}"

        # Validate non-empty and valid json
        with open(traj_file, "r", encoding="utf-8") as tf:
            traj_data = json.load(tf)
            assert len(traj_data) > 0

        with open(particles_file, "r", encoding="utf-8") as pf:
            part_data = json.load(pf)
            assert len(part_data) == 500

        with open(meta_file, "r", encoding="utf-8") as mf:
            meta_data = json.load(mf)
            assert meta_data["hypothesis_id"] == hid
            assert meta_data["active_particle_fraction"] == 1.0
