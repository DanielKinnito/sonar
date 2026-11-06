"use client";

import React, { useState } from "react";
import { Cpu, ShieldCheck, AlertTriangle, Activity, Waves, Gauge, Upload, Search } from "lucide-react";
import SpectrogramCanvas from "./SpectrogramCanvas";
import { verifyPhysics, PhysicsReport } from "@/lib/api";

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

  const verdictStyles: Record<string, string> = {
    PHYSICALLY_AUTHENTIC: "bg-sonar-green/20 text-sonar-green border-sonar-green",
    LIKELY_PHYSICALLY_AUTHENTIC: "bg-sonar-cyan/20 text-sonar-cyan border-sonar-cyan",
    AI_GENERATED_OR_MANIPULATED: "bg-sonar-red/20 text-sonar-red border-sonar-red animate-pulse",
    INCONCLUSIVE: "bg-sonar-amber/20 text-sonar-amber border-sonar-amber",
  };

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Cpu className="w-5 h-5 text-sonar-amber" />
              <h2 className="text-lg font-bold tracking-tight text-white uppercase">
                Sub-Mode 3B: AI / Synthetic Audio Inspector
              </h2>
            </div>
            <p className="text-xs text-sonar-muted max-w-2xl">
              Generative video and audio models (Sora, ElevenLabs, etc.) mimic pitch drops but violate
              retarded-time wave propagation and harmonic rotor phase locking. Evaluates ε_harm and ε_kin.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleRunVerify(undefined, true)}
              disabled={loading}
              className="px-4 py-2 bg-sonar-amber/10 hover:bg-sonar-amber/20 border border-sonar-amber/40 hover:border-sonar-amber text-sonar-amber font-mono text-xs rounded-lg transition-all flex items-center gap-2"
            >
              <Activity className="w-4 h-4" />
              <span>{loading ? "Analyzing Waves..." : "Inspect Authentic Demo"}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-sonar-red/15 border border-sonar-red/40 rounded-lg text-xs font-mono text-sonar-red">
            {error}
          </div>
        )}
      </div>

      {/* Spectrogram Canvas */}
      {imageUri && (
        <SpectrogramCanvas
          imageDataUri={imageUri}
          title="Doppler Wave Kinematics & Wavefront Verification"
          height={320}
        />
      )}

      {/* Forensic Verdict & Metrics */}
      {report && (
        <div className="space-y-6">
          <div className="bg-sonar-panel border border-sonar-border rounded-xl p-6 shadow-xl">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
              <span className={`px-4 py-1.5 rounded-lg border text-sm font-bold font-mono ${verdictStyles[report.verdict] || "text-white"}`}>
                VERDICT: {report.verdict}
              </span>
              <span className="font-mono text-xs text-sonar-muted">
                Confidence: <span className="font-bold text-white">{(report.confidence * 100).toFixed(0)}%</span>
              </span>
            </div>

            <p className="text-sm font-mono text-sonar-text leading-relaxed bg-sonar-bg/70 p-4 rounded-lg border border-sonar-border">
              {report.summary}
            </p>

            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Metric 1: Harmonic Lock Residual */}
              <div className="p-4 bg-sonar-bg/60 border border-sonar-border rounded-lg space-y-2">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-sonar-cyan font-bold flex items-center gap-2">
                    <Waves className="w-4 h-4" />
                    Harmonic Lock Residual (ε_harm)
                  </span>
                  <span className="text-[10px] text-sonar-muted">Physical Threshold: &lt; 0.00500</span>
                </div>
                <p className="text-[11px] text-sonar-muted leading-relaxed">
                  Genuine rotor acoustics maintain exact integer harmonic frequencies (fk ≡ k · f1).
                  Neural generative models exhibit frequency-dependent phase and pitch drift.
                </p>
              </div>

              {/* Metric 2: Kinematic Fit Residual */}
              <div className="p-4 bg-sonar-bg/60 border border-sonar-border rounded-lg space-y-2">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-sonar-amber font-bold flex items-center gap-2">
                    <Gauge className="w-4 h-4" />
                    Kinematic Fit Residual (ε_kin)
                  </span>
                  <span className="text-[10px] text-sonar-muted">Physical Threshold: &lt; 0.85 Hz</span>
                </div>
                <p className="text-[11px] text-sonar-muted leading-relaxed">
                  Fits exact 3D retarded-time wave equation. Evaluates whether implied velocity and
                  maximum inflection slope |df/dt| = f0·v²/(c·d) are physically realizable.
                </p>
              </div>
            </div>
          </div>

          {/* Pass Details */}
          {report.passes.length > 0 && (
            <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl space-y-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-sonar-muted">
                Evaluated Vehicle / Aircraft Doppler Passes ({report.passes.length})
              </h3>
              <div className="space-y-3">
                {report.passes.map((p) => (
                  <div
                    key={p.pass_id}
                    className="p-4 bg-sonar-bg/80 border border-sonar-border rounded-lg space-y-3 text-xs font-mono"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sonar-border/50 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{p.pass_id}</span>
                        <span className="text-sonar-muted text-[11px]">
                          f0={p.f0_hz.toFixed(1)}Hz | v={p.velocity_ms.toFixed(1)}m/s | d={p.slant_distance_m.toFixed(0)}m
                        </span>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${verdictStyles[p.verdict] || "text-white"}`}>
                        {p.verdict}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                      <div>
                        <span className="text-sonar-muted text-[10px] block">KINEMATIC RESIDUAL (ε_kin)</span>
                        <span className={`font-bold ${p.epsilon_kin_hz < 0.85 ? "text-sonar-green" : "text-sonar-red"}`}>
                          {p.epsilon_kin_hz.toFixed(3)} Hz
                        </span>
                      </div>
                      <div>
                        <span className="text-sonar-muted text-[10px] block">HARMONIC LOCK (ε_harm)</span>
                        <span className={`font-bold ${p.epsilon_harm !== null && p.epsilon_harm < 0.005 ? "text-sonar-green" : (p.epsilon_harm !== null ? "text-sonar-red" : "text-sonar-muted")}`}>
                          {p.epsilon_harm !== null ? p.epsilon_harm.toFixed(5) : "Single Harmonic"}
                        </span>
                      </div>
                      <div>
                        <span className="text-sonar-muted text-[10px] block">CPA INFLECTION SLOPE</span>
                        <span className="text-white font-bold">{p.inflection_slope_hz_s.toFixed(2)} Hz/s</span>
                      </div>
                      <div>
                        <span className="text-sonar-muted text-[10px] block">MULTI-HARMONICS</span>
                        <span className="text-sonar-cyan font-bold">{p.has_harmonics ? "Locked (2x, 3x)" : "Single"}</span>
                      </div>
                    </div>

                    <p className="text-[11px] text-sonar-muted bg-sonar-card/60 p-2.5 rounded border border-sonar-border/60">
                      {p.rationale}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
