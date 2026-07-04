import { RefreshCw, ChevronRight, ChevronDown, ChevronUp, ExternalLink, Terminal, SlidersHorizontal, Square, Zap, Database, Cpu, Clock, CheckCircle, Gauge, Timer, Layers, TrendingDown, GitBranch } from 'lucide-react'
import { cn } from '../../lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { DirectorySearchSelect } from './DirectorySearchSelect'
import { TagSearchSelect } from './TagSearchSelect'
import { useAsk } from '../../contexts/useAsk'
import type { ProgressStep } from '../../contexts/AskContextCore'
import { useEffect, useRef, memo, useState } from 'react'

type Toast = { tone: 'success' | 'danger'; message: string }
type Citation = {
  source_chunk_id: string
  source_input_id: string
  exact_quote?: string
  raw_text?: string
  cleaned_text?: string
  start_char?: number | null
  end_char?: number | null
}
type ContextEngineering = {
  ran?: boolean
  raw_chars?: number
  packed_chars?: number
  saved_chars?: number
  shrink_percent?: number
}
type FlowStep = {
  id: string
  title: string
  subtitle?: string
  type: 'llm' | 'cache' | 'process'
  status: 'hit' | 'miss' | 'skip' | 'skipped' | 'completed' | 'error'
  duration_ms?: number
  model_used?: string
  metrics?: { calls?: number; prompt_tokens?: number; completion_tokens?: number; total_tokens?: number; duration_ms?: number; model_used?: string }
  details?: Record<string, any>
  badges?: string[]
  children?: FlowStep[]
}
type TraceSummaryItem = {
  id: string
  label: string
  value: string
  detail?: string
  tone?: 'success' | 'warning' | 'danger' | 'neutral'
}
type RetrievalTraceUi = {
  summary?: TraceSummaryItem[]
  flow?: FlowStep[]
  savings?: Record<string, any>
}

type RetrievalTraceLike = {
  context_engineering?: ContextEngineering
  context_chars_before_packing?: number
  context_chars_after_packing?: number
  llm_saved_metrics?: {
    llm_calls: number
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  cache_summary?: Record<string, string>
  mode?: string
  source_chunk_count?: number
  citation_count?: number
  sub_queries?: string[]
  extracted_subjects?: string[]
  flow_steps?: FlowStep[]
  ui?: RetrievalTraceUi
}

// We don't use CITE_MARKER_RE and CITE_MARKER_ONLY_RE anymore with ReactMarkdown,
// but keep them in case they're needed elsewhere or just remove them to fix TS errors.
// Actually, let's just remove them.
const STRAY_CITE_MARKER_RE = /\[\[cite:[^\]\s]+(?:\]\])?/g
function contextShrinkPercent(before?: number, after?: number) {
  if (!before || before <= 0) return 0
  return Math.round(Math.min(100, Math.max(0, ((before - (after || 0)) / before) * 100)))
}

function contextEngineeringTrace(trace?: RetrievalTraceLike | null): ContextEngineering | null {
  if (!trace) return null
  if (trace.context_engineering) return trace.context_engineering
  const raw = Number(trace.context_chars_before_packing || 0)
  const packed = Number(trace.context_chars_after_packing || 0)
  return {
    ran: raw > 0,
    raw_chars: raw,
    packed_chars: packed,
    saved_chars: Math.max(raw - packed, 0),
    shrink_percent: contextShrinkPercent(raw, packed),
  }
}

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

