import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  AlertTriangle,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Settings,
  Trash2,
  X,
  Info,
  Activity,
} from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../../lib/api'
import type { EmbeddingConfig, LLMConfig, ProcessingSettings, StageConfig, StageRoute } from '../../lib/api'
import { useConfig } from '../../lib/context/useConfig'
import { cn } from '../../lib/utils'
import { useVersionCheck } from '../../lib/useVersionCheck'

type Toast = { tone: 'success' | 'danger'; message: string }
type SplitKind = 'llm' | 'embedding'
type LlmDraft = Omit<LLMConfig, 'id'> & { llm_api_key: string }
type EmbeddingDraft = Omit<EmbeddingConfig, 'id'> & { embedding_api_key: string }

const defaultProcessing: ProcessingSettings = {
  embedding_batch_size: 100,
  chunk_size: 1000,
  chunk_overlap: 200,
  ingest_retry_backoff_seconds: '5,15,30,60,120',
}

const defaultStageConfig: StageConfig = {
  llm: {},
  embedding: {},
  llm_configs: [],
  embedding_configs: [],
}

const defaultLlmDraft: LlmDraft = {
  name: 'OpenAI answers',
  llm_provider: 'openai',
  llm_model: 'gpt-4o',
  llm_base_url: '',
  llm_api_key: '',
  llm_temperature: 0,
  llm_max_retries: 2,
  llm_max_tokens: undefined,
  llm_rate_limit_per_minute: 0,
}

const defaultEmbeddingDraft: EmbeddingDraft = {
  name: 'OpenAI embeddings',
  embedding_provider: 'openai',
  embedding_model: 'text-embedding-3-small',
  embedding_base_url: '',
  embedding_api_key: '',
  embedding_rate_limit_per_minute: 0,
  embedding_batch_size: 100,
}

const LLM_STAGE_LABELS: Record<string, string> = {
  'ingest.source_chunk_draft': 'Ingest source summaries',
  'ingest.recall_draft': 'Ingest recall extraction',
  'retrieval.query_breakdown': 'Query breakdown',
  'retrieval.subject_extraction': 'Subject extraction',
  'retrieval.verifier': 'Verifier',
  'retrieval.answer': 'Answer',
}

