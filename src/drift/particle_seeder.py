"""
Particle Seeder for Lagrangian Drift Modelling.

Generates initial particle ensembles seeded across candidate oil slick geometries.
Supports both raster-based weighted seeding (weighted by backscatter darkness)
and vector polygon / bounding-box sampling.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from src.common.logging import get_logger

logger = get_logger(__name__)


def seed_particles_from_pixels(
    pixel_coords: List[Tuple[int, int]],
    raster_transform: Any,
    num_particles: int = 500,
    weights: Optional[np.ndarray] = None,
    random_seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Seed particles from a list of (row, col) pixel coordinates.
    Converts raster row/col to (lat, lon) coordinates using affine transform,
    with uniform sub-pixel jitter.
    """
    rng = np.random.RandomState(random_seed)
    n_pixels = len(pixel_coords)
    if n_pixels == 0:
        raise ValueError("Cannot seed particles from an empty pixel list.")

    if weights is not None:
        p_weights = np.asarray(weights, dtype=np.float64)
        p_weights = np.nan_to_num(p_weights, nan=0.0, posinf=0.0, neginf=0.0)
        p_sum = np.sum(p_weights)
        if p_sum > 0:
            probs = p_weights / p_sum
        else:
            probs = np.full(n_pixels, 1.0 / n_pixels)
    else:
        probs = np.full(n_pixels, 1.0 / n_pixels)

    # Sample pixel indices
    chosen_indices = rng.choice(n_pixels, size=num_particles, replace=True, p=probs)

    particles: List[Dict[str, Any]] = []
    # Pixel size in x (lon) and y (lat)
    px_w = raster_transform.a
    px_h = raster_transform.e  # Usually negative for north-up

    for p_id, idx in enumerate(chosen_indices):
        r, c = pixel_coords[idx]
        # Center of pixel + uniform jitter within [-0.5, 0.5] pixel
        jitter_x = rng.uniform(-0.45, 0.45)
        jitter_y = rng.uniform(-0.45, 0.45)
        pixel_x = (c + 0.5) + jitter_x
        pixel_y = (r + 0.5) + jitter_y

        # Transform to lon, lat
        lon, lat = raster_transform * (pixel_x, pixel_y)

        particles.append({
            "particle_id": p_id,
            "lat": float(lat),
            "lon": float(lon),
            "initial_lat": float(lat),
            "initial_lon": float(lon),
            "weight": 1.0 / float(num_particles),
            "status": "active",
        })

    return particles


def seed_particles_from_bbox(
    bbox: Union[Dict[str, float], List[float], Tuple[float, float, float, float]],
    num_particles: int = 500,
    random_seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Seed particles uniformly within a bounding box.
    bbox can be a dict {'west': w, 'south': s, 'east': e, 'north': n}
    or a list/tuple [w, s, e, n].
    """
    rng = np.random.RandomState(random_seed)

    if isinstance(bbox, dict):
        w, s, e, n = bbox["west"], bbox["south"], bbox["east"], bbox["north"]
    else:
        w, s, e, n = bbox[0], bbox[1], bbox[2], bbox[3]

    if w >= e or s >= n:
        raise ValueError(f"Invalid bounding box for particle seeding: {bbox}")

    lats = rng.uniform(s, n, size=num_particles)
    lons = rng.uniform(w, e, size=num_particles)

    particles: List[Dict[str, Any]] = []
    for i in range(num_particles):
        particles.append({
            "particle_id": i,
            "lat": float(lats[i]),
            "lon": float(lons[i]),
            "initial_lat": float(lats[i]),
            "initial_lon": float(lons[i]),
            "weight": 1.0 / float(num_particles),
            "status": "active",
        })

    return particles


def seed_particles_from_polygon(
    polygon_coords: List[List[float]],
    num_particles: int = 500,
    random_seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Seed particles uniformly within a polygon boundary using rejection sampling.
    polygon_coords is a list of [lon, lat] pairs defining the exterior ring.
    """
    from matplotlib.path import Path as MplPath

    poly_arr = np.array(polygon_coords)
    if poly_arr.ndim != 2 or poly_arr.shape[0] < 3:
        raise ValueError("Polygon must have at least 3 vertices.")

    # lon is col 0, lat is col 1
    w = float(np.min(poly_arr[:, 0]))
    e = float(np.max(poly_arr[:, 0]))
    s = float(np.min(poly_arr[:, 1]))
    n = float(np.max(poly_arr[:, 1]))

    path = MplPath(poly_arr)
    rng = np.random.RandomState(random_seed)

    accepted_lats: List[float] = []
    accepted_lons: List[float] = []

    # Rejection sampling in batches
    batch_size = max(num_particles * 2, 1000)
    max_attempts = 100
    attempt = 0

    while len(accepted_lats) < num_particles and attempt < max_attempts:
        attempt += 1
        cand_lons = rng.uniform(w, e, size=batch_size)
        cand_lats = rng.uniform(s, n, size=batch_size)
        points = np.column_stack([cand_lons, cand_lats])

        inside = path.contains_points(points)
        for pt in points[inside]:
            accepted_lons.append(float(pt[0]))
            accepted_lats.append(float(pt[1]))
            if len(accepted_lats) == num_particles:
                break

    if len(accepted_lats) < num_particles:
        # Fallback: fill remaining with uniform bbox sampling
        remaining = num_particles - len(accepted_lats)
        cand_lons = rng.uniform(w, e, size=remaining)
        cand_lats = rng.uniform(s, n, size=remaining)
        for i in range(remaining):
            accepted_lons.append(float(cand_lons[i]))
            accepted_lats.append(float(cand_lats[i]))

    particles: List[Dict[str, Any]] = []
    for i in range(num_particles):
        particles.append({
            "particle_id": i,
            "lat": float(accepted_lats[i]),
            "lon": float(accepted_lons[i]),
            "initial_lat": float(accepted_lats[i]),
            "initial_lon": float(accepted_lons[i]),
            "weight": 1.0 / float(num_particles),
            "status": "active",
        })

    return particles


def seed_particles_from_point(
    lat: float,
    lon: float,
    radius_m: float = 50.0,
    num_particles: int = 500,
    random_seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Seed a compact ensemble of particles around a single release point (lat, lon).
    Uses uniform disk sampling within radius_m.
    """
    from src.drift.integrator import meters_to_degrees

    rng = np.random.RandomState(random_seed)

    # Uniform disk sampling: r = R * sqrt(u), theta = 2 * pi * v
    u = rng.uniform(0.0, 1.0, size=num_particles)
    v = rng.uniform(0.0, 1.0, size=num_particles)
    r = radius_m * np.sqrt(u)
    theta = 2.0 * np.pi * v

    dx_m = r * np.cos(theta)
    dy_m = r * np.sin(theta)

    particles: List[Dict[str, Any]] = []
    for i in range(num_particles):
        dlon, dlat = meters_to_degrees(float(dx_m[i]), float(dy_m[i]), lat)
        p_lat = lat + dlat
        p_lon = lon + dlon
        particles.append({
            "particle_id": i,
            "lat": float(p_lat),
            "lon": float(p_lon),
            "initial_lat": float(p_lat),
            "initial_lon": float(p_lon),
            "weight": 1.0 / float(num_particles),
            "status": "active",
        })

    return particles