// Isolated terminal component — memo prevents parent re-renders from scrolling the list
const MiniTerminal = memo(function MiniTerminal({
  steps, loading, open, onToggle
}: {
  steps: ProgressStep[]
  loading: boolean
  open: boolean
  onToggle: () => void
}) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new steps arrive while open
  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [steps, open])

  if (steps.length === 0) return null

  const lastStep = steps[steps.length - 1]

  return (
    <div className={cn(
      "mb-6 rounded-2xl border overflow-hidden transition-all duration-300",
      loading
        ? "border-primary-500/30 bg-black/5 dark:bg-black/60 shadow-[0_0_24px_rgba(var(--primary-500-rgb),0.08)]"
        : "border-border/30 bg-black/5 dark:bg-black/40"
    )}>
      {/* Terminal header bar */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 px-4 py-2.5 hover:bg-black/5 dark:hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
        </div>
        <Terminal size={12} className={cn("ml-1", loading ? "text-primary-500 dark:text-primary-400" : "text-muted-foreground/60")} />
        <span className={cn("text-xs font-mono font-medium flex-1 text-left truncate",
          loading ? "text-primary-600 dark:text-primary-300/80" : "text-muted-foreground/60"
        )}>
          {loading ? lastStep.message : `${steps.length} steps completed`}
        </span>
        {loading && <RefreshCw size={11} className="text-primary-400 animate-spin shrink-0" />}
        {open ? <ChevronUp size={14} className="text-muted-foreground/50 shrink-0" /> : <ChevronDown size={14} className="text-muted-foreground/50 shrink-0" />}
      </button>

      {/* Scrollable log body */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 160 }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div
              ref={scrollRef}
              className="h-40 overflow-y-auto px-4 py-3 font-mono text-xs flex flex-col gap-1.5 custom-scrollbar"
            >
              {steps.map((step, idx) => {
                const isLast = idx === steps.length - 1
                const details = formatProgressDetails(step.details)
                return (
                  <div
                    key={`${step.ref}-${idx}`}
                    className={cn(
                      "flex items-start gap-2 leading-relaxed",
                      isLast && loading ? "text-primary-600 dark:text-primary-300" : "text-zinc-600 dark:text-zinc-500"
                    )}
                    style={{ paddingLeft: `${Math.min(step.depth, 6) * 14}px` }}
                  >
                    <span className="shrink-0 mt-px">
                      {isLast && loading
                        ? <span className="inline-block w-1.5 h-3 bg-primary-500 dark:bg-primary-400 animate-pulse rounded-sm" />
                        : <span className="text-zinc-400 dark:text-zinc-700">›</span>
                      }
                    </span>
                    <span className="min-w-0">
                      <span className="break-words">{step.message}</span>
                      {details && <span className="ml-2 text-zinc-400 dark:text-zinc-600">{details}</span>}
                    </span>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
})

function formatProgressDetails(details?: Record<string, unknown>) {
  if (!details) return ''
  const entries = Object.entries(details)
    .filter(([key]) => !key.endsWith('_ids') && key !== 'recall_keys' && key !== 'sub_queries')
    .slice(0, 3)
  if (entries.length === 0) return ''
  return entries.map(([key, value]) => `${key}:${compactValue(value)}`).join(' ')
}

function compactValue(value: unknown) {
  if (Array.isArray(value)) return `[${value.length}]`
  if (value && typeof value === 'object') return '{...}'
  const text = String(value)
  return text.length > 40 ? `${text.slice(0, 37)}...` : text
}

function citationHref(citation: Citation) {
  return `/notes/${citation.source_input_id}?start=${citation.start_char ?? ''}&end=${citation.end_char ?? ''}`
}

function InlineAnswer({ answer, citations }: { answer: string; citations: Citation[] }) {
  const [openId, setOpenId] = useState<string | null>(null)
  
  let citeIndex = 0
  const processedAnswer = answer
    .replace(/\[\[cite:([^\]\s]+)\]\]?/g, (_, chunkId) => {
      const id = `${chunkId}:${citeIndex++}`
      return `[cite](cite:${id})`
    })
    .replace(STRAY_CITE_MARKER_RE, '') // strip any malformed stray markers

  return (
    <div className="prose dark:prose-invert max-w-none prose-p:leading-7 prose-headings:font-bold prose-pre:bg-input/50 prose-pre:border prose-pre:border-border/50">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children, ...props }) => {
            let chunkId: string | null = null;
            let indexStr = '0';

            if (href?.startsWith('cite:')) {
              [chunkId, indexStr] = href.replace('cite:', '').split(':')
            } else if (href && citations.some((c) => c.source_chunk_id === href)) {
              chunkId = href;
              indexStr = (citeIndex++).toString();
            }

            if (chunkId) {
              const citation = citations.find((item) => item.source_chunk_id === chunkId)
              if (!citation) return <span className="text-muted-foreground line-through decoration-muted-foreground/50 cursor-help" title="Source not found">{children}</span>
              const sourceNumber = citations.findIndex((item) => item.source_chunk_id === chunkId) + 1
              const markerId = `${chunkId}-${indexStr}`
              const isOpen = openId === markerId

              return (
                <span className={`inline-citation-wrap ${isOpen ? '!z-[100]' : ''}`}>
                  <button
                    type="button"
                    className="inline-citation-chip"
                    onClick={(e) => {
                      e.preventDefault();
                      setOpenId(isOpen ? null : markerId);
                    }}
                  >
                    Source {sourceNumber}
                  </button>
                  <AnimatePresence>
                    {isOpen && (
                      <motion.span
                        initial={{ opacity: 0, y: 8, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 6, scale: 0.98 }}
                        transition={{ duration: 0.16 }}
                        className="inline-citation-popover"
                      >
                        <span className="inline-citation-label">Cited lines</span>
                        <span className="inline-citation-quote">
                          "{citation.exact_quote || citation.raw_text}"
                        </span>
                        {citation.cleaned_text && (
                          <span className="inline-citation-summary">{citation.cleaned_text}</span>
                        )}
                        <Link className="inline-citation-link" to={citationHref(citation)}>
                          Open in note <ExternalLink size={13} />
                        </Link>
                      </motion.span>
                    )}
                  </AnimatePresence>
                </span>
              )
            }
            
            // If the LLM hallucinated a citation link that isn't valid, don't render it as a clickable link
            const textContent = String(children).toLowerCase();
            if (textContent === 'cite' || textContent.includes('citecite') || href === '#' || href === 'cite') {
               return <span className="text-muted-foreground line-through decoration-muted-foreground/50 cursor-help" title="Source not found">{children}</span>
            }

            return (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer" 
                onClick={(e) => {
                  if (!href || href.startsWith('#') || !href.startsWith('http')) {
                    e.preventDefault();
                  }
                }}
                {...props}
              >
                {children}
              </a>
            )
          }
        }}
      >
        {processedAnswer}
      </ReactMarkdown>
    </div>
  )
}

