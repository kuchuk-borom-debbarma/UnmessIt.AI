import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  RotateCw,
  Save,
  Settings,
  Trash2,
  X,
} from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../../lib/api'
import type { Preset, ProcessingSettings, RotationConfig } from '../../lib/api'
import { useConfig } from '../../lib/context/useConfig'
import { cn } from '../../lib/utils'

type RotationDraft = {
  name: string
  llm_provider: string
  llm_model: string
  llm_base_url: string
  llm_api_key: string
  llm_temperature: number
  llm_max_retries: number
  llm_max_tokens: number
  llm_rate_limit_per_minute: number
  embedding_base_url: string
  embedding_api_key: string
  embedding_rate_limit_per_minute: number
}

type Toast = { tone: 'success' | 'danger'; message: string }

const defaultProcessing: ProcessingSettings = {
  embedding_provider: 'openai',
  embedding_model: 'text-embedding-3-small',
  embedding_batch_size: 100,
  chunk_size: 1000,
  chunk_overlap: 200,
  ingest_retry_backoff_seconds: '5,15,30,60,120',
}

const defaultLane: RotationDraft = {
  name: 'New Lane',
  llm_provider: 'openai',
  llm_model: 'gpt-4o',
  llm_base_url: '',
  llm_api_key: '',
  llm_temperature: 0,
  llm_max_retries: 2,
  llm_max_tokens: 2048,
  llm_rate_limit_per_minute: 0,
  embedding_base_url: '',
  embedding_api_key: '',
  embedding_rate_limit_per_minute: 0,
}

function ToastMessage({ toast }: { toast: Toast }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      className={cn(
        'fixed left-1/2 top-24 z-50 -translate-x-1/2 rounded-lg border px-4 py-2 text-sm font-semibold shadow-lg backdrop-blur-md',
        toast.tone === 'success'
          ? 'border-primary-500/20 bg-primary-500/10 text-primary-500'
          : 'border-red-500/20 bg-red-500/10 text-red-500',
      )}
    >
      {toast.message}
    </motion.div>
  )
}

