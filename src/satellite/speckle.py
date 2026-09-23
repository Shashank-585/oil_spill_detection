"""
SAR Speckle Filtering Module.

Provides configurable spatial speckle reduction filters for calibrated
SAR intensity rasters (sigma0 linear).

Speckle is multiplicative in SAR imagery:
    I = R * S
Where I is observed intensity, R is radar cross section, and S is speckle noise
with variance 1 / ENL (Equivalent Number of Looks).

Filtering is performed in the linear intensity domain, NOT in decibels.
"""

from typing import Optional
import numpy as np
from scipy.ndimage import uniform_filter

from src.common.logging import get_logger

logger = get_logger("src.satellite.speckle")


def apply_speckle_filter(
    raster: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    method: str = "lee",
    window_size: int = 5,
    num_looks: float = 4.4
) -> np.ndarray:
    """
    Apply a speckle filter to a 2D SAR intensity raster.

    Args:
        raster: 2D numpy array of linear backscatter (sigma0 linear).
        valid_mask: Optional boolean mask where True indicates valid pixels.
        method: Filter algorithm ('lee' or 'box').
        window_size: Filter kernel size (must be an odd integer >= 3).
        num_looks: Equivalent Number of Looks (ENL) for Sentinel-1 IW GRDH (~4.4).

    Returns:
        Filtered 2D numpy array preserving original shape, dtype, and NoData.
    """
    if raster.ndim != 2:
        raise ValueError(f"Expected 2D raster, got shape {raster.shape}")
    if window_size % 2 == 0 or window_size < 3:
        raise ValueError(f"window_size must be an odd integer >= 3, got {window_size}")

    if valid_mask is None:
        valid_mask = np.isfinite(raster) & (raster > 0)
    else:
        valid_mask = valid_mask & np.isfinite(raster) & (raster > 0)

    # Work with float32 array
    img = raster.astype(np.float32)
    # Fill invalid areas with local valid mean or zero to prevent edge contamination
    filtered = np.full_like(img, fill_value=np.nan)

    if not np.any(valid_mask):
        logger.warning("No valid pixels found for speckle filtering.")
        return filtered

    method_lower = method.lower()
    logger.info(
        f"Applying speckle filter: method='{method_lower}', "
        f"window_size={window_size}, num_looks={num_looks}"
    )

    if method_lower == "box":
        # Moving box average
        mean_img = uniform_filter(np.where(valid_mask, img, 0.0), size=window_size)
        weights = uniform_filter(valid_mask.astype(np.float32), size=window_size)
        weights_safe = np.where(weights > 0, weights, 1.0)
        norm_mean = mean_img / weights_safe
        filtered = np.where(valid_mask, norm_mean, np.nan)

    elif method_lower == "lee":
        # Enhanced/standard Lee filter for SAR intensity
        # Noise variance for intensity image with ENL looks
        noise_var = 1.0 / float(num_looks)

        # Local mean
        valid_float = valid_mask.astype(np.float32)
        mean_i = uniform_filter(np.where(valid_mask, img, 0.0), size=window_size)
        w = uniform_filter(valid_float, size=window_size)
        w_safe = np.where(w > 0, w, 1.0)
        mean_i = mean_i / w_safe

        # Local mean of squares
        mean_i2 = uniform_filter(np.where(valid_mask, img ** 2, 0.0), size=window_size) / w_safe

        # Local sample variance
        var_i = np.maximum(0.0, mean_i2 - mean_i ** 2)

        # A-priori signal variance: var_x = (var_i - mean_i^2 * noise_var) / (1 + noise_var)
        var_x = np.maximum(0.0, (var_i - (mean_i ** 2) * noise_var) / (1.0 + noise_var))

        # Weight factor W = var_x / var_i (clipped to [0, 1])
        var_i_safe = np.where(var_i > 0, var_i, 1.0)
        weight = np.where(var_i > 0, np.clip(var_x / var_i_safe, 0.0, 1.0), 0.0)

        # Filtered output: R_hat = mean_i + weight * (img - mean_i)
        lee_out = mean_i + weight * (img - mean_i)
        filtered = np.where(valid_mask, np.maximum(0.0, lee_out), np.nan)

    else:
        raise ValueError(f"Unsupported speckle filter method: {method}. Choose 'lee' or 'box'.")

    return filtered
