const fs = require('fs');
const content = fs.readFileSync('web/src/components/views/NoteDetailView.tsx', 'utf8');

let newContent = content.replace(
  "import { ArrowLeft, Tag, RefreshCw, Trash2, FolderOpen, BrainCircuit } from 'lucide-react'",
  "import { ArrowLeft, Tag, RefreshCw, Trash2, FolderOpen, BrainCircuit, Edit2, Save, X } from 'lucide-react'"
);

const stateInsert = `  const [directory, setDirectory] = useState<Directory | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchParams] = useSearchParams()

  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState('')`;

newContent = newContent.replace(
  `  const [directory, setDirectory] = useState<Directory | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchParams] = useSearchParams()`,
  stateInsert
);

const loadInsert = `      const { data } = await api<{ data: Note }>(\`/notes/\${id}\`, { token })
      setNote(data)
      setEditText(data.text)`;

newContent = newContent.replace(
  `      const { data } = await api<{ data: Note }>(\`/notes/\${id}\`, { token })
      setNote(data)`,
  loadInsert
);

const renderNoteTextOld = `        <div className="prose prose-lg dark:prose-invert max-w-none">
          <div className="text-lg leading-8 text-foreground/90 whitespace-pre-wrap">
            {renderNoteText()}
          </div>
        </div>`;

const renderNoteTextNew = `        <div className="prose prose-lg dark:prose-invert max-w-none">
          {isEditing ? (
            <textarea
              autoFocus
              className="w-full min-h-[300px] bg-transparent border border-border/50 rounded-xl p-4 text-lg leading-8 text-foreground/90 focus:ring-2 focus:ring-primary-500/50 outline-none resize-y"
              value={editText}
              onChange={e => setEditText(e.target.value)}
            />
          ) : (
            <div className="text-lg leading-8 text-foreground/90 whitespace-pre-wrap">
              {renderNoteText()}
            </div>
          )}
        </div>`;

newContent = newContent.replace(renderNoteTextOld, renderNoteTextNew);

const handleSaveStr = `  const handleSave = async () => {
    if (!note || !editText.trim()) return
    try {
      await api(\`/notes/\${note.id}\`, {
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
  }`;

const buttonsOld = `          <div className="flex items-center gap-3">
            <button 
              className="flex items-center gap-2 h-10 px-4 rounded-lg bg-accent-500/10 text-accent-500 hover:bg-accent-500 hover:text-white transition-colors text-sm font-bold"
              onClick={() => navigate(\`/notes/\${note.id}/insights\`)}
            >
              <BrainCircuit size={16} /> Insights
            </button>
            <button 
              className="flex items-center gap-2 h-10 px-4 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white transition-colors text-sm font-bold"
              onClick={async () => {
                if (confirm('Delete this note?')) {
                  await api(\`/notes/\${note.id}\`, { method: 'DELETE', token })
                  navigate('/notes')
                }
              }}
            >
              <Trash2 size={16} /> Delete Note
            </button>
          </div>`;

const buttonsNew = `${handleSaveStr}

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
                  onClick={() => navigate(\`/notes/\${note.id}/insights\`)}
                >
                  <BrainCircuit size={16} /> Insights
                </button>
                <button 
                  className="flex items-center gap-2 h-10 px-4 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white transition-colors text-sm font-bold"
                  onClick={async () => {
                    if (confirm('Delete this note?')) {
                      await api(\`/notes/\${note.id}\`, { method: 'DELETE', token })
                      navigate('/notes')
                    }
                  }}
                >
                  <Trash2 size={16} /> Delete Note
                </button>
              </>
            )}
          </div>`;

newContent = newContent.replace(buttonsOld, buttonsNew);

fs.writeFileSync('web/src/components/views/NoteDetailView.tsx', newContent);
console.log('patched');
