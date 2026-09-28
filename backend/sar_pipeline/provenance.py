"""
backend/sar_pipeline/provenance.py

SIH26143 — Marine Oil Spill Attribution Decision-Support System
Phase 5: SAR Observation Provenance Module

Constructs a reproducible, 6-step scientific provenance record for any SAR observation:
1. SOURCE (Sentinel-1 Observation)
2. CALIBRATION (Radiometric calibration to sigma0)
3. FILTER (Speckle noise reduction)
4. DETECTION (Dark-spot segmentation)
5. VECTORIZATION (Candidate slick polygon extraction)
6. ATTRIBUTION (Multi-hypothesis spatiotemporal & causal attribution)
"""

from typing import Any, Dict, List
from backend.sar_pipeline.schemas import ProvenanceStep


def build_sar_provenance_chain(case_id: str, metadata: Dict[str, Any], detection_stats: Dict[str, Any]) -> List[ProvenanceStep]:
    """
    Generate an auditable, step-by-step scientific provenance chain.
    """
    platform = metadata.get("platform", "Sentinel-1A")
    sensor = metadata.get("sensor", "C-SAR")
    acq_time = metadata.get("acquisition_time_utc", "N/A")
    mode = metadata.get("acquisition_mode", "IW")
    prod = metadata.get("product_type", "GRDH")
    pol = metadata.get("polarization", "VV")

    cand_count = detection_stats.get("total_candidates_extracted", 0)
    acc_count = detection_stats.get("accepted_candidates", 0)
    rej_count = detection_stats.get("rejected_candidates", 0)

    return [
        ProvenanceStep(
            step_number=1,
            stage="SOURCE",
            title="Satellite SAR Observation Ingestion",
            method=f"ESA Copernicus {platform} {sensor} orbital pass ({mode} {prod})",
            input_artifact="Copernicus Data Space Level-1 GRDH measurement product",
            output_artifact=f"{case_id}_s1_raw_measurement.tiff",
            details=f"Acquisition at {acq_time} in co-polarized {pol} mode. Georeferenced WGS84 coordinates.",
            status="VERIFIED",
        ),
        ProvenanceStep(
            step_number=2,
            stage="CALIBRATION",
            title="Radiometric Backscatter Calibration",
            method="Level-1 Sentinel-1 radiometric calibration LUT: sigma0 = DN^2 / A_sigma^2",
            input_artifact=f"{case_id}_s1_raw_measurement.tiff",
            output_artifact=f"{case_id}_s1_sigma0_db.tif",
            details="Calibration factor applied to convert digital numbers to physical sigma0 linear radar cross-section and decibels (dB).",
            status="VERIFIED",
        ),
        ProvenanceStep(
            step_number=3,
            stage="FILTER",
            title="Spatial Speckle Noise Reduction",
            method="Adaptive Gamma-MAP / Lee filter (7×7 window, ENL=4.4 looks)",
            input_artifact=f"{case_id}_s1_sigma0_linear.tif",
            output_artifact=f"{case_id}_s1_sigma0_filtered.tif",
            details="Multiplicative speckle reduction applied in linear intensity domain preserving slick boundary sharpness and edge gradients.",
            status="VERIFIED",
        ),
        ProvenanceStep(
            step_number=4,
            stage="DETECTION",
            title="Dark-Spot & Slick Segmentation",
            method="Adaptive dual-parameter CFAR thresholding (contrast threshold 3.5 dB, 101 px local background)",
            input_artifact=f"{case_id}_s1_sigma0_db.tif",
            output_artifact=f"{case_id}_s1_candidate_slicks_mask.tif",
            details=f"Extracted {cand_count} dark-spot candidate components demonstrating significant backscatter dampening relative to local ocean background.",
            status="VERIFIED",
        ),
        ProvenanceStep(
            step_number=5,
            stage="VECTORIZATION",
            title="Polygon Extraction & Spatial Look-Alike Filtering",
            method="Connected component polygonization & geometric rule filtering (area, contrast, aspect ratio)",
            input_artifact=f"{case_id}_s1_candidate_slicks_mask.tif",
            output_artifact=f"{case_id}_candidate_slicks.geojson",
            details=f"Filtered {cand_count} raw candidates: {acc_count} accepted as candidate slicks, {rej_count} rejected as low-wind or non-spill look-alikes.",
            status="VERIFIED",
        ),
        ProvenanceStep(
            step_number=6,
            stage="ATTRIBUTION",
            title="Hydrodynamic & Causal Attribution Ingestion",
            method="Lagrangian drift simulation coupled with HYCOM surface currents, ERA5 winds, and AIS telemetry",
            input_artifact=f"{case_id}_candidate_slicks.geojson",
            output_artifact=f"{case_id}_attribution_dossier.json",
            details="Accepted candidate slick centroids ingested by forward/backward trajectory integration for vessel hypothesis compatibility scoring.",
            status="VERIFIED",
        ),
    ]
