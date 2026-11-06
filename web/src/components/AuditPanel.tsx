"use client";

import React, { useState } from "react";
import { Upload, AlertTriangle, CheckCircle, ShieldAlert, Radio, Activity, Compass, Wind } from "lucide-react";
import SpectrogramCanvas from "./SpectrogramCanvas";
import { auditAudio, AuditResponse } from "@/lib/api";

interface AuditPanelProps {
  initialData?: AuditResponse | null;
}

export default function AuditPanel({ initialData }: AuditPanelProps) {
  const [auditData, setAuditData] = useState<AuditResponse | null>(initialData || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [planesCount, setPlanesCount] = useState<number>(2);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const data = await auditAudio(file);
      setAuditData(data);
    } catch (err: any) {
      setError(err.message || "Failed to audit file.");
    } finally {
      setLoading(false);
    }
  };

  const handleRunDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await auditAudio(undefined, true, planesCount);
      setAuditData(data);
    } catch (err: any) {
      setError(err.message || "Failed to generate demo fixture.");
    } finally {
      setLoading(false);
    }
  };

  const assessment = auditData?.leak_assessment;
  const risk = assessment?.risk_level || "CLEAN";

  const riskBadgeStyle = {
    CRITICAL: "bg-sonar-red/20 text-sonar-red border-sonar-red animate-pulse",
    MODERATE: "bg-sonar-amber/20 text-sonar-amber border-sonar-amber",
    LOW: "bg-blue-500/20 text-blue-400 border-blue-500",
    CLEAN: "bg-sonar-green/20 text-sonar-green border-sonar-green",
  }[risk];

  return (
    <div className="space-y-6">
      {/* Action Header Card */}
      <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Radio className="w-5 h-5 text-sonar-cyan" />
              <h2 className="text-lg font-bold tracking-tight text-white uppercase">
                Pillar 1: Acoustic Leak Audit
              </h2>
            </div>
            <p className="text-xs text-sonar-muted max-w-2xl">
              Extracts sub-audible 40–450 Hz propeller blade-pass Doppler ridges from video audio
              tracks, fits the retarded-time acoustic equation, and evaluates geolocation leak risk.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="cursor-pointer px-4 py-2 bg-sonar-card hover:bg-sonar-border border border-sonar-border hover:border-sonar-cyan text-xs font-mono rounded-lg transition-all flex items-center gap-2 text-white">
              <Upload className="w-4 h-4 text-sonar-cyan" />
              <span>Select Audio / Video</span>
              <input
                type="file"
                accept="audio/*,video/*,.wav,.mp4,.mov,.mkv,.flac"
                className="hidden"
                onChange={handleFileUpload}
                disabled={loading}
              />
            </label>

            <button
              onClick={handleRunDemo}
              disabled={loading}
              className="px-4 py-2 bg-sonar-cyan/10 hover:bg-sonar-cyan/20 border border-sonar-cyan/40 hover:border-sonar-cyan text-sonar-cyan font-mono text-xs rounded-lg transition-all flex items-center gap-2"
            >
              <Activity className="w-4 h-4" />
              <span>{loading ? "Computing STFT..." : "Load Synthetic Fixture"}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-sonar-red/15 border border-sonar-red/40 rounded-lg text-xs font-mono text-sonar-red">
            {error}
          </div>
        )}
      </div>

      {/* Main Interactive Spectrogram Canvas */}
      <SpectrogramCanvas
        spectrogram={auditData?.spectrogram}
        imageDataUri={auditData?.image_data_uri}
        detections={assessment?.detections}
        title="Whitened Acoustic Spectrogram (40 - 450 Hz) & Doppler Physics Overlays"
        height={380}
      />

      {/* Leak Assessment & Detections Breakdown */}
      {assessment && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Risk Level Card */}
          <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl flex flex-col justify-between">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-sonar-muted">
                Geolocation Vulnerability Score
              </span>
              <div className="flex items-center justify-between mt-2 mb-4">
                <span className={`px-3 py-1 rounded border text-sm font-bold font-mono ${riskBadgeStyle}`}>
                  {risk} RISK
                </span>
                <span className="text-2xl font-black font-mono text-white">
                  {assessment.risk_score.toFixed(1)}
                  <span className="text-xs text-sonar-muted font-normal"> / 10.0</span>
                </span>
              </div>
              <p className="text-xs text-sonar-text leading-relaxed bg-sonar-bg/60 p-3 rounded-lg border border-sonar-border/80">
                {assessment.risk_rationale}
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-sonar-border/80 grid grid-cols-2 gap-2 text-xs font-mono">
              <div>
                <span className="text-sonar-muted text-[10px] block">TOTAL DETECTIONS</span>
                <span className="text-lg font-bold text-sonar-cyan">{assessment.num_detections}</span>
              </div>
              <div>
                <span className="text-sonar-muted text-[10px] block">SAMPLE RATE</span>
                <span className="text-lg font-bold text-white">{auditData?.fs} Hz</span>
              </div>
            </div>
          </div>

          {/* Detected Aircraft Cards */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-mono uppercase tracking-wider text-sonar-muted">
                Detected Doppler Curves & Inferred Flight Kinematics
              </h3>
              <span className="text-[11px] font-mono text-sonar-cyan">
                {assessment.detections.length} candidate passes
              </span>
            </div>

            {assessment.detections.length === 0 ? (
              <div className="bg-sonar-panel border border-sonar-border rounded-xl p-8 text-center text-sonar-muted text-xs font-mono">
                No acoustic Doppler signatures detected in the 40–450 Hz band. Media is clean.
              </div>
            ) : (
              <div className="space-y-3">
                {assessment.detections.map((det) => {
                  const p = det.fitted_params;
                  const knots = (p.velocity_ms * 1.94384).toFixed(0);
                  return (
                    <div
                      key={det.detection_id}
                      className="bg-sonar-panel border border-sonar-border hover:border-sonar-cyan/50 rounded-xl p-4 transition-all"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-2 border-b border-sonar-border/60">
                        <div className="flex items-center gap-2">
                          <Compass className="w-4 h-4 text-sonar-amber" />
                          <span className="font-mono font-bold text-white text-sm">
                            {det.detection_id}
                          </span>
                          <span className="text-[11px] font-mono px-2 py-0.5 bg-sonar-card rounded text-sonar-muted">
                            T+{det.start_time_s.toFixed(1)}s → T+{det.end_time_s.toFixed(1)}s (
                            {det.duration_s.toFixed(1)}s pass)
                          </span>
                        </div>
                        <div className="flex items-center gap-3 font-mono text-xs">
                          <span className="text-sonar-green font-semibold">
                            SNR: {det.mean_snr_sigma.toFixed(1)}σ
                          </span>
                          <span className="text-sonar-muted">
                            Fit RMSE: {p.fit_rmse_hz.toFixed(2)} Hz
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                        <div className="bg-sonar-bg/50 p-2.5 rounded border border-sonar-border/50">
                          <span className="text-[10px] text-sonar-muted block">FUNDAMENTAL f0</span>
                          <span className="text-sm font-bold text-sonar-cyan">{p.f0_hz.toFixed(1)} Hz</span>
                        </div>
                        <div className="bg-sonar-bg/50 p-2.5 rounded border border-sonar-border/50">
                          <span className="text-[10px] text-sonar-muted block">SPEED (m/s)</span>
                          <span className="text-sm font-bold text-white">
                            {p.velocity_ms.toFixed(1)} m/s <span className="text-[10px] text-sonar-muted">({knots} kts)</span>
                          </span>
                        </div>
                        <div className="bg-sonar-bg/50 p-2.5 rounded border border-sonar-border/50">
                          <span className="text-[10px] text-sonar-muted block">SLANT CPA DISTANCE</span>
                          <span className="text-sm font-bold text-white">{p.slant_distance_m.toFixed(0)} m</span>
                        </div>
                        <div className="bg-sonar-bg/50 p-2.5 rounded border border-sonar-border/50">
                          <span className="text-[10px] text-sonar-muted block">CPA INFLECTION</span>
                          <span className="text-sm font-bold text-sonar-amber">{p.inflection_slope_hz_s.toFixed(2)} Hz/s</span>
                        </div>
                      </div>

                      {det.harmonics.length > 0 && (
                        <div className="mt-3 pt-2 flex items-center gap-2 text-[11px] font-mono text-sonar-muted">
                          <span className="text-sonar-cyan">Harmonic Locks:</span>
                          {det.harmonics.map((h, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-sonar-cyan/10 text-sonar-cyan rounded border border-sonar-cyan/30">
                              {h.label} ({h.mean_snr_sigma.toFixed(1)}σ)
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
