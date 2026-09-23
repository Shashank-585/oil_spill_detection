"""
Candidate Slick Heuristic Confidence Scoring Module.

Calculates a transparent, rule-based heuristic score [0.0, 1.0] for candidate
oil slicks based on:
1. Radiometric contrast relative to local ocean background
2. Absolute backscatter darkness below clutter median
3. Geometric elongation / aspect ratio plausibility under ocean current/wind shear
4. Spatial area plausibility

SCIENTIFIC GUARDRAIL:
This score is a heuristic candidate confidence ranking, NOT a calibrated
probabilistic classifier or machine-learning probability.
"""

from typing import Dict, Any
import numpy as np


def compute_candidate_score(candidate: Dict[str, Any]) -> float:
    """
    Calculate a transparent heuristic confidence score [0.0, 1.0] for a candidate slick.

    Args:
        candidate: Dictionary containing extracted geometric and radiometric features.

    Returns:
        Float score between 0.0 and 1.0.
    """
    mean_db = candidate.get("mean_sigma0_db", -20.0)
    mean_contrast = candidate.get("mean_contrast_db", 0.0)
    area_km2 = candidate.get("area_km2", 0.0)
    aspect_ratio = candidate.get("aspect_ratio", 1.0)
    
    # 1. Contrast Score (0.0 to 1.0)
    # Typical slick damping in C-band VV is 3 to 8 dB
    # Contrast < 2.0 dB is marginal; >= 6.0 dB is prominent
    s_contrast = float(np.clip((mean_contrast - 2.0) / 5.0, 0.0, 1.0))
    
    # 2. Darkness Score (0.0 to 1.0)
    # C-band VV clean ocean clutter median is ~ -19.5 dB
    # Mean backscatter of -22 dB gets ~0.25; -28 dB gets ~0.85
    s_darkness = float(np.clip((-19.5 - mean_db) / 10.0, 0.0, 1.0))
    
    # 3. Shape / Elongation Score (0.0 to 1.0)
    # Physical oil slicks are naturally stretched into windrows or filaments
    # Aspect ratio 1.0 (circular) is less characteristic; 2.0 to 10.0 is typical
    # Extreme aspect ratio > 25 indicates potential swath edge artifact
    if aspect_ratio <= 1.0:
        s_shape = 0.2
    elif aspect_ratio <= 8.0:
        s_shape = float(np.clip(0.2 + 0.8 * ((aspect_ratio - 1.0) / 7.0), 0.2, 1.0))
    elif aspect_ratio <= 20.0:
        s_shape = 0.95
    else:
        # Penalty for extreme razor-thin line artifacts
        s_shape = float(np.clip(1.0 - ((aspect_ratio - 20.0) / 15.0), 0.2, 0.95))
        
    # 4. Size Plausibility Score (0.0 to 1.0)
    # Target range for single slick patches: 0.1 km^2 to 15 km^2
    if area_km2 < 0.05:
        s_size = 0.2
    elif area_km2 <= 0.5:
        s_size = float(0.2 + 0.7 * (area_km2 / 0.5))
    elif area_km2 <= 10.0:
        s_size = 0.95
    elif area_km2 <= 30.0:
        s_size = float(np.clip(0.95 - 0.5 * ((area_km2 - 10.0) / 20.0), 0.3, 0.95))
    else:
        # Massive basin-scale dark areas (> 30 km^2) are frequently low-wind calm water
        s_size = 0.25
        
    # Weighted composite heuristic score
    # Primary weights on contrast and darkness (radiometric damping signature)
    score = (
        0.40 * s_contrast +
        0.30 * s_darkness +
        0.15 * s_shape +
        0.15 * s_size
    )
    
    return round(float(np.clip(score, 0.0, 1.0)), 3)
