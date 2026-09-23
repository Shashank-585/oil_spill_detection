"""
Sentinel-1 SAR Radiometric Calibration Module.

Provides traceable calibration of Sentinel-1 Level-1 GRD detected amplitude
Digital Numbers (DN) to radar backscatter (sigma nought, sigma0).

ESA Sentinel-1 Calibration Formula:
    sigma0_linear = (DN^2) / (A_sigma^2)
    sigma0_dB = 10 * log10(sigma0_linear) = 20 * log10(DN) - 20 * log10(A_sigma)

Where:
    - DN: Ground range detected linear amplitude measurement (uint16)
    - A_sigma: Radiometric calibration factor derived from Sentinel-1
      product calibration vectors (<sigmaNought> lookup table).

Provenance:
    - Calibration Vectors: data/raw/satellite/case_001_calibration_vv.xml
    - Geolocation Grid: data/raw/satellite/case_001_annotation_vv.xml
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
import numpy as np

from src.common.logging import get_logger

logger = get_logger("src.satellite.calibration")


class Sentinel1Calibration:
    """
    Handles radiometric calibration vector parsing and spatial interpolation
    for Sentinel-1 C-band SAR products.
    """

    def __init__(
        self,
        calibration_xml_path: str,
        annotation_xml_path: Optional[str] = None
    ) -> None:
        """
        Initialize the Sentinel-1 calibration parser.

        Args:
            calibration_xml_path: Path to the product calibration XML (schema-calibration-vv).
            annotation_xml_path: Path to the product annotation XML (schema-product-vv)
                                containing geolocationGridPoint entries.
        """
        if not os.path.exists(calibration_xml_path):
            raise FileNotFoundError(f"Calibration XML not found: {calibration_xml_path}")
        
        self.calibration_xml_path = calibration_xml_path
        self.annotation_xml_path = annotation_xml_path
        
        self.cal_pixels: Optional[np.ndarray] = None
        self.cal_sigmas: Optional[np.ndarray] = None
        self.num_vectors: int = 0
        self.line_indices: List[int] = []
        
        self.gcp_points: Optional[np.ndarray] = None  # (lon, lat, line, pixel, sigma)
        
        self._parse_calibration_lut()
        if self.annotation_xml_path and os.path.exists(self.annotation_xml_path):
            self._parse_geolocation_grid()

    def _parse_calibration_lut(self) -> None:
        """
        Extract calibration vectors from the ESA calibration XML.
        """
        logger.info(f"Parsing calibration vectors from {self.calibration_xml_path}")
        tree = ET.parse(self.calibration_xml_path)
        root = tree.getroot()
        
        vectors = root.findall(".//calibrationVector")
        if not vectors:
            raise ValueError(f"No calibrationVector elements found in {self.calibration_xml_path}")
        
        self.num_vectors = len(vectors)
        self.line_indices = [int(v.find("line").text) for v in vectors]
        
        # In Sentinel-1 GRDH IW products, each calibration vector has range pixel indices and sigmaNought
        v0 = vectors[0]
        self.cal_pixels = np.array([int(p) for p in v0.find("pixel").text.split()], dtype=np.int32)
        self.cal_sigmas = np.array([float(s) for s in v0.find("sigmaNought").text.split()], dtype=np.float64)
        
        logger.info(
            f"Parsed {self.num_vectors} calibration vectors: "
            f"lines {min(self.line_indices)}..{max(self.line_indices)}, "
            f"pixels {self.cal_pixels.min()}..{self.cal_pixels.max()} ({len(self.cal_pixels)} points), "
            f"sigmaNought range: {self.cal_sigmas.min():.4f}..{self.cal_sigmas.max():.4f}"
        )

    def _parse_geolocation_grid(self) -> None:
        """
        Extract geolocation tie points from the ESA product annotation XML.
        """
        logger.info(f"Parsing geolocation grid from {self.annotation_xml_path}")
        tree = ET.parse(self.annotation_xml_path)
        root = tree.getroot()
        
        pts = root.findall(".//geolocationGridPoint")
        if not pts:
            logger.warning("No geolocationGridPoint elements found in annotation XML.")
            return
            
        gcp_list = []
        for pt in pts:
            line = float(pt.find("line").text)
            pixel = float(pt.find("pixel").text)
            lat = float(pt.find("latitude").text)
            lon = float(pt.find("longitude").text)
            # Evaluate sigmaNought for this pixel
            sig = float(np.interp(pixel, self.cal_pixels, self.cal_sigmas))
            gcp_list.append((lon, lat, line, pixel, sig))
            
        self.gcp_points = np.array(gcp_list, dtype=np.float64)
        logger.info(
            f"Parsed {len(self.gcp_points)} geolocation tie points: "
            f"lon [{self.gcp_points[:, 0].min():.4f}, {self.gcp_points[:, 0].max():.4f}], "
            f"lat [{self.gcp_points[:, 1].min():.4f}, {self.gcp_points[:, 1].max():.4f}]"
        )

    def compute_calibration_grid(
        self,
        bounds: Tuple[float, float, float, float],
        shape: Tuple[int, int]
    ) -> np.ndarray:
        """
        Compute the 2D calibration factor A_sigma(y, x) across the specified raster grid.

        Args:
            bounds: Geographic bounds (west, south, east, north) in EPSG:4326.
            shape: Raster dimensions (height, width).

        Returns:
            2D numpy array of shape (height, width) with float32 A_sigma values.
        """
        west, south, east, north = bounds
        height, width = shape
        
        if self.gcp_points is None or len(self.gcp_points) == 0:
            raise RuntimeError("Cannot compute 2D calibration grid without geolocation tie points.")
            
        # Select GCPs in and around the AOI neighborhood (+ 0.5 deg margin)
        margin = 0.5
        mask = (
            (self.gcp_points[:, 0] >= west - margin) &
            (self.gcp_points[:, 0] <= east + margin) &
            (self.gcp_points[:, 1] >= south - margin) &
            (self.gcp_points[:, 1] <= north + margin)
        )
        aoi_pts = self.gcp_points[mask]
        if len(aoi_pts) < 6:
            # Fallback to all GCPs if AOI is small or sparse
            aoi_pts = self.gcp_points
            
        lons = aoi_pts[:, 0]
        lats = aoi_pts[:, 1]
        sigmas = aoi_pts[:, 4]
        
        # Fit degree-2 bivariate polynomial surface:
        # A_sigma(lon, lat) = c0 + c1*lon + c2*lat + c3*lon^2 + c4*lat^2 + c5*lon*lat
        A = np.column_stack([np.ones_like(lons), lons, lats, lons**2, lats**2, lons * lats])
        coeffs, _, _, _ = np.linalg.lstsq(A, sigmas, rcond=None)
        
        # Evaluate on the raster grid:
        # Longitudes increase from west to east (col 0 to col width-1)
        # Latitudes decrease from north to south (row 0 to row height-1)
        grid_lons = np.linspace(west, east, width, dtype=np.float32)
        grid_lats = np.linspace(north, south, height, dtype=np.float32)
        
        # Separable evaluation for memory and performance:
        # f(lon, lat) = (c0 + c1*lon + c3*lon^2) + lat*(c2 + c5*lon) + c4*(lat^2)
        lon_term = coeffs[0] + coeffs[1] * grid_lons + coeffs[3] * (grid_lons**2)
        lat_factor = coeffs[2] + coeffs[5] * grid_lons
        c4 = coeffs[4]
        
        lut_2d = np.empty((height, width), dtype=np.float32)
        for r in range(height):
            lat = grid_lats[r]
            lut_2d[r, :] = lon_term + lat * lat_factor + c4 * (lat**2)
            
        # Verify physical validity
        if np.any(lut_2d <= 0):
            raise ValueError("Calibration grid contains non-positive A_sigma values.")
            
        logger.info(
            f"Computed calibration surface A_sigma: shape={lut_2d.shape}, "
            f"min={lut_2d.min():.4f}, max={lut_2d.max():.4f}, mean={lut_2d.mean():.4f}"
        )
        return lut_2d

    def get_metadata_summary(self) -> Dict[str, object]:
        """
        Return a summary dictionary of the parsed calibration metadata.
        """
        return {
            "calibration_xml": self.calibration_xml_path,
            "annotation_xml": self.annotation_xml_path,
            "num_vectors": self.num_vectors,
            "line_range": (min(self.line_indices), max(self.line_indices)) if self.line_indices else None,
            "pixel_range": (int(self.cal_pixels.min()), int(self.cal_pixels.max())) if self.cal_pixels is not None else None,
            "sigma0_lut_range": (float(self.cal_sigmas.min()), float(self.cal_sigmas.max())) if self.cal_sigmas is not None else None,
            "tie_points_count": len(self.gcp_points) if self.gcp_points is not None else 0
        }
