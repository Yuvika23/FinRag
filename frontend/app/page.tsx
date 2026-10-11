"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { OverviewStats, Document } from "@/lib/types";
import {
  FileText,
  Building2,
  Database,
  Calendar,
  Search,
  Upload,
  ArrowRight,
  TrendingUp,
  Cpu,
  CheckCircle2,
  Clock,
  Layers,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

const sampleChartData = [
  { name: "TechVision FY23", Revenue: 1250, NetIncome: 243.8 },
  { name: "TechVision FY24", Revenue: 1435, NetIncome: 309.0 },
  { name: "GlobalBank FY24", Revenue: 4850, NetIncome: 1120.0 },
];

export default function OverviewPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [overviewStats, docs] = await Promise.all([
          api.getOverviewStats().catch(() => null),
          api.getDocuments({ limit: 5 }).catch(() => []),
        ]);
        setStats(overviewStats);
        setRecentDocs(docs);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="flex-1 flex flex-col">
      <Navbar
        title="Filing Intelligence Overview"
        subtitle="End-to-end vector retrieval, SQL analytics, and verifiable citations"
      />

      <div className="p-8 space-y-8 flex-1">
        {/* Synthetic Data Notice Banner */}
        <div className="p-3.5 px-4 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2.5 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>
              <strong>FinRAG Engine Active:</strong> Demo corpus uses synthetic enterprise filings labeled for verification. Real SEC 10-K & 10-Q PDFs can be ingested anytime via the Document Library.
            </span>
          </div>
          <Link
            href="/documents"
            className="text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1 transition"
          >
            Upload Filing <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Metric Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="p-5 rounded-xl bg-navy-950 border border-slate-800 glass-panel-hover space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Indexed Filings</span>
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                <FileText className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-bold text-white tracking-tight">
                {loading ? "..." : stats?.total_documents ?? 0}
              </div>
              <p className="text-xs text-slate-400 mt-1">Annual reports & transcripts</p>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-navy-950 border border-slate-800 glass-panel-hover space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Companies Tracked</span>
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                <Building2 className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-bold text-white tracking-tight">
                {loading ? "..." : stats?.total_companies ?? 0}
              </div>
              <p className="text-xs text-slate-400 mt-1">Across Tech & Financial sectors</p>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-navy-950 border border-slate-800 glass-panel-hover space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-semibold uppercase tracking-wider">FAISS Vector Chunks</span>
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                <Database className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-bold text-white tracking-tight font-mono">
                {loading ? "..." : stats?.faiss_total_vectors ?? 0}
              </div>
              <p className="text-xs text-slate-400 mt-1">384d normalized embeddings</p>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-navy-950 border border-slate-800 glass-panel-hover space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Structured Metrics</span>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-bold text-white tracking-tight">
                {loading ? "..." : stats?.total_metrics ?? 0}
              </div>
              <p className="text-xs text-slate-400 mt-1">YoY comparison records in SQL</p>
            </div>
          </div>
        </div>

        {/* Middle Section: Chart & Quick Action Launchpad */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart card */}
          <div className="lg:col-span-2 p-6 rounded-xl bg-navy-950 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Indexed Financial Metrics (USD M)</h2>
                <p className="text-xs text-slate-400">Revenue & Net Income extracted from filings</p>
              </div>
              <Link
                href="/analytics"
                className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-medium transition"
              >
                Detailed Analytics <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="h-64 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sampleChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                  <Bar dataKey="Revenue" fill="#10b981" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="NetIncome" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Quick Action Launchpad */}
          <div className="p-6 rounded-xl bg-navy-950 border border-slate-800 flex flex-col justify-between space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-white">Intelligence Launchpad</h2>
              <p className="text-xs text-slate-400 mt-0.5">Direct access to query engines</p>
            </div>

            <div className="space-y-3">
              <Link
                href="/research"
                className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-emerald-500/40 hover:bg-slate-850 flex items-center justify-between transition group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Search className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-semibold text-white group-hover:text-emerald-400 transition">
                      Ask Filing Question
                    </div>
                    <div className="text-[11px] text-slate-400">Natural language RAG + SQL</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-400 transition" />
              </Link>

              <Link
                href="/documents"
                className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-blue-500/40 hover:bg-slate-850 flex items-center justify-between transition group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                    <Upload className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-semibold text-white group-hover:text-blue-400 transition">
                      Upload Filing (PDF/TXT)
                    </div>
                    <div className="text-[11px] text-slate-400">Auto-chunk & index into FAISS</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-400 transition" />
              </Link>

              <Link
                href="/evaluation"
                className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-purple-500/40 hover:bg-slate-850 flex items-center justify-between transition group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-semibold text-white group-hover:text-purple-400 transition">
                      Run RAG Benchmark
                    </div>
                    <div className="text-[11px] text-slate-400">Recall@K & Faithfulness test</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-purple-400 transition" />
              </Link>
            </div>

            <div className="pt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Deterministic SQL queries prevent LLM math errors</span>
            </div>
          </div>
        </div>

        {/* Recent Filings Table */}
        <div className="p-6 rounded-xl bg-navy-950 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Recent Indexed Filings</h2>
              <p className="text-xs text-slate-400">Documents available for vector similarity retrieval</p>
            </div>
            <Link
              href="/documents"
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1 transition"
            >
              View All Filings <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {recentDocs.length === 0 ? (
            <div className="p-8 text-center rounded-lg border border-dashed border-slate-800 bg-slate-900/30">
              <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">No documents indexed yet.</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Run the demo data import script or upload a filing in the Document Library.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                    <th className="pb-3 font-semibold">Document Title</th>
                    <th className="pb-3 font-semibold">Company / Ticker</th>
                    <th className="pb-3 font-semibold">Fiscal Year</th>
                    <th className="pb-3 font-semibold">Pages / Chunks</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {recentDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-800/20 transition">
                      <td className="py-3 font-medium text-white flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        <span className="truncate max-w-[240px]">{doc.original_filename}</span>
                      </td>
                      <td className="py-3 font-mono text-slate-300">
                        {doc.ticker || doc.company_name || "—"}
                      </td>
                      <td className="py-3 font-mono text-slate-300">{doc.fiscal_year || "—"}</td>
                      <td className="py-3 text-slate-400">
                        {doc.page_count ?? 1} pages / {doc.chunk_count ?? "—"} chunks
                      </td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                            doc.status === "indexed"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : doc.status === "processing"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-red-500/10 text-red-400 border border-red-500/20"
                          }`}
                        >
                          {doc.status}
                        </span>
                      </td>
                      <td className="py-3 text-slate-400 capitalize">
                        {doc.document_type.replace("_", " ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
