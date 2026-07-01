import { useState, useEffect, useRef } from 'react'
import { api } from '../../lib/api'
import { Search, Loader2, X, FolderOpen, FolderMinus } from 'lucide-react'
import { cn } from '../../lib/utils'

type Directory = {
  id: string
  name: string
  path: string
}

interface DirectorySearchSelectProps {
  label: string
  mode: 'include' | 'exclude'
  value: string
  onChange: (val: string) => void
  token: string
}

export function DirectorySearchSelect({ label, mode, value, onChange, token }: DirectorySearchSelectProps) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [results, setResults] = useState<Directory[]>([])
  const [loading, setLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [cursor, setCursor] = useState(0)
  const [hasMore, setHasMore] = useState(true)

  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const observerTarget = useRef<HTMLDivElement>(null)

  const selected = value.split(',').map(s => s.trim()).filter(Boolean)

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
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
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
        const data = await api<{ data: Directory[] }>(
          `/api/v1/directories/search?q=${encodeURIComponent(debouncedQuery)}&limit=10&cursor=${cursor}`,
          { token }
        )
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
        if (entries[0].isIntersecting && hasMore && !loading) setCursor(prev => prev + 10)
      },
      { threshold: 1.0 }
    )
    if (observerTarget.current) observer.observe(observerTarget.current)
    return () => observer.disconnect()
  }, [hasMore, loading])

  const handleSelect = (dir: Directory) => {
    if (!selected.includes(dir.path)) {
      onChange([...selected, dir.path].join(', '))
    }
    setQuery('')
    setIsOpen(false)
    inputRef.current?.focus()
  }

  const handleRemove = (path: string) => {
    onChange(selected.filter(p => p !== path).join(', '))
  }

  const isInclude = mode === 'include'

  return (
    <div className="relative" ref={wrapperRef}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className={cn(
          "flex items-center justify-center w-5 h-5 rounded-md",
          isInclude ? "text-emerald-400" : "text-rose-400"
        )}>
          {isInclude ? <FolderOpen size={14} /> : <FolderMinus size={14} />}
        </div>
        <span className={cn(
          "text-xs font-semibold uppercase tracking-widest",
          isInclude ? "text-emerald-400/80" : "text-rose-400/80"
        )}>
          {label}
        </span>
      </div>

      {/* Input + chips area */}
      <div
        className={cn(
          "min-h-[44px] w-full rounded-xl border px-3 py-2 flex flex-wrap gap-1.5 items-center cursor-text transition-all duration-200",
          "bg-background/40 backdrop-blur-sm",
          isOpen
            ? isInclude
              ? "border-emerald-500/40 shadow-[0_0_0_3px_rgba(52,211,153,0.08)]"
              : "border-rose-500/40 shadow-[0_0_0_3px_rgba(251,113,133,0.08)]"
            : "border-border/40 hover:border-border/70"
        )}
        onClick={() => { setIsOpen(true); inputRef.current?.focus() }}
      >
        {selected.map(path => (
          <span
            key={path}
            className={cn(
              "inline-flex items-center gap-1 pl-2.5 pr-1.5 py-0.5 rounded-lg text-xs font-medium max-w-[160px]",
              isInclude
                ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                : "bg-rose-500/10 text-rose-300 border border-rose-500/20"
            )}
          >
            <span className="truncate">{path.split('/').pop() || path}</span>
            <button
              type="button"
              onClick={e => { e.stopPropagation(); handleRemove(path) }}
              className={cn(
                "flex-shrink-0 rounded-md p-0.5 transition-colors",
                isInclude ? "hover:bg-emerald-500/20" : "hover:bg-rose-500/20"
              )}
              aria-label={`Remove ${path}`}
            >
              <X size={10} />
            </button>
          </span>
        ))}

        <div className="relative flex-1 flex items-center min-w-[80px]">
          <Search size={12} className="absolute left-1 text-muted-foreground/50 pointer-events-none" />
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent pl-5 text-sm outline-none placeholder:text-muted-foreground/30 text-foreground"
            placeholder={selected.length === 0 ? "Search directories..." : "Add more..."}
            value={query}
            onChange={e => { setQuery(e.target.value); setIsOpen(true) }}
            onFocus={() => setIsOpen(true)}
          />
          {loading && <Loader2 size={12} className="absolute right-1 text-muted-foreground/60 animate-spin" />}
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && query.trim() && (
        <div className="absolute z-30 left-0 right-0 mt-1.5 bg-card/95 backdrop-blur-xl border border-border/50 rounded-xl shadow-2xl overflow-hidden max-h-52 overflow-y-auto">
          {results.length === 0 && !loading ? (
            <div className="p-3 text-center text-xs text-muted-foreground">No directories found</div>
          ) : (
            <>
              {results.map(dir => (
                <button
                  key={dir.id}
                  type="button"
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors border-b border-border/10 last:border-0",
                    selected.includes(dir.path)
                      ? isInclude ? "bg-emerald-500/10" : "bg-rose-500/10"
                      : "hover:bg-primary-500/8"
                  )}
                  onClick={() => handleSelect(dir)}
                >
                  <FolderOpen size={14} className="shrink-0 text-muted-foreground/60" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">{dir.name}</div>
                    <div className="text-xs text-muted-foreground/60 font-mono truncate">{dir.path}</div>
                  </div>
                  {selected.includes(dir.path) && (
                    <div className={cn("ml-auto shrink-0 w-1.5 h-1.5 rounded-full", isInclude ? "bg-emerald-400" : "bg-rose-400")} />
                  )}
                </button>
              ))}
              {hasMore && (
                <div ref={observerTarget} className="p-3 flex justify-center">
                  <Loader2 size={14} className="text-muted-foreground animate-spin" />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
