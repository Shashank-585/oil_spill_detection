# Phase 24 — Alert & Authority Notification Workflow

## 1. Executive Summary & Forensic Delivery Role

Phase 24 establishes an **Authority Notification & Alert Dispatch Workflow** for the SIH26143 Marine Oil Spill Attribution Decision-Support System.

> **Forensic Philosophy**: The notification layer is **NOT the product itself**. It is the structured, non-prejudicial **delivery mechanism** for conveying scientific investigation findings to coast guards, maritime administrations, and environmental protection authorities.

---

## 2. End-to-End Investigation Lifecycle

The notification layer maps chronologically across the six physical milestones of maritime pollution response:

```
                      Potential Spill Detected
                      (Sentinel-1 SAR Bragg Damping)
                                  │
                                  ▼
                       Investigation Initiated
                      (Backward Drift Plume Modeling)
                                  │
                                  ▼
                         Evidence Generated
                      (AIS Traffic Gating & IoU Comparison)
                                  │
                                  ▼
                         Attribution Status
                      (Causal Precedence & Monte Carlo)
                                  │
                                  ▼
                       Authority Notification
                     (Dispatch Memo & Notification Feed)
                                  │
                                  ▼
                        Investigation Dossier
                      (Full 16-Section Legal Report)
```

---

## 3. Standardized Alert Types

To maintain scientific fidelity and prevent alarmism or bias, alerts are strictly classified into six supported types (excluding unsupported subjective labels like "high risk"):

| Alert Type | Severity Level | Trigger Condition & Scientific Role |
| :--- | :--- | :--- |
| **`POTENTIAL_SPILL_DETECTED`** | `NOTICE` | Automated SAR segmentation detects backscatter damping; slick area and coordinates established. |
| **`INVESTIGATION_INITIATED`** | `INFO` | Metocean forcing (HYCOM currents, ERA5 winds) and backward Lagrangian drift modeling commenced. |
| **`INVESTIGATION_READY`** | `INFO` | Multi-metric comparisons, candidate associations, and 16-section dossier synthesized. |
| **`STRONGLY_SUPPORTED_HYPOTHESIS`** | `ACTION_REQUIRED` | Single candidate vessel exhibits high evidence score, causal temporal precedence, and 100% Monte Carlo rank stability. |
| **`INSUFFICIENT_EVIDENCE`** | `NOTICE` | Physical evidence indicates non-vessel origin (e.g. subsea pipeline failure) or ambiguous multi-vessel corridor. |
| **`AIS_DATA_UNAVAILABLE`** | `NOTICE` | Commercial/regional AIS paywalls prevent candidate tracking; attribution suppressed to prevent speculation. |
| **`INVESTIGATION_UPDATED`** | `INFO` | Secondary observations, revised metocean data, or updated causal filters modify candidate rankings. |

---

## 4. Strict Forensic Language Standards

Decision-support alerts must never compromise legal neutrality or prejudge culpability:

* **Prohibited Phrasing**:
  - ❌ `"This vessel caused the spill."`
  - ❌ `"The culprit vessel has been identified."`
  - ❌ `"Guilty vessel confirmed."`
  - ❌ `"Legal proof established."`
  - ❌ `"High risk offender."`
* **Mandated Phrasing**:
  - ✅ **Positive Attribution**: `"Vessel X is currently the highest-ranked hypothesis under the available evidence."`
  - ✅ **Negative Control / Ambiguous Traffic**: `"No vessel attribution is currently supported."`
  - ✅ **AIS Limitation**: `"No vessel attribution is currently supported. Regional multi-vessel dynamic AIS telemetry is commercially paywalled and unavailable."`

---

## 5. Case-by-Case Notification Behavior & Validation

### Case 001: Huntington Beach Pipeline (Negative Control)
- **Alert Type**: `INSUFFICIENT_EVIDENCE`
- **Severity**: `NOTICE`
- **Attribution Status**: `NEGATIVE_CONTROL`
- **Notification Phrasing**:  
  > `"No vessel attribution is currently supported."`
