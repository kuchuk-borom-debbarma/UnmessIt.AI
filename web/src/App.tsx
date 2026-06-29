import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Folder,
  FolderPlus,
  KeyRound,
  Layers3,
  LogIn,
  LogOut,
  Play,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings,
  Shield,
  Sparkles,
  Trash2,
  UserPlus,
} from 'lucide-react'
import { API_BASE, api, authApi } from './lib/api'
import type { Directory, Note, Preset } from './lib/api'
import { cn } from './lib/utils'

type View = 'notes' | 'ask' | 'memory' | 'jobs' | 'settings'
type Job = { id: string; status: string; stage: string; error?: string; created_at?: string; updated_at?: string }
type MemoryItem = { id: string; content: string; created_at: string; source_chunks?: Array<{ id: string; summary: string; text: string }> }
type RecallKey = { id: string; name: string; kind: string; summary: string; link_count: number; links: unknown[] }
type ToastTone = 'neutral' | 'success' | 'danger'
type Toast = { message: string; tone?: ToastTone }

type PresetDraft = {
  name: string
  llm_provider: string
  llm_model: string
  llm_base_url: string
  llm_api_key: string
  llm_temperature: string
  llm_max_retries: string
  llm_max_tokens: string
  embedding_provider: string
  embedding_model: string
  embedding_base_url: string
  embedding_api_key: string
  chunk_size: string
  chunk_overlap: string
}

const tokenKey = 'unmessit.token'

const navItems: Array<{ id: View; label: string; icon: LucideIcon; kicker: string }> = [
  { id: 'notes', label: 'Notes', icon: FileText, kicker: 'Capture' },
  { id: 'ask', label: 'Ask AI', icon: Bot, kicker: 'Search' },
  { id: 'memory', label: 'Memory', icon: Database, kicker: 'Evidence' },
  { id: 'jobs', label: 'Indexing', icon: Activity, kicker: 'Pipeline' },
  { id: 'settings', label: 'Settings', icon: Settings, kicker: 'Models' },
]

const viewCopy: Record<View, { title: string; subtitle: string }> = {
  notes: { title: 'Notes', subtitle: 'Write, tag, and organize source material.' },
  ask: { title: 'Ask AI', subtitle: 'Query saved knowledge with source-backed answers.' },
  memory: { title: 'Memory', subtitle: 'Review indexed sources, chunks, and recall keys.' },
  jobs: { title: 'Indexing', subtitle: 'Track ingestion work and repair failed jobs.' },
  settings: { title: 'Settings', subtitle: 'Manage AI presets for this account.' },
}

const defaultDraft: PresetDraft = {
  name: 'Primary AI preset',
  llm_provider: 'openai',
  llm_model: '',
  llm_base_url: '',
  llm_api_key: '',
  llm_temperature: '0',
  llm_max_retries: '2',
  llm_max_tokens: '2048',
  embedding_provider: 'openai',
  embedding_model: '',
  embedding_base_url: '',
  embedding_api_key: '',
  chunk_size: '1000',
  chunk_overlap: '200',
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(tokenKey))
  const [view, setView] = useState<View>('notes')

  const saveToken = (next: string | null) => {
    if (next) localStorage.setItem(tokenKey, next)
    else localStorage.removeItem(tokenKey)
    setToken(next)
  }

  if (!token) return <AuthScreen onToken={saveToken} />

  const activeView = viewCopy[view]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <BrandLockup variant="light" />
          <nav className="mt-8 space-y-1.5" aria-label="Primary">
            {navItems.map((item) => (
              <NavItem key={item.id} item={item} active={view === item.id} onClick={() => setView(item.id)} />
            ))}
          </nav>
        </div>
        <button className="btn-ghost w-full justify-start" onClick={() => saveToken(null)}>
          <LogOut size={17} /> Logout
        </button>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="flex min-w-0 items-center gap-3 lg:hidden">
            <BrandMark size="sm" />
            <span className="truncate text-sm font-semibold">UnmessIt.AI</span>
          </div>
          <div className="hidden min-w-0 lg:block">
            <p className="eyebrow">{activeView.title}</p>
            <h1 className="page-title">{activeView.subtitle}</h1>
          </div>
          <div className="topbar-actions">
            <StatusPill icon={Sparkles} label="AI presets" />
            <StatusPill icon={Shield} label="Private account" />
            <button className="icon-button lg:hidden" onClick={() => saveToken(null)} aria-label="Logout">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <nav className="mobile-tabs" aria-label="Mobile navigation">
          {navItems.map((item) => (
            <button key={item.id} className={cn('mobile-tab', view === item.id && 'mobile-tab-active')} onClick={() => setView(item.id)}>
              <item.icon size={16} /> {item.label}
            </button>
          ))}
        </nav>

        <div className="content-wrap">
          {view === 'notes' && <NotesView token={token} />}
          {view === 'ask' && <AskView token={token} />}
          {view === 'memory' && <MemoryView token={token} />}
          {view === 'jobs' && <JobsView token={token} />}
          {view === 'settings' && <SettingsView token={token} />}
        </div>
      </main>
    </div>
  )
}

