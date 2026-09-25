# PHASE 26 — SATELLITE OBSERVATION METADATA UPGRADE

## Executive Summary

**Phase 26** upgrades the satellite observation experience across the **SIH26143 Maritime Oil Spill Attribution Platform**, strictly differentiating operational radar detection inputs from supporting multi-spectral optical observations.

The platform processes physical satellite acquisitions to reconstruct oil slick geometry, backscatter contrast, and temporal trajectory anchors without inventing synthetic datasets, introducing fake real-time feeds, or claiming optical attribution where unsupported by scientific outputs.

---

## 1. Sentinel-1 Operational SAR Architecture

Sentinel-1 Synthetic Aperture Radar (C-SAR) is the **primary operational sensor** driving the dark-spot detection pipeline across all benchmark cases.

### Core Metadata Fields Exposed

| Parameter | Specification | Platform Role |
|---|---|---|
| **Platform** | Sentinel-1A / Sentinel-1B | Spacecraft constellation identifier |
| **Sensor** | C-SAR (Center Frequency: 5.405 GHz, C-band) | Active microwave radar instrument |
| **Mode** | IW (Interferometric Wide Swath) | 250 km swath width with TOPSAR burst acquisition |
| **Product Type** | Level-1 GRDH (Ground Range Detected High Resolution) | Multilooked amplitude detected product resampled to ground range |
| **Polarization Used** | **VV (Vertical transmit / Vertical receive)** | **Operational detector channel** |
| **Orbit Direction** | ASCENDING / DESCENDING | Track orientation |
| **Spatial Resolution** | 10.0 m × 10.0 m pixel spacing (20 m range × 22 m azimuth) | Calibrated spatial sampling |
| **Processing Status** | `CALIBRATED_AND_DETECTED` / `CALIBRATED_BENCHMARK` | Stage of internal processing |

### Operational Channel Rationale: VV Polarization

The adaptive CFAR (Constant False Alarm Rate) segmentation detector operates strictly on the **VV channel**:
- **Physical Bragg Scattering**: Co-polarized VV waves interact with wind-generated ocean capillary and short gravity waves via Bragg resonance, producing strong diffuse background backscatter.
- **Surface Tension Dampening**: Floating petroleum films dampen capillary waves, suppressing backscatter and producing dark contrast spots.
- **Cross-Polarization (VH) Exclusion**: While VH cross-polarization is recorded, it suffers from a significantly lower signal-to-noise ratio over open ocean and high sensitivity to radar thermal noise floor ($NESZ \approx -22\text{ dB}$), making it unsuitable as the primary segmentation channel.

---

## 2. Sentinel-2 Supporting Optical Observations

Supporting optical observations provide valuable visual confirmation in clear daylight conditions, but are **explicitly decoupled** from the operational radar pipeline.

### Case-by-Case Status

| Case ID | Incident Name | Sentinel-2 Availability | Operational Role |
|---|---|---|---|
| `case_001` | Huntington Beach Pipeline | **Not Active** (Nighttime SAR) | None (Pure radar pipeline) |
| `case_002_wakashio` | MV Wakashio Grounding | **Available** (`S2B_MSIL2A_20200806`) | **Supporting optical observation only** |
| `case_003_golden_ray` | Golden Ray Capsizing | **Not Active** | None (Pure radar pipeline) |

### Case 002 (Wakashio) Optical Metadata

- **Platform & Sensor**: Sentinel-2B MSI (Multi-Spectral Instrument)
- **Acquisition Timestamp**: `2020-08-06T06:24:49.024Z` (+4.91 hours post-breach)
- **Cloud Cover**: `<0.1%` (`<0.08%` over coral reef and Pointe d'Esny lagoon)
- **Available Bands & Products**: B02 (Blue), B03 (Green), B04 (Red), B08 (NIR), and True Color Image (TCI) Level-2A BOA reflectance.
- **Scientific Boundary Notice**:
  > *Supporting optical observation only. Not ingested by the operational radar dark-spot segmentation pipeline and does NOT contribute to vessel candidate attribution.*

---

## 3. Observation Timeline

For every case, the observation timeline places sensor observations in chronological context relative to the incident reference time ($T_0$):

```
       Pre-Event Baseline           Incident Origin (T0)       Supporting Optical          Operational SAR
   [Orbit Revisit / Baseline] ────► [Vessel Breach / Spill] ─► [Sentinel-2 Visual] ──────► [Sentinel-1 C-SAR]
               │                              │                         │                         │
     T_ref = -191.9 hours               T_ref = 0.0 hours          T_ref = +4.91 hours       T_ref = +96.14 hours
```

### Observation Types & Milestones:
1. **Pre-Event Observation (`PRE_EVENT`)**: Baseline radar or optical scene acquired prior to incident initiation, establishing unpolluted background backscatter levels.
2. **Incident Reference Time (`INCIDENT_REFERENCE`)**: Ground truth $T_0$ timestamp derived from official casualty reports, VTS logs, or telemetry.
3. **Supporting Optical Observation (`SUPPORTING_OPTICAL`)**: Daytime multi-spectral scene verifying visual discoloration or surface sheen.
4. **Operational SAR Acquisition (`OPERATIONAL_SAR`)**: Primary calibrated radar measurement scene ingested by the detection pipeline.
5. **Post-Event Observation (`POST_EVENT`)**: Subsequent orbital pass tracking dispersion and weathering.

---

## 4. Revisit / Acquisition Context

The platform strictly differentiates between **orbital pass opportunity** and **actual acquired product**:

### Critical Operational Distinction:
- **Satellite Orbital Revisit Opportunity**:
  Geometric track overpass of an area by satellite constellation (nominal 12 days per satellite, 6 days for dual A/B constellation; overlapping cross-track swaths provide geometric opportunities every 24–72 hours).
- **Actual Acquired / Usable Observation**:
  Requires that the satellite payload was commanded into high-rate data take mode (IW/EW), instrument telemetry was downlinked to ground stations, and Level-1 products were generated and archived without missing packets or corrupted ephemeris.

*The platform rejects synthetic "real-time feeds" and strictly exposes verified historical satellite acquisitions.*

---

## 5. User Interface Integration

1. **Synthetic Aperture Radar Workspace (`/sar`)**:
   - Enhanced with tabbed sub-navigation:
     - **`SATELLITE OBSERVATIONS & PROVENANCE`**: Embeds `SatelliteObservationPanel` exposing Sentinel-1 metadata, Sentinel-2 supporting panel, observation timeline, and revisit context.
     - **`RADIOMETRIC CALIBRATION & SLICK DETECTION`**: Shows calibrated backscatter stats ($\sigma^0$), LUT gain factors ($A_\sigma$), Gamma-MAP speckle filter parameters, and segmented slick vector polygons.
2. **Investigation Report Dossier (`/audit`)**:
   - **SECTION 03 · SATELLITE OBSERVATION**: Includes one-click expandable inspection of the full observation package and timeline.

---

## 6. Verification & Quality Gates

- **Backend Pytest Suite**:
  - `tests/test_satellite_observation.py`: 6 tests validating Sentinel-1 VV channel enforcement, Sentinel-2 optical presence/absence, timeline sorting, revisit context distinction, and API endpoints.
  - Complete test suite: **199 passed, 2 warnings in 35.64s** (`python -m pytest tests/`).
- **Frontend Production Build**:
  - `npm run build` completed with **0 errors, 2927 modules transformed**.
