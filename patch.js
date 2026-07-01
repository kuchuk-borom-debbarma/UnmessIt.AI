const fs = require('fs');
const content = fs.readFileSync('web/src/components/views/NotesView.tsx', 'utf8');

let newContent = content.replace(
  "import { Plus, Tag, RefreshCw, Trash2, FolderOpen, FileText, Maximize2, FolderPlus, FolderMinus, ChevronRight, X, CheckCircle2, Clock3, AlertCircle, Pause } from 'lucide-react'",
  "import { Plus, Tag, RefreshCw, Trash2, FolderOpen, FileText, Maximize2, FolderPlus, FolderMinus, ChevronRight, X, CheckCircle2, Clock3, AlertCircle, Pause, Edit2, FolderInput } from 'lucide-react'"
);

const folderCardOld = `const FolderCard = React.memo(function FolderCard({ dir, onSelect, onDelete }: { dir: Directory, onSelect: () => void, onDelete: () => void }) {
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
})`;

const folderCardNew = `const FolderCard = React.memo(function FolderCard({ dir, onSelect, onDelete, onRename }: { dir: Directory, onSelect: () => void, onDelete: () => void, onRename: (newName: string) => void }) {
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
})`;

newContent = newContent.replace(folderCardOld, folderCardNew);

const noteCardOldStart = `const NoteCard = React.memo(function NoteCard({ note, allDirectories, token, load }: { note: Note, allDirectories: Directory[], token: string, load: () => void }) {
  const navigate = useNavigate()
  const isLong = note.text.length > 400 || note.text.split('\\n').length > 8

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="bento-card break-inside-avoid p-6 flex flex-col group relative cursor-pointer hover:border-primary-500/50 transition-colors"
      onClick={() => navigate(\`/notes/\${note.id}\`)}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground/70">
          <FolderOpen size={14} /> 
          {allDirectories.find(d => d.id === note.directory_id)?.name || 'Root'}`;

const noteCardNewStart = `const NoteCard = React.memo(function NoteCard({ note, allDirectories, token, load }: { note: Note, allDirectories: Directory[], token: string, load: () => void }) {
  const navigate = useNavigate()
  const isLong = note.text.length > 400 || note.text.split('\\n').length > 8
  const [isMoving, setIsMoving] = useState(false)

  const handleMove = async (newDirId: string | null) => {
    try {
      await api(\`/notes/\${note.id}\`, {
        method: 'PUT',
        token,
        body: JSON.stringify({
          text: note.text,
          tags: note.tags,
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
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="bento-card break-inside-avoid p-6 flex flex-col group relative cursor-pointer hover:border-primary-500/50 transition-colors"
      onClick={() => navigate(\`/notes/\${note.id}\`)}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground/70 flex-1 min-w-0 pr-2">
          <FolderOpen size={14} className="shrink-0" /> 
          {isMoving ? (
            <select
              autoFocus
              className="premium-input h-7 py-0 text-xs w-32 bg-background border-border/50"
              value={note.directory_id || ''}
              onChange={e => handleMove(e.target.value || null)}
              onBlur={() => setIsMoving(false)}
              onClick={e => e.stopPropagation()}
            >
              <option value="">Root</option>
              {allDirectories.map(d => <option key={d.id} value={d.id}>{d.path}</option>)}
            </select>
          ) : (
            <span className="truncate">{allDirectories.find(d => d.id === note.directory_id)?.name || 'Root'}</span>
          )}`;

newContent = newContent.replace(noteCardOldStart, noteCardNewStart);

const noteCardOldMiddle = `          )}
        </div>
        <div className="flex items-center gap-2">
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-primary-500/10 hover:text-primary-500"`;

const noteCardNewMiddle = `          )}
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
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-primary-500/10 hover:text-primary-500 transition-colors"`;

newContent = newContent.replace(noteCardOldMiddle, noteCardNewMiddle);

// Also remove opacity-0 group-hover... from the maximize and delete buttons because they are now wrapped in a div that handles opacity. Wait, I replaced `gap-2` with `gap-1 opacity-0...`. Let's just fix the classes.
const noteCardButtonsOld = `          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-primary-500/10 hover:text-primary-500"
            onClick={(e) => {
              e.stopPropagation()
              navigate(\`/notes/\${note.id}\`)
            }}
            title="Expand Note"
          >
            <Maximize2 size={14} />
          </button>
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/10 hover:text-red-500"
            onClick={async (e) => {`;
            
const noteCardButtonsNew = `          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-primary-500/10 hover:text-primary-500 transition-colors"
            onClick={(e) => {
              e.stopPropagation()
              navigate(\`/notes/\${note.id}\`)
            }}
            title="Expand Note"
          >
            <Maximize2 size={14} />
          </button>
          <button 
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-colors"
            onClick={async (e) => {`;
            
newContent = newContent.replace(noteCardButtonsOld, noteCardButtonsNew);

const handleRenameStr = `  const handleDeleteFolder = async (dirId: string) => {`;
const handleRenameInsert = `  const handleRenameFolder = async (dirId: string, newName: string) => {
    try {
      await api(\`/directories/\${dirId}\`, {
        method: 'PUT',
        token,
        body: JSON.stringify({ name: newName })
      })
      await load()
    } catch (err: any) {
      alert(err.message || 'Failed to rename folder')
    }
  }

  const handleDeleteFolder = async (dirId: string) => {`;

newContent = newContent.replace(handleRenameStr, handleRenameInsert);

const renderFolderCardOld = `              <FolderCard 
                key={d.id} 
                dir={d} 
                onSelect={() => handleSelectDir(d.id)} 
                onDelete={() => handleDeleteFolder(d.id)} 
              />`;

const renderFolderCardNew = `              <FolderCard 
                key={d.id} 
                dir={d} 
                onSelect={() => handleSelectDir(d.id)} 
                onDelete={() => handleDeleteFolder(d.id)}
                onRename={(newName) => handleRenameFolder(d.id, newName)}
              />`;

newContent = newContent.replace(renderFolderCardOld, renderFolderCardNew);

fs.writeFileSync('web/src/components/views/NotesView.tsx', newContent);
console.log('patched');
