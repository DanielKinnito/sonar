"""Automated Doppler Ridge Extraction, Viterbi Dynamic Programming, and Huber Curve Fitter.

Scans whitened STFT spectrograms for continuous narrowband Doppler signatures,
fits the exact retarded-time acoustic Doppler equation to each curve, boosts
confidence using harmonic stacks, and computes leak risk levels.
"""

from __future__ import annotations

import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from scipy.optimize import least_squares

from sonar.core.physics import straight_line_doppler, cpa_inflection_slope, SPEED_OF_SOUND

# Detection thresholds
MIN_RIDGE_DURATION_S: float = 12.0
MIN_MEAN_SNR_SIGMA: float = 3.0
MIN_TOTAL_FREQ_DROP_HZ: float = 4.0
MAX_FREQ_JUMP_HZ_PER_S: float = 3.5


class DopplerRidge:
    """Represents a continuous acoustic frequency ridge tracked across time."""
    def __init__(
        self,
        times: np.ndarray,
        freqs: np.ndarray,
        snrs: np.ndarray,
    ):
        self.times = np.asarray(times, dtype=np.float64)
        self.freqs = np.asarray(freqs, dtype=np.float64)
        self.snrs = np.asarray(snrs, dtype=np.float64)
        self.duration_s = float(self.times[-1] - self.times[0]) if len(self.times) > 1 else 0.0
        self.mean_snr = float(np.mean(self.snrs)) if len(self.snrs) > 0 else 0.0
        self.max_snr = float(np.max(self.snrs)) if len(self.snrs) > 0 else 0.0
        self.freq_drop = float(self.freqs[0] - self.freqs[-1]) if len(self.freqs) > 1 else 0.0


