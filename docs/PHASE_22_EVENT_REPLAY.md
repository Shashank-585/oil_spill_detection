# Phase 22 — Historical Investigation Replay

## 1. Overview & Forensic Objective
Phase 22 implements an investigator-facing **Historical Investigation Replay Mode** that visually reconstructs the 4D timeline of an incident without modifying underlying scientific drift or attribution calculations.

The workflow provides a smooth, interactive progression across 5 physical milestones:
$$\text{Start} \longrightarrow \text{Pre-Event Traffic} \longrightarrow \text{Incident Reference Time } (T_0) \longrightarrow \text{Post-Event Traffic / Dispersion} \longrightarrow \text{Satellite Observation } (T_{\text{obs}})$$

```
                                 INCIDENT T₀ (Capsizing)
                                       05:46 UTC
                                          │
    ┌──────────────────────┬──────────────┴──────────────┬──────────────────────┐
    │                      │                             │                      │
 1. Start           2. Pre-Event Traffic          4. Post-Event Response   5. Satellite SAR Pass
11:46 UTC (-18h)    23:32 UTC (-6h)               08:35 UTC (+3h)          11:25 UTC (+5h 39m)
```

---

## 2. Interactive Capabilities

### Playback Controls
- **Play / Pause**: Initiates a 60 FPS animation loop with `requestAnimationFrame` and delta timing.
- **Spacebar Shortcut**: Toggles Play / Pause globally without clicking, disabled automatically when text inputs are focused.
- **Playback Speed**: Configurable via five speed multipliers:
  - `0.5x` — High-precision inspection
  - `1.0x` — Default baseline (1 second real time advances 10 minutes simulated time)
  - `2.0x` — Rapid corridor transit
  - `5.0x` — Multi-hour transit review
  - `10.0x` — Full search window sweep
- **Step Previous / Next**: Advances or rewinds directly to adjacent physical milestones.
- **Reset (`↺`)**: Resets the playback head directly to incident origin time $T_0$.

### Relative Offset & Active Phase Badging
- Real-time offset counter relative to $T_0$:
  $$T \pm \text{hh:mm:ss} \quad (\text{e.g., } T - 06\text{h } 13\text{m } 06\text{s} \text{ or } T + 05\text{h } 39\text{m } 31\text{s})$$
- Dynamic 4-phase status banner:
  1. `PHASE 1: PRE-EVENT VESSEL TRAFFIC`
  2. `PHASE 2: INCIDENT EVENT T₀ (ORIGIN)`
  3. `PHASE 3: POST-EVENT MOVEMENT & RESPONSE`
  4. `PHASE 4: SATELLITE SAR OBSERVATION (T_OBS)`

### Map Layer Quick Toggles
Investigators can independently toggle map layers during replay:
1. **AIS Vessels**: Interpolated vessel positions and track envelopes.
2. **Incident Point ($T_0$)**: Geographical marker at incident origin.
3. **Observed Slick**: SAR detected dark formation boundary.
4. **Lagrangian Drift**: Forward/backward particles simulating surface parcel advection.
5. **Release Hypotheses**: Evaluated candidate release sourcing locations.
6. **SAR Footprint**: Satellite ground swath coverage / AOI bounding polygon.

---

## 3. Case-by-Case Handling & Non-Deceptive Provenance

| Case ID | Incident | Replay Experience & Forensic Provenance |
| :--- | :--- | :--- |
| `case_003_golden_ray` | Golden Ray Capsizing | Full 4D vessel movement leading to capsize at $05:46\text{ UTC}$, subsequent escort/tug vessel response, and Sentinel-1 SAR acquisition at $11:25\text{ UTC}$. |
| `case_001_santa_barbara` | Pipeline 001 Failure | Negative-control validation. Stationary infrastructure anchor at $T_0$ with transit corridor vessels. |
| `case_002_wakashio` | MV Wakashio Grounding | Physical validation benchmark. Replay reflects lack of high-density AIS telemetry with explicit limitation notice: *AIS Telemetry Unavailable — Physical Validation Benchmark*. |

### Provenance Banner
To eliminate investigator confusion, all replay displays feature explicit forensic labeling:
> `[RECONSTRUCTED AIS TELEMETRY]` Linear interpolation from discrete transponder pings.  
> `[SIMULATED DRIFT]` Lagrangian particles from hydrodynamic/wind reanalysis.  
> `[OBSERVED SAR SLICK]` Static radar observation at satellite acquisition epoch $T_{\text{obs}}$.

---

## 4. Performance & Architectural Integrity
1. **Zero Browser Drift Recalculation**: Drift trajectories and candidate scorings use pre-computed artifacts from the backend API.
2. **Pre-Indexed Numeric Epochs**: No `new Date()` parsing inside the rendering loop. Coordinates and epochs are pre-indexed upon loading tracks.
3. **Logarithmic Time Lookups**: Spatial interpolation uses binary search $O(\log N)$ across chronologically sorted epoch arrays (`getPointAtTimeFast`).
4. **Jitter-Free RAF Loop**: Delta timing capped at 100ms prevents animation stutter or massive skips when switching browser tabs.
5. **All 179 Python Tests Passing**: Verified with `python -m pytest tests/ -q` ($179\text{ passed in } 38.70\text{s}$).
6. **Zero TypeScript / Vite Bundle Warnings**: Verified with `npm run build` ($0\text{ errors}$).