export function SettingsView({ token }: { token: string }) {
  const { checkConfig } = useConfig()
  const [presets, setPresets] = useState<Preset[]>([])
  const [processing, setProcessing] = useState<ProcessingSettings>(defaultProcessing)
  const [rotationEnabled, setRotationEnabled] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [laneDraft, setLaneDraft] = useState<RotationDraft>(defaultLane)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showLoading, setShowLoading] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [])

  const selectedPresets = useMemo(
    () => selectedIds.map((id) => presets.find((preset) => preset.id === id)).filter(Boolean) as Preset[],
    [presets, selectedIds],
  )
  const rotationInvalid = rotationEnabled && selectedIds.length < 2

  const load = useCallback(async () => {
    try {
      const [presetData, processingData, rotationData] = await Promise.all([
        api<Preset[]>('/configs/presets', { token }),
        api<ProcessingSettings>('/configs/processing', { token }),
        api<RotationConfig>('/configs/rotation', { token }),
      ])
      setPresets(presetData)
      setProcessing(processingData)
      setRotationEnabled(rotationData.enabled)
      setSelectedIds(rotationData.preset_ids)
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Settings load failed' })
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void load()
  }, [load])

  const saveProcessing = async () => {
    setToast(null)
    try {
      await api('/configs/processing', { method: 'PUT', token, body: JSON.stringify(processing) })
      setToast({ tone: 'success', message: 'Processing settings saved.' })
      await checkConfig()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Processing save failed' })
    }
  }

  const saveRotation = async () => {
    setToast(null)
    try {
      await api('/configs/rotation', {
        method: 'PUT',
        token,
        body: JSON.stringify({ enabled: rotationEnabled, preset_ids: selectedIds }),
      })
      setToast({ tone: 'success', message: 'Rotation order saved.' })
      await load()
      await checkConfig()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Rotation save failed' })
    }
  }

  const saveLane = async () => {
    setToast(null)
    const payload = {
      ...laneDraft,
      embedding_provider: processing.embedding_provider,
      embedding_model: processing.embedding_model,
      embedding_batch_size: processing.embedding_batch_size,
      chunk_size: processing.chunk_size,
      chunk_overlap: processing.chunk_overlap,
      ingest_retry_backoff_seconds: processing.ingest_retry_backoff_seconds,
    }
    try {
      const endpoint = editingId ? `/configs/presets/${editingId}` : '/configs/presets'
      await api<{ id: string }>(endpoint, {
        method: editingId ? 'PUT' : 'POST',
        token,
        body: JSON.stringify(payload),
      })
      setToast({ tone: 'success', message: editingId ? 'Rotation lane updated.' : 'Rotation lane created.' })
      setLaneDraft(defaultLane)
      setEditingId(null)
      setFormOpen(false)
      await load()
      await checkConfig()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Lane save failed' })
    }
  }

  const editLane = (preset: Preset) => {
    setLaneDraft({
      name: preset.name,
      llm_provider: preset.llm_provider,
      llm_model: preset.llm_model,
      llm_base_url: preset.llm_base_url || '',
      llm_api_key: '',
      llm_temperature: preset.llm_temperature,
      llm_max_retries: preset.llm_max_retries,
      llm_max_tokens: preset.llm_max_tokens,
      llm_rate_limit_per_minute: preset.llm_rate_limit_per_minute,
      embedding_base_url: preset.embedding_base_url || '',
      embedding_api_key: '',
      embedding_rate_limit_per_minute: preset.embedding_rate_limit_per_minute,
    })
    setEditingId(preset.id)
    setFormOpen(true)
  }

  const moveSelected = (id: string, delta: -1 | 1) => {
    setSelectedIds((ids) => {
      const index = ids.indexOf(id)
      const nextIndex = index + delta
      if (index < 0 || nextIndex < 0 || nextIndex >= ids.length) return ids
      const next = [...ids]
      const [item] = next.splice(index, 1)
      next.splice(nextIndex, 0, item)
      return next
    })
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
    <div className="mx-auto flex h-full w-full max-w-6xl flex-1 flex-col gap-8 px-4 pb-32 pt-8 md:px-0">
      <AnimatePresence>{toast && <ToastMessage toast={toast} />}</AnimatePresence>

      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="mb-2 text-4xl font-extrabold tracking-tight">AI Configuration</h1>
          <p className="font-medium text-muted-foreground">Processing stays fixed; rotation lanes fail over per job or query.</p>
        </div>
        <button
          className="premium-btn premium-btn-primary h-12 gap-2 px-5"
          onClick={() => {
            setLaneDraft(defaultLane)
            setEditingId(null)
            setFormOpen(true)
          }}
        >
          <Plus size={18} /> Add Lane
        </button>
      </header>

      <section className="bento-card p-6 md:p-8">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-bold">Processing</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">Stable chunking and embedding settings. Rotation never changes these mid-job.</p>
          </div>
          <button className="premium-btn premium-btn-secondary h-11 gap-2 px-4" onClick={saveProcessing}>
            <Save size={17} /> Save
          </button>
        </div>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          <Field label="Embedding model">
            <input className="premium-input bg-transparent" value={processing.embedding_model} onChange={(e) => setProcessing({ ...processing, embedding_model: e.target.value })} />
          </Field>
          <Field label="Embedding batch size">
            <input type="number" className="premium-input bg-transparent" value={processing.embedding_batch_size} onChange={(e) => setProcessing({ ...processing, embedding_batch_size: Number(e.target.value) || 100 })} />
          </Field>
          <Field label="Retry backoff seconds">
            <input className="premium-input bg-transparent" value={processing.ingest_retry_backoff_seconds} onChange={(e) => setProcessing({ ...processing, ingest_retry_backoff_seconds: e.target.value })} />
          </Field>
          <Field label="Chunk size">
            <input type="number" className="premium-input bg-transparent" value={processing.chunk_size} onChange={(e) => setProcessing({ ...processing, chunk_size: Number(e.target.value) || 1000 })} />
          </Field>
          <Field label="Chunk overlap">
            <input type="number" className="premium-input bg-transparent" value={processing.chunk_overlap} onChange={(e) => setProcessing({ ...processing, chunk_overlap: Number(e.target.value) || 0 })} />
          </Field>
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
            <div className="mb-1 flex items-center gap-2 font-bold text-amber-300">
              <AlertTriangle size={16} /> Hard rule
            </div>
            Rotation lanes only change API access and rate limits. Chunking, embedding model, and batch size are fixed for the whole job.
          </div>
        </div>
      </section>

      <section className="bento-card p-6 md:p-8">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-bold"><RotateCw size={22} /> Rotation</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">Each job/query starts at lane 1. If it fails, the next lane is tried. No last-good pointer is saved.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex h-11 cursor-pointer items-center gap-3 rounded-lg border border-border bg-input px-4 text-sm font-bold">
              <input type="checkbox" checked={rotationEnabled} onChange={(e) => setRotationEnabled(e.target.checked)} />
              Enable rotation
            </label>
            <button className="premium-btn premium-btn-primary h-11 gap-2 px-4 disabled:cursor-not-allowed disabled:opacity-50" disabled={rotationInvalid} onClick={saveRotation}>
              <Save size={17} /> Save order
            </button>
          </div>
        </div>

        {rotationInvalid && (
          <div className="mb-5 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm font-semibold text-red-300">
            Rotation needs at least two selected lanes.
          </div>
        )}

        {selectedPresets.length > 0 && (
          <div className="mb-6">
            <div className="mb-3 text-xs font-bold uppercase tracking-widest text-muted-foreground">Current rotation order</div>
            <div className="space-y-2">
              {selectedPresets.map((preset, index) => (
                <div key={preset.id} className="flex items-center gap-3 rounded-lg border border-border/60 bg-input/40 p-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-500/15 text-sm font-black text-primary-400">{index + 1}</div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-bold">{preset.name}</div>
                    <div className="truncate text-xs font-mono text-muted-foreground">{preset.llm_model}{preset.llm_rate_limit_per_minute > 0 ? ` · ${preset.llm_rate_limit_per_minute} LLM RPM` : ''}</div>
                  </div>
                  <button className="icon-btn" onClick={() => moveSelected(preset.id, -1)} aria-label="Move lane up"><ArrowUp size={17} /></button>
                  <button className="icon-btn" onClick={() => moveSelected(preset.id, 1)} aria-label="Move lane down"><ArrowDown size={17} /></button>
                  <button className="icon-btn text-red-400 hover:bg-red-500/10" onClick={() => setSelectedIds((ids) => ids.filter((id) => id !== preset.id))} aria-label="Remove lane from rotation"><X size={17} /></button>
                </div>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {formOpen && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mb-6 overflow-hidden">
              <div className="rounded-lg border border-border/70 bg-background/30 p-5">
                <div className="mb-5 flex items-center justify-between">
                  <h3 className="text-xl font-bold">{editingId ? 'Edit rotation lane' : 'New rotation lane'}</h3>
                  <button className="icon-btn" onClick={() => setFormOpen(false)} aria-label="Close lane form"><X size={18} /></button>
                </div>
                <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                  <Field label="Lane name"><input className="premium-input bg-transparent" value={laneDraft.name} onChange={(e) => setLaneDraft({ ...laneDraft, name: e.target.value })} /></Field>
                  <Field label="LLM model"><input className="premium-input bg-transparent" value={laneDraft.llm_model} onChange={(e) => setLaneDraft({ ...laneDraft, llm_model: e.target.value })} /></Field>
                  <Field label="LLM API key">
                    <SecretInput value={laneDraft.llm_api_key} placeholder={editingId ? 'Leave blank to keep existing key' : 'sk-...'} onChange={(value) => setLaneDraft({ ...laneDraft, llm_api_key: value })} />
                  </Field>
                  <Field label="Embedding API key">
                    <SecretInput value={laneDraft.embedding_api_key} placeholder={editingId ? 'Leave blank to keep existing key' : 'sk-...'} onChange={(value) => setLaneDraft({ ...laneDraft, embedding_api_key: value })} />
                  </Field>
                  <Field label="LLM base URL"><input className="premium-input bg-transparent" value={laneDraft.llm_base_url} onChange={(e) => setLaneDraft({ ...laneDraft, llm_base_url: e.target.value })} placeholder="https://api.openai.com/v1" /></Field>
                  <Field label="Embedding base URL"><input className="premium-input bg-transparent" value={laneDraft.embedding_base_url} onChange={(e) => setLaneDraft({ ...laneDraft, embedding_base_url: e.target.value })} placeholder="https://api.openai.com/v1" /></Field>
                  <Field label="LLM rate limit"><input type="number" className="premium-input bg-transparent" value={laneDraft.llm_rate_limit_per_minute} onChange={(e) => setLaneDraft({ ...laneDraft, llm_rate_limit_per_minute: Number(e.target.value) || 0 })} /></Field>
                  <Field label="Embedding rate limit"><input type="number" className="premium-input bg-transparent" value={laneDraft.embedding_rate_limit_per_minute} onChange={(e) => setLaneDraft({ ...laneDraft, embedding_rate_limit_per_minute: Number(e.target.value) || 0 })} /></Field>
                  <Field label="Max tokens"><input type="number" className="premium-input bg-transparent" value={laneDraft.llm_max_tokens} onChange={(e) => setLaneDraft({ ...laneDraft, llm_max_tokens: Number(e.target.value) || 2048 })} /></Field>
                  <Field label="Max retries"><input type="number" className="premium-input bg-transparent" value={laneDraft.llm_max_retries} onChange={(e) => setLaneDraft({ ...laneDraft, llm_max_retries: Number(e.target.value) || 0 })} /></Field>
                </div>
                <div className="mt-6 flex justify-end gap-3">
                  <button className="premium-btn premium-btn-secondary h-11 px-5" onClick={() => setFormOpen(false)}>Cancel</button>
                  <button className="premium-btn premium-btn-primary h-11 gap-2 px-5" onClick={saveLane}><Save size={17} /> Save lane</button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-1 gap-4">
          {presets.map((preset) => {
            const selected = selectedIds.includes(preset.id)
            return (
              <motion.div key={preset.id} layout className={cn('flex flex-col gap-4 rounded-lg border p-4 transition-colors md:flex-row md:items-center', selected ? 'border-primary-500/50 bg-primary-500/5' : 'border-border/60 bg-input/30')}>
                <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-4">
                  <input className="mt-1" type="checkbox" checked={selected} onChange={(e) => setSelectedIds((ids) => e.target.checked ? [...ids, preset.id] : ids.filter((id) => id !== preset.id))} />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="truncate text-lg font-bold">{preset.name}</h3>
                      {preset.is_active === 1 && <span className="rounded-full bg-primary-500/15 px-2 py-0.5 text-xs font-bold text-primary-400">Default</span>}
                      {selected && <span className="rounded-full bg-accent-500/15 px-2 py-0.5 text-xs font-bold text-accent-400">In rotation</span>}
                    </div>
                    <div className="mt-1 text-xs font-mono text-muted-foreground">
                      {preset.llm_model} · embedding API lane{preset.embedding_rate_limit_per_minute > 0 ? ` · ${preset.embedding_rate_limit_per_minute} embedding RPM` : ''}
                    </div>
                  </div>
                </label>
                <div className="flex items-center gap-2">
                  {preset.is_active !== 1 && (
                    <button className="icon-btn text-primary-400" onClick={() => api(`/configs/presets/${preset.id}/activate`, { method: 'PUT', token }).then(load).then(checkConfig)} aria-label="Set default lane">
                      <CheckCircle2 size={18} />
                    </button>
                  )}
                  <button className="icon-btn text-amber-400" onClick={() => editLane(preset)} aria-label="Edit lane"><Pencil size={18} /></button>
                  <button
                    className="icon-btn text-red-400 hover:bg-red-500/10"
                    onClick={() => {
                      if (confirm('Delete rotation lane?')) {
                        void api(`/configs/presets/${preset.id}`, { method: 'DELETE', token }).then(load).then(checkConfig)
                      }
                    }}
                    aria-label="Delete lane"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </motion.div>
            )
          })}
        </div>

        {presets.length === 0 && !formOpen && (
          <div className="py-16 text-center text-muted-foreground">
            <Settings className="mx-auto mb-4 opacity-50" size={44} />
            <p>No rotation lanes configured. Add one to start using AI features.</p>
          </div>
        )}
      </section>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-foreground/80">{label}</span>
      {children}
    </label>
  )
}

function SecretInput({ value, placeholder, onChange }: { value: string; placeholder: string; onChange: (value: string) => void }) {
  return (
    <div className="relative">
      <KeyRound className="absolute left-3 top-3.5 text-muted-foreground" size={16} />
      <input type="password" className="premium-input bg-transparent pl-10" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  )
}
