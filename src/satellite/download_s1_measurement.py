"""
Download and extract the Sentinel-1 SAR VV measurement raster for Case 001.

Product: S1A_IW_GRDH_1SDV_20211002T015821_20211002T015850_039934_04B9C9
Polarization: VV
AOI Bounding Box: [-118.40, 33.40, -117.85, 33.80]
Target File: data/raw/satellite/case_001_s1_measurement_vv.tif
"""

import os
import json
import time
import urllib.request
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds

ITEM_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd/items/S1A_IW_GRDH_1SDV_20211002T015821_20211002T015850_039934_04B9C9"
TOKEN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-grd"
OUT_PATH = "data/raw/satellite/case_001_s1_measurement_vv.tif"

# Case AOI bounds in EPSG:4326
AOI_WEST = -118.40
AOI_SOUTH = 33.40
AOI_EAST = -117.85
AOI_NORTH = 33.80

# 10m nominal pixel spacing in degrees (~0.0001 deg ≈ 11m lat, 9.2m lon at 33.6°N)
PIXEL_RES_DEG = 0.0001


def download_and_extract_s1_vv():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    t0 = time.time()
    
    print("1. Requesting Planetary Computer SAS token...")
    req = urllib.request.Request(TOKEN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        token = json.loads(r.read().decode())["token"]
        
    print("2. Retrieving STAC item metadata...")
    req_item = urllib.request.Request(ITEM_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_item, timeout=15) as r:
        item = json.loads(r.read().decode())
        
    vv_href = item["assets"]["vv"]["href"] + "?" + token
    print(f"VV Asset URL resolved: {item['assets']['vv']['href'][:80]}...")
    
    # Destination raster geometry
    dst_width = int(round((AOI_EAST - AOI_WEST) / PIXEL_RES_DEG))
    dst_height = int(round((AOI_NORTH - AOI_SOUTH) / PIXEL_RES_DEG))
    dst_transform = from_bounds(AOI_WEST, AOI_SOUTH, AOI_EAST, AOI_NORTH, dst_width, dst_height)
    
    print(f"3. Reprojecting AOI measurement raster ({dst_width} x {dst_height} pixels)...")
    with rasterio.open(vv_href) as src:
        gcps, gcp_crs = src.gcps
        dst_arr = np.zeros((dst_height, dst_width), dtype=np.uint16)
        
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_arr,
            src_gcps=gcps,
            src_crs=gcp_crs,
            dst_transform=dst_transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.bilinear
        )
        
    print("4. Writing georeferenced Cloud-Optimized GeoTIFF with DEFLATE compression...")
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "nodata": 0,
        "width": dst_width,
        "height": dst_height,
        "count": 1,
        "crs": "EPSG:4326",
        "transform": dst_transform,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512
    }
    
    with rasterio.open(OUT_PATH, "w", **profile) as dst:
        dst.write(dst_arr, 1)
        dst.update_tags(
            TIFFTAG_IMAGEDESCRIPTION="Sentinel-1A C-SAR Level-1 GRD VV measurement raster for Case 001",
            POLARIZATION="VV",
            PRODUCT_ID="S1A_IW_GRDH_1SDV_20211002T015821_20211002T015850_039934_04B9C9",
            ACQUISITION_DATETIME="2021-10-02T01:58:36.165236Z",
            SENSOR_MODE="IW",
            PRODUCT_TYPE="GRD"
        )
        
    elapsed = time.time() - t0
    file_size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)
    print(f"Saved {OUT_PATH} ({file_size_mb:.2f} MB) in {elapsed:.1f}s")
    
    # Verify by reopening
    with rasterio.open(OUT_PATH) as check:
        data = check.read(1)
        valid = data[data > 0]
        print(f"Verification: Shape={check.shape}, CRS={check.crs}, Dtype={check.dtypes[0]}")
        print(f"Valid pixels: {len(valid):,} / {data.size:,} ({len(valid)/data.size*100:.1f}%)")
        print(f"Min DN={valid.min()}, Max DN={valid.max()}, Mean DN={valid.mean():.1f}")


if __name__ == "__main__":
    download_and_extract_s1_vv()
