"""Retarded-time acoustic Doppler physics engine.

Implements exact retarded-time sound propagation solvers for straight-line
constant-velocity flyovers and arbitrary 3D ADS-B flight trajectories in ENU
coordinates.
"""

from __future__ import annotations

import math
from typing import Tuple, Dict, Any, Optional
import numpy as np
from scipy.interpolate import CubicSpline, interp1d

# Standard speed of sound in air at ~20°C and 1 atm (m/s)
SPEED_OF_SOUND: float = 343.0

# WGS84 Ellipsoid constants
WGS84_A: float = 6378137.0  # semi-major axis (m)
WGS84_F: float = 1.0 / 298.257223563  # flattening
WGS84_B: float = WGS84_A * (1.0 - WGS84_F)  # semi-minor axis (m)
WGS84_E2: float = 2.0 * WGS84_F - WGS84_F ** 2  # eccentricity squared


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> np.ndarray:
    """Convert geodetic coordinates (lat, lon in degrees, alt in meters) to ECEF (x, y, z in meters)."""
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    
    sin_lat = np.sin(lat_rad)
    cos_lat = np.cos(lat_rad)
    sin_lon = np.sin(lon_rad)
    cos_lon = np.cos(lon_rad)
    
    # Radius of curvature in prime vertical
    n = WGS84_A / np.sqrt(1.0 - WGS84_E2 * sin_lat ** 2)
    
    x = (n + alt_m) * cos_lat * cos_lon
    y = (n + alt_m) * cos_lat * sin_lon
    z = (n * (1.0 - WGS84_E2) + alt_m) * sin_lat
    
    return np.array([x, y, z], dtype=np.float64)


