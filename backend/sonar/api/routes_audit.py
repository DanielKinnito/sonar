"""FastAPI Route: POST /api/audit."""

from __future__ import annotations

import base64
import os
import tempfile
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Response
from pydantic import BaseModel

from sonar.core.audio_io import load_audio
from sonar.core.spectrogram import (
    compute_spectrogram,
    export_spectrogram_image,
    spectrogram_to_json_payload,
    TARGET_FS,
)
from sonar.core.detector import audit_spectrogram
from sonar.utils.synthetic_gen import generate_synthetic_fixture

router = APIRouter(prefix="/api", tags=["audit"])


MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB cap


@router.post("/audit")
async def audit_endpoint(
    file: Optional[UploadFile] = File(None),
    demo: bool = Form(False),
    planes: int = Form(2),
):
    """Audit audio for acoustic side-channel Doppler leak risks."""
    if demo or file is None:
        # Generate synthetic fixture on the fly
        audio, _ = generate_synthetic_fixture(duration_s=120.0, fs=TARGET_FS, num_planes=min(max(planes, 1), 3))
    else:
        # Check size and save uploaded file to temp file
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
                
    times, freqs, s_white, _ = compute_spectrogram(audio, fs=TARGET_FS)
    audit_res = audit_spectrogram(s_white, freqs, times)
    
    # Export spectrogram PNG as base64 data URI
    png_bytes = export_spectrogram_image(s_white)
    png_base64 = base64.b64encode(png_bytes).decode("ascii")
    
    # JSON downsampled matrix for WebGL / interactive canvas
    matrix_payload = spectrogram_to_json_payload(times, freqs, s_white, downsample_factor_t=1, downsample_factor_f=2)
    
    return {
        "status": "success",
        "duration_s": float(len(audio)) / TARGET_FS,
        "fs": TARGET_FS,
        "leak_assessment": audit_res,
        "spectrogram": matrix_payload,
        "image_data_uri": f"data:image/png;base64,{png_base64}",
    }