const EMBEDDING_STAGE_LABELS: Record<string, string> = {
  'ingest.source_chunk_vectors': 'Source chunk indexing',
  'ingest.recall_key_vectors': 'Recall key indexing',
  'retrieval.vector_search': 'Retrieval vector search',
  'retrieval.semantic_cache': 'Semantic caches',
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
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([])
  const [embeddingConfigs, setEmbeddingConfigs] = useState<EmbeddingConfig[]>([])
  const [stageConfig, setStageConfig] = useState<StageConfig>(defaultStageConfig)
  const [isPinging, setIsPinging] = useState(false)
  const [processing, setProcessing] = useState<ProcessingSettings>(defaultProcessing)
  const [llmDraft, setLlmDraft] = useState<LlmDraft>(defaultLlmDraft)
  const [embeddingDraft, setEmbeddingDraft] = useState<EmbeddingDraft>(defaultEmbeddingDraft)
  const [splitEditing, setSplitEditing] = useState<{ kind: SplitKind; id: string | null } | null>(null)
  const [splitModalOpen, setSplitModalOpen] = useState<SplitKind | null>(null)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showLoading, setShowLoading] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)
  const { currentVersion } = useVersionCheck()

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [])

  const load = useCallback(async () => {
    try {
      const [processingData, llmData, embeddingData, stageData] = await Promise.all([
        api<ProcessingSettings>('/api/v1/configs/processing', { token }),
        api<LLMConfig[]>('/api/v1/configs/llm', { token }),
        api<EmbeddingConfig[]>('/api/v1/configs/embedding', { token }),
        api<StageConfig>('/api/v1/configs/stages', { token }),
      ])
      setProcessing(processingData)
      setLlmConfigs(llmData)
      setEmbeddingConfigs(embeddingData)
      setStageConfig(stageData)
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Settings load failed' })
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void load()
  }, [load])

  const openNewSplitConfig = (kind: SplitKind) => {
    setSplitEditing({ kind, id: null })
    if (kind === 'llm') setLlmDraft(defaultLlmDraft)
    else setEmbeddingDraft(defaultEmbeddingDraft)
    setSplitModalOpen(kind)
  }

  const openEditSplitConfig = (kind: SplitKind, config: LLMConfig | EmbeddingConfig) => {
    setSplitEditing({ kind, id: config.id })
    if (kind === 'llm') {
      const llm = config as LLMConfig
      setLlmDraft({ ...llm, llm_base_url: llm.llm_base_url || '', llm_api_key: '' })
    } else {
      const embedding = config as EmbeddingConfig
      setEmbeddingDraft({ ...embedding, embedding_base_url: embedding.embedding_base_url || '', embedding_api_key: '' })
    }
    setSplitModalOpen(kind)
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

  const saveSplitConfig = async () => {
    if (!splitModalOpen) return
    setToast(null)
    const editing = splitEditing?.id
    const path = splitModalOpen === 'llm' ? '/api/v1/configs/llm' : '/api/v1/configs/embedding'
    const payload = splitModalOpen === 'llm' ? llmPayload(llmDraft) : embeddingPayload(embeddingDraft)
    try {
      await api<{ id: string }>(editing ? `${path}/${editing}` : path, {
        method: editing ? 'PUT' : 'POST',
        token,
        body: JSON.stringify(payload),
      })
      setToast({ tone: 'success', message: splitModalOpen === 'llm' ? 'LLM config saved.' : 'Embedding config saved.' })
      setSplitModalOpen(null)
      setSplitEditing(null)
      await load()
      await checkConfig()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Config save failed' })
    }
  }

  const pingConfig = async () => {
    if (!splitModalOpen || isPinging) return
    setIsPinging(true)
    setToast(null)
    const editing = splitEditing?.id
    const payload = splitModalOpen === 'llm' ? llmPayload(llmDraft) : embeddingPayload(embeddingDraft)
    try {
      await api('/api/v1/configs/test', {
        method: 'POST',
        token,
        body: JSON.stringify({
          kind: splitModalOpen,
          config: payload,
          config_id: editing || undefined,
        }),
      })
      setToast({ tone: 'success', message: 'API ping successful!' })
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'API ping failed' })
    } finally {
      setIsPinging(false)
    }
  }

  const deleteSplitConfig = async (kind: SplitKind, id: string) => {
    if (!confirm(`Delete ${kind} config?`)) return
    try {
      await api(`/api/v1/configs/${kind}/${id}`, { method: 'DELETE', token })
      await load()
      await checkConfig()
      setToast({ tone: 'success', message: 'Config deleted.' })
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Config delete failed' })
    }
  }

  const saveStage = async (stage: string, route: StageRoute) => {
    try {
      await api(`/api/v1/configs/stages/${stage}`, {
        method: 'PUT',
        token,
        body: JSON.stringify(route),
      })
      await load()
      setToast({ tone: 'success', message: 'Stage routing saved.' })
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Stage routing save failed' })
    }
  }

  const applyToAllLlmStages = async () => {
    const stages = Object.keys(LLM_STAGE_LABELS)
    if (stages.length < 2) return
    const firstStage = stages[0]
    const sourceRoute = stageConfig.llm[firstStage] || { stage: firstStage, kind: 'llm', enabled: false, config_ids: [], active_config_id: llmConfigs[0]?.id }
    
    try {
      await Promise.all(stages.slice(1).map(stage => {
        const newRoute = { ...sourceRoute, stage }
        return api(`/api/v1/configs/stages/${stage}`, {
          method: 'PUT',
          token,
          body: JSON.stringify(newRoute),
        })
      }))
      await load()
      setToast({ tone: 'success', message: 'Applied to all LLM stages.' })
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Apply to all failed' })
    }
  }

  const applyToAllEmbeddingStages = async () => {
    const stages = Object.keys(EMBEDDING_STAGE_LABELS)
    if (stages.length < 2) return
    const firstStage = stages[0]
    const sourceRoute = stageConfig.embedding[firstStage] || { stage: firstStage, kind: 'embedding', enabled: false, config_ids: [], active_config_id: embeddingConfigs[0]?.id }
    
    try {
      await Promise.all(stages.slice(1).map(stage => {
        const newRoute = { ...sourceRoute, stage }
        return api(`/api/v1/configs/stages/${stage}`, {
          method: 'PUT',
          token,
          body: JSON.stringify(newRoute),
        })
      }))
      await load()
      setToast({ tone: 'success', message: 'Applied to all Embedding stages.' })
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Apply to all failed' })
    }
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
    <div className="app-page max-w-6xl">
      <AnimatePresence>{toast && <ToastMessage toast={toast} />}</AnimatePresence>

      <section className="page-hero">
        <div className="page-hero-inner">
          <div className="page-hero-copy">
            <div className="page-hero-icon">
              <Settings size={24} />
            </div>
            <div>
              <p className="page-hero-kicker">AI Settings</p>
              <h1 className="page-hero-title">Tune models without losing reliability.</h1>
              <p className="page-hero-subtitle">
                Configure separate models and rate limits for LLMs vs Embeddings. Route different stages of your pipeline to different configurations or fallbacks.
              </p>
            </div>
          </div>
        </div>
        <div className="page-stat-grid">
          <div className="page-stat-card">
            <span>LLM Configs</span>
            <strong>{llmConfigs.length}</strong>
            <small>saved LLM setups</small>
          </div>
          <div className="page-stat-card">
            <span>Embedding Configs</span>
            <strong>{embeddingConfigs.length}</strong>
            <small>saved embedding setups</small>
          </div>
          <div className="page-stat-card">
            <span>Version</span>
            <strong>{currentVersion}</strong>
            <small>current local build</small>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <SplitConfigList
          kind="llm"
          title="LLM Configs"
          configs={llmConfigs}
          modelOf={(config) => (config as LLMConfig).llm_model}
          onNew={() => openNewSplitConfig('llm')}
          onEdit={(config) => openEditSplitConfig('llm', config)}
          onDelete={(id) => void deleteSplitConfig('llm', id)}
        />
        <SplitConfigList
          kind="embedding"
          title="Embedding Configs"
          configs={embeddingConfigs}
          modelOf={(config) => (config as EmbeddingConfig).embedding_model}
          onNew={() => openNewSplitConfig('embedding')}
          onEdit={(config) => openEditSplitConfig('embedding', config)}
          onDelete={(id) => void deleteSplitConfig('embedding', id)}
        />
      </section>

      <section className="bento-card p-6 md:p-8">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Stage Routing</h2>
          </div>
        </div>
        <StageRouting
          title="LLM stages"
          labels={LLM_STAGE_LABELS}
          routes={stageConfig.llm}
          configs={llmConfigs}
          modelOf={(config) => config.llm_model}
          onSave={(stage, route) => void saveStage(stage, route)}
          onApplyToAll={applyToAllLlmStages}
        />
        <div className="mt-6">
          <StageRouting
            title="Embedding stages"
            labels={EMBEDDING_STAGE_LABELS}
            routes={stageConfig.embedding}
            configs={embeddingConfigs}
            modelOf={(config) => config.embedding_model}
            onSave={(stage, route) => void saveStage(stage, route)}
            onApplyToAll={applyToAllEmbeddingStages}
          />
        </div>
      </section>

      <section className="bento-card p-6 md:p-8">
        <button className="flex w-full items-center justify-between text-left" onClick={() => setAdvancedOpen((value) => !value)}>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Advanced Processing</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">Usually safe to leave alone. These settings do not rotate mid-job.</p>
          </div>
          <span className="text-sm font-bold text-primary-600 dark:text-primary-400">{advancedOpen ? 'Hide' : 'Show'}</span>
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
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-800 dark:text-amber-200 lg:col-span-3">
              <div className="mb-1 flex items-center gap-2 font-bold text-amber-700 dark:text-amber-300">
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
        {splitModalOpen && (
          <SplitConfigModal
            kind={splitModalOpen}
            editing={Boolean(splitEditing?.id)}
            llmDraft={llmDraft}
            embeddingDraft={embeddingDraft}
            onLlmChange={setLlmDraft}
            onEmbeddingChange={setEmbeddingDraft}
            onClose={() => setSplitModalOpen(null)}
            onSave={saveSplitConfig}
            onPing={pingConfig}
            isPinging={isPinging}
          />
        )}
      </AnimatePresence>
      
      <div className="mt-8 flex items-center justify-center gap-2 text-center text-sm font-medium text-muted-foreground/60">
        <Info size={14} /> UnmessIt.AI Version {currentVersion}
      </div>
    </div>
  )
}

