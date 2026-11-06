"use client";

import React, { useState } from "react";
import { ShieldCheck, Download, Shield, Sliders, Play, AlertCircle, CheckCircle2 } from "lucide-react";
import SpectrogramCanvas from "./SpectrogramCanvas";
import { cloakAudio, CloakResponse } from "@/lib/api";

interface CloakPanelProps {
  initialData?: CloakResponse | null;
}

export default function CloakPanel({ initialData }: CloakPanelProps) {
  const [cloakData, setCloakData] = useState<CloakResponse | null>(initialData || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sanitization parameter controls
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
    <div className="space-y-6">
      {/* Sanitization Control Deck */}
      <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck className="w-5 h-5 text-sonar-green" />
              <h2 className="text-lg font-bold tracking-tight text-white uppercase">
                Pillar 2: Active Privacy Cloaking
              </h2>
            </div>
            <p className="text-xs text-sonar-muted max-w-2xl">
              Defeats ADS-B acoustic geolocation tools using a 3-layer defense: dynamic STFT notch
              resynthesis, phase-continuous synthetic decoy chaff, and sub-perceptual time-base warping.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="cursor-pointer px-4 py-2 bg-sonar-card hover:bg-sonar-border border border-sonar-border hover:border-sonar-green text-xs font-mono rounded-lg transition-all flex items-center gap-2 text-white">
              <span>Sanitize Uploaded File</span>
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
              className="px-4 py-2 bg-sonar-green/10 hover:bg-sonar-green/20 border border-sonar-green/40 hover:border-sonar-green text-sonar-green font-mono text-xs rounded-lg transition-all flex items-center gap-2"
            >
              <Shield className="w-4 h-4" />
              <span>{loading ? "Sanitizing..." : "Sanitize Demo Recording"}</span>
            </button>
          </div>
        </div>

        {/* 3-Layer Parameter Adjusters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-sonar-bg/70 rounded-lg border border-sonar-border/80">
          {/* Layer 1: Surgical STFT Notch */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-white">
                Layer 1: Surgical STFT Notch
              </span>
              <input
                type="checkbox"
                checked={enableNotch}
                onChange={(e) => setEnableNotch(e.target.checked)}
                className="accent-sonar-green cursor-pointer"
              />
            </div>
            <p className="text-[11px] text-sonar-muted leading-relaxed">
              Erases detected blade-pass ridges (±2.5 Hz) and harmonics, replacing energy with local noise floor.
            </p>
          </div>

          {/* Layer 2: Synthetic Decoy Chaff */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-white">
                Layer 2: Decoy Chaff Count
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
              className="w-full accent-sonar-green cursor-pointer"
            />
            <p className="text-[11px] text-sonar-muted">
              Poisons search algorithms with realistic fake propeller curves at -50 dBFS.
            </p>
          </div>

          {/* Layer 3: Time-Base & Pitch Warping */}
          <div className="space-y-2">
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
              className="w-full accent-sonar-green cursor-pointer"
            />
            <p className="text-[11px] text-sonar-muted">
              Oscillates playback speed by ±{warpPct}% over 22s to break locked multi-event temporal offsets.
            </p>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-sonar-red/15 border border-sonar-red/40 rounded-lg text-xs font-mono text-sonar-red">
            {error}
          </div>
        )}
      </div>

      {/* Before / After Comparison */}
      {cloakData && (
        <div className="space-y-6">
          {/* Export Action Card */}
          <div className="bg-sonar-card border border-sonar-green/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-sonar-green" />
              <div>
                <h3 className="text-sm font-semibold font-mono text-white">
                  Media Sanitized & Container Metadata Stripped
                </h3>
                <p className="text-xs text-sonar-muted">
                  Doppler trajectories neutralized to 0 dB SNR. QuickTime/EXIF GPS metadata purged.
                </p>
              </div>
            </div>

            <a
              href={`http://127.0.0.1:8000${cloakData.download_url}`}
              download={cloakData.filename}
              className="px-4 py-2 bg-sonar-green text-sonar-bg font-mono font-semibold text-xs rounded-lg hover:bg-sonar-green/90 transition-all flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              <span>Download Sanitized Media</span>
            </a>
          </div>

          {/* Dual Spectrogram View */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-2">
              <span className="text-xs font-mono text-sonar-red uppercase tracking-wider block">
                Original Input (Vulnerable Doppler Signature)
              </span>
              <SpectrogramCanvas
                imageDataUri={cloakData.spectrogram_before_uri}
                detections={cloakData.audit_before?.detections}
                title="Before Cloak: Unprotected Leak"
                height={280}
              />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-mono text-sonar-green uppercase tracking-wider block">
                Sanitized Output (Chaff Injection & Dynamic Notch)
              </span>
              <SpectrogramCanvas
                imageDataUri={cloakData.spectrogram_after_uri}
                chaffCurves={cloakData.chaff_manifest.map((c) => ({
                  times: [c.t0_cpa_s - 15, c.t0_cpa_s, c.t0_cpa_s + 15],
                  freqs: [c.f0_hz + 8, c.f0_hz, c.f0_hz - 8],
                  label: c.chaff_id,
                }))}
                title="After Cloak: Geolocation Defense Active"
                height={280}
              />
            </div>
          </div>

          {/* Injected Decoy Chaff Manifest */}
          <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl">
            <h3 className="text-xs font-mono uppercase tracking-wider text-sonar-muted mb-4">
              Injected Decoy Chaff Manifest ({cloakData.chaff_manifest.length} Poison Decoys)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {cloakData.chaff_manifest.map((chaff) => (
                <div
                  key={chaff.chaff_id}
                  className="bg-sonar-bg/70 border border-sonar-border rounded-lg p-3 text-xs font-mono space-y-1"
                >
                  <div className="flex items-center justify-between text-sonar-green font-bold">
                    <span>{chaff.chaff_id}</span>
                    <span className="text-[10px] text-sonar-muted">{chaff.level_dbfs} dBFS</span>
                  </div>
                  <div className="text-sonar-text">f0: {chaff.f0_hz.toFixed(1)} Hz</div>
                  <div className="text-sonar-muted text-[11px]">
                    v: {chaff.velocity_ms.toFixed(0)} m/s | d: {chaff.slant_distance_m.toFixed(0)}m
                  </div>
                  <div className="text-sonar-cyan text-[11px]">
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
