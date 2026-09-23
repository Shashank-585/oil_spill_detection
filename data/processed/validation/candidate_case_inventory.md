# Candidate Real Historical Oil-Spill Incident Inventory

> **Purpose**: Catalogs independent real-world maritime oil-spill incidents with verified or credible
> ground truth documentation to expand beyond the single negative pipeline case (`case_001`).

## Case Acquisition Status Summary

| Case ID | Incident | Date | Origin Type | Known Culprit | Satellite Status | AIS Status | Meteo Status | Quality Level | Acquisition Source | Status Category |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| `case_001` | **Huntington Beach Pipeline / San Pedro Bay Oil Spill** | 2021-10-02 | pipeline | None (Pipeline/Other) | Local (.tif) | Local (.csv) | Local (NetCDF/CSV) | **Tier A** | NTSB Accident Report DCA22FM001 ... | `VERIFIED_AVAILABLE` |
| `case_002_wakashio` | **MV Wakashio Grounding & Bunker Oil Spill** | 2020-07-25 | vessel | WAKASHIO | Public Identified | Public Identified | Global Archive | **Tier A** | Panama Maritime Authority / Maur... | `POTENTIALLY_AVAILABLE` |
| `case_003_sanchi` | **MV Sanchi / CF Crystal Tanker Collision** | 2018-01-06 | vessel | SANCHI | Public Identified | Public Identified | Global Archive | **Tier A** | Joint Investigation Report (Chin... | `POTENTIALLY_AVAILABLE` |
| `case_004_os35` | **MV OS 35 Bulk Carrier Collision & Bunker Spill** | 2022-08-29 | vessel | OS 35 | Public Identified | Public Identified | Global Archive | **Tier A** | Gibraltar Port Authority / Tuval... | `POTENTIALLY_AVAILABLE` |
| `case_005_new_diamond` | **MT New Diamond Crude Tanker Fire & Spill** | 2020-09-03 | vessel | NEW DIAMOND | Public Identified | Public Identified | Global Archive | **Tier B** | Sri Lanka MEPA / Indian Coast Gu... | `POTENTIALLY_AVAILABLE` |
| `case_006_grande_america` | **MV Grande America Fire & Sinking** | 2019-03-10 | vessel | GRANDE AMERICA | Public Identified | Public Identified | Global Archive | **Tier A** | BEA Mer (France) Official Marine... | `POTENTIALLY_AVAILABLE` |
| `CASE_007_WABAMUN` | **Lake Wabamun Train Derailment Spill** | 2005-08-03 | other | None (Pipeline/Other) | Not Found | Not Found | Global Archive | **Tier D** | Transportation Safety Board of C... | `NOT_VERIFIED` |

---

## Detailed Historical Incident Profiles & Data Requirements

### 1. `case_001`: Huntington Beach Pipeline Rupture (Status: `VERIFIED_AVAILABLE`)
- **Role**: Negative Safety Benchmark (Non-Vessel Pipeline Source)
- **Incident Date**: 2021-10-02 | **Location**: San Pedro Bay, California (-118.05°W, 33.60°N)
- **Ground Truth Source**: NTSB Investigation DCA22FM001 / USCG Marine Safety Unit
- **Dataset Availability**: Fully ingested (Sentinel-1 VV GRD, NOAA Filtered AIS, HYCOM currents, ERA5 wind).
- **Attribution Role**: Verified that passing ships 5-10 km away are **refused** `HIGH_SUPPORT` attribution.

### 2. `case_002_wakashio`: MV Wakashio Bulk Carrier Grounding (Status: `POTENTIALLY_AVAILABLE`)
- **Role**: Primary Target for Positive Vessel Attribution Validation
- **Incident Date**: 2020-07-25 (Grounding), 2020-08-06 (Hull Breach & Bunker Spill)
- **Location**: Pointe d'Esny Coral Reef, Mauritius (57.74°E, -20.44°S)
- **Known Culprit Vessel**: Bulk Carrier `WAKASHIO` (IMO 9337183, MMSI 356508000, Flag: Panama)
- **Ground Truth Quality**: **Tier A** (Official Panama Maritime Authority Investigation Report)
- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20200806T014312_20200806T014337_033780_03EC26`
- **Missing Datasets**: Sentinel-1 SAR GRD measurement raster (download from Copernicus Open Access Hub); regional AIS trajectory file (extract MMSI 356508000 and background traffic within 50 km).
- **Acquisition Source**: Copernicus Open Access Hub / Spire Global / MarineTraffic Historical Archive.

### 3. `case_003_sanchi`: MV Sanchi / CF Crystal Tanker Collision (Status: `POTENTIALLY_AVAILABLE`)
- **Role**: Positive Multi-Vessel Collision & Sinking Validation
- **Incident Date**: 2018-01-06 | **Location**: East China Sea (125.97°E, 28.37°N)
- **Known Culprit Vessel**: Condensate Tanker `SANCHI` (IMO 9356608, MMSI 477156900, Flag: Panama)
- **Ground Truth Quality**: **Tier A** (Joint Investigation Report submitted to IMO by China, Iran, Panama, HK)
- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20180115T094056_20180115T094121_020150_0225D0`
- **Missing Datasets**: Sentinel-1 measurement raster (Copernicus); East China Sea AIS records covering collision hour.
- **Acquisition Source**: Copernicus Data Space Ecosystem / Japan Coast Guard / EMSA archives.

### 4. `case_004_os35`: MV OS 35 Bulk Carrier Collision & Grounding (Status: `POTENTIALLY_AVAILABLE`)
- **Role**: Positive Vessel Attribution in Extremely Dense Traffic Corridor
- **Incident Date**: 2022-08-29 | **Location**: Catalan Bay, Gibraltar (-5.34°W, 36.14°N)
- **Known Culprit Vessel**: Bulk Carrier `OS 35` (IMO 9179040, MMSI 572396000, Flag: Tuvalu)
- **Ground Truth Quality**: **Tier A** (Gibraltar Port Authority / Tuvalu Ship Registry Report)
- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20220901T061448_20220901T061513_044807_0559F0`
- **Missing Datasets**: Sentinel-1 GRD product; Strait of Gibraltar VTS / EMSA SafeSeaNet AIS trajectory export.
- **Acquisition Source**: Copernicus Hub / Gibraltar Port Authority / EMSA.

### 5. `case_005_new_diamond`: MT New Diamond Crude Tanker Fire (Status: `POTENTIALLY_AVAILABLE`)
- **Role**: Positive Vessel Attribution with Towing & Drift Uncertainty
- **Incident Date**: 2020-09-03 | **Location**: approx. 38 nm off Sangamankanda Point, Sri Lanka (82.30°E, 7.30°N)
- **Known Culprit Vessel**: Crude Tanker `NEW DIAMOND` (IMO 9212852, MMSI 351249000)
- **Ground Truth Quality**: **Tier B** (Sri Lanka MEPA / Indian Coast Guard Reports)
- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20200908T002534_20200908T002559_034261_03F9CD`
- **Missing Datasets**: Sentinel-1 scene; Sri Lankan coastal / Satellite AIS records.
- **Acquisition Source**: Copernicus / MEPA Sri Lanka / MarineTraffic.

### 6. `case_006_grande_america`: MV Grande America Ro-Ro Sinking (Status: `POTENTIALLY_AVAILABLE`)
- **Role**: Positive Deep-Sea Vessel Sinking Benchmark
- **Incident Date**: 2019-03-10 | **Location**: Bay of Biscay (-5.78°W, 46.07°N)
- **Known Culprit Vessel**: Ro-Ro Container Vessel `GRANDE AMERICA` (IMO 9130949, MMSI 247164900)
- **Ground Truth Quality**: **Tier A** (BEA Mer Official Marine Accident Investigation Report)
- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20190313T180743_20190313T180808_026323_02F0B9`
- **Missing Datasets**: Sentinel-1 scene; EMSA CleanSeaNet radar / AIS archive.
- **Acquisition Source**: Copernicus Hub / BEA Mer / Cedre.

### 7. `CASE_007_WABAMUN`: Lake Wabamun Train Derailment (Status: `NOT_VERIFIED`)
- **Role**: Ineligible Case Demonstration
- **Incident Date**: 2005-08-03 | **Location**: Alberta, Canada (-114.60°W, 53.55°N)
- **Ground Truth Quality**: **Tier D** (TSB Canada Report R05E0059)
- **Assessment**: Inland freshwater rail spill occurring prior to Sentinel-1 constellation launch with zero maritime AIS. Unsuitable for marine radar attribution.

---

## Scientific Guardrails Notice
- Synthetic benchmark cases (`SYN_001` through `SYN_006`) are strictly separated and excluded from this inventory.
- No missing satellite scenes or AIS trajectories will be fabricated.
- Score calibration cannot proceed until at least one independent positive case (e.g. `case_002_wakashio`) is fully ingested.