# FinRAG Retrieval and Generation Evaluation Methodology

Evaluating Financial RAG systems requires rigorous quantitative measurement across two distinct dimensions:
1. **Retrieval Precision**: Did the search engine find the authoritative disclosure paragraphs and tables?
2. **Generation Faithfulness & Citation Accuracy**: Did the generated synthesis attribute facts only to retrieved chunks without hallucinating figures?

FinRAG incorporates a standardized evaluation harness with an embedded financial evaluation benchmark (`data/evaluation/eval_dataset.json`).

---

## 1. Core Metrics Defined

### 1.1 Recall@K
Measures whether the gold-standard source documents or sections are present in the top-$K$ retrieved passages.

$$\text{Recall@}K = \frac{|\text{Retrieved Top-}K \cap \text{Relevant Gold Chunks}|}{|\text{Relevant Gold Chunks}|}$$

A high Recall@K guarantees that the LLM has access to the necessary evidentiary context.

### 1.2 Precision@K
Measures the proportion of retrieved chunks in the top-$K$ that are genuinely relevant to answering the prompt.

$$\text{Precision@}K = \frac{|\text{Retrieved Top-}K \cap \text{Relevant Gold Chunks}|}{K}$$

High Precision@K minimizes context pollution and reduces LLM distractors.

### 1.3 Mean Reciprocal Rank (MRR)
Measures where the first relevant gold chunk ranks in the retrieval list:

$$\text{MRR} = \frac{1}{\text{rank}_1}$$

Where $\text{rank}_1$ is the position of the first relevant passage. If the top passage is relevant, $\text{MRR} = 1.0$.

### 1.4 Citation Accuracy
Verifies whether each cited passage or page reference in the response directly supports the statement it is attached to:
- Passages cited in the response are cross-referenced with retrieved chunk text.
- If an answer cites `[Document: TechVision FY2024, Page 3]`, the evaluation verifies that page 3 of that filing actually contains the cited facts.
- Binary or ratio score: fraction of generated citations that accurately map to retrieved evidence.

### 1.5 Faithfulness (Groundedness)
Measures the degree to which all claims in the generated response can be inferred purely from the provided context passages.
- Statements in the generated response are broken down into atomic financial propositions (e.g., "Revenue grew by 14.8%", "Operating margin expanded to 21.6%").
- Each claim is verified against retrieved chunks and structured SQL query results.
- Penalizes hallucinated figures, fabricated metrics, or unverifiable commentary.

---

## 2. Evaluation Dataset Structure

The benchmark suite (`data/evaluation/eval_dataset.json`) covers four distinct financial question archetypes:

1. **Numerical & Comparative Queries**:
   - *Example*: "What was TechVision's revenue and net income growth from FY2023 to FY2024?"
   - *Target*: Exact SQL metric extraction, correct YoY percentage calculations ($+14.8\%$ and $+26.7\%$).
2. **Qualitative Disclosures**:
   - *Example*: "What key risk factors did TechVision disclose regarding customer concentration and AI infrastructure?"
   - *Target*: Semantic search retrieval of Risk Factors section, citing exact page numbers.
3. **Combined Hybrid Inquiries**:
   - *Example*: "Explain the drivers behind TechVision's operating margin expansion in FY2024."
   - *Target*: Synthesis combining structured metric table (21.6% vs 19.5%) with management discussion & analysis (MD&A) passages.
4. **Unsupported / Out-of-Domain Inquiries**:
   - *Example*: "What is TechVision's projected FY2028 guidance for quantum computing hardware?"
   - *Target*: Refusal or explicit disclosure that the indexed documents do not contain guidance for that horizon.

---

## 3. Running Evaluations

Via REST API:
```http
POST /api/evaluation/run
Content-Type: application/json

{
  "dataset_path": "data/evaluation/eval_dataset.json",
  "name": "Benchmark Run v1"
}
```

Via Frontend:
Navigate to `/evaluation`, click **Run Benchmark**, and observe real-time score progression across Recall@K, Precision@K, MRR, Citation Accuracy, and Faithfulness.
