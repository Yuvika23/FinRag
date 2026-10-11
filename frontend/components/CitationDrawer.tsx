"use client";

import { X, FileText, Bookmark, ExternalLink, Hash, CheckCircle2 } from "lucide-react";
import { Citation } from "@/lib/types";

interface CitationDrawerProps {
  citation: Citation | null;
  onClose: () => void;
}

export function CitationDrawer({ citation, onClose }: CitationDrawerProps) {
  if (!citation) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 max-w-full bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col animate-fade-in">
      {/* Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-navy-950/70">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Bookmark className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Citation Audit</h3>
            <p className="text-[11px] text-slate-400">Ground-truth evidence passage</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
        {/* Source metadata card */}
        <div className="p-3.5 rounded-lg bg-navy-950 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              Document:
            </span>
            <span className="text-slate-200 font-medium text-right truncate max-w-[180px]">
              {citation.source_document}
            </span>
          </div>

          {citation.page_number && (
            <div className="flex items-center justify-between text-slate-400">
              <span className="flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5 text-slate-400" />
                Page Reference:
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono font-medium">
                Page {citation.page_number}
              </span>
            </div>
          )}

          {citation.ticker && (
            <div className="flex items-center justify-between text-slate-400">
              <span>Company / Ticker:</span>
              <span className="text-slate-200 font-mono">{citation.ticker}</span>
            </div>
          )}

          {citation.fiscal_year && (
            <div className="flex items-center justify-between text-slate-400">
              <span>Fiscal Year:</span>
              <span className="text-slate-200 font-mono">{citation.fiscal_year}</span>
            </div>
          )}

          {citation.similarity_score !== undefined && (
            <div className="flex items-center justify-between text-slate-400">
              <span>Relevance Score:</span>
              <span className="text-emerald-400 font-mono">
                {(citation.similarity_score * 100).toFixed(1)}% match
              </span>
            </div>
          )}
        </div>

        {/* Verification Status */}
        <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40 flex items-center gap-2.5 text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Extracted directly from indexed filing chunk. No synthetic interpolation.</span>
        </div>

        {/* Chunk Content */}
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Verbatim Passage Excerpt
          </div>
          <div className="p-4 rounded-lg bg-navy-950 border border-slate-800 text-slate-300 leading-relaxed font-mono text-[11px] whitespace-pre-wrap select-text">
            {citation.snippet}
          </div>
        </div>

        <div className="text-[11px] text-slate-400 font-mono break-all">
          Chunk ID: {citation.chunk_id}
        </div>
      </div>
    </div>
  );
}
