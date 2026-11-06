"""Tests for Spatiotemporal Alibi Verifier and AI Physics Inspector."""

import numpy as np
import pytest
from datetime import datetime, timezone

from sonar.core.verify_alibi import verify_spatiotemporal_alibi
from sonar.core.verify_physics import inspect_audio_physics
from sonar.core.physics import geodetic_to_ecef, ecef_to_enu, straight_line_doppler
from sonar.utils.synthetic_gen import synthesize_propeller_flyover, generate_ambient_background


def test_verify_alibi_match_and_silence_violation():
    """Verify alibi verifier detects positive matches and flags silence violations."""
    fs = 4000
    duration_s = 60.0
    ref_lat = 37.7749
    ref_lon = -122.4194
    t0_ref = datetime(2026, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
    t0_epoch = t0_ref.timestamp()
    
    # 1. Synthesize audio with an aircraft passing at CPA at T+30s, f0 = 92.5 Hz, v = 60 m/s, d_cpa = 600m
    plane_audio, _, _ = synthesize_propeller_flyover(
        duration_s=duration_s,
        fs=fs,
        f0=92.5,
        v=60.0,
        d_cpa=600.0,
        t0_cpa=30.0,
        peak_dbfs=-14.0,
    )
    ambient = generate_ambient_background(duration_s, fs=fs, snr_db=-34.0)
    audio_with_plane = plane_audio + ambient
    
    # Construct matching ADS-B flight trace in ENU coordinates
    t_flight = np.linspace(0.0, 60.0, 31)
    # Observer is at (0, 0, 0) relative to ref_lat, ref_lon
    # Flight passes directly overhead at altitude 600m, speed 60 m/s Eastbound
    enu_pts = np.zeros((len(t_flight), 3))
    enu_pts[:, 0] = 60.0 * (t_flight - 30.0)  # East
    enu_pts[:, 1] = 0.0                       # North
    enu_pts[:, 2] = 600.0                     # Up (600m)
    
    # Convert ENU back to approximate lat/lon
    # 1 deg lat ~ 111000m, 1 deg lon ~ 111000 * cos(lat)
    cos_lat = np.cos(np.radians(ref_lat))
    flight_points = []
    for idx, t_val in enumerate(t_flight):
        d_east = enu_pts[idx, 0]
        d_north = enu_pts[idx, 1]
        p_lat = ref_lat + (d_north / 111000.0)
        p_lon = ref_lon + (d_east / (111000.0 * cos_lat))
        
        flight_points.append({
            "t_epoch_s": t0_epoch + t_val,
            "lat": p_lat,
            "lon": p_lon,
            "alt_m": 600.0,
            "speed_ms": 60.0,
        })
        
    mock_trace = [{
        "flight_id": "TEST-C172",
        "hex": "A1B2C3",
        "icao_type": "C172",
        "is_prop_or_rotor": True,
        "points": flight_points,
    }]
    
    # Test positive match
    res_match = verify_spatiotemporal_alibi(
        audio=audio_with_plane,
        fs=fs,
        lat=ref_lat,
        lon=ref_lon,
        utc_iso=t0_ref.isoformat(),
        flight_traces=mock_trace,
    )
    assert res_match["verdict"] == "VERIFIED_MATCH"
    assert res_match["best_match"]["alignment_score_sigma"] >= 3.8
    
    # Test silence violation: feed quiet ambient audio where plane SHOULD have been heard
    quiet_audio = generate_ambient_background(duration_s, fs=fs, snr_db=-34.0)
    res_silence = verify_spatiotemporal_alibi(
        audio=quiet_audio,
        fs=fs,
        lat=ref_lat,
        lon=ref_lon,
        utc_iso=t0_ref.isoformat(),
        flight_traces=mock_trace,
    )
    assert res_silence["verdict"] == "CONTRADICTION_SILENCE_VIOLATION"


def test_verify_physics_ai_pitch_drift():
    """Verify that verify_physics separates authentic physical harmonic passes from AI drift."""
    fs = 4000
    duration_s = 45.0
    
    # Authentic physical pass with 3 locked harmonics
    plane_audio, _, _ = synthesize_propeller_flyover(
        duration_s=duration_s,
        fs=fs,
        f0=100.0,
        v=60.0,
        d_cpa=500.0,
        t0_cpa=22.0,
        harmonic_weights=(1.0, 0.5, 0.25),
        peak_dbfs=-14.0,
    )
    noise = np.random.randn(len(plane_audio)).astype(np.float32) * 0.005
    authentic_audio = plane_audio + noise
    
    res_auth = inspect_audio_physics(authentic_audio, fs=fs)
    assert res_auth["verdict"] in ["PHYSICALLY_AUTHENTIC", "LIKELY_PHYSICALLY_AUTHENTIC"]
    
    # AI / neural generative pass: non-physical harmonic drift between fundamental and 2nd harmonic
    t = np.arange(len(plane_audio)) / float(fs)
    f_fund = straight_line_doppler(t, 100.0, 60.0, 500.0, 22.0)
    # Drift factor 2.5% oscillation
    drift = 1.0 + 0.025 * np.sin(2.0 * np.pi * t / 6.0)
    f_harm_ai = 2.0 * f_fund * drift
    
    phi1 = 2.0 * np.pi * np.cumsum(f_fund) / float(fs)
    phi2 = 2.0 * np.pi * np.cumsum(f_harm_ai) / float(fs)
    
    ai_wave = (0.7 * np.sin(phi1) + 0.35 * np.sin(phi2)).astype(np.float32)
    ai_audio = ai_wave * 0.2 + noise
    
    res_ai = inspect_audio_physics(ai_audio, fs=fs)
    assert res_ai["verdict"] in ["AI_GENERATED_OR_MANIPULATED", "INCONCLUSIVE"]
