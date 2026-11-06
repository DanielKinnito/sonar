"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Maximize2, RefreshCw, Eye, EyeOff, Layers } from "lucide-react";
import { SpectrogramPayload, DopplerDetection } from "@/lib/api";

interface OverlayOptions {
  showSpectrogram: boolean;
  showRawRidges: boolean;
  showFittedCurves: boolean;
  showHarmonics: boolean;
  showChaff: boolean;
  showAdsbCurves: boolean;
}

interface SpectrogramCanvasProps {
  spectrogram?: SpectrogramPayload | null;
  imageDataUri?: string | null;
  detections?: DopplerDetection[];
  chaffCurves?: Array<{ times: number[]; freqs: number[]; label?: string }>;
  adsbCurves?: Array<{ times: number[]; freqs: number[]; flight_id: string; is_match?: boolean }>;
  title?: string;
  height?: number;
}

export default function SpectrogramCanvas({
  spectrogram,
  imageDataUri,
  detections = [],
  chaffCurves = [],
  adsbCurves = [],
  title = "Acoustic Spectrogram Analysis (40 - 450 Hz)",
  height = 360,
}: SpectrogramCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [overlays, setOverlays] = useState<OverlayOptions>({
    showSpectrogram: true,
    showRawRidges: true,
    showFittedCurves: true,
    showHarmonics: true,
    showChaff: true,
    showAdsbCurves: true,
  });

  const [cursorPos, setCursorPos] = useState<{
    x: number;
    y: number;
    time: number;
    freq: number;
    snr: number;
  } | null>(null);

  // Time & Frequency bounds
  const minFreq = 40.0;
  const maxFreq = 450.0;
  const maxTime = spectrogram?.times?.length
    ? spectrogram.times[spectrogram.times.length - 1]
    : 120.0;
  const minTime = 0.0;

  // Render loop
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const h = canvas.height;

    // Clear background
    ctx.fillStyle = "#090A0F";
    ctx.fillRect(0, 0, width, h);

    // Coordinate transforms
    const timeToX = (t: number) => ((t - minTime) / (maxTime - minTime)) * width;
    const freqToY = (f: number) => h - ((f - minFreq) / (maxFreq - minFreq)) * h;

    // 1. Draw Spectrogram Matrix or Background Image
    if (overlays.showSpectrogram) {
      if (imageDataUri) {
        const img = new Image();
        img.src = imageDataUri;
        if (img.complete && img.naturalWidth > 0) {
          ctx.drawImage(img, 0, 0, width, h);
        } else {
          img.onload = () => {
            if (canvasRef.current) drawCanvas();
          };
        }
      } else if (spectrogram?.s_white) {
        // Draw directly from s_white matrix
        const nFreqs = spectrogram.freqs.length;
        const nTimes = spectrogram.times.length;
        if (nFreqs > 0 && nTimes > 0) {
          const imgData = ctx.createImageData(nTimes, nFreqs);
          const data = imgData.data;

          for (let f = 0; f < nFreqs; f++) {
            // Invert Y so lowest frequency is at bottom
            const rowIdx = (nFreqs - 1 - f) * nTimes;
            for (let t = 0; t < nTimes; t++) {
              const val = Math.min(1.0, Math.max(0.0, spectrogram.s_white[f][t] / 10.0));
              const pIdx = (rowIdx + t) * 4;

              // Magma colormap approx
              data[pIdx] = Math.min(255, Math.floor(val * 1.6 * 255));
              data[pIdx + 1] = Math.min(255, Math.floor(Math.max(0, val - 0.25) * 1.8 * 255));
              data[pIdx + 2] = Math.min(255, Math.floor(Math.max(0, val - 0.6) * 2.5 * 255 + (val < 0.2 ? val * 2 * 255 : 0)));
              data[pIdx + 3] = 255;
            }
          }
          // Create temp offscreen canvas to scale smoothly
          const off = document.createElement("canvas");
          off.width = nTimes;
          off.height = nFreqs;
          const offCtx = off.getContext("2d");
          if (offCtx) {
            offCtx.putImageData(imgData, 0, 0);
            ctx.drawImage(off, 0, 0, width, h);
          }
        }
      }
    }

    // 2. Draw Frequency & Time Grid Overlay
    ctx.strokeStyle = "rgba(30, 36, 51, 0.6)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    // Frequency grid lines every 50 Hz
    for (let f = 50; f <= 400; f += 50) {
      const y = freqToY(f);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();

      // Label
      ctx.fillStyle = "rgba(136, 146, 176, 0.45)";
      ctx.font = "10px monospace";
      ctx.fillText(`${f} Hz`, 8, y - 4);
    }

    // Time grid lines every 15s
    for (let t = 15; t < maxTime; t += 15) {
      const x = timeToX(t);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();

      ctx.fillStyle = "rgba(136, 146, 176, 0.45)";
      ctx.font = "10px monospace";
      ctx.fillText(`${t}s`, x + 4, h - 8);
    }
    ctx.setLineDash([]);

    // 3. Draw Injected Chaff Decoy Curves (Layer 2)
    if (overlays.showChaff && chaffCurves.length > 0) {
      chaffCurves.forEach((c) => {
        if (!c.times.length) return;
        ctx.strokeStyle = "rgba(255, 51, 102, 0.85)";
        ctx.lineWidth = 1.8;
        ctx.setLineDash([6, 3]);
        ctx.beginPath();
        for (let i = 0; i < c.times.length; i++) {
          const x = timeToX(c.times[i]);
          const y = freqToY(c.freqs[i]);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      });
    }

    // 4. Draw Historical ADS-B Modeled Curves (Pillar 3)
    if (overlays.showAdsbCurves && adsbCurves.length > 0) {
      adsbCurves.forEach((c) => {
        if (!c.times.length) return;
        ctx.strokeStyle = c.is_match ? "rgba(0, 255, 136, 0.95)" : "rgba(0, 240, 255, 0.65)";
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        for (let i = 0; i < c.times.length; i++) {
          const x = timeToX(c.times[i]);
          const y = freqToY(c.freqs[i]);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Label flight ID
        const midIdx = Math.floor(c.times.length / 2);
        ctx.fillStyle = c.is_match ? "#00FF88" : "#00F0FF";
        ctx.font = "bold 10px monospace";
        ctx.fillText(
          `✈ ${c.flight_id}`,
          timeToX(c.times[midIdx]) + 6,
          freqToY(c.freqs[midIdx]) - 6
        );
      });
    }

    // 5. Draw Raw Viterbi Extracted Ridges
    if (overlays.showRawRidges && detections.length > 0) {
      detections.forEach((det) => {
        const r = det.raw_ridge;
        if (!r?.times?.length) return;

        ctx.strokeStyle = "rgba(255, 184, 0, 0.9)";
        ctx.lineWidth = 2.0;
        ctx.beginPath();
        for (let i = 0; i < r.times.length; i++) {
          const x = timeToX(r.times[i]);
          const y = freqToY(r.freqs[i]);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });
    }

    // 6. Draw Fitted Physics Curves (f0, 2f0, 3f0)
    if (overlays.showFittedCurves && detections.length > 0) {
      detections.forEach((det, dIdx) => {
        const m = det.model_curve;
        if (!m?.times?.length) return;

        // Fundamental f0
        ctx.strokeStyle = "#00F0FF";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        for (let i = 0; i < m.times.length; i++) {
          const x = timeToX(m.times[i]);
          const y = freqToY(m.freqs[i]);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // CPA Marker circle
        const p = det.fitted_params;
        const cpaX = timeToX(p.t_observed_cpa_s);
        const cpaY = freqToY(p.f0_hz);

        ctx.fillStyle = "#00F0FF";
        ctx.beginPath();
        ctx.arc(cpaX, cpaY, 4, 0, 2 * Math.PI);
        ctx.fill();

        ctx.font = "bold 10px monospace";
        ctx.fillStyle = "#00F0FF";
        ctx.fillText(
          `${det.detection_id}: f0=${p.f0_hz.toFixed(1)}Hz v=${p.velocity_ms.toFixed(0)}m/s`,
          cpaX + 8,
          cpaY - 6
        );

        // Harmonics (2f0, 3f0)
        if (overlays.showHarmonics) {
          [2.0, 3.0].forEach((k) => {
            ctx.strokeStyle = k === 2.0 ? "rgba(0, 240, 255, 0.45)" : "rgba(0, 240, 255, 0.25)";
            ctx.lineWidth = 1.5;
            ctx.setLineDash([3, 2]);
            ctx.beginPath();
            for (let i = 0; i < m.times.length; i++) {
              const hFreq = m.freqs[i] * k;
              if (hFreq <= maxFreq) {
                const x = timeToX(m.times[i]);
                const y = freqToY(hFreq);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
              }
            }
            ctx.stroke();
            ctx.setLineDash([]);
          });
        }
      });
    }

    // 7. Cursor Crosshair Telemetry
    if (cursorPos) {
      const cx = cursorPos.x;
      const cy = cursorPos.y;

      ctx.strokeStyle = "rgba(0, 240, 255, 0.5)";
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);

      // Vertical crosshair
      ctx.beginPath();
      ctx.moveTo(cx, 0);
      ctx.lineTo(cx, h);
      ctx.stroke();

      // Horizontal crosshair
      ctx.beginPath();
      ctx.moveTo(0, cy);
      ctx.lineTo(width, cy);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [
    overlays,
    imageDataUri,
    spectrogram,
    detections,
    chaffCurves,
    adsbCurves,
    cursorPos,
    maxTime,
  ]);

  // Handle Canvas Resize
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;
      canvas.width = container.clientWidth;
      canvas.height = height;
      drawCanvas();
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [drawCanvas, height]);

  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  // Mouse Move Telemetry
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const time = (x / canvas.width) * (maxTime - minTime) + minTime;
    const freq = maxFreq - (y / canvas.height) * (maxFreq - minFreq);

    // Look up SNR from spectrogram matrix if available
    let snr = 0.0;
    if (spectrogram?.s_white) {
      const fIdx = Math.min(
        spectrogram.freqs.length - 1,
        Math.max(
          0,
          Math.floor(
            ((freq - minFreq) / (maxFreq - minFreq)) * spectrogram.freqs.length
          )
        )
      );
      const tIdx = Math.min(
        spectrogram.times.length - 1,
        Math.max(
          0,
          Math.floor(
            ((time - minTime) / (maxTime - minTime)) * spectrogram.times.length
          )
        )
      );
      snr = spectrogram.s_white[fIdx]?.[tIdx] ?? 0.0;
    }

    setCursorPos({ x, y, time, freq, snr });
  };

  const handleMouseLeave = () => setCursorPos(null);

  return (
    <div
      ref={containerRef}
      className="flex flex-col bg-sonar-panel border border-sonar-border rounded-lg overflow-hidden shadow-2xl"
    >
      {/* Canvas Header & Controls */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 bg-sonar-card/80 border-b border-sonar-border text-xs">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-sonar-cyan" />
          <span className="font-semibold text-sonar-text tracking-wide uppercase">
            {title}
          </span>
        </div>

        {/* Overlay Toggles */}
        <div className="flex items-center gap-2 text-[11px] font-mono">
          <button
            onClick={() =>
              setOverlays((o) => ({ ...o, showSpectrogram: !o.showSpectrogram }))
            }
            className={`px-2 py-0.5 rounded border transition-colors ${
              overlays.showSpectrogram
                ? "bg-sonar-cyan/15 border-sonar-cyan text-sonar-cyan"
                : "bg-sonar-bg border-sonar-border text-sonar-muted"
            }`}
          >
            STFT Map
          </button>
          <button
            onClick={() =>
              setOverlays((o) => ({ ...o, showRawRidges: !o.showRawRidges }))
            }
            className={`px-2 py-0.5 rounded border transition-colors ${
              overlays.showRawRidges
                ? "bg-sonar-amber/15 border-sonar-amber text-sonar-amber"
                : "bg-sonar-bg border-sonar-border text-sonar-muted"
            }`}
          >
            Viterbi Ridges
          </button>
          <button
            onClick={() =>
              setOverlays((o) => ({
                ...o,
                showFittedCurves: !o.showFittedCurves,
              }))
            }
            className={`px-2 py-0.5 rounded border transition-colors ${
              overlays.showFittedCurves
                ? "bg-sonar-cyan/15 border-sonar-cyan text-sonar-cyan"
                : "bg-sonar-bg border-sonar-border text-sonar-muted"
            }`}
          >
            Fitted f0
          </button>
          <button
            onClick={() =>
              setOverlays((o) => ({ ...o, showHarmonics: !o.showHarmonics }))
            }
            className={`px-2 py-0.5 rounded border transition-colors ${
              overlays.showHarmonics
                ? "bg-sonar-cyan/15 border-sonar-cyan text-sonar-cyan"
                : "bg-sonar-bg border-sonar-border text-sonar-muted"
            }`}
          >
            Harmonics (2f0, 3f0)
          </button>
          {chaffCurves.length > 0 && (
            <button
              onClick={() =>
                setOverlays((o) => ({ ...o, showChaff: !o.showChaff }))
              }
              className={`px-2 py-0.5 rounded border transition-colors ${
                overlays.showChaff
                  ? "bg-sonar-red/15 border-sonar-red text-sonar-red"
                  : "bg-sonar-bg border-sonar-border text-sonar-muted"
              }`}
            >
              Chaff Decoys
            </button>
          )}
          {adsbCurves.length > 0 && (
            <button
              onClick={() =>
                setOverlays((o) => ({
                  ...o,
                  showAdsbCurves: !o.showAdsbCurves,
                }))
              }
              className={`px-2 py-0.5 rounded border transition-colors ${
                overlays.showAdsbCurves
                  ? "bg-sonar-green/15 border-sonar-green text-sonar-green"
                  : "bg-sonar-bg border-sonar-border text-sonar-muted"
              }`}
            >
              ADS-B Trajectories
            </button>
          )}
        </div>
      </div>

      {/* Main Canvas Viewport */}
      <div className="relative w-full overflow-hidden bg-sonar-bg">
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="w-full cursor-crosshair block"
        />

        {/* Real-time Cursor Telemetry Readout */}
        <div className="absolute bottom-2 right-3 px-3 py-1 bg-sonar-bg/90 border border-sonar-border rounded font-mono text-[11px] text-sonar-text shadow-lg backdrop-blur-sm pointer-events-none flex items-center gap-4">
          <div>
            <span className="text-sonar-muted">TIME: </span>
            <span className="text-sonar-cyan">
              {cursorPos
                ? `${Math.floor(cursorPos.time / 60)}:${(cursorPos.time % 60)
                    .toFixed(2)
                    .padStart(5, "0")}s`
                : "--:--.--s"}
            </span>
          </div>
          <div>
            <span className="text-sonar-muted">FREQ: </span>
            <span className="text-sonar-amber">
              {cursorPos ? `${cursorPos.freq.toFixed(2)} Hz` : "---.-- Hz"}
            </span>
          </div>
          <div>
            <span className="text-sonar-muted">SNR: </span>
            <span className="text-sonar-green">
              {cursorPos ? `${cursorPos.snr.toFixed(1)} σ` : "-.- σ"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
