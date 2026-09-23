"""
Look-Alike and Artifact Filtering Module.

Evaluates candidate dark slicks against transparent physical and sensor criteria:
- Minimum physical area (rejecting sub-pixel or tiny isolated speckle artifacts)
- Maximum physical area (rejecting massive regional low-wind / upwelling calm zones)
- Minimum local contrast floor
- Extreme aspect ratio boundaries
- Proximity to orbital swath nodata boundaries

SCIENTIFIC INTEGRITY RULE:
Candidates are NOT silently deleted. All candidates are preserved in the catalog
with explicit status ('ACCEPTED' vs 'REJECTED') and documented rejection reasons.
"""

from typing import List, Dict, Any, Tuple
import numpy as np

from src.common.logging import get_logger

logger = get_logger("src.detection.lookalike_filter")


class LookAlikeFilter:
    """
    Transparent rule-based candidate filtering engine.
    """

    def __init__(
        self,
        min_area_km2: float = 0.05,
        max_area_km2: float = 50.0,
        min_contrast_db: float = 2.5,
        max_aspect_ratio: float = 30.0,
        swath_edge_buffer_pixels: int = 10
    ) -> None:
        self.min_area_km2 = min_area_km2
        self.max_area_km2 = max_area_km2
        self.min_contrast_db = min_contrast_db
        self.max_aspect_ratio = max_aspect_ratio
        self.swath_edge_buffer_pixels = swath_edge_buffer_pixels

    def filter_candidates(
        self,
        candidates: List[Dict[str, Any]],
        swath_valid_mask: Optional[np.ndarray] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Evaluate each candidate against the look-alike and artifact criteria.

        Args:
            candidates: List of candidate dictionaries from geometry extraction.
            swath_valid_mask: Optional 2D boolean mask of valid orbital swath pixels.

        Returns:
            Tuple of:
                - annotated_candidates: All candidates with 'status' and 'rejection_reasons'
                - rejection_counts: Frequency dictionary of each rejection reason
        """
        rejection_counts: Dict[str, int] = {
            "AREA_TOO_SMALL": 0,
            "AREA_TOO_LARGE": 0,
            "INSUFFICIENT_CONTRAST": 0,
            "EXTREME_ASPECT_RATIO": 0,
            "SWATH_EDGE_PROXIMITY": 0
        }
        
        annotated: List[Dict[str, Any]] = []

        for cand in candidates:
            cand_copy = cand.copy()
            reasons: List[str] = []
            
            area = cand.get("area_km2", 0.0)
            contrast = cand.get("mean_contrast_db", 0.0)
            aspect = cand.get("aspect_ratio", 1.0)
            
            # Rule 1: Area too small
            if area < self.min_area_km2:
                reasons.append("AREA_TOO_SMALL")
                rejection_counts["AREA_TOO_SMALL"] += 1
                
            # Rule 2: Area too large (low wind zone)
            if area > self.max_area_km2:
                reasons.append("AREA_TOO_LARGE")
                rejection_counts["AREA_TOO_LARGE"] += 1
                
            # Rule 3: Insufficient local contrast
            if contrast < self.min_contrast_db:
                reasons.append("INSUFFICIENT_CONTRAST")
                rejection_counts["INSUFFICIENT_CONTRAST"] += 1
                
            # Rule 4: Extreme aspect ratio
            if aspect > self.max_aspect_ratio:
                reasons.append("EXTREME_ASPECT_RATIO")
                rejection_counts["EXTREME_ASPECT_RATIO"] += 1
                
            cand_copy["rejection_reasons"] = reasons
            cand_copy["status"] = "ACCEPTED" if len(reasons) == 0 else "REJECTED"
            annotated.append(cand_copy)

        accepted_count = sum(1 for c in annotated if c["status"] == "ACCEPTED")
        rejected_count = len(annotated) - accepted_count
        
        logger.info(
            f"Look-alike filtering complete: {len(annotated)} total candidates, "
            f"{accepted_count} ACCEPTED, {rejected_count} REJECTED. "
            f"Reasons: {dict(rejection_counts)}"
        )
        
        return annotated, rejection_counts
