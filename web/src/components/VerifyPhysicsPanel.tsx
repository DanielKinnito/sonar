"use client";

import React, { useState } from "react";
import { Cpu, Activity, Waves, Gauge, Upload, Search } from "lucide-react";
import SpectrogramCanvas from "./SpectrogramCanvas";
import { verifyPhysics, PhysicsReport } from "@/lib/api";

const verdictStyles: Record<string, string> = {
  PHYSICALLY_AUTHENTIC: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  LIKELY_PHYSICALLY_AUTHENTIC: "bg-sky-500/10 text-sky-400 border-sky-500/30",
  AI_GENERATED_OR_MANIPULATED: "bg-red-500/10 text-red-400 border-red-500/30",
  INCONCLUSIVE: "bg-amber-500/10 text-amber-400 border-amber-500/30",
};

export default function VerifyPhysicsPanel() {
  const [report, setReport] = useState<PhysicsReport | null>(null);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [freqMin, setFreqMin] = useState<number>(40.0);
  const [freqMax, setFreqMax] = useState<number>(450.0);

  const handleRunVerify = async (file?: File, demo = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await verifyPhysics(file, demo, freqMin, freqMax);
      setReport(res.physics_report);
      setImageUri(res.spectrogram_image_uri);
    } catch (err: any) {
      setError(err.message || "Failed to inspect audio physics.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleRunVerify(file, false);
  };

  return (
    <div className="space-y-5">
      {/* Physics Inspector Deck */}
      <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-4 sm:p-5">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sonar-amber" />
              <h2 className="text-sm font-mono font-bold tracking-wider text-white uppercase">
                Pillar 3B: AI & Synthetic Audio Physics Forensics
              </h2>
            </div>
            <p className="text-xs text-sonar-secondary max-w-2xl leading-relaxed">
              Generative video and audio models (Sora, ElevenLabs) mimic pitch drops but violate
              retarded-time wave propagation and harmonic rotor phase locking. Evaluates ε_harm and ε_kin.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <label className="cursor-pointer px-3 py-1.5 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-mono rounded transition-colors flex items-center gap-1.5 text-white">
              <span>Upload Audio</span>
              <input
                type="file"
                accept="audio/*,video/*,.wav,.mp4,.mov,.mkv,.flac"
                className="hidden"
                onChange={handleFileUpload}
                disabled={loading}
              />
            </label>

            <button
              onClick={() => handleRunVerify(undefined, true)}
              disabled={loading}
              className="px-3.5 py-1.5 bg-sonar-amber/15 hover:bg-sonar-amber/25 border border-sonar-amber/40 text-sonar-amber font-mono text-xs font-medium rounded transition-colors flex items-center gap-1.5"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>{loading ? "Analyzing Waves..." : "Inspect Authentic Demo"}</span>
            </button>
          </div>
        </div>

        {/* Bandwidth Selector */}
        <div className="grid grid-cols-2 gap-3 p-3 bg-[#0B0E14] rounded border border-white/[0.06]">
          <div>
            <label className="text-[9px] font-mono text-sonar-muted block mb-1 uppercase tracking-wider">
              MINIMUM FREQUENCY (HZ)
            </label>
            <input
              type="number"
              value={freqMin}
              onChange={(e) => setFreqMin(parseFloat(e.target.value))}
              className="w-full bg-[#12161F] border border-white/[0.08] rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-sonar-amber"
            />
          </div>
          <div>
            <label className="text-[9px] font-mono text-sonar-muted block mb-1 uppercase tracking-wider">
              MAXIMUM FREQUENCY (HZ)
            </label>
            <input
              type="number"
              value={freqMax}
              onChange={(e) => setFreqMax(parseFloat(e.target.value))}
              className="w-full bg-[#12161F] border border-white/[0.08] rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-sonar-amber"
            />
          </div>
        </div>

        {error && (
          <div className="mt-3 p-2.5 bg-red-500/10 border border-red-500/25 rounded text-xs font-mono text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Spectrogram Canvas */}
      {imageUri && (
        <SpectrogramCanvas
          imageDataUri={imageUri}
          title="DOPPLER WAVE KINEMATICS & WAVEFRONT VERIFICATION"
          height={300}
        />
      )}

      {/* Forensic Verdict & Metrics */}
      {report && (
        <div className="space-y-4">
          <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-5">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
              <span className={`px-2.5 py-1 rounded border text-xs font-mono font-bold ${verdictStyles[report.verdict] || "text-white"}`}>
                VERDICT: {report.verdict}
              </span>
              <span className="font-mono text-xs text-sonar-muted">
                CONFIDENCE: <span className="font-bold text-white">{(report.confidence * 100).toFixed(0)}%</span>
              </span>
            </div>

            <p className="text-xs text-sonar-secondary leading-relaxed bg-[#0B0E14] p-3 rounded border border-white/[0.05] mb-4">
              {report.summary}
            </p>

            {/* Metric Threshold Guide Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              <div className="p-3 bg-[#0B0E14] rounded border border-white/[0.06] space-y-1.5">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-sonar-cyan font-bold flex items-center gap-1.5">
                    <Waves className="w-3.5 h-3.5" />
                    Harmonic Lock Residual (ε_harm)
                  </span>
                  <span className="text-[9px] text-sonar-muted">Threshold: &lt; 0.005</span>
                </div>
                <p className="text-[10px] text-sonar-muted leading-relaxed">
                  Genuine rotor acoustics maintain exact integer harmonic frequencies (fk ≡ k · f1).
                  Neural generative models exhibit frequency-dependent phase and pitch drift.
                </p>
              </div>

              <div className="p-3 bg-[#0B0E14] rounded border border-white/[0.06] space-y-1.5">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-sonar-amber font-bold flex items-center gap-1.5">
                    <Gauge className="w-3.5 h-3.5" />
                    Kinematic Fit Residual (ε_kin)
                  </span>
                  <span className="text-[9px] text-sonar-muted">Threshold: &lt; 0.85 Hz</span>
                </div>
                <p className="text-[10px] text-sonar-muted leading-relaxed">
                  Fits exact 3D retarded-time wave equation. Evaluates whether implied velocity and
                  maximum inflection slope |df/dt| = f0·v²/(c·d) are physically realizable.
                </p>
              </div>
            </div>

            {/* Passes Detail List */}
            {report.passes.length > 0 && (
              <div className="space-y-2">
                <span className="text-[10px] font-mono text-sonar-muted uppercase tracking-wider block">
                  EVALUATED PASSES ({report.passes.length})
                </span>
                <div className="space-y-2.5">
                  {report.passes.map((p) => (
                    <div
                      key={p.pass_id}
                      className="p-3 bg-[#0B0E14] border border-white/[0.06] rounded font-mono text-xs space-y-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.05] pb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-xs">{p.pass_id}</span>
                          <span className="text-sonar-muted text-[10px]">
                            f0={p.f0_hz.toFixed(1)}Hz | v={p.velocity_ms.toFixed(1)}m/s | d={p.slant_distance_m.toFixed(0)}m
                          </span>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${verdictStyles[p.verdict] || "text-white"}`}>
                          {p.verdict}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                        <div className="p-1.5 bg-[#12161F] rounded border border-white/[0.04]">
                          <span className="text-sonar-muted text-[9px] block">KINEMATIC RESIDUAL</span>
                          <span className={`font-bold ${p.epsilon_kin_hz < 0.85 ? "text-emerald-400" : "text-red-400"}`}>
                            {p.epsilon_kin_hz.toFixed(3)} Hz
                          </span>
                        </div>
                        <div className="p-1.5 bg-[#12161F] rounded border border-white/[0.04]">
                          <span className="text-sonar-muted text-[9px] block">HARMONIC LOCK</span>
                          <span className={`font-bold ${p.epsilon_harm !== null && p.epsilon_harm < 0.005 ? "text-emerald-400" : (p.epsilon_harm !== null ? "text-red-400" : "text-sonar-muted")}`}>
                            {p.epsilon_harm !== null ? p.epsilon_harm.toFixed(5) : "Single"}
                          </span>
                        </div>
                        <div className="p-1.5 bg-[#12161F] rounded border border-white/[0.04]">
                          <span className="text-sonar-muted text-[9px] block">CPA INFLECTION</span>
                          <span className="text-white font-bold">{p.inflection_slope_hz_s.toFixed(2)} Hz/s</span>
                        </div>
                        <div className="p-1.5 bg-[#12161F] rounded border border-white/[0.04]">
                          <span className="text-sonar-muted text-[9px] block">HARMONIC RATIO</span>
                          <span className="text-sonar-cyan font-bold">{p.has_harmonics ? "Locked (2x, 3x)" : "Single"}</span>
                        </div>
                      </div>

                      <p className="text-[10px] text-sonar-secondary bg-[#12161F] p-2 rounded border border-white/[0.04]">
                        {p.rationale}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
