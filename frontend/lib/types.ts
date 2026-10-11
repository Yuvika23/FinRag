export interface Company {
  id: string;
  name: string;
  ticker: string;
  sector?: string;
  industry?: string;
  currency: string;
  created_at: string;
  document_count?: number;
  metric_count?: number;
}

export interface Document {
  id: string;
  company_id?: string;
  company_name?: string;
  ticker?: string;
  filename: string;
  original_filename: string;
  file_size: number;
  document_type: "annual_report" | "quarterly_filing" | "earnings_transcript" | "csv_metrics" | "other";
  status: "pending" | "processing" | "indexed" | "failed" | "deleted";
  fiscal_year?: string;
  reporting_period?: string;
  page_count?: number;
  chunk_count?: number;
  error_message?: string;
  is_synthetic: boolean;
  created_at: string;
}

export interface Citation {
  chunk_id: string;
  source_document: string;
  page_number?: number;
  ticker?: string;
  fiscal_year?: string;
  similarity_score?: number;
  snippet: string;
}

export interface SQLDataRow {
  company: string;
  ticker: string;
  fiscal_year: string;
  metric: string;
  value: number;
  unit?: string;
  filing_reference?: string;
}

export interface ChatResponse {
  query: string;
  route_taken: "qualitative" | "numerical" | "combined";
  answer: string;
  citations: Citation[];
  sql_data: SQLDataRow[];
  latency_ms: number;
  confidence_score?: number;
  unsupported_query?: boolean;
}

export interface FinancialMetricRow {
  id: string;
  company_id: string;
  company_name: string;
  ticker: string;
  fiscal_year: string;
  period_type: string;
  metric_name: string;
  metric_category: string;
  value: number;
  unit: string;
  filing_reference?: string;
  is_synthetic: boolean;
}

export interface YoYMetric {
  metric_name: string;
  year1_value: number;
  year2_value: number;
  abs_change: number;
  pct_change: number;
  unit: string;
}

export interface YoYComparisonResponse {
  company_name: string;
  ticker: string;
  year1: string;
  year2: string;
  metrics: YoYMetric[];
}

export interface OverviewStats {
  total_documents: number;
  total_companies: number;
  total_chunks: number;
  total_metrics: number;
  fiscal_years_count: number;
  llm_provider: string;
  faiss_total_vectors: number;
}

export interface EvaluationResultItem {
  id: string;
  question: string;
  expected_answer?: string;
  generated_answer?: string;
  recall_at_k?: number;
  precision_at_k?: number;
  mrr?: number;
  citation_accuracy?: number;
  faithfulness?: number;
  latency_ms?: number;
  error?: string;
}

export interface EvaluationRun {
  id: string;
  name: string;
  dataset_path?: string;
  total_questions: number;
  completed_questions: number;
  avg_recall_at_k?: number;
  avg_precision_at_k?: number;
  avg_mrr?: number;
  avg_citation_accuracy?: number;
  avg_faithfulness?: number;
  avg_latency_ms?: number;
  failed_queries: number;
  created_at: string;
  completed_at?: string;
  results?: EvaluationResultItem[];
}