function SplitConfigList<T extends LLMConfig | EmbeddingConfig>({
  title,
  configs,
  modelOf,
  onNew,
  onEdit,
  onDelete,
}: {
  kind: SplitKind
  title: string
  configs: T[]
  modelOf: (config: T) => string
  onNew: () => void
  onEdit: (config: T) => void
  onDelete: (id: string) => void
}) {
  return (
    <section className="bento-card p-6 md:p-8">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-foreground">{title}</h2>
          <p className="mt-1 text-sm font-medium text-muted-foreground">Named configs used by stage routing.</p>
        </div>
        <button className="premium-btn premium-btn-secondary h-10 gap-2 px-3" onClick={onNew}>
          <Plus size={16} /> New
        </button>
      </div>
      <div className="space-y-3">
        {configs.map((config) => (
          <div key={config.id} className="flex items-center gap-3 rounded-lg border border-border/60 bg-card/35 p-3">
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-bold text-foreground">{config.name}</div>
              <div className="truncate font-mono text-xs text-muted-foreground">{modelOf(config)}</div>
            </div>
            <button className="icon-btn text-amber-400" onClick={() => onEdit(config)} aria-label="Edit config"><Pencil size={16} /></button>
            <button className="icon-btn text-red-400 hover:bg-red-500/10" onClick={() => onDelete(config.id)} aria-label="Delete config"><Trash2 size={16} /></button>
          </div>
        ))}
        {configs.length === 0 && <div className="rounded-lg border border-border/60 p-6 text-center text-sm text-muted-foreground">No configs yet.</div>}
      </div>
    </section>
  )
}

