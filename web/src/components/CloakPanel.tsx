"use client";

import React, { useState } from "react";
import { ShieldCheck, Download, Shield, Sliders, CheckCircle2 } from "lucide-react";
import SpectrogramCanvas from "./SpectrogramCanvas";
import { cloakAudio, CloakResponse } from "@/lib/api";

interface CloakPanelProps {
  initialData?: CloakResponse | null;
}

export default function CloakPanel({ initialData }: CloakPanelProps) {
  const [cloakData, setCloakData] = useState<CloakResponse | null>(initialData || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sanitization parameters
  const [chaffCount, setChaffCount] = useState<number>(5);
  const [warpPct, setWarpPct] = useState<number>(0.35);
  const [enableNotch, setEnableNotch] = useState<boolean>(true);

  const handleRunCloak = async (file?: File, demo = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await cloakAudio(file, demo, chaffCount, warpPct, enableNotch);
      setCloakData(data);
    } catch (err: any) {
      setError(err.message || "Failed to sanitize media.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleRunCloak(file, false);
  };

  return (
    <div className="space-y-5">
      {/* Sanitization Control Deck */}
      <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-4 sm:p-5">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sonar-green" />
              <h2 className="text-sm font-mono font-bold tracking-wider text-white uppercase">
                Pillar 2: Active Privacy Cloak
              </h2>
            </div>
            <p className="text-xs text-sonar-secondary max-w-2xl leading-relaxed">
              Defeats ADS-B acoustic correlation tools using a 3-layer defense: surgical STFT notch resynthesis,
              synthetic decoy chaff injection, and sub-perceptual time-base warping.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <label className="cursor-pointer px-3 py-1.5 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-mono rounded transition-colors flex items-center gap-1.5 text-white">
              <span>Sanitize File</span>
              <input
                type="file"
                accept="audio/*,video/*,.wav,.mp4,.mov,.mkv,.flac"
                className="hidden"
                onChange={handleFileUpload}
                disabled={loading}
              />
            </label>

            <button
              onClick={() => handleRunCloak(undefined, true)}
              disabled={loading}
              className="px-3.5 py-1.5 bg-sonar-green/15 hover:bg-sonar-green/25 border border-sonar-green/40 text-sonar-green font-mono text-xs font-medium rounded transition-colors flex items-center gap-1.5"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>{loading ? "Sanitizing..." : "Sanitize Demo Recording"}</span>
            </button>
          </div>
        </div>

        {/* 3-Layer Parameter Sliders */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 p-3.5 bg-[#0B0E14] rounded border border-white/[0.06]">
          {/* Layer 1: Surgical STFT Notch */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-white">
                Layer 1: Surgical Notch
              </span>
              <input
                type="checkbox"
                checked={enableNotch}
                onChange={(e) => setEnableNotch(e.target.checked)}
                className="accent-sonar-green cursor-pointer h-3.5 w-3.5"
              />
            </div>
            <p className="text-[10px] font-mono text-sonar-muted leading-relaxed">
              Erases detected ridges (±2.5 Hz) and harmonics, replacing energy with local noise floor (0 dB SNR).
            </p>
          </div>

          {/* Layer 2: Decoy Chaff */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-white">
                Layer 2: Decoy Chaff
              </span>
              <span className="font-mono text-xs text-sonar-green font-bold">
                {chaffCount} aircraft
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              step={1}
              value={chaffCount}
              onChange={(e) => setChaffCount(parseInt(e.target.value))}
              className="w-full cursor-pointer"
            />
            <p className="text-[10px] font-mono text-sonar-muted">
              Injects realistic fake propeller curves at -50 dBFS to poison candidate search algorithms.
            </p>
          </div>

          {/* Layer 3: Time-Base Drift */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-white">
                Layer 3: Time-Base Drift
              </span>
              <span className="font-mono text-xs text-sonar-green font-bold">
                ±{warpPct.toFixed(2)}%
              </span>
            </div>
            <input
              type="range"
              min={0.0}
              max={0.8}
              step={0.05}
              value={warpPct}
              onChange={(e) => setWarpPct(parseFloat(e.target.value))}
              className="w-full cursor-pointer"
            />
            <p className="text-[10px] font-mono text-sonar-muted">
              Oscillates playback speed over 22s windows to break locked multi-event temporal offsets.
            </p>
          </div>
        </div>

        {error && (
          <div className="mt-3 p-2.5 bg-red-500/10 border border-red-500/25 rounded text-xs font-mono text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Before / After Comparison */}
      {cloakData && (
        <div className="space-y-5">
          {/* Export Action Card */}
          <div className="bg-[#12161F] border border-sonar-green/30 rounded-lg p-3.5 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-sonar-green shrink-0" />
              <div>
                <h3 className="text-xs font-mono font-bold text-white">
                  Media Sanitized & QuickTime/EXIF GPS Metadata Purged
                </h3>
                <p className="text-[11px] text-sonar-muted">
                  Doppler trajectories dropped to 0 dB SNR. Decoy chaff injected. Clean container remuxed.
                </p>
              </div>
            </div>

            <a
              href={`http://127.0.0.1:8000${cloakData.download_url}`}
              download={cloakData.filename}
              className="px-3.5 py-1.5 bg-sonar-green text-[#0B0E14] font-mono font-bold text-xs rounded hover:bg-sonar-green/90 transition-colors flex items-center gap-1.5 shrink-0"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Sanitized Media</span>
            </a>
          </div>

          {/* Dual Spectrogram View */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono text-red-400 uppercase tracking-wider block">
                ORIGINAL INPUT: VULNERABLE DOPPLER TRACK
              </span>
              <SpectrogramCanvas
                imageDataUri={cloakData.spectrogram_before_uri}
                detections={cloakData.audit_before?.detections}
                title="BEFORE: UNPROTECTED RECORDING"
                height={260}
              />
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider block">
                SANITIZED OUTPUT: NOTCHED RIDGE + INJECTED CHAFF
              </span>
              <SpectrogramCanvas
                imageDataUri={cloakData.spectrogram_after_uri}
                chaffCurves={cloakData.chaff_manifest.map((c) => ({
                  times: [c.t0_cpa_s - 15, c.t0_cpa_s, c.t0_cpa_s + 15],
                  freqs: [c.f0_hz + 8, c.f0_hz, c.f0_hz - 8],
                  label: c.chaff_id,
                }))}
                title="AFTER: SANITIZED WITH CHAFF"
                height={260}
              />
            </div>
          </div>

          {/* Decoy Chaff Manifest Breakdown */}
          <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-4">
            <h3 className="text-xs font-mono uppercase tracking-wider text-sonar-muted mb-3">
              INJECTED DECOY CHAFF SIGNATURES ({cloakData.chaff_manifest.length} DECOYS)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2.5">
              {cloakData.chaff_manifest.map((chaff) => (
                <div
                  key={chaff.chaff_id}
                  className="bg-[#0B0E14] border border-white/[0.06] rounded p-2.5 text-xs font-mono space-y-1"
                >
                  <div className="flex items-center justify-between text-sonar-green font-bold">
                    <span>{chaff.chaff_id}</span>
                    <span className="text-[9px] text-sonar-muted">{chaff.level_dbfs} dBFS</span>
                  </div>
                  <div className="text-white text-xs font-semibold">f0: {chaff.f0_hz.toFixed(1)} Hz</div>
                  <div className="text-sonar-muted text-[10px]">
                    v: {chaff.velocity_ms.toFixed(0)} m/s | d: {chaff.slant_distance_m.toFixed(0)}m
                  </div>
                  <div className="text-sonar-cyan text-[10px]">
                    CPA: T+{chaff.t0_cpa_s.toFixed(1)}s
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
