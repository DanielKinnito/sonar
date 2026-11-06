"""Tests for Doppler ridge tracker and Huber least-squares curve fitter."""

import numpy as np
import pytest

from sonar.core.spectrogram import compute_spectrogram
from sonar.core.detector import audit_spectrogram, fit_doppler_curve
from sonar.utils.synthetic_gen import generate_synthetic_fixture, synthesize_propeller_flyover


def test_detector_recovers_synthetic_parameters():
    """Verify that detector recovers aircraft f0, velocity, and d_cpa within 3-5% of ground truth."""
    fs = 4000
    duration_s = 60.0
    gt_f0 = 100.0       # Hz
    gt_v = 60.0         # m/s
    gt_d_cpa = 600.0    # m
    gt_t0 = 30.0        # s
    
    # Generate clean single-plane flyover with subtle background
    plane_audio, t_obs, f_curve = synthesize_propeller_flyover(
        duration_s=duration_s,
        fs=fs,
        f0=gt_f0,
        v=gt_v,
        d_cpa=gt_d_cpa,
        t0_cpa=gt_t0,
        peak_dbfs=-12.0,
    )
    # Add gentle pink noise floor
    noise = np.random.randn(len(plane_audio)).astype(np.float32) * 0.005
    audio = plane_audio + noise
    
    times, freqs, s_white, _ = compute_spectrogram(audio, fs=fs)
    audit_res = audit_spectrogram(s_white, freqs, times)
    
    assert audit_res["num_detections"] >= 1, "Detector should detect at least one Doppler ridge"
    best_det = audit_res["detections"][0]
    fitted = best_det["fitted_params"]
    
    assert fitted["success"] is True
    # f0 recovered within 3%
    f0_err = abs(fitted["f0_hz"] - gt_f0) / gt_f0
    assert f0_err < 0.03, f"f0 relative error {f0_err*100:.2f}% (got {fitted['f0_hz']} vs {gt_f0})"
    
    # Velocity recovered within 5%
    v_err = abs(fitted["velocity_ms"] - gt_v) / gt_v
    assert v_err < 0.05, f"Velocity relative error {v_err*100:.2f}% (got {fitted['velocity_ms']} vs {gt_v})"
    
    # Slant distance recovered within 5%
    d_err = abs(fitted["slant_distance_m"] - gt_d_cpa) / gt_d_cpa
    assert d_err < 0.05, f"Slant distance relative error {d_err*100:.2f}% (got {fitted['slant_distance_m']} vs {gt_d_cpa})"
    
    # Risk score should be CRITICAL or MODERATE
    assert audit_res["risk_level"] in ["CRITICAL", "MODERATE"]


def test_multi_plane_fixture_audit():
    """Verify that multi-plane synthetic fixture generates multiple detections and flags CRITICAL risk."""
    audio, ground_truth = generate_synthetic_fixture(
        duration_s=90.0,
        fs=4000,
        num_planes=2,
        seed=123,
    )
    
    times, freqs, s_white, _ = compute_spectrogram(audio, fs=4000)
    audit_res = audit_spectrogram(s_white, freqs, times)
    
    assert audit_res["num_detections"] >= 2
    assert audit_res["risk_level"] == "CRITICAL"
