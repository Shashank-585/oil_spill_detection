"""
Sentinel-1 SAR Preprocessing Pipeline Module.

Orchestrates the conversion of raw Sentinel-1 Level-1 GRD detected amplitude
measurement rasters into analysis-ready calibrated radar backscatter products:
1. Calibrated sigma0 linear (Float32 GeoTIFF)
2. Calibrated sigma0 dB (Float32 GeoTIFF)
3. Valid data boolean mask (UInt8 GeoTIFF)
4. Comprehensive diagnostics and statistical metrics
"""

import os
import json
import time
from typing import Dict, Any, Optional, Tuple
import numpy as np
import rasterio
from rasterio.transform import Affine
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.common.paths import get_project_root, resolve_path
from src.common.config import load_config
from src.common.case_loader import load_case_config
from src.common.logging import get_logger
from src.satellite.calibration import Sentinel1Calibration
from src.satellite.speckle import apply_speckle_filter

logger = get_logger("src.satellite.preprocessor")


class Sentinel1SARPreprocessor:
    """
    End-to-end radiometric calibration and preprocessing engine for Sentinel-1.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        case_id: str = "case_001"
    ) -> None:
        self.root = get_project_root()
        self.config = config or load_config()
        self.case_id = case_id
        self.case = load_case_config(self.case_id)
        
        # Output directory
        self.out_dir = str(resolve_path("data/processed/satellite"))
        os.makedirs(self.out_dir, exist_ok=True)
        
        # Extract file paths from case config
        sat_files = self.case.raw_data.get("satellite", {}).get("files", {})
        self.raw_tif_path = str(resolve_path(sat_files.get("measurement_raster_vv", "data/raw/satellite/case_001_s1_measurement_vv.tif")))
        self.cal_xml_path = str(resolve_path(sat_files.get("calibration_lut", "data/raw/satellite/case_001_calibration_vv.xml")))
        self.annot_xml_path = str(resolve_path(sat_files.get("annotation_xml", "data/raw/satellite/case_001_annotation_vv.xml")))
        
        # Product destination paths
        self.sigma0_linear_path = os.path.join(self.out_dir, f"{self.case_id}_s1_sigma0_linear.tif")
        self.sigma0_db_path = os.path.join(self.out_dir, f"{self.case_id}_s1_sigma0_db.tif")
        self.valid_mask_path = os.path.join(self.out_dir, f"{self.case_id}_s1_valid_mask.tif")
        self.diag_plot_path = os.path.join(self.out_dir, f"{self.case_id}_s1_calibration_diagnostic.png")
        self.stats_json_path = os.path.join(self.out_dir, f"{self.case_id}_s1_preprocessing_stats.json")
        
        # Processing parameters
        sat_proc = self.config.get("satellite_processing", {})
        self.nodata_val = float(sat_proc.get("nodata_value", -9999.0))
        self.speckle_cfg = sat_proc.get("speckle_filter", {})
        self.speckle_enabled = bool(self.speckle_cfg.get("enabled", False))

    def run(self) -> Dict[str, Any]:
        """
        Execute the full Sentinel-1 SAR preprocessing pipeline.

        Returns:
            Dictionary containing processing metadata, output paths, and statistics.
        """
        t0 = time.time()
        logger.info(f"=== Starting Sentinel-1 SAR Preprocessing for {self.case_id} ===")
        logger.info(f"Input Raw Measurement: {self.raw_tif_path}")
        logger.info(f"Calibration LUT XML: {self.cal_xml_path}")
        logger.info(f"Annotation XML: {self.annot_xml_path}")

        # 1. Read Raw Measurement
        if not os.path.exists(self.raw_tif_path):
            raise FileNotFoundError(f"Raw measurement raster missing: {self.raw_tif_path}")
            
        with rasterio.open(self.raw_tif_path) as src:
            dn_raw = src.read(1)
            profile = src.profile.copy()
            transform: Affine = src.transform
            crs = str(src.crs)
            height, width = src.height, src.width
            bounds = (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
            tags = src.tags()

        logger.info(
            f"Loaded raw DN raster: shape=({height}, {width}), dtype={dn_raw.dtype}, "
            f"CRS={crs}, bounds={bounds}"
        )

        # 2. Extract Valid Data Mask
        # In Sentinel-1 Level-1 products, 0 represents NoData / outside orbital swath
        valid_mask = (dn_raw > 0)
        valid_count = int(np.count_nonzero(valid_mask))
        nodata_count = int(dn_raw.size - valid_count)
        valid_pct = (valid_count / dn_raw.size) * 100.0

        logger.info(
            f"Valid pixels: {valid_count:,} / {dn_raw.size:,} ({valid_pct:.2f}%), "
            f"NoData pixels: {nodata_count:,} ({100.0 - valid_pct:.2f}%)"
        )

        # 3. Parse and Evaluate Calibration Surface A_sigma
        calibrator = Sentinel1Calibration(
            calibration_xml_path=self.cal_xml_path,
            annotation_xml_path=self.annot_xml_path
        )
        a_sigma_2d = calibrator.compute_calibration_grid(bounds=bounds, shape=(height, width))

        # 4. Compute Calibrated Radar Backscatter (sigma0)
        # sigma0_linear = DN^2 / A_sigma^2 on valid pixels
        logger.info("Computing radiometric calibration: sigma0 = DN^2 / A_sigma^2")
        sigma0_linear = np.full((height, width), fill_value=self.nodata_val, dtype=np.float32)
        sigma0_db = np.full((height, width), fill_value=self.nodata_val, dtype=np.float32)

        dn_valid = dn_raw[valid_mask].astype(np.float64)
        a_valid = a_sigma_2d[valid_mask].astype(np.float64)

        lin_valid = (dn_valid ** 2) / (a_valid ** 2)
        db_valid = 10.0 * np.log10(lin_valid)

        sigma0_linear[valid_mask] = lin_valid.astype(np.float32)
        sigma0_db[valid_mask] = db_valid.astype(np.float32)

        # 5. Optional Speckle Filtering (Configurable, disabled by default)
        filtered_linear_path = None
        filtered_db_path = None
        if self.speckle_enabled:
            logger.info("Speckle filtering is enabled; generating filtered products...")
            filter_method = self.speckle_cfg.get("method", "lee")
            w_size = int(self.speckle_cfg.get("window_size", 5))
            n_looks = float(self.speckle_cfg.get("num_looks", 4.4))
            
            lin_filtered = apply_speckle_filter(
                raster=sigma0_linear,
                valid_mask=valid_mask,
                method=filter_method,
                window_size=w_size,
                num_looks=n_looks
            )
            # Recompute dB from filtered linear
            db_filtered = np.full_like(lin_filtered, fill_value=self.nodata_val)
            db_filtered[valid_mask] = (10.0 * np.log10(np.maximum(lin_filtered[valid_mask], 1e-10))).astype(np.float32)
            
            filtered_linear_path = os.path.join(self.out_dir, f"{self.case_id}_s1_sigma0_linear_filtered.tif")
            filtered_db_path = os.path.join(self.out_dir, f"{self.case_id}_s1_sigma0_db_filtered.tif")
            self._write_geotiff(filtered_linear_path, lin_filtered, profile, self.nodata_val, "sigma0_linear_filtered")
            self._write_geotiff(filtered_db_path, db_filtered, profile, self.nodata_val, "sigma0_db_filtered")

        # 6. Write Canonical Unfiltered Products
        logger.info(f"Saving canonical sigma0 linear raster to {self.sigma0_linear_path}")
        self._write_geotiff(self.sigma0_linear_path, sigma0_linear, profile, self.nodata_val, "sigma0_linear")

        logger.info(f"Saving canonical sigma0 dB raster to {self.sigma0_db_path}")
        self._write_geotiff(self.sigma0_db_path, sigma0_db, profile, self.nodata_val, "sigma0_db")

        logger.info(f"Saving valid data mask raster to {self.valid_mask_path}")
        mask_profile = profile.copy()
        mask_profile.update(dtype="uint8", nodata=0)
        with rasterio.open(self.valid_mask_path, "w", **mask_profile) as dst:
            dst.write(valid_mask.astype(np.uint8), 1)
            dst.update_tags(
                PRODUCT_TYPE="VALID_DATA_MASK",
                PARENT_SCENE=tags.get("PRODUCT_ID", self.case_id),
                ACQUISITION_DATETIME=tags.get("ACQUISITION_DATETIME", "")
            )

        # 7. Calculate Comprehensive Statistics
        stats = self._calculate_statistics(
            dn_raw=dn_raw,
            valid_mask=valid_mask,
            lin_valid=lin_valid,
            db_valid=db_valid,
            a_valid=a_valid,
            bounds=bounds,
            height=height,
            width=width,
            transform=transform,
            crs=crs
        )

        with open(self.stats_json_path, "w") as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Saved statistics to {self.stats_json_path}")

        # 8. Generate Visual Diagnostics
        logger.info(f"Generating 5-panel diagnostic visualization at {self.diag_plot_path}")
        self._generate_diagnostic_plot(
            dn_raw=dn_raw,
            sigma0_linear=sigma0_linear,
            sigma0_db=sigma0_db,
            valid_mask=valid_mask,
            db_valid=db_valid,
            stats=stats
        )

        elapsed = time.time() - t0
        logger.info(f"=== Sentinel-1 Preprocessing Completed Successfully in {elapsed:.2f}s ===")

        return {
            "case_id": self.case_id,
            "status": "READY FOR BASELINE DETECTION",
            "elapsed_seconds": round(elapsed, 2),
            "input_file": self.raw_tif_path,
            "output_files": {
                "sigma0_linear": self.sigma0_linear_path,
                "sigma0_db": self.sigma0_db_path,
                "valid_mask": self.valid_mask_path,
                "diagnostic_plot": self.diag_plot_path,
                "statistics_json": self.stats_json_path,
                "filtered_linear": filtered_linear_path,
                "filtered_db": filtered_db_path
            },
            "calibration_source": {
                "calibration_lut_xml": self.cal_xml_path,
                "annotation_xml": self.annot_xml_path,
                "formula": "sigma0_linear = DN^2 / A_sigma^2; sigma0_dB = 10 * log10(sigma0_linear)"
            },
            "statistics": stats
        }

    def _write_geotiff(
        self,
        filepath: str,
        data: np.ndarray,
        base_profile: Dict[str, Any],
        nodata: float,
        description: str
    ) -> None:
        """Write a Float32 GeoTIFF with DEFLATE compression and standard geospatial metadata."""
        prof = base_profile.copy()
        prof.update(
            dtype="float32",
            nodata=nodata,
            compress="deflate",
            tiled=True,
            blockxsize=512,
            blockysize=512
        )
        with rasterio.open(filepath, "w", **prof) as dst:
            dst.write(data.astype(np.float32), 1)
            dst.update_tags(
                PRODUCT_DESCRIPTION=f"Calibrated Sentinel-1 SAR {description} for {self.case_id}",
                CALIBRATION_STANDARD="ESA Sentinel-1 Level-1 Radiometric Calibration",
                UNITS="decibels (dB)" if "db" in description else "linear radar cross section",
                POLARIZATION="VV"
            )

    def _calculate_statistics(
        self,
        dn_raw: np.ndarray,
        valid_mask: np.ndarray,
        lin_valid: np.ndarray,
        db_valid: np.ndarray,
        a_valid: np.ndarray,
        bounds: Tuple[float, float, float, float],
        height: int,
        width: int,
        transform: Affine,
        crs: str
    ) -> Dict[str, Any]:
        """Compute comprehensive scientific statistics over valid SAR pixels."""
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        lin_pcts = np.percentile(lin_valid, percentiles)
        db_pcts = np.percentile(db_valid, percentiles)
        
        pixel_x_deg = abs(transform.a)
        pixel_y_deg = abs(transform.e)

        return {
            "raster_metadata": {
                "crs": crs,
                "dimensions": {"height": height, "width": width, "total_pixels": height * width},
                "bounds_epsg4326": {
                    "west": bounds[0],
                    "south": bounds[1],
                    "east": bounds[2],
                    "north": bounds[3]
                },
                "pixel_resolution_degrees": {"lon_deg": pixel_x_deg, "lat_deg": pixel_y_deg},
                "valid_pixel_count": int(np.count_nonzero(valid_mask)),
                "nodata_pixel_count": int(dn_raw.size - np.count_nonzero(valid_mask)),
                "valid_percentage": round(float(np.count_nonzero(valid_mask) / dn_raw.size * 100.0), 3)
            },
            "calibration_factor_A_sigma": {
                "min": round(float(a_valid.min()), 4),
                "max": round(float(a_valid.max()), 4),
                "mean": round(float(a_valid.mean()), 4),
                "std": round(float(a_valid.std()), 4)
            },
            "raw_digital_number_DN": {
                "min": int(dn_raw[valid_mask].min()),
                "max": int(dn_raw[valid_mask].max()),
                "mean": round(float(dn_raw[valid_mask].mean()), 2),
                "median": float(np.median(dn_raw[valid_mask]))
            },
            "calibrated_sigma0_linear": {
                "min": float(f"{lin_valid.min():.6e}"),
                "max": float(f"{lin_valid.max():.6e}"),
                "mean": float(f"{lin_valid.mean():.6e}"),
                "median": float(f"{np.median(lin_valid):.6e}"),
                "percentiles": {f"p{p}": float(f"{val:.6e}") for p, val in zip(percentiles, lin_pcts)}
            },
            "calibrated_sigma0_dB": {
                "units": "dB",
                "min": round(float(db_valid.min()), 2),
                "max": round(float(db_valid.max()), 2),
                "mean": round(float(db_valid.mean()), 2),
                "median": round(float(np.median(db_valid)), 2),
                "std": round(float(db_valid.std()), 2),
                "percentiles": {f"p{p}": round(float(val), 2) for p, val in zip(percentiles, db_pcts)}
            }
        }

    def _generate_diagnostic_plot(
        self,
        dn_raw: np.ndarray,
        sigma0_linear: np.ndarray,
        sigma0_db: np.ndarray,
        valid_mask: np.ndarray,
        db_valid: np.ndarray,
        stats: Dict[str, Any]
    ) -> None:
        """Create a 5-panel diagnostic figure comparing raw and calibrated backscatter."""
        # Subsample for plotting efficiency: step=4 (1000 x 1375 pixels)
        sub = 4
        sub_dn = dn_raw[::sub, ::sub].astype(np.float32)
        sub_lin = sigma0_linear[::sub, ::sub]
        sub_db = sigma0_db[::sub, ::sub]
        sub_mask = valid_mask[::sub, ::sub]

        sub_dn[~sub_mask] = np.nan
        sub_lin[~sub_mask] = np.nan
        sub_db[~sub_mask] = np.nan

        fig = plt.figure(figsize=(20, 12), dpi=150)
        gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.0], hspace=0.25, wspace=0.20)

        # 1. Raw DN
        ax1 = fig.add_subplot(gs[0, 0])
        p1, p99_dn = np.percentile(dn_raw[valid_mask], [1, 99])
        im1 = ax1.imshow(sub_dn, cmap="gray", vmin=p1, vmax=p99_dn, origin="upper")
        ax1.set_title("1. Raw Amplitude DN (uint16)", fontsize=12, fontweight="bold")
        ax1.axis("off")
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04, label="Digital Number")

        # 2. Sigma0 Linear
        ax2 = fig.add_subplot(gs[0, 1])
        p1_lin, p99_lin = np.percentile(sigma0_linear[valid_mask], [1, 99])
        im2 = ax2.imshow(sub_lin, cmap="gray", vmin=p1_lin, vmax=p99_lin, origin="upper")
        ax2.set_title("2. Calibrated $\\sigma^0$ Linear (Intensity)", fontsize=12, fontweight="bold")
        ax2.axis("off")
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04, label="Linear Radar Cross Section")

        # 3. Sigma0 dB
        ax3 = fig.add_subplot(gs[0, 2])
        im3 = ax3.imshow(sub_db, cmap="viridis", vmin=-28, vmax=-10, origin="upper")
        ax3.set_title("3. Calibrated $\\sigma^0$ (dB)", fontsize=12, fontweight="bold")
        ax3.axis("off")
        plt.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04, label="Backscatter $\\sigma^0$ (dB)")

        # 4. Valid Mask
        ax4 = fig.add_subplot(gs[1, 0])
        im4 = ax4.imshow(sub_mask.astype(np.uint8), cmap="Blues", vmin=0, vmax=1, origin="upper")
        ax4.set_title(f"4. Valid / NoData Mask ({stats['raster_metadata']['valid_percentage']}% Valid)", fontsize=12, fontweight="bold")
        ax4.axis("off")
        plt.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04, ticks=[0, 1], label="0: NoData | 1: Valid")

        # 5. Sigma0 dB Histogram
        ax5 = fig.add_subplot(gs[1, 1:])
        hist_sample = np.random.choice(db_valid, size=min(500000, len(db_valid)), replace=False)
        counts, bins, patches = ax5.hist(hist_sample, bins=120, range=(-35, 10), density=True, color="#1f77b4", alpha=0.75, edgecolor="black", linewidth=0.5)
        
        med = stats["calibrated_sigma0_dB"]["median"]
        mean_db = stats["calibrated_sigma0_dB"]["mean"]
        ax5.axvline(med, color="crimson", linestyle="--", linewidth=1.8, label=f"Median: {med:.2f} dB")
        ax5.axvline(mean_db, color="gold", linestyle="-.", linewidth=1.8, label=f"Mean: {mean_db:.2f} dB")
        ax5.axvspan(-32, -24, color="purple", alpha=0.15, label="Typical Oil Slick Range (-32 to -24 dB)")
        ax5.axvspan(-24, -14, color="teal", alpha=0.10, label="Typical Clean Sea Clutter (-24 to -14 dB)")
        
        ax5.set_title("5. Calibrated Backscatter Distribution ($\\sigma^0$ dB)", fontsize=12, fontweight="bold")
        ax5.set_xlabel("$\\sigma^0$ (dB)", fontsize=11)
        ax5.set_ylabel("Probability Density", fontsize=11)
        ax5.grid(True, linestyle=":", alpha=0.6)
        ax5.legend(loc="upper right", frameon=True)

        fig.suptitle(
            f"Sentinel-1 SAR Preprocessing Diagnostics — Case 001 (Huntington Beach)\n"
            f"Product: S1A_IW_GRDH_1SDV (VV) | Calibration: Official ESA LUT Vectors | "
            f"Shape: {stats['raster_metadata']['dimensions']['height']}x{stats['raster_metadata']['dimensions']['width']}",
            fontsize=14, fontweight="bold", y=0.98
        )

        plt.tight_layout(rect=[0, 0.02, 1, 0.95])
        plt.savefig(self.diag_plot_path, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    preprocessor = Sentinel1SARPreprocessor()
    result = preprocessor.run()
    print("\n--- Preprocessing Result ---")
    print("Status:", result["status"])
    print("Linear Product:", result["output_files"]["sigma0_linear"])
    print("dB Product:", result["output_files"]["sigma0_db"])
    print("Valid Mask:", result["output_files"]["valid_mask"])
    print("Diagnostic Plot:", result["output_files"]["diagnostic_plot"])
    print("Statistics JSON:", result["output_files"]["statistics_json"])
    print("dB Median:", result["statistics"]["calibrated_sigma0_dB"]["median"])
    print("dB Mean:", result["statistics"]["calibrated_sigma0_dB"]["mean"])
