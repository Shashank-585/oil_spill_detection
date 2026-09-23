"""
Geospatial conventions and geodesic calculations for the SIH26143 pipeline.

CONVENTIONS:
1. Default Geographic CRS: EPSG:4326 (WGS84 2D latitude/longitude in degrees).
2. Rule: Metric distance and area operations must NEVER be performed naively
   in degree units. All physical metric evaluations must use geodesic (Haversine/Vincenty)
   or appropriate local projected coordinate systems (e.g. UTM).
"""

import math
from typing import Dict, Tuple, Union, Any

DEFAULT_GEOGRAPHIC_CRS = "EPSG:4326"
EARTH_RADIUS_METERS = 6371000.0  # Mean spherical Earth radius (IUGG)


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude in [-90, 90] and longitude in [-180, 180]."""
    if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
        return False
    if math.isnan(lat) or math.isnan(lon):
        return False
    return (-90.0 <= lat <= 90.0) and (-180.0 <= lon <= 180.0)


def validate_bounding_box(bbox: Dict[str, float]) -> bool:
    """Validate dictionary bounding box with west, south, east, north keys."""
    required = {"west", "south", "east", "north"}
    if not required.issubset(bbox.keys()):
        return False
    w, s, e, n = bbox["west"], bbox["south"], bbox["east"], bbox["north"]
    if not (validate_coordinates(s, w) and validate_coordinates(n, e)):
        return False
    return (w < e) and (s < n)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth
    using the Haversine formula.

    Returns distance in METERS.
    """
    if not (validate_coordinates(lat1, lon1) and validate_coordinates(lat2, lon2)):
        raise ValueError(f"Invalid coordinates: ({lat1}, {lon1}) or ({lat2}, {lon2})")

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    
    # Clip numerical floating inaccuracies
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in KILOMETERS."""
    return haversine_distance_m(lat1, lon1, lat2, lon2) / 1000.0


def geodesic_bounding_box_area_km2(bbox: Dict[str, float]) -> float:
    """
    Compute geodesic area of a bounding box in SQUARE KILOMETERS.
    Accurately accounts for spherical Earth geometry (latitudinal convergence).
    """
    if not validate_bounding_box(bbox):
        raise ValueError(f"Invalid bounding box: {bbox}")

    w, s, e, n = bbox["west"], bbox["south"], bbox["east"], bbox["north"]
    
    phi1 = math.radians(s)
    phi2 = math.radians(n)
    delta_lambda = math.radians(e - w)
    
    # Surface area of spherical zone: R^2 * (lon2 - lon1) * (sin(lat2) - sin(lat1))
    area_m2 = (EARTH_RADIUS_METERS ** 2) * delta_lambda * (math.sin(phi2) - math.sin(phi1))
    return abs(area_m2) / 1e6


def point_in_bbox(lat: float, lon: float, bbox: Dict[str, float]) -> bool:
    """Check if point (lat, lon) lies inside bbox."""
    return (bbox["south"] <= lat <= bbox["north"]) and (bbox["west"] <= lon <= bbox["east"])


def bboxes_intersect(bbox1: Dict[str, float], bbox2: Dict[str, float]) -> bool:
    """Check if two bounding boxes in WGS84 intersect."""
    return not (
        bbox1["east"] < bbox2["west"] or
        bbox1["west"] > bbox2["east"] or
        bbox1["north"] < bbox2["south"] or
        bbox1["south"] > bbox2["north"]
    )
