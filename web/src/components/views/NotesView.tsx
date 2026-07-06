import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Plus, Tag, RefreshCw, Trash2, FolderOpen, FileText, Maximize2, FolderPlus, FolderMinus, ChevronRight, X, CheckCircle2, Clock3, AlertCircle, Pause, Edit2, FolderInput } from 'lucide-react'
import { api, type Note, type Directory } from '../../lib/api'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { TagSearchSelect } from './TagSearchSelect'
import { type JobEvent, type JobProgressEvent, type JobStatus, useIngestJobEvents } from '../../lib/ingestJobEvents'

type ApiPaginatedData<T> = { data: T, total: number, page: number, limit: number }

function MoveItemModal({ isOpen, onClose, currentDirId, allDirectories, onMove, itemName }: { isOpen: boolean, onClose: () => void, currentDirId: string | null, allDirectories: Directory[], onMove: (dirId: string | null) => void, itemName?: string }) {
  const [query, setQuery] = useState('')
  const filteredDirs = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return allDirectories
    return allDirectories.filter(d => d.path.toLowerCase().includes(normalized))
  }, [allDirectories, query])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-md bg-card border border-border/50 shadow-2xl rounded-2xl p-4 flex flex-col gap-4 max-h-[80vh]"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold">Move {itemName ? `"${itemName}"` : "Item"}</h3>
          <button onClick={onClose} className="p-2 text-muted-foreground hover:bg-muted rounded-full">
            <X size={16} />
          </button>
        </div>
        <div className="relative">
          <FolderInput size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
          <input
            autoFocus
            className="w-full bg-input/50 border border-border/50 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            placeholder="Search folders..."
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
        <div className="flex-1 overflow-y-auto min-h-[100px] max-h-[300px] flex flex-col gap-1 -mx-2 px-2">
          <button
            className={cn("text-left px-3 py-2 rounded-lg text-sm transition-colors hover:bg-primary-500/10 flex items-center gap-2", currentDirId === null ? "bg-primary-500/20 text-primary-500 font-bold" : "text-muted-foreground")}
            onClick={() => onMove(null)}
          >
            <FolderOpen size={14}/> Root Directory
          </button>
          {filteredDirs.map(d => (
            <button
              key={d.id}
              className={cn("text-left px-3 py-2 rounded-lg text-sm transition-colors hover:bg-primary-500/10 flex items-center gap-2", currentDirId === d.id ? "bg-primary-500/20 text-primary-500 font-bold" : "text-muted-foreground")}
              onClick={() => onMove(d.id)}
            >
              <FolderOpen size={14}/> 
              <span className="truncate flex-1">{d.name}</span>
              <span className="text-muted-foreground/30 text-xs ml-auto truncate max-w-[150px]">{d.path}</span>
            </button>
          ))}
          {filteredDirs.length === 0 && (
            <div className="text-center py-8 text-sm text-muted-foreground">No matching folders found.</div>
          )}
        </div>
      </motion.div>
    </div>
  )
}

const FolderCard = React.memo(function FolderCard({ dir, onSelect, onDelete, onRename }: { dir: Directory, onSelect: () => void, onDelete: () => void, onRename: (newName: string) => void }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState(dir.name)

  const handleSave = () => {
    if (editName.trim() && editName !== dir.name) {
      onRename(editName.trim())
    }
    setIsEditing(false)
  }

  return (
    <div 
      className="bento-card p-4 flex items-center justify-between cursor-pointer group hover:border-primary-500/50 transition-colors"
      onClick={() => { if (!isEditing) onSelect() }}
    >
      <div className="flex items-center gap-3 text-foreground/90 font-bold flex-1 mr-2">
        <FolderOpen size={18} className="text-primary-500 shrink-0" />
        {isEditing ? (
          <input 
            autoFocus
            className="premium-input h-8 py-0 w-full text-sm font-bold bg-background"
            value={editName}
            onChange={e => setEditName(e.target.value)}
            onBlur={handleSave}
            onKeyDown={e => {
              if (e.key === 'Enter') handleSave()
              if (e.key === 'Escape') {
                setEditName(dir.name)
                setIsEditing(false)
              }
            }}
            onClick={e => e.stopPropagation()}
          />
        ) : (
          <span className="truncate">{dir.name}</span>
        )}
      </div>
      {!isEditing && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-primary-500/10 hover:text-primary-500 transition-colors"
            onClick={(e) => {
              e.stopPropagation()
              setEditName(dir.name)
              setIsEditing(true)
            }}
            title="Rename Folder"
          >
            <Edit2 size={14} />
          </button>
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
      )}
    </div>
  )
})