- **Investigative Findings**:
  - 10 commercial transit vessels evaluated in the San Pedro Bay shipping channel; all confirmed non-causal.
  - Slicks track back to offshore platforms / fixed infrastructure (*Pipeline 001*).
  - Explicit authority recommendation: *Ensure commercial transit vessels in shipping fairway are not subjected to false enforcement.*

### Case 002: MV Wakashio Grounding (Physical Validation Benchmark)
- **Alert Type**: `AIS_DATA_UNAVAILABLE`
- **Severity**: `NOTICE`
- **Attribution Status**: `AIS_UNAVAILABLE`
- **Notification Phrasing**:  
  > `"No vessel attribution is currently supported. Regional multi-vessel dynamic AIS telemetry is commercially paywalled and unavailable."`
- **Investigative Findings**:
  - 0 candidate vessels evaluated due to commercial paywalls.
  - Remote-sensing SAR detection and forward hydrodynamic dispersion models verified as physical benchmarks only.
  - Attribution candidate ranking suppressed to prevent unsupported vessel attributions.

### Case 003: M/V Golden Ray (Blind Attribution Validated)
- **Alert Type**: `STRONGLY_SUPPORTED_HYPOTHESIS`
- **Severity**: `ACTION_REQUIRED`
- **Attribution Status**: `STRONGLY_SUPPORTED`
- **Notification Phrasing**:  
  > `"Vessel Vehicle Carrier GOLDEN RAY (MMSI 538007762) is currently the highest-ranked hypothesis under the available evidence."`
- **Investigative Findings**:
  - Composite evidence score: `0.6891` (Rank #1 of 25 evaluated candidate vessels).
  - Causal precedence confirmed **`AT_RELEASE`** at T₀ (05:46 UTC). Escort tugs (*Dorothy Moran*, *Ann Moran*) disqualified as post-event emergency responders.
  - Monte Carlo uncertainty analysis demonstrates **100% Rank Stability** across 50 metocean perturbations (+0.284 margin over Rank #2).

---

## 6. Implementation Architecture

### 1. Prototype Authority Notification Inbox & Preview UI
As no external email connector plugin was pre-authorized, the system implements a **clean prototype dispatch preview and inbox UI** rather than inventing a fake email backend or making false external delivery claims.
- **Component**: `frontend/src/components/notifications/AuthorityNotificationView.tsx`
- **Navigation**:
  - Dedicated **ALERTS** navigation item in the primary left `NavigationRail`.
  - Notification Bell button with dynamic alert counter in `TopHeader`.
  - Direct deep-linking via `/cases/:case_id/alerts` or `#view=alerts`.
- **Features**:
  - Master-detail dispatch feed with filtering by alert type and severity.
  - Official Memorandum preview with Coast Guard styling and forensic integrity badges.
  - One-click **COPY MEMO TO CLIPBOARD** action.
  - **EXPORT TXT** (Plaintext dispatch memo) and **EXPORT JSON** (Structured notification artifact).
  - One-click seamless navigation to the complete 16-section investigation dossier.

### 2. Backend Data Bridge Endpoints
- `GET /api/cases/{case_id}/notifications` — Returns the chronological `NotificationFeedResponse` for a specific case.
- `GET /api/notifications` — Aggregates all alerts across all registered cases sorted chronologically.
- `GET /api/notifications/{alert_id}` — Looks up a specific alert by unique ID with path traversal protection.

---

## 7. Automated Test Verification

1. **Pytest Notification Test Suite** (`tests/test_notifications.py`):
   - `test_case_001_negative_control_notification`: PASSED
   - `test_case_002_ais_unavailable_notification`: PASSED
   - `test_case_003_positive_ranking_notification`: PASSED
   - `test_api_case_notifications_endpoint`: PASSED
   - `test_api_all_notifications_endpoint`: PASSED
   - `test_api_notifications_error_handling`: PASSED
   - **Result**: `6/6 passed in 1.69s`

2. **Frontend Production Build**:
   - `tsc -b && vite build`: **Built in 1.20s with 0 errors**.
