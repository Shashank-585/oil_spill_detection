# PHASE 25 — DATA READINESS & REPRODUCIBLE PROVENANCE

## Executive Overview

**Phase 25** establishes pre-investigation and in-investigation visibility into data availability, observational constraints, and scientific provenance across the **SIH26143 Maritime Oil Spill Attribution Platform**.

Prior to attributing oil spill events or dispatching authority alerts, operators, investigators, and automated decision-support pipelines must audit whether the underlying scientific inputs are complete, constrained, or absent. 

---

## 1. Data Readiness Assessment: The Seven Pillars

Every registered case undergoes an automated data availability check across seven core dimensions. Statuses are strictly limited to the four approved platform categories:

| Status Enum | Semantic Definition | UI Treatment |
|---|---|---|
| **`READY`** | Dataset present, verified, spatiotemporally aligned, and suitable for full analysis. | Emerald Badge (`#3fb950`) |
| **`LIMITED`** | Dataset partially available, coarse, bounded by archival paywalls, or exhibiting partial overlap. | Amber Badge (`#d29922`) |
| **`UNAVAILABLE`** | Mandatory dataset absent from public archive or catalog. Attribution pipeline inhibited. | Crimson Badge (`#f85149`) |
| **`NOT REQUIRED`** | Data dimension non-essential for case category (e.g., ground-truth telemetry in exploratory cases). | Neutral Slate (`#8b949e`) |

*Rule: No intermediate or invented statuses (e.g., "PARTIAL", "PENDING", "UNKNOWN") are permitted.*

### Checked Dimensions

1. **Satellite (`Satellite`)**:
   - Primary SAR imagery coverage (e.g., Sentinel-1 C-SAR IW GRD) and radiometric calibration status.
2. **Environmental (`Environmental`)**:
   - Atmospheric wind (10m u/v vectors) and ocean surface currents (Copernicus Marine / ERA5 reanalysis).
3. **AIS (`AIS`)**:
   - Terrestrial or satellite AIS positional broadcasts within the bounding spatio-temporal envelope.
4. **Temporal Overlap (`Temporal overlap`)**:
   - Concurrency between sensor acquisition timestamp ($T_{obs}$), spill occurrence interval ($T_0$), and candidate transit records.
5. **Spatial Coverage (`Spatial coverage`)**:
   - Geometric overlap between detected slick polygons, candidate search buffer (e.g., 50 km), and environmental grid domains.
6. **Ground Truth (`Ground truth where applicable`)**:
   - Independent verification records (e.g., USCG POLREP, Cedre dossier, or verified pipeline/anchor coordinates).
7. **Artifact Availability (`Artifact availability`)**:
   - Generation of preprocessed GeoTIFF rasters, detected slick GeoJSONs, backward drift trajectories, and forward counterfactual simulations.

---

## 2. Benchmark Case Readiness Audits

### Case 001: Huntington Beach Pipeline Incident (Negative-Control Validation)
- **Role**: Natural seepage / verified benign or infrastructure baseline.
- **Readiness State**: `READY`
- **AIS Availability**: `READY` (91 candidate tracks evaluated, non-attribution verified).
- **Negative-Control Behavior**: Explicitly flags that the platform has full operational telemetry to disprove arbitrary vessel false positives.
- **Ground Truth**: `READY` (US Coast Guard / CDFW POLREP Ground Truth).

### Case 002: MV Wakashio Grounding (Pointe d'Esny, Mauritius)
- **Role**: Physical drift benchmark validation.
- **Readiness State**: `LIMITED`
- **AIS Availability**: `UNAVAILABLE` (Historical 2020 Indian Ocean satellite AIS paywalled/unavailable in public open catalogs).
- **Temporal Overlap**: `LIMITED` (Satellite SAR and ERA5 metocean available; AIS concurrent stream missing).
- **Platform Behavior**: Inhibits vessel attribution ranking; surfaces explicit hydrodynamic drift benchmark validation without forced culprit designation.

### Case 003: Eastern Mediterranean Multi-Candidate Incident
- **Role**: Attribution and rank stability validation.
- **Readiness State**: `READY`
- **AIS Availability**: `READY` (12 commercial vessels tracked within 48h temporal search window).
- **Platform Behavior**: Enables end-to-end evidence ranking, causal consistency filtering, and Monte Carlo rank stability scoring.

---

## 3. Reproducible Provenance Architecture

Scientific and technical transparency is maintained without claiming legal chain-of-custody.

> **Standard Platform Terminology**:
> The pipeline uses **"reproducible provenance"** rather than "legal chain of custody" or "forensic admissibility". All records document deterministic data pipelines, processing versioning, and cryptographic SHA-256 integrity checksums.

### Provenance Attributes Exposed:
- **`dataset_name`**: Formal name of dataset or artifact (e.g., Sentinel-1 SAR IW GRD, ERA5 Metocean Reanalysis, Historical Spatiotemporal AIS Archive).
- **`source`**: Upstream provider or satellite mission (e.g., European Space Agency / Copernicus Open Access Hub, ECMWF, MarineTraffic / Spire Open AIS).
- **`acquisition_time`**: ISO-8601 UTC timestamp of original sensor observation or archive ingest.
- **`processing_version`**: Platform pipeline release version (e.g., `v1.0.0-phase25`).
- **`sha256_checksum`**: Hexadecimal SHA-256 hash calculated directly from the file content when stored.
- **`artifact_timestamp`**: Timestamp of platform artifact compilation.
- **`record_type`**: `"reproducible provenance"`.

---

## 4. User Interface Integration

1. **Top Header Quick-Audit**:
   - `DATA: READY` / `DATA: LIMITED` status badge directly on top navigation bar with one-click full audit modal launcher (`DataReadinessModal`).
2. **Forensic Inspector Drawer (Continuous Inspection)**:
   - Dedicated `DATA READINESS & PROVENANCE` card embedded between Incident Profile and Attribution Leaderboard.
   - Provides immediate, non-intrusive visibility before starting or reviewing an attribution analysis.
3. **Investigation Dossier View (`/audit`)**:
   - Embedded within **SECTION 14 · DATA READINESS, LIMITATIONS & SYSTEM BOUNDARIES**.
   - Includes cryptographic checksums with one-click clipboard copying in **SECTION 16 · PROVENANCE & CRYPTOGRAPHIC ARTIFACT AUDIT**.
4. **Compact "Data Limitations" Callout**:
   - Amber warning card displaying specific boundary constraints per case without deceptive legal assurances.

---

## 5. API Endpoints

- `GET /api/cases/{case_id}/readiness`
  - Returns complete `DataReadinessReport` containing the 7 checks, data limitations array, reproducible provenance records, and overall case status.
- `GET /api/cases/{case_id}/provenance`
  - Returns raw `List[DatasetProvenanceRecord]` with cryptographic hashes and version stamps.

---

## 6. Verification & Quality Gates

- **Backend Pytest Suite**:
  - `tests/test_data_readiness.py`: 6 dedicated tests verifying status adherence, pillar presence, case-specific conditions, non-legal terminology, and API endpoints.
  - Overall test suite: **193 tests passed** in 37.67s (`python -m pytest tests/`).
- **Frontend Production Build**:
  - `npm run build` executed with `tsc -b && vite build`: **0 errors, 2926 modules transformed**.
