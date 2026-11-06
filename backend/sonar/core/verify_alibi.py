"""Spatiotemporal Alibi Verifier (Sub-Mode 3A).

Correlates media recording against historical ADS-B flight trajectories and
AWS Terrarium DEM ground elevations. 3D retarded-time forward modeling predicts
expected acoustic curves and identifies forensic acoustic matches or Silence Violations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from sonar.core.physics import (
    geodetic_to_ecef,
    ecef_to_enu,
    trajectory_3d_doppler,
    SPEED_OF_SOUND,
)
from sonar.core.spectrogram import compute_spectrogram, TARGET_FS
from sonar.data.elevation import ElevationProvider
from sonar.data.adsb import ADSBProvider


def score_curve_on_spectrogram(
    t_curve: np.ndarray,
    f_curve: np.ndarray,
    s_white: np.ndarray,
    time_grid: np.ndarray,
    freq_grid: np.ndarray,
) -> float:
    """Calculate mean whitened STFT energy along a modeled Doppler curve."""
    dt = float(time_grid[1] - time_grid[0])
    df = float(freq_grid[1] - freq_grid[0])
    
    # Overlap with spectrogram bounds
    mask = (
        (t_curve >= time_grid[0]) & (t_curve <= time_grid[-1]) &
        (f_curve >= freq_grid[0]) & (f_curve <= freq_grid[-1])
    )
    if np.sum(mask) < 8:
        return 0.0
        
    valid_t = t_curve[mask]
    valid_f = f_curve[mask]
    
    t_indices = np.clip(np.round((valid_t - time_grid[0]) / dt).astype(int), 0, s_white.shape[1] - 1)
    f_indices = np.clip(np.round((valid_f - freq_grid[0]) / df).astype(int), 0, s_white.shape[0] - 1)
    
    samples = s_white[f_indices, t_indices]
    return float(np.mean(samples))


def verify_spatiotemporal_alibi(
    audio: np.ndarray,
    fs: int = TARGET_FS,
    lat: float = 37.7749,
    lon: float = -122.4194,
    utc_iso: Optional[str] = None,
    search_radius_km: float = 15.0,
    flight_traces: Optional[List[Dict[str, Any]]] = None,
    elevation_provider: Optional[ElevationProvider] = None,
    adsb_provider: Optional[ADSBProvider] = None,
) -> Dict[str, Any]:
    """Execute Sub-Mode 3A Spatiotemporal Alibi Verification.
    
    Parameters:
        audio: Audio float32 array
        fs: Sampling rate (default 4000 Hz)
        lat: Claimed observer latitude
        lon: Claimed observer longitude
        utc_iso: Claimed start timestamp in UTC ISO-8601
        search_radius_km: Search radius in km (default 15 km)
        flight_traces: Optional pre-loaded flight traces (from GeoJSON/CSV)
        elevation_provider: Optional ElevationProvider instance
        adsb_provider: Optional ADSBProvider instance
    """
    elev_prov = elevation_provider or ElevationProvider()
    adsb_prov = adsb_provider or ADSBProvider()
    
    # 1. Ground elevation at observer coordinate
    observer_alt_m = elev_prov.get_elevation_m(lat, lon)
    
    # 2. Compute whitened spectrogram of media
    time_grid, freq_grid, s_white, _ = compute_spectrogram(audio, fs=fs)
    rec_duration_s = float(time_grid[-1] - time_grid[0]) if len(time_grid) > 1 else 0.0
    
    # Parse UTC timestamp
    if utc_iso:
        try:
            t_ref_dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        except Exception:
            t_ref_dt = datetime.now(timezone.utc)
    else:
        t_ref_dt = datetime.now(timezone.utc)
    t_ref_epoch = t_ref_dt.timestamp()
    
    # 3. Retrieve flight traces if not provided
    if flight_traces is None:
        flight_traces = adsb_prov.query_adsb_lol(lat, lon, radius_km=search_radius_km, utc_time=t_ref_dt)
        
    evaluated_flights: List[Dict[str, Any]] = []
    has_silence_violation = False
    silence_violation_details = []
    best_match: Optional[Dict[str, Any]] = None
    max_alignment_score = 0.0
    
    candidate_fundamentals = [80.0, 92.5, 105.0, 118.0, 135.0, 150.0]
    
    for fl in flight_traces:
        pts = fl.get("points", [])
        if len(pts) < 4:
            continue
            
        t_epochs = np.array([p["t_epoch_s"] for p in pts], dtype=np.float64)
        t_relative = t_epochs - t_ref_epoch
        
        # Check if flight was within time window of the recording
        if t_relative[-1] < -30.0 or t_relative[0] > rec_duration_s + 30.0:
            continue
            
        # Convert aircraft coordinates to ECEF and ENU
        enu_list = []
        for p in pts:
            ecef = geodetic_to_ecef(p["lat"], p["lon"], p["alt_m"])
            enu = ecef_to_enu(ecef, lat, lon, observer_alt_m)
            enu_list.append(enu)
        enu_arr = np.array(enu_list, dtype=np.float64)
        
        # Calculate 3D slant distances
        distances = np.sqrt(np.sum(enu_arr ** 2, axis=1))
        min_slant_m = float(np.min(distances))
        min_dist_idx = int(np.argmin(distances))
        t_cpa_rel = float(t_relative[min_dist_idx])
        
        # If aircraft was outside acoustic detection envelope (> 12 km), skip
        if min_slant_m > 12000.0:
            continue
            
        # Forward model Doppler curve for candidate prop blade fundamentals
        best_f0 = 105.0
        best_score = 0.0
        best_curve_t = np.array([])
        best_curve_f = np.array([])
        
        for f0_cand in candidate_fundamentals:
            try:
                t_obs_model, f_obs_model = trajectory_3d_doppler(
                    t_relative,
                    enu_arr,
                    f0=f0_cand,
                )
                score = score_curve_on_spectrogram(t_obs_model, f_obs_model, s_white, time_grid, freq_grid)
                if score > best_score:
                    best_score = score
                    best_f0 = f0_cand
                    best_curve_t = t_obs_model
                    best_curve_f = f_obs_model
            except Exception:
                continue
                
        is_acoustic_match = best_score >= 3.8
        
        # Check Silence Violation: Low-altitude flyover (< 1000m) directly overhead during recording but zero acoustic energy (< 1.4 sigma)
        is_close_pass = (min_slant_m <= 1000.0) and (0.0 <= t_cpa_rel <= rec_duration_s)
        is_silence_violation = is_close_pass and (best_score < 1.4)
        
        if is_silence_violation:
            has_silence_violation = True
            silence_violation_details.append({
                "flight_id": fl.get("flight_id", "AC"),
                "min_slant_m": round(min_slant_m, 1),
                "t_cpa_s": round(t_cpa_rel, 1),
                "measured_snr_sigma": round(best_score, 2),
                "expected_snr_sigma": 8.0,
            })
            
        fl_record = {
            "flight_id": fl.get("flight_id", "UNKNOWN"),
            "hex": fl.get("hex", "unknown"),
            "icao_type": fl.get("icao_type", "PROP"),
            "min_slant_m": round(min_slant_m, 1),
            "t_cpa_relative_s": round(t_cpa_rel, 2),
            "best_f0_hz": best_f0,
            "alignment_score_sigma": round(best_score, 2),
            "is_acoustic_match": is_acoustic_match,
            "is_silence_violation": is_silence_violation,
            "modeled_curve": {
                "times": np.round(best_curve_t, 2).tolist() if len(best_curve_t) > 0 else [],
                "freqs": np.round(best_curve_f, 2).tolist() if len(best_curve_f) > 0 else [],
            }
        }
        evaluated_flights.append(fl_record)
        
        if best_score > max_alignment_score:
            max_alignment_score = best_score
            best_match = fl_record
            
    # Formulate verdict
    if has_silence_violation:
        verdict = "CONTRADICTION_SILENCE_VIOLATION"
        confidence = 0.92
        summary = (
            f"SILENCE VIOLATION DETECTED: Historical flight {silence_violation_details[0]['flight_id']} "
            f"passed at {silence_violation_details[0]['min_slant_m']}m overhead at T+{silence_violation_details[0]['t_cpa_s']}s, "
            f"but media spectrogram contains zero trace ({silence_violation_details[0]['measured_snr_sigma']}σ vs expected ≥8.0σ). "
            "Recording was almost certainly not recorded at this location/time."
        )
    elif max_alignment_score >= 3.8 and best_match is not None:
        verdict = "VERIFIED_MATCH"
        confidence = 0.95
        summary = (
            f"ACOUSTIC ALIBI CONFIRMED: Aircraft {best_match['flight_id']} ({best_match['icao_type']}) "
            f"Doppler trajectory precisely matches the recording at {best_match['min_slant_m']}m slant range "
            f"(alignment SNR: {max_alignment_score:.1f}σ)."
        )
    elif len(evaluated_flights) == 0:
        verdict = "UNVERIFIABLE_QUIET_SKY"
        confidence = 0.50
        summary = "No propeller/rotorcraft flight tracks occurred within the 15km acoustic envelope during this time window."
    else:
        verdict = "INCONCLUSIVE"
        confidence = 0.45
        summary = f"Evaluated {len(evaluated_flights)} aircraft; no definitive acoustic match or silence violation established."
        
    return {
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "claimed_coordinates": {
            "lat": lat,
            "lon": lon,
            "observer_elevation_m": round(observer_alt_m, 1),
            "utc_time": t_ref_dt.isoformat(),
        },
        "num_flights_evaluated": len(evaluated_flights),
        "evaluated_flights": evaluated_flights,
        "best_match": best_match,
    }
