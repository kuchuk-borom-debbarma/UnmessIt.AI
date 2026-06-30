import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Tag, RefreshCw, Trash2, FolderOpen, BrainCircuit } from 'lucide-react'
import { api, type Note, type Directory } from '../../lib/api'
import { motion } from 'framer-motion'

export function NoteDetailView({ token }: { token: string }) {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [note, setNote] = useState<Note | null>(null)
  const [directory, setDirectory] = useState<Directory | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!id) return
    try {
      const { data } = await api<{ data: Note }>(`/notes/${id}`, { token })
      setNote(data)
      
      if (data.directory_id) {
        const { data: dirs } = await api<{ data: Directory[] }>('/directories/', { token })
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
                  await api(`/notes/${note.id}`, { method: 'DELETE', token })
                  navigate('/notes')
                }
              }}
            >
              <Trash2 size={16} /> Delete Note
            </button>
          </div>
        </div>

        <div className="prose prose-lg dark:prose-invert max-w-none">
          <p className="text-lg leading-8 text-foreground/90 whitespace-pre-wrap">
            {note.text}
          </p>
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
