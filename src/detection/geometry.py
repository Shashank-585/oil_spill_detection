"""
Candidate Slick Geometric and Radiometric Feature Extraction Module.

Extracts connected components from binary detection masks and calculates:
- Pixel count and geospatially correct metric area (km^2) using latitude scaling
- Metric perimeter (km)
- Centroid (lat, lon) and geographic bounding box
- Inertia tensor equivalent ellipse length, width, aspect ratio, and orientation (deg from North)
- Radiometric statistics (mean/min sigma0 dB, mean/max local contrast dB)
- GeoJSON polygon geometries via rasterio.features.shapes
"""

import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import rasterio.features
from rasterio.transform import Affine
from scipy.ndimage import label, binary_dilation

from src.common.logging import get_logger

logger = get_logger("src.detection.geometry")

# WGS-84 Mean Earth Radius in kilometers
EARTH_RADIUS_KM = 6371.0088


def compute_metric_pixel_area_km2(lat_deg: float, res_x_deg: float, res_y_deg: float) -> float:
    """
    Compute the physical ground area of a pixel in km^2 given its latitude
    and angular grid spacing in degrees.
    """
    d_lat_rad = math.radians(abs(res_y_deg))
    d_lon_rad = math.radians(abs(res_x_deg))
    lat_rad = math.radians(lat_deg)
    
    # Differential surface area on a sphere: R^2 * cos(lat) * d_lat * d_lon
    area_km2 = (EARTH_RADIUS_KM ** 2) * math.cos(lat_rad) * d_lat_rad * d_lon_rad
    return area_km2


