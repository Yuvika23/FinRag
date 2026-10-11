"use client";

import { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import { CitationDrawer } from "@/components/CitationDrawer";
import { api } from "@/lib/api";
import { ChatResponse, Citation, Company } from "@/lib/types";
import {
  Search,
  Sparkles,
  Database,
  FileText,
  Clock,
  Bookmark,
  CheckCircle2,
  AlertCircle,
  Filter,
  ArrowRight,
  Send,
  Loader2,
  Info,
} from "lucide-react";

const SUGGESTIONS = [
  "What was TechVision's revenue and net income growth from FY2023 to FY2024?",
  "What key risk factors did TechVision disclose regarding customer concentration and AI infrastructure?",
  "Explain the drivers behind TechVision's operating margin expansion in FY2024.",
  "What was GlobalBank's net interest margin and non-performing loan ratio in FY2024?",
];

export default function ResearchPage() {
  const [query, setQuery] = useState("");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>("");
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  useEffect(() => {
    api.getCompanies()
      .then(setCompanies)
      .catch(() => setCompanies([]));
  }, []);

  async function handleSearch(searchQuery?: string) {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.chat({
        query: q.trim(),
        company_id: selectedCompany || null,
        fiscal_year: selectedYear || null,
        top_k: 5,
      });
      setResponse(res);
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Failed to execute query. Check backend connection.");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      handleSearch();
    }
  }

  return (
    <div className="flex-1 flex flex-col relative">
      <Navbar
        title="Research Assistant"
        subtitle="Source-grounded financial reasoning across filings and structured metrics"
      />

      <div className="p-8 space-y-6 max-w-6xl mx-auto w-full flex-1">
        {/* Search Input Box */}
        <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask any financial, disclosure, or numerical question..."
                className="w-full pl-12 pr-4 py-3.5 rounded-xl bg-slate-900 border border-slate-700/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition"
              />
            </div>

            <button
              onClick={() => handleSearch()}
              disabled={loading || !query.trim()}
              className="px-6 py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-navy-950 font-semibold text-sm flex items-center gap-2 transition shadow-lg shadow-emerald-500/20"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>Analyze</span>
            </button>
          </div>

          {/* Filtering options */}
          <div className="flex flex-wrap items-center gap-3 text-xs pt-1">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Filter className="w-3.5 h-3.5" />
              <span>Scope Filters:</span>
            </div>

            <select
              value={selectedCompany}
              onChange={(e) => setSelectedCompany(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-emerald-500"
            >
              <option value="">All Companies</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.ticker})
                </option>
              ))}
            </select>

            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:border-emerald-500"
            >
              <option value="">All Fiscal Years</option>
              <option value="FY2024">FY2024</option>
              <option value="FY2023">FY2023</option>
            </select>
          </div>

          {/* Suggested Questions */}
          <div className="pt-2">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Sample Inquiries
            </div>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setQuery(item);
                    handleSearch(item);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-emerald-500/30 hover:bg-slate-800 text-left text-xs text-slate-300 transition"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error notice */}
        {error && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-center gap-3">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="p-8 rounded-2xl bg-navy-950 border border-slate-800 space-y-4 animate-pulse">
            <div className="h-4 bg-slate-800 rounded w-1/4" />
            <div className="h-4 bg-slate-800 rounded w-3/4" />
            <div className="h-4 bg-slate-800 rounded w-2/3" />
            <div className="h-20 bg-slate-900 rounded" />
          </div>
        )}

        {/* Response Presentation */}
        {response && !loading && (
          <div className="space-y-6 animate-fade-in">
            {/* Header with Route & Latency Badge */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-navy-950 border border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Execution Route:</span>
                <span
                  className={`px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wider ${
                    response.route_taken === "combined"
                      ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                      : response.route_taken === "numerical"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  }`}
                >
                  {response.route_taken === "combined"
                    ? "Hybrid (SQL + FAISS)"
                    : response.route_taken === "numerical"
                    ? "Structured SQL Analytics"
                    : "Dense Vector Search"}
                </span>
              </div>

              <div className="flex items-center gap-4 text-xs text-slate-400">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-mono text-slate-300">
                    {response.latency_ms.toFixed(1)} ms
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Ground-Truth Verified</span>
                </div>
              </div>
            </div>

            {/* Answer Box */}
            <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>Synthesized Answer</span>
              </div>

              <div className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                {response.answer}
              </div>
            </div>

            {/* Structured SQL Data Table (if present) */}
            {response.sql_data && response.sql_data.length > 0 && (
              <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                    <Database className="w-4 h-4 text-blue-400" />
                    <span>Structured SQL Verification Data</span>
                  </div>
                  <span className="text-[11px] text-slate-400">Direct parameter query (0% hallucination)</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                        <th className="pb-2.5 font-semibold">Company</th>
                        <th className="pb-2.5 font-semibold">Ticker</th>
                        <th className="pb-2.5 font-semibold">Period</th>
                        <th className="pb-2.5 font-semibold">Metric</th>
                        <th className="pb-2.5 font-semibold text-right">Value</th>
                        <th className="pb-2.5 font-semibold">Reference</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {response.sql_data.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/20">
                          <td className="py-2.5 font-medium text-white">{row.company}</td>
                          <td className="py-2.5 font-mono text-slate-300">{row.ticker}</td>
                          <td className="py-2.5 font-mono text-slate-300">{row.fiscal_year}</td>
                          <td className="py-2.5 text-slate-300">{row.metric}</td>
                          <td className="py-2.5 font-mono text-right text-emerald-400 font-semibold">
                            {row.value.toLocaleString()} {row.unit || ""}
                          </td>
                          <td className="py-2.5 text-slate-400 text-[11px]">
                            {row.filing_reference || "Official Filing"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Citations Panel */}
            {response.citations && response.citations.length > 0 && (
              <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                    <Bookmark className="w-4 h-4 text-emerald-400" />
                    <span>Evidence Passages & Citations ({response.citations.length})</span>
                  </div>
                  <span className="text-[11px] text-slate-400">Click any citation to inspect verbatim page context</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {response.citations.map((c, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveCitation(c)}
                      className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/40 hover:bg-slate-850 text-left transition group space-y-2"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-white flex items-center gap-1.5 truncate max-w-[200px]">
                          <FileText className="w-3.5 h-3.5 text-emerald-400" />
                          {c.source_document}
                        </span>
                        {c.page_number && (
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[10px]">
                            Page {c.page_number}
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed group-hover:text-slate-300 transition font-mono text-[11px]">
                        "{c.snippet}"
                      </p>

                      <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500">
                        <span>{c.fiscal_year || "Filing"}</span>
                        <span className="text-emerald-400 flex items-center gap-0.5 font-medium">
                          Audit passage <ArrowRight className="w-3 h-3" />
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Slide-out Citation Inspection Drawer */}
      <CitationDrawer
        citation={activeCitation}
        onClose={() => setActiveCitation(null)}
      />
    </div>
  );
}
