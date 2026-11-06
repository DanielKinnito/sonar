"""Tests for retarded-time acoustic Doppler physics and 3D ENU coordinate transformations."""

import numpy as np
import pytest

from sonar.core.physics import (
    straight_line_doppler,
    naive_doppler,
    solve_emission_times_straight_line,
    cpa_inflection_slope,
    geodetic_to_ecef,
    ecef_to_enu,
    trajectory_3d_doppler,
    compute_harmonic_lock_residual,
    SPEED_OF_SOUND,
)


def test_retarded_time_arrival_delay():
    """Verify sound arrives at observer delayed by exactly slant_distance / c."""
    t0 = 50.0  # Emission CPA timestamp
    v = 60.0   # 60 m/s (~116 knots)
    d_cpa = 686.0  # meters
    c = SPEED_OF_SOUND  # 343 m/s
    
    # Expected observation time at CPA: t0 + d_cpa / c = 50.0 + 2.0 = 52.0s
    expected_t_obs_cpa = t0 + (d_cpa / c)
    assert abs(expected_t_obs_cpa - 52.0) < 1e-4
    
    # Evaluate solver at t_obs = 52.0s
    t_e = solve_emission_times_straight_line(np.array([52.0]), t0, v, d_cpa, c=c)
    assert abs(t_e[0] - t0) < 1e-4, f"Emission time at CPA should be 50.0, got {t_e[0]}"


def test_retarded_vs_naive_doppler_asymmetry():
    """Verify that retarded-time Doppler accounts for wave propagation and exhibits physical time lag."""
    f0 = 100.0  # Hz
    v = 70.0    # m/s
    d_cpa = 1000.0  # m
    t0 = 60.0   # s
    c = 343.0
    
    t_grid = np.linspace(30.0, 90.0, 600)
    
    f_retarded = straight_line_doppler(t_grid, f0, v, d_cpa, t0, c=c)
    f_naive = naive_doppler(t_grid, f0, v, d_cpa, t0, c=c)
    
    # At t = t0 (60.0s), naive Doppler has reached exactly f0 (CPA point)
    assert abs(f_naive[np.argmin(np.abs(t_grid - t0))] - f0) < 0.1
    
    # But retarded-time Doppler reaches f0 only at t0 + d_cpa / c = 60 + 1000/343 = 62.915s
    t_obs_cpa = t0 + (d_cpa / c)
    idx_obs_cpa = np.argmin(np.abs(t_grid - t_obs_cpa))
    assert abs(f_retarded[idx_obs_cpa] - f0) < 0.1
    
    # Therefore at t = 60s, retarded Doppler is still above f0 because aircraft was still approaching when the sound arriving now was emitted
    idx_t0 = np.argmin(np.abs(t_grid - t0))
    assert f_retarded[idx_t0] > f0 + 2.0


def test_cpa_inflection_slope():
    """Verify numerical derivative |df/dt| at CPA matches theoretical formula f0 * v^2 / (c * d_cpa)."""
    f0 = 120.0
    v = 65.0
    d_cpa = 800.0
    t0 = 40.0
    c = 343.0
    
    t_obs_cpa = t0 + (d_cpa / c)
    # Fine grid around t_obs_cpa for high accuracy finite difference
    dt = 0.001
    t_eval = np.array([t_obs_cpa - dt, t_obs_cpa + dt])
    f_eval = straight_line_doppler(t_eval, f0, v, d_cpa, t0, c=c)
    
    numerical_slope = abs(f_eval[1] - f_eval[0]) / (2.0 * dt)
    theoretical_slope = cpa_inflection_slope(f0, v, d_cpa, c=c)
    
    # Theoretical: 120 * 65^2 / (343 * 800) = 507000 / 274400 = 1.84766 Hz/s
    rel_error = abs(numerical_slope - theoretical_slope) / theoretical_slope
    assert rel_error < 1e-3, f"Numerical {numerical_slope} vs Theoretical {theoretical_slope}"


def test_geodetic_to_enu_straight_flyover():
    """Verify 3D trajectory calculation agrees with 1D straight line solver for level flyover."""
    ref_lat = 37.7749   # San Francisco
    ref_lon = -122.4194
    ref_alt = 10.0      # meters
    
    # Simulated level flyover flying East at altitude 500m, speed 50 m/s
    # Observer at (0, 0, 0) in ENU
    t0 = 50.0
    v = 50.0
    alt = 500.0  # slant distance at CPA = 500m
    
    t_e = np.linspace(20.0, 80.0, 301)
    # Positions in ENU meters: x = v * (t - t0), y = 0, z = alt
    enu_points = np.zeros((len(t_e), 3), dtype=np.float64)
    enu_points[:, 0] = v * (t_e - t0)
    enu_points[:, 1] = 0.0
    enu_points[:, 2] = alt
    
    f0 = 110.0
    t_obs_3d, f_obs_3d = trajectory_3d_doppler(t_e, enu_points, f0=f0)
    
    # Calculate using 1D straight line solver on the same observation times
    f_obs_1d = straight_line_doppler(t_obs_3d, f0, v, alt, t0)
    
    # Should agree within 0.05 Hz across entire pass
    max_diff = np.max(np.abs(f_obs_3d - f_obs_1d))
    assert max_diff < 0.05, f"3D vs 1D max diff: {max_diff} Hz"


def test_harmonic_lock_residual():
    """Verify that true physical harmonic stacks yield epsilon_harm < 0.005, while AI drift is caught."""
    t = np.linspace(0.0, 30.0, 300)
    f_fund = 100.0 - 0.5 * t  # Linear drop
    
    # True physical second harmonic: exactly 2 * f_fund
    f_harm_true = 2.0 * f_fund
    eps_true = compute_harmonic_lock_residual(f_fund, f_harm_true, k=2)
    assert eps_true < 1e-6
    
    # AI / neural generative drift: 1.5% non-physical drift
    drift = 1.0 + 0.015 * np.sin(2.0 * np.pi * t / 5.0)
    f_harm_ai = 2.0 * f_fund * drift
    eps_ai = compute_harmonic_lock_residual(f_fund, f_harm_ai, k=2)
    assert eps_ai > 0.008, f"AI drift should be flagged: {eps_ai}"
