"""FastAPI Route: POST /api/cloak."""

from __future__ import annotations

import base64
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse

from sonar.core.audio_io import load_audio, save_audio, remux_cloaked_media
from sonar.core.spectrogram import (
    compute_spectrogram,
    export_spectrogram_image,
    spectrogram_to_json_payload,
    TARGET_FS,
)
from sonar.core.cloak import cloak_audio_stream
from sonar.utils.synthetic_gen import generate_synthetic_fixture

router = APIRouter(prefix="/api", tags=["cloak"])

STORAGE_DIR = Path(tempfile.gettempdir()) / "sonar_sanitized"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+\.(wav|mp4|mov|mkv|flac)$")
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB cap


@router.post("/cloak")
async def cloak_endpoint(
    file: Optional[UploadFile] = File(None),
    demo: bool = Form(False),
    chaff_count: int = Form(5),
    warp_pct: float = Form(0.35),
    enable_notch: bool = Form(True),
):
    """Sanitize media using the 3-layer active privacy cloaking engine."""
    if demo or file is None:
        audio, _ = generate_synthetic_fixture(duration_s=90.0, fs=TARGET_FS, num_planes=2)
        orig_file_path = None
    else:
        suffix = os.path.splitext(file.filename or "media.wav")[1]
        content = await file.read(MAX_FILE_SIZE_BYTES + 1)
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File too large (maximum 100 MB).")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            orig_file_path = tmp.name
            tmp.write(content)
            
        try:
            audio, _ = load_audio(orig_file_path, target_fs=TARGET_FS)
        except Exception as e:
            if os.path.exists(orig_file_path):
                os.remove(orig_file_path)
            raise HTTPException(status_code=400, detail=f"Audio ingestion failed: {str(e)}")
        
    cloak_res = cloak_audio_stream(
        audio,
        fs=TARGET_FS,
        chaff_count=chaff_count,
        warp_pct=warp_pct,
        enable_notch=enable_notch,
    )
    
    # Save sanitized media file for downloading
    download_id = f"sanitized_{uuid.uuid4().hex[:8]}.wav"
    output_path = str(STORAGE_DIR / download_id)
    
    if orig_file_path:
        temp_wav = str(STORAGE_DIR / f"temp_{download_id}")
        save_audio(temp_wav, cloak_res["cloaked_audio"], fs=TARGET_FS)
        remux_cloaked_media(orig_file_path, temp_wav, output_path)
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        if os.path.exists(orig_file_path):
            os.remove(orig_file_path)
    else:
        save_audio(output_path, cloak_res["cloaked_audio"], fs=TARGET_FS)
        
    # Generate before/after spectrogram matrices and image URIs
    times_pre, freqs_pre, s_white_pre, _ = compute_spectrogram(audio, fs=TARGET_FS)
    times_post, freqs_post, s_white_post, _ = compute_spectrogram(cloak_res["cloaked_audio"], fs=TARGET_FS)
    
    png_pre = export_spectrogram_image(s_white_pre)
    png_post = export_spectrogram_image(s_white_post)
    
    uri_pre = f"data:image/png;base64,{base64.b64encode(png_pre).decode('ascii')}"
    uri_post = f"data:image/png;base64,{base64.b64encode(png_post).decode('ascii')}"
    
    return {
        "status": "success",
        "download_url": f"/api/download/{download_id}",
        "filename": download_id,
        "layers_applied": cloak_res["layers_applied"],
        "audit_before": cloak_res["audit_before"],
        "audit_after": cloak_res["audit_after"],
        "chaff_manifest": cloak_res["chaff_manifest"],
        "spectrogram_before_uri": uri_pre,
        "spectrogram_after_uri": uri_post,
        "spectrogram_after": spectrogram_to_json_payload(times_post, freqs_post, s_white_post, 1, 2),
    }


@router.get("/download/{file_name}")
async def download_file(file_name: str):
    """Download sanitized media file with strict path traversal protections."""
    base_name = os.path.basename(file_name)
    if not SAFE_FILENAME_RE.match(base_name):
        raise HTTPException(status_code=400, detail="Invalid filename format.")

    safe_path = (STORAGE_DIR / base_name).resolve()
    storage_root = STORAGE_DIR.resolve()

    if not str(safe_path).startswith(str(storage_root)) or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="Requested file not found or expired.")

    return FileResponse(str(safe_path), filename=base_name, media_type="audio/wav")
