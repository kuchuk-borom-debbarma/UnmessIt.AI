import React, { useCallback, useEffect, useState } from 'react'
import { Plus, Tag, RefreshCw, Trash2, FolderOpen, FileText, Maximize2, FolderPlus, FolderMinus, ChevronRight, X, CheckCircle2, Clock3, AlertCircle, Pause } from 'lucide-react'
import { API_BASE, api, type Note, type Directory } from '../../lib/api'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils'
import { useNavigate, useSearchParams } from 'react-router-dom'

type ApiPaginatedData<T> = { data: T, total: number, page: number, limit: number }
type JobStatus = NonNullable<Note['job_status']>
type JobEvent = { job: { id: string; status: JobStatus } }
type JobProgressEvent = { job_id: string; status: JobStatus }

const FolderCard = React.memo(function FolderCard({ dir, onSelect, onDelete }: { dir: Directory, onSelect: () => void, onDelete: () => void }) {
  return (
    <div 
      className="bento-card p-4 flex items-center justify-between cursor-pointer group hover:border-primary-500/50 transition-colors"
      onClick={onSelect}
    >
      <div className="flex items-center gap-3 text-foreground/90 font-bold">
        <FolderOpen size={18} className="text-primary-500" />
        {dir.name}
      </div>
      <button 
        className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-colors"
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        title="Delete Folder"
      >
        <FolderMinus size={14} />
      </button>
    </div>
  )
})

