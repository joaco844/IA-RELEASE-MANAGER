// ---------- Auth ----------

export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

// ---------- Repositories ----------

export interface Repository {
  id: number;
  name: string;
  gitlab_url: string;
  project_path: string;
  default_branch: string | null;
  description: string | null;
  last_release_at: string | null;
  created_at: string;
}

export interface RepositoryDetail extends Repository {
  recent_releases: Release[];
}

export interface ConnectRepositoryPayload {
  name?: string;
  gitlab_url: string;
  project_path: string;
  access_token: string;
}

// ---------- Releases ----------

export type ReleaseStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "published";

export type RiskLevel = "low" | "medium" | "high";

export interface Release {
  id: number;
  repository_id: number;
  repository_name: string;
  title: string;
  status: ReleaseStatus;
  range_summary: string;
  risk_level: RiskLevel | null;
  created_at: string;
  completed_at: string | null;
  slack_message_url: string | null;
  error_message: string | null;
}

export interface ReleaseNotes {
  executive: string | null;
  technical: string | null;
  markdown: string | null;
  slack: string | null;
}

export interface QaReport {
  approved: boolean;
  issues_found: string[];
  traceability_score: number;
}

export interface AnalysisItem {
  summary: string;
  business_impact: string;
  technical_impact: string;
  risk_level: string;
}

export interface AnalysisCategory {
  category: string;
  items: AnalysisItem[];
}

export interface ReleaseAnalysis {
  categories: AnalysisCategory[];
}

export interface ReleaseCommit {
  sha: string;
  title: string;
  author_name: string;
  created_at: string;
}

export interface ReleaseIssue {
  iid: number;
  title: string;
  state: string;
  labels: string[];
  web_url: string;
}

export interface ReleaseMergeRequest {
  iid: number;
  title: string;
  state: string;
  author_name: string;
  web_url: string;
}

export interface ReleaseMetrics {
  generation_seconds: number | null;
  commits_analyzed: number;
  issues_analyzed: number;
  mrs_analyzed: number;
}

export interface ReleaseDetail extends Release {
  notes: ReleaseNotes;
  qa_report: QaReport | null;
  analysis: ReleaseAnalysis | null;
  commits: ReleaseCommit[];
  issues: ReleaseIssue[];
  merge_requests: ReleaseMergeRequest[];
  metrics: ReleaseMetrics;
}

export type ReleaseRangeType = "tag_range" | "last_days" | "since_date";

export interface ReleaseRange {
  type: ReleaseRangeType;
  from_tag?: string;
  to_tag?: string;
  days?: number;
  since?: string;
}

export type AiProvider = "openai" | "gemini";

export interface AiConfig {
  provider?: AiProvider;
  temperature?: number;
}

export interface GenerateReleasePayload {
  repository_id: number;
  title?: string;
  range: ReleaseRange;
  ai?: AiConfig;
}

export interface PaginatedReleases {
  items: Release[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReleaseListParams {
  repository_id?: number;
  status?: ReleaseStatus;
  page?: number;
  page_size?: number;
}

// ---------- Issue board ----------

export interface BoardLabel {
  name: string;
  color: string;
  text_color: string;
  description: string | null;
}

export interface BoardIssue {
  iid: number;
  title: string;
  state: string;
  labels: string[];
  author_name: string | null;
  assignee_names: string[];
  milestone: string | null;
  created_at: string | null;
  closed_at: string | null;
  web_url: string | null;
  user_notes_count: number;
}

export type BoardColumnType = "open" | "label" | "closed";

export interface BoardColumn {
  key: string;
  title: string;
  type: BoardColumnType;
  list_id: number | null;
  label: BoardLabel | null;
  issues: BoardIssue[];
}

export interface Board {
  repository_id: number;
  repository_name: string;
  labels: BoardLabel[];
  columns: BoardColumn[];
}

export interface BoardList {
  id: number;
  label: string;
  position: number;
}

export interface BoardColumnRef {
  type: BoardColumnType;
  label?: string | null;
}

export interface CreateBoardIssuePayload {
  title: string;
  description?: string;
  labels: string[];
}

export interface MoveBoardIssuePayload {
  iid: number;
  from_column: BoardColumnRef;
  to_column: BoardColumnRef;
  /** Key of the destination column, used for the optimistic cache update. */
  toKey: string;
}

// ---------- Slack ----------

export interface SlackWorkspace {
  id: number;
  team_name: string;
  default_channel: string;
  connected_at: string;
}

export interface ConnectSlackPayload {
  bot_token: string;
  default_channel: string;
}

export interface PublishReleasePayload {
  release_id: number;
  channel?: string;
}

export interface SlackPublication {
  message_url: string;
  channel: string;
  published_at: string;
}

// ---------- Metrics ----------

export interface MetricsTotals {
  releases: number;
  completed: number;
  commits_analyzed: number;
  issues_analyzed: number;
  mrs_analyzed: number;
  slack_publications: number;
  hours_saved: number;
}

export interface MetricsResponse {
  totals: MetricsTotals;
  avg_generation_seconds: number | null;
  releases_by_week: { week: string; count: number }[];
  categories_breakdown: { category: string; count: number }[];
  recent_generation_times: {
    release_id: number;
    title: string;
    seconds: number;
  }[];
}
