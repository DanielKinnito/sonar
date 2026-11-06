"use client";

import React, { useState } from "react";
import { Upload, Radio, Activity, Compass, Info, CheckCircle, ShieldAlert } from "lucide-react";
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
    CRITICAL: "bg-red-500/10 text-red-400 border-red-500/30",
    MODERATE: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    LOW: "bg-sky-500/10 text-sky-400 border-sky-500/30",
    CLEAN: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  }[risk];

  return (
    <div className="space-y-5">
      {/* Instrument Command Deck */}
      <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-4 sm:p-5">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sonar-cyan" />
              <h2 className="text-sm font-mono font-bold tracking-wider text-white uppercase">
                Pillar 1: Acoustic Leak Audit
              </h2>
            </div>
            <p className="text-xs text-sonar-secondary max-w-2xl leading-relaxed">
              Extracts sub-audible 40–450 Hz propeller blade-pass Doppler ridges from video audio
              tracks, fits the retarded-time acoustic equation, and evaluates geolocation leak risk.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center bg-[#0B0E14] px-2 py-1 rounded border border-white/[0.08] text-xs font-mono">
              <span className="text-sonar-muted text-[10px] mr-2">PLANES:</span>
              <select
                value={planesCount}
                onChange={(e) => setPlanesCount(parseInt(e.target.value))}
                className="bg-transparent text-white focus:outline-none cursor-pointer text-xs"
              >
                <option value={1} className="bg-[#12161F]">1 Plane</option>
                <option value={2} className="bg-[#12161F]">2 Planes</option>
                <option value={3} className="bg-[#12161F]">3 Planes</option>
              </select>
            </div>

            <label className="cursor-pointer px-3 py-1.5 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-mono rounded transition-colors flex items-center gap-1.5 text-white">
              <Upload className="w-3.5 h-3.5 text-sonar-secondary" />
              <span>Upload Media</span>
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
              className="px-3.5 py-1.5 bg-sonar-cyan/15 hover:bg-sonar-cyan/25 border border-sonar-cyan/40 text-sonar-cyan font-mono text-xs font-medium rounded transition-colors flex items-center gap-1.5"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>{loading ? "Computing STFT..." : "Load Synthetic Fixture"}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-3 p-2.5 bg-red-500/10 border border-red-500/25 rounded text-xs font-mono text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Main Interactive Spectrogram Canvas */}
      <SpectrogramCanvas
        spectrogram={auditData?.spectrogram}
        imageDataUri={auditData?.image_data_uri}
        detections={assessment?.detections}
        title="WHITENED ACOUSTIC SPECTRUM & FITTED DOPPLER CURVES"
        height={340}
      />

      {/* Assessment Breakdown */}
      {assessment && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Threat Assessment Metric Card */}
          <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono uppercase tracking-wider text-sonar-muted">
                  GEOLOCATION THREAT LEVEL
                </span>
                <span className={`px-2 py-0.5 rounded border text-[11px] font-mono font-medium ${riskBadgeStyle}`}>
                  {risk}
                </span>
              </div>

              <div className="flex items-baseline gap-1 my-3">
                <span className="text-3xl font-mono font-bold text-white tracking-tight">
                  {assessment.risk_score.toFixed(1)}
                </span>
                <span className="text-xs font-mono text-sonar-muted">/ 10.0</span>
              </div>

              <p className="text-xs text-sonar-secondary leading-relaxed bg-[#0B0E14] p-3 rounded border border-white/[0.05]">
                {assessment.risk_rationale}
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-white/[0.06] grid grid-cols-2 gap-2 font-mono text-xs">
              <div>
                <span className="text-sonar-muted text-[10px] block">CANDIDATE PASSES</span>
                <span className="text-base font-semibold text-sonar-cyan">{assessment.num_detections}</span>
              </div>
              <div>
                <span className="text-sonar-muted text-[10px] block">SAMPLE RATE</span>
                <span className="text-base font-semibold text-white">{auditData?.fs} Hz</span>
              </div>
            </div>
          </div>

          {/* Detected Aircraft Kinematics Cards */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-mono uppercase tracking-wider text-sonar-muted">
                INFERRED FLIGHT KINEMATICS & DOPPLER SOLUTIONS
              </h3>
              <span className="text-[11px] font-mono text-sonar-cyan">
                {assessment.detections.length} target{assessment.detections.length === 1 ? "" : "s"} resolved
              </span>
            </div>

            {assessment.detections.length === 0 ? (
              <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-8 text-center text-sonar-muted text-xs font-mono">
                No acoustic Doppler signatures detected in the 40–450 Hz band. Media is clean.
              </div>
            ) : (
              <div className="space-y-2.5">
                {assessment.detections.map((det) => {
                  const p = det.fitted_params;
                  const knots = (p.velocity_ms * 1.94384).toFixed(0);
                  return (
                    <div
                      key={det.detection_id}
                      className="bg-[#12161F] border border-white/[0.08] hover:border-white/[0.18] rounded-lg p-3.5 transition-colors"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5 pb-2 border-b border-white/[0.05]">
                        <div className="flex items-center gap-2">
                          <Compass className="w-3.5 h-3.5 text-sonar-amber" />
                          <span className="font-mono font-bold text-white text-xs">
                            {det.detection_id}
                          </span>
                          <span className="text-[10px] font-mono text-sonar-muted">
                            T+{det.start_time_s.toFixed(1)}s → T+{det.end_time_s.toFixed(1)}s ({det.duration_s.toFixed(1)}s pass)
                          </span>
                        </div>
                        <div className="flex items-center gap-3 font-mono text-xs">
                          <span className="text-sonar-green font-medium">
                            SNR: +{det.mean_snr_sigma.toFixed(1)}σ
                          </span>
                          <span className="text-sonar-muted text-[11px]">
                            RMSE: {p.fit_rmse_hz.toFixed(2)} Hz
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                        <div className="bg-[#0B0E14] p-2 rounded border border-white/[0.05]">
                          <span className="text-[9px] text-sonar-muted block uppercase">FUNDAMENTAL f0</span>
                          <span className="text-xs font-bold text-sonar-cyan">{p.f0_hz.toFixed(1)} Hz</span>
                        </div>
                        <div className="bg-[#0B0E14] p-2 rounded border border-white/[0.05]">
                          <span className="text-[9px] text-sonar-muted block uppercase">SPEED</span>
                          <span className="text-xs font-bold text-white">
                            {p.velocity_ms.toFixed(1)} m/s <span className="text-[9px] text-sonar-muted">({knots} kts)</span>
                          </span>
                        </div>
                        <div className="bg-[#0B0E14] p-2 rounded border border-white/[0.05]">
                          <span className="text-[9px] text-sonar-muted block uppercase">SLANT CPA DISTANCE</span>
                          <span className="text-xs font-bold text-white">{p.slant_distance_m.toFixed(0)} m</span>
                        </div>
                        <div className="bg-[#0B0E14] p-2 rounded border border-white/[0.05]">
                          <span className="text-[9px] text-sonar-muted block uppercase">INFLECTION SLOPE</span>
                          <span className="text-xs font-bold text-sonar-amber">{p.inflection_slope_hz_s.toFixed(2)} Hz/s</span>
                        </div>
                      </div>

                      {det.harmonics.length > 0 && (
                        <div className="mt-2.5 pt-2 flex items-center gap-1.5 text-[10px] font-mono text-sonar-muted">
                          <span className="text-sonar-secondary">HARMONIC LOCKS:</span>
                          {det.harmonics.map((h, i) => (
                            <span key={i} className="px-1.5 py-0.2 bg-white/[0.04] text-sonar-cyan rounded border border-white/[0.08]">
                              {h.label} (+{h.mean_snr_sigma.toFixed(1)}σ)
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
