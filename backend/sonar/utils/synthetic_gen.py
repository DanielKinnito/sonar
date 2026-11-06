"""Ground-truth synthetic acoustic fixture generator.

Synthesizes realistic outdoor ambient audio tracks containing genuine physical
retarded-time Doppler curves for propeller aircraft flyovers. Used for deterministic
verification of detection, cloaking, and forensic engines.
"""

from __future__ import annotations

import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from scipy import signal
import soundfile as sf

from sonar.core.physics import (
    straight_line_doppler,
    solve_emission_times_straight_line,
    cpa_inflection_slope,
    SPEED_OF_SOUND,
)


def generate_pink_noise(n_samples: int) -> np.ndarray:
    """Generate 1/f pink noise using Voss-McCartney algorithm."""
    # Fast frequency-domain pink noise filtering
    white = np.random.randn(n_samples).astype(np.float64)
    # FFT
    f_white = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n_samples)
    freqs[0] = 1.0  # Avoid divide by zero at DC
    # 1 / sqrt(f) filter for power spectral density proportional to 1/f
    pink_filter = 1.0 / np.sqrt(freqs)
    pink_filter[0] = 0.0
    f_pink = f_white * pink_filter
    pink = np.fft.irfft(f_pink, n=n_samples)
    std = np.std(pink)
    if std > 1e-8:
        pink = pink / std
    return pink.astype(np.float32)


def generate_ambient_background(
    duration_s: float,
    fs: int = 4000,
    mains_hz: float = 60.0,
    snr_db: float = -32.0,
) -> np.ndarray:
    """Generate realistic outdoor acoustic background with pink noise and stationary mains hum.
    
    Parameters:
        duration_s: Length of audio in seconds
        fs: Sampling rate (Hz)
        mains_hz: Mains power hum fundamental (50 Hz or 60 Hz)
        snr_db: RMS level in dBFS
    """
    n_samples = int(duration_s * fs)
    t = np.arange(n_samples) / float(fs)
    
    # 1. Pink noise floor
    ambient = generate_pink_noise(n_samples) * 0.7
    
    # 2. Add subtle mains hum (fundamental + 2nd & 3rd harmonics)
    mains = (
        0.15 * np.sin(2.0 * np.pi * mains_hz * t) +
        0.06 * np.sin(2.0 * np.pi * 2.0 * mains_hz * t + 0.4) +
        0.02 * np.sin(2.0 * np.pi * 3.0 * mains_hz * t + 1.1)
    )
    
    combined = ambient + mains
    # Scale to desired dBFS
    rms = np.sqrt(np.mean(combined ** 2))
    target_rms = 10.0 ** (snr_db / 20.0)
    if rms > 1e-8:
        combined = combined * (target_rms / rms)
    return combined.astype(np.float32)


