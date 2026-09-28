"""
src/detection/interface.py

SIH26143 — Marine Oil Spill Attribution Decision-Support System
Phase 5: SAR Observation Processing Pipeline — Detector Interface

Defines formal detection interfaces decoupling preprocessing, deterministic
threshold detectors, and future ML detectors (e.g. U-Net, DeepLab, Vision Transformer).

SCIENTIFIC INTEGRITY GUARDRAILS:
1. Operational detector channel is strictly calibrated Sentinel-1 VV SAR backscatter.
2. The deterministic baseline detector is the operational default.
3. The ML detector interface is a structured integration point for future models;
   no imaginary models or fake confidence predictions are fabricated.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class DetectionOutput:
    """
    Standardized container for candidate slick segmentation outputs.
    """

    def __init__(
        self,
        candidate_count: int,
        accepted_count: int,
        rejected_count: int,
        raw_dark_pixels: int,
        cleaned_dark_pixels: int,
        rejection_reasons: Dict[str, int],
        mask_array: Optional[np.ndarray] = None,
        polygon_features: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.candidate_count = candidate_count
        self.accepted_count = accepted_count
        self.rejected_count = rejected_count
        self.raw_dark_pixels = raw_dark_pixels
        self.cleaned_dark_pixels = cleaned_dark_pixels
        self.rejection_reasons = rejection_reasons
        self.mask_array = mask_array
        self.polygon_features = polygon_features or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_candidates_extracted": self.candidate_count,
            "accepted_candidates": self.accepted_count,
            "rejected_candidates": self.rejected_count,
            "raw_dark_pixels": self.raw_dark_pixels,
            "cleaned_dark_pixels": self.cleaned_dark_pixels,
            "rejection_reasons_breakdown": self.rejection_reasons,
            "metadata": self.metadata,
        }


class BaseSlickDetector(ABC):
    """
    Abstract Base Class for all SAR dark-spot and oil-slick candidate detectors.
    """

    @abstractmethod
    def get_detector_info(self) -> Dict[str, Any]:
        """Return detector identification, methodology, and capability metadata."""
        pass

    @abstractmethod
    def detect(
        self,
        sigma0_db: np.ndarray,
        valid_mask: np.ndarray,
        transform: Any,
        crs: str,
        case_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> DetectionOutput:
        """
        Execute candidate detection over calibrated SAR decibel backscatter.

        Args:
            sigma0_db: 2D numpy array of calibrated backscatter (dB).
            valid_mask: 2D boolean array where True indicates valid ocean pixels.
            transform: Affine geotransform.
            crs: Coordinate Reference System string.
            case_id: Canonical identifier of the case.
            config: Optional runtime detector hyperparameters.

        Returns:
            DetectionOutput containing candidate counts, geometries, and rejection reasons.
        """
        pass


class DeterministicThresholdDetector(BaseSlickDetector):
    """
    Operational Deterministic Multi-Mode SAR Backscatter & Local Contrast Detector.
    Wraps src.detection.detector.BaselineDarkSlickDetector.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config

    def get_detector_info(self) -> Dict[str, Any]:
        return {
            "detector_id": "DETERMINISTIC_DUAL_PARAMETER_CFAR",
            "name": "Deterministic Multi-Mode SAR Backscatter & Local Contrast Detector",
            "type": "CLASSICAL_DETERMINISTIC",
            "status": "OPERATIONAL_DEFAULT",
            "polarization": "VV",
            "thresholding_mode": "adaptive",
            "default_parameters": {
                "global_threshold_db": -23.0,
                "contrast_threshold_db": 3.5,
                "local_window_size_pixels": 101,
                "morphological_cleanup": True,
                "min_connected_pixels": 50,
                "lookalike_filtering_rules": {
                    "min_area_km2": 0.05,
                    "max_area_km2": 50.0,
                    "min_contrast_db": 2.5,
                    "max_aspect_ratio": 30.0,
                    "swath_edge_buffer_pixels": 10,
                },
            },
            "scientific_rationale": (
                "Dual-parameter adaptive thresholding identifies anomalous radar backscatter dampening "
                "relative to the local ambient ocean background. Candidate connected components are "
                "subsequently filtered against spatial look-alike criteria (low wind speed, internal waves, "
                "swath boundary artifacts) using transparent geometric rules."
            ),
        }

    def detect(
        self,
        sigma0_db: np.ndarray,
        valid_mask: np.ndarray,
        transform: Any,
        crs: str,
        case_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> DetectionOutput:
        from src.detection.detector import BaselineDarkSlickDetector

        detector = BaselineDarkSlickDetector(config=config or self.config, case_id=case_id)
        res = detector.run()
        counts = res.get("detection_counts", {})
        reasons = counts.get("rejection_reasons_breakdown", {})

        return DetectionOutput(
            candidate_count=counts.get("total_candidates_extracted", 0),
            accepted_count=counts.get("accepted_candidates", 0),
            rejected_count=counts.get("rejected_candidates", 0),
            raw_dark_pixels=counts.get("raw_dark_pixels", 0),
            cleaned_dark_pixels=counts.get("cleaned_dark_pixels", 0),
            rejection_reasons=reasons,
            metadata={
                "algorithm": res.get("algorithm"),
                "elapsed_seconds": res.get("elapsed_seconds"),
                "output_files": res.get("output_files", {}),
            },
        )


class MLDetectorInterface(BaseSlickDetector):
    """
    Formal interface stub for future Machine Learning / Deep Learning slick segmentation models.

    SCIENTIFIC INTEGRITY NOTICE:
    No imaginary weights or fabricated inference predictions are executed in this phase.
    DeterministicThresholdDetector remains the active operational detector.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    def get_detector_info(self) -> Dict[str, Any]:
        return {
            "detector_id": "FUTURE_ML_DEEP_SEGMENTATION_STUB",
            "name": "Deep Convolutional / Transformer SAR Slick Segmentation Interface",
            "type": "DEEP_LEARNING_FUTURE_EXTENSION",
            "status": "INTERFACE_PREPARED_MODEL_UNCONNECTED",
            "polarization": "VV (with optional VH co-input)",
            "required_runtime": "PyTorch / ONNX Runtime (GPU recommended)",
            "model_path": self.model_path,
            "scientific_rationale": (
                "Decoupled detector interface designed to accept trained semantic segmentation architectures "
                "(e.g., U-Net with ResNet/EfficientNet backbone, DeepLabV3+, or SegFormer). When trained weights "
                "are mounted, outputs map directly to DetectionOutput polygon features and feed the downstream "
                "hydrodynamic attribution pipeline without altering case logic."
            ),
        }

    def detect(
        self,
        sigma0_db: np.ndarray,
        valid_mask: np.ndarray,
        transform: Any,
        crs: str,
        case_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> DetectionOutput:
        raise NotImplementedError(
            "MLDetectorInterface is a prepared integration point for future model inference. "
            "No trained neural network weights are connected in this prototype. "
            "Execute DeterministicThresholdDetector for verified operational dark-spot detection."
        )


def get_registered_detector(detector_type: str = "deterministic") -> BaseSlickDetector:
    """Factory function for detector retrieval."""
    if detector_type.lower() in ["deterministic", "default", "classical"]:
        return DeterministicThresholdDetector()
    elif detector_type.lower() in ["ml", "future_ml", "deep_learning"]:
        return MLDetectorInterface()
    else:
        raise ValueError(f"Unknown detector type '{detector_type}'. Valid options: 'deterministic', 'ml'")
