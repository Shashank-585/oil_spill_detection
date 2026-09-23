"""
Environmental forcing data loader and spatio-temporal interpolator.

Provides 4D spatio-temporal interpolation of:
1. Ocean surface currents (HYCOM NetCDF: water_u, water_v in m/s)
2. Sea-surface winds (ERA5 10m wind: wind_u_10m_mps, wind_v_10m_mps in m/s)

Strictly enforces spatial and temporal boundary validation to prevent unphysical extrapolation.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import math
import numpy as np
import pandas as pd
import scipy.io

from src.common.logging import get_logger
from src.common.paths import resolve_path
from src.common.time_utils import parse_utc_timestamp

logger = get_logger(__name__)


class EnvironmentalForcingInterpolator:
    """
    Interpolates ocean current and wind vectors across space (lat, lon)
    and time (UTC datetime).
    """

    def __init__(
        self,
        hycom_netcdf_path: Union[str, Path],
        era5_wind_csv_path: Union[str, Path],
        boundary_buffer_deg: float = 0.15,
    ):
        self.hycom_path = resolve_path(hycom_netcdf_path)
        self.era5_path = resolve_path(era5_wind_csv_path)
        self.boundary_buffer_deg = float(boundary_buffer_deg)

        if not self.hycom_path.exists():
            raise FileNotFoundError(f"HYCOM ocean currents file not found: {self.hycom_path}")
        if not self.era5_path.exists():
            raise FileNotFoundError(f"ERA5 wind file not found: {self.era5_path}")

        self._load_hycom()
        self._load_era5()

    def _load_hycom(self) -> None:
        """Load and parse HYCOM NetCDF file using scipy.io.netcdf."""
        nc = scipy.io.netcdf_file(str(self.hycom_path), "r", mmap=False)
        try:
            # Time coordinate
            time_var = nc.variables["time"]
            raw_time = time_var[:].copy()
            # HYCOM time units are typically "hours since 2000-01-01 00:00:00"
            units_attr = getattr(time_var, "units", b"").decode("utf-8") if isinstance(getattr(time_var, "units", b""), bytes) else str(getattr(time_var, "units", ""))
            
            base_time = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            if "since" in units_attr:
                parts = units_attr.split("since")
                time_unit = parts[0].strip().lower()
                base_str = parts[1].strip()
                try:
                    base_time = parse_utc_timestamp(base_str)
                except Exception:
                    pass

            self.current_times: List[datetime] = []
            for t_val in raw_time:
                self.current_times.append(base_time + timedelta(hours=float(t_val)))

            # Lat coordinate (sorted increasing)
            self.current_lats = np.array(nc.variables["lat"][:].copy(), dtype=np.float64)

            # Lon coordinate: convert [0, 360] to [-180, 180] if necessary
            raw_lons = np.array(nc.variables["lon"][:].copy(), dtype=np.float64)
            converted_lons = np.where(raw_lons > 180.0, raw_lons - 360.0, raw_lons)
            self.current_lons = converted_lons

            # Sort coordinates if not strictly monotonic increasing
            lat_sort_idx = np.argsort(self.current_lats)
            self.current_lats = self.current_lats[lat_sort_idx]

            lon_sort_idx = np.argsort(self.current_lons)
            self.current_lons = self.current_lons[lon_sort_idx]

            # Velocity variables (shape: time, depth, lat, lon)
            u_var = nc.variables["water_u"]
            v_var = nc.variables["water_v"]

            u_scale = float(getattr(u_var, "scale_factor", 1.0))
            v_scale = float(getattr(v_var, "scale_factor", 1.0))
            u_miss = getattr(u_var, "missing_value", -30000)
            v_miss = getattr(v_var, "missing_value", -30000)

            u_raw = u_var[:].copy().squeeze()  # (n_time, n_lat, n_lon)
            v_raw = v_var[:].copy().squeeze()

            # Apply coordinate re-ordering
            u_raw = u_raw[:, lat_sort_idx, :][:, :, lon_sort_idx]
            v_raw = v_raw[:, lat_sort_idx, :][:, :, lon_sort_idx]

            u_scaled = np.where((u_raw == u_miss) | (u_raw < -29000), np.nan, u_raw * u_scale)
            v_scaled = np.where((v_raw == v_miss) | (v_raw < -29000), np.nan, v_raw * v_scale)

            self.current_u = u_scaled
            self.current_v = v_scaled

            self.current_time_min = self.current_times[0]
            self.current_time_max = self.current_times[-1]

            logger.info(
                f"Loaded HYCOM ocean currents: {len(self.current_times)} steps "
                f"({self.current_time_min.isoformat()} to {self.current_time_max.isoformat()}), "
                f"lat [{self.current_lats[0]:.3f}, {self.current_lats[-1]:.3f}], "
                f"lon [{self.current_lons[0]:.3f}, {self.current_lons[-1]:.3f}]"
            )
        finally:
            nc.close()

    def _load_era5(self) -> None:
        """Load and parse ERA5 wind CSV file with station locations."""
        df = pd.read_csv(self.era5_path)
        required_cols = {"timestamp_utc", "latitude", "longitude", "wind_u_10m_mps", "wind_v_10m_mps"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"ERA5 CSV missing required columns: {required_cols - set(df.columns)}")

        df["dt"] = df["timestamp_utc"].apply(parse_utc_timestamp)
        self.wind_times = sorted(df["dt"].unique())
        self.wind_time_min = self.wind_times[0]
        self.wind_time_max = self.wind_times[-1]

        # Station coordinates (n_stations, 2) [lat, lon]
        station_df = df[["latitude", "longitude"]].drop_duplicates()
        self.wind_station_coords = station_df.values.astype(np.float64)
        n_stations = len(self.wind_station_coords)

        # Build (n_times, n_stations) arrays for u and v
        self.wind_station_u = np.zeros((len(self.wind_times), n_stations), dtype=np.float64)
        self.wind_station_v = np.zeros((len(self.wind_times), n_stations), dtype=np.float64)

        time_map = {t: i for i, t in enumerate(self.wind_times)}
        station_map = {(row[0], row[1]): i for i, row in enumerate(self.wind_station_coords)}

        for _, row in df.iterrows():
            t_idx = time_map[row["dt"]]
            s_idx = station_map[(row["latitude"], row["longitude"])]
            self.wind_station_u[t_idx, s_idx] = row["wind_u_10m_mps"]
            self.wind_station_v[t_idx, s_idx] = row["wind_v_10m_mps"]

        buf = max(self.boundary_buffer_deg, 0.35)
        self.wind_lat_min = float(np.min(self.wind_station_coords[:, 0])) - buf
        self.wind_lat_max = float(np.max(self.wind_station_coords[:, 0])) + buf
        self.wind_lon_min = float(np.min(self.wind_station_coords[:, 1])) - buf
        self.wind_lon_max = float(np.max(self.wind_station_coords[:, 1])) + buf

        logger.info(
            f"Loaded ERA5 winds: {len(self.wind_times)} steps across {n_stations} spatial stations "
            f"({self.wind_time_min.isoformat()} to {self.wind_time_max.isoformat()}), "
            f"lat [{self.wind_lat_min:.3f}, {self.wind_lat_max:.3f}], "
            f"lon [{self.wind_lon_min:.3f}, {self.wind_lon_max:.3f}]"
        )

    def _interp_hycom_3d(
        self,
        lat: float,
        lon: float,
        dt: datetime,
        data_3d: np.ndarray,
        var_name: str,
    ) -> float:
        """
        Bilinear spatial and linear temporal interpolation on HYCOM regular 3D grid (time, lat, lon).
        """
        if dt < self.current_times[0] or dt > self.current_times[-1]:
            raise ValueError(
                f"Requested time {dt.isoformat()} is out of {var_name} temporal bounds "
                f"[{self.current_times[0].isoformat()}, {self.current_times[-1].isoformat()}]"
            )

        buf = self.boundary_buffer_deg
        if lat < (self.current_lats[0] - buf) or lat > (self.current_lats[-1] + buf):
            raise ValueError(
                f"Requested latitude {lat:.5f} is out of {var_name} spatial bounds "
                f"[{self.current_lats[0] - buf:.5f}, {self.current_lats[-1] + buf:.5f}]"
            )
        if lon < (self.current_lons[0] - buf) or lon > (self.current_lons[-1] + buf):
            raise ValueError(
                f"Requested longitude {lon:.5f} is out of {var_name} spatial bounds "
                f"[{self.current_lons[0] - buf:.5f}, {self.current_lons[-1] + buf:.5f}]"
            )

        lat = min(max(lat, self.current_lats[0]), self.current_lats[-1])
        lon = min(max(lon, self.current_lons[0]), self.current_lons[-1])

        # Temporal bracket
        t_pos = np.searchsorted([t.timestamp() for t in self.current_times], dt.timestamp())
        if t_pos == 0:
            t0_idx = t1_idx = 0
            w_t = 0.0
        elif t_pos >= len(self.current_times):
            t0_idx = t1_idx = len(self.current_times) - 1
            w_t = 0.0
        else:
            t0_idx = t_pos - 1
            t1_idx = t_pos
            dt_total = (self.current_times[t1_idx] - self.current_times[t0_idx]).total_seconds()
            w_t = (dt - self.current_times[t0_idx]).total_seconds() / dt_total if dt_total > 0 else 0.0

        # Latitude bracket
        lat_pos = np.searchsorted(self.current_lats, lat)
        if lat_pos == 0:
            lat0_idx = lat1_idx = 0
            w_lat = 0.0
        elif lat_pos >= len(self.current_lats):
            lat0_idx = lat1_idx = len(self.current_lats) - 1
            w_lat = 0.0
        else:
            lat0_idx = lat_pos - 1
            lat1_idx = lat_pos
            d_lat = self.current_lats[lat1_idx] - self.current_lats[lat0_idx]
            w_lat = (lat - self.current_lats[lat0_idx]) / d_lat if d_lat > 0 else 0.0

        # Longitude bracket
        lon_pos = np.searchsorted(self.current_lons, lon)
        if lon_pos == 0:
            lon0_idx = lon1_idx = 0
            w_lon = 0.0
        elif lon_pos >= len(self.current_lons):
            lon0_idx = lon1_idx = len(self.current_lons) - 1
            w_lon = 0.0
        else:
            lon0_idx = lon_pos - 1
            lon1_idx = lon_pos
            d_lon = self.current_lons[lon1_idx] - self.current_lons[lon0_idx]
            w_lon = (lon - self.current_lons[lon0_idx]) / d_lon if d_lon > 0 else 0.0

        def interp_2d(t_slice: np.ndarray) -> float:
            c00 = t_slice[lat0_idx, lon0_idx]
            c01 = t_slice[lat0_idx, lon1_idx]
            c10 = t_slice[lat1_idx, lon0_idx]
            c11 = t_slice[lat1_idx, lon1_idx]

            corners = np.array([c00, c01, c10, c11])
            weights = np.array([
                (1.0 - w_lat) * (1.0 - w_lon),
                (1.0 - w_lat) * w_lon,
                w_lat * (1.0 - w_lon),
                w_lat * w_lon,
            ])

            valid = ~np.isnan(corners)
            if not np.any(valid):
                return 0.0
            if not np.all(valid):
                v_weights = weights[valid]
                w_sum = np.sum(v_weights)
                return float(np.sum(corners[valid] * (v_weights / w_sum))) if w_sum > 0 else float(np.nanmean(corners))
            return float(np.sum(corners * weights))

        val_t0 = interp_2d(data_3d[t0_idx])
        if t0_idx == t1_idx:
            return val_t0
        val_t1 = interp_2d(data_3d[t1_idx])
        return float((1.0 - w_t) * val_t0 + w_t * val_t1)

    def _interp_era5_wind(self, lat: float, lon: float, dt: datetime) -> Tuple[float, float]:
        """
        Interpolate wind vectors at (lat, lon, dt) using temporal linear interpolation
        and spatial Inverse Distance Weighting (IDW) across station points.
        """
        if dt < self.wind_time_min or dt > self.wind_time_max:
            raise ValueError(
                f"Requested time {dt.isoformat()} is out of ERA5 wind temporal bounds "
                f"[{self.wind_time_min.isoformat()}, {self.wind_time_max.isoformat()}]"
            )

        if lat < self.wind_lat_min or lat > self.wind_lat_max:
            raise ValueError(
                f"Requested latitude {lat:.5f} is out of ERA5 wind spatial bounds "
                f"[{self.wind_lat_min:.5f}, {self.wind_lat_max:.5f}]"
            )
        if lon < self.wind_lon_min or lon > self.wind_lon_max:
            raise ValueError(
                f"Requested longitude {lon:.5f} is out of ERA5 wind spatial bounds "
                f"[{self.wind_lon_min:.5f}, {self.wind_lon_max:.5f}]"
            )

        # Temporal linear interpolation at each station
        t_pos = np.searchsorted([t.timestamp() for t in self.wind_times], dt.timestamp())
        if t_pos == 0:
            station_u = self.wind_station_u[0]
            station_v = self.wind_station_v[0]
        elif t_pos >= len(self.wind_times):
            station_u = self.wind_station_u[-1]
            station_v = self.wind_station_v[-1]
        else:
            t0 = self.wind_times[t_pos - 1]
            t1 = self.wind_times[t_pos]
            dt_tot = (t1 - t0).total_seconds()
            wt = (dt - t0).total_seconds() / dt_tot if dt_tot > 0 else 0.0
            station_u = (1.0 - wt) * self.wind_station_u[t_pos - 1] + wt * self.wind_station_u[t_pos]
            station_v = (1.0 - wt) * self.wind_station_v[t_pos - 1] + wt * self.wind_station_v[t_pos]

        # Spatial IDW across stations
        diffs = self.wind_station_coords - np.array([lat, lon])
        dists = np.hypot(diffs[:, 0], diffs[:, 1])

        # Exact match check
        min_dist_idx = np.argmin(dists)
        if dists[min_dist_idx] < 1e-6:
            return float(station_u[min_dist_idx]), float(station_v[min_dist_idx])

        weights = 1.0 / (dists ** 2)
        weights /= np.sum(weights)

        u_interp = float(np.sum(station_u * weights))
        v_interp = float(np.sum(station_v * weights))
        return u_interp, v_interp

    def get_ocean_current(self, lat: float, lon: float, dt: datetime) -> Tuple[float, float]:
        """
        Get ocean surface current velocity (u, v) in m/s at (lat, lon, dt).
        """
        u = self._interp_hycom_3d(lat, lon, dt, self.current_u, "HYCOM current_u")
        v = self._interp_hycom_3d(lat, lon, dt, self.current_v, "HYCOM current_v")
        return float(u), float(v)

    def get_wind(self, lat: float, lon: float, dt: datetime) -> Tuple[float, float]:
        """
        Get 10m wind velocity (u, v) in m/s at (lat, lon, dt).
        """
        return self._interp_era5_wind(lat, lon, dt)

    def get_total_surface_velocity(
        self,
        lat: float,
        lon: float,
        dt: datetime,
        wind_drift_factor: float = 0.031,
        wind_deflection_angle_deg: float = 0.0,
        current_factor: float = 1.0,
    ) -> Tuple[float, float]:
        """
        Calculate combined oil drift surface velocity vector:
        V_oil = c * V_current + alpha * R(theta) * V_wind

        Returns (u_mps, v_mps).
        """
        u_curr, v_curr = self.get_ocean_current(lat, lon, dt)
        u_wind, v_wind = self.get_wind(lat, lon, dt)

        # Wind rotation by deflection angle theta (radians)
        theta = math.radians(wind_deflection_angle_deg)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        u_wind_rot = u_wind * cos_t - v_wind * sin_t
        v_wind_rot = u_wind * sin_t + v_wind * cos_t

        u_total = current_factor * u_curr + wind_drift_factor * u_wind_rot
        v_total = current_factor * v_curr + wind_drift_factor * v_wind_rot

        return float(u_total), float(v_total)
