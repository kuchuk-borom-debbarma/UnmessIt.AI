import { useCallback, useEffect, useState } from 'react'
import { Play, RefreshCw, AlertCircle, CheckCircle2, Clock3, Pause, Square, ExternalLink } from 'lucide-react'
import { api } from '../../lib/api'
import { cn } from '../../lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'

type JobStatus = 'queued' | 'running' | 'waiting_retry' | 'complete' | 'failed' | 'aborted' | 'paused'

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
}

type Toast = { tone: 'success' | 'danger'; message: string }
type JobsResponse = { data: IngestJob[], total: number, page: number, limit: number }

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

export function JobsView({ token }: { token: string }) {
  const [jobs, setJobs] = useState<IngestJob[]>([])
  const [loading, setLoading] = useState(true)
  const [, setShowLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [])
  const [toast, setToast] = useState<Toast | null>(null)
  
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20

  const load = useCallback(async () => {
    try {
      const data = await api<JobsResponse>(`/api/advanced/ingest_jobs?page=${page}&limit=${limit}`, { token })
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
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [load])

  const resumeJob = async (jobId: string) => {
    try {
      await api(`/api/advanced/ingest_jobs/${jobId}/resume`, { method: 'POST', token })
      setToast({ tone: 'success', message: 'Job resumed' })
      load()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Failed to resume job' })
    }
  }

  const pauseJob = async (jobId: string) => {
    try {
      await api(`/api/advanced/ingest_jobs/${jobId}/pause`, { method: 'POST', token })
      setToast({ tone: 'success', message: 'Job paused' })
      load()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Failed to pause job' })
    }
  }

  const deleteJob = async (jobId: string) => {
    if (!confirm('Stop and delete this job?')) return
    try {
      await api(`/api/advanced/ingest_jobs/${jobId}`, { method: 'DELETE', token })
      setToast({ tone: 'success', message: 'Job stopped and deleted' })
      load()
    } catch (err) {
      setToast({ tone: 'danger', message: err instanceof Error ? err.message : 'Failed to stop job' })
    }
  }

  return (
    <div className="flex flex-col flex-1 h-full max-w-6xl mx-auto w-full pt-8">
      <AnimatePresence>
        {toast && <ToastMessage toast={toast} />}
      </AnimatePresence>

      <div className="flex items-end justify-between mb-12">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2">Ingestion Pipeline</h1>
          <p className="text-muted-foreground font-medium">Monitor background chunking and embedding tasks.</p>
        </div>
        <button 
          onClick={load}
          className="premium-btn premium-btn-secondary w-12 h-12 rounded-[1.5rem]"
          aria-label="Refresh jobs"
          title="Refresh jobs"
        >
          <RefreshCw size={20} className={cn(loading && "animate-spin")} />
        </button>
      </div>

      <div className="bento-card bg-[#0a0a0a] border-[#222] p-2">
        {/* Terminal Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[#222]">
          <div className="w-3 h-3 rounded-full bg-red-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-amber-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-green-500/50"></div>
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
              jobs.map(job => (
                <motion.div 
                  key={job.id} 
                  layout
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-black border border-[#222] hover:border-primary-500/30 transition-colors font-mono text-sm"
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
                              to={`/notes/${job.id}`}
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
                        <div className="text-red-400 mt-1 bg-red-950/30 px-3 py-2 rounded-md border border-red-900/50">
                          {job.error}
                        </div>
                      )}
                      <div className="flex flex-wrap items-center gap-3 mt-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                        <span className="flex items-center gap-1">
                          Stage: <span className="text-zinc-300">{job.stage}</span>
                        </span>
                        <span>&bull;</span>
                        <span className="flex items-center gap-1">
                          Attempts: <span className="text-zinc-300">{job.attempt_count}</span>
                        </span>
                        <span>&bull;</span>
                        <span className="flex items-center gap-1">
                          Updated: <span className="text-zinc-300">{new Date(job.updated_at).toLocaleTimeString()}</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pl-7 md:pl-0">
                    {(job.status === 'queued' || job.status === 'running' || job.status === 'waiting_retry') && (
                      <button 
                        onClick={() => pauseJob(job.id)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 transition-colors border border-amber-500/20"
                        title="Pause Job"
                      >
                        <Pause size={14} /> Pause
                      </button>
                    )}
                    {(job.status === 'failed' || job.status === 'paused') && (
                      <button 
                        onClick={() => resumeJob(job.id)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-500 hover:bg-primary-500/20 transition-colors border border-primary-500/20"
                      >
                        <Play size={14} /> Resume
                      </button>
                    )}
                    <button 
                      onClick={() => deleteJob(job.id)}
                      className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-900 border border-[#222] text-zinc-500 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-500 transition-colors ml-1"
                      title="Stop and Delete Job"
                    >
                      <Square size={14} />
                    </button>
                  </div>
                </motion.div>
              ))
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
