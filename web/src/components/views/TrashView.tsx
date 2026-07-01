import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, Trash2, FolderOpen, AlertCircle, RotateCcw } from 'lucide-react'
import { api, type Note, type Directory } from '../../lib/api'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils'

type ApiPaginatedData<T> = { data: T, total: number, page: number, limit: number }

function TrashCard({ note, directories, token, load }: { note: Note, directories: Directory[], token: string, load: () => void }) {
  const isLong = note.text.length > 400 || note.text.split('\n').length > 8

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="bento-card break-inside-avoid p-6 flex flex-col group relative bg-red-500/5 hover:border-red-500/50 transition-colors"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-red-500/70">
          <FolderOpen size={14} /> 
          {directories.find(d => d.id === note.directory_id)?.name || 'Root'}
        </div>
        <div className="flex items-center gap-2">
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-green-500/10 hover:text-green-500"
            onClick={async (e) => {
              e.stopPropagation()
              await api(`/api/v1/notes/${note.id}/restore`, { method: 'POST', token })
              load()
            }}
            title="Restore Note"
          >
            <RotateCcw size={14} />
          </button>
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/10 hover:text-red-500"
            onClick={async (e) => {
              e.stopPropagation()
              if (confirm('Permanently delete this note? This action cannot be undone.')) {
                await api(`/api/v1/notes/${note.id}/hard`, { method: 'DELETE', token })
                load()
              }
            }}
            title="Permanently Delete"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="relative flex-1 opacity-60">
        <p className={cn(
          "text-base text-foreground/90 whitespace-pre-wrap transition-all duration-300",
          isLong ? "line-clamp-[10]" : ""
        )}>
          {note.text}
        </p>
        
        {isLong && (
          <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-card to-transparent pointer-events-none" />
        )}
      </div>
    </motion.div>
  )
}

export function TrashView({ token }: { token: string }) {
  const [notes, setNotes] = useState<Note[]>([])
  const [directories, setDirectories] = useState<Directory[]>([])
  const [loading, setLoading] = useState(true)
  const [showLoading, setShowLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowLoading(true), 150)
    return () => clearTimeout(timer)
  }, [])
  
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20

  const load = useCallback(async () => {
    try {
      const [n, d] = await Promise.all([
        api<ApiPaginatedData<Note[]>>(`/api/v1/notes/trash?page=${page}&limit=${limit}`, { token }),
        api<{data: Directory[]}>('/api/v1/directories/?all=true', { token })
      ])
      setNotes(n.data)
      setTotal(n.total)
      setDirectories(d.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [token, page, limit])

  useEffect(() => {
    load()
  }, [load])

  if (loading && page === 1) {
    if (!showLoading) return null
    return (
      <div className="flex-1 flex items-center justify-center">
        <RefreshCw className="animate-spin text-primary-500" size={32} />
      </div>
    )
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="flex flex-col flex-1 h-full max-w-7xl mx-auto w-full pt-8">
      
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2 text-red-500">Trash</h1>
          <p className="text-muted-foreground font-medium">Recover or permanently delete your notes.</p>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="columns-1 md:columns-2 xl:columns-3 gap-6 space-y-6">
        <AnimatePresence>
          {notes.map((note) => (
            <TrashCard key={note.id} note={note} directories={directories} token={token} load={load} />
          ))}
        </AnimatePresence>
        
        {notes.length === 0 && (
          <div className="col-span-full py-20 text-center">
            <div className="inline-flex w-16 h-16 rounded-[2rem] bg-input items-center justify-center text-muted-foreground mb-4">
              <AlertCircle size={24} />
            </div>
            <h3 className="text-xl font-bold mb-2">Trash is empty</h3>
            <p className="text-muted-foreground">Nothing to see here.</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-12 mb-8">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="premium-btn premium-btn-secondary px-6 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm font-medium text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
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
