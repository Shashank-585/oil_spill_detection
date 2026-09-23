"""
Utility script to stream/download NOAA MarineCadastre AIS for October 2, 2021,
and filter for Case 001 Area of Interest (Huntington Beach / San Pedro Bay).

AOI Bounds:
  Latitude:  33.30 to 33.90 N
  Longitude: -118.50 to -117.80 W
"""

import os
import sys
import time
import zipfile
import urllib.request
import pandas as pd

AIS_URL = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2021/AIS_2021_10_02.zip"
ZIP_PATH = "data/raw/ais/AIS_2021_10_02.zip"
CSV_FILTERED_PATH = "data/raw/ais/case_001_ais_filtered.csv"

# Bounding box with buffer for vessel entry/exit
LAT_MIN, LAT_MAX = 33.30, 33.90
LON_MIN, LON_MAX = -118.50, -117.80


def download_noaa_ais():
    os.makedirs(os.path.dirname(ZIP_PATH), exist_ok=True)
    if os.path.exists(ZIP_PATH) and os.path.getsize(ZIP_PATH) > 300 * 1024 * 1024:
        print(f"Zip already downloaded at {ZIP_PATH} ({os.path.getsize(ZIP_PATH)} bytes)")
        return

    print(f"Downloading NOAA AIS from {AIS_URL}...")
    t0 = time.time()
    req = urllib.request.Request(AIS_URL, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=60) as response, open(ZIP_PATH, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        last_log = time.time()
        
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if time.time() - last_log > 10:
                elapsed = time.time() - t0
                rate = (downloaded / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                pct = (downloaded / total_size * 100) if total_size > 0 else 0
                print(f"Downloaded {downloaded/(1024*1024):.1f}/{total_size/(1024*1024):.1f} MB ({pct:.1f}%) at {rate:.2f} MB/s")
                last_log = time.time()
                
    elapsed = time.time() - t0
    print(f"Download complete: {os.path.getsize(ZIP_PATH)} bytes in {elapsed:.1f}s")


def filter_ais_for_case():
    print(f"Opening {ZIP_PATH} to extract and filter AOI...")
    t0 = time.time()
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        csv_names = [n for n in z.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise FileNotFoundError("No CSV found in NOAA AIS zip")
        csv_name = csv_names[0]
        print(f"Found CSV member: {csv_name}")

        chunk_size = 500000
        filtered_chunks = []
        total_rows = 0

        with z.open(csv_name) as f:
            for i, chunk in enumerate(pd.read_csv(f, chunksize=chunk_size, low_memory=False)):
                total_rows += len(chunk)
                # NOAA AIS column names: MMSI, BaseDateTime, LAT, LON, SOG, COG, Heading, VesselName, IMO, CallSign, VesselType, Status, Length, Width, Draft, Cargo, TransceiverClass
                mask = (
                    (chunk["LAT"] >= LAT_MIN) & (chunk["LAT"] <= LAT_MAX) &
                    (chunk["LON"] >= LON_MIN) & (chunk["LON"] <= LON_MAX)
                )
                matching = chunk[mask]
                if len(matching) > 0:
                    filtered_chunks.append(matching)
                if (i + 1) % 5 == 0:
                    print(f"Processed {total_rows:,} rows, found {sum(len(c) for c in filtered_chunks):,} matches in AOI...")

        if filtered_chunks:
            df_filtered = pd.concat(filtered_chunks, ignore_index=True)
            # Ensure BaseDateTime is converted to standard ISO 8601 UTC
            df_filtered["timestamp_utc"] = pd.to_datetime(df_filtered["BaseDateTime"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            df_filtered.to_csv(CSV_FILTERED_PATH, index=False)
            elapsed = time.time() - t0
            print(f"Saved {len(df_filtered):,} AIS records for Case 001 to {CSV_FILTERED_PATH} in {elapsed:.1f}s")
            print(f"Unique vessels (MMSI) in AOI: {df_filtered['MMSI'].nunique()}")
            print(f"Time range in data: {df_filtered['timestamp_utc'].min()} to {df_filtered['timestamp_utc'].max()}")
        else:
            print("Warning: No records found in specified AOI.")


if __name__ == "__main__":
    download_noaa_ais()
    filter_ais_for_case()
