"""Tests for geospatial conventions and geodesic calculations."""
import pytest
from src.common.geo import (
    DEFAULT_GEOGRAPHIC_CRS,
    validate_coordinates,
    validate_bounding_box,
    haversine_distance_m,
    haversine_distance_km,
    geodesic_bounding_box_area_km2,
    point_in_bbox,
    bboxes_intersect
)


def test_crs_convention():
    assert DEFAULT_GEOGRAPHIC_CRS == "EPSG:4326"


def test_validate_coordinates():
    assert validate_coordinates(33.6, -118.0) is True
    assert validate_coordinates(91.0, 0.0) is False
    assert validate_coordinates(0.0, 181.0) is False


def test_validate_bounding_box():
    valid_bbox = {"west": -118.4, "south": 33.4, "east": -117.85, "north": 33.8}
    assert validate_bounding_box(valid_bbox) is True

    # Inverted bounds
    invalid_bbox = {"west": -117.85, "south": 33.4, "east": -118.4, "north": 33.8}
    assert validate_bounding_box(invalid_bbox) is False


def test_haversine_distance():
    # Long Beach (33.77°N, -118.19°W) to Huntington Beach (33.66°N, -117.99°W)
    d_m = haversine_distance_m(33.77, -118.19, 33.66, -117.99)
    d_km = haversine_distance_km(33.77, -118.19, 33.66, -117.99)
    assert 20_000 < d_m < 25_000  # Approx 22 km
    assert abs(d_m / 1000.0 - d_km) < 1e-4


def test_geodesic_area():
    bbox = {"west": -118.4, "south": 33.4, "east": -117.85, "north": 33.8}
    area = geodesic_bounding_box_area_km2(bbox)
    # 0.55 deg lon (~51 km) x 0.40 deg lat (~44.5 km) ≈ 2,270 km²
    assert 2000 < area < 2500


def test_bboxes_intersect():
    b1 = {"west": -118.4, "south": 33.4, "east": -117.85, "north": 33.8}
    b2 = {"west": -118.0, "south": 33.5, "east": -117.5, "north": 33.9}
    b3 = {"west": -117.0, "south": 33.5, "east": -116.5, "north": 33.9}
    assert bboxes_intersect(b1, b2) is True
    assert bboxes_intersect(b1, b3) is False
