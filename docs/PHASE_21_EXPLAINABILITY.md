# Phase 21 — Explainable Why / Why-Not Attribution

## 1. Executive Summary

Phase 21 introduces forensic explainability to the SIH26143 decision-support system. An investigator reviewing candidate vessel rankings can now answer two core questions with exact, artifact-backed evidence:
1. **Why was this hypothesis ranked highly?** (Physical drift accuracy, close spatial source distance, release window alignment, continuous AIS trajectory, verified causal precedence).
2. **Why was another hypothesis not ranked highly?** (Explicit identification of limiting evidence: excessive spatial offset, large temporal deviation, backward drift discrepancy, post-event status, or sparse AIS telemetry).

The feature includes a **Head-to-Head Candidate Comparison Modal** enabling side-by-side evaluation between the best-supported hypothesis (e.g., *Golden Ray*) and any other evaluated candidate (e.g., *KUJAWY*, *RECOVERY*).

> [!IMPORTANT]
> **Scientific Integrity & Boundary Preservation**:
> - Zero changes were made to the attribution algorithm, scoring weights, causal DAGs, or uncertainty models.
> - All displayed numbers, distances, timestamps, and classifications originate 100% from existing validated artifacts (`{case_id}_causal_hypothesis_evidence.csv`, `{case_id}_hypothesis_evidence.json`, and `{case_id}_causal_vessel_summary.csv`).
> - Loaded or legalistic language is strictly avoided. Terminology adheres to objective, physical compatibility definitions.

---

## 2. Core Architecture & Evidence Schema

### 2.1 Backend Data Bridge (`backend/schemas.py` & `backend/main.py`)

The `/api/cases/{case_id}/attribution/ranking` endpoint was augmented to serialize:
- `underlying_metrics`: Raw physical parameters extracted from the hypothesis evidence records.
- `primary_strength` & `primary_weakness`: Deterministic component strength/weakness classifications.
- `evidence_breakdown`:
  - `why_ranked_highly`: Array of factual physical concordance statements.
  - `why_not_ranked_higher`: Array of factual limiting explanations.
  - `limiting_factors`: Structured records detailing dimensions, severity, labels, and underlying values.

```python
class UnderlyingMetrics(BaseModel):
    centroid_error_m: Optional[float] = None
    mean_particle_distance_m: Optional[float] = None
    vessel_source_distance_m: Optional[float] = None
    release_timestamp: Optional[str] = None
    ais_gap_seconds: Optional[float] = None
    ais_track_quality: Optional[str] = None
    coverage: Optional[float] = None
    iou: Optional[float] = None
    causal_precedence_status: Optional[str] = None
    causal_eligibility: Optional[bool] = None
    has_conflict: Optional[bool] = None
    conflict_description: Optional[str] = None
    source_score: Optional[float] = None
    spatial_score: Optional[float] = None
    temporal_score: Optional[float] = None
    drift_score: Optional[float] = None
    ais_quality_score: Optional[float] = None

class LimitingFactor(BaseModel):
    dimension: str
    label: str
    severity: str  # "DISQUALIFYING" | "HIGH_LIMITING" | "MODERATE_LIMITING"
    detail: str
    underlying_value: Optional[str] = None

class EvidenceBreakdown(BaseModel):
    why_ranked_highly: List[str]
    why_not_ranked_higher: List[str]
    limiting_factors: List[LimitingFactor]
```

---

## 3. Deterministic Evidence Logic

### 3.1 Why This Hypothesis?
For every candidate hypothesis, the system highlights physical and temporal criteria that satisfy high compatibility:
- **Physical Drift**: When $\text{drift\_score} \ge 0.70$, displays exact centroid error (e.g., `24.28 m` for *Golden Ray*, `19.01 m` for *Dorothy Moran*).
- **Spatial Compatibility**: When $\text{spatial\_score} \ge 0.60$, displays source distance (e.g., `1,701.57 m` / `1.70 km`).
- **Temporal Alignment**: When $\text{temporal\_score} \ge 0.80$, displays exact hypothesized release timestamp (`2019-09-08T05:25:31.797740+00:00`).
- **AIS Trajectory**: Displays interpolation method (`bracketed_interpolation`) and maximum telemetry ping gap (`69 s`).
- **Causal Consistency**: When status is `AT_RELEASE`, explicitly marks candidate as causal release-source eligible.
- **Forward Simulation**: When $\text{IoU} \ge 0.08$, reports geometric overlap with observed SAR slick.

### 3.2 Why Not This Hypothesis? (Limiting Evidence)
For lower-ranked candidates, the system flags the exact limiting physical bottlenecks:
1. **Post-Event AIS Presence**:
   - Condition: `causal_precedence_status == 'POST_RELEASE'` or `causal_eligibility == False`.
   - Text: *"Not eligible as a release-source explanation because its relevant AIS presence occurs after the hypothesized release."* (Severity: `DISQUALIFYING`).
