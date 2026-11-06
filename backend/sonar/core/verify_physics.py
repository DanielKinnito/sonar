"""AI / Synthetic Audio Physics Inspector (Sub-Mode 3B).

Examines Doppler passes in audio to distinguish genuine physical acoustic wave
propagation from neural audio generation (Sora, Veo, ElevenLabs, etc.) or manual pitch bends.
Computes Harmonic Lock Residual (epsilon_harm) and Kinematic Trajectory Fit Residual (epsilon_kin).
"""

from __future__ import annotations

import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from sonar.core.physics import (
    straight_line_doppler,
    compute_harmonic_lock_residual,
    cpa_inflection_slope,
    SPEED_OF_SOUND,
)
from sonar.core.spectrogram import compute_spectrogram, TARGET_FS
from sonar.core.detector import viterbi_ridge_tracker, fit_doppler_curve


def inspect_audio_physics(
    audio: np.ndarray,
    fs: int = TARGET_FS,
    f_min: float = 40.0,
    f_max: float = 450.0,
) -> Dict[str, Any]:
    """Forensically inspect audio for physical acoustic wave propagation fidelity vs AI synthesis.
    
    Returns:
        Dictionary containing verdict, epsilon_harm, epsilon_kin, and physical kinematics report.
    """
    times, freqs, s_white, _ = compute_spectrogram(audio, fs=fs, f_min=f_min, f_max=f_max)
    
    # Extract continuous tonal ridges
    ridges = viterbi_ridge_tracker(s_white, freqs, times)
    if not ridges:
        return {
            "verdict": "INCONCLUSIVE",
            "confidence": 0.30,
            "summary": "No continuous Doppler frequency ridges detected to evaluate physics.",
            "epsilon_harm": None,
            "epsilon_kin": None,
            "passes_evaluated": 0,
        }
        
    evaluated_passes: List[Dict[str, Any]] = []
    
    for idx, (r_times, r_freqs, r_snrs) in enumerate(ridges, start=1):
        # 1. Kinematic Fit Residual (epsilon_kin)
        fit_res = fit_doppler_curve(r_times, r_freqs)
        f_pred = straight_line_doppler(
            r_times,
            fit_res["f0_hz"],
            fit_res["velocity_ms"],
            fit_res["slant_distance_m"],
            fit_res["t_emission_cpa_s"],
        )
        eps_kin = float(np.sqrt(np.mean((f_pred - r_freqs) ** 2)))
        
        # Check for 2nd and 3rd harmonics in the remaining ridges
        eps_harm_list = []
        harm_multipliers = [2.0, 3.0]
        
        for mult in harm_multipliers:
            # Look for companion ridge with frequency ~ mult * fundamental
            target_f = r_freqs * mult
            for (c_times, c_freqs, c_snrs) in ridges:
                # Check time overlap
                t_common_min = max(r_times[0], c_times[0])
                t_common_max = min(r_times[-1], c_times[-1])
                if t_common_max - t_common_min >= 8.0:
                    # Interpolate both onto common time grid
                    t_eval = np.linspace(t_common_min, t_common_max, 50)
                    f1_interp = np.interp(t_eval, r_times, r_freqs)
                    fk_interp = np.interp(t_eval, c_times, c_freqs)
                    
                    mean_ratio = np.mean(fk_interp / f1_interp)
                    if abs(mean_ratio - mult) < 0.2:
                        eps_h = compute_harmonic_lock_residual(f1_interp, fk_interp, int(mult))
                        eps_harm_list.append(eps_h)
                        break
                        
        mean_eps_harm = float(np.mean(eps_harm_list)) if eps_harm_list else None
        
        # Check physical bounds on kinematics
        v_fit = fit_res["velocity_ms"]
        d_fit = fit_res["slant_distance_m"]
        slope_cpa = fit_res["inflection_slope_hz_s"]
        
        # Real subsonic aircraft fly between 25 m/s and 180 m/s
        is_kinematically_sound = (20.0 <= v_fit <= 220.0) and (eps_kin < 0.85)
        
        # Real acoustic rotors maintain epsilon_harm < 0.005 (0.5% drift)
        # AI models regularly exhibit 1.5% to 5% non-physical pitch drift
        is_harmonic_locked = (mean_eps_harm is not None) and (mean_eps_harm < 0.005)
        is_harmonic_drifting = (mean_eps_harm is not None) and (mean_eps_harm >= 0.005)
        
        harm_str = f"ε_harm={mean_eps_harm:.4f}" if mean_eps_harm is not None else "no locked harmonic"
        if is_harmonic_drifting or (not is_kinematically_sound and eps_kin >= 1.2):
            pass_verdict = "AI_GENERATED_OR_MANIPULATED"
            rationale = (
                f"Forensic violation ({harm_str}): exceeds physical 0.005 threshold "
                f"or kinematic fit residual ε_kin={eps_kin:.2f}Hz exhibits synthetic pitch drift."
            )
        elif is_harmonic_locked and is_kinematically_sound:
            pass_verdict = "PHYSICALLY_AUTHENTIC"
            rationale = (
                f"Physical acoustic lock verified: ε_harm={mean_eps_harm:.5f} (< 0.005), "
                f"ε_kin={eps_kin:.2f}Hz conforms to retarded-time wave equation."
            )
        elif is_kinematically_sound:
            pass_verdict = "LIKELY_PHYSICALLY_AUTHENTIC"
            rationale = f"Kinematic curve fits retarded-time equation (ε_kin={eps_kin:.2f}Hz, v={v_fit:.1f}m/s)."
        else:
            pass_verdict = "INCONCLUSIVE"
            rationale = f"Weak curve or ambiguous kinematic residual (ε_kin={eps_kin:.2f}Hz)."
            
        pass_info = {
            "pass_id": f"PASS-{idx:02d}",
            "f0_hz": fit_res["f0_hz"],
            "velocity_ms": v_fit,
            "slant_distance_m": d_fit,
            "inflection_slope_hz_s": slope_cpa,
            "epsilon_kin_hz": round(eps_kin, 3),
            "epsilon_harm": round(mean_eps_harm, 5) if mean_eps_harm is not None else None,
            "has_harmonics": bool(eps_harm_list),
            "verdict": pass_verdict,
            "rationale": rationale,
            "trajectory_points": {
                "times": np.round(r_times, 2).tolist(),
                "freqs": np.round(r_freqs, 2).tolist(),
                "fitted_model_freqs": np.round(f_pred, 2).tolist(),
            }
        }
        evaluated_passes.append(pass_info)
        
    # Aggregate verdict
    if any(p["verdict"] == "AI_GENERATED_OR_MANIPULATED" for p in evaluated_passes):
        overall_verdict = "AI_GENERATED_OR_MANIPULATED"
        confidence = 0.94
        summary = "FORENSIC VIOLATION: Observed audio fails physical acoustic wave propagation or harmonic lock constraints. Characteristic of neural generative synthesis."
    elif any(p["verdict"] == "PHYSICALLY_AUTHENTIC" for p in evaluated_passes):
        overall_verdict = "PHYSICALLY_AUTHENTIC"
        confidence = 0.96
        summary = "PHYSICALLY AUTHENTIC: Audio adheres strictly to 3D retarded-time wave propagation and rotor harmonic frequency locking."
    elif any(p["verdict"] == "LIKELY_PHYSICALLY_AUTHENTIC" for p in evaluated_passes):
        overall_verdict = "LIKELY_PHYSICALLY_AUTHENTIC"
        confidence = 0.82
        summary = "LIKELY AUTHENTIC: Kinematic Doppler inflection matches physical aircraft velocity and slant distance."
    else:
        overall_verdict = "INCONCLUSIVE"
        confidence = 0.40
        summary = "Insufficient acoustic SNR or harmonic structure to definitively determine physical authenticity."
        
    return {
        "verdict": overall_verdict,
        "confidence": confidence,
        "summary": summary,
        "passes_evaluated": len(evaluated_passes),
        "passes": evaluated_passes,
    }
