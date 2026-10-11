import {
  Company,
  Document,
  ChatResponse,
  FinancialMetricRow,
  YoYComparisonResponse,
  OverviewStats,
  EvaluationRun,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status}] ${response.statusText}: ${errorBody}`);
  }

  return response.json();
}

export const api = {
  // System Health
  async getHealth(): Promise<{
    status: string;
    version: string;
    database: string;
    faiss_total_vectors: number;
    llm_provider: string;
  }> {
    return fetchJSON("/api/health");
  },

  // Overview / Analytics
  async getOverviewStats(): Promise<OverviewStats> {
    return fetchJSON("/api/analytics/overview");
  },

  // Companies
  async getCompanies(): Promise<Company[]> {
    return fetchJSON("/api/companies");
  },

  async createCompany(data: {
    name: string;
    ticker: string;
    sector?: string;
    industry?: string;
    currency?: string;
  }): Promise<Company> {
    return fetchJSON("/api/companies", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Documents
  async getDocuments(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    company_id?: string;
  }): Promise<Document[]> {
    const query = new URLSearchParams();
    if (params?.skip) query.set("skip", params.skip.toString());
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.status) query.set("status", params.status);
    if (params?.company_id) query.set("company_id", params.company_id);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return fetchJSON(`/api/documents${qs}`);
  },

  async uploadDocument(formData: FormData): Promise<Document> {
    const response = await fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      body: formData, // do not set Content-Type header so browser adds boundary
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(`Upload failed [${response.status}]: ${err}`);
    }
    return response.json();
  },

  async deleteDocument(id: string): Promise<{ message: string; id: string }> {
    return fetchJSON(`/api/documents/${id}`, { method: "DELETE" });
  },

  async reindexDocument(id: string): Promise<{ message: string; id: string }> {
    return fetchJSON(`/api/documents/${id}/reindex`, { method: "POST" });
  },

  // Research / Chat
  async chat(data: {
    query: string;
    company_id?: string | null;
    fiscal_year?: string | null;
    top_k?: number;
  }): Promise<ChatResponse> {
    return fetchJSON("/api/chat", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Financial Analytics
  async getFinancialMetrics(params?: {
    company_id?: string;
    fiscal_year?: string;
    metric_name?: string;
  }): Promise<FinancialMetricRow[]> {
    const query = new URLSearchParams();
    if (params?.company_id) query.set("company_id", params.company_id);
    if (params?.fiscal_year) query.set("fiscal_year", params.fiscal_year);
    if (params?.metric_name) query.set("metric_name", params.metric_name);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return fetchJSON(`/api/analytics/financials${qs}`);
  },

  async getYoYComparison(params: {
    company_id: string;
    year1: string;
    year2: string;
  }): Promise<YoYComparisonResponse> {
    const query = new URLSearchParams({
      company_id: params.company_id,
      year1: params.year1,
      year2: params.year2,
    });
    return fetchJSON(`/api/analytics/yoy?${query.toString()}`);
  },

  // Evaluation
  async getEvaluationRuns(): Promise<EvaluationRun[]> {
    return fetchJSON("/api/evaluation/results");
  },

  async runEvaluation(data?: { name?: string; dataset_path?: string }): Promise<EvaluationRun> {
    return fetchJSON("/api/evaluation/run", {
      method: "POST",
      body: JSON.stringify(data || {}),
    });
  },
};
