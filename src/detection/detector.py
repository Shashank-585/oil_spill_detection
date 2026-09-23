"""
Baseline Oil-Slick Candidate Detector Module.

Implements a transparent, deterministic baseline detector for candidate dark
slicks in calibrated Sentinel-1 VV SAR imagery:
1. Multi-mode thresholding: Global, Local Contrast, and Adaptive
2. Connected component labeling & metric geometric feature extraction
3. Transparent rule-based look-alike filtering with explicit rejection logging
4. Heuristic confidence scoring [0.0, 1.0] (candidate_score)
5. Machine-readable exports (GeoTIFF mask, GeoJSON polygons, CSV catalog, JSON summary)
6. Comprehensive multi-panel diagnostic visualization

SCIENTIFIC GUARDRAIL:
Outputs are strictly designated as 'CANDIDATE OIL SLICK', not 'confirmed oil spill'.
Confidence values are designated as 'candidate_score', not 'oil probability'.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import uniform_filter, binary_opening
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

from src.common.paths import resolve_path, get_project_root
from src.common.config import load_config
from src.common.case_loader import load_case_config
from src.common.logging import get_logger
from src.detection.geometry import extract_candidate_components
from src.detection.scoring import compute_candidate_score
from src.detection.lookalike_filter import LookAlikeFilter

logger = get_logger("src.detection.detector")


class BaselineDarkSlickDetector:
    """
    Deterministic baseline detector for candidate dark slicks in SAR backscatter.
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

        # Directories
        self.out_dir = str(resolve_path("data/processed/satellite"))
        os.makedirs(self.out_dir, exist_ok=True)

        # Configuration parameters
        det_cfg = self.config.get("dark_slick_detection", {})
        self.mode = det_cfg.get("mode", "adaptive").lower()
        self.input_product = det_cfg.get("input_product", "unfiltered").lower()
        self.global_threshold_db = float(det_cfg.get("global_threshold_db", -23.0))
        self.contrast_threshold_db = float(det_cfg.get("contrast_threshold_db", 3.5))
        self.local_window_size = int(det_cfg.get("local_window_size", 101))
        self.morphological_cleanup = bool(det_cfg.get("morphological_cleanup", True))
        self.min_connected_pixels = int(det_cfg.get("min_connected_pixels", 50))

        # Look-alike filtering rules
        la_cfg = det_cfg.get("lookalike_filtering", {})
        self.filter_rules = {
            "min_area_km2": float(la_cfg.get("min_area_km2", 0.05)),
            "max_area_km2": float(la_cfg.get("max_area_km2", 50.0)),
            "min_contrast_db": float(la_cfg.get("min_contrast_db", 2.5)),
            "max_aspect_ratio": float(la_cfg.get("max_aspect_ratio", 30.0)),
            "swath_edge_buffer_pixels": int(la_cfg.get("swath_edge_buffer_pixels", 10))
        }

        # Source input files
        sat_files = self.case.raw_data.get("satellite", {}).get("files", {})
        if self.input_product == "filtered" and "sigma0_db_filtered" in sat_files:
            self.input_db_path = str(resolve_path(sat_files["sigma0_db_filtered"]))
        else:
            self.input_db_path = str(resolve_path(sat_files.get("sigma0_db", f"data/processed/satellite/{self.case_id}_s1_sigma0_db.tif")))

        self.valid_mask_path = str(resolve_path(sat_files.get("valid_mask", f"data/processed/satellite/{self.case_id}_s1_valid_mask.tif")))

        # Destination product paths
        self.mask_out_path = os.path.join(self.out_dir, f"{self.case_id}_s1_candidate_slicks_mask.tif")
        self.geojson_out_path = os.path.join(self.out_dir, f"{self.case_id}_candidate_slicks.geojson")
        self.csv_out_path = os.path.join(self.out_dir, f"{self.case_id}_candidate_slicks.csv")
        self.summary_json_path = os.path.join(self.out_dir, f"{self.case_id}_candidate_slicks_summary.json")
        self.diagnostic_plot_path = os.path.join(self.out_dir, f"{self.case_id}_s1_detection_diagnostic.png")

    def run(self) -> Dict[str, Any]:
        """
        Execute the end-to-end baseline candidate detection pipeline.

        Returns:
            Dictionary containing detection statistics and output product paths.
        """
        t0 = time.time()
        logger.info(f"=== Starting Baseline Oil-Slick Detection for {self.case_id} ===")
        logger.info(f"Input Backscatter Raster: {self.input_db_path}")
        logger.info(f"Valid Mask: {self.valid_mask_path}")
        logger.info(
            f"Mode: '{self.mode}', Global T: {self.global_threshold_db} dB, "
            f"Contrast T: {self.contrast_threshold_db} dB, Window: {self.local_window_size} px"
        )

        # 1. Load Calibrated dB Raster & Valid Mask
        if not os.path.exists(self.input_db_path):
            raise FileNotFoundError(f"Input sigma0 dB raster not found: {self.input_db_path}")
        if not os.path.exists(self.valid_mask_path):
            raise FileNotFoundError(f"Valid mask raster not found: {self.valid_mask_path}")

        with rasterio.open(self.input_db_path) as src_db:
            sigma0_db = src_db.read(1)
            profile = src_db.profile.copy()
            transform: Affine = src_db.transform
            crs = str(src_db.crs)
            height, width = src_db.height, src_db.width
            bounds = (src_db.bounds.left, src_db.bounds.bottom, src_db.bounds.right, src_db.bounds.top)

        with rasterio.open(self.valid_mask_path) as src_mask:
            swath_mask = (src_mask.read(1) == 1)

        # Combined valid mask (in-swath and finite valid backscatter)
        valid_pixels = swath_mask & np.isfinite(sigma0_db) & (sigma0_db > -9000.0)
        logger.info(f"Loaded {np.count_nonzero(valid_pixels):,} valid SAR pixels ({height}x{width}).")

        # 2. Compute Local Ocean Background and Local Contrast
        logger.info(f"Estimating local ocean background using window_size={self.local_window_size}...")
        win = self.local_window_size
        valid_float = valid_pixels.astype(np.float32)

        mean_db_sum = uniform_filter(np.where(valid_pixels, sigma0_db, 0.0), size=win)
        weights = uniform_filter(valid_float, size=win)
        weights_safe = np.where(weights > 0, weights, 1.0)
        local_background_db = mean_db_sum / weights_safe

        # contrast(x, y) = local_background(x, y) - sigma0_dB(x, y)
        # Positive contrast indicates that the pixel is darker than surrounding sea
        contrast_db = np.where(valid_pixels, local_background_db - sigma0_db, 0.0).astype(np.float32)

        # 3. Apply Thresholding Mode
        logger.info(f"Applying thresholding mode: '{self.mode}'...")
        if self.mode == "global":
            raw_binary = valid_pixels & (sigma0_db <= self.global_threshold_db)
        elif self.mode == "contrast":
            raw_binary = valid_pixels & (contrast_db >= self.contrast_threshold_db)
        elif self.mode == "adaptive":
            # Both dark and prominent relative to local ocean background
            raw_binary = valid_pixels & (sigma0_db <= self.global_threshold_db) & (contrast_db >= self.contrast_threshold_db)
        else:
            raise ValueError(f"Unsupported detection mode: '{self.mode}'. Use 'global', 'contrast', or 'adaptive'.")

        raw_dark_pixels = int(np.count_nonzero(raw_binary))
        logger.info(f"Raw dark candidate pixels before morphological cleanup: {raw_dark_pixels:,}")

        # 4. Optional Light Morphological Opening (remove 1-2 pixel isolated speckle)
        if self.morphological_cleanup:
            # 3x3 structuring element
            struct = np.ones((3, 3), dtype=bool)
            cleaned_binary = binary_opening(raw_binary, structure=struct)
        else:
            cleaned_binary = raw_binary

        cleaned_dark_pixels = int(np.count_nonzero(cleaned_binary))
        logger.info(f"Candidate dark pixels after morphological opening: {cleaned_dark_pixels:,}")

        # 5. Connected Component Analysis & Geometric Extraction
        logger.info(f"Extracting connected components (min_pixels={self.min_connected_pixels})...")
        labeled_mask, initial_candidates = extract_candidate_components(
            binary_mask=cleaned_binary,
            transform=transform,
            sigma0_db=sigma0_db,
            contrast_db=contrast_db,
            min_pixels=self.min_connected_pixels
        )

        # 6. Compute Heuristic Confidence Scores
        for cand in initial_candidates:
            cand["candidate_score"] = compute_candidate_score(cand)
            cand["heuristic_confidence"] = cand["candidate_score"]

        # 7. Apply Transparent Look-Alike Filtering (No Silent Deletions)
        la_filter = LookAlikeFilter(**self.filter_rules)
        annotated_candidates, rejection_counts = la_filter.filter_candidates(
            candidates=initial_candidates,
            swath_valid_mask=swath_mask
        )

        accepted_candidates = [c for c in annotated_candidates if c["status"] == "ACCEPTED"]
        rejected_candidates = [c for c in annotated_candidates if c["status"] == "REJECTED"]

        # 8. Export GeoTIFF Binary Candidate Mask
        logger.info(f"Writing candidate slicks raster mask to {self.mask_out_path}")
        mask_profile = profile.copy()
        mask_profile.update(dtype="uint8", nodata=0, compress="deflate")
        # 1 for accepted candidate pixels, 2 for rejected candidate pixels, 0 for background
        export_mask = np.zeros((height, width), dtype=np.uint8)
        for cand in annotated_candidates:
            val = 1 if cand["status"] == "ACCEPTED" else 2
            export_mask[labeled_mask == cand["numeric_id"]] = val

        with rasterio.open(self.mask_out_path, "w", **mask_profile) as dst:
            dst.write(export_mask, 1)
            dst.update_tags(
                PRODUCT_DESCRIPTION="Candidate Oil Slick Detection Mask",
                VALUES="0: Background/NoData | 1: Accepted Candidate Slick | 2: Rejected Candidate Patch",
                CASE_ID=self.case_id,
                DETECTION_MODE=self.mode
            )

        # 9. Export GeoJSON Polygons
        logger.info(f"Writing candidate slicks GeoJSON to {self.geojson_out_path}")
        geojson_features = []
        for cand in annotated_candidates:
            geom = cand.get("geometry")
            if geom:
                # Omit geometry dict from properties payload
                props = {k: v for k, v in cand.items() if k != "geometry"}
                feature = {
                    "type": "Feature",
                    "id": cand["candidate_id"],
                    "geometry": geom,
                    "properties": props
                }
                geojson_features.append(feature)

        geojson_payload = {
            "type": "FeatureCollection",
            "metadata": {
                "case_id": self.case_id,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "detection_mode": self.mode,
                "total_candidates": len(annotated_candidates),
                "accepted_candidates": len(accepted_candidates),
                "rejected_candidates": len(rejected_candidates)
            },
            "features": geojson_features
        }

        with open(self.geojson_out_path, "w") as f:
            json.dump(geojson_payload, f, indent=2)

        # 10. Export CSV Metadata Table
        logger.info(f"Writing candidate slicks CSV to {self.csv_out_path}")
        csv_records = []
        for cand in annotated_candidates:
            rec = {k: v for k, v in cand.items() if k != "geometry"}
            rec["rejection_reasons"] = ";".join(rec["rejection_reasons"]) if rec["rejection_reasons"] else "NONE"
            csv_records.append(rec)

        df_candidates = pd.DataFrame(csv_records)
        df_candidates.to_csv(self.csv_out_path, index=False)

        # 11. Create Summary JSON
        elapsed = time.time() - t0
        summary = {
            "case_id": self.case_id,
            "status": "READY FOR PHASE 4",
            "elapsed_seconds": round(elapsed, 2),
            "algorithm": "Deterministic Multi-Mode SAR Backscatter & Local Contrast Detector",
            "parameters": {
                "detection_mode": self.mode,
                "input_product": self.input_product,
                "global_threshold_db": self.global_threshold_db,
                "contrast_threshold_db": self.contrast_threshold_db,
                "local_window_size_pixels": self.local_window_size,
                "morphological_cleanup": self.morphological_cleanup,
                "min_connected_pixels": self.min_connected_pixels,
                "lookalike_filtering_rules": self.filter_rules
            },
            "detection_counts": {
                "raw_dark_pixels": raw_dark_pixels,
                "cleaned_dark_pixels": cleaned_dark_pixels,
                "total_candidates_extracted": len(annotated_candidates),
                "accepted_candidates": len(accepted_candidates),
                "rejected_candidates": len(rejected_candidates),
                "rejection_reasons_breakdown": rejection_counts
            },
            "accepted_candidate_ids": [c["candidate_id"] for c in accepted_candidates],
            "output_files": {
                "candidate_slicks_mask": self.mask_out_path,
                "candidate_slicks_geojson": self.geojson_out_path,
                "candidate_slicks_csv": self.csv_out_path,
                "summary_json": self.summary_json_path,
                "diagnostic_plot": self.diagnostic_plot_path
            }
        }

        with open(self.summary_json_path, "w") as f:
            json.dump(summary, f, indent=2)

        # 12. Render 5-Panel Diagnostic Visualization
        logger.info(f"Rendering 5-panel detection diagnostic to {self.diagnostic_plot_path}...")
        self._render_diagnostic_plot(
            sigma0_db=sigma0_db,
            contrast_db=contrast_db,
            raw_binary=raw_binary,
            labeled_mask=labeled_mask,
            annotated_candidates=annotated_candidates,
            valid_pixels=valid_pixels,
            transform=transform,
            summary=summary
        )

        logger.info(f"=== Baseline Oil-Slick Detection Completed in {elapsed:.2f}s ===")
        return summary

    def _render_diagnostic_plot(
        self,
        sigma0_db: np.ndarray,
        contrast_db: np.ndarray,
        raw_binary: np.ndarray,
        labeled_mask: np.ndarray,
        annotated_candidates: List[Dict[str, Any]],
        valid_pixels: np.ndarray,
        transform: Affine,
        summary: Dict[str, Any]
    ) -> None:
        """Create a 5-panel visualization of the detection pipeline."""
        sub = 4  # Subsample step for efficient rendering (1000 x 1375)
        sub_db = sigma0_db[::sub, ::sub].copy()
        sub_contrast = contrast_db[::sub, ::sub].copy()
        sub_raw_bin = raw_binary[::sub, ::sub].copy()
        sub_labeled = labeled_mask[::sub, ::sub].copy()
        sub_valid = valid_pixels[::sub, ::sub].copy()

        sub_db[~sub_valid] = np.nan
        sub_contrast[~sub_valid] = np.nan

        fig = plt.figure(figsize=(22, 13), dpi=150)
        gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.0], hspace=0.25, wspace=0.20)

        # Panel 1: Calibrated sigma0 dB
        ax1 = fig.add_subplot(gs[0, 0])
        im1 = ax1.imshow(sub_db, cmap="viridis", vmin=-28, vmax=-12, origin="upper")
        ax1.set_title("1. Calibrated $\\sigma^0$ (dB)", fontsize=12, fontweight="bold")
        ax1.axis("off")
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04, label="Backscatter (dB)")

        # Panel 2: Local Contrast
        ax2 = fig.add_subplot(gs[0, 1])
        im2 = ax2.imshow(sub_contrast, cmap="magma", vmin=0, vmax=8, origin="upper")
        ax2.set_title(f"2. Local Contrast $\\Delta\\sigma^0$ (Window={self.local_window_size}px)", fontsize=12, fontweight="bold")
        ax2.axis("off")
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04, label="Damping Contrast (dB)")

        # Panel 3: Raw Dark Binary Threshold Mask
        ax3 = fig.add_subplot(gs[0, 2])
        im3 = ax3.imshow(sub_raw_bin.astype(np.uint8), cmap="gray", vmin=0, vmax=1, origin="upper")
        ax3.set_title(f"3. Threshold Mask (Mode: {self.mode.upper()})\n$T_{{global}}={self.global_threshold_db}$ dB, $T_{{contrast}}={self.contrast_threshold_db}$ dB", fontsize=11, fontweight="bold")
        ax3.axis("off")
        plt.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04, ticks=[0, 1], label="0: Sea | 1: Dark")

        # Panel 4: Detected Candidates with Bounding Boxes & IDs
        ax4 = fig.add_subplot(gs[1, 0:2])
        ax4.imshow(sub_db, cmap="gray", vmin=-28, vmax=-14, origin="upper")
        ax4.set_title("4. Candidate Oil Slicks (Green: ACCEPTED | Red: REJECTED)", fontsize=12, fontweight="bold")
        ax4.axis("off")

        # Overlay candidate bounding boxes and annotations
        for cand in annotated_candidates:
            # Geographic bbox: [min_lon, min_lat, max_lon, max_lat]
            min_lon, min_lat, max_lon, max_lat = cand["bounding_box"]
            # Convert to subsampled pixel coordinates
            inv_trans = ~transform
            col_min, row_max_px = inv_trans * (min_lon, min_lat)
            col_max, row_min_px = inv_trans * (max_lon, max_lat)

            # Subsample scaling
            x0 = col_min / sub
            y0 = row_min_px / sub
            w_box = max(2.0, (col_max - col_min) / sub)
            h_box = max(2.0, (row_max_px - row_min_px) / sub)

            is_accepted = (cand["status"] == "ACCEPTED")
            color = "#00ff66" if is_accepted else "#ff3333"
            linewidth = 1.8 if is_accepted else 0.9
            linestyle = "-" if is_accepted else ":"

            rect = patches.Rectangle(
                (x0, y0), w_box, h_box,
                linewidth=linewidth, edgecolor=color, facecolor="none",
                linestyle=linestyle
            )
            ax4.add_patch(rect)

            if is_accepted:
                label_text = f"{cand['candidate_id']}\nScore: {cand['candidate_score']}\n{cand['area_km2']} km²"
                ax4.text(
                    x0 + w_box + 2, y0 + h_box / 2, label_text,
                    color="white", fontsize=8, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#006622", alpha=0.8, edgecolor="#00ff66")
                )
            elif cand["area_km2"] >= 0.2:
                # Annotate prominent rejected candidates with reason
                reason = cand["rejection_reasons"][0] if cand["rejection_reasons"] else "REJECTED"
                ax4.text(
                    x0 + w_box + 2, y0 + h_box / 2, f"{cand['candidate_id']}\n({reason})",
                    color="#ff9999", fontsize=6,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#660000", alpha=0.7, edgecolor="#ff3333")
                )

        # Panel 5: Candidate Score vs Area Summary
        ax5 = fig.add_subplot(gs[1, 2])
        if annotated_candidates:
            acc_scores = [c["candidate_score"] for c in annotated_candidates if c["status"] == "ACCEPTED"]
            acc_areas = [c["area_km2"] for c in annotated_candidates if c["status"] == "ACCEPTED"]
            rej_scores = [c["candidate_score"] for c in annotated_candidates if c["status"] == "REJECTED"]
            rej_areas = [c["area_km2"] for c in annotated_candidates if c["status"] == "REJECTED"]

            if rej_scores:
                ax5.scatter(rej_areas, rej_scores, color="#ff3333", alpha=0.6, s=35, label=f"Rejected ({len(rej_scores)})", marker="x")
            if acc_scores:
                ax5.scatter(acc_areas, acc_scores, color="#00aa44", alpha=0.9, s=70, label=f"Accepted ({len(acc_scores)})", edgecolors="black", linewidth=0.8)

            ax5.set_xscale("log")
            ax5.set_xlabel("Physical Area ($km^2$)", fontsize=11)
            ax5.set_ylabel("Candidate Confidence Score", fontsize=11)
            ax5.set_ylim(0.0, 1.05)
            ax5.grid(True, linestyle=":", alpha=0.6)
            ax5.legend(loc="upper left", frameon=True)
            ax5.set_title("5. Candidate Characterization\n(Score vs. Area)", fontsize=11, fontweight="bold")
        else:
            ax5.text(0.5, 0.5, "No candidates found", ha="center", va="center")

        fig.suptitle(
            f"Baseline Dark-Slick Detection Diagnostics — Case 001 (Huntington Beach)\n"
            f"Mode: {self.mode.upper()} | Accepted Candidates: {summary['detection_counts']['accepted_candidates']} | "
            f"Rejected: {summary['detection_counts']['rejected_candidates']}",
            fontsize=14, fontweight="bold", y=0.98
        )

        plt.savefig(self.diagnostic_plot_path, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    detector = BaselineDarkSlickDetector()
    results = detector.run()
    print("\n--- Detection Results ---")
    print("Status:", results["status"])
    print("Mode:", results["parameters"]["detection_mode"])
    print("Total Extracted:", results["detection_counts"]["total_candidates_extracted"])
    print("Accepted Candidates:", results["detection_counts"]["accepted_candidates"])
    print("Rejected Candidates:", results["detection_counts"]["rejected_candidates"])
    print("Rejection Breakdown:", results["detection_counts"]["rejection_reasons_breakdown"])
    print("Mask Output:", results["output_files"]["candidate_slicks_mask"])
    print("GeoJSON Output:", results["output_files"]["candidate_slicks_geojson"])
    print("CSV Output:", results["output_files"]["candidate_slicks_csv"])
    print("Diagnostic Plot:", results["output_files"]["diagnostic_plot"])
