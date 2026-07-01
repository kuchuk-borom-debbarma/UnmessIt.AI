import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Tag, RefreshCw, Trash2, FolderOpen, BrainCircuit, Edit2, Save, X } from 'lucide-react'
import { api, type Note, type Directory } from '../../lib/api'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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

  const highlightStart = parseInt(searchParams.get('start') || '-1', 10)
  const highlightEnd = parseInt(searchParams.get('end') || '-1', 10)

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
    if (note && highlightStart >= 0) {
      setTimeout(() => {
        const el = document.getElementById('citation-highlight')
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          el.classList.add('bg-primary-500/60')
          setTimeout(() => el.classList.remove('bg-primary-500/60'), 2000)
        }
      }, 100)
    }
  }, [note, highlightStart])

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
    try {
      await api(`/api/v1/notes/${note.id}`, {
        method: 'PUT',
        token,
        body: JSON.stringify({
          text: editText,
          tags: note.tags.map(t => t.name),
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
    <div className="flex flex-col flex-1 h-full max-w-4xl mx-auto w-full pt-8 pb-32">
      
      <div className="mb-8">
        <button 
          onClick={() => navigate('/notes')}
          className="flex items-center gap-2 text-sm font-bold text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} /> Back to Notes
        </button>
      </div>

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
                  onClick={() => setIsEditing(true)}
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
            <textarea
              autoFocus
              className="w-full min-h-[300px] bg-transparent border border-border/50 rounded-xl p-4 text-lg leading-8 text-foreground/90 focus:ring-2 focus:ring-primary-500/50 outline-none resize-y"
              value={editText}
              onChange={e => setEditText(e.target.value)}
            />
          ) : (
            <div className="bg-card/40 backdrop-blur-sm border border-border/50 rounded-xl p-6 shadow-sm overflow-x-auto">
              {renderNoteText()}
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
