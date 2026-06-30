import { useState, useEffect, useRef } from 'react'
import { api } from '../../lib/api'
import { Check, Copy, Search, Loader2 } from 'lucide-react'

type Directory = {
  id: string
  name: string
  path: string
}

interface DirectorySearchSelectProps {
  label: string
  value: string
  onChange: (val: string) => void
  token: string
  placeholder?: string
}

export function DirectorySearchSelect({ label, value, onChange, token, placeholder }: DirectorySearchSelectProps) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [results, setResults] = useState<Directory[]>([])
  const [loading, setLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [cursor, setCursor] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  
  const wrapperRef = useRef<HTMLDivElement>(null)
  const observerTarget = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    setCursor(0)
    setHasMore(true)
    setResults([])
  }, [debouncedQuery])

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([])
      setHasMore(false)
      return
    }

    let isMounted = true
    const fetchResults = async () => {
      setLoading(true)
      try {
        const data = await api<{ data: Directory[] }>(`/directories/search?q=${encodeURIComponent(debouncedQuery)}&limit=10&cursor=${cursor}`, {
          token
        })
        if (isMounted) {
          const newResults = data.data || []
          setResults(prev => cursor === 0 ? newResults : [...prev, ...newResults])
          setHasMore(newResults.length === 10)
        }
      } catch (err) {
        console.error('Failed to search directories:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    fetchResults()

    return () => { isMounted = false }
  }, [debouncedQuery, cursor, token])

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          setCursor(prev => prev + 10)
        }
      },
      { threshold: 1.0 }
    )

    if (observerTarget.current) {
      observer.observe(observerTarget.current)
    }

    return () => observer.disconnect()
  }, [hasMore, loading])

  const handleSelect = (dir: Directory) => {
    const current = value.split(',').map(s => s.trim()).filter(Boolean)
    if (!current.includes(dir.id)) {
      onChange([...current, dir.id].join(', '))
    }
    setQuery('')
    setIsOpen(false)
  }

  const handleCopy = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    navigator.clipboard.writeText(id)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleRawInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)
  }

  return (
    <div className="relative" ref={wrapperRef}>
      <label className="text-sm font-medium text-foreground/80 mb-1.5 block">{label}</label>
      
      <div className="relative">
        <input
          type="text"
          className="w-full bg-input/50 border border-border/50 rounded-xl px-4 py-3 text-sm outline-none focus:border-primary-500/50 focus:bg-background transition-colors placeholder:text-muted-foreground/40 text-foreground mb-2 font-mono"
          placeholder={placeholder || "Paste IDs or type to search..."}
          value={value}
          onChange={handleRawInputChange}
        />
      </div>

      <div className="relative">
        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          <Search size={14} className="text-muted-foreground" />
        </div>
        <input
          type="text"
          className="w-full bg-input/30 border border-border/30 rounded-lg pl-9 pr-4 py-2 text-sm outline-none focus:border-primary-500/30 transition-colors placeholder:text-muted-foreground/50 text-foreground"
          placeholder="Search directory by name..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
        />
        {loading && (
          <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
            <Loader2 size={14} className="text-primary-500 animate-spin" />
          </div>
        )}
      </div>

      {isOpen && query.trim() && (
        <div className="absolute z-10 w-full mt-1 bg-background/95 backdrop-blur-xl border border-border/50 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto custom-scrollbar">
          {results.length === 0 && !loading ? (
            <div className="p-4 text-center text-sm text-muted-foreground">No directories found.</div>
          ) : (
            <>
              {results.map(dir => (
                <div 
                  key={dir.id}
                  className="flex items-center justify-between p-3 hover:bg-primary-500/10 cursor-pointer transition-colors border-b border-border/20 last:border-0"
                  onClick={() => handleSelect(dir)}
                >
                  <div>
                    <div className="font-medium text-sm text-foreground">{dir.name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5 font-mono">
                      {dir.id.substring(0, 8)}...
                    </div>
                  </div>
                  
                  <button
                    onClick={(e) => handleCopy(e, dir.id)}
                    className="p-1.5 rounded-md hover:bg-background/80 text-muted-foreground hover:text-foreground transition-colors z-20"
                    title="Copy full ID"
                  >
                    {copiedId === dir.id ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                  </button>
                </div>
              ))}
              {hasMore && (
                <div ref={observerTarget} className="p-4 flex justify-center">
                  <Loader2 size={16} className="text-muted-foreground animate-spin" />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