function AuthScreen({ onToken }: { onToken: (token: string) => void }) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [toast, setToast] = useState<Toast | null>(null)
  const [loading, setLoading] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setToast(null)
    try {
      const result = mode === 'signin' ? await authApi.signIn(username, password) : await authApi.signUp(username, password)
      if (!result.token) throw new Error(result.message || 'No token returned')
      onToken(result.token)
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Authentication failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-visual">
        <BrandLockup variant="light" />
        <div className="auth-copy">
          <p className="eyebrow-light">AI knowledge workspace</p>
          <h1>Turn saved notes into answers you can trust.</h1>
        </div>
        <div className="signal-board" aria-hidden="true">
          <div className="signal-row">
            <span>Research notes</span>
            <FileText size={18} />
          </div>
          <div className="signal-row signal-row-accent">
            <span>AI answer</span>
            <Bot size={18} />
          </div>
          <div className="signal-row">
            <span>Source evidence</span>
            <Layers3 size={18} />
          </div>
        </div>
      </section>

      <section className="auth-form-wrap">
        <form onSubmit={submit} className="auth-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Welcome</p>
              <h2 className="form-title">{mode === 'signin' ? 'Sign in' : 'Create account'}</h2>
            </div>
            <BrandMark size="md" />
          </div>

          <div className="segmented mt-7">
            <button type="button" className={cn('segment', mode === 'signin' && 'segment-active')} onClick={() => setMode('signin')}>
              <LogIn size={16} /> Sign in
            </button>
            <button type="button" className={cn('segment', mode === 'signup' && 'segment-active')} onClick={() => setMode('signup')}>
              <UserPlus size={16} /> Create
            </button>
          </div>

          <Field label="Username">
            <input className="input" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </Field>
          <Field label="Password">
            <input
              className="input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
            />
          </Field>

          {toast && <ToastMessage toast={toast} />}

          <button className="btn-primary w-full" disabled={loading || !username || !password}>
            {loading ? <RefreshCw className="animate-spin" size={17} /> : <Shield size={17} />}
            {mode === 'signin' ? 'Sign in' : 'Create account'}
          </button>
        </form>
      </section>
    </main>
  )
}

