import { useState, useEffect, useRef } from 'react'
import { Search, RefreshCw, ChevronRight, ChevronDown, ChevronUp, CheckCircle2, ExternalLink, Terminal, SlidersHorizontal } from 'lucide-react'
import { api, API_BASE } from '../../lib/api'
import { cn } from '../../lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import { DirectorySearchSelect } from './DirectorySearchSelect'
import { TagSearchSelect } from './TagSearchSelect'

type SourceChunk = {
  id: string
  raw_input_id: string
  note_id: string
  text: string
  summary: string
}

type QueryResult = {
  answer: string
  citations: any[]
  source_chunks: SourceChunk[]
  retrieval_trace: Record<string, any>
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

export function AskView({ token }: { token: string }) {
  const [query, setQuery] = useState(() => sessionStorage.getItem('ask_query') || '')
  const [loading, setLoading] = useState(false)
  const [showTrace, setShowTrace] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [withinDirectories, setWithinDirectories] = useState(() => sessionStorage.getItem('ask_within_dirs') || '')
  const [excludingDirectories, setExcludingDirectories] = useState(() => sessionStorage.getItem('ask_excluding_dirs') || '')
  const [withinTags, setWithinTags] = useState(() => sessionStorage.getItem('ask_within_tags') || '')
  const [excludingTags, setExcludingTags] = useState(() => sessionStorage.getItem('ask_excluding_tags') || '')
  const [withinTagsCondition, setWithinTagsCondition] = useState<'any' | 'all'>(() => (sessionStorage.getItem('ask_within_tags_condition') as 'any' | 'all') || 'any')
  const [result, setResult] = useState<QueryResult | null>(() => {
    try {
      const saved = sessionStorage.getItem('ask_result')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })
  const [toast, setToast] = useState<Toast | null>(null)
  const [progressSteps, setProgressSteps] = useState<string[]>(() => {
    try {
      const saved = sessionStorage.getItem('ask_progress')
      return saved ? JSON.parse(saved) : []
    } catch { return [] }
  })

  useEffect(() => {
    sessionStorage.setItem('ask_query', query)
    sessionStorage.setItem('ask_within_dirs', withinDirectories)
    sessionStorage.setItem('ask_excluding_dirs', excludingDirectories)
    sessionStorage.setItem('ask_within_tags', withinTags)
    sessionStorage.setItem('ask_excluding_tags', excludingTags)
    sessionStorage.setItem('ask_within_tags_condition', withinTagsCondition)
  }, [query, withinDirectories, excludingDirectories, withinTags, excludingTags, withinTagsCondition])

  useEffect(() => {
    if (result) {
      sessionStorage.setItem('ask_result', JSON.stringify(result))
    } else {
      sessionStorage.removeItem('ask_result')
    }
  }, [result])

  useEffect(() => {
    if (progressSteps.length > 0) {
      sessionStorage.setItem('ask_progress', JSON.stringify(progressSteps))
    } else {
      sessionStorage.removeItem('ask_progress')
    }
  }, [progressSteps])

  const abortControllerRef = useRef<AbortController | null>(null)
  const evtSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
      evtSourceRef.current?.close()
    }
  }, [])

  const handleAsk = async () => {
    if (!query.trim() || loading) return
    setLoading(true)
    setToast(null)
    setResult(null)
    setProgressSteps([])

    const clientId = crypto.randomUUID()
    const evtSource = new EventSource(`${API_BASE}/api/retrieval/events/${clientId}`)
    evtSourceRef.current = evtSource
    evtSource.addEventListener('progress', (e) => {
      try {
        const evData = JSON.parse(e.data)
        setProgressSteps(prev => [...prev, evData.message])
      } catch {}
    })

    const abortController = new AbortController()
    abortControllerRef.current = abortController

    try {
      const within = withinDirectories.split(',').map(s => s.trim()).filter(Boolean)
      const excluding = excludingDirectories.split(',').map(s => s.trim()).filter(Boolean)
      const withinTagsArr = withinTags.split(',').map(s => s.trim()).filter(Boolean)
      const excludingTagsArr = excludingTags.split(',').map(s => s.trim()).filter(Boolean)
      
      const data = await api<QueryResult>('/api/retrieval/query', {
        method: 'POST',
        token,
        body: JSON.stringify({ 
          query, 
          client_id: clientId,
          within_directories: within.length > 0 ? within : undefined,
          excluding_directories: excluding.length > 0 ? excluding : undefined,
          within_tags: withinTagsArr.length > 0 ? withinTagsArr : undefined,
          excluding_tags: excludingTagsArr.length > 0 ? excludingTagsArr : undefined,
          within_tags_condition: withinTagsCondition,
        }),
        signal: abortController.signal
      })
      setResult(data)
    } catch (err) {
      console.error(err)
      if (err instanceof Error && err.name !== 'AbortError') {
        setToast({ tone: 'danger', message: err.message })
      }
    } finally {
      evtSource.close()
      evtSourceRef.current = null
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col flex-1 h-full max-w-4xl mx-auto w-full pt-10 md:pt-20 relative">
      {/* Dynamic Ambient Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <motion.div 
          animate={{ 
            scale: [1, 1.1, 1],
            opacity: [0.15, 0.3, 0.15],
            rotate: [0, 45, 0]
          }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary-500/30 blur-[120px]"
        />
        <motion.div 
          animate={{ 
            scale: [1, 1.2, 1],
            opacity: [0.1, 0.25, 0.1],
            rotate: [0, -45, 0]
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-[-10%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-accent-500/20 blur-[140px]"
        />
      </div>

      <AnimatePresence>
        {toast && <ToastMessage toast={toast} />}
      </AnimatePresence>

      {/* The Omnibar */}
      <motion.div 
        layout
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
                  void handleAsk()
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
            <button
              className={cn(
                "m-2.5 rounded-[1.2rem] px-6 py-4 font-bold transition-all flex items-center gap-2 shrink-0",
                query.trim() && !loading
                  ? "bg-foreground text-background hover:scale-105 active:scale-95 shadow-lg"
                  : "bg-muted text-muted-foreground cursor-not-allowed opacity-50"
              )}
              onClick={handleAsk}
              disabled={!query.trim() || loading}
            >
              {loading ? 'Searching...' : 'Ask'} <ChevronRight size={18} className={cn("transition-transform", query.trim() && !loading ? "translate-x-1" : "")} />
            </button>
          </div>
          
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, y: -10, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -10, height: 0 }}
                className="w-full mt-4 p-5 bg-background/80 backdrop-blur-xl border border-border/50 rounded-[1.8rem] shadow-xl flex flex-col gap-4 overflow-visible relative z-10"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <DirectorySearchSelect
                    label="Include Directories"
                    value={withinDirectories}
                    onChange={setWithinDirectories}
                    token={token}
                  />
                  <DirectorySearchSelect
                    label="Exclude Directories"
                    value={excludingDirectories}
                    onChange={setExcludingDirectories}
                    token={token}
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <TagSearchSelect
                    label="Include Tags"
                    value={withinTags}
                    onChange={setWithinTags}
                    condition={withinTagsCondition}
                    onConditionChange={setWithinTagsCondition}
                    token={token}
                  />
                  <TagSearchSelect
                    label="Exclude Tags"
                    value={excludingTags}
                    onChange={setExcludingTags}
                    token={token}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Progress Steps */}
      <AnimatePresence>
        {loading && progressSteps.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0, filter: 'blur(10px)' }}
            animate={{ opacity: 1, height: 'auto', filter: 'blur(0px)' }}
            exit={{ opacity: 0, height: 0, filter: 'blur(10px)' }}
            className="mb-8 overflow-hidden"
          >
            <div className="bento-card p-6 flex flex-col gap-4">
              {progressSteps.map((step, idx) => {
                const isLast = idx === progressSteps.length - 1;
                return (
                  <motion.div 
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={cn(
                      "flex items-center gap-3 font-mono text-sm",
                      isLast ? "text-primary-400" : "text-muted-foreground"
                    )}
                  >
                    {isLast ? (
                      <RefreshCw className="animate-spin" size={16} />
                    ) : (
                      <CheckCircle2 size={16} />
                    )}
                    <span>{step}</span>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* The Answer Sheet */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 40, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
            className="bento-card p-8 md:p-12"
          >
            <div className="prose prose-invert prose-lg max-w-none prose-headings:font-space prose-headings:font-bold prose-a:text-primary-400 prose-a:no-underline hover:prose-a:text-primary-300">
              <div dangerouslySetInnerHTML={{ __html: result.answer }} />
            </div>

            {result.source_chunks?.length > 0 && (
              <div className="mt-12 pt-8 border-t border-border/50">
                <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-6">Sources Used</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {result.source_chunks.map((chunk, i) => (
                    <Link 
                      key={i} 
                      to={`/notes/${chunk.note_id}`}
                      className="group p-4 rounded-2xl bg-input/50 border border-border/50 hover:bg-input hover:border-primary-500/50 transition-colors block"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-xs font-bold text-primary-500 group-hover:text-primary-400 transition-colors">
                          Source {i + 1}
                        </div>
                        <ExternalLink size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <p className="text-sm text-foreground/80 line-clamp-3 italic mb-2">"{chunk.text}"</p>
                      <p className="text-xs text-muted-foreground line-clamp-2">{chunk.summary}</p>
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
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-5 rounded-2xl bg-black/40 border border-[#222] shadow-inner">
                          <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Sub-Queries Generated</div>
                          <div className="flex flex-wrap gap-2">
                            {result.retrieval_trace.sub_queries?.map((sq: string, i: number) => (
                              <span key={i} className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-300">
                                {sq}
                              </span>
                            )) || <span className="text-zinc-600 text-xs italic">None</span>}
                          </div>
                        </div>

                        <div className="p-5 rounded-2xl bg-black/40 border border-[#222] shadow-inner">
                          <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Entities Extracted</div>
                          <div className="flex flex-wrap gap-2">
                            {result.retrieval_trace.extracted_subjects?.map((subj: string, i: number) => (
                              <span key={i} className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 flex items-center gap-1">
                                <Search size={10} className="text-zinc-500" /> {subj}
                              </span>
                            )) || <span className="text-zinc-600 text-xs italic">None</span>}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                        <div className="p-5 rounded-2xl bg-black/40 border border-[#222] flex flex-col items-center justify-center text-center shadow-inner">
                          <div className="text-3xl font-black text-white mb-1">{result.retrieval_trace.source_chunk_count || 0}</div>
                          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Chunks Found</div>
                        </div>
                        <div className="p-5 rounded-2xl bg-black/40 border border-[#222] flex flex-col items-center justify-center text-center shadow-inner relative overflow-hidden">
                          <div className="absolute inset-0 bg-primary-500/10 blur-xl"></div>
                          <div className="text-3xl font-black text-primary-400 mb-1 relative z-10">{result.retrieval_trace.citation_count || 0}</div>
                          <div className="text-[10px] font-bold text-primary-500/70 uppercase tracking-widest relative z-10">Citations Used</div>
                        </div>
                        <div className="p-5 rounded-2xl bg-black/40 border border-[#222] flex flex-col items-center justify-center text-center shadow-inner md:col-span-2">
                          <div className="text-lg font-black text-zinc-300 mb-1 truncate w-full px-2">{String(result.retrieval_trace.mode || 'N/A').replace(/_/g, ' ')}</div>
                          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Retrieval Mode</div>
                        </div>
                        {result.retrieval_trace.context_chars_before_packing && (
                          <div className="p-5 rounded-2xl bg-black/40 border border-emerald-900/30 flex flex-col justify-center shadow-inner md:col-span-4">
                            <div className="flex justify-between items-end mb-3">
                              <div className="text-[10px] font-bold text-emerald-500/80 uppercase tracking-widest">Token Optimization via Context Engineering</div>
                              <div className="text-xl font-black text-emerald-400">-{result.retrieval_trace.context_chars_saved?.toLocaleString()} chars</div>
                            </div>
                            <div className="w-full bg-zinc-900 rounded-full h-1.5 overflow-hidden">
                              <div 
                                className="bg-emerald-500 h-full rounded-full" 
                                style={{ width: `${Math.min(100, Math.max(0, ((result.retrieval_trace.context_chars_saved || 0) / (result.retrieval_trace.context_chars_before_packing || 1)) * 100))}%` }}
                              ></div>
                            </div>
                            <div className="flex justify-between mt-2 text-[10px] text-zinc-500 font-mono">
                              <span>Raw Text: {result.retrieval_trace.context_chars_before_packing?.toLocaleString()}c</span>
                              <span>Packed: {result.retrieval_trace.context_chars_after_packing?.toLocaleString()}c</span>
                            </div>
                          </div>
                        )}
                      </div>

                      <details className="mt-6 group">
                        <summary className="text-xs font-mono font-bold text-zinc-600 cursor-pointer hover:text-zinc-400 transition-colors list-none flex items-center gap-2">
                          <ChevronRight size={14} className="group-open:rotate-90 transition-transform" /> View Raw JSON Trace
                        </summary>
                        <pre className="mt-3 p-6 rounded-2xl bg-[#0a0a0a] border border-[#222] text-[10px] font-mono text-zinc-500 overflow-x-auto custom-scrollbar shadow-inner">
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
