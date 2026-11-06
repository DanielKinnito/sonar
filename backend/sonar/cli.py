"""Typer CLI interface for Sonar Acoustic Security & Forensics Suite."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from sonar.core.audio_io import load_audio, save_audio, remux_cloaked_media
from sonar.core.spectrogram import compute_spectrogram, export_spectrogram_image, TARGET_FS
from sonar.core.detector import audit_spectrogram
from sonar.core.cloak import cloak_audio_stream
from sonar.core.verify_alibi import verify_spatiotemporal_alibi
from sonar.core.verify_physics import inspect_audio_physics
from sonar.utils.synthetic_gen import generate_synthetic_fixture

app = typer.Typer(
    name="sonar",
    help="Sonar: Local-first Acoustic Side-Channel Security & Forensics Suite",
    add_completion=False,
)
console = Console()


@app.command("synth-fixture")
def synth_fixture(
    output: Path = typer.Option(Path("sample_leak.wav"), "--output", "-o", help="Output WAV path"),
    planes: int = typer.Option(2, "--planes", "-p", help="Number of synthetic aircraft flyovers (1-3)"),
    duration: float = typer.Option(180.0, "--duration", "-d", help="Audio duration in seconds"),
):
    """Generate a realistic outdoor ambient audio fixture with embedded propeller Doppler curves."""
    console.print(f"[bold cyan]Generating synthetic ground-truth fixture with {planes} aircraft...[/bold cyan]")
    audio, manifest = generate_synthetic_fixture(
        output_path=str(output),
        duration_s=duration,
        fs=TARGET_FS,
        num_planes=planes,
    )
    
    table = Table(title="Synthesized Aircraft Ground Truth", border_style="cyan")
    table.add_column("Plane ID", style="bold yellow")
    table.add_column("Fundamental f0", justify="right")
    table.add_column("Speed (m/s)", justify="right")
    table.add_column("Slant CPA (m)", justify="right")
    table.add_column("Observed CPA (s)", justify="right")
    table.add_column("Slope @ CPA (Hz/s)", justify="right")
    
    for ac in manifest:
        table.add_row(
            ac["plane_id"],
            f"{ac['f0_hz']:.1f} Hz",
            f"{ac['velocity_ms']:.1f} m/s",
            f"{ac['slant_distance_m']:.0f} m",
            f"{ac['t_observed_cpa_s']:.1f} s",
            f"{ac['inflection_slope_hz_s']:.2f} Hz/s",
        )
        
    console.print(table)
    console.print(f"[bold green]✔ Saved fixture to {output.resolve()}[/bold green] ({len(audio)/TARGET_FS:.1f}s, {TARGET_FS} Hz mono)\n")


@app.command("audit")
def audit(
    file: Path = typer.Argument(..., help="Path to audio or video file to audit", exists=True),
    json_out: bool = typer.Option(False, "--json", help="Output raw JSON results to stdout"),
    plot: Optional[Path] = typer.Option(None, "--plot", help="Export annotated spectrogram PNG"),
):
    """Scan audio/video file for narrowband Doppler ridges that could leak location/time metadata."""
    if not json_out:
        console.print(f"[bold cyan]Auditing acoustic side-channel leak risk in: {file.name}[/bold cyan]")
        
    audio, fs = load_audio(str(file), target_fs=TARGET_FS)
    times, freqs, s_white, _ = compute_spectrogram(audio, fs=fs)
    audit_res = audit_spectrogram(s_white, freqs, times)
    
    if plot:
        png_bytes = export_spectrogram_image(s_white)
        plot.write_bytes(png_bytes)
        if not json_out:
            console.print(f"[green]✔ Exported spectrogram to {plot.resolve()}[/green]")
            
    if json_out:
        console.print(json.dumps(audit_res, indent=2))
        return
        
    risk_colors = {
        "CRITICAL": "bold red",
        "MODERATE": "bold yellow",
        "LOW": "bold blue",
        "CLEAN": "bold green",
    }
    risk_color = risk_colors.get(audit_res["risk_level"], "white")
    
    panel_content = (
        f"[{risk_color}]Risk Level: {audit_res['risk_level']}[/{risk_color}] (Score: {audit_res['risk_score']:.1f}/10)\n"
        f"{audit_res['risk_rationale']}\n"
        f"Detected Curves: {audit_res['num_detections']}"
    )
    console.print(Panel(panel_content, title="Acoustic Side-Channel Leak Assessment", border_style=risk_color))
    
    if audit_res["num_detections"] > 0:
        table = Table(title="Detected Doppler Signatures", border_style="dim")
        table.add_column("ID", style="bold")
        table.add_column("Time Window", justify="center")
        table.add_column("f0 (Hz)", justify="right")
        table.add_column("Speed (m/s)", justify="right")
        table.add_column("Slant CPA (m)", justify="right")
        table.add_column("Mean SNR (σ)", justify="right")
        table.add_column("Fit RMSE (Hz)", justify="right")
        table.add_column("Harmonics", justify="center")
        
        for det in audit_res["detections"]:
            p = det["fitted_params"]
            harms_str = ", ".join(h["label"] for h in det.get("harmonics", [])) or "None"
            table.add_row(
                det["detection_id"],
                f"{det['start_time_s']:.1f}s - {det['end_time_s']:.1f}s",
                f"{p['f0_hz']:.1f}",
                f"{p['velocity_ms']:.1f}",
                f"{p['slant_distance_m']:.0f}",
                f"{det['mean_snr_sigma']:.1f}σ",
                f"{p['fit_rmse_hz']:.2f}",
                harms_str,
            )
        console.print(table)


@app.command("cloak")
def cloak(
    input_file: Path = typer.Argument(..., help="Input media file to sanitize", exists=True),
    output_file: Path = typer.Option(..., "--output", "-o", help="Output sanitized media file"),
    chaff_count: int = typer.Option(5, "--chaff-count", help="Number of synthetic flyover decoys to inject"),
    warp_pct: float = typer.Option(0.35, "--warp-pct", help="Max time-base warping drift percentage"),
    no_notch: bool = typer.Option(False, "--no-notch", help="Disable Layer 1 surgical STFT notch erasure"),
):
    """Execute 3-layer active privacy cloaking and remux with stripped container metadata."""
    console.print(f"[bold cyan]Sanitizing acoustic signatures in: {input_file.name}[/bold cyan]")
    
    audio, fs = load_audio(str(input_file), target_fs=TARGET_FS)
    cloak_res = cloak_audio_stream(
        audio,
        fs=fs,
        chaff_count=chaff_count,
        warp_pct=warp_pct,
        enable_notch=not no_notch,
    )
    
    # Save temporary cloaked audio
    temp_wav = output_file.with_suffix(".tmp.wav")
    save_audio(str(temp_wav), cloak_res["cloaked_audio"], fs=fs)
    
    # Remux and strip metadata
    remux_cloaked_media(str(input_file), str(temp_wav), str(output_file))
    if temp_wav.is_file():
        temp_wav.unlink(missing_ok=True)
        
    audit_pre = cloak_res["audit_before"]
    audit_post = cloak_res["audit_after"]
    
    table = Table(title="Privacy Cloaking Summary", border_style="green")
    table.add_column("Metric")
    table.add_column("Before Cloak", style="bold red")
    table.add_column("After Cloak", style="bold green")
    
    table.add_row("Leak Risk Level", audit_pre["risk_level"], audit_post["risk_level"])
    table.add_row("Detected Real Curves", str(audit_pre["num_detections"]), str(audit_post["num_detections"]))
    table.add_row("Decoy Chaff Injected", "0", str(len(cloak_res["chaff_manifest"])))
    table.add_row("Time-Base Warping", "0.0%", f"±{warp_pct:.2f}%")
    table.add_row("Container GPS/EXIF", "Preserved", "Stripped (-map_metadata -1)")
    
    console.print(table)
    console.print(f"[bold green]✔ Successfully sanitized file exported to {output_file.resolve()}[/bold green]\n")


@app.command("verify-alibi")
def verify_alibi(
    file: Path = typer.Argument(..., help="Media file containing acoustic recording", exists=True),
    lat: float = typer.Option(..., "--lat", help="Claimed observer latitude in degrees"),
    lon: float = typer.Option(..., "--lon", help="Claimed observer longitude in degrees"),
    utc: str = typer.Option(..., "--utc", help="Claimed UTC ISO-8601 start timestamp"),
    radius_km: float = typer.Option(15.0, "--radius-km", help="Historical flight search radius in km"),
    trace: Optional[Path] = typer.Option(None, "--trace", help="Optional local GeoJSON/CSV flight trace file"),
):
    """Spatiotemporal Alibi Verifier: correlate audio against DEM elevation and ADS-B flight paths."""
    console.print(f"[bold cyan]Verifying spatiotemporal alibi at ({lat:.4f}, {lon:.4f}) on {utc}...[/bold cyan]")
    audio, fs = load_audio(str(file), target_fs=TARGET_FS)
    
    flight_traces = None
    if trace:
        from sonar.data.adsb import ADSBProvider
        prov = ADSBProvider()
        ext = trace.suffix.lower()
        if ext == ".geojson":
            flight_traces = prov.parse_geojson(str(trace))
        elif ext == ".csv":
            flight_traces = prov.parse_csv(str(trace))
        elif ext == ".json":
            # Attempt adsb.lol trace format, fallback to GeoJSON
            try:
                flight_traces = prov.parse_adsblol_trace_json(str(trace))
            except Exception:
                flight_traces = prov.parse_geojson(str(trace))
            
    res = verify_spatiotemporal_alibi(
        audio=audio,
        fs=fs,
        lat=lat,
        lon=lon,
        utc_iso=utc,
        search_radius_km=radius_km,
        flight_traces=flight_traces,
    )
    
    verdict_colors = {
        "VERIFIED_MATCH": "bold green",
        "CONTRADICTION_SILENCE_VIOLATION": "bold red",
        "UNVERIFIABLE_QUIET_SKY": "bold yellow",
        "INCONCLUSIVE": "bold blue",
    }
    col = verdict_colors.get(res["verdict"], "white")
    
    panel_msg = (
        f"[{col}]Verdict: {res['verdict']}[/{col}] (Confidence: {res['confidence']*100:.0f}%)\n"
        f"{res['summary']}\n"
        f"Observer Ground Elevation: {res['claimed_coordinates']['observer_elevation_m']}m"
    )
    console.print(Panel(panel_msg, title="Alibi Verification Verdict", border_style=col))


@app.command("verify-physics")
def verify_physics(
    file: Path = typer.Argument(..., help="Audio or video file containing vehicle/aircraft pass", exists=True),
    freq_min: float = typer.Option(40.0, "--freq-min", help="Minimum analysis frequency (Hz)"),
    freq_max: float = typer.Option(450.0, "--freq-max", help="Maximum analysis frequency (Hz)"),
):
    """Forensic AI & Synthetic Audio Inspector: check harmonic lock and retarded-time kinematics."""
    console.print(f"[bold cyan]Analyzing physical acoustic wave propagation in: {file.name}...[/bold cyan]")
    audio, fs = load_audio(str(file), target_fs=TARGET_FS)
    res = inspect_audio_physics(audio, fs=fs, f_min=freq_min, f_max=freq_max)
    
    col = "bold green" if "AUTHENTIC" in res["verdict"] else ("bold red" if "AI" in res["verdict"] else "bold yellow")
    panel_msg = (
        f"[{col}]Verdict: {res['verdict']}[/{col}] (Confidence: {res['confidence']*100:.0f}%)\n"
        f"{res['summary']}"
    )
    console.print(Panel(panel_msg, title="Acoustic Physics & AI Forensics", border_style=col))
    
    if res.get("passes"):
        table = Table(title="Kinematic & Harmonic Analysis", border_style="dim")
        table.add_column("Pass ID", style="bold")
        table.add_column("f0 (Hz)", justify="right")
        table.add_column("Implied Speed (m/s)", justify="right")
        table.add_column("Slant CPA (m)", justify="right")
        table.add_column("ε_kin (Hz)", justify="right")
        table.add_column("ε_harm (drift)", justify="right")
        table.add_column("Pass Verdict", justify="center")
        
        for p in res["passes"]:
            harm_disp = f"{p['epsilon_harm']:.5f}" if p["epsilon_harm"] is not None else "N/A"
            table.add_row(
                p["pass_id"],
                f"{p['f0_hz']:.1f}",
                f"{p['velocity_ms']:.1f}",
                f"{p['slant_distance_m']:.0f}",
                f"{p['epsilon_kin_hz']:.2f}",
                harm_disp,
                p["verdict"],
            )
        console.print(table)


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="FastAPI host"),
    port: int = typer.Option(8000, "--port", "-p", help="FastAPI port"),
    reload: bool = typer.Option(False, "--reload", help="Enable live code reloading"),
):
    """Start the FastAPI backend server for the Next.js frontend workstation."""
    import uvicorn
    console.print(f"[bold cyan]Starting Sonar API server on http://{host}:{port}...[/bold cyan]")
    uvicorn.run("sonar.api.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