def extract_candidate_components(
    binary_mask: np.ndarray,
    transform: Affine,
    sigma0_db: np.ndarray,
    contrast_db: np.ndarray,
    min_pixels: int = 50
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Label connected components in the binary candidate mask and extract
    geometric and radiometric features.

    Args:
        binary_mask: 2D boolean or uint8 mask (1=candidate, 0=background).
        transform: Rasterio affine geotransform mapping pixel (col, row) to (lon, lat).
        sigma0_db: Calibrated backscatter raster in dB.
        contrast_db: Local contrast raster in dB (positive = darker than background).
        min_pixels: Minimum component size in pixels to retain in the initial extraction.

    Returns:
        Tuple of:
            - labeled_mask: 2D int32 array where pixels are labeled 1..K (0=background)
            - candidate_list: List of candidate property dictionaries
    """
    clean_mask = (binary_mask > 0).astype(np.uint8)
    
    # 8-connectivity structure for diagonal continuity of slick filaments
    struct = np.ones((3, 3), dtype=np.int32)
    labeled_array, num_features = label(clean_mask, structure=struct)
    
    logger.info(f"Identified {num_features} raw connected components in binary mask.")
    
    res_x_deg = abs(transform.a)
    res_y_deg = abs(transform.e)
    
    # Component pixel counts
    counts = np.bincount(labeled_array.ravel())
    
    candidates: List[Dict[str, Any]] = []
    filtered_labeled_mask = np.zeros_like(labeled_array, dtype=np.int32)
    retained_id = 1
    
    for comp_id in range(1, num_features + 1):
        pixel_count = counts[comp_id] if comp_id < len(counts) else 0
        if pixel_count < min_pixels:
            continue
            
        # Get row, col coordinates for this component
        rows, cols = np.where(labeled_array == comp_id)
        
        # Geographic coordinates for every pixel
        lons, lats = rasterio.transform.xy(transform, rows, cols)
        lons = np.array(lons, dtype=np.float64)
        lats = np.array(lats, dtype=np.float64)
        
        centroid_lat = float(np.mean(lats))
        centroid_lon = float(np.mean(lons))
        
        # Geospatially correct metric area calculation
        pixel_areas = np.array([
            compute_metric_pixel_area_km2(lat, res_x_deg, res_y_deg) for lat in lats
        ])
        area_km2 = float(np.sum(pixel_areas))
        
        # Geographic bounding box
        bbox = [
            float(np.min(lons)),
            float(np.min(lats)),
            float(np.max(lons)),
            float(np.max(lats))
        ]
        
        # Local metric coordinates (km) relative to centroid for shape analysis
        # 1 deg lat ≈ 111.195 km; 1 deg lon ≈ 111.195 * cos(lat) km
        cos_lat = math.cos(math.radians(centroid_lat))
        y_km = (lats - centroid_lat) * 111.195
        x_km = (lons - centroid_lon) * 111.195 * cos_lat
        
        # Equivalent Inertia Tensor / Second Moments
        if len(x_km) >= 4:
            cov_xx = np.var(x_km)
            cov_yy = np.var(y_km)
            cov_xy = np.mean((x_km - np.mean(x_km)) * (y_km - np.mean(y_km)))
            
            # Eigenvalues of 2x2 covariance matrix:
            # (cov_xx + cov_yy)/2 +/- sqrt(((cov_xx - cov_yy)/2)^2 + cov_xy^2)
            mid = (cov_xx + cov_yy) / 2.0
            diff = math.sqrt(max(0.0, ((cov_xx - cov_yy) / 2.0) ** 2 + cov_xy ** 2))
            lambda_1 = max(0.0, mid + diff)
            lambda_2 = max(0.0, mid - diff)
            
            # Standard 2-sigma equivalent ellipse axes
            length_km = float(4.0 * math.sqrt(lambda_1))
            width_km = float(4.0 * math.sqrt(max(1e-6, lambda_2)))
            aspect_ratio = float(length_km / max(width_km, 1e-3))
            
            # Orientation: angle of major eigenvector relative to True North (Y-axis)
            # theta = 0.5 * atan2(2 * cov_xy, cov_xx - cov_yy)
            # In image/map coordinates: Y is North, X is East
            angle_rad = 0.5 * math.atan2(2.0 * cov_xy, cov_yy - cov_xx)
            orientation_deg = float(math.degrees(angle_rad))
        else:
            length_km = float(math.sqrt(area_km2))
            width_km = float(math.sqrt(area_km2))
            aspect_ratio = 1.0
            orientation_deg = 0.0
            
        # Metric Perimeter (Boundary pixels count * average step)
        comp_submask = (labeled_array == comp_id)
        # Dilate 1 pixel and find border
        dilated = binary_dilation(comp_submask)
        perimeter_pixels = np.count_nonzero(dilated & (~comp_submask))
        step_km = math.sqrt(compute_metric_pixel_area_km2(centroid_lat, res_x_deg, res_y_deg))
        perimeter_km = float(perimeter_pixels * step_km)
        
        # Radiometric statistics over the candidate pixels
        comp_db = sigma0_db[rows, cols]
        comp_contrast = contrast_db[rows, cols]
        
        mean_db = float(np.mean(comp_db))
        min_db = float(np.min(comp_db))
        mean_contrast = float(np.mean(comp_contrast))
        max_contrast = float(np.max(comp_contrast))
        
        # Vectorize polygon geometry via rasterio.features.shapes
        # Slice local bounding box for vectorization efficiency
        r_min, r_max = int(np.min(rows)), int(np.max(rows)) + 1
        c_min, c_max = int(np.min(cols)), int(np.max(cols)) + 1
        sub_mask = (labeled_array[r_min:r_max, c_min:c_max] == comp_id).astype(np.uint8)
        
        sub_transform = transform @ Affine.translation(c_min, r_min)
        shape_gen = rasterio.features.shapes(sub_mask, mask=(sub_mask > 0), transform=sub_transform)
        
        polygon_geom: Optional[Dict[str, Any]] = None
        for geom, val in shape_gen:
            if val == 1:
                polygon_geom = geom
                break
                
        # Assign to filtered labeled mask
        filtered_labeled_mask[rows, cols] = retained_id
        
        candidate = {
            "candidate_id": f"CS_{retained_id:04d}",
            "numeric_id": retained_id,
            "raw_component_id": comp_id,
            "pixel_count": int(pixel_count),
            "area_km2": round(area_km2, 4),
            "perimeter_km": round(perimeter_km, 3),
            "centroid_lon": round(centroid_lon, 5),
            "centroid_lat": round(centroid_lat, 5),
            "bounding_box": [round(b, 5) for b in bbox],
            "length_km": round(length_km, 3),
            "width_km": round(width_km, 3),
            "aspect_ratio": round(aspect_ratio, 2),
            "orientation_deg": round(orientation_deg, 1),
            "mean_sigma0_db": round(mean_db, 2),
            "min_sigma0_db": round(min_db, 2),
            "mean_contrast_db": round(mean_contrast, 2),
            "max_contrast_db": round(max_contrast, 2),
            "geometry": polygon_geom
        }
        candidates.append(candidate)
        retained_id += 1

    logger.info(f"Retained {len(candidates)} candidate components after min_pixels={min_pixels} filter.")
    return filtered_labeled_mask, candidates
