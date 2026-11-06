"use client";

import React, { useState } from "react";
import { Globe, Search, Plane, AlertOctagon, CheckCircle2, Upload } from "lucide-react";
import SpectrogramCanvas from "./SpectrogramCanvas";
import { verifyAlibi, AlibiReport } from "@/lib/api";

const verdictStyles: Record<string, string> = {
  VERIFIED_MATCH: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  CONTRADICTION_SILENCE_VIOLATION: "bg-red-500/10 text-red-400 border-red-500/30",
  UNVERIFIABLE_QUIET_SKY: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  INCONCLUSIVE: "bg-white/[0.04] text-sonar-secondary border-white/[0.1]",
};

export default function VerifyAlibiPanel() {
  const [report, setReport] = useState<AlibiReport | null>(null);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Claimed observer inputs
  const [lat, setLat] = useState<number>(37.7749);
  const [lon, setLon] = useState<number>(-122.4194);
  const [utcTime, setUtcTime] = useState<string>("2026-06-15T14:00:00Z");
  const [radiusKm, setRadiusKm] = useState<number>(15.0);

  const handleRunVerify = async (file?: File, demo = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await verifyAlibi(file, demo, lat, lon, utcTime, radiusKm);
      setReport(res.alibi_report);
      setImageUri(res.spectrogram_image_uri);
    } catch (err: any) {
      setError(err.message || "Failed to verify spatiotemporal alibi.");
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
      {/* Alibi Mission Parameter Deck */}
      <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-4 sm:p-5">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sonar-cyan" />
              <h2 className="text-sm font-mono font-bold tracking-wider text-white uppercase">
                Pillar 3A: Spatiotemporal Alibi Verifier
              </h2>
            </div>
            <p className="text-xs text-sonar-secondary max-w-2xl leading-relaxed">
              Cross-references media audio against historical ADS-B flight trajectories and AWS Terrarium DEM
              elevations. 3D retarded-time forward modeling predicts acoustic alignment and flags Silence Violations.
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
              className="px-3.5 py-1.5 bg-sonar-cyan/15 hover:bg-sonar-cyan/25 border border-sonar-cyan/40 text-sonar-cyan font-mono text-xs font-medium rounded transition-colors flex items-center gap-1.5"
            >
              <Search className="w-3.5 h-3.5" />
              <span>{loading ? "Modeling Skies..." : "Verify Demo Sky"}</span>
            </button>
          </div>
        </div>

        {/* Claimed Coordinates Form */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-3 bg-[#0B0E14] rounded border border-white/[0.06]">
          <div>
            <label className="text-[9px] font-mono text-sonar-muted block mb-1 uppercase tracking-wider">
              LATITUDE (DEG)
            </label>
            <input
              type="number"
              step="0.0001"
              value={lat}
              onChange={(e) => setLat(parseFloat(e.target.value))}
              className="w-full bg-[#12161F] border border-white/[0.08] rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
          <div>
            <label className="text-[9px] font-mono text-sonar-muted block mb-1 uppercase tracking-wider">
              LONGITUDE (DEG)
            </label>
            <input
              type="number"
              step="0.0001"
              value={lon}
              onChange={(e) => setLon(parseFloat(e.target.value))}
              className="w-full bg-[#12161F] border border-white/[0.08] rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
          <div>
            <label className="text-[9px] font-mono text-sonar-muted block mb-1 uppercase tracking-wider">
              CLAIMED UTC TIME (ISO-8601)
            </label>
            <input
              type="text"
              value={utcTime}
              onChange={(e) => setUtcTime(e.target.value)}
              className="w-full bg-[#12161F] border border-white/[0.08] rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
          <div>
            <label className="text-[9px] font-mono text-sonar-muted block mb-1 uppercase tracking-wider">
              SEARCH RADIUS (KM)
            </label>
            <input
              type="number"
              step="1.0"
              value={radiusKm}
              onChange={(e) => setRadiusKm(parseFloat(e.target.value))}
              className="w-full bg-[#12161F] border border-white/[0.08] rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
        </div>

        {error && (
          <div className="mt-3 p-2.5 bg-red-500/10 border border-red-500/25 rounded text-xs font-mono text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Modeled ADS-B Spectrogram Canvas */}
      {imageUri && (
        <SpectrogramCanvas
          imageDataUri={imageUri}
          adsbCurves={report?.evaluated_flights?.map((f) => ({
            times: f.modeled_curve.times,
            freqs: f.modeled_curve.freqs,
            flight_id: f.flight_id,
            is_match: f.is_acoustic_match,
          }))}
          title="HISTORICAL SKY DOPPLER FORWARD MODEL & ADS-B ALIGNMENT"
          height={320}
        />
      )}

      {/* Forensic Alibi Results */}
      {report && (
        <div className="space-y-4">
          <div className="bg-[#12161F] border border-white/[0.08] rounded-lg p-5">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
              <span className={`px-2.5 py-1 rounded border text-xs font-mono font-bold ${verdictStyles[report.verdict] || "text-white"}`}>
                VERDICT: {report.verdict}
              </span>
              <div className="flex items-center gap-4 text-xs font-mono text-sonar-muted">
                <span>TERRARIUM DEM: {report.claimed_coordinates.observer_elevation_m}m MSL</span>
                <span>MATCH CONFIDENCE: {(report.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>

            <p className="text-xs text-sonar-secondary leading-relaxed bg-[#0B0E14] p-3 rounded border border-white/[0.05] mb-4">
              {report.summary}
            </p>

            {/* Evaluated Flight Details */}
            {report.evaluated_flights.length > 0 && (
              <div className="space-y-2">
                <span className="text-[10px] font-mono text-sonar-muted uppercase tracking-wider block">
                  CORRELATED ADS-B FLIGHT TRAJECTORIES ({report.evaluated_flights.length})
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {report.evaluated_flights.map((fl, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-[#0B0E14] rounded border border-white/[0.06] font-mono text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-xs flex items-center gap-1.5">
                          <Plane className={`w-3.5 h-3.5 ${fl.is_acoustic_match ? "text-emerald-400" : "text-sonar-muted"}`} />
                          {fl.flight_id} ({fl.icao_type})
                        </span>
                        {fl.is_acoustic_match && (
                          <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded text-[9px] font-bold">
                            ACOUSTIC MATCH
                          </span>
                        )}
                        {fl.is_silence_violation && (
                          <span className="px-1.5 py-0.5 bg-red-500/10 text-red-400 border border-red-500/30 rounded text-[9px] font-bold">
                            SILENCE VIOLATION
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-[10px] text-sonar-muted">
                        <div>MIN SLANT: <span className="text-white">{fl.min_slant_m.toFixed(0)}m</span></div>
                        <div>ALIGNMENT: <span className="text-white">{fl.alignment_score_sigma.toFixed(2)} σ</span></div>
                      </div>
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
