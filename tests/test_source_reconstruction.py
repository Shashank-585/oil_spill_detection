"""
Tests for Phase 4: Backward Lagrangian Source Reconstruction.

Covers:
1. Direction inversion consistency (forward vs backward transport).
2. Known synthetic source recovery.
3. Multi-particle spatial dispersion (Euler-Maruyama turbulent diffusion).
4. Environmental interpolation bounds checking.
5. Source plausibility density field normalization [0, 1].
6. Deterministic execution with fixed random seed.
7. Case 001 end-to-end integration and artifact validation.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.common.geo import haversine_distance_m
from src.drift.integrator import LagrangianIntegrator, meters_to_degrees
from src.drift.particle_seeder import seed_particles_from_bbox, seed_particles_from_polygon
from src.environmental.interpolator import EnvironmentalForcingInterpolator
from src.source.reconstructor import BackwardSourceReconstructor


class MockConstantInterpolator:
    """Mock interpolator providing constant velocity for analytical physics tests."""

    def __init__(self, u_mps: float = 0.5, v_mps: float = 0.2):
        self.u_mps = float(u_mps)
        self.v_mps = float(v_mps)

    def get_ocean_current(self, lat: float, lon: float, dt: datetime):
        return self.u_mps, self.v_mps

    def get_wind(self, lat: float, lon: float, dt: datetime):
        return 0.0, 0.0

    def get_total_surface_velocity(self, lat: float, lon: float, dt: datetime, **kwargs):
        return self.u_mps, self.v_mps


# ---------------------------------------------------------------------------
# Test 1: Direction Inversion Consistency
# ---------------------------------------------------------------------------
def test_direction_inversion_consistency():
    """
    Verify that forward advection moves along velocity vector
    and backward advection moves opposite to velocity vector.
    With D=0, forward followed by backward step returns to the exact initial point.
    """
    mock_interp = MockConstantInterpolator(u_mps=1.0, v_mps=0.0)
    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=0.0,
        time_step_seconds=600.0,
    )

    start_lat = 33.500000
    start_lon = -118.200000
    t0 = datetime(2021, 10, 2, 0, 0, 0, tzinfo=timezone.utc)

    # Forward step: eastward (lon increases)
    fwd_lat, fwd_lon, status_fwd = integrator.step(start_lat, start_lon, t0, direction="forward")
    assert status_fwd == "active"
    assert fwd_lon > start_lon, "Forward step with positive u must increase longitude"
    assert abs(fwd_lat - start_lat) < 1e-7

    # Backward step from fwd position: westward (lon decreases)
    bwd_lat, bwd_lon, status_bwd = integrator.step(fwd_lat, fwd_lon, t0 + timedelta(seconds=600), direction="backward")
    assert status_bwd == "active"
    assert bwd_lon < fwd_lon, "Backward step with positive u must decrease longitude"

    # Must return to initial point within numerical precision (< 1 mm)
    dist_error_m = haversine_distance_m(start_lat, start_lon, bwd_lat, bwd_lon)
    assert dist_error_m < 0.01, f"Inversion position error too large: {dist_error_m} m"


# ---------------------------------------------------------------------------
# Test 2: Known Synthetic Source Recovery
# ---------------------------------------------------------------------------
def test_known_synthetic_source_recovery():
    """
    Synthetic release at (lat0, lon0) advected forward by 2h.
    Backtracking the resulting slick for 2h must recover the known release point.
    """
    u_const, v_const = 0.40, -0.20  # m/s
    mock_interp = MockConstantInterpolator(u_mps=u_const, v_mps=v_const)
    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=0.0,  # Pure advection for exact recovery
        time_step_seconds=300.0,
    )

    true_source_lat = 33.550000
    true_source_lon = -118.250000
    t_release = datetime(2021, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    t_observe = t_release + timedelta(hours=2.0)

    # 1. Forward advection of source particle ensemble for 2 hours
    source_particles = seed_particles_from_bbox(
        [true_source_lon - 0.001, true_source_lat - 0.001, true_source_lon + 0.001, true_source_lat + 0.001],
        num_particles=20,
        random_seed=42,
    )

    observed_particles = []
    for p in source_particles:
        curr_lat, curr_lon = p["lat"], p["lon"]
        curr_t = t_release
        for _ in range(24):  # 24 steps * 300s = 7200s = 2h
            curr_lat, curr_lon, _ = integrator.step(curr_lat, curr_lon, curr_t, direction="forward")
            curr_t += timedelta(seconds=300.0)
        observed_particles.append({
            "particle_id": p["particle_id"],
            "lat": curr_lat,
            "lon": curr_lon,
            "weight": p["weight"],
            "status": "active",
        })

    # 2. Backtrack observed particles by 2 hours
    backtrack_res = integrator.backtrack_ensemble(
        initial_particles=observed_particles,
        start_time=t_observe,
        source_ages_hours=[2.0],
        random_seed=42,
    )

    recovered_snap = backtrack_res["snapshots"][2.0]
    rec_lats = [p["lat"] for p in recovered_snap]
    rec_lons = [p["lon"] for p in recovered_snap]

    recovered_mean_lat = float(np.mean(rec_lats))
    recovered_mean_lon = float(np.mean(rec_lons))

    recovery_error_m = haversine_distance_m(true_source_lat, true_source_lon, recovered_mean_lat, recovered_mean_lon)
    assert recovery_error_m < 50.0, f"Synthetic source recovery error too large: {recovery_error_m:.2f} m"


# ---------------------------------------------------------------------------
# Test 3: Multi-Particle Spatial Dispersion
# ---------------------------------------------------------------------------
def test_multi_particle_spatial_dispersion():
    """
    Verify that turbulent diffusion (D > 0) causes particle cloud dispersion
    to monotonically increase over time, and that the cloud does not collapse.
    """
    mock_interp = MockConstantInterpolator(u_mps=0.1, v_mps=0.1)
    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=5.0,  # Active turbulent diffusion
        time_step_seconds=600.0,
    )

    # Seed 50 particles in a tight cluster
    particles = seed_particles_from_bbox(
        [-118.201, 33.500, -118.199, 33.502],
        num_particles=50,
        random_seed=42,
    )

    t0 = datetime(2021, 10, 2, 0, 0, 0, tzinfo=timezone.utc)
    res = integrator.backtrack_ensemble(
        initial_particles=particles,
        start_time=t0,
        source_ages_hours=[1.0, 4.0, 8.0],
        random_seed=42,
    )

    dispersions = []
    for age in [1.0, 4.0, 8.0]:
        snap = res["snapshots"][age]
        lats = np.array([p["lat"] for p in snap])
        lons = np.array([p["lon"] for p in snap])
        c_lat, c_lon = np.mean(lats), np.mean(lons)
        dists = [haversine_distance_m(c_lat, c_lon, la, lo) for la, lo in zip(lats, lons)]
        dispersions.append(np.std(dists))

    # Dispersion must be strictly positive (cloud has not collapsed)
    assert dispersions[0] > 10.0, "Initial 1h dispersion must be positive"
    # Dispersion must increase monotonically with backward elapsed time
    assert dispersions[1] > dispersions[0], f"4h dispersion ({dispersions[1]:.1f}m) <= 1h ({dispersions[0]:.1f}m)"
    assert dispersions[2] > dispersions[1], f"8h dispersion ({dispersions[2]:.1f}m) <= 4h ({dispersions[1]:.1f}m)"


# ---------------------------------------------------------------------------
# Test 4: Environmental Interpolation Bounds Checking
# ---------------------------------------------------------------------------
def test_environmental_interpolator_bounds_checking():
    """
    Verify that EnvironmentalForcingInterpolator correctly returns velocities
    within valid bounds and strictly raises ValueError for out-of-bounds queries.
    """
    hycom_path = "data/raw/environmental/case_001_ocean_currents_hycom.nc"
    era5_path = "data/raw/environmental/case_001_wind_era5.csv"

    interp = EnvironmentalForcingInterpolator(
        hycom_netcdf_path=hycom_path,
        era5_wind_csv_path=era5_path,
        boundary_buffer_deg=0.15,
    )

    valid_t = datetime(2021, 10, 2, 1, 58, 36, tzinfo=timezone.utc)
    valid_lat = 33.50
    valid_lon = -118.20

    # In-bounds query must succeed with finite numbers
    u_c, v_c = interp.get_ocean_current(valid_lat, valid_lon, valid_t)
    u_w, v_w = interp.get_wind(valid_lat, valid_lon, valid_t)
    assert np.isfinite(u_c) and np.isfinite(v_c)
    assert np.isfinite(u_w) and np.isfinite(v_w)

    # 1. Temporal out-of-bounds (year 2019)
    out_of_time = datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="out of .* temporal bounds"):
        interp.get_ocean_current(valid_lat, valid_lon, out_of_time)

    with pytest.raises(ValueError, match="out of .* temporal bounds"):
        interp.get_wind(valid_lat, valid_lon, out_of_time)

    # 2. Spatial out-of-bounds (far beyond buffer)
    with pytest.raises(ValueError, match="out of .* spatial bounds"):
        interp.get_ocean_current(45.0, valid_lon, valid_t)

    with pytest.raises(ValueError, match="out of .* spatial bounds"):
        interp.get_wind(valid_lat, -130.0, valid_t)


# ---------------------------------------------------------------------------
# Test 5: Source Plausibility Normalization
# ---------------------------------------------------------------------------
def test_source_plausibility_normalization():
    """
    Verify that 2D KDE source plausibility field is normalized into [0, 1]
    with maximum value of 1.0.
    """
    reconstructor = BackwardSourceReconstructor("case_001")

    # Synthetic particle cloud
    rng = np.random.RandomState(42)
    lons = (-118.40 + rng.normal(0, 0.02, 100)).tolist()
    lats = (33.40 + rng.normal(0, 0.02, 100)).tolist()

    kde_res = reconstructor._compute_source_plausibility_field(lons, lats)
    assert "source_plausibility" in kde_res
    sp_field = kde_res["source_plausibility"]

    assert np.all(sp_field >= 0.0), "Plausibility field contains negative values"
    assert np.isclose(np.max(sp_field), 1.0, atol=1e-5), f"Max plausibility must be 1.0, got {np.max(sp_field)}"
    assert np.all(sp_field <= 1.0 + 1e-5), "Plausibility field exceeds 1.0"


# ---------------------------------------------------------------------------
# Test 6: Deterministic Execution
# ---------------------------------------------------------------------------
def test_deterministic_reproducibility():
    """
    Verify that with fixed random_seed, two independent simulations
    produce identical trajectory coordinates and hypothesis centroids.
    """
    mock_interp = MockConstantInterpolator(u_mps=0.3, v_mps=-0.1)
    integrator = LagrangianIntegrator(
        interpolator=mock_interp,
        diffusion_coefficient_m2s=1.0,
        time_step_seconds=600.0,
    )

    t0 = datetime(2021, 10, 2, 0, 0, 0, tzinfo=timezone.utc)

    # Run 1
    particles1 = seed_particles_from_bbox([-118.3, 33.4, -118.2, 33.5], num_particles=20, random_seed=42)
    res1 = integrator.backtrack_ensemble(particles1, t0, [2.0, 4.0], random_seed=42)

    # Run 2
    particles2 = seed_particles_from_bbox([-118.3, 33.4, -118.2, 33.5], num_particles=20, random_seed=42)
    res2 = integrator.backtrack_ensemble(particles2, t0, [2.0, 4.0], random_seed=42)

    snap1 = res1["snapshots"][4.0]
    snap2 = res2["snapshots"][4.0]

    for p1, p2 in zip(snap1, snap2):
        assert np.isclose(p1["lat"], p2["lat"], atol=1e-9)
        assert np.isclose(p1["lon"], p2["lon"], atol=1e-9)


# ---------------------------------------------------------------------------
# Test 7: Case 001 End-to-End Output Artifacts
# ---------------------------------------------------------------------------
def test_case_001_end_to_end_artifacts():
    """
    Verify that Case 001 source reconstruction generated all 4 required artifacts
    with proper schemas, columns, and non-empty content.
    """
    hyp_csv = Path("data/processed/drift/case_001_source_hypotheses.csv")
    traj_json = Path("data/processed/drift/case_001_source_trajectories.json")
    summ_json = Path("data/processed/drift/case_001_source_reconstruction_summary.json")
    diag_png = Path("data/processed/drift/case_001_source_reconstruction_diagnostic.png")

    assert hyp_csv.exists(), f"Hypotheses CSV missing: {hyp_csv}"
    assert traj_json.exists(), f"Trajectories JSON missing: {traj_json}"
    assert summ_json.exists(), f"Summary JSON missing: {summ_json}"
    assert diag_png.exists(), f"Diagnostic PNG missing: {diag_png}"

    # Verify CSV content
    df_hyp = pd.read_csv(hyp_csv)
    assert len(df_hyp) == 14, f"Expected 14 hypotheses (2 candidates x 7 ages), got {len(df_hyp)}"
    required_cols = {
        "hypothesis_id", "candidate_id", "source_age_hours", "estimated_release_time_utc",
        "centroid_lat", "centroid_lon", "bbox_west", "bbox_south", "bbox_east", "bbox_north",
        "dispersion_std_km", "active_particle_fraction", "particle_count", "source_plausibility"
    }
    assert required_cols.issubset(df_hyp.columns), f"Missing columns in hypotheses CSV: {required_cols - set(df_hyp.columns)}"
    assert (df_hyp["active_particle_fraction"] > 0.9).all(), "Active particle fraction should be near 1.0"
    assert (df_hyp["source_plausibility"] > 0.0).all()
    assert (df_hyp["dispersion_std_km"] > 0.0).all()

    # Verify Summary JSON
    with open(summ_json, "r", encoding="utf-8") as f:
        summary = json.load(f)
    assert summary["case_id"] == "case_001"
    assert summary["candidate_slicks_count"] == 2
    assert summary["total_hypotheses_generated"] == 14
    assert len(summary["top_plausible_hypotheses"]) == 5

    # Verify Trajectories JSON
    with open(traj_json, "r", encoding="utf-8") as f:
        trajs = json.load(f)
    assert trajs["case_id"] == "case_001"
    assert "CS_0010" in trajs["trajectories_by_candidate"]
    assert "CS_0015" in trajs["trajectories_by_candidate"]
    assert len(trajs["trajectories_by_candidate"]["CS_0010"]) == 500

    # Verify Diagnostic PNG size
    assert diag_png.stat().st_size > 100_000, "Diagnostic PNG should be a detailed non-empty image"
