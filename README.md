<div align="center">

# 🛰️ SONAR
### Acoustic Side-Channel Security & Forensics Suite
**Defend against and operationalize acoustic geolocation from sub-audible aircraft Doppler sweeps.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-14%2F14%20Passing-brightgreen.svg)]()
[![Local-First](https://img.shields.io/badge/Privacy-100%25%20Local--First-success.svg)]()
[![Port](https://img.shields.io/badge/Port-50242%20(SO2AR)-informational.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

[**Quick Start**](#quick-start) •
[**The Threat Model**](#threat-model) •
[**3 Core Pillars**](#core-pillars) •
[**User Manual**](#user-manual) •
[**CLI Reference**](#cli-reference) •
[**Mathematical DSP Specification**](#dsp-foundations) •
[**Security Hardening**](#security-hardening)

</div>

---

## 📖 Executive Summary

**Sonar** is a production-grade, local-first acoustic side-channel security and forensics suite. It counters and operationalizes the acoustic geolocation technique demonstrated by OSINT researchers (popularized by colsto's *"I discovered a sound that leaks your exact location"* and implemented in tools like `mjshiggins/dopplertrack` and `1337isnot1337/DOPPLERGEIST`).

Those offensive tools extract faint, sub-audible propeller aircraft blade-pass Doppler sweeps ($40\text{--}450\text{ Hz}$) from ambient video or audio recordings. By correlating these acoustic sweeps against historical ADS-B flight trajectories and Digital Elevation Models (DEMs), an investigator can pinpoint a recording's real-world physical location within **~100 meters** without relying on GPS metadata or visual landmarks.

---

<a id="threat-model"></a>
## 🔬 The Threat Model: Colsto Acoustic Geolocation

```
+-----------------------------------------------------------------------------------------+
|                                    THE ATTACK PIPELINE                                  |
|                                                                                         |
|  [Raw Video/Audio]                                                                      |
|          │                                                                              |
|          ▼                                                                              |
|  [40-450 Hz STFT] ──► [Spectral Whitening] ──► [Viterbi Ridge Tracking: f_obs(t)]       |
|                                                                   │                     |
|  [Historical ADS-B Logs] (adsb.lol / readsb)                      │                     |
|          │                                                        ▼                     |
|          ▼                                          [Retarded-Time 3D Solver]           |
|  [Candidate Coordinates Grid] ────────────────────► [Predicted Doppler Curves]          |
|          │                                                        │                     |
|          ▼                                                        ▼                     |
|  [AWS Terrarium DEM] ─────────────────────────────► [Huber Least-Squares Correlation]   |
|                                                                   │                     |
|                                                                   ▼                     |
|                                                      [Target Geolocated: < 100m]        |
+-----------------------------------------------------------------------------------------+
|                                  SONAR 3-LAYER DEFENSE                                  |
|                                                                                         |
|  1. Surgical Notch: Replaces real ridge with randomized phase & median noise (0 dB SNR) |
|  2. Decoy Chaff: Injects N realistic fake propeller curves (-50 dBFS) to poison search  |
|  3. Time-Base Warp: Oscillates playback rate ±0.35% to distort df/dt inflection slope   |
|  4. Metadata Purge: ffmpeg -map_metadata -1 -bitexact strips all QuickTime/EXIF GPS tags|
+-----------------------------------------------------------------------------------------+
```

---

<a id="core-pillars"></a>
## 🏛️ Core System Architecture (3 Pillars)

Sonar counters acoustic geolocation through three interconnected pillars:

| Pillar | Operational Role | Key Capabilities |
|---|---|---|
| **Pillar 1: `AUDIT`** | Passive Leak Detection | 2-stage whitened STFT ($N_{fft}=16384$), vectorized Viterbi ridge tracking, Huber least-squares curve fitting ($f_0, v, d_{CPA}, t_{CPA}$), 4-tier risk categorization (`CRITICAL`, `MODERATE`, `LOW`, `CLEAN`). |
| **Pillar 2: `CLOAK`** | Active Privacy Sanitization | 3-layer defense: Layer 1 dynamic notch with median noise floor replacement (0 dB SNR), Layer 2 synthetic decoy chaff injection (-50 dBFS), Layer 3 $\pm 0.35\%$ time-base drift, and container metadata stripping (`-map_metadata -1`). |
| **Pillar 3: `VERIFY`** | Forensics & Synthetic Media | **Sub-Mode 3A (`verify-alibi`):** AWS Terrarium DEM ground elevation decode + 3D retarded-time Doppler forward modeling, Silence Violation detection.<br>**Sub-Mode 3B (`verify-physics`):** AI audio drift detection evaluating Harmonic Lock Residual $\epsilon_{harm}$ and kinematic acceleration bounds $\epsilon_{kin}$. |

---

<a id="quick-start"></a>
## ⚡ Quick Start in 60 Seconds

### Prerequisites
- **Python:** 3.11, 3.12, or 3.13
- **Node.js:** 18+ or 20+
- **FFmpeg:** Installed and available on system `PATH` (`ffmpeg -version`)

### 1. Installation
Clone the repository and set up backend virtual environment:

```bash
# Clone the repository
git clone https://github.com/DanielKinnito/sonar.git
cd sonar

# Set up Python backend
cd backend
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Install Sonar in editable mode with all dependencies
pip install -e .

# Set up Next.js frontend
cd ../web
npm install
cd ..
```

### 2. Run Verification Test Suite
Verify that all 14 DSP, physics, cloaking, and security tests pass:

```bash
backend/.venv/Scripts/pytest backend/tests -v
```
```text
backend/tests/test_cloak.py::test_dynamic_notch_erases_ridge PASSED
backend/tests/test_cloak.py::test_full_cloak_pipeline PASSED
backend/tests/test_detector.py::test_detector_recovers_synthetic_parameters PASSED
backend/tests/test_detector.py::test_multi_plane_fixture_audit PASSED
backend/tests/test_physics.py::test_retarded_time_arrival_delay PASSED
backend/tests/test_physics.py::test_retarded_vs_naive_doppler_asymmetry PASSED
backend/tests/test_physics.py::test_cpa_inflection_slope PASSED
backend/tests/test_physics.py::test_geodetic_to_enu_straight_flyover PASSED
backend/tests/test_physics.py::test_harmonic_lock_residual PASSED
backend/tests/test_security.py::test_cors_headers PASSED
backend/tests/test_security.py::test_download_path_traversal_blocked PASSED
backend/tests/test_security.py::test_audit_demo_payload PASSED
backend/tests/test_verify.py::test_verify_alibi_match_and_silence_violation PASSED
backend/tests/test_verify.py::test_verify_physics_ai_pitch_drift PASSED
============================= 14 passed in 12.4s =============================
```

### 3. Launch the Complete Workstation
Start both the FastAPI core server and Next.js frontend:

```bash
# Terminal 1: Launch FastAPI Core (Port 8000)
cd c:\Projects\sonar\backend
.venv\Scripts\python -m sonar.cli serve --port 8000 --reload

# Terminal 2: Launch Next.js Workstation (Port 50242)
cd c:\Projects\sonar\web
npm run dev
```

Open your browser to:
**👉 [http://localhost:50242](http://localhost:50242)**

> **Why Port 50242?**  
> `50242` is chosen intentionally:  
> 1. It spells **SO2AR** ("SONAR") in leetspeak ($5=S, 0=O, 2=N, 4=A, 2=R$).  
> 2. It resides in the IANA/RFC 6335 private & dynamic port range ($49152\text{--}65535$), ensuring zero port collisions with other Node/Next.js/React projects occupying port `3000`.

---

<a id="user-manual"></a>
## 🖥️ Web Workstation User Manual

The Sonar workstation features a custom HTML5 high-refresh dual canvas spectrogram renderer with real-time crosshair telemetry `(Time, Frequency, Whitened SNR σ)`.

```
========================================================================================
[ S ]  SONAR  v0.1.0        [ Audit ]  [ Cloak ]  [ Verify: Alibi ]  [ Verify: AI Physics ]
========================================================================================
+--------------------------------------------------------------------------------------+
| SPECTROGRAM DISPLAY (40 - 450 Hz)                      [Time: 42.5s | Freq: 112.4Hz]  |
| 400Hz -------------------------------------------------------------------------------|
| 300Hz -----------------------------\-------------------------------------------------|
| 200Hz ------------------------------\---[2f0 Harmonic Stack]-------------------------|
| 100Hz -------------------------------\--[f0 Fundamental Ridge (CPA @ T+41.2s)]-------|
|  40Hz --------------------------------\----------------------------------------------|
|        0s         20s         40s         60s         80s        100s        120s    |
+--------------------------------------------------------------------------------------+
| OVERLAYS: [X] Spectrogram  [X] Viterbi Ridges  [X] Fitted Model  [X] Harmonics  [X] Chaff |
+--------------------------------------------------------------------------------------+
```

### Tab 1: Acoustic Leak Audit (`Pillar 1`)
1. Click **"Select Audio / Video"** to upload an `.mp4`, `.mov`, `.wav`, or `.flac` recording (or click **"Load Synthetic Fixture"** for an immediate zero-setup demo).
2. The engine computes the whitened STFT and runs the Viterbi ridge tracker.
3. Review the **Geolocation Vulnerability Score**:
   - `CRITICAL`: High-confidence multi-plane or multi-harmonic tracks detected with sufficient curvature to achieve spatiotemporal lock.
   - `MODERATE`: Single-plane track with detectable Doppler inflection.
   - `LOW`: Faint or fragmented tonal components with weak curvature.
   - `CLEAN`: Zero detectable aircraft Doppler ridges.
4. Hover your mouse over the canvas to inspect precise frequency and signal-to-noise ratio ($\sigma$) at any coordinate.

### Tab 2: Active Privacy Cloak (`Pillar 2`)
1. Upload your source video or audio recording.
2. Configure the 3 defensive layers:
   - **Layer 1 (Surgical STFT Notch):** Toggle on/off. Dynamically tracks the $f_{ridge}(t)$ trajectory and replaces narrow $\pm 2.5\text{ Hz}$ bins with local noise floor and randomized phase.
   - **Layer 2 (Decoy Chaff Count):** Adjust slider from $1$ to $10$ aircraft passes (default: $5$). Injects realistic synthetic propeller passes at $-50\text{ dBFS}$ to poison candidate search algorithms.
   - **Layer 3 (Time-Base Drift):** Adjust slider from $0.0\%$ to $0.8\%$ (default: $\pm 0.35\%$). Smoothly oscillates playback speed over 22-second windows to break multi-event time-offset locks.
3. Click **"Sanitize Recording"**.
4. Inspect the **Before vs. After dual spectrogram**: verify that real ridges are erased and decoy chaff is injected.
5. Click **"Download Sanitized Media"**: downloads the clean container with all QuickTime/EXIF GPS metadata completely stripped.

### Tab 3: Spatiotemporal Alibi Verifier (`Pillar 3A`)
1. Enter the claimed **Observer Latitude**, **Longitude**, **UTC Timestamp**, and **Search Radius (km)**.
2. Upload the audio recording captured at that scene (or click **"Verify Demo Sky"**).
3. The engine automatically fetches ground elevation from AWS Terrarium DEM tiles and queries historical ADS-B flight trajectories within the radius.
4. Non-propeller aircraft (turbofan jets) are filtered out via ICAO designator tables.
5. The 3D retarded-time model forward-calculates the predicted acoustic curve at the observer's microphone and evaluates spectrogram correlation:
   - **MATCH_CONFIRMED:** Overhead flight acoustics match the historical sky data.
   - **SILENCE_VIOLATION:** An aircraft flew at low altitude within 1.5 km of the claimed coordinate, but the recording contains zero acoustic trace.
   - **INCONCLUSIVE:** No candidate low-altitude propeller traffic was recorded in the airspace during that window.

### Tab 4: AI & Synthetic Audio Physics Inspector (`Pillar 3B`)
1. Upload an audio clip containing a passing vehicle, drone, siren, or propeller aircraft.
2. Click **"Inspect Authentic Demo"** or submit uploaded audio.
3. The engine extracts the fundamental ridge $f_1(t)$ and harmonics $f_2(t), f_3(t)$.
4. Sonar calculates:
   - **Harmonic Lock Residual ($\epsilon_{harm}$):** Physical rotors maintain $\epsilon_{harm} < 0.005$. AI generators (Sora, ElevenLabs) produce frequency-dependent pitch drift where $\epsilon_{harm} > 0.015$.
   - **Kinematic Fit Residual ($\epsilon_{kin}$):** Checks whether the curve obeys physical velocity and acceleration bounds without non-physical inflections.
5. Outputs a definitive forensic verdict: `PHYSICALLY_AUTHENTIC`, `NON_PHYSICAL_DRIFT_DETECTED`, or `UNCONSTRAINED_KINEMATICS`.

---

<a id="cli-reference"></a>
## ⌨️ CLI Reference Manual

Sonar includes a full-featured Typer + Rich command-line interface.

### 1. Synthesize Ground-Truth Calibration Fixture
Generate a mathematically deterministic multi-plane acoustic test file:
```bash
sonar synth-fixture --output sample_leak.wav --planes 2 --duration 180 --fs 4000
```
- `--output / -o`: Output WAV path.
- `--planes / -n`: Number of passing aircraft (1 to 4).
- `--duration / -d`: Duration in seconds (default: 180.0).

### 2. Audit Media for Acoustic Leak Risk
Scan any audio or video file for Doppler curves:
```bash
sonar audit sample_leak.wav
```
Export structured forensic JSON report or spectrogram PNG:
```bash
sonar audit video.mp4 --json audit_report.json --plot spectrogram.png
```

**Example Terminal Output:**
```text
+------------------------------------------------------------------------------------+
|                             SONAR LEAK AUDIT REPORT                                |
+------------------------------------------------------------------------------------+
| File: sample_leak.wav                                 Duration: 180.0s (fs=4000Hz) |
| RISK LEVEL: CRITICAL                                  RISK SCORE: 8.5 / 10.0       |
+------------------------------------------------------------------------------------+
| DETECTED AIRCRAFT PASSES:                                                          |
| Plane 1: f0=114.8 Hz | Speed=64.2 m/s | CPA Dist=642 m | CPA Time=45.2s | SNR=14.2σ|
|   Harmonics Detected: 2f0 (229.6 Hz, 9.8σ), 3f0 (344.4 Hz, 6.1σ)                   |
| Plane 2: f0=82.1 Hz  | Speed=58.1 m/s | CPA Dist=890 m | CPA Time=118.4s| SNR=11.5σ|
+------------------------------------------------------------------------------------+
| RATIONALE: High leak risk: Multi-plane flyovers detected with locked harmonics.    |
| Multi-event temporal offset Δt = 73.2s enables global ADS-B database lock.         |
+------------------------------------------------------------------------------------+
```

### 3. Active Privacy Cloak
Sanitize an audio or video file:
```bash
sonar cloak video.mp4 -o video_cloaked.mp4 --chaff-count 5 --warp-pct 0.35 --notch
```
- `-o / --output`: Output file path (preserves video container, strips metadata).
- `--chaff-count`: Number of decoy curves to inject (default: 5).
- `--warp-pct`: Maximum time-base oscillation percent (default: 0.35%).
- `--notch / --no-notch`: Enable or disable Layer 1 surgical STFT notch.

### 4. Forensic Spatiotemporal Alibi Verification
Verify whether an audio recording matches the historical sky at a given location:
```bash
sonar verify-alibi recording.wav \
  --lat 37.7749 \
  --lon -122.4194 \
  --utc "2026-06-15T14:30:00Z" \
  --radius-km 15.0
```
- `--trace-file`: Optional offline `adsb.lol`/`readsb` `trace_full_*.json`, GeoJSON, or CSV file for retrospective forensic analysis.

### 5. AI / Synthetic Audio Wave Forensics
Analyze an audio file for generative model pitch drift:
```bash
sonar verify-physics generated_clip.wav --f-min 40 --f-max 450
```

### 6. Start Local API Server
```bash
sonar serve --host 127.0.0.1 --port 8000 --reload
```

---

<a id="dsp-foundations"></a>
## 📐 Mathematical & DSP Foundations

### 1. Two-Stage Spectral Whitening
To isolate faint acoustic ridges beneath speech, wind, and city noise, Sonar applies two-stage spectral whitening:
1. **Temporal Median Subtraction** (eliminates static 50/60 Hz electrical hums and HVAC resonance):
   $$S_{stat}(f, t) = S_{dB}(f, t) - \text{median}_{t}(S_{dB}(f, t))$$
2. **Local Frequency Median Subtraction** ($W_f = 61$ bins, flattens broadband voice formants and wind):
   $$S_{white}(f, t) = \max\left(0,\ S_{stat}(f, t) - \text{median}_{f \in \pm 30\text{ bins}}(S_{stat}(f, t))\right)$$
3. **Robust MAD Normalization:** Normalizes $S_{white}(f, t)$ by its Median Absolute Deviation ($\text{MAD} \times 1.4826$), yielding values expressed directly in local standard deviations of noise ($\sigma$).

### 2. Retarded-Time Acoustic Doppler Physics
Sonar accounts for the finite speed of sound ($c = 343.0\text{ m/s}$). Sound emitted at emission time $t_e$ arrives at the observer at observation time $t_{obs}$:
$$t_{obs}(t_e) = t_e + \frac{R(t_e)}{c}$$
Where $R(t_e) = \sqrt{v^2 (t_e - t_0)^2 + d_{CPA}^2}$.

Observed frequency:
$$f_{obs}(t_{obs}) = \frac{f_0}{1 + \frac{v_r(t_e)}{c}}, \quad v_r(t_e) = \frac{v^2 (t_e - t_0)}{\sqrt{v^2 (t_e - t_0)^2 + d_{CPA}^2}}$$

To solve for $t_e$ given an observation time $t_{obs}$, Sonar applies a 5-iteration Newton-Raphson root-finder on $g(t_e) = t_e + \frac{R(t_e)}{c} - t_{obs}$:
$$t_e^{(k+1)} = t_e^{(k)} - \frac{t_e^{(k)} + \frac{R(t_e^{(k)})}{c} - t_{obs}}{1 + \frac{v_r(t_e^{(k)})}{c}}$$

### 3. Maximum Inflection Slope
At the Closest Point of Approach ($t_e = t_0$), the rate of frequency drop reaches its maximum:
$$\left.\frac{df}{dt}\right\vert_{CPA} = -\frac{f_0 \, v^2}{c \, d_{CPA}}$$
This relationship constrains kinematic parameter estimation during non-linear curve fitting.

### 4. Vectorized Viterbi Dynamic Programming Ridge Tracker
To extract continuous frequency tracks $f_{ridge}(t)$ from whitened spectrogram $S_{white}$, Sonar solves the optimal path over time frames $t = 1 \dots T$:
$$\max_{f_{1:T}} \sum_{t=1}^{T} S_{white}(f_t, t) - \sum_{t=2}^{T} \left[ \lambda_{step} \, |f_t - f_{t-1}| + \lambda_{dir} \, \max(0, f_t - f_{t-1}) \right]$$
The directional penalty $\lambda_{dir}$ biases against non-physical upward Doppler transitions.

### 5. Forensic Metrics for AI Audio Detection
- **Harmonic Lock Residual ($\epsilon_{harm}$):**
  $$\epsilon_{harm} = \frac{1}{T} \sum_{t=1}^{T} \left| \frac{f_2(t)}{2 f_1(t)} - 1 \right|$$
  Genuine rotating machinery maintains $\epsilon_{harm} < 0.005$. Generative neural models exhibit incoherent phase drift where $\epsilon_{harm} > 0.015$.

---

<a id="security-hardening"></a>
## 🛡️ Security Hardening & Privacy

Sonar is engineered following strict DevSecOps and OWASP Top 10 guidelines:

| Security Vector | Implementation Detail |
|---|---|
| **Zero Cloud Offload** | All STFT computation, Viterbi ridge tracking, audio cloaking, and physics fitting execute 100% locally on your CPU. No audio bytes or metadata are ever transmitted across the network. |
| **Path Traversal Protection** | The `/api/download/{filename}` endpoint enforces strict regex validation (`^[a-zA-Z0-9_\-]+\.(wav\|mp4\|mov\|mkv\|flac)$`), isolates downloads to a dedicated sandbox directory, and verifies directory containment via resolved path bounds. |
| **Denial-of-Service Defense** | File uploads are capped at 100 MB at the system boundary to prevent memory exhaustion attacks. |
| **CORS Policy** | Restricted to explicit origins (`http://localhost:50242`, `http://127.0.0.1:50242`, `http://localhost:3000`). Wildcard credentials (`*` with `allow_credentials=True`) are strictly forbidden. |
| **Container Sanitization** | Cloaked media is remuxed with `ffmpeg -c:v copy -map_metadata -1 -bitexact`, removing EXIF, GPS, QuickTime location atoms, and hardware serial numbers. |

---

## 📂 Project Structure

```text
sonar/
├── .gitignore                      # Exhaustive rules for media, caches, Python, & Node
├── Makefile                        # Unified build, test, and dev automation
├── README.md                       # Documentation & user manual
├── backend/
│   ├── pyproject.toml              # Dependencies & CLI entry point (sonar = sonar.cli:app)
│   ├── sonar/
│   │   ├── cli.py                  # Typer + Rich command-line application
│   │   ├── api/
│   │   │   ├── main.py             # FastAPI entry point & CORS configuration
│   │   │   ├── routes_audit.py     # POST /api/audit
│   │   │   ├── routes_cloak.py     # POST /api/cloak & GET /api/download/{filename}
│   │   │   └── routes_verify.py    # POST /api/verify/alibi & POST /api/verify/physics
│   │   ├── core/
│   │   │   ├── audio_io.py         # ffmpeg 4000Hz extraction & metadata-stripping remux
│   │   │   ├── spectrogram.py      # Hann STFT, 2-stage whitening, PNG/JSON export
│   │   │   ├── physics.py          # Retarded-time Newton-Raphson solvers & 3D WGS84->ENU
│   │   │   ├── detector.py         # Vectorized Viterbi tracker & Huber curve fitter
│   │   │   ├── cloak.py            # 3-layer active privacy cloaking engine
│   │   │   ├── verify_alibi.py     # Spatiotemporal ADS-B alibi verifier
│   │   │   └── verify_physics.py   # AI & synthetic wave physics inspector
│   │   ├── data/
│   │   │   ├── elevation.py        # AWS Terrarium DEM fetcher, disk cache, bilinear interp
│   │   │   ├── adsb.py             # adsb.lol / readsb trace parser & ICAO filter
│   │   │   └── icao_types.json     # Propeller/turboprop vs jet categorization table
│   │   └── utils/
│   │       └── synthetic_gen.py    # Deterministic ground-truth acoustic fixture generator
│   └── tests/
│       ├── test_physics.py         # Doppler arrival delays, naive vs retarded, ENU geometry
│       ├── test_detector.py        # Viterbi extraction & parameter recovery
│       ├── test_cloak.py           # Surgical notch erasure & 3-layer pipeline
│       ├── test_verify.py          # Alibi matching, silence violations, & AI drift
│       └── test_security.py        # Path traversal, CORS allowlist, upload limits
└── web/
    ├── package.json                # Next.js 14, React 18, Tailwind CSS, Lucide icons
    ├── tsconfig.json
    ├── tailwind.config.ts          # Laboratory-grade dark graphite color ramp
    ├── next.config.mjs
    └── src/
        ├── app/
        │   ├── page.tsx            # 4-tab workstation layout & engine health pill
        │   ├── layout.tsx
        │   └── globals.css
        ├── components/
        │   ├── SpectrogramCanvas.tsx # Custom HTML5 dual canvas with real-time crosshair
        │   ├── AuditPanel.tsx      # Pillar 1 UI
        │   ├── CloakPanel.tsx      # Pillar 2 UI
        │   ├── VerifyAlibiPanel.tsx # Pillar 3A UI
        │   └── VerifyPhysicsPanel.tsx # Pillar 3B UI
        └── lib/
            └── api.ts              # Strongly typed API client
```

---

## 📜 License & Acknowledgments

Distributed under the **MIT License**.

- Built to counter and study the acoustic geolocation research demonstrated by **colsto** (*"I discovered a sound that leaks your exact location"*).
- Incorporates trajectory data conventions from open-source intelligence projects [`mjshiggins/dopplertrack`](https://github.com/mjshiggins/dopplertrack) and [`1337isnot1337/DOPPLERGEIST`](https://github.com/1337isnot1337/DOPPLERGEIST).
- Open elevation tiles provided by **AWS Terrarium DEM**.
- Flight data interfaces compatible with **adsb.lol** and **OpenSky Network**.
