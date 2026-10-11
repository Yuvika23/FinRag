"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  FileText,
  BarChart3,
  Award,
  ShieldCheck,
  Cpu,
  Layers,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/research", label: "Research Assistant", icon: Search },
  { href: "/documents", label: "Document Library", icon: FileText },
  { href: "/analytics", label: "Financial Analytics", icon: BarChart3 },
  { href: "/evaluation", label: "RAG Evaluation", icon: Award },
];

export function Sidebar() {
  const pathname = usePathname();
  const [health, setHealth] = useState<{
    database: string;
    faiss_total_vectors: number;
    llm_provider: string;
  } | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <aside className="w-64 min-h-screen bg-navy-950 border-r border-slate-800/80 flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800/80 gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-900/30">
          <Layers className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
            FinRAG
            <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              v1.0
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">Filing Intelligence</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Workspace
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-emerald-400" : "text-slate-400"}`} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* System Status Footprint */}
      <div className="p-4 border-t border-slate-800/80 bg-navy-900/40">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          Engine Engine Status
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span>Database:</span>
            <span className="flex items-center gap-1.5 text-slate-200 font-medium">
              <span className={`w-2 h-2 rounded-full ${health ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
              {health ? health.database : "connecting..."}
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>FAISS Vectors:</span>
            <span className="text-slate-200 font-mono font-medium">
              {health ? health.faiss_total_vectors : "0"}
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>LLM Mode:</span>
            <span className="text-emerald-400 font-mono font-medium capitalize">
              {health ? health.llm_provider : "loading..."}
            </span>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center gap-2 text-[11px] text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Verifiable Citations Only</span>
        </div>
      </div>
    </aside>
  );
}