function StageRouting<T extends LLMConfig | EmbeddingConfig>({
  title,
  labels,
  routes,
  configs,
  modelOf,
  onSave,
  onApplyToAll,
}: {
  title: string
  labels: Record<string, string>
  routes: Record<string, StageRoute>
  configs: T[]
  modelOf: (config: T) => string
  onSave: (stage: string, route: StageRoute) => void
  onApplyToAll?: () => void
}) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-extrabold uppercase tracking-[0.14em] text-muted-foreground">{title}</h3>
        {onApplyToAll && (
          <button className="text-xs font-bold text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300" onClick={onApplyToAll}>
            Apply to All
          </button>
        )}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {Object.entries(labels).map(([stage, label]) => {
          const route = routes[stage] || { stage, kind: title.startsWith('LLM') ? 'llm' : 'embedding', enabled: false, config_ids: [], active_config_id: configs[0]?.id }
          return (
            <div key={stage} className="rounded-lg border border-border/60 bg-card/30 p-3">
              <div className="mb-3">
                <div className="text-sm font-bold text-foreground">{label}</div>
                <div className="font-mono text-[11px] text-muted-foreground">{stage}</div>
              </div>
              <div className="grid gap-2">
                <select
                  className="premium-input bg-transparent"
                  value={route.enabled ? 'rotation' : 'single'}
                  onChange={(event) => onSave(stage, { ...route, enabled: event.target.value === 'rotation' })}
                >
                  <option value="single">Single config</option>
                  <option value="rotation">Fallback rotation</option>
                </select>
                {!route.enabled ? (
                  <select
                    className="premium-input bg-transparent"
                    value={route.active_config_id || ''}
                    onChange={(event) => onSave(stage, { ...route, enabled: false, active_config_id: event.target.value })}
                  >
                    {configs.map((config) => <option key={config.id} value={config.id}>{config.name} - {modelOf(config)}</option>)}
                  </select>
                ) : (
                  <div className="space-y-2">
                    {configs.map((config) => {
                      const checked = route.config_ids.includes(config.id)
                      return (
                        <label key={config.id} className="flex items-center gap-2 rounded-md border border-border/50 px-3 py-2 text-xs font-semibold text-muted-foreground">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(event) => {
                              const config_ids = event.target.checked
                                ? [...route.config_ids, config.id].filter((value, index, self) => self.indexOf(value) === index)
                                : route.config_ids.filter((id) => id !== config.id)
                              onSave(stage, { ...route, enabled: true, config_ids })
                            }}
                          />
                          {config.name} <span className="font-mono opacity-70">{modelOf(config)}</span>
                        </label>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SplitConfigModal({
  kind,
  editing,
  llmDraft,
  embeddingDraft,
  onLlmChange,
  onEmbeddingChange,
  onClose,
  onSave,
  onPing,
  isPinging,
}: {
  kind: SplitKind
  editing: boolean
  llmDraft: LlmDraft
  embeddingDraft: EmbeddingDraft
  onLlmChange: (draft: LlmDraft) => void
  onEmbeddingChange: (draft: EmbeddingDraft) => void
  onClose: () => void
  onSave: () => void
  onPing: () => void
  isPinging: boolean
}) {
  const isLlm = kind === 'llm'
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
        aria-label={editing ? `Edit ${kind} config` : `Create ${kind} config`}
        className="w-full max-w-2xl rounded-lg border border-border bg-card p-6 shadow-2xl md:p-8"
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 18, scale: 0.98 }}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">{editing ? 'Edit' : 'Create'} {isLlm ? 'LLM' : 'Embedding'} Config</h2>
            <p className="mt-1 text-sm font-medium text-muted-foreground">Named config for stage routing and fallback rotation.</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close modal"><X size={18} /></button>
        </div>

        {isLlm ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Name"><input className="premium-input bg-transparent" value={llmDraft.name} onChange={(e) => onLlmChange({ ...llmDraft, name: e.target.value })} /></Field>
            <Field label="Model"><input className="premium-input bg-transparent" value={llmDraft.llm_model} onChange={(e) => onLlmChange({ ...llmDraft, llm_model: e.target.value })} /></Field>
            <Field label="API key"><SecretInput value={llmDraft.llm_api_key} placeholder={editing ? 'Leave blank to keep existing key' : 'sk-...'} onChange={(value) => onLlmChange({ ...llmDraft, llm_api_key: value })} /></Field>
            <Field label="Base URL"><input className="premium-input bg-transparent" value={llmDraft.llm_base_url || ''} onChange={(e) => onLlmChange({ ...llmDraft, llm_base_url: e.target.value })} /></Field>
            <Field label="Temperature"><input type="number" step="0.1" className="premium-input bg-transparent" value={llmDraft.llm_temperature} onChange={(e) => onLlmChange({ ...llmDraft, llm_temperature: Number(e.target.value) || 0 })} /></Field>
            <Field label="Rate limit"><input type="number" className="premium-input bg-transparent" value={llmDraft.llm_rate_limit_per_minute} onChange={(e) => onLlmChange({ ...llmDraft, llm_rate_limit_per_minute: Number(e.target.value) || 0 })} /></Field>
            <Field label="Max tokens"><input type="number" className="premium-input bg-transparent" value={llmDraft.llm_max_tokens ?? ''} onChange={(e) => onLlmChange({ ...llmDraft, llm_max_tokens: e.target.value ? Number(e.target.value) : undefined })} placeholder="Default" /></Field>
            <Field label="Max retries"><input type="number" className="premium-input bg-transparent" value={llmDraft.llm_max_retries} onChange={(e) => onLlmChange({ ...llmDraft, llm_max_retries: Number(e.target.value) || 0 })} /></Field>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Name"><input className="premium-input bg-transparent" value={embeddingDraft.name} onChange={(e) => onEmbeddingChange({ ...embeddingDraft, name: e.target.value })} /></Field>
            <Field label="Model"><input className="premium-input bg-transparent" value={embeddingDraft.embedding_model} onChange={(e) => onEmbeddingChange({ ...embeddingDraft, embedding_model: e.target.value })} /></Field>
            <Field label="API key"><SecretInput value={embeddingDraft.embedding_api_key} placeholder={editing ? 'Leave blank to keep existing key' : 'sk-...'} onChange={(value) => onEmbeddingChange({ ...embeddingDraft, embedding_api_key: value })} /></Field>
            <Field label="Base URL"><input className="premium-input bg-transparent" value={embeddingDraft.embedding_base_url || ''} onChange={(e) => onEmbeddingChange({ ...embeddingDraft, embedding_base_url: e.target.value })} /></Field>
            <Field label="Batch size"><input type="number" className="premium-input bg-transparent" value={embeddingDraft.embedding_batch_size} onChange={(e) => onEmbeddingChange({ ...embeddingDraft, embedding_batch_size: Number(e.target.value) || 100 })} /></Field>
            <Field label="Rate limit"><input type="number" className="premium-input bg-transparent" value={embeddingDraft.embedding_rate_limit_per_minute} onChange={(e) => onEmbeddingChange({ ...embeddingDraft, embedding_rate_limit_per_minute: Number(e.target.value) || 0 })} /></Field>
          </div>
        )}

        <div className="mt-8 flex justify-end gap-3 border-t border-border/60 pt-5">
          <button className="premium-btn premium-btn-secondary h-11 px-5" onClick={onClose} disabled={isPinging}>Cancel</button>
          <button 
            className="premium-btn premium-btn-secondary h-11 gap-2 px-5 disabled:opacity-50" 
            onClick={onPing} 
            disabled={isPinging}
          >
            {isPinging ? <RefreshCw className="animate-spin" size={16} /> : <Activity size={16} />}
            {isPinging ? 'Pinging...' : 'Ping API'}
          </button>
          <button className="premium-btn premium-btn-primary h-11 gap-2 px-5" onClick={onSave} disabled={isPinging}>
            <Save size={17} /> Save Config
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

function Field({ label, helpText, children }: { label: string; helpText?: string; children: ReactNode }) {
  return (
    <label className="relative block">
      <span className="mb-1.5 flex items-center text-xs font-bold uppercase tracking-wider text-foreground/80">
        {label}
        {helpText && (
          <div className="group relative ml-1.5 flex items-center">
            <Info className="shrink-0 text-muted-foreground/70 hover:text-foreground" size={14} />
            <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-md bg-zinc-800 p-2.5 text-xs font-medium normal-case leading-relaxed tracking-normal text-zinc-200 opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
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

function llmPayload(draft: LlmDraft) {
  return {
    ...draft,
    llm_base_url: draft.llm_base_url || null,
    llm_api_key: draft.llm_api_key || null,
    llm_max_tokens: draft.llm_max_tokens || null,
  }
}

function embeddingPayload(draft: EmbeddingDraft) {
  return {
    ...draft,
    embedding_base_url: draft.embedding_base_url || null,
    embedding_api_key: draft.embedding_api_key || null,
  }
}
