"use client";

import React, { useState } from "react";
import { MapPin, Globe, Plane, AlertOctagon, CheckCircle2, HelpCircle, Upload, Search } from "lucide-react";
import SpectrogramCanvas from "./SpectrogramCanvas";
import { verifyAlibi, AlibiReport } from "@/lib/api";

export default function VerifyAlibiPanel() {
  const [report, setReport] = useState<AlibiReport | null>(null);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Form controls
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
      setError(err.message || "Failed to verify alibi.");
    } finally {
      setLoading(false);
    }
  };

  const verdictStyles: Record<string, string> = {
    VERIFIED_MATCH: "bg-sonar-green/20 text-sonar-green border-sonar-green",
    CONTRADICTION_SILENCE_VIOLATION: "bg-sonar-red/20 text-sonar-red border-sonar-red animate-pulse",
    UNVERIFIABLE_QUIET_SKY: "bg-sonar-amber/20 text-sonar-amber border-sonar-amber",
    INCONCLUSIVE: "bg-blue-500/20 text-blue-400 border-blue-500",
  };

  return (
    <div className="space-y-6">
      {/* Search & Coordinate Input Deck */}
      <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Globe className="w-5 h-5 text-sonar-cyan" />
              <h2 className="text-lg font-bold tracking-tight text-white uppercase">
                Sub-Mode 3A: Spatiotemporal Alibi Verifier
              </h2>
            </div>
            <p className="text-xs text-sonar-muted max-w-2xl">
              Cross-references media audio against historical ADS-B flight trajectories and AWS Terrarium DEM
              elevations. 3D retarded-time forward modeling predicts acoustic alignment and flags Silence Violations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleRunVerify(undefined, true)}
              disabled={loading}
              className="px-4 py-2 bg-sonar-cyan/10 hover:bg-sonar-cyan/20 border border-sonar-cyan/40 hover:border-sonar-cyan text-sonar-cyan font-mono text-xs rounded-lg transition-all flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              <span>{loading ? "Modeling Skies..." : "Verify Demo Sky"}</span>
            </button>
          </div>
        </div>

        {/* Claimed Coordinates Form */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-sonar-bg/70 rounded-lg border border-sonar-border">
          <div>
            <label className="text-[10px] font-mono text-sonar-muted block mb-1">OBSERVER LATITUDE</label>
            <input
              type="number"
              step="0.0001"
              value={lat}
              onChange={(e) => setLat(parseFloat(e.target.value))}
              className="w-full bg-sonar-card border border-sonar-border rounded px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
          <div>
            <label className="text-[10px] font-mono text-sonar-muted block mb-1">OBSERVER LONGITUDE</label>
            <input
              type="number"
              step="0.0001"
              value={lon}
              onChange={(e) => setLon(parseFloat(e.target.value))}
              className="w-full bg-sonar-card border border-sonar-border rounded px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
          <div>
            <label className="text-[10px] font-mono text-sonar-muted block mb-1">CLAIMED UTC TIME (ISO-8601)</label>
            <input
              type="text"
              value={utcTime}
              onChange={(e) => setUtcTime(e.target.value)}
              className="w-full bg-sonar-card border border-sonar-border rounded px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
          <div>
            <label className="text-[10px] font-mono text-sonar-muted block mb-1">SEARCH RADIUS (KM)</label>
            <input
              type="number"
              step="1"
              min={1}
              max={50}
              value={radiusKm}
              onChange={(e) => setRadiusKm(parseFloat(e.target.value))}
              className="w-full bg-sonar-card border border-sonar-border rounded px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-sonar-cyan"
            />
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-sonar-red/15 border border-sonar-red/40 rounded-lg text-xs font-mono text-sonar-red">
            {error}
          </div>
        )}
      </div>

      {/* Spectrogram with Modeled ADS-B Trajectories Overlay */}
      {imageUri && (
        <SpectrogramCanvas
          imageDataUri={imageUri}
          adsbCurves={report?.evaluated_flights?.map((f) => ({
            times: f.modeled_curve?.times || [],
            freqs: f.modeled_curve?.freqs || [],
            flight_id: f.flight_id,
            is_match: f.is_acoustic_match,
          }))}
          title="Modeled ADS-B Retarded-Time Doppler Curves Over Spectrogram"
          height={320}
        />
      )}

      {/* Alibi Verdict Card */}
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

            <div className="mt-4 pt-4 border-t border-sonar-border/60 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div>
                <span className="text-sonar-muted text-[10px] block">DEM GROUND ELEVATION</span>
                <span className="text-sm font-bold text-sonar-cyan">{report.claimed_coordinates.observer_elevation_m}m</span>
              </div>
              <div>
                <span className="text-sonar-muted text-[10px] block">EVALUATED FLIGHTS</span>
                <span className="text-sm font-bold text-white">{report.num_flights_evaluated}</span>
              </div>
              <div>
                <span className="text-sonar-muted text-[10px] block">FILTERED TRAFFIC</span>
                <span className="text-sm font-bold text-sonar-green">Piston / Turboprop Only</span>
              </div>
              <div>
                <span className="text-sonar-muted text-[10px] block">UTC TIMESTAMP</span>
                <span className="text-[11px] text-sonar-text">{report.claimed_coordinates.utc_time}</span>
              </div>
            </div>
          </div>

          {/* Evaluated Flight Details */}
          {report.evaluated_flights.length > 0 && (
            <div className="bg-sonar-panel border border-sonar-border rounded-xl p-5 shadow-xl space-y-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-sonar-muted">
                Historical Overhead Flight Trajectories ({report.evaluated_flights.length})
              </h3>
              <div className="space-y-3">
                {report.evaluated_flights.map((fl, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-sonar-bg/80 border border-sonar-border rounded-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs font-mono"
                  >
                    <div className="flex items-center gap-3">
                      <Plane className={`w-5 h-5 ${fl.is_acoustic_match ? "text-sonar-green" : "text-sonar-muted"}`} />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-sm">{fl.flight_id}</span>
                          <span className="px-2 py-0.5 bg-sonar-card rounded text-sonar-cyan text-[10px]">
                            {fl.icao_type}
                          </span>
                        </div>
                        <span className="text-[11px] text-sonar-muted">
                          Min Slant: {fl.min_slant_m.toFixed(0)}m | Rel CPA: T+{fl.t_cpa_relative_s.toFixed(1)}s
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div>
                        <span className="text-[10px] text-sonar-muted block">ACOUSTIC ALIGNMENT</span>
                        <span className={`font-bold ${fl.alignment_score_sigma >= 3.8 ? "text-sonar-green" : "text-sonar-muted"}`}>
                          {fl.alignment_score_sigma.toFixed(2)} σ
                        </span>
                      </div>

                      {fl.is_acoustic_match && (
                        <span className="px-2 py-1 bg-sonar-green/15 text-sonar-green border border-sonar-green/30 rounded text-[11px] font-bold">
                          MATCH
                        </span>
                      )}
                      {fl.is_silence_violation && (
                        <span className="px-2 py-1 bg-sonar-red/15 text-sonar-red border border-sonar-red/30 rounded text-[11px] font-bold animate-pulse">
                          SILENCE VIOLATION
                        </span>
                      )}
                    </div>
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