2. **Poor Spatial Proximity**:
   - Condition: `vessel_source_distance_m >= 3000 m` or $\text{spatial\_score} < 0.40$.
   - Text: *"Candidate vessel was {distance_km} km away from hypothesized release position at candidate release time (spatial score: {score})."*
3. **Poor Drift Match**:
   - Condition: `centroid_error_m >= 100 m` or $\text{drift\_score} < 0.60$.
   - Text: *"Substantial displacement from simulated backward drift trajectory (centroid error: {error} m, drift score: {score})."*
4. **Poor Temporal Match**:
   - Condition: $\text{temporal\_score} < 0.65$.
   - Text: *"Candidate AIS telemetry deviates from hypothesized release time (temporal score: {score})."*
5. **Insufficient AIS Telemetry**:
   - Condition: `ais_gap_seconds > 1800 s` or $\text{ais\_quality\_score} < 0.50$.
   - Text: *"Insufficient AIS evidence due to sparse telemetry or significant track gap ({gap}s gap, score: {score})."*
6. **Poor Forward Simulation Match**:
   - Condition: $\text{IoU} < 0.05$ and $\text{coverage} < 0.70$.
   - Text: *"Forward trajectory simulation exhibits low geometric overlap with observed slick (IoU: {iou}, coverage: {cov})."*
7. **Dimensional Discrepancies**:
   - Condition: `has_conflict == True` in artifact.
   - Text: Injected directly from `conflict_description` (e.g. *"Physical drift model strongly matches observed slick, but candidate vessel was 6.8 km away from release point at hypothesized release time."*).

---

## 4. Investigator UI Features

### 4.1 In-Table "Why?" Expander Rows
- Every candidate row in `CandidateRankingTable.tsx` includes an interactive **"Why?"** button.
- Expanding reveals a 3-column forensic dashboard directly in the table:
  1. **WHY THIS HYPOTHESIS?**: Green checkmarks ($\checkmark$) detailing exact physical metrics.
  2. **WHY NOT HIGHER?**: Amber/red alert callout boxes detailing limiting factors.
  3. **UNDERLYING METRICS**: Quick summary of source distance, centroid error, AIS quality, and causal status, plus a "Side-by-Side Compare" button.

### 4.2 Candidate Comparison Modal (`CandidateComparisonModal.tsx`)
- Triggerable via header button ("Compare Candidates") or per-row ("Compare").
- Allows selecting any two vessels (Benchmark vs Comparative Candidate).
- Features:
  - Side-by-side header cards with rank, vessel type, MMSI, and compatibility scores.
  - Comprehensive physical metrics comparison table with automated color-coded relative advantage indicators.
  - Side-by-side "Why this candidate is ranked highly" vs "Why not this candidate (limiting factors)".
  - **Forensic Investigator Delta Summary**: Objective narrative explaining the exact physical deltas that separate the two hypotheses.

### 4.3 Inspector Drawer Evidence Sections (`CandidatePreview.tsx`)
- The Forensic Investigation Panel on the right side of the screen displays dedicated "WHY THIS HYPOTHESIS?" and "WHY NOT THIS HYPOTHESIS?" cards alongside the multi-component weight bars.
- Includes a direct "Compare With Other Candidates" action button.

---

## 5. Forensic Language Compliance

| Recommended Standard | Disallowed Terminology | System Implementation |
| :--- | :--- | :--- |
| "best-supported hypothesis" | "culprit", "guilty party" | Used in rankings, comparison verdict, and table |
| "physical compatibility" | "probability of guilt" | Standard label for numerical scores (0.0 – 1.0) |
| "evidence" | "proof", "proven" | Applied across all evidence breakdown items |
| "candidate" | "suspect" | Standard entity label for evaluated vessels |
| "insufficient evidence" | "innocent", "cleared" | Used when track gap or telemetry is sparse |

---

## 6. Verification and Validation

### 6.1 Automated Backend Tests
- **Test Suite**: `python -m pytest tests/ -q`
- **Result**: `179 passed, 2 warnings in 36.74s` (100% pass rate).
- Preserved all baseline and regression test guarantees.

### 6.2 Frontend Production Build
- **Build Command**: `cd frontend && npm run build`
- **Result**: TypeScript check and Vite production bundle compiled cleanly with 0 errors.

### 6.3 Live End-to-End Browser Verification (`browser_subagent`)
- Verified on Case 003 (*Golden Ray*):
  - Verified #1 *GOLDEN RAY* ($0.6891$) displays drift centroid error of $24.28\text{ m}$, source distance of $1.70\text{ km}$, release time `05:25:31 UTC`, and track quality `bracketed_interpolation`.
  - Verified #13 *KUJAWY* ($0.5667$) displays the limiting factor: *"Candidate vessel was 6.8 km away from hypothesized release position at candidate release time (spatial score: 0.25)"*.
  - Verified Head-to-Head Comparison Modal displays side-by-side metric table and forensic delta summary.
  - Visual recording saved to: `file:///C:/Users/rkchi/.gemini/antigravity-ide/brain/5ee4b8ae-d5c7-4aab-8574-247c59ed8740/phase21_explainability_1790205085378.webp`.
