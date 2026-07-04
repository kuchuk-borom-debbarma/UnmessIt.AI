export const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:2317' : '')

export type AuthResult = { status: 'success' | 'error'; token?: string; message?: string }
export type Tag = { id: string; name: string }
export type Directory = { id: string; name: string; parent_id: string | null; path: string }
export type Note = {
  id: string
  text: string
  directory_id: string | null
  user_id: string
  tags: Tag[]
  created_at: string
  updated_at: string
  metadata?: { filename?: string; extension?: string; [key: string]: any }
  job_status?: 'queued' | 'running' | 'waiting_retry' | 'complete' | 'failed' | 'aborted' | 'paused'
}
export type Preset = {
  id: string
  name: string
  is_active: number
  llm_is_active?: number
  embedding_is_active?: number
  llm_provider: string
  llm_model: string
  llm_base_url?: string | null
  llm_temperature: number
  llm_max_retries: number
  llm_max_tokens?: number | null
  embedding_provider: string
  embedding_model: string
  embedding_base_url?: string | null
  llm_rate_limit_per_minute: number
  embedding_rate_limit_per_minute: number
  embedding_batch_size: number
  chunk_size: number
  chunk_overlap: number
  ingest_retry_backoff_seconds: string
}

export type ProcessingSettings = {
  embedding_batch_size: number
  chunk_size: number
  chunk_overlap: number
  ingest_retry_backoff_seconds: string
}

export type LLMConfig = {
  id: string
  name: string
  llm_provider: string
  llm_model: string
  llm_base_url?: string | null
  llm_temperature: number
  llm_max_retries: number
  llm_max_tokens?: number | null
  llm_rate_limit_per_minute: number
}

export type EmbeddingConfig = {
  id: string
  name: string
  embedding_provider: string
  embedding_model: string
  embedding_base_url?: string | null
  embedding_rate_limit_per_minute: number
  embedding_batch_size: number
}

export type StageRoute = {
  stage: string
  kind: 'llm' | 'embedding'
  enabled: boolean
  config_ids: string[]
  active_config_id?: string | null
}

export type StageConfig = {
  llm: Record<string, StageRoute>
  embedding: Record<string, StageRoute>
  llm_configs: LLMConfig[]
  embedding_configs: EmbeddingConfig[]
}

export type RotationConfig = {
  enabled: boolean
  preset_ids: string[]
  presets: Preset[]
  llm: RotationLane
  embedding: RotationLane
}

export type RotationLane = {
  enabled: boolean
  preset_ids: string[]
  active_preset_id?: string | null
  presets: Preset[]
}

export type ConfigTestResult = {
  status: 'ok'
  status_code: number
  kind: 'llm' | 'embedding'
  message: string
}

type Options = RequestInit & { token?: string | null }

export class ApiError extends Error {
  status: number
  kind: 'network' | 'api' | 'server'
  upstreamStatus?: number

  constructor(message: string, status: number, kind: 'network' | 'api' | 'server', upstreamStatus?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.kind = kind
    this.upstreamStatus = upstreamStatus
  }
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`)
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch (err) {
    throw new ApiError(`API connection failed. Is the backend running? ${err instanceof Error ? err.message : String(err)}`, 0, 'network')
  }
  const text = await res.text()
  let data: any = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    if (!res.ok) throw new ApiError(`Server returned ${res.status} ${res.statusText}: ${text.slice(0, 240)}`, res.status, res.status >= 500 ? 'server' : 'api')
    throw new ApiError(`Server returned invalid JSON with status ${res.status}.`, res.status, 'server')
  }
  if (!res.ok || data?.status === 'error') {
    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent('unmessit:logout'))
    }
    throw makeApiError(res, data)
  }
  return data as T
}

function makeApiError(res: Response, data: any) {
  const detail = data?.detail
  const upstreamStatus = typeof detail?.upstream_status === 'number' ? detail.upstream_status : undefined
  const detailMessage = formatDetail(detail, upstreamStatus)
  const message = data?.message || detailMessage || res.statusText || 'Request failed'
  const kind = detail?.kind === 'api' || res.status === 502 || res.status === 503 || res.status === 504
    ? 'api'
    : res.status >= 500 ? 'server' : 'api'
  const prefix = kind === 'server' ? 'Internal server error' : 'API/provider error'
  return new ApiError(`${prefix} (${res.status}): ${message}`, res.status, kind, upstreamStatus)
}

function formatDetail(detail: any, upstreamStatus?: number) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (item?.msg) return `${Array.isArray(item.loc) ? item.loc.join('.') : 'field'}: ${item.msg}`
      return JSON.stringify(item)
    }).join('; ')
  }
  if (detail?.message) return [detail.message, upstreamStatus ? `upstream ${upstreamStatus}` : ''].filter(Boolean).join(' ')
  return [upstreamStatus ? `upstream ${upstreamStatus}` : '', detail?.error].filter(Boolean).join(' ')
}

export const authApi = {
  signIn: (username: string, password: string) =>
    api<AuthResult>('/api/v1/auth/sign_in', { method: 'POST', body: JSON.stringify({ username, password }) }),
  signUp: (username: string, password: string) =>
    api<AuthResult>('/api/v1/auth/sign_up', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: (token: string) => api<{ id: string; identifier: string }>('/api/v1/auth/me', { token }),
}