def ecef_to_enu(ecef_points: np.ndarray, ref_lat_deg: float, ref_lon_deg: float, ref_alt_m: float) -> np.ndarray:
    """Convert ECEF coordinates (N, 3) to East-North-Up (ENU) coordinates relative to a reference geodetic point."""
    ref_ecef = geodetic_to_ecef(ref_lat_deg, ref_lon_deg, ref_alt_m)
    diff = ecef_points - ref_ecef
    
    lat_rad = math.radians(ref_lat_deg)
    lon_rad = math.radians(ref_lon_deg)
    
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)
    
    # Rotation matrix from ECEF to ENU
    rot = np.array([
        [-sin_lon, cos_lon, 0.0],
        [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
        [cos_lat * cos_lon, cos_lat * sin_lon, sin_lat]
    ], dtype=np.float64)
    
    if diff.ndim == 1:
        return rot @ diff
    return (rot @ diff.T).T


def solve_emission_times_straight_line(
    t_obs: np.ndarray,
    t0_cpa: float,
    v: float,
    d_cpa: float,
    c: float = SPEED_OF_SOUND,
    n_iters: int = 5,
) -> np.ndarray:
    """Solve for sound emission times t_e given observation arrival times t_obs using Newton-Raphson.
    
    Relation: t_obs = t_e + R(t_e) / c
    where R(t_e) = sqrt(v^2 * (t_e - t0_cpa)^2 + d_cpa^2)
    """
    t_obs = np.asarray(t_obs, dtype=np.float64)
    # Initial guess: travel time estimated by minimum slant distance
    t_e = t_obs - (d_cpa / c)
    
    v2 = v * v
    d2 = d_cpa * d_cpa
    
    for _ in range(n_iters):
        dt = t_e - t0_cpa
        r = np.sqrt(v2 * dt * dt + d2)
        # g(t_e) = t_e + r / c - t_obs
        g = t_e + (r / c) - t_obs
        # g'(t_e) = 1 + (v^2 * dt) / (c * r)
        g_prime = 1.0 + (v2 * dt) / (c * r)
        t_e = t_e - g / g_prime
        
    return t_e


def straight_line_doppler(
    t_obs: np.ndarray,
    f0: float,
    v: float,
    d_cpa: float,
    t0_cpa: float,
    c: float = SPEED_OF_SOUND,
) -> np.ndarray:
    """Compute exact retarded-time acoustic Doppler curve f_obs(t_obs) for a constant-velocity straight flyover.
    
    Parameters:
        t_obs: Observer time grid (seconds)
        f0: Fundamental emitted frequency (Hz)
        v: Aircraft speed (m/s)
        d_cpa: Closest Point of Approach slant distance (m)
        t0_cpa: CPA timestamp in emission time (seconds)
        c: Speed of sound (m/s)
        
    Returns:
        Array of observed frequencies f_obs corresponding to t_obs
    """
    t_obs = np.asarray(t_obs, dtype=np.float64)
    t_e = solve_emission_times_straight_line(t_obs, t0_cpa, v, d_cpa, c=c)
    
    dt = t_e - t0_cpa
    r = np.sqrt((v * dt) ** 2 + d_cpa ** 2)
    # Radial velocity: v_r = dR/dt_e = v^2 * (t_e - t0) / R(t_e)
    # v_r < 0 when approaching (dt < 0), v_r > 0 when receding (dt > 0)
    v_r = (v * v * dt) / r
    
    # Observed frequency: f_obs = f0 / (1 + v_r / c)
    f_obs = f0 / (1.0 + v_r / c)
    return f_obs


def naive_doppler(
    t: np.ndarray,
    f0: float,
    v: float,
    d_cpa: float,
    t0_cpa: float,
    c: float = SPEED_OF_SOUND,
) -> np.ndarray:
    """Compute naive instantaneous (non-retarded) Doppler curve for comparison / baseline tests.
    
    Assumes infinite speed of sound propagation (no travel time delay).
    """
    t = np.asarray(t, dtype=np.float64)
    dt = t - t0_cpa
    r = np.sqrt((v * dt) ** 2 + d_cpa ** 2)
    v_r = (v * v * dt) / r
    return f0 / (1.0 + v_r / c)


def cpa_inflection_slope(f0: float, v: float, d_cpa: float, c: float = SPEED_OF_SOUND) -> float:
    """Calculate theoretical maximum frequency slope |df/dt| at CPA:
    
    |df/dt|_cpa = (f0 * v^2) / (c * d_cpa)
    """
    return (f0 * (v ** 2)) / (c * d_cpa)


def trajectory_3d_doppler(
    t_emission: np.ndarray,
    enu_coords: np.ndarray,
    f0: float,
    t_obs_grid: Optional[np.ndarray] = None,
    c: float = SPEED_OF_SOUND,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate retarded-time Doppler curve for an arbitrary 3D trajectory relative to the observer.
    
    Parameters:
        t_emission: 1D array of emission timestamps (seconds, monotonic)
        enu_coords: (N, 3) array of [East, North, Up] positions in meters
        f0: Fundamental emitted frequency (Hz)
        t_obs_grid: Optional target uniform observer time grid. If None, returns (t_obs, f_obs).
        c: Speed of sound (m/s)
        
    Returns:
        (t_obs, f_obs): Array of observer timestamps and corresponding observed frequencies.
    """
    t_e = np.asarray(t_emission, dtype=np.float64)
    p = np.asarray(enu_coords, dtype=np.float64)
    
    if len(t_e) < 4:
        raise ValueError("At least 4 trajectory points required for cubic spline differentiation.")
        
    # Fit cubic spline to trajectory components to compute smooth velocities
    cs_x = CubicSpline(t_e, p[:, 0])
    cs_y = CubicSpline(t_e, p[:, 1])
    cs_z = CubicSpline(t_e, p[:, 2])
    
    vx = cs_x(t_e, 1)
    vy = cs_y(t_e, 1)
    vz = cs_z(t_e, 1)
    
    # Slant range R(t_e)
    r = np.sqrt(p[:, 0] ** 2 + p[:, 1] ** 2 + p[:, 2] ** 2)
    r = np.maximum(r, 1.0)  # Avoid division by zero at ground point
    
    # Radial velocity: v_r = (p . v) / R
    v_r = (p[:, 0] * vx + p[:, 1] * vy + p[:, 2] * vz) / r
    
    # Retarded arrival time at observer
    t_obs = t_e + (r / c)
    
    # Doppler frequency at observer arrival time
    f_obs = f0 * (c / (c + v_r))
    
    # If a specific observer time grid was requested, interpolate onto it
    if t_obs_grid is not None:
        t_obs_grid = np.asarray(t_obs_grid, dtype=np.float64)
        # Check overlap
        valid_mask = (t_obs_grid >= t_obs[0]) & (t_obs_grid <= t_obs[-1])
        interpolator = interp1d(t_obs, f_obs, kind="cubic", fill_value="extrapolate")
        f_grid = np.zeros_like(t_obs_grid)
        f_grid[valid_mask] = interpolator(t_obs_grid[valid_mask])
        return t_obs_grid, f_grid
        
    return t_obs, f_obs


def compute_harmonic_lock_residual(f_fund: np.ndarray, f_harm: np.ndarray, k: int) -> float:
    """Compute harmonic lock residual epsilon_harm = mean(|f_harm(t) / (k * f_fund(t)) - 1|).
    
    For genuine physical rotor/blade acoustics, epsilon_harm < 0.005.
    Neural generative audio models (Sora, ElevenLabs, etc.) exhibit frequency-dependent drift.
    """
    f_fund = np.asarray(f_fund, dtype=np.float64)
    f_harm = np.asarray(f_harm, dtype=np.float64)
    
    mask = (f_fund > 10.0) & (f_harm > 10.0)
    if not np.any(mask):
        return 1.0
        
    ratio = f_harm[mask] / (float(k) * f_fund[mask])
    residual = float(np.mean(np.abs(ratio - 1.0)))
    return residual
