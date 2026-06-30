import { useCallback, useEffect, useState } from 'react'
import { Settings, Plus, KeyRound, CheckCircle2, Trash2, RefreshCw, Pencil } from 'lucide-react'
import { api } from '../../lib/api'
import type { Preset } from '../../lib/api'
import { cn } from '../../lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { useConfig } from '../../lib/context/useConfig'

type PresetDraft = {
  name: string
  llm_provider: string
  llm_model: string
  llm_base_url: string
  llm_api_key: string
  llm_temperature: number
  llm_max_retries: number
  llm_max_tokens: number
  llm_rate_limit_per_minute: number
  embedding_provider: string
  embedding_model: string
  embedding_base_url: string
  embedding_api_key: string
  embedding_rate_limit_per_minute: number
  embedding_batch_size: number
  chunk_size: number
  chunk_overlap: number
  ingest_retry_backoff_seconds: string
}

const defaultDraft: PresetDraft = {
  name: 'New Preset',
  llm_provider: 'openai',
  llm_model: 'gpt-4o',
  llm_base_url: '',
  llm_api_key: '',
  llm_temperature: 0.0,
  llm_max_retries: 2,
  llm_max_tokens: 2048,
  llm_rate_limit_per_minute: 0,
  embedding_provider: 'openai',
  embedding_model: 'text-embedding-3-small',
  embedding_base_url: '',
  embedding_api_key: '',
  embedding_rate_limit_per_minute: 0,
  embedding_batch_size: 100,
  chunk_size: 1000,
  chunk_overlap: 200,
  ingest_retry_backoff_seconds: '5,15,30,60,120',
}

type Toast = { tone: 'success' | 'danger'; message: string }

function ToastMessage({ toast }: { toast: Toast }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn(
        "fixed top-24 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-xl text-sm font-semibold shadow-lg backdrop-blur-md border",
        toast.tone === 'success' 
          ? "bg-primary-500/10 text-primary-500 border-primary-500/20" 
          : "bg-red-500/10 text-red-500 border-red-500/20"
      )}
    >
      {toast.message}
    </motion.div>
  )
}



