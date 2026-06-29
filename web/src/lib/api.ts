export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type AuthResult = { status: 'success' | 'error'; token?: string; message?: string }
export type Tag = { id: string; name: string }
export type Directory = { id: string; name: string; parent_id: string | null; path: string }
export type Note = { id: string; text: string; directory_id: string | null; tags: Tag[]; created_at: string; updated_at: string }
export type Preset = {
  id: string
  name: string
  is_active: number
  llm_provider: string
  llm_model: string
  llm_base_url?: string | null
  llm_temperature: number
  llm_max_retries: number
  llm_max_tokens: number
  embedding_provider: string
  embedding_model: string
  embedding_base_url?: string | null
  chunk_size: number
  chunk_overlap: number
}

type Options = RequestInit & { token?: string | null }

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`)
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok || data?.status === 'error') throw new Error(data?.message || data?.detail || res.statusText)
  return data as T
}

export const authApi = {
  signIn: (username: string, password: string) =>
    api<AuthResult>('/api/auth/sign_in', { method: 'POST', body: JSON.stringify({ username, password }) }),
  signUp: (username: string, password: string) =>
    api<AuthResult>('/api/auth/sign_up', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: (token: string) => api<{ id: string }>('/api/auth/me', { token }),
}