const NoteCard = React.memo(function NoteCard({ note, allDirectories, token, load }: { note: Note, allDirectories: Directory[], token: string, load: () => void }) {
  const navigate = useNavigate()
  const isLong = note.text.length > 400 || note.text.split('\n').length > 8

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="bento-card break-inside-avoid p-6 flex flex-col group relative cursor-pointer hover:border-primary-500/50 transition-colors"
      onClick={() => navigate(`/notes/${note.id}`)}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground/70">
          <FolderOpen size={14} /> 
          {allDirectories.find(d => d.id === note.directory_id)?.name || 'Root'}
          
          {note.job_status && (
            <div className="flex items-center gap-1 ml-2 border-l border-border/50 pl-2">
              {note.job_status === 'complete' && <span title="Indexed"><CheckCircle2 className="text-primary-500" size={14} /></span>}
              {note.job_status === 'failed' && <span title="Index Failed"><AlertCircle className="text-red-500" size={14} /></span>}
              {note.job_status === 'aborted' && <span title="Index Aborted"><AlertCircle className="text-red-500" size={14} /></span>}
              {note.job_status === 'running' && <span title="Indexing"><RefreshCw className="animate-spin text-amber-500" size={14} /></span>}
              {note.job_status === 'queued' && <span title="Queued for index"><Clock3 className="text-muted-foreground" size={14} /></span>}
              {note.job_status === 'waiting_retry' && <span title="Waiting Retry"><Clock3 className="text-amber-500" size={14} /></span>}
              {note.job_status === 'paused' && <span title="Paused"><Pause className="text-muted-foreground" size={14} /></span>}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-primary-500/10 hover:text-primary-500"
            onClick={(e) => {
              e.stopPropagation()
              navigate(`/notes/${note.id}`)
            }}
            title="Expand Note"
          >
            <Maximize2 size={14} />
          </button>
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/10 hover:text-red-500"
            onClick={async (e) => {
              e.stopPropagation()
              await api(`/notes/${note.id}`, { method: 'DELETE', token })
              load()
            }}
            title="Move to Trash"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="relative flex-1">
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

      <div className="mt-6 pt-4 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Tag size={12} /> {note.tags.length} Tags
        </div>
        <div className="font-mono">
          {new Date(note.created_at).toLocaleDateString()}
        </div>
      </div>
    </motion.div>
  )
})

function NoteCreationModal({ isOpen, onClose, token, allDirectories, selectedDir, onSuccess }: { isOpen: boolean, onClose: () => void, token: string, allDirectories: Directory[], selectedDir: string | null, onSuccess: () => void }) {
  const [draft, setDraft] = useState('')
  const [draftDir, setDraftDir] = useState<string>(selectedDir || '')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  
  useEffect(() => {
    if (isOpen) {
      setDraftDir(selectedDir || '')
      setDraft('')
      setTags([])
      setTagInput('')
    }
  }, [isOpen, selectedDir])

  const handleAddTag = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const newTag = tagInput.trim().toLowerCase()
      if (newTag && !tags.includes(newTag)) {
        setTags([...tags, newTag])
      }
      setTagInput('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(t => t !== tagToRemove))
  }

  const handleCreateNote = async () => {
    if (!draft.trim()) return
    try {
      await api('/notes/', {
        method: 'POST',
        token,
        body: JSON.stringify({
          text: draft,
          directory_id: draftDir || null,
          tags: tags
        })
      })
      onSuccess()
      onClose()
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="w-full max-w-2xl bg-card border border-border/50 shadow-2xl rounded-[2rem] overflow-hidden"
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold">New Note</h3>
                <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/5 transition-colors">
                  <X size={18} />
                </button>
              </div>
              
              <div className="flex flex-col flex-1 h-[250px] relative">
                <textarea
                  autoFocus
                  className="w-full flex-1 bg-transparent border-none focus:ring-0 text-xl font-medium placeholder:text-muted-foreground/40 resize-none pb-4"
                  placeholder="Start typing your thoughts..."
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                />
                
                <div className="border-t border-border/50 pt-3 flex flex-col gap-2">
                  <div className="flex flex-wrap gap-2">
                    {tags.map(tag => (
                      <span key={tag} className="flex items-center gap-1 px-2 py-1 rounded-md bg-primary-500/10 text-primary-500 text-xs uppercase tracking-widest font-bold">
                        {tag}
                        <button onClick={() => handleRemoveTag(tag)} className="hover:text-primary-400 focus:outline-none">
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Tag size={16} />
                    <input
                      type="text"
                      className="bg-transparent border-none focus:ring-0 text-sm placeholder:text-muted-foreground/50 w-full"
                      placeholder="Add tags (press Enter or comma to add)..."
                      value={tagInput}
                      onChange={e => setTagInput(e.target.value)}
                      onKeyDown={handleAddTag}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-input/50 p-4 border-t border-border/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <select 
                className="premium-input w-48 h-10 py-0 bg-background border-border/50"
                value={draftDir}
                onChange={e => setDraftDir(e.target.value)}
              >
                <option value="">Root Directory</option>
                {allDirectories.map(d => <option key={d.id} value={d.id}>{d.path}</option>)}
              </select>
              <div className="flex gap-2">
                <button className="premium-btn premium-btn-secondary h-10 px-4" onClick={onClose}>Cancel</button>
                <button className="premium-btn premium-btn-primary h-10 px-6" onClick={handleCreateNote}>Save Note</button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

export function NotesView({ token }: { token: string }) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  
  // Navigation State
  const selectedDir = searchParams.get('dir')

  const handleSelectDir = (dirId: string | null) => {
    // Clear lists to prevent seeing old data
    setNotes([])
    setDirectories([])
    
    if (dirId) {
      setSearchParams({ dir: dirId })
    } else {
      setSearchParams({})
    }
    setDirPage(1)
    setNotePage(1)
  }
  
  // Data State
  const [notes, setNotes] = useState<Note[]>([])
  const [directories, setDirectories] = useState<Directory[]>([])
  const [allDirectories, setAllDirectories] = useState<Directory[]>([])
  const [loading, setLoading] = useState(true)
  
  // Pagination State
  const [notePage, setNotePage] = useState(1)
  const [noteTotal, setNoteTotal] = useState(0)
  const noteLimit = 20
  
  const [dirPage, setDirPage] = useState(1)
  const [dirTotal, setDirTotal] = useState(0)
  const dirLimit = 20
  
  // UI State
  const [isComposing, setIsComposing] = useState(false)
  
  const [isCreatingFolder, setIsCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')

  const load = useCallback(async () => {
    try {
      const parentQuery = selectedDir ? `&directory_id=${selectedDir}` : ''
      const dirParentQuery = selectedDir ? `&parent_id=${selectedDir}` : ''

      const [n, d, allD] = await Promise.all([
        api<ApiPaginatedData<Note[]>>(`/notes/?page=${notePage}&limit=${noteLimit}${parentQuery}`, { token }),
        api<ApiPaginatedData<Directory[]>>(`/directories/?page=${dirPage}&limit=${dirLimit}${dirParentQuery}`, { token }),
        api<ApiPaginatedData<Directory[]>>(`/directories/?all=true&limit=1000`, { token })
      ])
      setNotes(n.data)
      setNoteTotal(n.total)
      setDirectories(d.data)
      setDirTotal(d.total)
      setAllDirectories(allD.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [token, selectedDir, notePage, noteLimit, dirPage, dirLimit])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    const controller = new AbortController()
    let retryTimer: number | undefined
    const setNoteStatus = (noteId: string, status: JobStatus) => {
      setNotes(current => current.map(note => note.id === noteId ? { ...note, job_status: status } : note))
    }
    const connect = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/advanced/ingest_jobs/events`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        })
        if (!response.body) return
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (!controller.signal.aborted) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split('\n\n')
          buffer = events.pop() || ''
          for (const block of events) {
            const event = block.split('\n').find(line => line.startsWith('event: '))?.slice(7)
            const rawData = block.split('\n').find(line => line.startsWith('data: '))?.slice(6)
            if (!rawData) continue
            if (event === 'job') {
              const data = JSON.parse(rawData) as JobEvent
              setNoteStatus(data.job.id, data.job.status)
            }
            if (event === 'job_progress') {
              const data = JSON.parse(rawData) as JobProgressEvent
              setNoteStatus(data.job_id, data.status)
            }
          }
        }
      } catch {
        if (!controller.signal.aborted) retryTimer = window.setTimeout(connect, 5000)
      }
    }
    void connect()
    return () => {
      controller.abort()
      if (retryTimer) clearTimeout(retryTimer)
    }
  }, [token])

  // Resolve breadcrumbs
  const breadcrumbs = []
  if (selectedDir) {
    let curr = allDirectories.find(d => d.id === selectedDir)
    while (curr) {
      breadcrumbs.unshift(curr)
      curr = allDirectories.find(d => d.id === curr!.parent_id)
    }
  }

  // Modal handles this now

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return
    try {
      await api('/directories/', {
        method: 'POST',
        token,
        body: JSON.stringify({
          name: newFolderName,
          parent_id: selectedDir || null
        })
      })
      setNewFolderName('')
      setIsCreatingFolder(false)
      await load()
    } catch (err: any) {
      alert(err.message || 'Failed to create folder')
    }
  }

  const handleDeleteFolder = async (dirId: string) => {
    if (confirm('Delete this folder and ALL notes inside it permanently?')) {
      try {
        await api(`/directories/${dirId}`, { method: 'DELETE', token })
        if (selectedDir === dirId) {
          handleSelectDir(null)
        } else {
          await load()
        }
      } catch (err: any) {
        alert(err.message || 'Failed to delete folder')
      }
    }
  }

  if (loading && notePage === 1 && dirPage === 1) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RefreshCw className="animate-spin text-primary-500" size={32} />
      </div>
    )
  }

  const noteTotalPages = Math.ceil(noteTotal / noteLimit)
  const dirTotalPages = Math.ceil(dirTotal / dirLimit)

  return (
    <div className="flex flex-col flex-1 h-full max-w-7xl mx-auto w-full pt-8 pb-20 relative">
      
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2">Knowledge Base</h1>
          <p className="text-muted-foreground font-medium">Capture, organize, and search your raw thoughts.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            className="w-12 h-12 flex items-center justify-center rounded-xl liquid-glass text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors"
            onClick={() => navigate('/trash')}
            title="View Trash"
          >
            <Trash2 size={20} />
          </button>
          <button 
            className="premium-btn premium-btn-primary h-12 px-6 gap-2"
            onClick={() => {
              setIsComposing(true)
            }}
          >
            <Plus size={18} /> New Note
          </button>
        </div>
      </div>

      {/* Breadcrumbs & Folder Actions */}
      <div className="flex items-center justify-between mb-8 p-4 liquid-glass rounded-2xl">
        <div className="flex items-center gap-2 overflow-x-auto whitespace-nowrap">
          <button 
            className="flex items-center gap-2 font-bold text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => handleSelectDir(null)}
          >
            <FolderOpen size={16} /> Root
          </button>
          
          {breadcrumbs.map((b, idx) => {
            const isLast = idx === breadcrumbs.length - 1;
            return (
              <div key={b.id} className="flex items-center gap-2">
                <ChevronRight size={16} className="text-muted-foreground/50" />
                <button 
                  className={cn(
                    "font-bold transition-colors hover:text-primary-400",
                    isLast ? "text-primary-500" : "text-muted-foreground hover:text-foreground"
                  )}
                  onClick={() => handleSelectDir(b.id)}
                >
                  {b.name}
                </button>
                {isLast && (
                  <button 
                    className="w-6 h-6 flex items-center justify-center rounded-md text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-colors ml-1"
                    onClick={() => handleDeleteFolder(b.id)}
                    title="Delete Current Folder"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            )
          })}
        </div>

        <div className="flex items-center gap-2 ml-4">
          {isCreatingFolder ? (
            <div className="flex items-center gap-2">
              <input
                autoFocus
                className="premium-input h-8 py-0 w-40 text-sm"
                placeholder="Folder name..."
                value={newFolderName}
                onChange={e => setNewFolderName(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleCreateFolder()
                  if (e.key === 'Escape') setIsCreatingFolder(false)
                }}
              />
              <button className="text-xs font-bold text-muted-foreground hover:text-foreground" onClick={() => setIsCreatingFolder(false)}>Cancel</button>
              <button className="text-xs font-bold text-primary-500 hover:text-primary-400" onClick={handleCreateFolder}>Create</button>
            </div>
          ) : (
            <button 
              className="flex items-center gap-1 text-xs font-bold text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setIsCreatingFolder(true)}
            >
              <FolderPlus size={14} /> New Folder
            </button>
          )}
        </div>
      </div>

      {/* Folders Grid */}
      {directories.length > 0 && (
        <div className="mb-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {directories.map(d => (
              <FolderCard 
                key={d.id} 
                dir={d} 
                onSelect={() => handleSelectDir(d.id)} 
                onDelete={() => handleDeleteFolder(d.id)} 
              />
            ))}
          </div>
          {dirTotalPages > 1 && (
            <div className="flex items-center justify-end gap-4 mt-4">
              <button disabled={dirPage <= 1} onClick={() => setDirPage(p => p - 1)} className="text-xs font-bold disabled:opacity-50">Prev Folders</button>
              <span className="text-xs text-muted-foreground">{dirPage}/{dirTotalPages}</span>
              <button disabled={dirPage >= dirTotalPages} onClick={() => setDirPage(p => p + 1)} className="text-xs font-bold disabled:opacity-50">Next Folders</button>
            </div>
          )}
        </div>
      )}

      {/* Notes Grid */}
      <div className="columns-1 md:columns-2 xl:columns-3 gap-6 space-y-6">
        <AnimatePresence>
          {notes.map((note) => (
            <NoteCard key={note.id} note={note} allDirectories={allDirectories} token={token} load={load} />
          ))}
        </AnimatePresence>
        
        {notes.length === 0 && directories.length === 0 && (
          <div className="col-span-full py-20 text-center">
            <div className="inline-flex w-16 h-16 rounded-[2rem] bg-input items-center justify-center text-muted-foreground mb-4">
              <FileText size={24} />
            </div>
            <h3 className="text-xl font-bold mb-2">Folder is empty</h3>
            <p className="text-muted-foreground">Create a note or a subfolder to get started.</p>
          </div>
        )}
      </div>

      {noteTotalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-12 mb-8">
          <button disabled={notePage <= 1} onClick={() => setNotePage(p => p - 1)} className="premium-btn premium-btn-secondary px-6 disabled:opacity-50">Previous Notes</button>
          <span className="text-sm font-medium text-muted-foreground">Page {notePage} of {noteTotalPages}</span>
          <button disabled={notePage >= noteTotalPages} onClick={() => setNotePage(p => p + 1)} className="premium-btn premium-btn-secondary px-6 disabled:opacity-50">Next Notes</button>
        </div>
      )}

      {/* Note Creation Modal */}
      <NoteCreationModal
        isOpen={isComposing}
        onClose={() => setIsComposing(false)}
        token={token}
        allDirectories={allDirectories}
        selectedDir={selectedDir}
        onSuccess={load}
      />

    </div>
  )
}