function statusToneClass(tone?: string) {
  if (tone === 'success') return 'border-primary-500/25 bg-primary-500/10 text-primary-600 dark:text-primary-300'
  if (tone === 'warning') return 'border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300'
  if (tone === 'danger') return 'border-red-500/25 bg-red-500/10 text-red-700 dark:text-red-300'
  return 'border-border/55 bg-background/45 text-foreground'
}

function TraceSummaryGrid({ items }: { items: TraceSummaryItem[] }) {
  const icons = [Timer, Zap, TrendingDown, Cpu, Layers, Database]
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
      {items.map((item, index) => {
        const Icon = icons[index % icons.length]
        return (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.22 }}
            className={cn('rounded-lg border p-4 min-h-28 flex flex-col justify-between', statusToneClass(item.tone))}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] font-extrabold uppercase tracking-[0.14em] opacity-70">{item.label}</span>
              <Icon size={16} className="shrink-0 opacity-70" />
            </div>
            <strong className="mt-3 block break-words text-2xl font-black leading-tight">{item.value}</strong>
            {item.detail && <span className="mt-1 text-xs font-semibold leading-5 opacity-75">{item.detail}</span>}
          </motion.div>
        )
      })}
    </div>
  )
}

function SavingsPanel({ savings }: { savings?: Record<string, any> }) {
  if (!savings) return null
  const rows = [
    ['Cache', `${savings.cache_hits ?? 0} hits`, `${savings.cache_misses ?? 0} misses · ${savings.cache_sets ?? 0} writes`, Zap],
    ['LLM', `${savings.llm_calls_saved ?? 0} calls saved`, `${savings.llm_calls_observed ?? 0} calls observed · ${formatNumber(savings.tokens_observed)} tokens`, Cpu],
    ['Context', `${savings.context_shrink_percent ?? 0}% smaller`, `${formatNumber(savings.context_saved_chars)} chars saved`, TrendingDown],
    ['Skipped', `${Array.isArray(savings.steps_skipped) ? savings.steps_skipped.length : 0} steps`, Array.isArray(savings.steps_skipped) ? savings.steps_skipped.slice(0, 4).join(', ') || 'None' : 'None', GitBranch],
  ] as const
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {rows.map(([label, value, detail, Icon]) => (
        <div key={label} className="rounded-lg border border-border/55 bg-background/35 p-4 flex items-start gap-3">
          <div className="h-9 w-9 rounded-lg border border-primary-500/20 bg-primary-500/10 text-primary-500 flex items-center justify-center shrink-0">
            <Icon size={17} />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
            <div className="mt-1 text-base font-black text-foreground">{value}</div>
            <div className="mt-0.5 text-xs font-semibold text-muted-foreground break-words">{detail}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

function FlowStepList({ steps }: { steps: FlowStep[] }) {
  const iconFor = (step: FlowStep) => {
    if (step.type === 'cache') return <Zap size={14} className="text-amber-500" />
    if (step.type === 'llm') return <Cpu size={14} className="text-blue-500" />
    return <Database size={14} className="text-zinc-500" />
  }

  const colorFor = (step: FlowStep) => {
    if (step.type === 'cache') return 'border-amber-400/60 bg-amber-50/40 dark:bg-amber-900/10'
    if (step.type === 'llm') return 'border-blue-400/60 bg-blue-50/40 dark:bg-blue-900/10'
    return 'border-zinc-300/60 dark:border-zinc-700/60 bg-black/5 dark:bg-white/5'
  }

  const lineColorFor = (step: FlowStep) => {
    if (step.type === 'cache') return 'bg-amber-400/50'
    if (step.type === 'llm') return 'bg-blue-400/50'
    return 'bg-zinc-400/40'
  }

  return (
    <div className="flex flex-col gap-0">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Retrieval Pipeline</div>
          <div className="text-xs text-muted-foreground mt-1">Backend-authored flow, including cache skips and nested sub-query passes.</div>
        </div>
        <Gauge size={18} className="text-primary-500" />
      </div>
      {steps.map((step, i) => (
        <motion.div
          key={step.id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05, duration: 0.22 }}
          className="flex gap-3"
        >
          <div className="flex flex-col items-center">
            <div className={cn('w-6 h-6 rounded-full border flex items-center justify-center flex-shrink-0 z-10', colorFor(step))}>
              {iconFor(step)}
            </div>
            {i < steps.length - 1 && (
              <div className={cn('w-0.5 flex-1 mt-1 mb-1', lineColorFor(step))} />
            )}
          </div>

          <div className={cn('flex-1 rounded-xl border px-4 py-3 mb-2', colorFor(step))}>
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 leading-tight">{step.title}</span>
              <div className="flex items-center gap-2 flex-wrap">
                <StepBadge status={step.status} />
                {step.metrics?.duration_ms != null && (
                  <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 flex items-center gap-1">
                    <Clock size={9} /> {formatMs(step.metrics.duration_ms)}
                  </span>
                )}
                {step.metrics?.model_used && (
                  <span className="text-[10px] font-mono text-blue-500/80 dark:text-blue-400/70">{step.metrics.model_used}</span>
                )}
              </div>
            </div>
            {step.subtitle && <p className="mt-1 text-xs leading-5 text-muted-foreground">{step.subtitle}</p>}
            {step.badges && step.badges.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {step.badges.map((badge) => (
                  <span key={badge} className="rounded-full border border-border/60 bg-background/50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    {badge.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}
            {step.metrics && (
              <div className="mt-1.5 flex gap-3 flex-wrap">
                {step.metrics.prompt_tokens != null && <span className="text-[10px] text-zinc-500">↑ {formatNumber(step.metrics.prompt_tokens)} prompt</span>}
                {step.metrics.completion_tokens != null && <span className="text-[10px] text-zinc-500">↓ {formatNumber(step.metrics.completion_tokens)} completion</span>}
                {step.metrics.total_tokens != null && <span className="text-[10px] font-semibold text-zinc-600 dark:text-zinc-400">= {formatNumber(step.metrics.total_tokens)} total tokens</span>}
              </div>
            )}
            <DetailChips details={step.details} />
            {step.children && step.children.length > 0 && (
              <div className="mt-3 grid gap-2">
                {step.children.map((child, childIndex) => (
                  <motion.div
                    key={child.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: (i * 0.05) + (childIndex * 0.03), duration: 0.18 }}
                    className="rounded-lg border border-border/55 bg-background/45 p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-foreground">{child.title}</div>
                        {child.subtitle && <div className="mt-0.5 text-[11px] leading-4 text-muted-foreground break-words">{child.subtitle}</div>}
                      </div>
                      <StepBadge status={child.status} />
                    </div>
                    <DetailChips details={child.details} />
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  )
}

function StepBadge({ status }: { status: FlowStep['status'] }) {
  const text = status === 'hit' ? 'Cache hit' : status === 'skipped' || status === 'skip' ? 'Skipped' : status
  const cls = status === 'hit'
    ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400'
    : status === 'skipped' || status === 'skip'
      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
      : 'bg-zinc-100 dark:bg-zinc-900/60 text-zinc-600 dark:text-zinc-400'
  return (
    <span className={cn('text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1 shrink-0', cls)}>
      {status === 'hit' && <CheckCircle size={9} />}
      {text}
    </span>
  )
}

function DetailChips({ details }: { details?: Record<string, any> }) {
  if (!details) return null
  const entries = Object.entries(details)
    .filter(([, value]) => value !== undefined && value !== null && value !== '' && !(Array.isArray(value) && value.length === 0))
    .slice(0, 8)
  if (entries.length === 0) return null
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {entries.map(([key, value]) => (
        <span key={key} className="text-[10px] px-2 py-0.5 rounded-md bg-white/70 dark:bg-zinc-900/60 border border-black/10 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400">
          <span className="font-bold">{key.replace(/_/g, ' ')}:</span> {compactTraceValue(value)}
        </span>
      ))}
    </div>
  )
}

function compactTraceValue(value: unknown) {
  if (Array.isArray(value)) return value.length <= 3 ? value.join(', ') : `${value.length} items`
  if (value && typeof value === 'object') return `${Object.keys(value as Record<string, unknown>).length} fields`
  const text = String(value)
  return text.length > 54 ? `${text.slice(0, 51)}...` : text
}

function formatNumber(value: unknown) {
  const n = Number(value || 0)
  return Number.isFinite(n) ? n.toLocaleString() : '0'
}

function formatMs(value: unknown) {
  const n = Number(value || 0)
  if (!Number.isFinite(n)) return 'n/a'
  return n < 1000 ? `${Math.round(n)}ms` : `${(n / 1000).toFixed(1)}s`
}

export function AskView({ token }: { token: string }) {

  const {
    query, setQuery, loading, showTrace, setShowTrace, showFilters, setShowFilters,
    terminalOpen, setTerminalOpen,
    withinDirectories, setWithinDirectories, excludingDirectories, setExcludingDirectories,
    withinTags, setWithinTags, excludingTags, setExcludingTags, withinTagsCondition, setWithinTagsCondition,
    result, toast, progressSteps, handleAsk, stopAsk
  } = useAsk()
  const contextEngineering = contextEngineeringTrace(result?.retrieval_trace)
  const traceUi = result?.retrieval_trace?.ui
  const flowSteps = traceUi?.flow || result?.retrieval_trace?.flow_steps || []

  return (
    <div className="flex flex-col flex-1 h-full max-w-4xl mx-auto w-full pt-10 md:pt-20 relative">
      {/* Dynamic Ambient Background */}
      <div className="ask-ambient fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="ask-ambient-primary" />
        <div className="ask-ambient-accent" />
      </div>

      <AnimatePresence>
        {toast && <ToastMessage toast={toast} />}
      </AnimatePresence>

      {/* The Omnibar */}
      <motion.div
        className={cn(
          "w-full transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] z-10",
          result ? "mb-12" : "my-auto"
        )}
      >
        {!result && !loading && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <motion.div 
              whileHover={{ scale: 1.05, rotate: 5 }}
              whileTap={{ scale: 0.95 }}
              className="inline-flex items-center justify-center w-20 h-20 rounded-[2.5rem] bg-background/50 backdrop-blur-xl border border-border/50 mb-6 shadow-2xl relative"
            >
              <div className="absolute inset-0 rounded-[2.5rem] bg-gradient-to-tr from-primary-500/20 to-accent-500/20 blur-md -z-10"></div>
              <img src="/favicon.svg" alt="UnmessIt" className="w-10 h-10 object-contain" />
            </motion.div>
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/60">
              What do you need to know?
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground font-medium max-w-2xl mx-auto">
              Ask anything and let the AI synthesize answers from your knowledge base.
            </p>
          </motion.div>
        )}

        <div className="relative group mx-auto w-full max-w-3xl">
          <div className="absolute -inset-1.5 bg-gradient-to-r from-primary-500/30 via-accent-500/30 to-primary-500/30 rounded-[2rem] blur-xl opacity-50 group-hover:opacity-100 transition duration-500 group-hover:duration-200"></div>
          <div className="relative flex items-center w-full bg-background/80 backdrop-blur-2xl border border-border/50 rounded-[1.8rem] shadow-2xl overflow-hidden focus-within:border-primary-500/50 focus-within:bg-background/95 transition-all duration-300 group-hover:shadow-primary-500/10">
            <div className="pl-6 flex items-center justify-center shrink-0">
              <img 
                src="/favicon.svg" 
                alt="UnmessIt" 
                className={cn(
                  "w-7 h-7 object-contain transition-all duration-700", 
                  loading ? "animate-spin" : "opacity-70 group-hover:opacity-100 group-focus-within:opacity-100 group-focus-within:scale-110"
                )} 
              />
            </div>
            <input
              autoFocus
              className="w-full bg-transparent border-none py-6 px-5 text-xl font-medium outline-none focus:outline-none focus:ring-0 placeholder:text-muted-foreground/40 text-foreground"
              placeholder="Ask anything..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey || !e.shiftKey)) {
                  e.preventDefault()
                  void handleAsk(token)
                }
              }}
            />
            <button
              className={cn(
                "mr-1 rounded-[1.2rem] p-4 transition-all flex items-center justify-center shrink-0",
                showFilters || withinDirectories || excludingDirectories || withinTags || excludingTags
                  ? "bg-primary-500/10 text-primary-500 hover:bg-primary-500/20"
                  : "bg-transparent text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
              onClick={() => setShowFilters(!showFilters)}
              title="Filters"
            >
              <SlidersHorizontal size={20} />
            </button>
            {loading ? (
              <button
                className="m-2.5 rounded-[1.2rem] px-6 py-4 font-bold transition-all flex items-center gap-2 shrink-0 bg-red-500/10 text-red-500 hover:bg-red-500/20 active:scale-95 shadow-lg"
                onClick={stopAsk}
              >
                <Square size={16} fill="currentColor" /> Stop
              </button>
            ) : (
              <button
                className={cn(
                  "m-2.5 rounded-[1.2rem] px-6 py-4 font-bold transition-all flex items-center gap-2 shrink-0",
                  query.trim()
                    ? "bg-foreground text-background hover:scale-105 active:scale-95 shadow-lg"
                    : "bg-muted text-muted-foreground cursor-not-allowed opacity-50"
                )}
                onClick={() => handleAsk(token)}
                disabled={!query.trim()}
              >
                Ask <ChevronRight size={18} className={cn("transition-transform", query.trim() ? "translate-x-1" : "")} />
              </button>
            )}
          </div>
          
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="w-full mt-3 overflow-visible relative z-10"
              >
                <div className="bg-background/60 backdrop-blur-xl border border-border/40 rounded-2xl p-4 shadow-2xl flex flex-col gap-4">
                  {/* Filter hints */}
                  <div className="text-[11px] text-muted-foreground/80 leading-relaxed bg-muted/20 border border-border/20 rounded-xl p-2.5 flex flex-col gap-1">
                    <p>
                      <strong className="text-foreground/90">Directories:</strong> If included, search is scoped <span className="underline decoration-primary-500/40">only</span> to those folders and their sub-folders. If only excluded, the whole knowledge base is searched except those folders.
                    </p>
                    <p>
                      <strong className="text-foreground/90">Tags:</strong> Scopes search to documents matching the specified tags (Any/All logical matching). Excluded tags will filter out matching documents entirely.
                    </p>
                  </div>

                  {/* Directories row */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <DirectorySearchSelect
                      label="Include Directories"
                      mode="include"
                      value={withinDirectories}
                      onChange={setWithinDirectories}
                      token={token}
                    />
                    <DirectorySearchSelect
                      label="Exclude Directories"
                      mode="exclude"
                      value={excludingDirectories}
                      onChange={setExcludingDirectories}
                      token={token}
                    />
                  </div>

                  <div className="h-px bg-border/20" />

                  {/* Tags row */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <TagSearchSelect
                      label="Include Tags"
                      mode="include"
                      value={withinTags}
                      onChange={setWithinTags}
                      condition={withinTagsCondition}
                      onConditionChange={setWithinTagsCondition}
                      token={token}
                    />
                    <TagSearchSelect
                      label="Exclude Tags"
                      mode="exclude"
                      value={excludingTags}
                      onChange={setExcludingTags}
                      token={token}
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Mini Terminal — fixed height, persists after result */}
      <MiniTerminal
        steps={progressSteps}
        loading={loading}
        open={terminalOpen}
        onToggle={() => setTerminalOpen(!terminalOpen)}
      />

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 40, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
            className="bento-card relative z-20 p-8 md:p-12"
          >
            <div className="text-lg leading-8 text-foreground/90">
              <InlineAnswer answer={result.answer} citations={result.citations || []} />
            </div>

            {result.citations?.length > 0 && (
              <div className="mt-12 pt-8 border-t border-border/50">
                <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-6">Sources Used</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {/* We map over citations instead of source_chunks here because source_chunks contains the 
                      entire raw retrieval context (which includes unrelated padding chunks from vector search's 
                      fixed top-K behavior). citations contains only what the AI actually decided to use. */}
                  {result.citations.map((citation, i) => (
                    <Link 
                      key={i} 
                      to={`/notes/${citation.source_input_id}?start=${citation.start_char ?? ''}&end=${citation.end_char ?? ''}`}
                      className="group p-4 rounded-2xl bg-input/50 border border-border/50 hover:bg-input hover:border-primary-500/50 transition-colors block"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-xs font-bold text-primary-500 group-hover:text-primary-400 transition-colors">
                          Source {i + 1}
                        </div>
                        <ExternalLink size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <p className="text-sm text-foreground/80 line-clamp-3 italic mb-2">"{citation.raw_text}"</p>
                      <p className="text-xs text-muted-foreground line-clamp-2">{citation.cleaned_text}</p>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {result.retrieval_trace && (
              <div className="mt-8 pt-8 border-t border-border/50">
                <button 
                  onClick={() => setShowTrace(!showTrace)}
                  className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors w-fit"
                >
                  <Terminal size={16} /> Retrieval Analysis
                  {showTrace ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                <AnimatePresence>
                  {showTrace && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="flex flex-col gap-6 mt-4">
                        {traceUi?.summary && traceUi.summary.length > 0 ? (
                          <TraceSummaryGrid items={traceUi.summary} />
                        ) : (
                          <TraceSummaryGrid items={[
                            { id: 'chunks', label: 'Chunks found', value: String(result.retrieval_trace.source_chunk_count || 0), tone: 'neutral' },
                            { id: 'citations', label: 'Citations used', value: String(result.retrieval_trace.citation_count || 0), tone: 'success' },
                            { id: 'mode', label: 'Retrieval mode', value: String(result.retrieval_trace.mode || 'N/A').replace(/_/g, ' '), tone: 'neutral' },
                            { id: 'context', label: 'Context saved', value: `${contextEngineering?.shrink_percent ?? 0}%`, detail: `${formatNumber(contextEngineering?.saved_chars)} chars`, tone: 'success' },
                          ]} />
                        )}

                        <SavingsPanel savings={traceUi?.savings} />

                        {flowSteps.length > 0 && (
                          <div className="mt-1 rounded-lg border border-border/45 bg-card/35 p-4 backdrop-blur-xl">
                            <FlowStepList steps={flowSteps} />
                          </div>
                        )}
                      </div>

                      <details className="mt-6 group">
                        <summary className="text-xs font-mono font-bold text-zinc-600 cursor-pointer hover:text-zinc-800 dark:hover:text-zinc-400 transition-colors list-none flex items-center gap-2">
                          <ChevronRight size={14} className="group-open:rotate-90 transition-transform" /> View Raw JSON Trace
                        </summary>
                        <pre className="mt-3 p-6 rounded-2xl bg-black/5 dark:bg-[#0a0a0a] border border-black/10 dark:border-[#222] text-[10px] font-mono text-zinc-600 dark:text-zinc-500 overflow-x-auto custom-scrollbar shadow-inner">
                          {JSON.stringify(result.retrieval_trace, null, 2)}
                        </pre>
                      </details>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