const NoteCard = React.memo(function NoteCard({ note, directoryName, allDirectories, token, load }: { note: Note, directoryName: string, allDirectories: Directory[], token: string, load: () => void }) {
  const navigate = useNavigate()
  const isLong = note.text.length > 400 || note.text.split('\n').length > 8
  const [isMoving, setIsMoving] = useState(false)

  const handleMove = async (newDirId: string | null) => {
    try {
      await api(`/api/v1/notes/${note.id}`, {
        method: 'PUT',
        token,
        body: JSON.stringify({
          text: note.text,
          tags: note.tags.map(t => t.name),
          directory_id: newDirId
        })
      })
      setIsMoving(false)
      load()
    } catch (err: any) {
      alert(err.message || 'Failed to move note')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="bento-card min-h-[260px] p-5 flex flex-col group relative cursor-pointer hover:border-primary-500/50 transition-colors"
      onClick={() => navigate(`/notes/${note.id}`)}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground/70 flex-1 min-w-0 pr-2">
          <FolderOpen size={14} className="shrink-0" /> 
          <span className="truncate">{directoryName}</span>
          
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
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-primary-500/10 hover:text-primary-500 transition-colors"
            onClick={(e) => {
              e.stopPropagation()
              setIsMoving(true)
            }}
            title="Move Note"
          >
            <FolderInput size={14} />
          </button>
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-primary-500/10 hover:text-primary-500 transition-colors"
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
              await api(`/api/v1/notes/${note.id}`, { method: 'DELETE', token })
              load()
            }}
            title="Move to Trash"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="relative min-h-0 flex-1">
        <p className={cn(
          "text-sm leading-6 text-foreground/90 whitespace-pre-wrap transition-all duration-300",
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
      <MoveItemModal
        isOpen={isMoving}
        onClose={() => setIsMoving(false)}
        currentDirId={note.directory_id}
        allDirectories={allDirectories}
        onMove={handleMove}
        itemName="Note"
      />
    </motion.div>
  )
})

function NoteTypeModal({ isOpen, onClose, onSelectUpload, onSelectManual }: { isOpen: boolean, onClose: () => void, onSelectUpload: (files: File[]) => void, onSelectManual: () => void }) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      onSelectUpload(files);
      // Reset the input so the same file can be selected again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="w-full max-w-md bg-card border border-border/50 shadow-2xl rounded-3xl p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold">New Note</h3>
              <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/5 transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="bento-card p-6 flex flex-col items-center justify-center gap-4 hover:border-primary-500/50 transition-colors group"
              >
                <div className="w-12 h-12 rounded-full bg-primary-500/10 flex items-center justify-center text-primary-500 group-hover:scale-110 transition-transform">
                  <FileText size={24} />
                </div>
                <div className="text-center">
                  <div className="font-bold mb-1">Upload File</div>
                  <div className="text-xs text-muted-foreground">.txt or .md</div>
                </div>
              </button>
              
              <button
                onClick={onSelectManual}
                className="bento-card p-6 flex flex-col items-center justify-center gap-4 hover:border-primary-500/50 transition-colors group"
              >
                <div className="w-12 h-12 rounded-full bg-primary-500/10 flex items-center justify-center text-primary-500 group-hover:scale-110 transition-transform">
                  <Edit2 size={24} />
                </div>
                <div className="text-center">
                  <div className="font-bold mb-1">Create Manually</div>
                  <div className="text-xs text-muted-foreground">Text Editor</div>
                </div>
              </button>
            </div>
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileChange} 
                className="hidden" 
                accept=".txt,.md,.markdown"
                multiple
              />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function NoteCreationModal({ isOpen, onClose, token, allDirectories, selectedDir, onSuccess }: { isOpen: boolean, onClose: () => void, token: string, allDirectories: Directory[], selectedDir: string | null, onSuccess: () => void }) {
  const [draft, setDraft] = useState('')
  const [draftDir, setDraftDir] = useState<string>(selectedDir || '')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [format, setFormat] = useState<'md' | 'txt'>('md')
  
  useEffect(() => {
    if (isOpen) {
      setDraftDir(selectedDir || '')
      setDraft('')
      setTags([])
      setTagInput('')
      setFormat('md')
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
      await api('/api/v1/notes/', {
        method: 'POST',
        token,
        body: JSON.stringify({
          text: draft,
          directory_id: draftDir || null,
          tags: tags,
          metadata: {
            extension: format
          }
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
              <div className="flex flex-col sm:flex-row gap-4">
                <select 
                  className="premium-input w-48 h-10 py-0 bg-background border-border/50"
                  value={draftDir}
                  onChange={e => setDraftDir(e.target.value)}
                >
                  <option value="">Root Directory</option>
                  {allDirectories.map(d => <option key={d.id} value={d.id}>{d.path}</option>)}
                </select>
                <select
                  className="premium-input w-32 h-10 py-0 bg-background border-border/50"
                  value={format}
                  onChange={e => setFormat(e.target.value as 'md' | 'txt')}
                >
                  <option value="md">Markdown</option>
                  <option value="txt">Plain Text</option>
                </select>
              </div>
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
  const loadSeq = useRef(0)
  
  // Navigation State
  
  const filterTagVal = searchParams.get('tag_val') || ''
  const filterTagMode = (searchParams.get('tag_mode') as 'any' | 'all') || 'any'
  
  const handleSelectTag = (val: string) => {
    const next = new URLSearchParams(searchParams)
    if (val) {
      next.set('tag_val', val)
    } else {
      next.delete('tag_val')
    }
    setSearchParams(next)
    setNotePage(1)
  }

  const handleTagModeChange = (val: 'any' | 'all') => {
    const next = new URLSearchParams(searchParams)
    next.set('tag_mode', val)
    setSearchParams(next)
    setNotePage(1)
  }

  const filterTagIds = filterTagVal 
    ? filterTagVal.split(',').map(t => t.split('|')[0].trim()).filter(Boolean).join(',') 
    : null

  const selectedDir = searchParams.get('dir')

  const handleSelectDir = (dirId: string | null) => {
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
  const [dirPage, setDirPage] = useState(1)
  const [dirTotal, setDirTotal] = useState(0)
  const noteLimit = 50
  const dirLimit = 50

  // UI State
  const [isCreatingFolder, setIsCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [isSelectingType, setIsSelectingType] = useState(false)
  const [isComposing, setIsComposing] = useState(false)
  
  // Upload Handler
  const handleUploadFile = async (files: File[]) => {
    setIsSelectingType(false)
    for (const file of files) {
      const reader = new FileReader()
      await new Promise<void>((resolve) => {
        reader.onload = async (e) => {
          const text = e.target?.result as string
          if (!text.trim()) {
            console.warn(`File ${file.name} is empty!`)
            resolve()
            return
          }
          const extension = file.name.split('.').pop()
          try {
            await api('/api/v1/notes/', {
              method: 'POST',
              token,
              body: JSON.stringify({
                text: text,
                directory_id: selectedDir || null,
                tags: [],
                metadata: {
                  filename: file.name,
                  extension: extension,
                }
              })
            })
          } catch (err: any) {
            console.error(`Failed to upload note ${file.name}:`, err)
          }
          resolve()
        }
        reader.onerror = () => resolve()
        reader.readAsText(file)
      })
    }
    load()
  }

  const loadAllDirectories = useCallback(async () => {
    try {
      const allD = await api<ApiPaginatedData<Directory[]>>(`/api/v1/directories/?all=true&limit=1000`, { token })
      setAllDirectories(allD.data)
    } catch (err) {
      console.error(err)
    }
  }, [token])

  const load = useCallback(async () => {
    const seq = loadSeq.current + 1
    loadSeq.current = seq
    try {
      const parentQuery = selectedDir ? `&directory_id=${selectedDir}` : ''
      const tagQuery = filterTagIds ? `&tag_ids=${filterTagIds}&tag_mode=${filterTagMode}` : ''
      const dirParentQuery = selectedDir ? `&parent_id=${selectedDir}` : ''

      const [n, d] = await Promise.all([
        api<ApiPaginatedData<Note[]>>(`/api/v1/notes/?page=${notePage}&limit=${noteLimit}${parentQuery}${tagQuery}`, { token }),
        api<ApiPaginatedData<Directory[]>>(`/api/v1/directories/?page=${dirPage}&limit=${dirLimit}${dirParentQuery}`, { token }),
      ])
      if (seq !== loadSeq.current) return
      setNotes(n.data)
      setNoteTotal(n.total)
      setDirectories(d.data)
      setDirTotal(d.total)
    } catch (err) {
      console.error(err)
    } finally {
      if (seq === loadSeq.current) setLoading(false)
    }
  }, [token, selectedDir, filterTagIds, filterTagMode, notePage, noteLimit, dirPage, dirLimit])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    void loadAllDirectories()
  }, [loadAllDirectories])

  const setNoteStatus = useCallback((noteId: string, status: JobStatus) => {
    setNotes(current => current.map(note => note.id === noteId ? { ...note, job_status: status } : note))
  }, [])

  useIngestJobEvents(token, {
    onJob: (data: JobEvent) => setNoteStatus(data.job.id, data.job.status),
    onProgress: (data: JobProgressEvent) => setNoteStatus(data.job_id, data.status),
    onError: err => console.error('Ingest job event stream failed:', err),
  })

  // Resolve breadcrumbs
  const allDirectoriesById = useMemo(() => new Map(allDirectories.map(dir => [dir.id, dir])), [allDirectories])

  const breadcrumbs = useMemo(() => {
    const next: Directory[] = []
    if (!selectedDir) return next
    let curr = allDirectoriesById.get(selectedDir)
    while (curr) {
      next.unshift(curr)
      curr = curr.parent_id ? allDirectoriesById.get(curr.parent_id) : undefined
    }
    return next
  }, [allDirectoriesById, selectedDir])

  // Modal handles this now

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return
    try {
      await api('/api/v1/directories/', {
        method: 'POST',
        token,
        body: JSON.stringify({
          name: newFolderName,
          parent_id: selectedDir || null
        })
      })
      setNewFolderName('')
      setIsCreatingFolder(false)
      await loadAllDirectories()
      await load()
    } catch (err: any) {
      alert(err.message || 'Failed to create folder')
    }
  }

  const handleRenameFolder = async (dirId: string, newName: string) => {
    try {
      await api(`/api/v1/directories/${dirId}`, {
        method: 'PUT',
        token,
      body: JSON.stringify({ name: newName })
      })
      await loadAllDirectories()
      await load()
    } catch (err: any) {
      alert(err.message || 'Failed to rename folder')
    }
  }

  const handleDeleteFolder = async (dirId: string) => {
    if (confirm('Delete this folder and ALL notes inside it permanently?')) {
      try {
        await api(`/api/v1/directories/${dirId}`, { method: 'DELETE', token })
        if (selectedDir === dirId) {
          await loadAllDirectories()
          handleSelectDir(null)
        } else {
          await loadAllDirectories()
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
    <div className="app-page max-w-7xl">
      <section className="page-hero">
        <div className="page-hero-inner">
          <div className="page-hero-copy">
            <div className="page-hero-icon">
              <FileText size={24} />
            </div>
            <div>
              <p className="page-hero-kicker">Knowledge Base</p>
              <h1 className="page-hero-title">Capture, append, and organize memory.</h1>
              <p className="page-hero-subtitle">
                Notes are indexed as source chunks, vectors, folder paths, and recall links so fresh edits stay searchable.
              </p>
            </div>
          </div>

          <div className="page-hero-actions">
            <button
              className="icon-btn h-12 w-12 text-muted-foreground hover:bg-red-500/10 hover:text-red-500"
              onClick={() => navigate('/trash')}
              title="View Trash"
            >
              <Trash2 size={20} />
            </button>
            <button
              className="premium-btn premium-btn-primary h-12 px-6 gap-2"
              onClick={() => {
                setIsSelectingType(true)
              }}
            >
              <Plus size={18} /> New Note
            </button>
          </div>
        </div>
        <div className="page-stat-grid">
          <div className="page-stat-card">
            <span>Notes</span>
            <strong>{noteTotal.toLocaleString()}</strong>
            <small>current folder scope</small>
          </div>
          <div className="page-stat-card">
            <span>Folders</span>
            <strong>{dirTotal.toLocaleString()}</strong>
            <small>visible at this level</small>
          </div>
          <div className="page-stat-card">
            <span>Indexed</span>
            <strong>{notes.filter(note => note.job_status === 'complete').length.toLocaleString()}</strong>
            <small>loaded notes ready for Ask</small>
          </div>
          <div className="page-stat-card">
            <span>Filter</span>
            <strong>{filterTagVal ? 'On' : 'Off'}</strong>
            <small>tag-aware note browsing</small>
          </div>
        </div>
      </section>

      {/* Breadcrumbs & Folder Actions */}
      <div className="app-toolbar flex items-center justify-between">
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

      
      <div className="z-20 relative max-w-sm">
        <TagSearchSelect
          label="Filter by Tag"
          mode="include"
          value={filterTagVal}
          onChange={handleSelectTag}
          condition={filterTagMode}
          onConditionChange={handleTagModeChange}
          token={token}
        />
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
                onRename={(newName) => handleRenameFolder(d.id, newName)}
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
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <AnimatePresence>
          {notes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              directoryName={note.directory_id ? allDirectoriesById.get(note.directory_id)?.name || 'Folder' : 'Root'}
              allDirectories={allDirectories}
              token={token}
              load={load}
            />
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
      <NoteTypeModal
        isOpen={isSelectingType}
        onClose={() => setIsSelectingType(false)}
        onSelectUpload={handleUploadFile}
        onSelectManual={() => {
          setIsSelectingType(false)
          setIsComposing(true)
        }}
      />
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
