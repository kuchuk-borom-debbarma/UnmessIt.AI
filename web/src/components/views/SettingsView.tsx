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
  Info,
} from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../../lib/api'
import type { Preset, ProcessingSettings, RotationConfig } from '../../lib/api'
import { useConfig } from '../../lib/context/useConfig'
import { cn } from '../../lib/utils'
import { useVersionCheck } from '../../lib/useVersionCheck'

type ConfigDraft = {
  name: string
  llm_provider: string
  llm_model: string
  llm_base_url: string
  llm_api_key: string
  llm_temperature: number
  llm_max_retries: number
  llm_max_tokens?: number | null
  llm_rate_limit_per_minute: number
  embedding_provider: string
  embedding_model: string
  embedding_base_url: string
  embedding_api_key: string
  embedding_rate_limit_per_minute: number
}

type Toast = { tone: 'success' | 'danger'; message: string }

const defaultProcessing: ProcessingSettings = {
  embedding_batch_size: 100,
  chunk_size: 1000,
  chunk_overlap: 200,
  ingest_retry_backoff_seconds: '5,15,30,60,120',
}

const defaultConfig: ConfigDraft = {
  name: 'OpenAI',
  llm_provider: 'openai',
  llm_model: 'gpt-4o',
  llm_base_url: '',
  llm_api_key: '',
  llm_temperature: 0,
  llm_max_retries: 2,
  llm_max_tokens: undefined,
  llm_rate_limit_per_minute: 0,
  embedding_provider: 'openai',
  embedding_model: 'text-embedding-3-small',
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
  const [draft, setDraft] = useState<ConfigDraft>(defaultConfig)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showLoading, setShowLoading] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)
  const { currentVersion } = useVersionCheck()

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [])

  const activePreset = presets.find((preset) => preset.is_active === 1)
  const selectedPresets = useMemo(
    () => selectedIds.map((id) => presets.find((preset) => preset.id === id)).filter(Boolean) as Preset[],
    [presets, selectedIds],
  )
  const rotationInvalid = rotationEnabled && selectedIds.length < 2

  const load = useCallback(async () => {
    try {
      const [presetData, processingData, rotationData] = await Promise.all([
        api<Preset[]>('/api/v1/configs/presets', { token }),
        api<ProcessingSettings>('/api/v1/configs/processing', { token }),
        api<RotationConfig>('/api/v1/configs/rotation', { token }),
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

  const openNewConfig = () => {
    setDraft(defaultConfig)
    setEditingId(null)
    setModalOpen(true)
  }

  const openEditConfig = (preset: Preset) => {
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
    })
    setEditingId(preset.id)
    setModalOpen(true)
  }

  const saveConfig = async () => {
    setToast(null)
    const payload = {
      ...draft,
      embedding_batch_size: processing.embedding_batch_size,
      chunk_size: processing.chunk_size,
      chunk_overlap: processing.chunk_overlap,
      ingest_retry_backoff_seconds: processing.ingest_retry_backoff_seconds,
    }
    try {
      await api<{ id: string }>(editingId ? `/api/v1/configs/presets/${editingId}` : '/api/v1/configs/presets', {
        method: editingId ? 'PUT' : 'POST',
        token,
        body: JSON.stringify(payload),
      })
      setToast({ tone: 'success', message: editingId ? 'Config updated.' : 'Config created.' })
      setModalOpen(false)
      setEditingId(null)
      await load()
      await checkConfig()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Config save failed' })
    }
  }

  const setActive = async (presetId: string) => {
    await api(`/api/v1/configs/presets/${presetId}/activate`, { method: 'PUT', token })
    setRotationEnabled(false)
    await api('/api/v1/configs/rotation', { method: 'PUT', token, body: JSON.stringify({ enabled: false, preset_ids: selectedIds }) })
    await load()
    await checkConfig()
  }

  const saveRotation = async () => {
    setToast(null)
    try {
      await api('/api/v1/configs/rotation', {
        method: 'PUT',
        token,
        body: JSON.stringify({ enabled: rotationEnabled, preset_ids: selectedIds }),
      })
      setToast({ tone: 'success', message: rotationEnabled ? 'Rotation enabled.' : 'Rotation disabled.' })
      await load()
      await checkConfig()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Rotation save failed' })
    }
  }

  const saveProcessing = async () => {
    setToast(null)
    try {
      await api('/api/v1/configs/processing', { method: 'PUT', token, body: JSON.stringify(processing) })
      setToast({ tone: 'success', message: 'Processing settings saved.' })
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Processing save failed' })
    }
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
          <h1 className="mb-2 text-4xl font-extrabold tracking-tight">AI Settings</h1>
          <p className="max-w-2xl font-medium text-muted-foreground">
            Start with one config preset. Rotation is optional and only helps when you want automatic fallback.
          </p>
        </div>
        <button className="premium-btn premium-btn-primary h-12 gap-2 px-5" onClick={openNewConfig}>
          <Plus size={18} /> Create New Config
        </button>
      </header>

      <section className="bento-card p-6 md:p-8">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground">How AI Should Run</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">
              Use one specific config for normal use. Turn on rotation only when you have multiple fallback configs.
            </p>
          </div>
          <ModeBadge rotationEnabled={rotationEnabled} activePreset={activePreset} />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <button
            className={cn(
              'rounded-lg border p-5 text-left transition-colors',
              !rotationEnabled ? 'border-primary-500/60 bg-primary-500/10' : 'border-border bg-input/40 hover:bg-input',
            )}
            onClick={() => setRotationEnabled(false)}
          >
            <div className="mb-2 flex items-center gap-2 text-lg font-bold text-foreground">
              <CheckCircle2 size={20} /> Use One Config
            </div>
            <p className="text-sm leading-6 text-muted-foreground">
              Best for most people. Pick one config and UnmessIt will use it for LLM and embedding calls.
            </p>
            <div className="mt-4 text-sm font-bold text-foreground">
              Current: {activePreset?.name || 'No config selected'}
            </div>
          </button>

          <button
            className={cn(
              'rounded-lg border p-5 text-left transition-colors',
              rotationEnabled ? 'border-primary-500/60 bg-primary-500/10' : 'border-border bg-input/40 hover:bg-input',
            )}
            onClick={() => setRotationEnabled(true)}
          >
            <div className="mb-2 flex items-center gap-2 text-lg font-bold text-foreground">
              <RotateCw size={20} /> Use Rotation
            </div>
            <p className="text-sm leading-6 text-muted-foreground">
              Optional. Choose two or more configs. If the first fails during a job/query, the next one is tried.
            </p>
            <div className="mt-4 text-sm font-bold text-foreground">
              Selected: {selectedIds.length} config{selectedIds.length === 1 ? '' : 's'}
            </div>
          </button>
        </div>

        <div className="mt-5 flex justify-end">
          <button className="premium-btn premium-btn-primary h-11 gap-2 px-4 disabled:cursor-not-allowed disabled:opacity-50" disabled={rotationInvalid} onClick={saveRotation}>
            <Save size={17} /> Save Mode
          </button>
        </div>

        {rotationInvalid && (
          <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm font-semibold text-red-300">
            Rotation needs at least two selected configs. Choose more configs below or switch back to one config.
          </div>
        )}
      </section>

      <section className="bento-card p-6 md:p-8">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Config Presets</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">
              A config stores model names, API keys, base URLs, and rate limits. Embedding model lives here too.
            </p>
          </div>
          <button className="premium-btn premium-btn-secondary h-11 gap-2 px-4" onClick={openNewConfig}>
            <Plus size={17} /> New Config
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {presets.map((preset) => {
            const selected = selectedIds.includes(preset.id)
            return (
              <motion.div
                key={preset.id}
                layout
                className={cn(
                  'rounded-lg border p-4 transition-colors',
                  preset.is_active === 1 && !rotationEnabled ? 'border-primary-500/60 bg-primary-500/10' : 'border-border/60 bg-input/30',
                )}
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center">
                  <label className="flex min-w-0 flex-1 items-start gap-4">
                    <input
                      className="mt-1"
                      type="checkbox"
                      checked={selected}
                      onChange={(e) => setSelectedIds((ids) => e.target.checked ? [...ids, preset.id] : ids.filter((id) => id !== preset.id))}
                      aria-label={`Use ${preset.name} in rotation`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="truncate text-lg font-bold text-foreground">{preset.name}</h3>
                        {preset.is_active === 1 && <span className="rounded-full bg-primary-500/15 px-2 py-0.5 text-xs font-bold text-primary-400">Specific config</span>}
                        {selected && <span className="rounded-full bg-accent-500/15 px-2 py-0.5 text-xs font-bold text-accent-400">Rotation</span>}
                      </div>
                      <div className="mt-1 text-xs font-mono text-muted-foreground">
                        LLM {preset.llm_model} · Embedding {preset.embedding_model}
                      </div>
                    </div>
                  </label>

                  <div className="flex flex-wrap items-center gap-2">
                    <button className="premium-btn premium-btn-secondary h-10 px-3" onClick={() => void setActive(preset.id)}>
                      Use this
                    </button>
                    <button className="icon-btn text-amber-400" onClick={() => openEditConfig(preset)} aria-label="Edit config">
                      <Pencil size={18} />
                    </button>
                    <button
                      className="icon-btn text-red-400 hover:bg-red-500/10"
                      onClick={() => {
                        if (confirm('Delete config preset?')) void api(`/api/v1/configs/presets/${preset.id}`, { method: 'DELETE', token }).then(load).then(checkConfig)
                      }}
                      aria-label="Delete config"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {presets.length === 0 && (
          <div className="py-16 text-center text-muted-foreground">
            <Settings className="mx-auto mb-4 opacity-50" size={44} />
            <p>No config presets yet. Create one to start using AI features.</p>
          </div>
        )}
      </section>

      {rotationEnabled && selectedPresets.length > 0 && (
        <section className="bento-card p-6 md:p-8">
          <h2 className="mb-1 flex items-center gap-2 text-2xl font-bold text-foreground">
            <RotateCw size={22} /> Rotation Order
          </h2>
          <p className="mb-5 text-sm font-medium text-muted-foreground">
            Each job/query starts at 1. If that config fails, the next one is tried. This order is not a queue and no last-good state is saved.
          </p>
          <div className="space-y-2">
            {selectedPresets.map((preset, index) => (
              <div key={preset.id} className="flex items-center gap-3 rounded-lg border border-border/60 bg-input/40 p-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-500/15 text-sm font-black text-primary-400">{index + 1}</div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-bold">{preset.name}</div>
                  <div className="truncate text-xs font-mono text-muted-foreground">{preset.llm_model} · {preset.embedding_model}</div>
                </div>
                <button className="icon-btn" onClick={() => moveSelected(preset.id, -1)} aria-label="Move config up"><ArrowUp size={17} /></button>
                <button className="icon-btn" onClick={() => moveSelected(preset.id, 1)} aria-label="Move config down"><ArrowDown size={17} /></button>
                <button className="icon-btn text-red-400 hover:bg-red-500/10" onClick={() => setSelectedIds((ids) => ids.filter((id) => id !== preset.id))} aria-label="Remove config from rotation"><X size={17} /></button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="bento-card p-6 md:p-8">
        <button className="flex w-full items-center justify-between text-left" onClick={() => setAdvancedOpen((value) => !value)}>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Advanced Processing</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">Usually safe to leave alone. These settings do not rotate mid-job.</p>
          </div>
          <span className="text-sm font-bold text-primary-400">{advancedOpen ? 'Hide' : 'Show'}</span>
        </button>

        {advancedOpen && (
          <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
            <Field label="Embedding batch size" helpText="Number of documents embedded at once. High: faster ingestion but risks rate limits/OOM. Low: safer but slower.">
              <input type="number" className="premium-input bg-transparent" value={processing.embedding_batch_size} onChange={(e) => setProcessing({ ...processing, embedding_batch_size: Number(e.target.value) || 100 })} />
            </Field>
            <Field label="Chunk size" helpText="Characters per text chunk. High: retains more context but might dilute specific facts. Low: more precise retrieval but risks losing context.">
              <input type="number" className="premium-input bg-transparent" value={processing.chunk_size} onChange={(e) => setProcessing({ ...processing, chunk_size: Number(e.target.value) || 1000 })} />
            </Field>
            <Field label="Chunk overlap" helpText="Characters overlapping between chunks. High: prevents cutting off sentences but increases token usage. Low: saves tokens but risks missing context at boundaries.">
              <input type="number" className="premium-input bg-transparent" value={processing.chunk_overlap} onChange={(e) => setProcessing({ ...processing, chunk_overlap: Number(e.target.value) || 0 })} />
            </Field>
            <Field label="Retry backoff" helpText="Comma-separated seconds to wait between retries. High: better for strict rate limits. Low: faster recovery for transient errors.">
              <input className="premium-input bg-transparent" value={processing.ingest_retry_backoff_seconds} onChange={(e) => setProcessing({ ...processing, ingest_retry_backoff_seconds: e.target.value })} />
            </Field>
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200 lg:col-span-3">
              <div className="mb-1 flex items-center gap-2 font-bold text-amber-300">
                <AlertTriangle size={16} /> Fixed during a job
              </div>
              Chunking, batch size, and retry backoff are job settings. Config presets can change LLM and embedding models; these processing knobs stay stable.
            </div>
            <div className="flex items-end">
              <button className="premium-btn premium-btn-secondary h-11 w-full gap-2 px-4" onClick={saveProcessing}>
                <Save size={17} /> Save Advanced
              </button>
            </div>
          </div>
        )}
      </section>

      <AnimatePresence>
        {modalOpen && (
          <ConfigModal
            draft={draft}
            editing={Boolean(editingId)}
            onClose={() => setModalOpen(false)}
            onSave={saveConfig}
            onChange={setDraft}
          />
        )}
      </AnimatePresence>
      
      <div className="mt-8 text-center text-sm font-medium text-muted-foreground/60 flex items-center justify-center gap-2">
        <Info size={14} /> UnmessIt.AI Version {currentVersion}
      </div>
    </div>
  )
}

function ModeBadge({ rotationEnabled, activePreset }: { rotationEnabled: boolean; activePreset?: Preset }) {
  return (
    <div className="rounded-lg border border-border bg-input px-4 py-3 text-sm font-semibold text-muted-foreground">
      {rotationEnabled ? 'Rotation mode' : `Specific config: ${activePreset?.name || 'none'}`}
    </div>
  )
}

function ConfigModal({
  draft,
  editing,
  onClose,
  onSave,
  onChange,
}: {
  draft: ConfigDraft
  editing: boolean
  onClose: () => void
  onSave: () => void
  onChange: (draft: ConfigDraft) => void
}) {
  return (
    <motion.div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-background/80 p-4 backdrop-blur-md"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label={editing ? 'Edit config preset' : 'Create config preset'}
        className="max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-border bg-card p-6 shadow-2xl md:p-8"
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 18, scale: 0.98 }}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">{editing ? 'Edit Config' : 'Create New Config'}</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">
              Save one complete model setup. You can use it directly or include it in rotation later.
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close modal"><X size={18} /></button>
        </div>

        <div className="space-y-6">
          <Field label="Config name">
            <input className="premium-input bg-transparent" value={draft.name} onChange={(e) => onChange({ ...draft, name: e.target.value })} placeholder="OpenAI production" />
          </Field>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <section className="rounded-lg border border-border/70 bg-input/25 p-4">
              <h3 className="mb-4 font-bold">Answer Model</h3>
              <div className="space-y-4">
                <Field label="LLM model">
                  <input className="premium-input bg-transparent" value={draft.llm_model} onChange={(e) => onChange({ ...draft, llm_model: e.target.value })} placeholder="gpt-4o" />
                </Field>
                <Field label="LLM API key">
                  <SecretInput value={draft.llm_api_key} placeholder={editing ? 'Leave blank to keep existing key' : 'sk-...'} onChange={(value) => onChange({ ...draft, llm_api_key: value })} />
                </Field>
                <Field label="LLM base URL">
                  <input className="premium-input bg-transparent" value={draft.llm_base_url} onChange={(e) => onChange({ ...draft, llm_base_url: e.target.value })} placeholder="https://api.openai.com/v1" />
                </Field>
                <Field label="LLM rate limit" helpText="Max requests per minute. 0 means unlimited.">
                  <input type="number" className="premium-input bg-transparent" value={draft.llm_rate_limit_per_minute} onChange={(e) => onChange({ ...draft, llm_rate_limit_per_minute: Number(e.target.value) || 0 })} />
                </Field>
              </div>
            </section>

            <section className="rounded-lg border border-border/70 bg-input/25 p-4">
              <h3 className="mb-4 font-bold">Embedding Model</h3>
              <div className="space-y-4">
                <Field label="Embedding model">
                  <input className="premium-input bg-transparent" value={draft.embedding_model} onChange={(e) => onChange({ ...draft, embedding_model: e.target.value })} placeholder="text-embedding-3-small" />
                </Field>
                <Field label="Embedding API key">
                  <SecretInput value={draft.embedding_api_key} placeholder={editing ? 'Leave blank to keep existing key' : 'sk-...'} onChange={(value) => onChange({ ...draft, embedding_api_key: value })} />
                </Field>
                <Field label="Embedding base URL">
                  <input className="premium-input bg-transparent" value={draft.embedding_base_url} onChange={(e) => onChange({ ...draft, embedding_base_url: e.target.value })} placeholder="https://api.openai.com/v1" />
                </Field>
                <Field label="Embedding rate limit" helpText="Max requests per minute. 0 means unlimited.">
                  <input type="number" className="premium-input bg-transparent" value={draft.embedding_rate_limit_per_minute} onChange={(e) => onChange({ ...draft, embedding_rate_limit_per_minute: Number(e.target.value) || 0 })} />
                </Field>
              </div>
            </section>
          </div>

          <details className="rounded-lg border border-border/70 bg-input/20 p-4">
            <summary className="cursor-pointer text-sm font-bold text-muted-foreground">Advanced answer options</summary>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              <Field label="Max tokens" helpText="Limits response length. Low: truncates answers. High (or empty): uses full model capability.">
                <input type="number" className="premium-input bg-transparent" value={draft.llm_max_tokens ?? ''} onChange={(e) => onChange({ ...draft, llm_max_tokens: e.target.value ? Number(e.target.value) : undefined })} placeholder="Default" />
              </Field>
              <Field label="Max retries" helpText="Number of times to retry on transient API errors.">
                <input type="number" className="premium-input bg-transparent" value={draft.llm_max_retries} onChange={(e) => onChange({ ...draft, llm_max_retries: Number(e.target.value) || 0 })} />
              </Field>
              <Field label="Temperature" helpText="Controls randomness. 0.0 is deterministic and focused, 1.0 is creative.">
                <input type="number" step="0.1" className="premium-input bg-transparent" value={draft.llm_temperature} onChange={(e) => onChange({ ...draft, llm_temperature: Number(e.target.value) || 0 })} />
              </Field>
            </div>
          </details>
        </div>

        <div className="mt-8 flex justify-end gap-3 border-t border-border/60 pt-5">
          <button className="premium-btn premium-btn-secondary h-11 px-5" onClick={onClose}>Cancel</button>
          <button className="premium-btn premium-btn-primary h-11 gap-2 px-5" onClick={onSave}>
            <Save size={17} /> Save Config
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

function Field({ label, helpText, children }: { label: string; helpText?: string; children: ReactNode }) {
  return (
    <label className="block relative">
      <span className="mb-1.5 flex items-center text-xs font-bold uppercase tracking-wider text-foreground/80">
        {label}
        {helpText && (
          <div className="group relative ml-1.5 flex items-center">
            <Info className="shrink-0 text-muted-foreground/70 hover:text-foreground" size={14} />
            <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 w-64 -translate-x-1/2 rounded-md bg-zinc-800 p-2.5 text-xs font-medium normal-case tracking-normal text-zinc-200 opacity-0 shadow-xl transition-opacity group-hover:opacity-100 z-50 leading-relaxed">
              {helpText}
              <div className="absolute left-1/2 top-full -mt-1.5 h-3 w-3 -translate-x-1/2 rotate-45 bg-zinc-800"></div>
            </div>
          </div>
        )}
      </span>
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
