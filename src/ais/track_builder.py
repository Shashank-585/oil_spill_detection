"""
AIS Track Reconstruction and Geodesic Temporal Interpolation.

Constructs continuous vessel trajectories from normalized AIS pings,
detects temporal gaps, segments tracks when gaps exceed allowable limits,
and computes robust position interpolation at arbitrary target timestamps.
"""

from datetime import datetime, timezone, timedelta
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.common.logging import get_logger

logger = get_logger(__name__)


def interpolate_cog_deg(cog1: float, cog2: float, tau: float) -> float:
    """
    Interpolate circular course-over-ground angles taking the shortest arc.
    """
    diff = (cog2 - cog1 + 180.0) % 360.0 - 180.0
    interp = (cog1 + tau * diff) % 360.0
    return float(interp)


class AISTrackBuilder:
    """
    Builds structured trajectories from normalized AIS data and provides
    defensible temporal position interpolation without bridging excessive gaps.
    """

    def __init__(
        self,
        df_normalized: pd.DataFrame,
        max_interpolation_gap_seconds: float = 3600.0,
        min_pings_per_track: int = 3,
    ):
        self.max_gap_seconds = float(max_interpolation_gap_seconds)
        self.min_pings = int(min_pings_per_track)
        self._build_tracks(df_normalized)

    def _build_tracks(self, df: pd.DataFrame) -> None:
        """
        Group by MMSI, sort chronologically, segment by temporal gaps,
        and index for fast temporal lookups.
        """
        self.vessel_tracks: Dict[int, pd.DataFrame] = {}
        self.vessel_metadata: Dict[int, Dict[str, Any]] = {}
        self.vessel_times: Dict[int, np.ndarray] = {}  # Array of POSIX timestamps

        grouped = df.groupby("mmsi")
        logger.info(f"Building tracks for {len(grouped)} unique MMSIs (max gap = {self.max_gap_seconds:.0f}s)...")

        for mmsi, group in grouped:
            track = group.sort_values(by="timestamp_utc").reset_index(drop=True).copy()
            n_pings = len(track)
            if n_pings < self.min_pings:
                continue

            # Compute consecutive time differences in seconds
            times = track["timestamp_utc"].values.astype("datetime64[s]").astype(np.int64)
            dt_seconds = np.diff(times, prepend=times[0])

            # Assign segment IDs where dt > max_gap_seconds
            gap_mask = dt_seconds > self.max_gap_seconds
            segment_ids = np.cumsum(gap_mask)
            track["segment_id"] = segment_ids
            track["gap_before_s"] = dt_seconds

            # Extract representative metadata (mode or last non-null)
            v_name = track["vessel_name"].dropna().iloc[-1] if ("vessel_name" in track.columns and track["vessel_name"].dropna().any()) else None
            v_type = track["vessel_type"].dropna().iloc[-1] if ("vessel_type" in track.columns and track["vessel_type"].dropna().any()) else None
            imo = track["imo"].dropna().iloc[-1] if ("imo" in track.columns and track["imo"].dropna().any()) else None
            callsign = track["callsign"].dropna().iloc[-1] if ("callsign" in track.columns and track["callsign"].dropna().any()) else None

            start_t = track["timestamp_utc"].iloc[0]
            end_t = track["timestamp_utc"].iloc[-1]
            span_h = (end_t - start_t).total_seconds() / 3600.0
            avg_int = float(np.mean(dt_seconds[1:])) if len(dt_seconds) > 1 else 0.0
            max_g = float(np.max(dt_seconds)) if len(dt_seconds) > 1 else 0.0

            self.vessel_tracks[mmsi] = track
            self.vessel_times[mmsi] = times
            self.vessel_metadata[mmsi] = {
                "mmsi": int(mmsi),
                "vessel_name": v_name,
                "vessel_type": v_type,
                "imo": imo,
                "callsign": callsign,
                "ping_count": n_pings,
                "segment_count": int(segment_ids[-1] + 1),
                "start_utc": start_t.isoformat(),
                "end_utc": end_t.isoformat(),
                "time_span_hours": round(span_h, 2),
                "avg_interval_seconds": round(avg_int, 1),
                "max_gap_seconds": round(max_g, 1),
                "usable_track": True,
            }

        logger.info(f"Retained {len(self.vessel_tracks)} usable vessel tracks with >= {self.min_pings} pings.")

    def get_vessel_position_at_time(
        self,
        mmsi: int,
        target_time: datetime,
        near_boundary_tolerance_seconds: float = 300.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Determine defensible vessel position at target_time.

        Parameters
        ----------
        mmsi : int
            Vessel MMSI.
        target_time : datetime
            Target UTC datetime.
        near_boundary_tolerance_seconds : float
            Maximum allowable gap if target_time is just before first ping
            or just after last ping (default 300s = 5 min).

        Returns
        -------
        Optional[Dict[str, Any]]
            Interpolated vessel state dict, or None if position is unknown/unreliable.
        """
        if mmsi not in self.vessel_tracks:
            return None

        track = self.vessel_tracks[mmsi]
        times = self.vessel_times[mmsi]
        t_target = int(target_time.replace(tzinfo=timezone.utc).timestamp())

        # Check boundary condition (before start or after end)
        t_start = times[0]
        t_end = times[-1]

        if t_target < t_start:
            delta = t_start - t_target
            if delta <= near_boundary_tolerance_seconds:
                p0 = track.iloc[0]
                return {
                    "mmsi": mmsi,
                    "latitude": float(p0["latitude"]),
                    "longitude": float(p0["longitude"]),
                    "sog_knots": float(p0["sog_knots"]),
                    "cog_deg": float(p0["cog_deg"]),
                    "timestamp_utc": target_time.isoformat(),
                    "quality": "near_boundary_first_ping",
                    "gap_seconds": float(delta),
                    "interpolated": False,
                }
            return None

        if t_target > t_end:
            delta = t_target - t_end
            if delta <= near_boundary_tolerance_seconds:
                p_last = track.iloc[-1]
                return {
                    "mmsi": mmsi,
                    "latitude": float(p_last["latitude"]),
                    "longitude": float(p_last["longitude"]),
                    "sog_knots": float(p_last["sog_knots"]),
                    "cog_deg": float(p_last["cog_deg"]),
                    "timestamp_utc": target_time.isoformat(),
                    "quality": "near_boundary_last_ping",
                    "gap_seconds": float(delta),
                    "interpolated": False,
                }
            return None

        # Binary search for bracket
        idx = np.searchsorted(times, t_target)
        if idx == 0:
            p0 = track.iloc[0]
            return {
                "mmsi": mmsi,
                "latitude": float(p0["latitude"]),
                "longitude": float(p0["longitude"]),
                "sog_knots": float(p0["sog_knots"]),
                "cog_deg": float(p0["cog_deg"]),
                "timestamp_utc": target_time.isoformat(),
                "quality": "exact_observation",
                "gap_seconds": 0.0,
                "interpolated": False,
            }

        idx_prev = idx - 1
        idx_next = idx

        p_prev = track.iloc[idx_prev]
        p_next = track.iloc[idx_next]

        # Exact match check
        if times[idx_next] == t_target:
            return {
                "mmsi": mmsi,
                "latitude": float(p_next["latitude"]),
                "longitude": float(p_next["longitude"]),
                "sog_knots": float(p_next["sog_knots"]),
                "cog_deg": float(p_next["cog_deg"]),
                "timestamp_utc": target_time.isoformat(),
                "quality": "exact_observation",
                "gap_seconds": 0.0,
                "interpolated": False,
            }

        # Check if bracket belongs to the SAME continuous segment
        gap = times[idx_next] - times[idx_prev]
        if p_prev["segment_id"] != p_next["segment_id"] or gap > self.max_gap_seconds:
            # Observations span an excessive gap; position is unknown
            return None

        # Defensible linear interpolation
        tau = (t_target - times[idx_prev]) / float(gap)
        lat = float(p_prev["latitude"] + tau * (p_next["latitude"] - p_prev["latitude"]))
        lon = float(p_prev["longitude"] + tau * (p_next["longitude"] - p_prev["longitude"]))
        sog = float(p_prev["sog_knots"] + tau * (p_next["sog_knots"] - p_prev["sog_knots"]))
        cog = interpolate_cog_deg(float(p_prev["cog_deg"]), float(p_next["cog_deg"]), tau)

        return {
            "mmsi": mmsi,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "sog_knots": round(sog, 2),
            "cog_deg": round(cog, 1),
            "timestamp_utc": target_time.isoformat(),
            "quality": "bracketed_interpolation",
            "gap_seconds": float(gap),
            "interpolated": True,
        }

    def get_all_vessel_positions_at_time(
        self,
        target_time: datetime,
        near_boundary_tolerance_seconds: float = 300.0,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate positions of all active vessels at target_time.
        """
        positions = []
        for mmsi in self.vessel_tracks:
            pos = self.get_vessel_position_at_time(
                mmsi, target_time, near_boundary_tolerance_seconds=near_boundary_tolerance_seconds
            )
            if pos is not None:
                meta = self.vessel_metadata[mmsi]
                pos.update({
                    "vessel_name": meta["vessel_name"],
                    "vessel_type": meta["vessel_type"],
                    "imo": meta["imo"],
                    "callsign": meta["callsign"],
                })
                positions.append(pos)
        return positions
