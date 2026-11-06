# 🛰️ Sonar Backend Core

FastAPI backend, DSP computation engine, and Typer CLI for **Sonar** (Acoustic Side-Channel Security & Forensics Suite).

## Architecture

The backend is built with Python 3.11+ using high-performance vectorized NumPy, SciPy, and Typer/Rich:

```text
backend/sonar/
├── api/
│   ├── main.py             # FastAPI entry point, CORS config, health check
│   ├── routes_audit.py     # POST /api/audit (Pillar 1)
│   ├── routes_cloak.py     # POST /api/cloak & GET /api/download/{filename} (Pillar 2)
│   └── routes_verify.py    # POST /api/verify/alibi & POST /api/verify/physics (Pillars 3A & 3B)
├── core/
│   ├── audio_io.py         # FFmpeg downsampling (4000 Hz mono) & metadata-stripping remux
│   ├── spectrogram.py      # Hann STFT, 2-stage spectral whitening, MAD normalization
│   ├── physics.py          # 3D retarded-time Doppler solvers, Newton-Raphson root finder, WGS84->ENU
│   ├── detector.py         # Vectorized Viterbi ridge tracker & Huber loss curve fitter
│   ├── cloak.py            # 3-layer active privacy cloaking engine (notch, chaff, time warp)
│   ├── verify_alibi.py     # Spatiotemporal ADS-B alibi verifier & silence violation detector
│   └── verify_physics.py   # AI generated audio drift & harmonic lock inspector
├── data/
│   ├── elevation.py        # AWS Terrarium DEM tile fetcher with disk cache & bilinear interpolation
│   ├── adsb.py             # Historical ADS-B trajectory query & readsb trace parser
│   └── icao_types.json     # Propeller/turboprop vs jet categorization table
└── utils/
    └── synthetic_gen.py    # Deterministic multi-plane calibration fixture generator
```

## Quick Start

### 1. Setup Virtual Environment
```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

### 2. Run Test Suite
```bash
pytest tests -v
```

### 3. CLI Commands
```bash
# Generate calibration fixture
sonar synth-fixture -o sample_leak.wav -n 2 -d 180

# Audit recording for acoustic leak risk
sonar audit sample_leak.wav

# Sanitize recording with 3-layer cloak
sonar cloak sample_leak.wav -o sample_cloaked.wav

# Spatiotemporal alibi verification
sonar verify-alibi recording.wav --lat 40.876466 --lon -73.524951 --utc "2026-09-08T18:35:00Z"

# AI audio kinematics & harmonic lock inspection
sonar verify-physics ai_sample.wav

# Launch local FastAPI server (Port 8000)
sonar serve --host 127.0.0.1 --port 8000 --reload
```

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Engine health, version, and CPU availability |
| `POST` | `/api/audit` | Upload media, returns whitened STFT & detected Doppler ridges |
| `POST` | `/api/cloak` | Sanitizes audio/video via 3-layer cloaking pipeline |
| `GET` | `/api/download/{filename}` | Download sanitized container (enforces path traversal sandbox) |
| `POST` | `/api/verify/alibi` | Forward-models ADS-B flight paths against observer coordinates |
| `POST` | `/api/verify/physics` | Forensic evaluation of harmonic locking & kinematic limits |
