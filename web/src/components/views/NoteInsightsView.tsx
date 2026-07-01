import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Link as LinkIcon, RefreshCw, BrainCircuit, ChevronLeft, ChevronRight, Hash, Network } from 'lucide-react'
import { api } from '../../lib/api'
import { cn } from '../../lib/utils'
import { motion, AnimatePresence } from 'framer-motion'

type TabType = 'chunks' | 'keys' | 'links'

export function NoteInsightsView({ token }: { token: string }) {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [activeTab, setActiveTab] = useState<TabType>('chunks')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showLoading, setShowLoading] = useState(false)
  const [page, setPage] = useState(1)

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [activeTab, page])

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      let res;
      if (activeTab === 'chunks') {
        res = await api<any>(`/api/v1/advanced/notes/${id}/chunks?page=${page}&limit=10`, { token })
      } else if (activeTab === 'keys') {
        res = await api<any>(`/api/v1/advanced/notes/${id}/recall_keys?page=${page}&limit=20`, { token })
      } else {
        res = await api<any>(`/api/v1/advanced/notes/${id}/recall_links?page=${page}&limit=20`, { token })
      }
      setData(res.data || res)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [id, token, page, activeTab])

  useEffect(() => {
    load()
  }, [load])

  const handleTabChange = (tab: TabType) => {
    if (activeTab === tab) return
    setActiveTab(tab)
    setPage(1)
    setData(null)
  }

  const items = data ? (activeTab === 'chunks' ? data.chunks : activeTab === 'keys' ? data.keys : data.links) : []
  const totalPages = data ? Math.ceil(data.total / data.limit) : 1

  return (
    <div className="flex flex-col flex-1 h-full max-w-5xl mx-auto w-full pt-8 pb-32">
      <div className="mb-8">
        <button 
          onClick={() => navigate(`/notes/${id}`)}
          className="flex items-center gap-2 text-sm font-bold text-muted-foreground hover:text-foreground transition-colors w-fit"
        >
          <ArrowLeft size={16} /> Back to Note
        </button>
      </div>

      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-[1.2rem] bg-accent-500/10 text-accent-500 flex items-center justify-center shadow-inner">
            <BrainCircuit size={28} />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Note Insights</h1>
            <p className="text-muted-foreground font-medium">Explore the semantic data extracted from this note.</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-8 border-b border-border/50 pb-px">
        <button 
          onClick={() => handleTabChange('chunks')}
          className={cn("px-4 py-3 font-bold text-sm border-b-2 transition-colors flex items-center gap-2", activeTab === 'chunks' ? "border-accent-500 text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}
        >
          <Hash size={16} /> Semantic Chunks
        </button>
        <button 
          onClick={() => handleTabChange('keys')}
          className={cn("px-4 py-3 font-bold text-sm border-b-2 transition-colors flex items-center gap-2", activeTab === 'keys' ? "border-accent-500 text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}
        >
          <BrainCircuit size={16} /> Recall Keys
        </button>
        <button 
          onClick={() => handleTabChange('links')}
          className={cn("px-4 py-3 font-bold text-sm border-b-2 transition-colors flex items-center gap-2", activeTab === 'links' ? "border-accent-500 text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}
        >
          <Network size={16} /> Recall Links
        </button>
      </div>

      <div className="space-y-6">
        {loading && !data && showLoading && (
          <div className="flex-1 flex items-center justify-center pt-20">
            <RefreshCw className="animate-spin text-accent-500" size={32} />
          </div>
        )}

        {!loading && items.length === 0 && (
          <div className="text-center p-12 bento-card text-muted-foreground font-medium flex flex-col items-center">
            <BrainCircuit size={32} className="opacity-50 mb-4" />
            No {activeTab} extracted for this note yet.
          </div>
        )}

        <AnimatePresence mode="popLayout">
          {!loading && activeTab === 'chunks' && items.map((chunk: any) => (
            <motion.div 
              key={chunk.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bento-card p-6 border-l-4 border-l-primary-500/50 hover:border-l-primary-500 transition-colors"
            >
              <div className="text-sm text-foreground/90 leading-relaxed max-w-3xl font-medium">
                {chunk.text}
              </div>
              
              {chunk.recall_links && chunk.recall_links.length > 0 && (
                <div className="mt-5 pt-4 border-t border-border/50">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-accent-500 mb-3">
                    <LinkIcon size={14} /> Connected Recall Keys
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {chunk.recall_links.map((link: any) => (
                      <div 
                        key={link.id} 
                        className="px-3 py-1.5 rounded-lg bg-background border border-border/60 flex items-center gap-2 text-sm hover:border-accent-500/50 transition-colors"
                      >
                        <span className="font-bold text-accent-500/80 text-[10px] uppercase tracking-wider">{link.kind}</span>
                        <span className="font-medium text-foreground">{link.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          ))}

          {!loading && activeTab === 'keys' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {items.map((key: any) => (
                <motion.div 
                  key={key.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bento-card p-5 hover:border-accent-500/30 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <h3 className="font-bold text-lg">{key.name}</h3>
                    <span className="px-2 py-1 rounded-md bg-accent-500/10 text-accent-500 text-[10px] font-bold uppercase tracking-wider">
                      {key.kind}
                    </span>
                  </div>
                  {key.summary && (
                    <p className="text-sm text-muted-foreground line-clamp-2">{key.summary}</p>
                  )}
                </motion.div>
              ))}
            </div>
          )}

          {!loading && activeTab === 'links' && items.map((link: any) => (
            <motion.div 
              key={link.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bento-card p-5 flex flex-col md:flex-row md:items-center gap-4"
            >
              <div className="flex-1">
                <div className="text-sm text-muted-foreground line-clamp-2 italic border-l-2 border-border/50 pl-3 mb-3">
                  "{link.chunk_text}"
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-input flex items-center justify-center shrink-0">
                    <LinkIcon size={14} className="text-muted-foreground" />
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{link.relation}</span>
                    <span className="px-2.5 py-1 rounded-md bg-accent-500/10 text-accent-500 text-sm font-bold">
                      {link.key_name}
                    </span>
                  </div>
                </div>
              </div>
              {link.reason && (
                <div className="md:w-1/3 text-xs text-muted-foreground/80 bg-input p-3 rounded-lg">
                  {link.reason}
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {totalPages > 1 && (
        <div className="mt-10 flex items-center justify-center gap-4">
          <button 
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="h-10 px-4 rounded-lg bg-input border border-border/50 disabled:opacity-50 flex items-center gap-2 font-bold text-sm hover:bg-background transition-colors"
          >
            <ChevronLeft size={18} /> Prev
          </button>
          <span className="text-sm font-bold text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <button 
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            className="h-10 px-4 rounded-lg bg-input border border-border/50 disabled:opacity-50 flex items-center gap-2 font-bold text-sm hover:bg-background transition-colors"
          >
            Next <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  )
}
