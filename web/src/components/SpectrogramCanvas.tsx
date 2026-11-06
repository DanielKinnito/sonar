"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Layers, Activity, Eye } from "lucide-react";
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

  // Frequency & Time bounds
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

    // Clear background to obsidian
    ctx.fillStyle = "#0A0D12";
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
        const nFreqs = spectrogram.freqs.length;
        const nTimes = spectrogram.times.length;
        if (nFreqs > 0 && nTimes > 0) {
          const imgData = ctx.createImageData(nTimes, nFreqs);
          const data = imgData.data;

          for (let f = 0; f < nFreqs; f++) {
            const rowIdx = (nFreqs - 1 - f) * nTimes;
            for (let t = 0; t < nTimes; t++) {
              const val = Math.min(1.0, Math.max(0.0, spectrogram.s_white[f][t] / 10.0));
              const pIdx = (rowIdx + t) * 4;

              // High-contrast radiant acoustic heat-map (amber/cyan)
              data[pIdx] = Math.min(255, Math.floor(val * 1.5 * 255));
              data[pIdx + 1] = Math.min(255, Math.floor(Math.max(0, val - 0.2) * 1.8 * 255));
              data[pIdx + 2] = Math.min(255, Math.floor(Math.max(0, val - 0.5) * 2.4 * 255 + (val < 0.15 ? val * 255 : 0)));
              data[pIdx + 3] = 255;
            }
          }
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

    // 2. Frequency & Time Grid Overlay (Precision Hairlines)
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 4]);

    for (let f = 50; f <= 400; f += 50) {
      const y = freqToY(f);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();

      // Tick label
      ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
      ctx.font = "9px ui-monospace, monospace";
      ctx.fillText(`${f} Hz`, 10, y - 3);
    }

    for (let t = 15; t < maxTime; t += 15) {
      const x = timeToX(t);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();

      ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
      ctx.font = "9px ui-monospace, monospace";
      ctx.fillText(`${t}s`, x + 4, h - 8);
    }
    ctx.setLineDash([]);

    // 3. Injected Decoy Chaff (Layer 2)
    if (overlays.showChaff && chaffCurves.length > 0) {
      chaffCurves.forEach((c) => {
        if (!c.times.length) return;
        ctx.strokeStyle = "rgba(239, 68, 68, 0.85)";
        ctx.lineWidth = 1.6;
        ctx.setLineDash([5, 3]);
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

    // 4. Modeled ADS-B Trajectories (Pillar 3)
    if (overlays.showAdsbCurves && adsbCurves.length > 0) {
      adsbCurves.forEach((c) => {
        if (!c.times.length) return;
        ctx.strokeStyle = c.is_match ? "#10B981" : "#38BDF8";
        ctx.lineWidth = 2.0;
        ctx.beginPath();
        for (let i = 0; i < c.times.length; i++) {
          const x = timeToX(c.times[i]);
          const y = freqToY(c.freqs[i]);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();

        const midIdx = Math.floor(c.times.length / 2);
        ctx.fillStyle = c.is_match ? "#10B981" : "#38BDF8";
        ctx.font = "bold 9px ui-monospace, monospace";
        ctx.fillText(
          `✈ ${c.flight_id}`,
          timeToX(c.times[midIdx]) + 6,
          freqToY(c.freqs[midIdx]) - 6
        );
      });
    }

    // 5. Raw Viterbi Extracted Ridges
    if (overlays.showRawRidges && detections.length > 0) {
      detections.forEach((det) => {
        const r = det.raw_ridge;
        if (!r?.times?.length) return;

        ctx.strokeStyle = "rgba(245, 158, 11, 0.9)";
        ctx.lineWidth = 1.8;
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

    // 6. Fitted Physics Curves (f0)
    if (overlays.showFittedCurves && detections.length > 0) {
      detections.forEach((det) => {
        const m = det.model_curve;
        if (!m?.times?.length) return;

        ctx.strokeStyle = "#38BDF8";
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        for (let i = 0; i < m.times.length; i++) {
          const x = timeToX(m.times[i]);
          const y = freqToY(m.freqs[i]);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // CPA Marker point
        const p = det.fitted_params;
        const cpaX = timeToX(p.t_observed_cpa_s);
        const cpaY = freqToY(p.f0_hz);

        ctx.fillStyle = "#38BDF8";
        ctx.beginPath();
        ctx.arc(cpaX, cpaY, 3.5, 0, 2 * Math.PI);
        ctx.fill();

        ctx.fillStyle = "#FFFFFF";
        ctx.font = "bold 9px ui-monospace, monospace";
        ctx.fillText(`CPA: ${p.f0_hz.toFixed(1)}Hz`, cpaX + 6, cpaY - 6);
      });
    }

    // 7. Harmonic Stacks (2f0, 3f0)
    if (overlays.showHarmonics && detections.length > 0) {
      detections.forEach((det) => {
        const m = det.model_curve;
        if (!m?.times?.length) return;

        [2, 3].forEach((k) => {
          ctx.strokeStyle = k === 2 ? "rgba(56, 189, 248, 0.45)" : "rgba(56, 189, 248, 0.3)";
          ctx.lineWidth = 1.2;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          for (let i = 0; i < m.times.length; i++) {
            const fHarm = m.freqs[i] * k;
            if (fHarm > maxFreq) continue;
            const x = timeToX(m.times[i]);
            const y = freqToY(fHarm);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.stroke();
          ctx.setLineDash([]);
        });
      });
    }

    // 8. Real-time Cursor Reticle & Crosshairs
    if (cursorPos) {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);

      // Vertical line
      ctx.beginPath();
      ctx.moveTo(cursorPos.x, 0);
      ctx.lineTo(cursorPos.x, h);
      ctx.stroke();

      // Horizontal line
      ctx.beginPath();
      ctx.moveTo(0, cursorPos.y);
      ctx.lineTo(width, cursorPos.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [
    overlays,
    spectrogram,
    imageDataUri,
    detections,
    chaffCurves,
    adsbCurves,
    cursorPos,
    maxTime,
  ]);

  // Canvas resize observer
  useEffect(() => {
    const handleResize = () => {
      if (!containerRef.current || !canvasRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      canvasRef.current.width = rect.width;
      canvasRef.current.height = height;
      drawCanvas();
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [drawCanvas, height]);

  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const time = minTime + (x / canvas.width) * (maxTime - minTime);
    const freq = maxFreq - (y / canvas.height) * (maxFreq - minFreq);

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
      className="flex flex-col bg-[#0E1219] border border-white/[0.08] rounded-lg overflow-hidden shadow-sm"
    >
      {/* Top HUD Instrument Strip */}
      <div className="flex flex-wrap items-center justify-between px-3.5 py-2 bg-[#141923] border-b border-white/[0.07] text-xs gap-2">
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-sonar-cyan" />
          <span className="font-mono font-medium text-white text-[11px] tracking-wide">
            {title}
          </span>
          <span className="text-[10px] font-mono text-sonar-muted px-1.5 py-0.2 bg-white/[0.04] rounded border border-white/[0.08]">
            40–450 Hz
          </span>
        </div>

        {/* Live HUD Telemetry Readout */}
        <div className="flex items-center gap-3 text-[11px] font-mono bg-[#0B0E14] px-2.5 py-1 rounded border border-white/[0.06]">
          <div className="flex items-center gap-1.5">
            <span className="text-sonar-muted text-[10px]">TIME:</span>
            <span className="text-white font-medium">
              {cursorPos
                ? `${Math.floor(cursorPos.time / 60)}:${(cursorPos.time % 60)
                    .toFixed(2)
                    .padStart(5, "0")}s`
                : "--:--.--s"}
            </span>
          </div>
          <span className="text-white/[0.15]">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-sonar-muted text-[10px]">FREQ:</span>
            <span className="text-sonar-amber font-medium">
              {cursorPos ? `${cursorPos.freq.toFixed(1)} Hz` : "---.- Hz"}
            </span>
          </div>
          <span className="text-white/[0.15]">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-sonar-muted text-[10px]">SNR:</span>
            <span className="text-sonar-cyan font-medium">
              {cursorPos ? `+${cursorPos.snr.toFixed(1)} σ` : "-.- σ"}
            </span>
          </div>
        </div>

        {/* Overlay Filters */}
        <div className="flex items-center gap-1.5 text-[10px] font-mono">
          <button
            onClick={() =>
              setOverlays((o) => ({ ...o, showSpectrogram: !o.showSpectrogram }))
            }
            className={`px-2 py-0.5 rounded transition-colors border ${
              overlays.showSpectrogram
                ? "bg-white/[0.08] border-white/[0.2] text-white"
                : "bg-transparent border-white/[0.06] text-sonar-muted"
            }`}
          >
            STFT
          </button>
          <button
            onClick={() =>
              setOverlays((o) => ({ ...o, showRawRidges: !o.showRawRidges }))
            }
            className={`px-2 py-0.5 rounded transition-colors border ${
              overlays.showRawRidges
                ? "bg-sonar-amber/10 border-sonar-amber/30 text-sonar-amber"
                : "bg-transparent border-white/[0.06] text-sonar-muted"
            }`}
          >
            Viterbi
          </button>
          <button
            onClick={() =>
              setOverlays((o) => ({
                ...o,
                showFittedCurves: !o.showFittedCurves,
              }))
            }
            className={`px-2 py-0.5 rounded transition-colors border ${
              overlays.showFittedCurves
                ? "bg-sonar-cyan/10 border-sonar-cyan/30 text-sonar-cyan"
                : "bg-transparent border-white/[0.06] text-sonar-muted"
            }`}
          >
            Fitted f0
          </button>
          <button
            onClick={() =>
              setOverlays((o) => ({ ...o, showHarmonics: !o.showHarmonics }))
            }
            className={`px-2 py-0.5 rounded transition-colors border ${
              overlays.showHarmonics
                ? "bg-sonar-cyan/10 border-sonar-cyan/30 text-sonar-cyan"
                : "bg-transparent border-white/[0.06] text-sonar-muted"
            }`}
          >
            2f0, 3f0
          </button>
          {chaffCurves.length > 0 && (
            <button
              onClick={() =>
                setOverlays((o) => ({ ...o, showChaff: !o.showChaff }))
              }
              className={`px-2 py-0.5 rounded transition-colors border ${
                overlays.showChaff
                  ? "bg-sonar-red/10 border-sonar-red/30 text-sonar-red"
                  : "bg-transparent border-white/[0.06] text-sonar-muted"
              }`}
            >
              Chaff
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
              className={`px-2 py-0.5 rounded transition-colors border ${
                overlays.showAdsbCurves
                  ? "bg-sonar-green/10 border-sonar-green/30 text-sonar-green"
                  : "bg-transparent border-white/[0.06] text-sonar-muted"
              }`}
            >
              ADS-B
            </button>
          )}
        </div>
      </div>

      {/* Main Canvas */}
      <div className="relative w-full overflow-hidden bg-[#0A0D12]">
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="w-full cursor-crosshair block"
        />
      </div>
    </div>
  );
}
