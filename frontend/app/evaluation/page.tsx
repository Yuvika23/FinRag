"use client";

import { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { EvaluationRun, EvaluationResultItem } from "@/lib/types";
import {
  Award,
  Play,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  Target,
  FileCheck,
  TrendingUp,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function EvaluationPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function loadRuns() {
    setLoading(true);
    try {
      const data = await api.getEvaluationRuns().catch(() => []);
      setRuns(data);
      if (data.length > 0) {
        setSelectedRun(data[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
  }, []);

  async function handleRunBenchmark() {
    setRunning(true);
    try {
      const newRun = await api.runEvaluation({ name: `Benchmark Run #${runs.length + 1}` });
      await loadRuns();
      setSelectedRun(newRun);
    } catch (err: any) {
      alert(`Benchmark execution failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col">
      <Navbar
        title="RAG Evaluation & Faithfulness Benchmark"
        subtitle="Quantitative assessment of vector retrieval, citation precision, and hallucination resistance"
      />

      <div className="p-8 space-y-8 max-w-7xl mx-auto w-full flex-1">
        {/* Header Action Card */}
        <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Award className="w-5 h-5 text-emerald-400" />
              Empirical Benchmark Runner
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Evaluates the active FAISS index against <code>data/evaluation/eval_dataset.json</code> containing verified ground-truth financial filing queries.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {runs.length > 0 && (
              <select
                value={selectedRun?.id || ""}
                onChange={(e) => {
                  const r = runs.find((item) => item.id === e.target.value);
                  if (r) setSelectedRun(r);
                }}
                className="px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-medium"
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({new Date(r.created_at).toLocaleTimeString()})
                  </option>
                ))}
              </select>
            )}

            <button
              onClick={handleRunBenchmark}
              disabled={running}
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-navy-950 font-semibold text-xs flex items-center gap-2 transition shadow-lg shadow-emerald-500/20"
            >
              {running ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Evaluating Retrieval & Citations...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Execute Benchmark</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Aggregate Benchmark Metric Cards */}
        {selectedRun ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 animate-fade-in">
            <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Recall @ K</div>
              <div className="text-2xl font-bold font-mono text-emerald-400">
                {selectedRun.avg_recall_at_k !== undefined && selectedRun.avg_recall_at_k !== null
                  ? `${(selectedRun.avg_recall_at_k * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <p className="text-[10px] text-slate-500">Gold source discovery</p>
            </div>

            <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Precision @ K</div>
              <div className="text-2xl font-bold font-mono text-blue-400">
                {selectedRun.avg_precision_at_k !== undefined && selectedRun.avg_precision_at_k !== null
                  ? `${(selectedRun.avg_precision_at_k * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <p className="text-[10px] text-slate-500">Context relevance ratio</p>
            </div>

            <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold uppercase text-slate-400">MRR Score</div>
              <div className="text-2xl font-bold font-mono text-purple-400">
                {selectedRun.avg_mrr !== undefined && selectedRun.avg_mrr !== null
                  ? selectedRun.avg_mrr.toFixed(2)
                  : "—"}
              </div>
              <p className="text-[10px] text-slate-500">Mean reciprocal rank</p>
            </div>

            <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Citation Acc.</div>
              <div className="text-2xl font-bold font-mono text-teal-400">
                {selectedRun.avg_citation_accuracy !== undefined && selectedRun.avg_citation_accuracy !== null
                  ? `${(selectedRun.avg_citation_accuracy * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <p className="text-[10px] text-slate-500">Page number audit</p>
            </div>

            <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Faithfulness</div>
              <div className="text-2xl font-bold font-mono text-emerald-400">
                {selectedRun.avg_faithfulness !== undefined && selectedRun.avg_faithfulness !== null
                  ? `${(selectedRun.avg_faithfulness * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <p className="text-[10px] text-slate-500">Hallucination resistance</p>
            </div>

            <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Avg Latency</div>
              <div className="text-2xl font-bold font-mono text-slate-200">
                {selectedRun.avg_latency_ms !== undefined && selectedRun.avg_latency_ms !== null
                  ? `${selectedRun.avg_latency_ms.toFixed(0)} ms`
                  : "—"}
              </div>
              <p className="text-[10px] text-slate-500">End-to-end response</p>
            </div>
          </div>
        ) : (
          <div className="p-10 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/40">
            <Target className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-white">No benchmark runs logged yet</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Click "Execute Benchmark" above to run the 6 gold-standard financial questions and record baseline accuracy.
            </p>
          </div>
        )}

        {/* Individual Query Results Table */}
        {selectedRun && selectedRun.results && selectedRun.results.length > 0 && (
          <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Question Level Verification Breakdown</h2>
                <p className="text-xs text-slate-400">
                  Granular audit of retrieved evidence vs expected benchmark ground truth
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {selectedRun.results.length} questions evaluated
              </span>
            </div>

            <div className="space-y-3">
              {selectedRun.results.map((res) => {
                const isExpanded = expandedId === res.id;
                return (
                  <div
                    key={res.id}
                    className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden transition"
                  >
                    <div
                      onClick={() => setExpandedId(isExpanded ? null : res.id)}
                      className="p-4 flex items-center justify-between gap-4 cursor-pointer hover:bg-slate-800/40"
                    >
                      <div className="flex-1 space-y-1">
                        <div className="text-xs font-semibold text-white flex items-center gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>{res.question}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0 text-xs font-mono">
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px]">
                          Recall: {res.recall_at_k !== undefined ? `${(res.recall_at_k * 100).toFixed(0)}%` : "—"}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[11px]">
                          MRR: {res.mrr !== undefined ? res.mrr.toFixed(2) : "—"}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20 text-[11px]">
                          Faithful: {res.faithfulness !== undefined ? `${(res.faithfulness * 100).toFixed(0)}%` : "—"}
                        </span>
                        <span className="text-slate-400 text-[11px]">
                          {res.latency_ms?.toFixed(0)} ms
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="p-4 border-t border-slate-800 bg-navy-950/70 space-y-3 text-xs">
                        {res.expected_answer && (
                          <div>
                            <div className="text-[10px] font-semibold uppercase text-slate-400 mb-1">
                              Expected Benchmark Ground-Truth Answer
                            </div>
                            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 leading-relaxed font-mono text-[11px]">
                              {res.expected_answer}
                            </div>
                          </div>
                        )}

                        {res.generated_answer && (
                          <div>
                            <div className="text-[10px] font-semibold uppercase text-slate-400 mb-1">
                              Generated Synthesis Answer
                            </div>
                            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-emerald-300 leading-relaxed font-mono text-[11px]">
                              {res.generated_answer}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Methodology Card */}
        <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 space-y-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-emerald-400" />
            Evaluation Methodology Standard
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-400 leading-relaxed">
            <div>
              <strong className="text-white block mb-1">Recall@K & Precision@K:</strong>
              Calculates whether the specific filing and page number containing the disclosure was retrieved in the top K FAISS vector passages.
            </div>
            <div>
              <strong className="text-white block mb-1">Mean Reciprocal Rank (MRR):</strong>
              Evaluates the rank position of the first authoritative passage. An MRR of 1.0 means the exact answer was in rank #1.
            </div>
            <div>
              <strong className="text-white block mb-1">Faithfulness & Citation Audit:</strong>
              Cross-verifies claims made in the answer with citations against raw chunk text to detect and penalize any hallucinated financial figures.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