def viterbi_ridge_tracker(
    s_white: np.ndarray,
    freq_grid: np.ndarray,
    time_grid: np.ndarray,
    lambda_smooth: float = 0.35,
    downward_bias: float = 0.15,
) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Extract candidate continuous frequency ridges using dynamic programming.
    
    Parameters:
        s_white: 2D array (n_freqs, n_times) of whitened STFT SNR in sigma
        freq_grid: 1D array of frequency bins (Hz)
        time_grid: 1D array of time stamps (seconds)
        lambda_smooth: Penalty multiplier for frequency jumps between frames
        downward_bias: Penalty multiplier for upward frequency steps (Doppler slopes are <= 0)
        
    Returns:
        List of (times, freqs, snrs) tuples for detected ridges.
    """
    n_freqs, n_times = s_white.shape
    if n_times < 10 or n_freqs < 10:
        return []
        
    dt = float(time_grid[1] - time_grid[0]) if n_times > 1 else 0.25
    df = float(freq_grid[1] - freq_grid[0]) if n_freqs > 1 else 0.25
    
    # Maximum bin jump per time step
    max_jump_hz = MAX_FREQ_JUMP_HZ_PER_S * dt
    max_jump_bins = max(1, int(np.ceil(max_jump_hz / df)))
    
    # Work on a copy to allow iterative extraction & ribbon suppression
    s_work = np.copy(s_white)
    extracted_ridges: List[Tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    
    # Extract up to 10 prominent ridges
    for _ in range(10):
        # Peak SNR in remaining spectrogram
        max_val = np.max(s_work)
        if max_val < MIN_MEAN_SNR_SIGMA:
            break
            
        # Viterbi forward pass vectorized across candidate delta jumps
        cost = np.zeros((n_freqs, n_times), dtype=np.float32)
        parent = np.zeros((n_freqs, n_times), dtype=np.int32)
        
        cost[:, 0] = s_work[:, 0]
        
        # Possible offsets d = j - i where j is prev_bin, i is curr_bin
        # So prev_bin = curr_bin + d
        possible_d = np.arange(-max_jump_bins, max_jump_bins + 1, dtype=np.int32)
        n_candidates = len(possible_d)
        
        # Precompute penalties for each offset d
        # Frequency change: f_curr - f_prev = -d * df
        freq_diffs = -possible_d * df
        base_penalties = lambda_smooth * (freq_diffs ** 2)
        upward_mask = freq_diffs > 0
        base_penalties[upward_mask] += downward_bias * freq_diffs[upward_mask]
        
        for t in range(1, n_times):
            prev_cost = cost[:, t - 1]
            curr_s = s_work[:, t]
            
            # Candidate matrix: shape (n_candidates, n_freqs)
            cand_scores = np.full((n_candidates, n_freqs), -1e9, dtype=np.float32)
            cand_prev_bins = np.zeros((n_candidates, n_freqs), dtype=np.int32)
            
            for k, d in enumerate(possible_d):
                # prev_bin j = i + d
                # We need 0 <= i + d < n_freqs  =>  -d <= i < n_freqs - d
                i_min = max(0, -d)
                i_max = min(n_freqs, n_freqs - d)
                if i_max > i_min:
                    j_min = i_min + d
                    j_max = i_max + d
                    cand_scores[k, i_min:i_max] = prev_cost[j_min:j_max] - base_penalties[k]
                    cand_prev_bins[k, i_min:i_max] = np.arange(j_min, j_max, dtype=np.int32)
                    
            best_cand_idx = np.argmax(cand_scores, axis=0)  # shape (n_freqs,)
            best_scores = np.take_along_axis(cand_scores, best_cand_idx[None, :], axis=0)[0]
            best_parents = np.take_along_axis(cand_prev_bins, best_cand_idx[None, :], axis=0)[0]
            
            cost[:, t] = best_scores + curr_s
            parent[:, t] = best_parents
                
        # Find best end bin at the final frame or frame with maximum score
        best_t = n_times - 1
        best_f = int(np.argmax(cost[:, best_t]))
        
        # Backtrack path
        path_bins = np.zeros(n_times, dtype=np.int32)
        path_bins[best_t] = best_f
        for t in range(best_t - 1, -1, -1):
            path_bins[t] = parent[path_bins[t + 1], t + 1]
            
        path_freqs = freq_grid[path_bins]
        path_snrs = np.array([s_work[path_bins[t], t] for t in range(n_times)])
        
        # Segment path into contiguous high-SNR runs (where SNR >= 2.0 sigma)
        valid = path_snrs >= 2.0
        # Find contiguous segments
        diff = np.diff(valid.astype(np.int32))
        starts = np.where(diff == 1)[0] + 1
        ends = np.where(diff == -1)[0]
        if valid[0]:
            starts = np.r_[0, starts]
        if valid[-1]:
            ends = np.r_[ends, n_times - 1]
            
        found_valid_segment = False
        for s_idx, e_idx in zip(starts, ends):
            seg_len_s = (e_idx - s_idx) * dt
            if seg_len_s >= MIN_RIDGE_DURATION_S:
                seg_times = time_grid[s_idx:e_idx + 1]
                seg_freqs = path_freqs[s_idx:e_idx + 1]
                seg_snrs = path_snrs[s_idx:e_idx + 1]
                
                total_drop = seg_freqs[0] - seg_freqs[-1]
                mean_snr = np.mean(seg_snrs)
                
                if mean_snr >= MIN_MEAN_SNR_SIGMA and total_drop >= MIN_TOTAL_FREQ_DROP_HZ:
                    extracted_ridges.append((seg_times, seg_freqs, seg_snrs))
                    found_valid_segment = True
                    
        # Ribbon suppression in s_work: zero out energy within +/- 4.5 Hz of the path
        suppress_radius_bins = max(1, int(np.round(4.5 / df)))
        for t in range(n_times):
            b = path_bins[t]
            low_b = max(0, b - suppress_radius_bins)
            high_b = min(n_freqs, b + suppress_radius_bins + 1)
            s_work[low_b:high_b, t] = 0.0
            
        if not found_valid_segment and max_val < 4.0:
            break
            
    return extracted_ridges


def check_harmonics(
    s_white: np.ndarray,
    freq_grid: np.ndarray,
    time_grid: np.ndarray,
    ridge_times: np.ndarray,
    ridge_freqs: np.ndarray,
    multipliers: Tuple[float, ...] = (2.0, 3.0, 0.5),
) -> List[Dict[str, Any]]:
    """Check whether harmonic or subharmonic traces exist for a candidate ridge."""
    dt = float(time_grid[1] - time_grid[0])
    df = float(freq_grid[1] - freq_grid[0])
    
    t_indices = np.clip(np.round((ridge_times - time_grid[0]) / dt).astype(int), 0, s_white.shape[1] - 1)
    
    detected_harmonics = []
    for mult in multipliers:
        harm_freqs = ridge_freqs * mult
        valid_mask = (harm_freqs >= freq_grid[0]) & (harm_freqs <= freq_grid[-1])
        if np.sum(valid_mask) < len(ridge_times) * 0.5:
            continue
            
        valid_t = t_indices[valid_mask]
        valid_f = harm_freqs[valid_mask]
        f_indices = np.clip(np.round((valid_f - freq_grid[0]) / df).astype(int), 0, s_white.shape[0] - 1)
        
        harm_snrs = s_white[f_indices, valid_t]
        mean_harm_snr = float(np.mean(harm_snrs))
        if mean_harm_snr >= 2.5:
            detected_harmonics.append({
                "multiplier": mult,
                "mean_snr_sigma": round(mean_harm_snr, 2),
                "label": f"{mult}x fundamental",
            })
            
    return detected_harmonics


def fit_doppler_curve(
    ridge_times: np.ndarray,
    ridge_freqs: np.ndarray,
    c: float = SPEED_OF_SOUND,
) -> Dict[str, Any]:
    """Fit retarded-time acoustic Doppler parameters theta = (f0, v, d_cpa, t0) to extracted ridge points.
    
    Uses scipy.optimize.least_squares with Huber loss ('soft_l1') for robustness to outliers.
    """
    t = np.asarray(ridge_times, dtype=np.float64)
    f = np.asarray(ridge_freqs, dtype=np.float64)
    
    # 1. Initial parameter estimates
    # Smooth ridge to estimate numerical derivative df/dt
    if len(t) >= 5:
        # 5-point moving average
        kernel = np.ones(5) / 5.0
        f_smooth = np.convolve(f, kernel, mode="same")
    else:
        f_smooth = f
        
    df_dt = np.gradient(f_smooth, t)
    # CPA is approximately where |df/dt| is maximized (steepest descent)
    min_slope_idx = int(np.argmin(df_dt))
    t0_guess = float(t[min_slope_idx])
    f0_guess = float(f[min_slope_idx])
    
    max_slope = abs(float(df_dt[min_slope_idx]))
    max_slope = max(max_slope, 0.5)
    
    # Velocity initial guess: general aviation average ~ 65 m/s (~126 kts)
    v_guess = 65.0
    # From slope equation: d_cpa = (f0 * v^2) / (c * |df/dt|_max)
    d_cpa_guess = (f0_guess * (v_guess ** 2)) / (c * max_slope)
    d_cpa_guess = float(np.clip(d_cpa_guess, 200.0, 5000.0))
    
    p0 = [f0_guess, v_guess, d_cpa_guess, t0_guess]
    
    # Physical parameter bounds
    # theta = [f0, v, d_cpa, t0]
    bounds_lower = np.array([40.0, 20.0, 100.0, t[0] - 30.0], dtype=np.float64)
    bounds_upper = np.array([445.0, 190.0, 10000.0, t[-1] + 30.0], dtype=np.float64)
    
    # Ensure initial guess is strictly within interior of bounds
    p0 = np.clip(p0, bounds_lower + 0.5, bounds_upper - 0.5)
    
    def residuals(params: np.ndarray) -> np.ndarray:
        p_f0, p_v, p_d_cpa, p_t0 = params
        f_pred = straight_line_doppler(t, p_f0, p_v, p_d_cpa, p_t0, c=c)
        return f_pred - f
        
    res = least_squares(
        residuals,
        p0,
        bounds=(bounds_lower, bounds_upper),
        loss="soft_l1",
        f_scale=1.0,
        max_nfev=300,
    )
    
    f0_fit, v_fit, d_cpa_fit, t0_fit = res.x
    rmse = float(np.sqrt(np.mean(res.fun ** 2)))
    
    # Compute observer CPA time: t_obs_cpa = t0 + d_cpa / c
    t_obs_cpa = t0_fit + (d_cpa_fit / c)
    inflection_slope = cpa_inflection_slope(f0_fit, v_fit, d_cpa_fit, c=c)
    
    return {
        "success": bool(res.success),
        "f0_hz": round(float(f0_fit), 2),
        "velocity_ms": round(float(v_fit), 2),
        "slant_distance_m": round(float(d_cpa_fit), 1),
        "t_emission_cpa_s": round(float(t0_fit), 2),
        "t_observed_cpa_s": round(float(t_obs_cpa), 2),
        "inflection_slope_hz_s": round(float(inflection_slope), 3),
        "fit_rmse_hz": round(float(rmse), 3),
    }


def classify_leak_risk(
    detections: List[Dict[str, Any]],
) -> Tuple[str, float, str]:
    """Assign overall leak risk score: CRITICAL, MODERATE, LOW, or CLEAN.
    
    Returns:
        (risk_level, max_risk_score, risk_rationale)
    """
    if not detections:
        return "CLEAN", 0.0, "No acoustic Doppler ridges detected in the 40-450 Hz band."
        
    max_snr = max(d["mean_snr_sigma"] for d in detections)
    has_harmonics = any(len(d.get("harmonics", [])) > 0 for d in detections)
    multi_event_lock = len(detections) >= 2
    min_rmse = min(d["fitted_params"]["fit_rmse_hz"] for d in detections)
    
    if (max_snr >= 7.0 and (has_harmonics or multi_event_lock)) or (multi_event_lock and max_snr >= 5.5 and min_rmse < 0.6):
        return (
            "CRITICAL",
            9.5,
            f"High-SNR Doppler ridge ({max_snr:.1f}σ) with "
            f"{'harmonic stacks' if has_harmonics else 'multi-event temporal lock'}. "
            "Sufficient to correlate against historical ADS-B flight paths within ~100m.",
        )
    elif max_snr >= 4.5 or (len(detections) >= 1 and min_rmse < 0.75):
        return (
            "MODERATE",
            6.5,
            f"Detected propeller Doppler curve ({max_snr:.1f}σ). Moderate geolocation leak risk under targeted correlation.",
        )
    else:
        return (
            "LOW",
            3.0,
            f"Weak ridge detected ({max_snr:.1f}σ). Low geolocation confidence without secondary acoustic confirmation.",
        )


def audit_spectrogram(
    s_white: np.ndarray,
    freq_grid: np.ndarray,
    time_grid: np.ndarray,
) -> Dict[str, Any]:
    """Run end-to-end AUDIT detection pipeline on a whitened spectrogram matrix."""
    raw_ridges = viterbi_ridge_tracker(s_white, freq_grid, time_grid)
    
    detections = []
    for idx, (r_times, r_freqs, r_snrs) in enumerate(raw_ridges, start=1):
        fit_res = fit_doppler_curve(r_times, r_freqs)
        harmonics = check_harmonics(s_white, freq_grid, time_grid, r_times, r_freqs)
        
        # Modeled curve for overlay on spectrogram
        t_model = np.linspace(r_times[0], r_times[-1], 100)
        f_model = straight_line_doppler(
            t_model,
            fit_res["f0_hz"],
            fit_res["velocity_ms"],
            fit_res["slant_distance_m"],
            fit_res["t_emission_cpa_s"],
        )
        
        det_entry = {
            "detection_id": f"DOPPLER-{idx:02d}",
            "start_time_s": round(float(r_times[0]), 2),
            "end_time_s": round(float(r_times[-1]), 2),
            "duration_s": round(float(r_times[-1] - r_times[0]), 2),
            "mean_snr_sigma": round(float(np.mean(r_snrs)), 2),
            "max_snr_sigma": round(float(np.max(r_snrs)), 2),
            "start_freq_hz": round(float(r_freqs[0]), 2),
            "end_freq_hz": round(float(r_freqs[-1]), 2),
            "freq_drop_hz": round(float(r_freqs[0] - r_freqs[-1]), 2),
            "fitted_params": fit_res,
            "harmonics": harmonics,
            "model_curve": {
                "times": np.round(t_model, 2).tolist(),
                "freqs": np.round(f_model, 2).tolist(),
            },
            "raw_ridge": {
                "times": np.round(r_times, 2).tolist(),
                "freqs": np.round(r_freqs, 2).tolist(),
            }
        }
        detections.append(det_entry)
        
    risk_level, risk_score, risk_rationale = classify_leak_risk(detections)
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_rationale": risk_rationale,
        "num_detections": len(detections),
        "detections": detections,
    }
