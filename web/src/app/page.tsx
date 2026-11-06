"use client";

import React, { useState, useEffect } from "react";
import { Radio, ShieldCheck, Globe, Cpu, Terminal, Layers, Activity } from "lucide-react";
import AuditPanel from "@/components/AuditPanel";
import CloakPanel from "@/components/CloakPanel";
import VerifyAlibiPanel from "@/components/VerifyAlibiPanel";
import VerifyPhysicsPanel from "@/components/VerifyPhysicsPanel";
import { checkHealth } from "@/lib/api";

type TabMode = "audit" | "cloak" | "verify_alibi" | "verify_physics";

export default function WorkstationPage() {
  const [activeTab, setActiveTab] = useState<TabMode>("audit");
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth().then(setBackendHealthy);
    const interval = setInterval(() => {
      checkHealth().then(setBackendHealthy);
    }, 12000);
    return () => clearInterval(interval);
  }, []);

  // Keyboard shortcuts 1, 2, 3, 4 for tabs
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "1") setActiveTab("audit");
      if (e.key === "2") setActiveTab("cloak");
      if (e.key === "3") setActiveTab("verify_alibi");
      if (e.key === "4") setActiveTab("verify_physics");
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-sonar-bg text-sonar-text flex flex-col font-sans selection:bg-sonar-cyan/20 selection:text-sonar-cyan">
      {/* Precision Hardware Console Header */}
      <header className="border-b border-white/[0.08] bg-sonar-panel/95 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          {/* Brand Mark & Classification */}
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded bg-white/[0.04] border border-white/[0.12] flex items-center justify-center font-mono font-bold text-xs text-sonar-cyan">
              S
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-mono font-bold text-white tracking-widest text-sm">
                SONAR
              </span>
              <span className="hidden sm:inline font-mono text-[10px] text-sonar-muted uppercase tracking-wider">
                Acoustic Forensics
              </span>
            </div>
          </div>

          {/* Hardware-Style Segmented Navigation */}
          <nav className="flex items-center bg-[#0B0E14] p-1 rounded-md border border-white/[0.07] font-mono text-xs">
            <button
              onClick={() => setActiveTab("audit")}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                activeTab === "audit"
                  ? "bg-sonar-card text-white font-medium border border-white/[0.12] shadow-sm"
                  : "text-sonar-secondary hover:text-white"
              }`}
            >
              <Radio className="w-3.5 h-3.5 text-sonar-cyan" />
              <span>Audit</span>
              <span className="hidden md:inline text-[9px] text-sonar-muted ml-0.5">1</span>
            </button>

            <button
              onClick={() => setActiveTab("cloak")}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                activeTab === "cloak"
                  ? "bg-sonar-card text-white font-medium border border-white/[0.12] shadow-sm"
                  : "text-sonar-secondary hover:text-white"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-sonar-green" />
              <span>Cloak</span>
              <span className="hidden md:inline text-[9px] text-sonar-muted ml-0.5">2</span>
            </button>

            <button
              onClick={() => setActiveTab("verify_alibi")}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                activeTab === "verify_alibi"
                  ? "bg-sonar-card text-white font-medium border border-white/[0.12] shadow-sm"
                  : "text-sonar-secondary hover:text-white"
              }`}
            >
              <Globe className="w-3.5 h-3.5 text-sonar-cyan" />
              <span>Alibi</span>
              <span className="hidden md:inline text-[9px] text-sonar-muted ml-0.5">3</span>
            </button>

            <button
              onClick={() => setActiveTab("verify_physics")}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                activeTab === "verify_physics"
                  ? "bg-sonar-card text-white font-medium border border-white/[0.12] shadow-sm"
                  : "text-sonar-secondary hover:text-white"
              }`}
            >
              <Cpu className="w-3.5 h-3.5 text-sonar-amber" />
              <span>AI Physics</span>
              <span className="hidden md:inline text-[9px] text-sonar-muted ml-0.5">4</span>
            </button>
          </nav>

          {/* Engine Calibration & Health Status */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-3 text-[11px] font-mono text-sonar-muted">
              <span>FS: 4000Hz</span>
              <span className="text-white/[0.15]">|</span>
              <span>FFT: 16384</span>
              <span className="text-white/[0.15]">|</span>
              <span>RES: 0.244Hz</span>
            </div>

            <div className="flex items-center gap-2 px-2.5 py-1 bg-white/[0.03] rounded border border-white/[0.08] font-mono text-[11px]">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendHealthy === true
                    ? "bg-sonar-green"
                    : backendHealthy === false
                    ? "bg-sonar-red"
                    : "bg-sonar-amber animate-pulse"
                }`}
              />
              <span className="text-sonar-secondary text-[10px]">
                {backendHealthy === true ? "DSP Core Online" : "Connecting..."}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Workstation Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "audit" && <AuditPanel />}
        {activeTab === "cloak" && <CloakPanel />}
        {activeTab === "verify_alibi" && <VerifyAlibiPanel />}
        {activeTab === "verify_physics" && <VerifyPhysicsPanel />}
      </main>

      {/* Laboratory Status Bar */}
      <footer className="border-t border-white/[0.06] bg-sonar-panel/60 px-4 py-2.5 text-[11px] font-mono text-sonar-muted">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 text-[11px]">
            <span className="text-sonar-secondary font-medium">SONAR ACOUSTIC FORENSICS</span>
            <span>•</span>
            <span>LOCAL CPU PROCESSING</span>
            <span>•</span>
            <span>ZERO CLOUD TELEMETRY</span>
          </div>
          <div className="flex items-center gap-4 text-sonar-muted text-[10px]">
            <span>ENGINE: FASTAPI :8000</span>
            <span>CONSOLE: PORT 50242</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
