"use client";

import { useState, useEffect, useRef } from "react";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { Document, Company } from "@/lib/types";
import {
  Upload,
  FileText,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Building2,
  Calendar,
  Loader2,
  FileCheck,
} from "lucide-react";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  // Form state
  const [file, setFile] = useState<File | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [ticker, setTicker] = useState("");
  const [fiscalYear, setFiscalYear] = useState("FY2024");
  const [docType, setDocType] = useState("annual_report");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadData() {
    setLoading(true);
    try {
      const [docs, comps] = await Promise.all([
        api.getDocuments().catch(() => []),
        api.getCompanies().catch(() => []),
      ]);
      setDocuments(docs);
      setCompanies(comps);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append("file", file);
    if (companyName) formData.append("company_name", companyName);
    if (ticker) formData.append("ticker", ticker);
    if (fiscalYear) formData.append("fiscal_year", fiscalYear);
    if (docType) formData.append("document_type", docType);

    try {
      const newDoc = await api.uploadDocument(formData);
      setUploadSuccess(`"${newDoc.original_filename}" uploaded and indexed successfully into FAISS!`);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      loadData();
    } catch (err: any) {
      console.error(err);
      setUploadError(err?.message || "Failed to upload document.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this filing? Vectors will be rebuilt.")) return;
    setActionInProgress(id);
    try {
      await api.deleteDocument(id);
      loadData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleReindex(id: string) {
    setActionInProgress(id);
    try {
      await api.reindexDocument(id);
      loadData();
    } catch (err: any) {
      alert(`Reindex failed: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  }

  return (
    <div className="flex-1 flex flex-col">
      <Navbar
        title="Document Library & Ingestion"
        subtitle="Upload filings, chunk text, and persist normalized embeddings to FAISS"
      />

      <div className="p-8 space-y-8 max-w-7xl mx-auto w-full flex-1">
        {/* Upload Card */}
        <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 space-y-5">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Upload className="w-4 h-4 text-emerald-400" />
              Ingest Financial Filing
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Supports .pdf (PyMuPDF page-preserving parser) and .txt filings up to 100MB
            </p>
          </div>

          <form onSubmit={handleUpload} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                  Select File (.pdf, .txt)
                </label>
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".pdf,.txt"
                  onChange={handleFileSelect}
                  className="w-full text-xs text-slate-400 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-850 file:text-emerald-400 hover:file:bg-slate-800 cursor-pointer border border-slate-800 rounded-lg p-1.5 bg-slate-900"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                  Company Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. TechVision Inc."
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                  Ticker / Fiscal Year
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="e.g. TCVX"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                  <input
                    type="text"
                    placeholder="e.g. FY2024"
                    value={fiscalYear}
                    onChange={(e) => setFiscalYear(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1.5">
                  Filing Category
                </label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                >
                  <option value="annual_report">Annual Report (10-K)</option>
                  <option value="quarterly_filing">Quarterly Filing (10-Q)</option>
                  <option value="earnings_transcript">Earnings Transcript</option>
                  <option value="other">Other Disclosure</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-slate-400">
                {file && (
                  <span className="text-emerald-400 font-mono">
                    Ready to ingest: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                )}
              </div>

              <button
                type="submit"
                disabled={uploading || !file}
                className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-navy-950 font-semibold text-xs flex items-center gap-2 transition shadow-md shadow-emerald-500/20"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Extracting & Chunking...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>Process & Index Filing</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Feedback banners */}
          {uploadSuccess && (
            <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{uploadSuccess}</span>
            </div>
          )}

          {uploadError && (
            <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>

        {/* Document Table */}
        <div className="p-6 rounded-2xl bg-navy-950 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Indexed Filing Corpus</h2>
              <p className="text-xs text-slate-400">
                {documents.length} filings indexed in PostgreSQL and FAISS
              </p>
            </div>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition text-xs flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>

          {documents.length === 0 ? (
            <div className="p-12 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30">
              <FileCheck className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white">No filings in corpus</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                Use the upload form above or run the demo script (`python scripts/import_demo_data.py`) to populate sample filings.
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
                    <th className="pb-3 font-semibold">Type</th>
                    <th className="pb-3 font-semibold">Pages / Chunks</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-800/20 transition">
                      <td className="py-3 font-medium text-white flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        <span className="truncate max-w-[260px]">{doc.original_filename}</span>
                        {doc.is_synthetic && (
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[9px] font-mono uppercase">
                            Synthetic
                          </span>
                        )}
                      </td>
                      <td className="py-3 font-mono text-slate-300">
                        {doc.ticker ? `${doc.ticker} (${doc.company_name || ""})` : doc.company_name || "—"}
                      </td>
                      <td className="py-3 font-mono text-slate-300">{doc.fiscal_year || "—"}</td>
                      <td className="py-3 text-slate-400 capitalize">
                        {doc.document_type.replace("_", " ")}
                      </td>
                      <td className="py-3 font-mono text-slate-400">
                        {doc.page_count ?? 1} pgs / {doc.chunk_count ?? 0} chunks
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
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleReindex(doc.id)}
                            disabled={actionInProgress === doc.id}
                            title="Reindex document chunks"
                            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-emerald-400 hover:border-emerald-500/30 transition disabled:opacity-50"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${actionInProgress === doc.id ? "animate-spin" : ""}`} />
                          </button>
                          <button
                            onClick={() => handleDelete(doc.id)}
                            disabled={actionInProgress === doc.id}
                            title="Delete filing & re-sync FAISS"
                            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-red-400 hover:border-red-500/30 transition disabled:opacity-50"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
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
