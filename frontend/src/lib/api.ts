const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type RankingStrategy =
  | "keyword"
  | "embedding"
  | "cross_encoder"
  | "citation_expansion";

export interface SearchFilters {
  venues?: string[];
  year_from?: number;
  year_to?: number;
  max_candidates?: number;
  citation_depth?: number;
}

export interface SearchRequest {
  topic: string;
  filters?: SearchFilters;
  strategies?: RankingStrategy[];
}

export interface Paper {
  sources: Array<{ provider: "arxiv" | "openalex"; identifier: string }>;
  title: string;
  abstract: string;
  authors: Array<{ name: string; orcid: string | null }>;
  categories: string[];
  doi: string | null;
  arxiv_id: string | null;
  citation_count: number;
  published_on: string;
  updated_on: string | null;
  venue: string | null;
  landing_page_url: string;
  pdf_url: string | null;
}

export interface RankedPaper {
  paper: Paper;
  rank: number;
  score: number;
  strategy: RankingStrategy;
}

export interface SearchOutcome {
  search_id: string;
  topic: string;
  ranking_strategy: RankingStrategy;
  results: RankedPaper[];
  diagnostics: {
    provider_candidates: Record<string, number>;
    candidate_count: number;
    deduplicated_count: number;
    returned_count: number;
    elapsed_ms: number;
    warnings: string[];
  };
}

export interface EvidenceClaim {
  summary: string;
  evidence: Array<{ quote: string; section: "title" | "abstract" }>;
}

export interface PaperExtraction {
  problem: EvidenceClaim;
  method: EvidenceClaim;
  results: EvidenceClaim[];
  contributions: EvidenceClaim[];
  limitations: EvidenceClaim[];
  keywords: string[];
}

export interface ExtractionUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface CompletedExtraction {
  paper_id: string;
  rank: number;
  title: string;
  run: {
    extraction: PaperExtraction;
    model: string;
    prompt_version: string;
    provider_response_id: string;
    usage: ExtractionUsage;
    elapsed_ms: number;
  };
}

export interface ExtractionBatch {
  search_id: string;
  requested_count: number;
  completed: CompletedExtraction[];
  failures: Array<{ paper_id: string; rank: number; title: string; error: string }>;
  usage: ExtractionUsage;
}

export interface ResearchLandscape {
  search_id: string;
  clustered: {
    clusters: Array<{ cluster_id: number; label: string; paper_ids: string[] }>;
    positions: Array<{
      paper_id: string;
      cluster_id: number;
      membership_score: number;
      x: number;
      y: number;
    }>;
    similarity_edges: Array<{
      source_paper_id: string;
      target_paper_id: string;
      similarity: number;
    }>;
    silhouette_score: number | null;
  };
  synthesis_run: {
    synthesis: {
      overview: string;
      clusters: Array<{
        cluster_id: number;
        name: string;
        summary: string;
        evidence_paper_ids: string[];
      }>;
      relationships: Array<{
        source_paper_id: string;
        target_paper_id: string;
        kind: "supports" | "extends" | "contrasts" | "shares_method";
        summary: string;
      }>;
      tensions: Array<{ summary: string; evidence_paper_ids: string[] }>;
      open_questions: Array<{
        question: string;
        rationale: string;
        evidence_paper_ids: string[];
      }>;
    };
    model: string;
    prompt_version: string;
    provider_response_id: string;
    usage: ExtractionUsage;
    elapsed_ms: number;
  };
}

export interface HealthResponse {
  status: "healthy";
  service: string;
  version: string;
  environment: "development" | "test" | "production";
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Keep transport and error parsing consistent across every pipeline action.
async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(
      payload?.detail ?? `Request failed with status ${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/v1/health");
}

export function createSearch(request: SearchRequest): Promise<SearchOutcome> {
  return requestJson<SearchOutcome>("/api/v1/searches", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function extractPapers(searchId: string, limit: number): Promise<ExtractionBatch> {
  return requestJson<ExtractionBatch>(`/api/v1/searches/${searchId}/extractions`, {
    method: "POST",
    body: JSON.stringify({ limit }),
  });
}

export function buildLandscape(searchId: string): Promise<ResearchLandscape> {
  return requestJson<ResearchLandscape>(`/api/v1/searches/${searchId}/landscape`, {
    method: "POST",
  });
}

export function getLandscape(searchId: string): Promise<ResearchLandscape> {
  return requestJson<ResearchLandscape>(`/api/v1/searches/${searchId}/landscape`);
}
