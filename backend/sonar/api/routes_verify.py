"""FastAPI Routes for Verification: POST /api/verify/alibi & POST /api/verify/physics."""

from __future__ import annotations

import base64
import math
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional
import numpy as np
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

from sonar.core.audio_io import load_audio
from sonar.core.spectrogram import compute_spectrogram, export_spectrogram_image, TARGET_FS
from sonar.core.verify_alibi import verify_spatiotemporal_alibi
from sonar.core.verify_physics import inspect_audio_physics
from sonar.utils.synthetic_gen import generate_synthetic_fixture, synthesize_propeller_flyover

router = APIRouter(prefix="/api/verify", tags=["verify"])

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB cap


@router.post("/alibi")
async def verify_alibi_endpoint(
    file: Optional[UploadFile] = File(None),
    demo: bool = Form(False),
    lat: float = Form(37.7749),
    lon: float = Form(-122.4194),
    utc_time: str = Form("2026-06-15T14:00:00Z"),
    radius_km: float = Form(15.0),
):
    """Sub-Mode 3A: Spatiotemporal Alibi Verification."""
    mock_trace = None
    if demo or file is None:
        # Generate synthetic pass matching the claimed coordinate
        t_ref = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
        t_epoch = t_ref.timestamp()
        
        # Audio with a passing C172 aircraft at T+40s
        audio, _, _ = synthesize_propeller_flyover(
            duration_s=90.0,
            fs=TARGET_FS,
            f0=92.5,
            v=62.0,
            d_cpa=650.0,
            t0_cpa=40.0,
            peak_dbfs=-15.0,
        )
        # Construct synthetic matching ADS-B flight points
        t_steps = np.linspace(0.0, 90.0, 45)
        cos_lat = math.cos(math.radians(lat))
        pts = []
        for t_val in t_steps:
            d_east = 62.0 * (t_val - 40.0)
            p_lat = lat
            p_lon = lon + (d_east / (111000.0 * max(cos_lat, 0.01)))
            pts.append({
                "t_epoch_s": t_epoch + t_val,
                "lat": p_lat,
                "lon": p_lon,
                "alt_m": 650.0,
                "speed_ms": 62.0,
            })
        mock_trace = [{
            "flight_id": "N172SP",
            "hex": "A4B92C",
            "icao_type": "C172",
            "is_prop_or_rotor": True,
            "points": pts,
        }]
    else:
        content = await file.read(MAX_FILE_SIZE_BYTES + 1)
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File too large (maximum 100 MB).")

        suffix = os.path.splitext(file.filename or "media.wav")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            tmp.write(content)
        try:
            audio, _ = load_audio(tmp_path, target_fs=TARGET_FS)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio ingestion failed: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    result = verify_spatiotemporal_alibi(
        audio=audio,
        fs=TARGET_FS,
        lat=lat,
        lon=lon,
        utc_iso=utc_time,
        search_radius_km=radius_km,
        flight_traces=mock_trace,
    )
    
    # Generate background spectrogram image
    times, freqs, s_white, _ = compute_spectrogram(audio, fs=TARGET_FS)
    png_bytes = export_spectrogram_image(s_white)
    data_uri = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"
    
    return {
        "status": "success",
        "alibi_report": result,
        "spectrogram_image_uri": data_uri,
    }


@router.post("/physics")
async def verify_physics_endpoint(
    file: Optional[UploadFile] = File(None),
    demo: bool = Form(False),
    freq_min: float = Form(40.0),
    freq_max: float = Form(450.0),
):
    """Sub-Mode 3B: AI & Synthetic Audio Physics Forensics."""
    if demo or file is None:
        audio, _ = generate_synthetic_fixture(duration_s=60.0, fs=TARGET_FS, num_planes=1)
    else:
        content = await file.read(MAX_FILE_SIZE_BYTES + 1)
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File too large (maximum 100 MB).")

        suffix = os.path.splitext(file.filename or "media.wav")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            tmp.write(content)
        try:
            audio, _ = load_audio(tmp_path, target_fs=TARGET_FS)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio ingestion failed: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    physics_report = inspect_audio_physics(
        audio=audio,
        fs=TARGET_FS,
        f_min=freq_min,
        f_max=freq_max,
    )
    
    times, freqs, s_white, _ = compute_spectrogram(audio, fs=TARGET_FS, f_min=freq_min, f_max=freq_max)
    png_bytes = export_spectrogram_image(s_white)
    data_uri = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"
    
    return {
        "status": "success",
        "physics_report": physics_report,
        "spectrogram_image_uri": data_uri,
    }