def synthesize_propeller_flyover(
    duration_s: float,
    fs: int,
    f0: float,
    v: float,
    d_cpa: float,
    t0_cpa: float,
    harmonic_weights: Tuple[float, float, float] = (1.0, 0.45, 0.20),
    peak_dbfs: float = -18.0,
    c: float = SPEED_OF_SOUND,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Synthesize a single propeller aircraft flyover acoustic signature using retarded-time physics.
    
    Parameters:
        duration_s: Total audio duration (s)
        fs: Sampling rate (Hz)
        f0: Emitted blade fundamental frequency (Hz)
        v: Speed (m/s)
        d_cpa: Minimum slant distance (m)
        t0_cpa: CPA timestamp in emission time (s)
        harmonic_weights: Relative amplitudes for [f0, 2*f0, 3*f0]
        peak_dbfs: Peak signal amplitude at CPA in dBFS
        c: Speed of sound (m/s)
        
    Returns:
        (signal_samples, t_obs_grid, f_obs_curve)
    """
    n_samples = int(duration_s * fs)
    t_obs = np.arange(n_samples, dtype=np.float64) / float(fs)
    
    # 1. Compute exact retarded-time Doppler curve for the fundamental
    f_obs = straight_line_doppler(t_obs, f0, v, d_cpa, t0_cpa, c=c)
    
    # 2. Solve emission times to get slant range R(t_e) for geometric spreading
    t_e = solve_emission_times_straight_line(t_obs, t0_cpa, v, d_cpa, c=c)
    r = np.sqrt((v * (t_e - t0_cpa)) ** 2 + d_cpa ** 2)
    
    # 3. Geometric spreading 1/R amplitude envelope, smoothed by Tukey window near boundaries
    envelope = (d_cpa / r)
    # Smooth start and end with 5% Tukey taper to avoid click artifacts
    taper_len = int(0.05 * n_samples)
    if taper_len > 1:
        taper = np.hanning(2 * taper_len)
        envelope[:taper_len] *= taper[:taper_len]
        envelope[-taper_len:] *= taper[taper_len:]
        
    # 4. Phase-continuous accumulation for fundamental: phi(t) = 2*pi * integral(f_obs) dt
    dt = 1.0 / float(fs)
    phase_fund = 2.0 * np.pi * np.cumsum(f_obs) * dt
    
    # 5. Harmonic stack synthesis
    signal_out = np.zeros(n_samples, dtype=np.float64)
    phase_offsets = [0.0, 0.73, 1.45]
    for k_idx, (weight, phase_off) in enumerate(zip(harmonic_weights, phase_offsets), start=1):
        # Atmospheric absorption rolls off higher harmonics more over long slant ranges
        # High-frequency damping factor
        hf_damping = np.exp(-0.0003 * float(k_idx) * f0 * (r / 1000.0))
        harm_phase = float(k_idx) * phase_fund + phase_off
        signal_out += weight * hf_damping * np.sin(harm_phase)
        
    # Apply spatial envelope
    signal_out *= envelope
    
    # Scale peak amplitude
    max_abs = np.max(np.abs(signal_out))
    target_peak = 10.0 ** (peak_dbfs / 20.0)
    if max_abs > 1e-8:
        signal_out = signal_out * (target_peak / max_abs)
        
    return signal_out.astype(np.float32), t_obs, f_obs


def generate_synthetic_fixture(
    output_path: Optional[str] = None,
    duration_s: float = 180.0,
    fs: int = 4000,
    num_planes: int = 2,
    seed: Optional[int] = 42,
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Generate multi-plane ground truth acoustic fixture.
    
    Parameters:
        output_path: If specified, writes a WAV file to this location.
        duration_s: Duration in seconds (default 180s = 3 minutes).
        fs: Sampling rate (default 4000 Hz).
        num_planes: Number of synthetic aircraft to inject (1, 2, or 3).
        seed: Random seed for repeatability.
        
    Returns:
        (audio_samples, ground_truth_manifest)
    """
    if seed is not None:
        np.random.seed(seed)
        
    # Start with realistic outdoor background
    audio = generate_ambient_background(duration_s, fs=fs, mains_hz=60.0, snr_db=-34.0)
    
    # Deterministic aircraft parameter profiles
    plane_profiles = [
        {"f0": 92.5, "v": 62.0, "d_cpa": 680.0, "t0_ratio": 0.25, "peak_dbfs": -16.0},
        {"f0": 138.0, "v": 78.0, "d_cpa": 1150.0, "t0_ratio": 0.70, "peak_dbfs": -18.5},
        {"f0": 110.0, "v": 55.0, "d_cpa": 890.0, "t0_ratio": 0.48, "peak_dbfs": -20.0},
    ]
    
    ground_truth: List[Dict[str, Any]] = []
    
    for i in range(min(num_planes, len(plane_profiles))):
        prof = plane_profiles[i]
        t0_cpa = duration_s * prof["t0_ratio"]
        # Add slight random perturbation if seed was not fixed, but here seed is deterministic
        plane_audio, t_obs, f_curve = synthesize_propeller_flyover(
            duration_s=duration_s,
            fs=fs,
            f0=prof["f0"],
            v=prof["v"],
            d_cpa=prof["d_cpa"],
            t0_cpa=t0_cpa,
            peak_dbfs=prof["peak_dbfs"],
        )
        audio += plane_audio
        
        # Calculate theoretical inflection slope at CPA
        slope_cpa = cpa_inflection_slope(prof["f0"], prof["v"], prof["d_cpa"])
        
        # Calculate observer CPA timestamp: t_obs_cpa = t0_cpa + d_cpa / c
        t_obs_cpa = t0_cpa + (prof["d_cpa"] / SPEED_OF_SOUND)
        
        gt_entry = {
            "plane_id": f"SYNTH-AC{i+1:02d}",
            "f0_hz": prof["f0"],
            "velocity_ms": prof["v"],
            "slant_distance_m": prof["d_cpa"],
            "t_emission_cpa_s": round(t0_cpa, 2),
            "t_observed_cpa_s": round(t_obs_cpa, 2),
            "inflection_slope_hz_s": round(slope_cpa, 3),
            "harmonics_hz": [prof["f0"], 2.0 * prof["f0"], 3.0 * prof["f0"]],
        }
        ground_truth.append(gt_entry)
        
    # Normalize to prevent any clipping: max peak at -1.0 dBFS
    max_peak = np.max(np.abs(audio))
    if max_peak > 0.89:
        audio = audio * (0.89 / max_peak)
        
    if output_path is not None:
        sf.write(output_path, audio, fs, subtype="PCM_16")
        
    return audio, ground_truth
