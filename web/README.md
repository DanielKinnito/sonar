# 🛰️ Sonar Web Workstation

Interactive, local-first Next.js 14 + TypeScript frontend for **Sonar** (Acoustic Side-Channel Security & Forensics Suite).

## Overview

The Sonar workstation delivers an acoustic forensics laboratory interface running on **Port 50242** (`SO2AR`). It interfaces directly with the local FastAPI backend (`http://127.0.0.1:8000`) with zero external telemetry or cloud dependencies.

```text
web/src/
├── app/
│   ├── layout.tsx            # Global metadata, Inter font, obsidian base styles
│   ├── page.tsx              # 4-tab workstation navigation & telemetry header
│   └── globals.css           # Custom scrollbars, monospace HUD tokens, canvas styling
├── components/
│   ├── SpectrogramCanvas.tsx # High-refresh dual HTML5 canvas with real-time crosshair HUD
│   ├── AuditPanel.tsx        # Pillar 1: Whitened STFT & automated Doppler ridge audit
│   ├── CloakPanel.tsx        # Pillar 2: 3-layer active cloaking controls & diff preview
│   ├── VerifyAlibiPanel.tsx  # Pillar 3A: ADS-B flight matching & silence violation detector
│   └── VerifyPhysicsPanel.tsx# Pillar 3B: AI / synthetic audio harmonic lock inspector
└── lib/
    └── api.ts                # Fully-typed client for the Sonar FastAPI engine
```

## Why Port 50242?

1. **Brand Identity:** `50242` spells **SO2AR** ("SONAR") in leetspeak ($5=\text{S}, 0=\text{O}, 2=\text{N}, 4=\text{A}, 2=\text{R}$).
2. **Zero Port Collisions:** Located in the IANA/RFC 6335 private & dynamic port range ($49152\text{--}65535$), preventing collisions with standard development servers occupying port `3000`.

## Quick Start

### 1. Install Dependencies
```bash
cd web
npm install
```

### 2. Launch Dev Workstation
```bash
npm run dev
```
Workstation starts immediately at:
**👉 [http://localhost:50242](http://localhost:50242)**

### 3. Production Build
```bash
npm run build
npm run start
```

## Workstation Features

- **High-Refresh Dual Canvas Spectrogram:** Renders $16384$-point whitened STFT matrices on an offscreen canvas with real-time interactive mouse crosshair telemetry displaying `(Time, Frequency, Whitened SNR σ)`.
- **4 Operational Pillars:**
  - **Audit:** Live vulnerability scoring (`CRITICAL`, `MODERATE`, `LOW`, `CLEAN`) with fitted Doppler curves and harmonic overlays ($f_0, 2f_0, 3f_0$).
  - **Cloak:** Configurable 3-layer active sanitization (surgical STFT notch, decoy chaff injection, $\pm 0.35\%$ time-base drift, and container metadata stripping).
  - **Verify Alibi:** Spatiotemporal cross-correlation against historical ADS-B flight paths and AWS Terrarium DEM ground elevations.
  - **Verify Physics:** Harmonic lock residual ($\epsilon_{harm}$) and kinematic boundary detection to unmask AI-generated audio (Sora, ElevenLabs).
