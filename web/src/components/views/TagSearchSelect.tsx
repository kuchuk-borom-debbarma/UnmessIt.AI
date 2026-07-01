import { useState, useEffect, useRef } from 'react'
import { api } from '../../lib/api'
import { Search, Loader2, X, Tag, TagIcon } from 'lucide-react'
import { cn } from '../../lib/utils'

type Tag = {
  id: string
  name: string
}

interface TagSearchSelectProps {
  label: string
  mode: 'include' | 'exclude'
  value: string
  onChange: (val: string) => void
  condition?: 'any' | 'all'
  onConditionChange?: (val: 'any' | 'all') => void
  token: string
}

export function TagSearchSelect({ label, mode, value, onChange, condition, onConditionChange, token }: TagSearchSelectProps) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [results, setResults] = useState<Tag[]>([])
  const [loading, setLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [cursor, setCursor] = useState(0)
  const [hasMore, setHasMore] = useState(true)

  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const observerTarget = useRef<HTMLDivElement>(null)

  const selected = value.split(',').map(parseSelectedTag).filter(item => item.id)
  const selectedIds = selected.map(item => item.id)

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
    let isMounted = true
    const fetchResults = async () => {
      setLoading(true)
      try {
        const data = await api<{ data: Tag[] }>(
          `/tags/search?q=${encodeURIComponent(debouncedQuery)}&limit=10&cursor=${cursor}`,
          { token }
        )
        if (isMounted) {
          const newResults = data.data || []
          setResults(prev => cursor === 0 ? newResults : [...prev, ...newResults])
          setHasMore(newResults.length === 10)
        }
      } catch (err) {
        console.error('Failed to search tags:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    if (isOpen) fetchResults()
    return () => { isMounted = false }
  }, [debouncedQuery, cursor, token, isOpen])

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

  const handleSelect = (tag: Tag) => {
    if (!selectedIds.includes(tag.id)) {
      onChange([...selected.map(formatSelectedTag), formatSelectedTag(tag)].join(', '))
    }
    setQuery('')
    setIsOpen(false)
    inputRef.current?.focus()
  }

  const handleRemove = (id: string) => {
    onChange(selected.filter(tag => tag.id !== id).map(formatSelectedTag).join(', '))
  }

  const isInclude = mode === 'include'

  return (
    <div className="relative" ref={wrapperRef}>
      {/* Header with label + any/all toggle */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={cn(
            "flex items-center justify-center w-5 h-5 rounded-md",
            isInclude ? "text-violet-400" : "text-rose-400"
          )}>
            {isInclude ? <TagIcon size={13} /> : <Tag size={13} />}
          </div>
          <span className={cn(
            "text-xs font-semibold uppercase tracking-widest",
            isInclude ? "text-violet-400/80" : "text-rose-400/80"
          )}>
            {label}
          </span>
        </div>

        {condition && onConditionChange && (
          <div className="flex items-center bg-background/60 rounded-lg p-0.5 border border-border/40 gap-0.5">
            <button
              type="button"
              onClick={() => onConditionChange('any')}
              className={cn(
                "px-2.5 py-1 text-[10px] font-bold tracking-wider uppercase rounded-md transition-all duration-150",
                condition === 'any'
                  ? "bg-violet-500/20 text-violet-300 shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              Any
            </button>
            <button
              type="button"
              onClick={() => onConditionChange('all')}
              className={cn(
                "px-2.5 py-1 text-[10px] font-bold tracking-wider uppercase rounded-md transition-all duration-150",
                condition === 'all'
                  ? "bg-violet-500/20 text-violet-300 shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              All
            </button>
          </div>
        )}
      </div>

      {/* Input + chips area */}
      <div
        className={cn(
          "min-h-[44px] w-full rounded-xl border px-3 py-2 flex flex-wrap gap-1.5 items-center cursor-text transition-all duration-200",
          "bg-background/40 backdrop-blur-sm",
          isOpen
            ? isInclude
              ? "border-violet-500/40 shadow-[0_0_0_3px_rgba(167,139,250,0.08)]"
              : "border-rose-500/40 shadow-[0_0_0_3px_rgba(251,113,133,0.08)]"
            : "border-border/40 hover:border-border/70"
        )}
        onClick={() => { setIsOpen(true); inputRef.current?.focus() }}
      >
        {selected.map(tag => (
          <span
            key={tag.id}
            className={cn(
              "inline-flex items-center gap-1 pl-2.5 pr-1.5 py-0.5 rounded-lg text-xs font-medium",
              isInclude
                ? "bg-violet-500/10 text-violet-300 border border-violet-500/20"
                : "bg-rose-500/10 text-rose-300 border border-rose-500/20"
            )}
          >
            <span className="max-w-[100px] truncate">{tag.name}</span>
            <button
              type="button"
              onClick={e => { e.stopPropagation(); handleRemove(tag.id) }}
              className={cn(
                "flex-shrink-0 rounded-md p-0.5 transition-colors",
                isInclude ? "hover:bg-violet-500/20" : "hover:bg-rose-500/20"
              )}
              aria-label={`Remove tag ${tag.name}`}
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
            placeholder={selected.length === 0 ? "Search tags..." : "Add more..."}
            value={query}
            onChange={e => { setQuery(e.target.value); setIsOpen(true) }}
            onFocus={() => setIsOpen(true)}
          />
          {loading && <Loader2 size={12} className="absolute right-1 text-muted-foreground/60 animate-spin" />}
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-30 left-0 right-0 mt-1.5 bg-card/95 backdrop-blur-xl border border-border/50 rounded-xl shadow-2xl overflow-hidden max-h-48 overflow-y-auto">
          {results.length === 0 && !loading ? (
            <div className="p-3 text-center text-xs text-muted-foreground">
              {query.trim() ? 'No tags found' : 'Start typing to search tags'}
            </div>
          ) : (
            <>
              {results.map(tag => (
                <button
                  key={tag.id}
                  type="button"
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors border-b border-border/10 last:border-0",
                    selectedIds.includes(tag.id)
                      ? isInclude ? "bg-violet-500/10" : "bg-rose-500/10"
                      : "hover:bg-primary-500/8"
                  )}
                  onClick={() => handleSelect(tag)}
                >
                  <TagIcon size={13} className="shrink-0 text-muted-foreground/60" />
                  <span className="text-sm font-medium text-foreground">{tag.name}</span>
                  {selectedIds.includes(tag.id) && (
                    <div className={cn("ml-auto shrink-0 w-1.5 h-1.5 rounded-full", isInclude ? "bg-violet-400" : "bg-rose-400")} />
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

function formatSelectedTag(tag: Pick<Tag, 'id' | 'name'>) {
  return `${tag.id}|${encodeURIComponent(tag.name)}`
}

function parseSelectedTag(value: string): Tag {
  const [id, encodedName] = value.trim().split('|')
  const name = encodedName ? decodeURIComponent(encodedName) : id
  return { id: id || '', name: name || id || '' }
}