function NotesView({ token }: { token: string }) {
  const [directories, setDirectories] = useState<Directory[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [selectedDir, setSelectedDir] = useState<string | null>(null)
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [text, setText] = useState('')
  const [tagText, setTagText] = useState('')
  const [dirName, setDirName] = useState('')
  const [toast, setToast] = useState<Toast | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    const notePath = selectedDir ? `/notes/?directory_id=${selectedDir}` : '/notes/?all=true'
    const [dirRes, noteRes] = await Promise.all([
      api<{ data: Directory[] }>('/directories/?all=true', { token }),
      api<{ data: Note[] }>(notePath, { token }),
    ])
    setDirectories(dirRes.data)
    setNotes(noteRes.data)
  }, [selectedDir, token])

  useEffect(() => {
    load().catch((err) => setToast({ tone: 'danger', message: err.message }))
  }, [load])

  const noteCountLabel = `${notes.length} ${notes.length === 1 ? 'note' : 'notes'}`
  const selectedDirectoryName = selectedDir ? directories.find((dir) => dir.id === selectedDir)?.name || 'Directory' : 'All notes'

  const saveNote = async () => {
    const tags = tagText.split(',').map((tag) => tag.trim()).filter(Boolean)
    const body = JSON.stringify({ text, directory_id: selectedDir, tags })
    setLoading(true)
    setToast(null)
    try {
      if (selectedNote) await api(`/notes/${selectedNote.id}`, { method: 'PUT', token, body })
      else await api('/notes/', { method: 'POST', token, body })
      setSelectedNote(null)
      setText('')
      setTagText('')
      setToast({ tone: 'success', message: 'Saved and queued for indexing.' })
      await load()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Save failed' })
    } finally {
      setLoading(false)
    }
  }

  const deleteNote = async (note: Note) => {
    await api(`/notes/${note.id}`, { method: 'DELETE', token })
    if (selectedNote?.id === note.id) clearDraft()
    await load()
    setToast({ tone: 'success', message: 'Note deleted.' })
  }

  const createDirectory = async () => {
    if (!dirName.trim()) return
    await api('/directories/', { method: 'POST', token, body: JSON.stringify({ name: dirName.trim(), parent_id: selectedDir }) })
    setDirName('')
    await load()
  }

  const editNote = (note: Note) => {
    setSelectedNote(note)
    setText(note.text)
    setTagText(note.tags.map((tag) => tag.name).join(', '))
  }

  const clearDraft = () => {
    setSelectedNote(null)
    setText('')
    setTagText('')
  }

  return (
    <div className="notes-layout">
      <section className="panel directory-panel">
        <PanelTitle icon={Folder} title="Directories" meta={noteCountLabel} />
        <button className={cn('tree-row', selectedDir === null && 'tree-row-active')} onClick={() => setSelectedDir(null)}>
          <Folder size={16} /> All notes
        </button>
        <div className="tree-list">
          {directories.map((dir) => (
            <button key={dir.id} className={cn('tree-row', selectedDir === dir.id && 'tree-row-active')} onClick={() => setSelectedDir(dir.id)}>
              <Folder size={16} /> <span className="truncate">{dir.name}</span>
            </button>
          ))}
        </div>
        <div className="compact-input-row">
          <input className="input" placeholder="New directory" value={dirName} onChange={(event) => setDirName(event.target.value)} />
          <button className="icon-button" onClick={createDirectory} aria-label="Create directory">
            <FolderPlus size={17} />
          </button>
        </div>
      </section>

      <section className="panel editor-panel">
        <PanelTitle icon={FileText} title={selectedNote ? 'Edit note' : 'New note'} meta={selectedDirectoryName} />
        <textarea
          className="textarea note-textarea"
          placeholder="Paste or write source text..."
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <input className="input mt-3" placeholder="tags: decision, research, idea" value={tagText} onChange={(event) => setTagText(event.target.value)} />
        <div className="editor-actions">
          <button className="btn-primary" onClick={saveNote} disabled={loading || !text.trim()}>
            {loading ? <RefreshCw className="animate-spin" size={17} /> : <Save size={17} />}
            {selectedNote ? 'Update note' : 'Create note'}
          </button>
          <button className="btn-secondary" onClick={clearDraft}>New draft</button>
          {toast && <ToastMessage toast={toast} compact />}
        </div>
      </section>

      <section className="panel notes-panel">
        <PanelTitle icon={Layers3} title="Saved notes" meta={selectedDirectoryName} />
        <div className="note-list">
          {notes.map((note) => (
            <article key={note.id} className={cn('note-card', selectedNote?.id === note.id && 'note-card-active')}>
              <button className="note-card-main" onClick={() => editNote(note)}>
                <span className="line-clamp-4">{note.text}</span>
              </button>
              <div className="note-card-footer">
                <div className="flex min-w-0 flex-wrap gap-1.5">
                  {note.tags.map((tag) => <span key={tag.id} className="badge">{tag.name}</span>)}
                </div>
                <button className="icon-button-danger" onClick={() => deleteNote(note)} aria-label="Delete note">
                  <Trash2 size={15} />
                </button>
              </div>
            </article>
          ))}
          {!notes.length && <Empty icon={FileText} label="No notes yet" />}
        </div>
      </section>
    </div>
  )
}

