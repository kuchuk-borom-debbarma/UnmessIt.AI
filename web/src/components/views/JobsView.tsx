import { memo, useCallback, useEffect, useMemo, useState, useRef } from 'react'
import { Play, RefreshCw, AlertCircle, CheckCircle2, Clock3, Pause, Square, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../../lib/api'
import { cn } from '../../lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import { applyProgressEvent, type JobProgressEvent, type JobStatus, type ProgressByJob, type ProgressLine, useIngestJobEvents } from '../../lib/ingestJobEvents'

type JobMetadata = {
  input_chars?: number
  source_window_count?: number
  source_chunk_count?: number
  source_chunks?: number
  source_chunks_reused?: number
  recall_chunk_count?: number
  recall_key_count?: number
  recall_keys?: number
  recall_link_count?: number
  recall_vector_count?: number
  source_vector_count?: number
  directory_path?: string
  progress_message?: string
  progress_logs?: string[]
}

type IngestJob = {
  id: string
  note_id: string
  note_text?: string
  status: JobStatus
  stage: string
  attempt_count: number
  error: string | null
  created_at: string
  updated_at: string
  metadata?: JobMetadata
}

type Toast = { tone: 'success' | 'danger'; message: string }
type JobsResponse = { data: IngestJob[], total: number, page: number, limit: number }

const statusRank: Record<JobStatus, number> = {
  running: 0,
  queued: 1,
  waiting_retry: 2,
  failed: 3,
  paused: 4,
  aborted: 5,
  complete: 6,
}

function numberMetric(value?: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString() : null
}

function jobMetrics(job: IngestJob) {
  const metadata = job.metadata ?? {}
  const items = [
    ['Input', numberMetric(metadata.input_chars)],
    ['Windows', numberMetric(metadata.source_window_count)],
    ['Chunks', numberMetric(metadata.source_chunk_count ?? metadata.source_chunks)],
    ['Recall chunks', numberMetric(metadata.recall_chunk_count)],
    ['Recall keys', numberMetric(metadata.recall_key_count ?? metadata.recall_keys)],
    ['Recall links', numberMetric(metadata.recall_link_count)],
    ['Key vectors', numberMetric(metadata.recall_vector_count)],
    ['Chunk vectors', numberMetric(metadata.source_vector_count)],
  ]
  return items.filter((item): item is [string, string] => item[1] !== null)
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

const ProgressLogLine = memo(function ProgressLogLine({ line }: { line: ProgressLine }) {
  const depth = Math.min(line.depth, 6)
  return (
    <div className="flex gap-2" style={{ paddingLeft: depth * 12 }}>
      <span className="text-amber-600/50 dark:text-amber-500/50 shrink-0">&gt;</span>
      <span className="break-words">{line.message}</span>
    </div>
  )
})

const JobProgressLog = memo(function JobProgressLog({ progress }: { progress: ProgressLine[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [progress])

  if (progress.length === 0) return null

  return (
    <div className="mt-1 relative border border-amber-500/20 dark:border-amber-900/30 rounded-md bg-amber-500/5 dark:bg-amber-950/20 text-amber-600 dark:text-amber-400/80 overflow-hidden font-mono text-[10px]">
      <div 
        ref={scrollRef}
        className={cn("px-3 py-2 overflow-y-auto custom-scrollbar flex flex-col gap-1 transition-all duration-300", expanded ? "max-h-96" : "max-h-64")}
      >
        {progress.map(line => (
          <ProgressLogLine key={line.ref} line={line} />
        ))}
      </div>
      <button 
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setExpanded(v => !v) }}
        className="absolute bottom-1 right-1 w-6 h-6 flex items-center justify-center bg-white/50 dark:bg-black/50 hover:bg-white/80 dark:hover:bg-black/80 rounded-md backdrop-blur-sm transition-colors text-amber-600/50 hover:text-amber-600 dark:text-amber-400/50 dark:hover:text-amber-400"
      >
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
    </div>
  )
})

export function JobsView({ token }: { token: string }) {
  const [jobs, setJobs] = useState<IngestJob[]>([])
  const [liveProgress, setLiveProgress] = useState<ProgressByJob>({})
  const [loading, setLoading] = useState(true)
  const [, setShowLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [])
  const [toast, setToast] = useState<Toast | null>(null)
  const [busyJobId, setBusyJobId] = useState<string | null>(null)
  
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20

  const load = useCallback(async () => {
    try {
      const data = await api<JobsResponse>(`/api/v1/advanced/ingest_jobs?page=${page}&limit=${limit}`, { token })
      setJobs(data.data)
      setTotal(data.total)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [page, token])

  useEffect(() => {
    load()
    const fallback = setInterval(load, 30000)
    return () => clearInterval(fallback)
  }, [load])

  const handleProgress = useCallback((data: JobProgressEvent) => {
    setLiveProgress(current => applyProgressEvent(current, data))
    setJobs(current => current
      .map(job => job.id === data.job_id ? { ...job, status: data.status, stage: data.stage } : job)
      .sort((a, b) => statusRank[a.status] - statusRank[b.status] || new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()))
  }, [])

  useIngestJobEvents(token, {
    onJob: () => { void load() },
    onProgress: handleProgress,
  })

  const jobCounts = useMemo(() => ({
    active: jobs.filter(job => ['running', 'queued', 'waiting_retry'].includes(job.status)).length,
    failed: jobs.filter(job => ['failed', 'aborted'].includes(job.status)).length,
    paused: jobs.filter(job => job.status === 'paused').length,
    complete: jobs.filter(job => job.status === 'complete').length,
  }), [jobs])

  const runJobAction = async (jobId: string, action: () => Promise<void>, success: string, failure: string) => {
    if (busyJobId) return
    setBusyJobId(jobId)
    try {
      await action()
      setToast({ tone: 'success', message: success })
      await load()
      window.setTimeout(() => {
        setBusyJobId(current => current === jobId ? null : current)
      }, 1000)
    } catch (err) {
      setBusyJobId(null)
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : failure })
    }
  }

  const resumeJob = async (jobId: string) => {
    await runJobAction(
      jobId,
      () => api(`/api/v1/advanced/ingest_jobs/${jobId}/resume`, { method: 'POST', token }),
      'Job resumed',
      'Failed to resume job'
    )
  }

  const pauseJob = async (jobId: string) => {
    await runJobAction(
      jobId,
      () => api(`/api/v1/advanced/ingest_jobs/${jobId}/pause`, { method: 'POST', token }),
      'Job paused',
      'Failed to pause job'
    )
  }

  const deleteJob = async (jobId: string) => {
    if (!confirm('Stop and delete this job?')) return
    await runJobAction(
      jobId,
      () => api(`/api/v1/advanced/ingest_jobs/${jobId}`, { method: 'DELETE', token }),
      'Job stopped and deleted',
      'Failed to stop job'
    )
  }

  return (
    <div className="app-page max-w-6xl">
      <AnimatePresence>
        {toast && <ToastMessage toast={toast} />}
      </AnimatePresence>

      <section className="page-hero">
        <div className="page-hero-inner">
          <div className="page-hero-copy">
            <div className="page-hero-icon">
              <RefreshCw size={24} />
            </div>
            <div>
              <p className="page-hero-kicker">Ingestion Pipeline</p>
              <h1 className="page-hero-title">Watch memory become searchable.</h1>
              <p className="page-hero-subtitle">
                Durable jobs chunk notes, generate recall links, embed vectors, and resume safely after rate limits or API failures.
              </p>
            </div>
          </div>
          <div className="page-hero-actions">
            <button className="premium-btn premium-btn-secondary h-11 gap-2 px-4" onClick={() => void load()}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
        </div>
        <div className="page-stat-grid">
          <div className="page-stat-card">
            <span>Active</span>
            <strong>{jobCounts.active}</strong>
            <small>running, queued, or retrying</small>
          </div>
          <div className="page-stat-card">
            <span>Paused</span>
            <strong>{jobCounts.paused}</strong>
            <small>manual resume available</small>
          </div>
          <div className="page-stat-card">
            <span>Failed</span>
            <strong>{jobCounts.failed}</strong>
            <small>needs attention</small>
          </div>
          <div className="page-stat-card">
            <span>Complete</span>
            <strong>{jobCounts.complete}</strong>
            <small>indexed history loaded</small>
          </div>
        </div>
      </section>

      <div className="bento-card bg-white dark:bg-[#0a0a0a] border-border/50 dark:border-[#222] p-2">
        {/* Terminal Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border/50 dark:border-[#222]">
          <div className="w-3 h-3 rounded-full bg-red-500/70"></div>
          <div className="w-3 h-3 rounded-full bg-amber-500/70"></div>
          <div className="w-3 h-3 rounded-full bg-green-500/70"></div>
          <span className="ml-2 text-xs font-mono text-zinc-500">pipeline-term</span>
        </div>

        {/* Terminal Body */}
        <div className="p-4 md:p-6 space-y-4">
          <AnimatePresence mode="popLayout">
            {jobs.length === 0 && !loading ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-12 text-center text-zinc-500 font-mono text-sm">
                &gt; No active or historical jobs found.
              </motion.div>
            ) : (
              jobs.map(job => {
                const metrics = jobMetrics(job)
                const progress = liveProgress[job.id] ?? []
                return (
                  <motion.div
                    key={job.id}
                    layout
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="flex flex-col md:flex-row md:items-start justify-between gap-4 p-4 rounded-xl bg-black/5 dark:bg-black border border-black/10 dark:border-[#222] hover:border-primary-500/30 transition-colors font-mono text-sm"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        {job.status === 'complete' && <CheckCircle2 className="text-primary-500" size={16} />}
                        {job.status === 'failed' && <AlertCircle className="text-red-500" size={16} />}
                        {job.status === 'aborted' && <AlertCircle className="text-red-500" size={16} />}
                        {job.status === 'running' && <RefreshCw className="animate-spin text-amber-500" size={16} />}
                        {job.status === 'queued' && <Clock3 className="text-muted-foreground" size={16} />}
                        {job.status === 'waiting_retry' && <Clock3 className="text-amber-500" size={16} />}
                        {job.status === 'paused' && <Pause className="text-muted-foreground" size={16} />}

                        <span className={cn(
                          "font-bold uppercase tracking-wider",
                          job.status === 'complete' && "text-primary-500",
                          job.status === 'failed' && "text-red-500",
                          job.status === 'aborted' && "text-red-500",
                          job.status === 'running' && "text-amber-500",
                          job.status === 'waiting_retry' && "text-amber-500",
                          job.status === 'queued' && "text-zinc-500",
                          job.status === 'paused' && "text-zinc-500",
                        )}>
                          [{job.status}]
                        </span>
                        <span className="text-zinc-500 truncate hidden md:inline-block">Job ID: {job.id}</span>
                      </div>
                      
                      <div className="flex flex-col gap-1 text-xs text-zinc-500 pl-7">
                        <div className="flex items-center gap-2">
                          {job.note_text ? (
                            <>
                              <span className="text-zinc-300 line-clamp-1 italic max-w-md">"{job.note_text}"</span>
                              <Link
                                to={`/notes/${job.note_id}`}
                                className="inline-flex items-center gap-1 hover:text-primary-400 transition-colors bg-primary-500/10 text-primary-500 px-2 py-0.5 rounded-md"
                                title="View Note"
                              >
                                View Note <ExternalLink size={12} />
                              </Link>
                            </>
                          ) : (
                            <span>Internal Task</span>
                          )}
                        </div>
                        {job.error && (
                          <div className="text-red-600 dark:text-red-400 mt-1 bg-red-500/10 dark:bg-red-950/30 px-3 py-2 rounded-md border border-red-500/20 dark:border-red-900/50">
                            {job.error}
                          </div>
                        )}
                        {job.status === 'running' && <JobProgressLog progress={progress} />}
                        {progress.length === 0 && job.metadata?.progress_message && job.status === 'running' && (
                          <div className="text-amber-600 dark:text-amber-400 mt-1 bg-amber-500/10 dark:bg-amber-950/30 px-3 py-2 rounded-md border border-amber-500/20 dark:border-amber-900/50 flex items-center gap-2">
                             <RefreshCw className="animate-spin" size={12} />
                             {job.metadata.progress_message}
                          </div>
                        )}
                        <div className="flex flex-wrap items-center gap-3 mt-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                          <span className="flex items-center gap-1">
                            Stage: <span className="text-zinc-700 dark:text-zinc-300">{job.stage}</span>
                          </span>
                          <span>&bull;</span>
                          <span className="flex items-center gap-1">
                            Attempts: <span className="text-zinc-700 dark:text-zinc-300">{job.attempt_count}</span>
                          </span>
                          <span>&bull;</span>
                          <span className="flex items-center gap-1">
                            Updated: <span className="text-zinc-700 dark:text-zinc-300">{new Date(job.updated_at).toLocaleTimeString()}</span>
                          </span>
                        </div>
                        {metrics.length > 0 && (
                          <div className="flex flex-wrap items-center gap-2 mt-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                            {metrics.map(([label, value]) => (
                              <span key={label} className="inline-flex items-center gap-1 rounded-md border border-black/10 dark:border-zinc-800 bg-black/5 dark:bg-zinc-950 px-2 py-0.5">
                                {label}: <span className="text-zinc-700 dark:text-zinc-300">{value}</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pl-7 md:pl-0">
                      {(job.status === 'queued' || job.status === 'running' || job.status === 'waiting_retry') && (
                        <button
                          disabled={busyJobId === job.id}
                          onClick={() => pauseJob(job.id)}
                          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 transition-colors border border-amber-500/20 disabled:opacity-50 disabled:pointer-events-none"
                          title="Pause Job"
                        >
                          <Pause size={14} /> Pause
                        </button>
                      )}
                      {(job.status === 'failed' || job.status === 'paused') && (
                        <button
                          disabled={busyJobId === job.id}
                          onClick={() => resumeJob(job.id)}
                          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-500 hover:bg-primary-500/20 transition-colors border border-primary-500/20 disabled:opacity-50 disabled:pointer-events-none"
                        >
                          <Play size={14} /> Resume
                        </button>
                      )}
                      <button 
                        disabled={busyJobId === job.id}
                        onClick={() => deleteJob(job.id)}
                        className="flex items-center justify-center w-8 h-8 rounded-lg bg-black/5 dark:bg-zinc-900 border border-black/10 dark:border-[#222] text-zinc-500 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-500 transition-colors ml-1 disabled:opacity-50 disabled:pointer-events-none"
                        title="Stop and Delete Job"
                      >
                        <Square size={14} />
                      </button>
                    </div>
                  </motion.div>
                )
              })
            )}
          </AnimatePresence>
        </div>
      </div>

      {Math.ceil(total / limit) > 1 && (
        <div className="flex items-center justify-center gap-4 mt-8 mb-12">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="premium-btn premium-btn-secondary px-6 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm font-medium text-muted-foreground">
            Page {page} of {Math.ceil(total / limit)}
          </span>
          <button
            disabled={page >= Math.ceil(total / limit)}
            onClick={() => setPage(p => p + 1)}
            className="premium-btn premium-btn-secondary px-6 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
