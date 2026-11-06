"use client";

import React, { useState, useEffect } from "react";
import { Radio, ShieldCheck, Globe, Cpu, Activity, RefreshCw, Terminal, Layers } from "lucide-react";
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
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-sonar-bg text-sonar-text flex flex-col font-sans">
      {/* Top Technical Navigation Header */}
      <header className="border-b border-sonar-border bg-sonar-panel/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-sonar-cyan/10 border border-sonar-cyan/30 flex items-center justify-center text-sonar-cyan font-mono font-semibold text-sm">
              S
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-white tracking-wider text-base">
                  SONAR
                </span>
                <span className="px-1.5 py-0.5 bg-sonar-card border border-sonar-border rounded font-mono text-[10px] text-sonar-cyan font-medium">
                  v0.1.0
                </span>
              </div>
              <p className="text-[10px] font-mono text-sonar-muted hidden sm:block">
                Acoustic Side-Channel Security & Forensics Suite
              </p>
            </div>
          </div>

          {/* Tab Navigation Switches */}
          <nav className="flex items-center gap-1 bg-sonar-card p-1 rounded-lg border border-sonar-border font-mono text-xs">
            <button
              onClick={() => setActiveTab("audit")}
              className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-2 ${
                activeTab === "audit"
                  ? "bg-sonar-panel text-sonar-cyan font-bold shadow border border-sonar-cyan/30"
                  : "text-sonar-muted hover:text-white"
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Audit</span>
            </button>

            <button
              onClick={() => setActiveTab("cloak")}
              className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-2 ${
                activeTab === "cloak"
                  ? "bg-sonar-panel text-sonar-green font-bold shadow border border-sonar-green/30"
                  : "text-sonar-muted hover:text-white"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Cloak</span>
            </button>

            <button
              onClick={() => setActiveTab("verify_alibi")}
              className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-2 ${
                activeTab === "verify_alibi"
                  ? "bg-sonar-panel text-white font-bold shadow border border-sonar-border"
                  : "text-sonar-muted hover:text-white"
              }`}
            >
              <Globe className="w-3.5 h-3.5 text-sonar-cyan" />
              <span className="hidden md:inline">Verify:</span> Alibi
            </button>

            <button
              onClick={() => setActiveTab("verify_physics")}
              className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-2 ${
                activeTab === "verify_physics"
                  ? "bg-sonar-panel text-sonar-amber font-bold shadow border border-sonar-amber/30"
                  : "text-sonar-muted hover:text-white"
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Verify:</span> AI Physics
            </button>
          </nav>

          {/* Engine Status Pill */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-sonar-card rounded border border-sonar-border font-mono text-[11px]">
              <span
                className={`w-2 h-2 rounded-full ${
                  backendHealthy === true
                    ? "bg-sonar-green"
                    : backendHealthy === false
                    ? "bg-sonar-red"
                    : "bg-sonar-amber animate-pulse"
                }`}
              />
              <span className="text-sonar-secondary font-medium">
                {backendHealthy === true ? "DSP Core 4000Hz (Online)" : "Connecting API..."}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Workstation Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "audit" && <AuditPanel />}
        {activeTab === "cloak" && <CloakPanel />}
        {activeTab === "verify_alibi" && <VerifyAlibiPanel />}
        {activeTab === "verify_physics" && <VerifyPhysicsPanel />}
      </main>

      {/* Footer Status Bar */}
      <footer className="border-t border-sonar-border bg-sonar-panel/50 px-4 py-3 text-[11px] font-mono text-sonar-muted">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <span className="text-sonar-text font-medium">SONAR Acoustic Geolocation Suite</span>
            <span>•</span>
            <span>Local-First DSP Architecture</span>
            <span>•</span>
            <span>Zero Cloud Audio Offload</span>
          </div>
          <div className="flex items-center gap-4 text-sonar-muted">
            <span>FastAPI @ 127.0.0.1:8000</span>
            <span>Next.js Workstation @ :50242</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