function AskView({ token }: { token: string }) {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [citations, setCitations] = useState<any[]>([])
  const [chunks, setChunks] = useState<any[]>([])
  const [trace, setTrace] = useState<any>(null)
  const [events, setEvents] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)

  const ask = async () => {
    if (!query.trim()) return
    const clientId = crypto.randomUUID()
    const source = new EventSource(`${API_BASE}/api/retrieval/events/${clientId}`)
    source.addEventListener('progress', (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      setEvents((items) => [...items, data.message])
    })
    setLoading(true)
    setToast(null)
    setEvents([])
    try {
      const res = await api<any>('/api/retrieval/query', { method: 'POST', token, body: JSON.stringify({ query, client_id: clientId }) })
      setAnswer(res.answer)
      setCitations(res.citations || [])
      setChunks(res.source_chunks || [])
      setTrace(res.retrieval_trace || null)
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Query failed' })
    } finally {
      setLoading(false)
      source.close()
    }
  }

  return (
    <div className="ask-layout">
      <section className="panel ask-panel">
        <PanelTitle icon={Bot} title="Ask AI" meta="Source-backed" />
        <div className="prompt-box">
          <textarea
            className="textarea prompt-textarea"
            placeholder="Ask about your saved notes..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') void ask()
            }}
          />
          <div className="prompt-actions">
            <span className="text-xs text-slate-500">Cmd/Ctrl + Enter</span>
            <button className="btn-primary" onClick={ask} disabled={loading || !query.trim()}>
              {loading ? <RefreshCw className="animate-spin" size={17} /> : <Search size={17} />} Ask
            </button>
          </div>
        </div>
        {toast && <ToastMessage toast={toast} />}
        <article className="answer-surface">
          <div className="answer-header">
            <div className="answer-icon"><Sparkles size={18} /></div>
            <div>
              <h2>Answer</h2>
              <p>{citations.length ? `${citations.length} sources used` : 'Ready'}</p>
            </div>
          </div>
          {answer ? <p className="answer-text">{answer}</p> : <Empty icon={Bot} label="Ask something to see an answer" />}
        </article>
        {!!citations.length && (
          <div className="source-grid">
            {citations.map((citation, index) => (
              <article key={index} className="source-tile">
                <span className="source-index">Source {index + 1}</span>
                <p>{citation.exact_quote || citation.raw_text || citation.cleaned_text}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel retrieval-panel">
        <PanelTitle icon={Brain} title="Retrieval" meta="Live trace" />
        <InfoBlock title="Progress" items={events} empty="No progress yet" />
        <InfoBlock title="Source chunks" items={chunks.map((chunk) => chunk.summary || chunk.text || chunk.id)} empty="No chunks selected" />
        <details className="trace-box">
          <summary>Trace data</summary>
          <pre>{trace ? JSON.stringify(trace, null, 2) : 'No trace yet.'}</pre>
        </details>
      </section>
    </div>
  )
}

function MemoryView({ token }: { token: string }) {
  const [memory, setMemory] = useState<MemoryItem[]>([])
  const [recall, setRecall] = useState<RecallKey[]>([])
  const [toast, setToast] = useState<Toast | null>(null)

  useEffect(() => {
    Promise.all([
      api<{ data: MemoryItem[] }>('/api/advanced/memory', { token }),
      api<{ data: RecallKey[] }>('/api/advanced/recall', { token }),
    ]).then(([memoryRes, recallRes]) => {
      setMemory(memoryRes.data)
      setRecall(recallRes.data)
    }).catch((err) => setToast({ tone: 'danger', message: err.message }))
  }, [token])

  return (
    <div className="memory-layout">
      <section className="panel">
        <PanelTitle icon={Database} title="Sources" meta={`${memory.length} indexed`} />
        {toast && <ToastMessage toast={toast} />}
        <div className="stack">
          {memory.map((item) => <SourceCard key={item.id} item={item} />)}
          {!memory.length && <Empty icon={Database} label="No indexed sources yet" />}
        </div>
      </section>
      <section className="panel">
        <PanelTitle icon={Brain} title="Recall keys" meta={`${recall.length} keys`} />
        <div className="stack">
          {recall.map((key) => (
            <article key={key.id} className="recall-card">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3>{key.name}</h3>
                  <p>{key.summary}</p>
                </div>
                <span className="badge badge-indigo">{key.kind}</span>
              </div>
              <span className="recall-meta">{key.link_count} evidence links</span>
            </article>
          ))}
          {!recall.length && <Empty icon={Brain} label="No recall keys yet" />}
        </div>
      </section>
    </div>
  )
}

function JobsView({ token }: { token: string }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [toast, setToast] = useState<Toast | null>(null)

  const load = useCallback(() => api<{ data: Job[] }>('/api/advanced/ingest_jobs', { token }).then((res) => setJobs(res.data)), [token])

  useEffect(() => {
    load().catch((err) => setToast({ tone: 'danger', message: err.message }))
  }, [load])

  const action = async (job: Job, type: 'resume' | 'delete') => {
    await api(`/api/advanced/ingest_jobs/${job.id}${type === 'resume' ? '/resume' : ''}`, { method: type === 'resume' ? 'POST' : 'DELETE', token })
    await load()
  }

  return (
    <section className="panel">
      <PanelTitle
        icon={Activity}
        title="Indexing jobs"
        meta={`${jobs.length} jobs`}
        action={<button className="btn-secondary" onClick={() => load()}><RefreshCw size={16} /> Refresh</button>}
      />
      {toast && <ToastMessage toast={toast} />}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr><th>Status</th><th>Stage</th><th>Updated</th><th>Error</th><th aria-label="Actions" /></tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td><StatusBadge status={job.status} /></td>
                <td>{job.stage || 'queued'}</td>
                <td className="muted-cell">{formatDate(job.updated_at || job.created_at)}</td>
                <td className="error-cell">{job.error || ''}</td>
                <td>
                  <div className="row-actions">
                    <button className="icon-button" onClick={() => action(job, 'resume')} aria-label="Resume job"><Play size={15} /></button>
                    <button className="icon-button-danger" onClick={() => action(job, 'delete')} aria-label="Delete job"><Trash2 size={15} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!jobs.length && <Empty icon={Clock3} label="No indexing jobs yet" />}
      </div>
    </section>
  )
}

function SettingsView({ token }: { token: string }) {
  const [presets, setPresets] = useState<Preset[]>([])
  const [draft, setDraft] = useState<PresetDraft>(defaultDraft)
  const [toast, setToast] = useState<Toast | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => api<Preset[]>('/configs/presets', { token }).then(setPresets), [token])

  useEffect(() => {
    load().catch((err) => setToast({ tone: 'danger', message: err.message }))
  }, [load])

  const activePreset = useMemo(() => presets.find((preset) => preset.is_active), [presets])

  const setField = (field: keyof PresetDraft, value: string) => {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  const create = async () => {
    setSaving(true)
    setToast(null)
    try {
      await api('/configs/presets', {
        method: 'POST',
        token,
        body: JSON.stringify({
          name: draft.name,
          llm_provider: draft.llm_provider,
          llm_model: draft.llm_model,
          llm_base_url: emptyToNull(draft.llm_base_url),
          llm_api_key: emptyToNull(draft.llm_api_key),
          llm_temperature: toNumber(draft.llm_temperature, 0),
          llm_max_retries: toNumber(draft.llm_max_retries, 2),
          llm_max_tokens: toNumber(draft.llm_max_tokens, 2048),
          embedding_provider: draft.embedding_provider,
          embedding_model: draft.embedding_model,
          embedding_base_url: emptyToNull(draft.embedding_base_url),
          embedding_api_key: emptyToNull(draft.embedding_api_key),
          chunk_size: toNumber(draft.chunk_size, 1000),
          chunk_overlap: toNumber(draft.chunk_overlap, 200),
        }),
      })
      setToast({ tone: 'success', message: 'Preset created.' })
      await load()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Preset failed' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-layout">
      <section className="panel">
        <PanelTitle icon={Settings} title="AI preset" meta={activePreset ? `Active: ${activePreset.name}` : 'No active preset'} />
        <div className="settings-grid">
          <Field label="Preset name">
            <input className="input" value={draft.name} onChange={(event) => setField('name', event.target.value)} />
          </Field>
          <Field label="Text provider">
            <select className="select" value={draft.llm_provider} onChange={(event) => setField('llm_provider', event.target.value)}>
              <option value="openai">OpenAI-compatible</option>
              <option value="ollama">Ollama</option>
            </select>
          </Field>
          <Field label="Text model">
            <input className="input" value={draft.llm_model} onChange={(event) => setField('llm_model', event.target.value)} placeholder="model name" />
          </Field>
          <Field label="Provider URL">
            <input className="input" value={draft.llm_base_url} onChange={(event) => setField('llm_base_url', event.target.value)} placeholder="https://..." />
          </Field>
          <Field label="API key">
            <input className="input" type="password" value={draft.llm_api_key} onChange={(event) => setField('llm_api_key', event.target.value)} />
          </Field>
          <Field label="Temperature">
            <input className="input" inputMode="decimal" value={draft.llm_temperature} onChange={(event) => setField('llm_temperature', event.target.value)} />
          </Field>
          <Field label="Embedding provider">
            <select className="select" value={draft.embedding_provider} onChange={(event) => setField('embedding_provider', event.target.value)}>
              <option value="openai">OpenAI-compatible</option>
              <option value="ollama">Ollama</option>
            </select>
          </Field>
          <Field label="Embedding model">
            <input className="input" value={draft.embedding_model} onChange={(event) => setField('embedding_model', event.target.value)} placeholder="embedding model" />
          </Field>
          <Field label="Embedding URL">
            <input className="input" value={draft.embedding_base_url} onChange={(event) => setField('embedding_base_url', event.target.value)} placeholder="https://..." />
          </Field>
          <Field label="Embedding API key">
            <input className="input" type="password" value={draft.embedding_api_key} onChange={(event) => setField('embedding_api_key', event.target.value)} />
          </Field>
          <Field label="Max retries">
            <input className="input" inputMode="numeric" value={draft.llm_max_retries} onChange={(event) => setField('llm_max_retries', event.target.value)} />
          </Field>
          <Field label="Max tokens">
            <input className="input" inputMode="numeric" value={draft.llm_max_tokens} onChange={(event) => setField('llm_max_tokens', event.target.value)} />
          </Field>
          <Field label="Chunk size">
            <input className="input" inputMode="numeric" value={draft.chunk_size} onChange={(event) => setField('chunk_size', event.target.value)} />
          </Field>
          <Field label="Chunk overlap">
            <input className="input" inputMode="numeric" value={draft.chunk_overlap} onChange={(event) => setField('chunk_overlap', event.target.value)} />
          </Field>
        </div>
        <div className="editor-actions">
          <button className="btn-primary" onClick={create} disabled={saving || !draft.name || !draft.llm_model || !draft.embedding_model}>
            {saving ? <RefreshCw className="animate-spin" size={17} /> : <Plus size={17} />}
            Create preset
          </button>
          {toast && <ToastMessage toast={toast} compact />}
        </div>
      </section>

      <section className="panel">
        <PanelTitle icon={KeyRound} title="Saved presets" meta={`${presets.length} total`} />
        <div className="stack">
          {presets.map((preset) => (
            <article key={preset.id} className={cn('preset-card', preset.is_active && 'preset-card-active')}>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3>{preset.name}</h3>
                  {preset.is_active ? <span className="badge badge-green">Active</span> : null}
                </div>
                <p>{preset.llm_provider}:{preset.llm_model}</p>
                <p>{preset.embedding_provider}:{preset.embedding_model}</p>
              </div>
              <div className="preset-actions">
                <button className="btn-secondary" onClick={() => api(`/configs/presets/${preset.id}/activate`, { method: 'PUT', token }).then(load)}>
                  <CheckCircle2 size={16} /> Activate
                </button>
                <button className="icon-button-danger" onClick={() => api(`/configs/presets/${preset.id}`, { method: 'DELETE', token }).then(load)} aria-label="Delete preset">
                  <Trash2 size={16} />
                </button>
              </div>
            </article>
          ))}
          {!presets.length && <Empty icon={Settings} label="No presets yet" />}
        </div>
      </section>
    </div>
  )
}

function NavItem({ item, active, onClick }: { item: { label: string; icon: LucideIcon; kicker: string }; active: boolean; onClick: () => void }) {
  return (
    <button className={cn('nav-item', active && 'nav-item-active')} onClick={onClick}>
      <span className="nav-icon"><item.icon size={18} /></span>
      <span className="min-w-0">
        <span className="block truncate">{item.label}</span>
        <span className="nav-kicker">{item.kicker}</span>
      </span>
    </button>
  )
}

function BrandLockup({ variant = 'dark' }: { variant?: 'dark' | 'light' }) {
  return (
    <div className="flex items-center gap-3">
      <BrandMark size="md" />
      <div>
        <div className={cn('text-base font-semibold tracking-tight', variant === 'light' ? 'text-white' : 'text-slate-950')}>UnmessIt.AI</div>
        <div className={cn('text-xs', variant === 'light' ? 'text-slate-400' : 'text-slate-500')}>AI knowledge base</div>
      </div>
    </div>
  )
}

function BrandMark({ size }: { size: 'sm' | 'md' }) {
  return (
    <img
      src="/favicon.svg"
      alt="UnmessIt.AI"
      className={cn(size === 'sm' ? 'size-8' : 'size-10', 'brand-mark')}
    />
  )
}

function PanelTitle({ icon: Icon, title, meta, action }: { icon: LucideIcon; title: string; meta?: string; action?: ReactNode }) {
  return (
    <div className="panel-title">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="panel-icon"><Icon size={17} /></span>
        <div className="min-w-0">
          <h2>{title}</h2>
          {meta ? <p>{meta}</p> : null}
        </div>
      </div>
      {action}
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}

function ToastMessage({ toast, compact = false }: { toast: Toast; compact?: boolean }) {
  return <div className={cn('toast', `toast-${toast.tone || 'neutral'}`, compact && 'toast-compact')}>{toast.message}</div>
}

function Empty({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <div className="empty-state">
      <Icon size={20} />
      <span>{label}</span>
    </div>
  )
}

function InfoBlock({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="info-block">
      <h3>{title}</h3>
      <div className="stack stack-tight">
        {items.length ? items.map((item, idx) => <div key={idx} className="info-row">{item}</div>) : <Empty icon={Clock3} label={empty} />}
      </div>
    </div>
  )
}

function SourceCard({ item }: { item: MemoryItem }) {
  return (
    <details className="source-card">
      <summary>{item.content.slice(0, 140) || item.id}</summary>
      <p>{item.content}</p>
      <div className="stack stack-tight">
        {(item.source_chunks || []).map((chunk) => <div key={chunk.id} className="info-row">{chunk.summary || chunk.text}</div>)}
      </div>
    </details>
  )
}

function StatusPill({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return <span className="status-pill"><Icon size={14} /> {label}</span>
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  return <span className={cn('status-badge', normalized.includes('fail') && 'status-danger', normalized.includes('done') && 'status-success')}>{status}</span>
}

function formatDate(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function emptyToNull(value: string) {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function toNumber(value: string, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export default App
