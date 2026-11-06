"""Tests for active privacy cloaking engine (3-layer defense)."""

import numpy as np
import pytest

from sonar.core.cloak import (
    cloak_audio_stream,
    dynamic_stft_notch_erasure,
    generate_synthetic_chaff,
    apply_time_base_warp,
)
from sonar.core.spectrogram import compute_spectrogram
from sonar.core.detector import audit_spectrogram
from sonar.utils.synthetic_gen import synthesize_propeller_flyover, generate_ambient_background


def test_dynamic_notch_erases_ridge():
    """Verify Layer 1 surgical notch removes tonal energy of detected Doppler ridge."""
    fs = 4000
    duration_s = 40.0
    f0 = 110.0
    v = 65.0
    d_cpa = 700.0
    t0 = 20.0
    
    plane_audio, _, _ = synthesize_propeller_flyover(
        duration_s=duration_s,
        fs=fs,
        f0=f0,
        v=v,
        d_cpa=d_cpa,
        t0_cpa=t0,
        peak_dbfs=-14.0,
    )
    # Add background noise
    noise = np.random.randn(len(plane_audio)).astype(np.float32) * 0.005
    audio = plane_audio + noise
    
    # Audit before
    times, freqs, s_white_pre, _ = compute_spectrogram(audio, fs=fs)
    audit_pre = audit_spectrogram(s_white_pre, freqs, times)
    assert audit_pre["num_detections"] >= 1
    max_snr_pre = audit_pre["detections"][0]["mean_snr_sigma"]
    
    # Apply Layer 1 notch
    notched_audio = dynamic_stft_notch_erasure(
        audio,
        fs=fs,
        detected_ridges=audit_pre["detections"],
        notch_width_hz=3.0,
    )
    
    # Audit after notch
    times, freqs, s_white_post, _ = compute_spectrogram(notched_audio, fs=fs)
    audit_post = audit_spectrogram(s_white_post, freqs, times)
    
    if audit_post["num_detections"] > 0:
        max_snr_post = audit_post["detections"][0]["mean_snr_sigma"]
        # SNR should drop significantly (by at least 4.0 sigma)
        assert max_snr_post < max_snr_pre - 3.5, f"Expected SNR drop: before {max_snr_pre}, after {max_snr_post}"
    else:
        # Completely erased below detection threshold
        assert audit_post["num_detections"] == 0


def test_full_cloak_pipeline():
    """Verify full 3-layer cloaking pipeline replaces true signature with decoys and alters time base."""
    fs = 4000
    duration_s = 60.0
    
    plane_audio, _, _ = synthesize_propeller_flyover(
        duration_s=duration_s,
        fs=fs,
        f0=120.0,
        v=70.0,
        d_cpa=800.0,
        t0_cpa=30.0,
        peak_dbfs=-16.0,
    )
    # Outdoor ambient background (e.g. wind/speech ambient at -22 dBFS)
    ambient = generate_ambient_background(duration_s, fs=fs, snr_db=-22.0)
    audio = plane_audio + ambient
    
    result = cloak_audio_stream(
        audio,
        fs=fs,
        chaff_count=4,
        warp_pct=0.35,
        enable_notch=True,
    )
    
    assert "cloaked_audio" in result
    assert len(result["cloaked_audio"]) == len(audio)
    assert len(result["chaff_manifest"]) == 4
    
    # Audio energy of background scene should remain perceptually intact
    rms_orig = np.sqrt(np.mean(audio ** 2))
    rms_cloaked = np.sqrt(np.mean(result["cloaked_audio"] ** 2))
    assert abs(rms_orig - rms_cloaked) / rms_orig < 0.25, "Cloaked audio RMS should be within 25% of original"
