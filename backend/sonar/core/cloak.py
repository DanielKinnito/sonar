"""Active Privacy Cloaking Engine for Acoustic Geolocation Countermeasures.

Implements a 3-layer defense against ADS-B acoustic geolocation tools:
  Layer 1 - Dynamic Time-Varying Spectral Notch (Surgical Erasure)
  Layer 2 - Phase-Continuous Synthetic Chaff Injection (Poisoning Search)
  Layer 3 - Sub-Perceptual Time-Base & Pitch Warping (Breaking Geometry Scoring)
"""

from __future__ import annotations

import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from scipy import signal
from scipy.interpolate import interp1d

from sonar.core.physics import straight_line_doppler, solve_emission_times_straight_line, SPEED_OF_SOUND
from sonar.core.spectrogram import compute_spectrogram, TARGET_FS, N_PER_SEG, N_FFT, HOP_LENGTH
from sonar.core.detector import audit_spectrogram


def dynamic_stft_notch_erasure(
    audio: np.ndarray,
    fs: int,
    detected_ridges: List[Dict[str, Any]],
    notch_width_hz: float = 2.5,
    bg_annulus_hz: float = 8.0,
) -> np.ndarray:
    """Layer 1: Apply dynamic time-varying spectral notch along detected Doppler ridges and harmonics.
    
    Replaces narrowband tonal ridge energy with randomized phase and local background noise floor,
    reducing ridge SNR to 0 dB relative to adjacent bins.
    """
    if not detected_ridges:
        return np.copy(audio)
        
    n_per_seg = 2048
    n_overlap = 1536
    n_fft = 8192  # 8k FFT for ~0.48 Hz bin resolution
    window = signal.windows.hann(n_per_seg, sym=False)
    
    freqs, times, stft_matrix = signal.stft(
        audio,
        fs=fs,
        window=window,
        nperseg=n_per_seg,
        noverlap=n_overlap,
        nfft=n_fft,
        boundary="zeros",
        padded=True,
    )
    
    # stft_matrix has shape (n_freqs, n_times)
    n_freqs, n_times = stft_matrix.shape
    df = float(freqs[1] - freqs[0])
    
    for det in detected_ridges:
        model = det.get("fitted_params", {})
        if not model.get("success", False):
            continue
            
        f0 = model["f0_hz"]
        v = model["velocity_ms"]
        d_cpa = model["slant_distance_m"]
        t0 = model["t_emission_cpa_s"]
        
        # Determine active observation time range
        t_start = det["start_time_s"]
        t_end = det["end_time_s"]
        
        active_t_mask = (times >= t_start - 1.0) & (times <= t_end + 1.0)
        t_active = times[active_t_mask]
        if len(t_active) == 0:
            continue
            
        # Compute exact Doppler curves for fundamental and harmonics (k = 1, 2, 3, and 0.5)
        f_obs_fund = straight_line_doppler(t_active, f0, v, d_cpa, t0)
        harmonic_multipliers = [1.0, 2.0, 3.0, 0.5]
        
        for mult in harmonic_multipliers:
            f_obs_harm = f_obs_fund * mult
            
            for t_sub_idx, (t_val, f_center) in enumerate(zip(t_active, f_obs_harm)):
                if f_center < freqs[0] or f_center > freqs[-1]:
                    continue
                    
                t_idx = np.where(active_t_mask)[0][t_sub_idx]
                
                # Notch band bins: [f_center - 2.5, f_center + 2.5]
                notch_low = max(0, int(np.floor((f_center - notch_width_hz - freqs[0]) / df)))
                notch_high = min(n_freqs, int(np.ceil((f_center + notch_width_hz - freqs[0]) / df)) + 1)
                
                # Reference background floor bins: [f_center - 8.0, f_center - 3.5] and [f_center + 3.5, f_center + 8.0]
                bg_low1 = max(0, int(np.floor((f_center - bg_annulus_hz - freqs[0]) / df)))
                bg_high1 = max(0, int(np.ceil((f_center - 3.5 - freqs[0]) / df)))
                bg_low2 = min(n_freqs, int(np.floor((f_center + 3.5 - freqs[0]) / df)))
                bg_high2 = min(n_freqs, int(np.ceil((f_center + bg_annulus_hz - freqs[0]) / df)) + 1)
                
                ref_bins = []
                if bg_high1 > bg_low1:
                    ref_bins.extend(range(bg_low1, bg_high1))
                if bg_high2 > bg_low2:
                    ref_bins.extend(range(bg_low2, bg_high2))
                    
                if len(ref_bins) > 0:
                    bg_mags = np.abs(stft_matrix[ref_bins, t_idx])
                    median_bg = float(np.median(bg_mags))
                else:
                    median_bg = float(np.abs(stft_matrix[notch_low, t_idx]) * 0.1)
                    
                # Replace notch bins with randomized phase and background magnitude floor
                num_notch = notch_high - notch_low
                random_phases = np.random.uniform(0.0, 2.0 * np.pi, size=num_notch)
                stft_matrix[notch_low:notch_high, t_idx] = median_bg * np.exp(1j * random_phases)
                
    # Inverse STFT
    _, audio_erased = signal.istft(
        stft_matrix,
        fs=fs,
        window=window,
        nperseg=n_per_seg,
        noverlap=n_overlap,
        nfft=n_fft,
    )
    
    # Match length of original audio
    if len(audio_erased) > len(audio):
        audio_erased = audio_erased[:len(audio)]
    elif len(audio_erased) < len(audio):
        audio_erased = np.pad(audio_erased, (0, len(audio) - len(audio_erased)))
        
    return audio_erased.astype(np.float32)


