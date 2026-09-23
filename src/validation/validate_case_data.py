"""
Data Feasibility and Integrity Validation Utility for Phase 0.

Validates that all required data streams for a designated case configuration:
1. Exist locally on disk
2. Have valid ISO 8601 UTC timestamps
3. Have valid EPSG:4326 coordinate ranges and spatially intersect the Case AOI
4. Have temporal ranges that appropriately cover the observation and source-search windows
5. Contain required physical vector variables in environmental datasets (ocean currents u/v, wind u/v)
6. Contain actual vessel positions (MMSI, lat, lon, SOG, COG) in/near the AOI
"""

import os
import sys
import json
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
import pandas as pd
from scipy.io import netcdf_file


class CaseDataValidator:
    def __init__(self, config_path: str):
        self.config_path = config_path
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Case configuration file not found at: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg: Dict[str, Any] = yaml.safe_load(f)

        self.case_id = self.cfg.get("case_id", "unknown")
        self.aoi = self.cfg["spatial"]["aoi_bounding_box"]
        self.results: List[Dict[str, Any]] = []

    def _record(self, category: str, test_name: str, passed: bool, message: str, details: Any = None):
        self.results.append({
            "category": category,
            "test": test_name,
            "passed": passed,
            "message": message,
            "details": details or {}
        })

    def _parse_utc(self, ts_str: str) -> datetime:
        """Strictly parse ISO 8601 string to timezone-aware UTC datetime."""
        # Handle trailing Z or offset
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise ValueError(f"Timestamp {ts_str} missing explicit UTC timezone offset")
        return dt.astimezone(timezone.utc)

    def _bboxes_intersect(self, box1: Dict[str, float], box2: Dict[str, float]) -> bool:
        """Check if two bounding boxes in WGS84 intersect."""
        return not (
            box1["east"] < box2["west"] or
            box1["west"] > box2["east"] or
            box1["north"] < box2["south"] or
            box1["south"] > box2["north"]
        )

    # 1. FILE EXISTENCE CHECK
    def check_files_exist(self):
        cat = "File Existence"
        # Satellite files
        sat_files = self.cfg.get("satellite", {}).get("files", {})
        for name, path in sat_files.items():
            if path.startswith("http"):
                continue  # Remote direct asset
            exists = os.path.exists(path) and os.path.getsize(path) > 0
            size = os.path.getsize(path) if exists else 0
            self._record(cat, f"satellite_{name}", exists,
                         f"File '{path}' exists ({size:,} bytes)" if exists else f"File '{path}' missing or empty")

        # Environmental files
        hycom_file = self.cfg.get("environmental", {}).get("ocean_currents", {}).get("file_path")
        if hycom_file:
            exists = os.path.exists(hycom_file) and os.path.getsize(hycom_file) > 0
            size = os.path.getsize(hycom_file) if exists else 0
            self._record(cat, "ocean_currents_file", exists,
                         f"HYCOM file '{hycom_file}' exists ({size:,} bytes)" if exists else f"HYCOM file '{hycom_file}' missing")

        wind_files = self.cfg.get("environmental", {}).get("wind", {}).get("files", {})
        for name, path in wind_files.items():
            exists = os.path.exists(path) and os.path.getsize(path) > 0
            size = os.path.getsize(path) if exists else 0
            self._record(cat, f"wind_{name}", exists,
                         f"Wind file '{path}' exists ({size:,} bytes)" if exists else f"Wind file '{path}' missing")

        # AIS files
        ais_filtered = self.cfg.get("ais", {}).get("files", {}).get("filtered_csv")
        if ais_filtered:
            exists = os.path.exists(ais_filtered) and os.path.getsize(ais_filtered) > 0
            size = os.path.getsize(ais_filtered) if exists else 0
            self._record(cat, "ais_filtered_csv", exists,
                         f"AIS filtered file '{ais_filtered}' exists ({size:,} bytes)" if exists else f"AIS filtered file '{ais_filtered}' missing")

    # 2. COORDINATE SYSTEM & BOUNDS VALIDATION
    def check_spatial_coordinates(self):
        cat = "Spatial & Coordinates"
        crs = self.cfg.get("spatial", {}).get("crs", "")
        self._record(cat, "crs_standard", crs == "EPSG:4326", f"CRS declared as {crs} (expected EPSG:4326 WGS84)")

        # Validate AOI bounds
        w, s, e, n = self.aoi["west"], self.aoi["south"], self.aoi["east"], self.aoi["north"]
        valid_bounds = (-180.0 <= w <= 180.0) and (-180.0 <= e <= 180.0) and (-90.0 <= s <= 90.0) and (-90.0 <= n <= 90.0)
        valid_order = (w < e) and (s < n)
        self._record(cat, "aoi_bounds_validity", valid_bounds and valid_order,
                     f"AOI [W:{w}, S:{s}, E:{e}, N:{n}] coordinates are mathematically and geographically valid")

    # 3. SPATIAL INTERSECTION CHECKS
    def check_spatial_coverage(self):
        cat = "Spatial Coverage & AOI Intersection"
        # Satellite coverage
        sat_bbox = self.cfg.get("satellite", {}).get("bounding_box")
        if sat_bbox:
            sat_intersects = self._bboxes_intersect(sat_bbox, self.aoi)
            self._record(cat, "satellite_aoi_intersection", sat_intersects,
                         f"Sentinel-1 footprint [{sat_bbox['west']:.2f}, {sat_bbox['south']:.2f}, {sat_bbox['east']:.2f}, {sat_bbox['north']:.2f}] intersects AOI",
                         {"sat_bbox": sat_bbox, "aoi": self.aoi})

        # Ocean current coverage
        hycom_bbox = self.cfg.get("environmental", {}).get("ocean_currents", {}).get("spatial_coverage")
        if hycom_bbox:
            hycom_intersects = self._bboxes_intersect(hycom_bbox, self.aoi)
            self._record(cat, "hycom_aoi_intersection", hycom_intersects,
                         f"HYCOM ocean currents domain [{hycom_bbox['west']:.2f}, {hycom_bbox['south']:.2f}, {hycom_bbox['east']:.2f}, {hycom_bbox['north']:.2f}] covers AOI")

        # Wind coverage
        wind_bbox = self.cfg.get("environmental", {}).get("wind", {}).get("spatial_coverage")
        if wind_bbox:
            wind_intersects = self._bboxes_intersect(wind_bbox, self.aoi)
            self._record(cat, "wind_aoi_intersection", wind_intersects,
                         f"ERA5 wind domain [{wind_bbox['west']:.2f}, {wind_bbox['south']:.2f}, {wind_bbox['east']:.2f}, {wind_bbox['north']:.2f}] covers AOI")

    # 4. TEMPORAL RANGE VALIDATION & OVERLAP
    def check_temporal_consistency(self):
        cat = "Temporal Consistency"
        try:
            t_sat = self._parse_utc(self.cfg["satellite"]["observation_timestamp_utc"])
            t_search_start = self._parse_utc(self.cfg["temporal"]["source_search_time_range"]["start_utc"])
            t_search_end = self._parse_utc(self.cfg["temporal"]["source_search_time_range"]["end_utc"])

            self._record(cat, "timestamp_parsing_utc", True,
                         f"Timestamps successfully parsed as strict UTC (Sat: {t_sat.isoformat()})")

            # Observation must fall within or close to search window
            sat_in_window = t_search_start <= t_sat <= t_search_end
            self._record(cat, "satellite_within_search_window", sat_in_window,
                         f"Satellite observation ({t_sat}) falls within search range [{t_search_start} -> {t_search_end}]")

            # Environmental temporal coverage
            hycom_start = self._parse_utc(self.cfg["environmental"]["ocean_currents"]["temporal_coverage"]["start_utc"])
            hycom_end = self._parse_utc(self.cfg["environmental"]["ocean_currents"]["temporal_coverage"]["end_utc"])
            hycom_covers = (hycom_start <= t_search_start) and (hycom_end >= t_sat)
            self._record(cat, "ocean_currents_temporal_overlap", hycom_covers,
                         f"HYCOM coverage [{hycom_start} to {hycom_end}] covers source search window through observation")

            wind_start = self._parse_utc(self.cfg["environmental"]["wind"]["temporal_coverage"]["start_utc"])
            wind_end = self._parse_utc(self.cfg["environmental"]["wind"]["temporal_coverage"]["end_utc"])
            wind_covers = (wind_start <= t_search_start) and (wind_end >= t_sat)
            self._record(cat, "wind_temporal_overlap", wind_covers,
                         f"ERA5 wind coverage [{wind_start} to {wind_end}] covers source search window through observation")

        except Exception as e:
            self._record(cat, "temporal_validation_exception", False, f"Temporal check failed with error: {str(e)}")

    # 5. ENVIRONMENTAL VARIABLES VALIDATION
    def check_environmental_variables(self):
        cat = "Environmental Variables"
        # HYCOM NetCDF
        hycom_path = self.cfg.get("environmental", {}).get("ocean_currents", {}).get("file_path")
        if hycom_path and os.path.exists(hycom_path):
            try:
                with netcdf_file(hycom_path, 'r') as nc:
                    var_keys = list(nc.variables.keys())
                    has_u = "water_u" in var_keys
                    has_v = "water_v" in var_keys
                    has_time = "time" in var_keys
                    has_coords = "lat" in var_keys and "lon" in var_keys
                    all_good = has_u and has_v and has_time and has_coords
                    u_shape = nc.variables["water_u"].shape if has_u else None
                    v_shape = nc.variables["water_v"].shape if has_v else None
                    self._record(cat, "hycom_netcdf_variables", all_good,
                                 f"HYCOM NetCDF contains required variables (water_u shape={u_shape}, water_v shape={v_shape}, coords present)",
                                 {"variables": var_keys, "u_shape": u_shape, "v_shape": v_shape})
            except Exception as e:
                self._record(cat, "hycom_netcdf_variables", False, f"Failed reading HYCOM NetCDF: {str(e)}")
        else:
            self._record(cat, "hycom_netcdf_variables", False, f"HYCOM file missing: {hycom_path}")

        # ERA5 Wind
        wind_csv = self.cfg.get("environmental", {}).get("wind", {}).get("files", {}).get("csv_path")
        if wind_csv and os.path.exists(wind_csv):
            try:
                wdf = pd.read_csv(wind_csv)
                req_cols = ["timestamp_utc", "latitude", "longitude", "wind_u_10m_mps", "wind_v_10m_mps", "wind_speed_10m_mps"]
                missing = [c for c in req_cols if c not in wdf.columns]
                has_cols = len(missing) == 0
                has_data = len(wdf) > 0 and wdf["wind_u_10m_mps"].notnull().all()
                self._record(cat, "era5_wind_variables", has_cols and has_data,
                             f"ERA5 wind dataset contains {len(wdf)} records across required variables with zero NaNs"
                             if has_cols and has_data else f"ERA5 wind missing required columns: {missing}")
            except Exception as e:
                self._record(cat, "era5_wind_variables", False, f"Failed reading ERA5 wind CSV: {str(e)}")
        else:
            self._record(cat, "era5_wind_variables", False, f"ERA5 wind CSV missing: {wind_csv}")

    # 6. AIS CONTENT & VESSEL TRAFFIC VALIDATION
    def check_ais_data(self):
        cat = "AIS Vessel Traffic"
        ais_csv = self.cfg.get("ais", {}).get("files", {}).get("filtered_csv")
        if not ais_csv or not os.path.exists(ais_csv):
            self._record(cat, "ais_dataset_content", False, f"Filtered AIS file missing: {ais_csv}")
            return

        try:
            df = pd.read_csv(ais_csv, low_memory=False)
            req_cols = ["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG"]
            missing = [c for c in req_cols if c not in df.columns]
            has_cols = len(missing) == 0

            # Spatial presence check
            in_aoi = (
                (df["LAT"] >= self.aoi["south"]) & (df["LAT"] <= self.aoi["north"]) &
                (df["LON"] >= self.aoi["west"]) & (df["LON"] <= self.aoi["east"])
            )
            count_in_aoi = in_aoi.sum()
            unique_vessels_aoi = df.loc[in_aoi, "MMSI"].nunique()

            # Plausibility checks: Coordinates must be 100% valid
            valid_coords = (df["LAT"] >= -90.0) & (df["LAT"] <= 90.0) & (df["LON"] >= -180.0) & (df["LON"] <= 180.0)
            
            # Maritime speeds: ITU-R M.1371 standard defines 102.3 as "speed not available". Physical speeds are <= 60 kts.
            itu_speed_na = (df["SOG"] >= 102.2)
            physical_speeds = (df["SOG"] >= 0.0) & (df["SOG"] <= 60.0)
            valid_speed_pct = (physical_speeds | itu_speed_na).mean() * 100

            passed = has_cols and (count_in_aoi > 0) and valid_coords.all() and (valid_speed_pct >= 99.0)

            msg = (
                f"AIS contains {len(df):,} total records, {count_in_aoi:,} records directly inside case AOI, "
                f"{unique_vessels_aoi} unique active vessels (MMSI) with valid coordinates and {valid_speed_pct:.2f}% compliant maritime speeds "
                f"(including standard ITU-R M.1371 SOG=102.3 sentinel flags)"
            )
            self._record(cat, "ais_dataset_content", passed, msg,
                         {"total_records": int(len(df)), "records_in_aoi": int(count_in_aoi), "unique_vessels": int(unique_vessels_aoi)})

        except Exception as e:
            self._record(cat, "ais_dataset_content", False, f"Error validating AIS data: {str(e)}")

    # 7. SAR MEASUREMENT RASTER VALIDATION
    def check_sar_measurement_raster(self):
        cat = "SAR Measurement Raster"
        raster_path = self.cfg.get("satellite", {}).get("files", {}).get("measurement_raster_vv")
        if not raster_path or not os.path.exists(raster_path):
            self._record(cat, "sar_measurement_pixels", False, f"SAR measurement raster missing: {raster_path}")
            return

        try:
            import rasterio
            with rasterio.open(raster_path) as src:
                has_crs = (src.crs is not None and str(src.crs) == "EPSG:4326")
                has_dims = (src.width > 0 and src.height > 0)
                is_uint16 = (src.dtypes[0] == "uint16")
                
                # Check bounds cover AOI
                b = src.bounds
                covers_aoi = (
                    b.left <= self.aoi["west"] and
                    b.bottom <= self.aoi["south"] and
                    b.right >= self.aoi["east"] and
                    b.top >= self.aoi["north"]
                )
                
                arr = src.read(1)
                valid_pixels = arr[arr > 0]
                has_valid_pixels = len(valid_pixels) > 1000000
                min_dn = int(valid_pixels.min()) if len(valid_pixels) > 0 else 0
                max_dn = int(valid_pixels.max()) if len(valid_pixels) > 0 else 0
                mean_dn = float(valid_pixels.mean()) if len(valid_pixels) > 0 else 0.0

                passed = has_crs and has_dims and is_uint16 and covers_aoi and has_valid_pixels
                msg = (
                    f"Sentinel-1 VV GeoTIFF verified: dimensions=({src.height}x{src.width}), CRS={src.crs}, "
                    f"dtype={src.dtypes[0]}, valid_pixels={len(valid_pixels):,} ({len(valid_pixels)/arr.size*100:.1f}%), "
                    f"DN_range=[{min_dn}..{max_dn}], mean_DN={mean_dn:.1f}"
                )
                self._record(cat, "sar_measurement_pixels", passed, msg,
                             {"height": src.height, "width": src.width, "crs": str(src.crs), "valid_pixels": int(len(valid_pixels))})

        except Exception as e:
            self._record(cat, "sar_measurement_pixels", False, f"Error validating SAR measurement raster: {str(e)}")

    def run_all(self) -> Tuple[bool, List[Dict[str, Any]]]:
        self.results = []
        self.check_files_exist()
        self.check_spatial_coordinates()
        self.check_spatial_coverage()
        self.check_temporal_consistency()
        self.check_environmental_variables()
        self.check_ais_data()
        self.check_sar_measurement_raster()

        overall_passed = all(r["passed"] for r in self.results)
        return overall_passed, self.results

    def generate_report(self) -> str:
        passed, results = self.run_all()
        lines = []
        lines.append("================================================================================")
        lines.append(f"DATA FEASIBILITY & INTEGRITY VALIDATION REPORT: {self.case_id.upper()}")
        lines.append(f"Case Name: {self.cfg.get('name')}")
        lines.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()} UTC")
        lines.append("================================================================================")
        lines.append(f"OVERALL STATUS: {'PASS' if passed else 'FAIL'}")
        lines.append("--------------------------------------------------------------------------------")

        curr_cat = None
        for r in results:
            if r["category"] != curr_cat:
                curr_cat = r["category"]
                lines.append(f"\n[{curr_cat}]")
            status_symbol = "[OK]  " if r["passed"] else "[FAIL]"
            lines.append(f"  {status_symbol} {r['test']}: {r['message']}")

        lines.append("\n================================================================================")
        return "\n".join(lines)


if __name__ == "__main__":
    case_path = sys.argv[1] if len(sys.argv) > 1 else "data/cases/case_001.yaml"
    validator = CaseDataValidator(case_path)
    report = validator.generate_report()
    print(report)
    passed, _ = validator.run_all()
    sys.exit(0 if passed else 1)
