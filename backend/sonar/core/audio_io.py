"""Audio and Video I/O, downsampling, and metadata-stripping remuxing.

Utilizes local ffmpeg (system or bundled imageio-ffmpeg) and soundfile for
lossless, fast, and secure local-first media processing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Tuple, Optional
import numpy as np
import soundfile as sf


def get_ffmpeg_binary() -> str:
    """Find the path to the ffmpeg executable (system PATH or imageio-ffmpeg)."""
    # 1. Check system PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
        
    # 2. Check Gyan / standard Windows install locations
    common_win_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common_win_paths:
        if os.path.isfile(p):
            return p
            
    # 3. Fallback to imageio_ffmpeg if available
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
        
    return "ffmpeg"


def load_audio(
    file_path: str,
    target_fs: int = 4000,
) -> Tuple[np.ndarray, int]:
    """Load any audio or video file, downmixing to mono float32 resampled to target_fs.
    
    Parameters:
        file_path: Path to audio/video file
        target_fs: Desired sample rate in Hz (default 4000 Hz)
        
    Returns:
        (audio_samples, sample_rate)
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    
    # Fast path for uncompressed / lossless WAV if already at target_fs
    if ext in [".wav", ".flac"]:
        try:
            data, fs = sf.read(file_path, dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=-1)
            if fs == target_fs:
                return data, fs
        except Exception:
            pass  # Fallback to ffmpeg below
            
    ffmpeg_exe = get_ffmpeg_binary()
    
    # Run ffmpeg to extract and resample to raw float32 mono stream
    cmd = [
        ffmpeg_exe,
        "-y",
        "-loglevel", "error",
        "-i", file_path,
        "-vn",  # disable video
        "-ac", "1",  # mono
        "-ar", str(target_fs),  # target sample rate
        "-f", "f32le",  # 32-bit float Little Endian
        "-",
    ]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw_bytes, stderr = proc.communicate()
    
    if proc.returncode != 0:
        # If ffmpeg failed, try fallback soundfile with scipy.signal.resample_poly
        try:
            data, fs = sf.read(file_path, dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=-1)
            if fs != target_fs:
                from scipy import signal
                gcd = math.gcd(target_fs, fs)
                up = target_fs // gcd
                down = fs // gcd
                data = signal.resample_poly(data, up, down).astype(np.float32)
            return data, target_fs
        except Exception as err:
            raise RuntimeError(f"Failed to load audio with ffmpeg ({stderr.decode('utf-8', errors='ignore')}) or soundfile: {err}")
            
    audio = np.frombuffer(raw_bytes, dtype=np.float32)
    return audio, target_fs


def save_audio(
    output_path: str,
    audio: np.ndarray,
    fs: int = 4000,
    subtype: str = "PCM_16",
) -> str:
    """Save audio array to file using soundfile."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    sf.write(output_path, audio, fs, subtype=subtype)
    return output_path


def remux_cloaked_media(
    original_input_path: str,
    cloaked_audio_path: str,
    output_path: str,
) -> str:
    """Remux cloaked audio into the original video/audio container, stripping all EXIF/GPS metadata.
    
    Executes:
    ffmpeg -i original -i cloaked -c:v copy -c:a aac -b:a 256k -map 0:v? -map 1:a:0 -map_metadata -1 output
    """
    ffmpeg_exe = get_ffmpeg_binary()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Check if original container contains video streams
    has_video = False
    try:
        probe_cmd = [
            ffmpeg_exe,
            "-i", original_input_path,
        ]
        probe_proc = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "Video:" in probe_proc.stderr:
            has_video = True
    except Exception:
        pass
        
    if has_video:
        cmd = [
            ffmpeg_exe,
            "-y",
            "-loglevel", "error",
            "-i", original_input_path,
            "-i", cloaked_audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "256k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-map_metadata", "-1",
            "-bitexact",
            output_path,
        ]
    else:
        # Audio-only container
        cmd = [
            ffmpeg_exe,
            "-y",
            "-loglevel", "error",
            "-i", cloaked_audio_path,
            "-map_metadata", "-1",
            "-bitexact",
            output_path,
        ]
        
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        # Fallback for simple copy if audio format matched
        shutil.copy2(cloaked_audio_path, output_path)
        
    return output_path