def generate_synthetic_chaff(
    duration_s: float,
    fs: int,
    num_chaff: int = 5,
    snr_dbfs: float = -50.0,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Layer 2: Synthesize phase-continuous fake propeller flyover curves to poison search & silence filters.
    
    Parameters:
        duration_s: Length of audio (seconds)
        fs: Sample rate (Hz)
        num_chaff: Number of fake decoys to inject (default 5)
        snr_dbfs: Target RMS level (-48 to -54 dBFS)
        seed: Random seed for repeatability
    """
    if seed is not None:
        np.random.seed(seed)
        
    n_samples = int(duration_s * fs)
    t_obs = np.arange(n_samples, dtype=np.float64) / float(fs)
    chaff_audio = np.zeros(n_samples, dtype=np.float64)
    chaff_manifest: List[Dict[str, Any]] = []
    
    # Space CPA timestamps across the duration to break multi-event delta-t offsets
    cpa_slots = np.linspace(duration_s * 0.15, duration_s * 0.85, num_chaff)
    
    for i in range(num_chaff):
        # Realistic parameters within general aviation envelope
        f0 = float(np.random.uniform(75.0, 165.0))
        v = float(np.random.uniform(45.0, 120.0))
        d_cpa = float(np.random.uniform(500.0, 2800.0))
        t0 = float(cpa_slots[i] + np.random.uniform(-4.0, 4.0))
        
        # Add subtle flight path curvature (slight acceleration)
        omega_a = 2.0 * np.pi / float(np.random.uniform(40.0, 90.0))
        a0 = float(np.random.uniform(0.5, 2.5))
        
        # Base straight-line Doppler
        f_obs = straight_line_doppler(t_obs, f0, v, d_cpa, t0)
        # Curvature perturbation
        f_obs = f_obs + (a0 / SPEED_OF_SOUND) * f0 * np.sin(omega_a * (t_obs - t0))
        
        # Phase integration
        dt = 1.0 / float(fs)
        phase_fund = 2.0 * np.pi * np.cumsum(f_obs) * dt
        
        # Envelope: geometric spreading + Tukey window
        t_e = solve_emission_times_straight_line(t_obs, t0, v, d_cpa)
        r = np.sqrt((v * (t_e - t0)) ** 2 + d_cpa ** 2)
        envelope = d_cpa / r
        
        # Window near edges
        taper_len = int(0.08 * n_samples)
        if taper_len > 1:
            taper = np.hanning(2 * taper_len)
            envelope[:taper_len] *= taper[:taper_len]
            envelope[-taper_len:] *= taper[taper_len:]
            
        weights = [1.0, 0.45, 0.20]
        phases = np.random.uniform(0.0, 2.0 * np.pi, size=3)
        decoy_signal = np.zeros(n_samples, dtype=np.float64)
        for k_idx, (w, phi0) in enumerate(zip(weights, phases), start=1):
            decoy_signal += w * np.sin(float(k_idx) * phase_fund + phi0)
            
        decoy_signal *= envelope
        
        # Scale to target dBFS
        rms = np.sqrt(np.mean(decoy_signal ** 2))
        target_rms = 10.0 ** (snr_dbfs / 20.0)
        if rms > 1e-9:
            decoy_signal = decoy_signal * (target_rms / rms)
            
        chaff_audio += decoy_signal
        chaff_manifest.append({
            "chaff_id": f"DECOY-{i+1:02d}",
            "f0_hz": round(f0, 2),
            "velocity_ms": round(v, 2),
            "slant_distance_m": round(d_cpa, 1),
            "t0_cpa_s": round(t0, 2),
            "level_dbfs": snr_dbfs,
        })
        
    return chaff_audio.astype(np.float32), chaff_manifest


def apply_time_base_warp(
    audio: np.ndarray,
    fs: int,
    warp_pct: float = 0.35,
    t_warp_period: float = 22.0,
    seed: Optional[int] = 42,
) -> np.ndarray:
    """Layer 3: Sub-perceptual time-base & pitch warping.
    
    Smoothly oscillates playback rate by +/- warp_pct% over 18-28s windows.
    Alters df/dt slopes and breaks locked multi-event temporal offsets.
    """
    if seed is not None:
        np.random.seed(seed)
        
    n_samples = len(audio)
    t = np.arange(n_samples, dtype=np.float64) / float(fs)
    
    # Delta tau max to achieve exact speed drift delta = warp_pct / 100.0
    delta = warp_pct / 100.0
    omega = 2.0 * np.pi / t_warp_period
    delta_tau_max = delta / omega
    phi0 = float(np.random.uniform(0.0, 2.0 * np.pi))
    
    # Boundary taper so time-shift smoothly begins and ends at exactly 0.0s (no extrapolation artifacts)
    boundary_window = np.sin(np.pi * t / t[-1]) ** 2
    delta_tau = delta_tau_max * np.sin(omega * t + phi0) * boundary_window
    
    # Warp mapping tau(t) strictly clamped inside [0, t[-1]]
    tau = np.clip(t + delta_tau, 0.0, t[-1])
    
    # Resample audio from t grid onto tau grid via linear/cubic interpolation
    interpolator = interp1d(t, audio, kind="linear", bounds_error=False, fill_value=(audio[0], audio[-1]))
    warped_audio = interpolator(tau).astype(np.float32)
    
    return warped_audio


def cloak_audio_stream(
    audio: np.ndarray,
    fs: int = TARGET_FS,
    chaff_count: int = 5,
    warp_pct: float = 0.35,
    enable_notch: bool = True,
    chaff_dbfs: float = -50.0,
) -> Dict[str, Any]:
    """Execute complete 3-layer privacy cloaking pipeline on audio array.
    
    Returns:
        Dictionary containing cloaked audio array, before/after leak audits, and chaff manifest.
    """
    duration_s = float(len(audio)) / float(fs)
    
    # 1. Pre-cloak audit
    times_pre, freqs_pre, s_white_pre, _ = compute_spectrogram(audio, fs=fs)
    audit_pre = audit_spectrogram(s_white_pre, freqs_pre, times_pre)
    
    work_audio = np.copy(audio)
    
    # 2. Layer 1: Dynamic STFT Notch Surgical Erasure
    if enable_notch and audit_pre["num_detections"] > 0:
        work_audio = dynamic_stft_notch_erasure(
            work_audio,
            fs=fs,
            detected_ridges=audit_pre["detections"],
        )
        
    # 3. Layer 2: Phase-Continuous Synthetic Chaff Injection
    chaff_audio, chaff_manifest = generate_synthetic_chaff(
        duration_s=duration_s,
        fs=fs,
        num_chaff=chaff_count,
        snr_dbfs=chaff_dbfs,
    )
    work_audio = work_audio + chaff_audio
    
    # 4. Layer 3: Sub-perceptual time-base warping
    if warp_pct > 0.0:
        work_audio = apply_time_base_warp(work_audio, fs=fs, warp_pct=warp_pct)
        
    # Prevent clipping
    max_peak = np.max(np.abs(work_audio))
    if max_peak > 0.95:
        work_audio = work_audio * (0.95 / max_peak)
        
    # 5. Post-cloak self-audit verification
    times_post, freqs_post, s_white_post, _ = compute_spectrogram(work_audio, fs=fs)
    audit_post = audit_spectrogram(s_white_post, freqs_post, times_post)
    
    return {
        "cloaked_audio": work_audio,
        "fs": fs,
        "duration_s": duration_s,
        "audit_before": audit_pre,
        "audit_after": audit_post,
        "chaff_manifest": chaff_manifest,
        "layers_applied": {
            "dynamic_notch": enable_notch and audit_pre["num_detections"] > 0,
            "synthetic_chaff_count": chaff_count,
            "time_warp_pct": warp_pct,
        }
    }
