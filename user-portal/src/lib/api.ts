export type TokenGetter = () => string | null | Promise<string | null>;

function apiBase(): string {
  const v = import.meta.env.VITE_API_URL?.replace(/\/$/, '').trim();
  return v || 'http://localhost:8000';
}

/** Public API origin (no trailing slash). */
export const API_URL = apiBase();

let tokenGetter: TokenGetter = () => {
  try {
    return (
      localStorage.getItem('ca:idToken') ?? sessionStorage.getItem('access_token') ?? null
    );
  } catch {
    return null;
  }
};

/** Replace default token resolution when wiring Cognito or another auth provider. */
export function setTokenGetter(fn: TokenGetter): void {
  tokenGetter = fn;
}

/**
 * Fetch against the API base URL with optional Bearer token from `setTokenGetter`
 * or `ca:idToken` / `access_token` in storage.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const base = apiBase();
  const url = path.startsWith('http') ? path : `${base}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers = new Headers(init.headers);
  const token = await Promise.resolve(tokenGetter());
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(url, { ...init, headers });
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await apiFetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let code = 'UNKNOWN';
    let message = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      if (errBody.error) {
        code = errBody.error.code ?? code;
        message = errBody.error.message ?? message;
      }
    } catch {
      // ignore
    }
    if (response.status === 401) {
      try {
        localStorage.removeItem('ca:idToken');
        localStorage.removeItem('ca:refreshToken');
        localStorage.removeItem('ca:expiresAt');
      } catch {
        // ignore storage errors
      }
      const current = window.location.pathname;
      if (current !== '/login' && current !== '/signup' && current !== '/auth/callback') {
        window.location.assign('/login');
      }
    }
    if (response.status === 403 && code === 'TRIAL_EXPIRED') {
      // Global signal: any component listening for this can render the paywall modal.
      window.dispatchEvent(new CustomEvent('subscription-required', { detail: { message } }));
    }
    throw new ApiError(response.status, code, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

// ----- Types mirroring backend schemas -----

export interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  cards: Array<{ type: string; data: Record<string, unknown> }> | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: Message[];
}

export interface SubscriptionOut {
  id: string;
  user_id: string;
  plan: string;
  status: string;
  trial_ends_at: string | null;
  current_period_end: string | null;
  past_due_since: string | null;
  cancel_at_period_end: boolean;
  stripe_customer_id: string | null;
  has_active_entitlement: boolean;
}

// ----- Phase 2c types -----

export interface CompanyRef {
  name: string;
  platform: 'greenhouse' | 'ashby' | 'lever';
  board_slug: string;
}

export interface ScanConfig {
  id: string;
  user_id: string;
  name: string;
  companies: CompanyRef[];
  keywords: string[] | null;
  exclude_keywords: string[] | null;
  schedule: 'manual' | 'daily' | 'weekly';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScanRun {
  id: string;
  user_id: string;
  scan_config_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  jobs_found: number;
  jobs_new: number;
  truncated: boolean;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface ScanResult {
  id: string;
  job_id: string;
  relevance_score: number | null;
  is_new: boolean;
  created_at: string;
}

export interface ScanRunDetail {
  scan_run: ScanRun;
  results: ScanResult[];
}

export interface BatchRun {
  id: string;
  user_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_jobs: number;
  l0_passed: number;
  l1_passed: number;
  l2_evaluated: number;
  source_type: string;
  source_ref: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface BatchItemsSummary {
  queued: number;
  l0: number;
  l1: number;
  l2: number;
  done: number;
  filtered: number;
}

export interface BatchEvaluationSummary {
  evaluation_id: string;
  job_id: string;
  job_title: string;
  company: string | null;
  overall_grade: string;
  match_score: number;
}

export interface BatchRunDetail {
  batch_run: BatchRun;
  items_summary: BatchItemsSummary;
  top_results: BatchEvaluationSummary[];
}

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  status: 'saved' | 'applied' | 'interviewing' | 'offered' | 'rejected' | 'withdrawn';
  applied_at: string | null;
  notes: string | null;
  evaluation_id: string | null;
  cv_output_id: string | null;
  negotiation_id: string | null;
  updated_at: string;
}

// ----- Phase 2d: interview prep, negotiation, star stories, feedback -----

export interface InterviewPrep {
  id: string;
  user_id: string;
  job_id: string | null;
  custom_role: string | null;
  questions: Array<Record<string, unknown>>;
  red_flag_questions: Array<Record<string, unknown>> | null;
  model_used: string;
  tokens_used: number | null;
  created_at: string;
}

export interface Negotiation {
  id: string;
  user_id: string;
  job_id: string;
  offer_details: Record<string, unknown>;
  market_research: Record<string, unknown>;
  counter_offer: Record<string, unknown>;
  scripts: Record<string, unknown>;
  model_used: string;
  tokens_used: number | null;
  created_at: string;
}

export interface StarStory {
  id: string;
  user_id: string;
  title: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  reflection: string | null;
  tags: string[] | null;
  source: 'ai_generated' | 'user_created';
  created_at: string;
}

export type FeedbackResource =
  | 'evaluation'
  | 'cv_output'
  | 'interview_prep'
  | 'negotiation';

export interface Profile {
  user_id: string;
  master_resume_md: string | null;
  master_resume_s3: string | null;
  parsed_resume_json: Record<string, unknown> | null;
  target_roles: string[] | null;
  target_locations: string[] | null;
  min_salary: number | null;
  preferred_industries: string[] | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  onboarding_state: 'resume_upload' | 'preferences' | 'done';
  created_at: string;
  updated_at: string;
}

export interface ParsedJob {
  content_hash: string;
  url: string | null;
  title: string;
  company: string | null;
  location: string | null;
  salary_min: number | null;
  salary_max: number | null;
  employment_type: string | null;
  seniority: string | null;
  description_md: string;
  requirements_json: Record<string, unknown> | null;
}

export type EvaluationGrade = 'A' | 'A-' | 'B+' | 'B' | 'C';

export interface EvaluationDetail {
  id: string;
  user_id: string;
  job_id: string;
  overall_grade: string;
  dimension_scores: Record<
    string,
    { score: number; grade: string; reasoning: string; signals?: string[] }
  >;
  reasoning: string;
  red_flags: string[] | null;
  personalization: string | null;
  match_score: number;
  recommendation: 'strong_match' | 'worth_exploring' | 'skip';
  model_used: string;
  tokens_used: number | null;
  cached: boolean;
  created_at: string;
}

export interface FirstEvaluationResponse {
  evaluation: {
    id: string;
    overall_grade: EvaluationGrade | string;
    match_score: number | null;
    dimension_scores: Record<string, unknown>;
    reasoning: string | null;
    recommendation: string | null;
    red_flags: unknown;
    personalization: unknown;
    cached: boolean;
    job_id: string | null;
  };
  job: {
    content_hash: string;
    url: string | null;
    title: string;
    company: string | null;
    location: string | null;
    description_md: string;
  };
}

// ----- API methods -----

export const api = {
  listConversations: () => request<{ data: Conversation[] }>('GET', '/api/v1/conversations'),
  createConversation: (title: string | null = null) =>
    request<{ data: Conversation }>('POST', '/api/v1/conversations', { title }),
  getConversation: (id: string) =>
    request<{ data: ConversationDetail }>('GET', `/api/v1/conversations/${id}`),
  sendMessage: (conversationId: string, content: string) =>
    request<{ data: Message; meta: { tokens_used: number; cost_cents?: number } }>(
      'POST',
      `/api/v1/conversations/${conversationId}/messages`,
      { content },
    ),
  /** Stripe Checkout — returns Stripe-hosted URL the browser should navigate to */
  startCheckout: () =>
    request<{ data: { url: string } }>('POST', '/api/v1/billing/checkout', {}),
  /** Stripe Customer Portal — returns Stripe-hosted URL the browser should navigate to */
  openPortal: () => request<{ data: { url: string } }>('POST', '/api/v1/billing/portal', {}),
  /** Current subscription state for the logged-in user */
  getSubscription: () =>
    request<{ data: SubscriptionOut }>('GET', '/api/v1/billing/subscription'),

  scanConfigs: {
    list: () => request<{ data: ScanConfig[] }>('GET', '/api/v1/scan-configs'),
    create: (body: {
      name: string;
      companies: CompanyRef[];
      keywords?: string[] | null;
      exclude_keywords?: string[] | null;
      schedule?: 'manual' | 'daily' | 'weekly';
    }) => request<{ data: ScanConfig }>('POST', '/api/v1/scan-configs', body),
    get: (id: string) => request<{ data: ScanConfig }>('GET', `/api/v1/scan-configs/${id}`),
    update: (id: string, body: Partial<ScanConfig>) =>
      request<{ data: ScanConfig }>('PUT', `/api/v1/scan-configs/${id}`, body),
    delete: (id: string) => request<void>('DELETE', `/api/v1/scan-configs/${id}`),
    run: (id: string) =>
      request<{ data: { scan_run_id: string; status: string } }>(
        'POST',
        `/api/v1/scan-configs/${id}/run`,
        {},
      ),
  },
  scanRuns: {
    list: (params: { limit?: number; status?: string } = {}) => {
      const qs = new URLSearchParams();
      if (params.limit) qs.set('limit', String(params.limit));
      if (params.status) qs.set('status', params.status);
      return request<{ data: ScanRun[] }>(
        'GET',
        `/api/v1/scan-runs${qs.size ? `?${qs}` : ''}`,
      );
    },
    get: (id: string) =>
      request<{ data: ScanRunDetail }>('GET', `/api/v1/scan-runs/${id}`),
  },
  batchRuns: {
    create: (
      body:
        | { job_urls: string[] }
        | { job_ids: string[] }
        | { scan_run_id: string },
    ) => request<{ data: BatchRun }>('POST', '/api/v1/batch-runs', body),
    list: () => request<{ data: BatchRun[] }>('GET', '/api/v1/batch-runs'),
    get: (id: string) =>
      request<{ data: BatchRunDetail }>('GET', `/api/v1/batch-runs/${id}`),
  },
  applications: {
    list: (params: { status?: string; min_grade?: string } = {}) => {
      const qs = new URLSearchParams();
      if (params.status) qs.set('status', params.status);
      if (params.min_grade) qs.set('min_grade', params.min_grade);
      return request<{ data: Application[] }>(
        'GET',
        `/api/v1/applications${qs.size ? `?${qs}` : ''}`,
      );
    },
    create: (body: {
      job_id: string;
      status?: Application['status'];
      evaluation_id?: string;
      cv_output_id?: string;
      notes?: string;
    }) => request<{ data: Application }>('POST', '/api/v1/applications', body),
    update: (id: string, body: Partial<Application>) =>
      request<{ data: Application }>('PUT', `/api/v1/applications/${id}`, body),
    delete: (id: string) => request<void>('DELETE', `/api/v1/applications/${id}`),
  },

  interviewPreps: {
    list: (limit = 20) =>
      request<{ data: InterviewPrep[] }>('GET', `/api/v1/interview-preps?limit=${limit}`),
    get: (id: string) =>
      request<{ data: InterviewPrep }>('GET', `/api/v1/interview-preps/${id}`),
    create: (body: { job_id?: string | null; custom_role?: string | null }) =>
      request<{ data: InterviewPrep }>('POST', '/api/v1/interview-preps', body),
    regenerate: (id: string, body: { feedback?: string | null }) =>
      request<{ data: InterviewPrep }>(
        'POST',
        `/api/v1/interview-preps/${id}/regenerate`,
        body,
      ),
  },

  negotiations: {
    list: (limit = 20) =>
      request<{ data: Negotiation[] }>('GET', `/api/v1/negotiations?limit=${limit}`),
    get: (id: string) =>
      request<{ data: Negotiation }>('GET', `/api/v1/negotiations/${id}`),
    create: (body: {
      job_id: string;
      offer_details: {
        base: number;
        equity?: string | null;
        signing_bonus?: number | null;
        total_comp?: number | null;
        location?: string | null;
        start_date?: string | null;
      };
    }) => request<{ data: Negotiation }>('POST', '/api/v1/negotiations', body),
    regenerate: (id: string, body: { feedback?: string | null }) =>
      request<{ data: Negotiation }>(
        'POST',
        `/api/v1/negotiations/${id}/regenerate`,
        body,
      ),
  },

  starStories: {
    list: (tags?: string) => {
      const qs = tags ? `?tags=${encodeURIComponent(tags)}` : '';
      return request<{ data: StarStory[] }>('GET', `/api/v1/star-stories${qs}`);
    },
    get: (id: string) =>
      request<{ data: StarStory }>('GET', `/api/v1/star-stories/${id}`),
    create: (body: {
      title: string;
      situation: string;
      task: string;
      action: string;
      result: string;
      reflection?: string | null;
      tags?: string[] | null;
    }) => request<{ data: StarStory }>('POST', '/api/v1/star-stories', body),
    update: (id: string, body: Partial<StarStory>) =>
      request<{ data: StarStory }>('PUT', `/api/v1/star-stories/${id}`, body),
    delete: (id: string) => request<void>('DELETE', `/api/v1/star-stories/${id}`),
  },

  profile: {
    get: () => request<{ data: Profile }>('GET', '/api/v1/profile'),
    uploadResume: async (form: FormData) => {
      const response = await apiFetch('/api/v1/profile/resume', {
        method: 'POST',
        body: form,
      });
      if (!response.ok) {
        let code = 'UNKNOWN';
        let message = `HTTP ${response.status}`;
        try {
          const errBody = await response.json();
          if (errBody.error) {
            code = errBody.error.code ?? code;
            message = errBody.error.message ?? message;
          }
        } catch {
          // ignore
        }
        throw new ApiError(response.status, code, message);
      }
      return (await response.json()) as { data: Profile };
    },
    uploadResumeText: (text: string) =>
      request<{ data: Profile }>('POST', '/api/v1/profile/resume-text', { text }),
  },

  jobs: {
    parse: (body: { url?: string; description_md?: string }) =>
      request<{ data: ParsedJob }>('POST', '/api/v1/jobs/parse', body),
    parseText: (body: { text: string; source_url?: string }) =>
      request<{ data: ParsedJob }>('POST', '/api/v1/jobs/parse-text', body),
  },

  onboarding: {
    firstEvaluation: (body: {
      job_input: { type: 'url' | 'text'; value: string };
    }) =>
      request<{ data: FirstEvaluationResponse }>(
        'POST',
        '/api/v1/onboarding/first-evaluation',
        body,
      ),
  },

  evaluations: {
    get: (id: string) =>
      request<{ data: EvaluationDetail }>('GET', `/api/v1/evaluations/${id}`),
  },

  feedback: {
    post: (
      resource: FeedbackResource,
      id: string,
      body: { rating: number; correction_notes?: string | null },
    ) => {
      const paths: Record<FeedbackResource, string> = {
        evaluation: `/api/v1/evaluations/${id}/feedback`,
        cv_output: `/api/v1/cv-outputs/${id}/feedback`,
        interview_prep: `/api/v1/interview-preps/${id}/feedback`,
        negotiation: `/api/v1/negotiations/${id}/feedback`,
      };
      return request<{ data: { id: string } }>('POST', paths[resource], body);
    },
  },
};