export function SettingsView({ token }: { token: string }) {
  const { checkConfig } = useConfig()
  const [presets, setPresets] = useState<Preset[]>([])
  const [draft, setDraft] = useState<PresetDraft>(defaultDraft)
  const [toast, setToast] = useState<Toast | null>(null)
  const [loading, setLoading] = useState(true)
  const [showLoading, setShowLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [])
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await api<Preset[]>('/configs/presets', { token })
      setPresets(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    load()
  }, [load])

  const handleSave = async () => {
    setToast(null)
    try {
      const endpoint = editingId ? `/configs/presets/${editingId}` : '/configs/presets'
      const method = editingId ? 'PUT' : 'POST'
      
      await api(endpoint, {
        method,
        token,
        body: JSON.stringify(draft)
      })
      setToast({ tone: 'success', message: editingId ? 'Preset updated.' : 'Preset created.' })
      setDraft(defaultDraft)
      setIsFormOpen(false)
      setEditingId(null)
      await load()
      void checkConfig()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Preset save failed' })
    }
  }

  const handleEdit = (preset: Preset) => {
    setDraft({
      name: preset.name,
      llm_provider: preset.llm_provider,
      llm_model: preset.llm_model,
      llm_base_url: preset.llm_base_url || '',
      llm_api_key: '',
      llm_temperature: preset.llm_temperature,
      llm_max_retries: preset.llm_max_retries,
      llm_max_tokens: preset.llm_max_tokens,
      llm_rate_limit_per_minute: preset.llm_rate_limit_per_minute,
      embedding_provider: preset.embedding_provider,
      embedding_model: preset.embedding_model,
      embedding_base_url: preset.embedding_base_url || '',
      embedding_api_key: '',
      embedding_rate_limit_per_minute: preset.embedding_rate_limit_per_minute,
      embedding_batch_size: preset.embedding_batch_size || 100,
      chunk_size: preset.chunk_size,
      chunk_overlap: preset.chunk_overlap,
      ingest_retry_backoff_seconds: preset.ingest_retry_backoff_seconds || defaultDraft.ingest_retry_backoff_seconds,
    })
    setEditingId(preset.id)
    setIsFormOpen(true)
  }



  if (loading) {
    if (!showLoading) return null
    return (
      <div className="flex flex-1 items-center justify-center">
        <RefreshCw className="animate-spin text-primary-500" size={32} />
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 h-full max-w-5xl mx-auto w-full pt-8 pb-32">
      <AnimatePresence>
        {toast && <ToastMessage toast={toast} />}
      </AnimatePresence>

      <div className="flex items-end justify-between mb-12">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2">AI Configuration</h1>
          <p className="text-muted-foreground font-medium">Manage language models and embedding providers.</p>
        </div>
        {!isFormOpen && (
          <button 
            className="premium-btn premium-btn-primary h-12 px-6 gap-2"
            onClick={() => {
              setDraft(defaultDraft)
              setEditingId(null)
              setIsFormOpen(true)
            }}
          >
            <Plus size={18} /> Add Preset
          </button>
        )}
      </div>

      <AnimatePresence>
        {isFormOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -20, height: 0 }}
            className="mb-12 overflow-hidden"
          >
            <div className="bento-card p-6 md:p-8">
              <h2 className="text-2xl font-bold mb-8">{editingId ? 'Edit Configuration' : 'New Configuration'}</h2>
              
              <div className="space-y-8">
                {/* General */}
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-widest text-primary-500 mb-4">General</h3>
                  <div className="max-w-md">
                    <label className="block text-xs font-bold mb-1 text-foreground/90">Preset Name</label>
                    <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">A memorable name for this configuration.</p>
                    <input className="premium-input" value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} placeholder="e.g. OpenAI production" />
                  </div>
                </div>

                {/* LLM */}
                <div className="pt-8 border-t border-border/50 grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div>
                    <h3 className="text-sm font-bold uppercase tracking-widest text-accent-500 mb-4">Language Model</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Provider</label>
                        <select className="premium-input bg-transparent" value={draft.llm_provider} onChange={e => setDraft({ ...draft, llm_provider: e.target.value })}>
                          <option value="openai">OpenAI</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Model Name</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Specific identifier used by the provider (e.g. gpt-4o).</p>
                        <input className="premium-input bg-transparent" value={draft.llm_model} onChange={e => setDraft({ ...draft, llm_model: e.target.value })} placeholder="gpt-4o" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">API Key</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Secret token to authenticate with the provider.</p>
                        <div className="relative">
                          <KeyRound className="absolute left-3 top-3.5 text-muted-foreground" size={16} />
                          <input type="password" className="premium-input bg-transparent pl-10" value={draft.llm_api_key} onChange={e => setDraft({ ...draft, llm_api_key: e.target.value })} placeholder={editingId ? "Leave blank to keep existing key" : "sk-..."} />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Base URL (Optional)</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Override if using a local proxy or custom gateway.</p>
                        <input className="premium-input bg-transparent" value={draft.llm_base_url} onChange={e => setDraft({ ...draft, llm_base_url: e.target.value })} placeholder="https://api.openai.com/v1" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Rate Limit (RPM)</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Max requests per minute. Set to 0 for unlimited.</p>
                        <input type="number" className="premium-input bg-transparent" value={draft.llm_rate_limit_per_minute} onChange={e => setDraft({ ...draft, llm_rate_limit_per_minute: parseInt(e.target.value) || 0 })} placeholder="0" />
                      </div>
                    </div>
                  </div>

                  {/* Embedding */}
                  <div>
                    <h3 className="text-sm font-bold uppercase tracking-widest text-primary-500 mb-4">Embedding Model</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Provider</label>
                        <select className="premium-input bg-transparent" value={draft.embedding_provider} onChange={e => setDraft({ ...draft, embedding_provider: e.target.value })}>
                          <option value="openai">OpenAI</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Model Name</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Model used for vectorizing text.</p>
                        <input className="premium-input bg-transparent" value={draft.embedding_model} onChange={e => setDraft({ ...draft, embedding_model: e.target.value })} placeholder="text-embedding-3-small" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">API Key</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Secret token to authenticate with the provider.</p>
                        <div className="relative">
                          <KeyRound className="absolute left-3 top-3.5 text-muted-foreground" size={16} />
                          <input type="password" className="premium-input bg-transparent pl-10" value={draft.embedding_api_key} onChange={e => setDraft({ ...draft, embedding_api_key: e.target.value })} placeholder={editingId ? "Leave blank to keep existing key" : "sk-..."} />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Base URL (Optional)</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Override if using a local proxy.</p>
                        <input className="premium-input bg-transparent" value={draft.embedding_base_url} onChange={e => setDraft({ ...draft, embedding_base_url: e.target.value })} placeholder="https://api.openai.com/v1" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Rate Limit (RPM)</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Max requests per minute. Set to 0 for unlimited.</p>
                        <input type="number" className="premium-input bg-transparent" value={draft.embedding_rate_limit_per_minute} onChange={e => setDraft({ ...draft, embedding_rate_limit_per_minute: parseInt(e.target.value) || 0 })} placeholder="0" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Batch Size</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Number of vectors to embed per API call.</p>
                        <input type="number" className="premium-input bg-transparent" value={draft.embedding_batch_size} onChange={e => setDraft({ ...draft, embedding_batch_size: parseInt(e.target.value) || 100 })} placeholder="100" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Chunking */}
                <div className="pt-8 border-t border-border/50 grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div>
                    <h3 className="text-sm font-bold uppercase tracking-widest text-primary-500 mb-4">Document Chunking</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Chunk Size (Characters)</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">
                          <strong>Pros:</strong> Large chunks preserve flow. Small chunks retrieve sharper facts.<br/>
                          <strong>Cons:</strong> Large chunks eat context window and dilute LLM attention. Small chunks cause fragmentation (partially offset by recall links).
                        </p>
                        <input type="number" className="premium-input bg-transparent" value={draft.chunk_size} onChange={e => setDraft({ ...draft, chunk_size: parseInt(e.target.value) || 1000 })} placeholder="1000" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Chunk Overlap (Characters)</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">
                          <strong>Pros:</strong> High overlap maintains continuity and context so facts aren't split.<br/>
                          <strong>Cons:</strong> High overlap increases storage cost and token redundancy.
                        </p>
                        <input type="number" className="premium-input bg-transparent" value={draft.chunk_overlap} onChange={e => setDraft({ ...draft, chunk_overlap: parseInt(e.target.value) || 200 })} placeholder="200" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold mb-1 text-foreground/90">Retry Backoff (Seconds)</label>
                        <p className="text-[11px] leading-relaxed text-muted-foreground mb-2.5">Comma-separated ingest retry delays after provider or indexing failures.</p>
                        <input className="premium-input bg-transparent" value={draft.ingest_retry_backoff_seconds} onChange={e => setDraft({ ...draft, ingest_retry_backoff_seconds: e.target.value })} placeholder="5,15,30,60,120" />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="pt-8 border-t border-border/50 flex justify-end gap-3">
                  <button className="premium-btn premium-btn-secondary h-12 px-6" onClick={() => { setIsFormOpen(false); setEditingId(null); }}>Cancel</button>
                  <button className="premium-btn premium-btn-primary h-12 px-8" onClick={handleSave}>Save Configuration</button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 gap-6">
        {presets.map((preset) => (
          <motion.div 
            key={preset.id} 
            layout
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn(
              "bento-card p-6 md:p-8 flex flex-col md:flex-row gap-6 justify-between transition-all duration-500",
              preset.is_active ? "border-primary-500/50 shadow-[0_0_40px_rgba(20,184,166,0.15)] ring-1 ring-primary-500/20" : ""
            )}
          >
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-2xl font-bold">{preset.name}</h3>
                {preset.is_active && (
                  <span className="px-3 py-1 rounded-full bg-primary-500/20 text-primary-500 text-xs font-bold tracking-wider uppercase flex items-center gap-1.5">
                    <CheckCircle2 size={14} /> Active
                  </span>
                )}
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
                <div className="p-4 rounded-lg bg-input border border-border/50">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">Language</div>
                  <div className="font-semibold text-foreground/90">{preset.llm_provider}</div>
                  <div className="text-xs text-muted-foreground mt-0.5 font-mono">{preset.llm_model} {preset.llm_rate_limit_per_minute > 0 ? `(${preset.llm_rate_limit_per_minute} RPM)` : ''}</div>
                </div>
                <div className="p-4 rounded-lg bg-input border border-border/50">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">Embedding</div>
                  <div className="font-semibold text-foreground/90">{preset.embedding_provider}</div>
                  <div className="text-xs text-muted-foreground mt-0.5 font-mono">{preset.embedding_model} {preset.embedding_rate_limit_per_minute > 0 ? `(${preset.embedding_rate_limit_per_minute} RPM)` : ''}</div>
                </div>
                <div className="p-4 rounded-lg bg-input border border-border/50 sm:col-span-2">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">Chunking</div>
                  <div className="text-sm font-semibold text-foreground/90">{preset.chunk_size} chars &middot; {preset.chunk_overlap} overlap &middot; retry {preset.ingest_retry_backoff_seconds || defaultDraft.ingest_retry_backoff_seconds}s</div>
                </div>
              </div>
            </div>

            <div className="flex md:flex-col items-center justify-end gap-3 pt-4 border-t border-border/50 md:pt-0 md:border-t-0 md:border-l md:pl-6">
              {!preset.is_active && (
                <button 
                  className="premium-btn premium-btn-primary h-12 px-6 w-full md:w-auto" 
                  onClick={() => api(`/configs/presets/${preset.id}/activate`, { method: 'PUT', token }).then(load).then(checkConfig)}
                >
                  <CheckCircle2 className="mr-2" size={18} /> Set Active
                </button>
              )}
              <div className="flex items-center gap-2">
                <button 
                  className={cn(
                    "flex items-center justify-center rounded-lg transition-colors",
                    "w-12 h-12 bg-input text-muted-foreground hover:bg-amber-500/10 hover:text-amber-500"
                  )}
                  onClick={() => handleEdit(preset)} 
                  aria-label="Edit preset"
                >
                  <Pencil size={20} />
                </button>
                <button 
                  className={cn(
                    "flex items-center justify-center rounded-lg transition-colors",
                    preset.is_active ? "w-12 h-12 bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white" : "w-12 h-12 bg-input text-muted-foreground hover:bg-red-500/10 hover:text-red-500"
                  )}
                  onClick={() => {
                    if(confirm('Delete preset?')) api(`/configs/presets/${preset.id}`, { method: 'DELETE', token }).then(load).then(checkConfig)
                  }} 
                  aria-label="Delete preset"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            </div>
          </motion.div>
        ))}

        {presets.length === 0 && !isFormOpen && (
          <div className="text-center py-20 text-muted-foreground">
            <Settings className="mx-auto mb-4 opacity-50" size={48} />
            <p>No presets configured. Add one to get started.</p>
          </div>
        )}
      </div>
    </div>
  )
}
