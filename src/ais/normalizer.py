"""
AIS Data Normalization and Quality Validation.

Standardizes raw/filtered AIS records into canonical UTC-aware schemas,
validates geographic coordinates, checks speed sanity, and removes duplicates
while preserving an explicit audit trail of all rejected records and reason codes.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.common.logging import get_logger
from src.common.paths import resolve_path
from src.common.time_utils import parse_utc_timestamp

logger = get_logger(__name__)

# Canonical column mapping from NOAA MarineCadastre / raw AIS columns
NOAA_COLUMN_MAP = {
    "MMSI": "mmsi",
    "BaseDateTime": "raw_datetime",
    "timestamp_utc": "timestamp_str",
    "LAT": "latitude",
    "LON": "longitude",
    "SOG": "sog_knots",
    "COG": "cog_deg",
    "Heading": "heading_deg",
    "VesselName": "vessel_name",
    "IMO": "imo",
    "CallSign": "callsign",
    "VesselType": "vessel_type",
    "Length": "length_m",
    "Width": "width_m",
    "Draft": "draft_m",
    "Status": "nav_status",
}


class AISNormalizer:
    """
    Validates and normalizes AIS data into clean, chronological vessel trajectories.
    """

    def __init__(
        self,
        max_speed_knots: float = 50.0,
        lat_range: Tuple[float, float] = (-90.0, 90.0),
        lon_range: Tuple[float, float] = (-180.0, 180.0),
    ):
        self.max_speed_knots = float(max_speed_knots)
        self.lat_min, self.lat_max = lat_range
        self.lon_min, self.lon_max = lon_range

    def normalize(
        self,
        data: Union[pd.DataFrame, str, Path],
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Normalize and validate AIS records.

        Parameters
        ----------
        data : Union[pd.DataFrame, str, Path]
            Raw AIS DataFrame or path to CSV file.

        Returns
        -------
        Tuple[pd.DataFrame, Dict[str, Any]]
            Clean normalized DataFrame and audit report dictionary.
        """
        if isinstance(data, (str, Path)):
            file_path = resolve_path(data)
            if not file_path.exists():
                raise FileNotFoundError(f"AIS file not found: {file_path}")
            logger.info(f"Loading AIS data from {file_path}...")
            df = pd.read_csv(file_path, low_memory=False)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise TypeError(f"Expected DataFrame, str, or Path, got {type(data)}")

        total_input_records = len(df)
        initial_mmsi_count = df["MMSI"].nunique() if "MMSI" in df.columns else (df["mmsi"].nunique() if "mmsi" in df.columns else 0)

        # Standardize column names
        rename_dict = {}
        for col in df.columns:
            if col in NOAA_COLUMN_MAP:
                rename_dict[col] = NOAA_COLUMN_MAP[col]
            elif col.lower() in [v for v in NOAA_COLUMN_MAP.values()]:
                rename_dict[col] = col.lower()
        df = df.rename(columns=rename_dict)

        required_cols = {"mmsi", "latitude", "longitude"}
        missing_required = required_cols - set(df.columns)
        if missing_required:
            raise ValueError(f"AIS data missing mandatory columns: {missing_required}")

        rejection_counts: Dict[str, int] = {
            "INVALID_MMSI": 0,
            "INVALID_COORDINATES": 0,
            "INVALID_TIMESTAMP": 0,
            "SPEED_ANOMALY": 0,
            "DUPLICATE_RECORD": 0,
        }

        # 1. MMSI validation
        mmsi_numeric = pd.to_numeric(df["mmsi"], errors="coerce")
        valid_mmsi_mask = mmsi_numeric.notna() & (mmsi_numeric > 0)
        rejection_counts["INVALID_MMSI"] += int((~valid_mmsi_mask).sum())
        df = df[valid_mmsi_mask].copy()
        df["mmsi"] = mmsi_numeric[valid_mmsi_mask].astype(np.int64)

        # 2. Coordinates validation
        lat_numeric = pd.to_numeric(df["latitude"], errors="coerce")
        lon_numeric = pd.to_numeric(df["longitude"], errors="coerce")
        valid_coords_mask = (
            lat_numeric.notna() & lon_numeric.notna() &
            (lat_numeric >= self.lat_min) & (lat_numeric <= self.lat_max) &
            (lon_numeric >= self.lon_min) & (lon_numeric <= self.lon_max)
        )
        rejection_counts["INVALID_COORDINATES"] += int((~valid_coords_mask).sum())
        df = df[valid_coords_mask].copy()
        df["latitude"] = lat_numeric[valid_coords_mask].astype(np.float64)
        df["longitude"] = lon_numeric[valid_coords_mask].astype(np.float64)

        # 3. Timestamp parsing & validation
        time_series = None
        if "timestamp_str" in df.columns:
            time_series = pd.to_datetime(df["timestamp_str"], utc=True, errors="coerce")
        elif "raw_datetime" in df.columns:
            time_series = pd.to_datetime(df["raw_datetime"], utc=True, errors="coerce")
        elif "timestamp" in df.columns:
            time_series = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        else:
            raise ValueError("No timestamp column found in AIS data.")

        valid_time_mask = time_series.notna()
        rejection_counts["INVALID_TIMESTAMP"] += int((~valid_time_mask).sum())
        df = df[valid_time_mask].copy()
        df["timestamp_utc"] = time_series[valid_time_mask]

        # 4. Speed sanity check
        if "sog_knots" in df.columns:
            sog_numeric = pd.to_numeric(df["sog_knots"], errors="coerce").fillna(0.0)
            valid_speed_mask = (sog_numeric >= 0.0) & (sog_numeric <= self.max_speed_knots)
            rejection_counts["SPEED_ANOMALY"] += int((~valid_speed_mask).sum())
            df = df[valid_speed_mask].copy()
            df["sog_knots"] = sog_numeric[valid_speed_mask].astype(np.float64)
        else:
            df["sog_knots"] = 0.0

        # Course / Heading
        if "cog_deg" in df.columns:
            df["cog_deg"] = pd.to_numeric(df["cog_deg"], errors="coerce").fillna(0.0)
        else:
            df["cog_deg"] = 0.0

        if "heading_deg" in df.columns:
            df["heading_deg"] = pd.to_numeric(df["heading_deg"], errors="coerce")
        else:
            df["heading_deg"] = np.nan

        # Clean string / identifier columns
        for str_col in ["vessel_name", "imo", "callsign", "vessel_type"]:
            if str_col in df.columns:
                df[str_col] = df[str_col].astype(str).str.strip().replace({"nan": None, "None": None, "": None})
            else:
                df[str_col] = None

        # 5. Deduplication: exact duplicate (mmsi, timestamp_utc)
        dup_mask = df.duplicated(subset=["mmsi", "timestamp_utc"], keep="first")
        rejection_counts["DUPLICATE_RECORD"] += int(dup_mask.sum())
        df = df[~dup_mask].copy()

        # Sort chronologically by MMSI and timestamp
        df = df.sort_values(by=["mmsi", "timestamp_utc"]).reset_index(drop=True)

        final_records = len(df)
        final_mmsi_count = df["mmsi"].nunique()
        total_rejected = sum(rejection_counts.values())

        report = {
            "total_input_records": total_input_records,
            "final_valid_records": final_records,
            "total_rejected_records": total_rejected,
            "rejection_breakdown": rejection_counts,
            "initial_unique_vessels": initial_mmsi_count,
            "final_unique_vessels": final_mmsi_count,
            "time_range": {
                "start_utc": df["timestamp_utc"].min().isoformat() if not df.empty else None,
                "end_utc": df["timestamp_utc"].max().isoformat() if not df.empty else None,
            },
        }

        logger.info(
            f"AIS Normalization complete: {final_records:,} valid records ({final_mmsi_count} vessels) "
            f"from {total_input_records:,} input records. Rejected {total_rejected:,} records."
        )

        return df, report
