import { useCallback, useEffect, useState, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Tag, RefreshCw, Trash2, FolderOpen, BrainCircuit, Edit2, Save, X, ChevronDown, ChevronUp, FileText } from 'lucide-react'
import { api, type Note, type Directory } from '../../lib/api'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { TagSearchSelect } from './TagSearchSelect'
import rehypeRaw from 'rehype-raw'
export function NoteDetailView({ token }: { token: string }) {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [note, setNote] = useState<Note | null>(null)
  const [directory, setDirectory] = useState<Directory | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchParams] = useSearchParams()

  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState('')

  const [isExpanded, setIsExpanded] = useState(false)
  const innerRef = useRef<HTMLDivElement>(null)
  const [canExpand, setCanExpand] = useState(false)
  
  useEffect(() => {
    if (!innerRef.current) return
    const el = innerRef.current
    
    let isActive = true
    const checkHeight = () => {
      if (!isActive || !el) return
      const contentEl = el.firstElementChild || el
      if (contentEl.scrollHeight > 350 || el.scrollHeight > 350) {
        setCanExpand(true)
      }
    }

    const observer = new ResizeObserver(() => checkHeight())
    observer.observe(el)
    if (el.firstElementChild) {
      observer.observe(el.firstElementChild)
    }
    
    checkHeight()
    // Aggressive polling for the first 2 seconds to catch any late layout shifts
    const interval = setInterval(checkHeight, 100)
    const timeout = setTimeout(() => clearInterval(interval), 2000)
    
    return () => {
      isActive = false
      observer.disconnect()
      clearInterval(interval)
      clearTimeout(timeout)
    }
  }, [note, isEditing])

  const [editTagsVal, setEditTagsVal] = useState('')

  const highlightStart = parseInt(searchParams.get('start') || '-1', 10)
  const highlightEnd = parseInt(searchParams.get('end') || '-1', 10)
  const hasCitationTarget = highlightStart >= 0 && highlightEnd > highlightStart

  const load = useCallback(async () => {
    if (!id) return
    try {
      const { data } = await api<{ data: Note }>(`/api/v1/notes/${id}`, { token })
      setNote(data)
      setEditText(data.text)
      
      if (data.directory_id) {
        const { data: dirs } = await api<{ data: Directory[] }>('/api/v1/directories/', { token })
        const found = dirs.find(d => d.id === data.directory_id)
        if (found) setDirectory(found)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [id, token])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (note && hasCitationTarget) {
      setIsExpanded(true)
      setTimeout(() => {
        const el = document.getElementById('citation-highlight')
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          el.classList.add('bg-primary-500/60')
          setTimeout(() => el.classList.remove('bg-primary-500/60'), 2000)
        }
      }, 100)
    }
  }, [note, hasCitationTarget, highlightStart, highlightEnd])

  const renderNoteText = () => {
    if (!note) return null
    
    const isMarkdown = note.metadata?.extension === 'md' || note.metadata?.extension === 'markdown'
    
    if (isMarkdown) {
      let content = note.text
      if (highlightStart >= 0 && highlightEnd > highlightStart && highlightEnd <= note.text.length) {
        const before = note.text.slice(0, highlightStart)
        const highlight = note.text.slice(highlightStart, highlightEnd)
        const after = note.text.slice(highlightEnd)
        content = `${before}<mark id="citation-highlight" class="bg-primary-500/30 text-foreground rounded px-1 py-0.5 transition-colors duration-1000">${highlight}</mark>${after}`
      }
      return (
        <div className="prose dark:prose-invert max-w-none prose-pre:bg-input/50 prose-pre:border prose-pre:border-border/50">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {content}
          </ReactMarkdown>
        </div>
      )
    }

    if (highlightStart >= 0 && highlightEnd > highlightStart && highlightEnd <= note.text.length) {
      const before = note.text.slice(0, highlightStart)
      const highlight = note.text.slice(highlightStart, highlightEnd)
      const after = note.text.slice(highlightEnd)
      return (
        <div className="whitespace-pre-wrap">
          {before}
          <mark 
            id="citation-highlight" 
            className="bg-primary-500/30 text-foreground rounded px-1 py-0.5 transition-colors duration-1000"
          >
            {highlight}
          </mark>
          {after}
        </div>
      )
    }
    return <div className="whitespace-pre-wrap">{note.text}</div>
  }

  const handleSave = async () => {
    if (!note || !editText.trim()) return
    
    const tagNames = editTagsVal.split(',').filter(Boolean).map(v => {
      const parts = v.trim().split('|')
      const name = parts[1] ? decodeURIComponent(parts[1]) : parts[0]
      return name
    })

    try {
      await api(`/api/v1/notes/${note.id}`, {
        method: 'PUT',
        token,
        body: JSON.stringify({
          text: editText,
          tags: tagNames,
          directory_id: note.directory_id
        })
      })

      setIsEditing(false)
      load()
    } catch (err: any) {
      alert(err.message || 'Failed to update note')
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RefreshCw className="animate-spin text-primary-500" size={32} />
      </div>
    )
  }

  if (!note) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center pt-20">
        <h2 className="text-2xl font-bold mb-4">Note not found</h2>
        <button 
          onClick={() => navigate('/notes')}
          className="premium-btn premium-btn-secondary h-10 px-4 flex items-center gap-2"
        >
          <ArrowLeft size={16} /> Back to Notes
        </button>
      </div>
    )
  }

  return (
    <div className="app-page max-w-4xl">
      <section className="page-hero">
        <div className="page-hero-inner">
          <div className="page-hero-copy">
            <div className="page-hero-icon">
              <FileText size={24} />
            </div>
            <div>
              <p className="page-hero-kicker">{directory?.name || 'Root'}</p>
              <h1 className="page-hero-title">Source note</h1>
              <p className="page-hero-subtitle">
                Read, edit, and inspect the exact text Ask AI can cite.
              </p>
            </div>
          </div>
          <div className="page-hero-actions">
            <button
              onClick={() => navigate('/notes')}
              className="premium-btn premium-btn-secondary h-11 gap-2 px-4"
            >
              <ArrowLeft size={16} /> Back to Notes
            </button>
          </div>
        </div>
        <div className="page-stat-grid">
          <div className="page-stat-card">
            <span>Characters</span>
            <strong>{note.text.length.toLocaleString()}</strong>
            <small>source text size</small>
          </div>
          <div className="page-stat-card">
            <span>Tags</span>
            <strong>{note.tags.length}</strong>
            <small>attached labels</small>
          </div>
          <div className="page-stat-card">
            <span>Folder</span>
            <strong>{directory?.name || 'Root'}</strong>
            <small>organization context</small>
          </div>
          <div className="page-stat-card">
            <span>Citation</span>
            <strong>{hasCitationTarget ? 'Open' : 'None'}</strong>
            <small>{hasCitationTarget ? 'highlighted source span' : 'normal reading mode'}</small>
          </div>
        </div>
      </section>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bento-card p-8 md:p-12"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4 border-b border-border/50 pb-6">
          <div className="flex items-center gap-3 text-sm font-bold uppercase tracking-wider text-muted-foreground/80">
            <FolderOpen size={16} /> 
            {directory?.name || 'Root'}
          </div>
          <div className="flex items-center gap-3">
            {isEditing ? (
              <>
                <button 
                  className="flex items-center gap-2 h-10 px-4 rounded-lg bg-muted-foreground/10 text-muted-foreground hover:bg-muted-foreground/20 transition-colors text-sm font-bold"
                  onClick={() => {
                    setEditText(note.text)
                    setIsEditing(false)
                  }}
                >
                  <X size={16} /> Cancel
                </button>
                <button 
                  className="flex items-center gap-2 h-10 px-4 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm font-bold"
                  onClick={handleSave}
                >
                  <Save size={16} /> Save Changes
                </button>
              </>
            ) : (
              <>
                <button 
                  className="flex items-center gap-2 h-10 px-4 rounded-lg bg-primary-500/10 text-primary-500 hover:bg-primary-500 hover:text-white transition-colors text-sm font-bold"
                  onClick={() => {
                    setEditText(note.text)
                    setEditTagsVal(note.tags.map(t => `${t.id}|${encodeURIComponent(t.name)}`).join(', '))
                    setIsEditing(true)
                  }}
                >
                  <Edit2 size={16} /> Edit Note
                </button>
                <button 
                  className="flex items-center gap-2 h-10 px-4 rounded-lg bg-accent-500/10 text-accent-500 hover:bg-accent-500 hover:text-white transition-colors text-sm font-bold"
                  onClick={() => navigate(`/notes/${note.id}/insights`)}
                >
                  <BrainCircuit size={16} /> Insights
                </button>
                <button 
                  className="flex items-center gap-2 h-10 px-4 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white transition-colors text-sm font-bold"
                  onClick={async () => {
                    if (confirm('Delete this note?')) {
                      await api(`/api/v1/notes/${note.id}`, { method: 'DELETE', token })
                      navigate('/notes')
                    }
                  }}
                >
                  <Trash2 size={16} /> Delete Note
                </button>
              </>
            )}
          </div>
        </div>

        <div className="prose prose-lg dark:prose-invert max-w-none">
          {isEditing ? (
            <>
              <div className="mb-4">
                <TagSearchSelect 
                  label="Tags" 
                  mode="include" 
                  value={editTagsVal} 
                  onChange={setEditTagsVal} 
                  token={token} 
                  allowCreate={true}
                />
              </div>
              <textarea
                autoFocus
                className="w-full min-h-[300px] bg-transparent border border-border/50 rounded-xl p-4 text-lg leading-8 text-foreground/90 focus:ring-2 focus:ring-primary-500/50 outline-none resize-y"
                value={editText}
                onChange={e => setEditText(e.target.value)}
              />
            </>
          ) : (
            <div className="bg-card/40 backdrop-blur-sm border border-border/50 rounded-xl shadow-sm overflow-hidden flex flex-col">
              <div 
                className={`relative w-full overflow-hidden`}
                style={{ 
                  maxHeight: (hasCitationTarget || isExpanded) ? 'none' : 400,
                }}
              >
                <div ref={innerRef} className="p-6 overflow-x-auto">
                  {renderNoteText()}
                </div>
                {(canExpand && !isExpanded && !hasCitationTarget) && (
                  <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-card to-transparent pointer-events-none" />
                )}
              </div>
              
              {(canExpand && !hasCitationTarget) && (
                <div className="flex items-center justify-center gap-4 py-3 bg-card/80 backdrop-blur-md border-t border-border/50">
                  {isExpanded ? (
                    <button 
                      className="flex items-center justify-center w-10 h-10 rounded-full bg-muted-foreground/10 text-muted-foreground hover:bg-muted-foreground/20 hover:text-foreground transition-all"
                      onClick={() => {
                        setIsExpanded(false)
                        window.scrollTo({ top: 0, behavior: 'smooth' })
                      }}
                      title="Shrink"
                    >
                      <ChevronUp size={20} />
                    </button>
                  ) : (
                    <button 
                      className="flex items-center justify-center w-10 h-10 rounded-full bg-primary-500/10 text-primary-500 hover:bg-primary-500 hover:text-white transition-all shadow-[0_0_15px_rgba(var(--primary-500),0.1)]"
                      onClick={() => setIsExpanded(true)}
                      title="Expand"
                    >
                      <ChevronDown size={20} />
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mt-12 pt-6 border-t border-border/50 flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground font-semibold">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Tag size={16} /> {note.tags.length} Tags
            </div>
            {note.tags.length > 0 && (
              <div className="flex items-center gap-2">
                {note.tags.map(tag => (
                  <span key={tag.id} className="px-2 py-1 rounded-md bg-input text-xs uppercase tracking-widest">{tag.name}</span>
                ))}
              </div>
            )}
          </div>
          <div className="font-mono bg-input px-3 py-1.5 rounded-lg border border-border/50">
            {new Date(note.created_at).toLocaleString()}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
