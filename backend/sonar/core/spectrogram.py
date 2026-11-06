"""High-resolution Short-Time Fourier Transform (STFT) & Two-Stage Spectral Whitener.

Extracts sub-audible narrowband acoustic ridges in the 40-450 Hz range by
eliminating stationary tonal hums (mains hum, HVAC) and broadband speech/wind
energy.
"""

from __future__ import annotations

import io
from typing import Tuple, Optional, Dict, Any
import numpy as np
from scipy import signal
from scipy.ndimage import median_filter
from PIL import Image

TARGET_FS: int = 4000  # Downsampled sample rate (Hz)
N_PER_SEG: int = 4000  # 1.0s window
N_FFT: int = 16384      # 16k FFT zero-padded -> 4000/16384 = 0.24414 Hz bin spacing
HOP_LENGTH: int = 1000  # 0.25s time step
F_MIN: float = 40.0     # Lower frequency boundary (Hz)
F_MAX: float = 450.0    # Upper frequency boundary (Hz)
MEDIAN_WINDOW_BINS: int = 61  # Local frequency median window (~15 Hz across bins)


def compute_spectrogram(
    audio: np.ndarray,
    fs: int = TARGET_FS,
    n_per_seg: int = N_PER_SEG,
    n_fft: int = N_FFT,
    hop_length: int = HOP_LENGTH,
    f_min: float = F_MIN,
    f_max: float = F_MAX,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute Short-Time Fourier Transform and two-stage whitened spectrogram.
    
    Parameters:
        audio: 1D float32 audio array at sample rate `fs`
        fs: Audio sample rate (default 4000 Hz)
        n_per_seg: Samples per STFT segment (default 4000 = 1.0s)
        n_fft: Zero-padded FFT length (default 16384 = 0.244 Hz bin resolution)
        hop_length: Hop length between successive windows (default 1000 = 0.25s)
        f_min: Minimum frequency to retain in output (default 40.0 Hz)
        f_max: Maximum frequency to retain in output (default 450.0 Hz)
        
    Returns:
        times: 1D array of time stamps (seconds)
        freqs: 1D array of frequency bins (Hz)
        s_white: 2D array of whitened SNR values in standard deviations (sigma), shape (n_freqs, n_times)
        stft_complex: 2D complex STFT slice in the frequency band, shape (n_freqs, n_times)
    """
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=-1)  # downmix to mono
        
    n_overlap = n_per_seg - hop_length
    window = signal.windows.hann(n_per_seg, sym=False)
    
    # Compute full STFT
    freqs_full, times, stft_matrix = signal.stft(
        audio,
        fs=fs,
        window=window,
        nperseg=n_per_seg,
        noverlap=n_overlap,
        nfft=n_fft,
        boundary="zeros",
        padded=True,
    )
    
    # Slice to strictly [f_min, f_max]
    band_mask = (freqs_full >= f_min) & (freqs_full <= f_max)
    freqs = freqs_full[band_mask]
    stft_complex = stft_matrix[band_mask, :]
    
    # 1. Convert magnitude to log-power dB
    mag = np.abs(stft_complex)
    s_db = 20.0 * np.log10(mag + 1e-10)
    
    # 2. Stage 1: Subtract temporal median per frequency bin (removes stationary 50/60Hz hums, HVAC)
    # Shape of s_db is (n_freqs, n_times)
    temporal_median = np.median(s_db, axis=1, keepdims=True)
    s_stat = s_db - temporal_median
    
    # 3. Stage 2: Subtract local frequency median per time frame (window of W_f = 61 bins ~ 15 Hz)
    # Flattens broadband speech/wind energy leaving sharp tonal ridges
    # We apply a 1D median filter along frequency axis (axis 0)
    local_freq_median = median_filter(s_stat, size=(MEDIAN_WINDOW_BINS, 1), mode="reflect")
    s_white_raw = np.maximum(0.0, s_stat - local_freq_median)
    
    # 4. Normalize by robust standard deviation (MAD * 1.4826)
    # Median Absolute Deviation
    median_val = np.median(s_white_raw)
    mad = np.median(np.abs(s_white_raw - median_val))
    robust_sigma = mad * 1.4826
    if robust_sigma < 1e-6:
        robust_sigma = float(np.std(s_white_raw) + 1e-6)
        
    s_white = (s_white_raw / robust_sigma).astype(np.float32)
    
    return times, freqs, s_white, stft_complex


def export_spectrogram_image(
    s_white: np.ndarray,
    cmap: str = "magma",
    v_max: float = 12.0,
    flip_ud: bool = True,
) -> bytes:
    """Render whitened spectrogram matrix to a colormapped PNG image buffer.
    
    Parameters:
        s_white: 2D array (n_freqs, n_times)
        cmap: 'magma', 'inferno', or 'viridis'
        v_max: Maximum SNR value in sigma for colormap clamping
        flip_ud: Whether to place lowest frequency at bottom (default True)
    """
    data = np.clip(s_white / max(v_max, 1e-3), 0.0, 1.0)
    if flip_ud:
        data = np.flipud(data)
        
    # High-contrast colormap LUT (256 RGB entries)
    # Magma-inspired colormap
    x = np.linspace(0.0, 1.0, 256)
    if cmap == "viridis":
        r = np.clip(0.267 + 2.8 * (x - 0.5)**2, 0.0, 1.0)
        g = np.clip(x * 0.95 + 0.05, 0.0, 1.0)
        b = np.clip(1.0 - 1.2 * x, 0.0, 1.0)
    else:  # magma / inferno
        r = np.clip(1.5 * x, 0.0, 1.0)
        g = np.clip(1.8 * (x - 0.25), 0.0, 1.0)
        b = np.clip(2.5 * (x - 0.65), 0.0, 1.0)
        # Deep blue/purple floor
        b = np.where(x < 0.25, x * 2.0, b)
        
    lut = np.zeros((256, 3), dtype=np.uint8)
    lut[:, 0] = (r * 255).astype(np.uint8)
    lut[:, 1] = (g * 255).astype(np.uint8)
    lut[:, 2] = (b * 255).astype(np.uint8)
    
    indices = (data * 255.0).astype(np.uint8)
    rgb = lut[indices]
    
    img = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def spectrogram_to_json_payload(
    times: np.ndarray,
    freqs: np.ndarray,
    s_white: np.ndarray,
    downsample_factor_t: int = 2,
    downsample_factor_f: int = 2,
) -> Dict[str, Any]:
    """Package downsampled spectrogram matrix for fast transmission over JSON/WebSocket."""
    t_down = times[::downsample_factor_t]
    f_down = freqs[::downsample_factor_f]
    matrix_down = s_white[::downsample_factor_f, ::downsample_factor_t]
    
    return {
        "times": np.round(t_down, 3).tolist(),
        "freqs": np.round(f_down, 2).tolist(),
        "s_white": np.round(matrix_down, 2).tolist(),
        "shape": [int(matrix_down.shape[0]), int(matrix_down.shape[1])],
        "max_snr": float(np.max(s_white)),
        "mean_snr": float(np.mean(s_white)),
    }
