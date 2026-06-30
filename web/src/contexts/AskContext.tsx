import { createContext, useContext, useState, useRef, useEffect, ReactNode, useCallback } from 'react'
import { api, API_BASE } from '../lib/api'

type SourceChunk = {
  id: string
  raw_input_id: string
  note_id: string
  text: string
  summary: string
}

type QueryResult = {
  answer: string
  citations: any[]
  source_chunks: SourceChunk[]
  retrieval_trace: Record<string, any>
}

type Toast = { tone: 'success' | 'danger'; message: string }

interface AskContextType {
  query: string
  setQuery: (q: string) => void
  loading: boolean
  showTrace: boolean
  setShowTrace: (s: boolean) => void
  showFilters: boolean
  setShowFilters: (s: boolean) => void
  withinDirectories: string
  setWithinDirectories: (d: string) => void
  excludingDirectories: string
  setExcludingDirectories: (d: string) => void
  withinTags: string
  setWithinTags: (t: string) => void
  excludingTags: string
  setExcludingTags: (t: string) => void
  withinTagsCondition: 'any' | 'all'
  setWithinTagsCondition: (c: 'any' | 'all') => void
  result: QueryResult | null
  toast: Toast | null
  setToast: (t: Toast | null) => void
  progressSteps: string[]
  handleAsk: (token: string) => void
  stopAsk: () => void
}

const AskContext = createContext<AskContextType | null>(null)

export function AskProvider({ children }: { children: ReactNode }) {
  const [query, setQuery] = useState(() => sessionStorage.getItem('ask_query') || '')
  const [loading, setLoading] = useState(false)
  const [showTrace, setShowTrace] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [withinDirectories, setWithinDirectories] = useState(() => sessionStorage.getItem('ask_within_dirs') || '')
  const [excludingDirectories, setExcludingDirectories] = useState(() => sessionStorage.getItem('ask_excluding_dirs') || '')
  const [withinTags, setWithinTags] = useState(() => sessionStorage.getItem('ask_within_tags') || '')
  const [excludingTags, setExcludingTags] = useState(() => sessionStorage.getItem('ask_excluding_tags') || '')
  const [withinTagsCondition, setWithinTagsCondition] = useState<'any' | 'all'>(() => (sessionStorage.getItem('ask_within_tags_condition') as 'any' | 'all') || 'any')
  const [result, setResult] = useState<QueryResult | null>(() => {
    try {
      const saved = sessionStorage.getItem('ask_result')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })
  const [toast, setToast] = useState<Toast | null>(null)
  const [progressSteps, setProgressSteps] = useState<string[]>(() => {
    try {
      const saved = sessionStorage.getItem('ask_progress')
      return saved ? JSON.parse(saved) : []
    } catch { return [] }
  })

  useEffect(() => {
    sessionStorage.setItem('ask_query', query)
    sessionStorage.setItem('ask_within_dirs', withinDirectories)
    sessionStorage.setItem('ask_excluding_dirs', excludingDirectories)
    sessionStorage.setItem('ask_within_tags', withinTags)
    sessionStorage.setItem('ask_excluding_tags', excludingTags)
    sessionStorage.setItem('ask_within_tags_condition', withinTagsCondition)
  }, [query, withinDirectories, excludingDirectories, withinTags, excludingTags, withinTagsCondition])

  useEffect(() => {
    if (result) {
      sessionStorage.setItem('ask_result', JSON.stringify(result))
    } else {
      sessionStorage.removeItem('ask_result')
    }
  }, [result])

  useEffect(() => {
    if (progressSteps.length > 0) {
      sessionStorage.setItem('ask_progress', JSON.stringify(progressSteps))
    } else {
      sessionStorage.removeItem('ask_progress')
    }
  }, [progressSteps])

  const abortControllerRef = useRef<AbortController | null>(null)
  const evtSourceRef = useRef<EventSource | null>(null)

  const stopAsk = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (evtSourceRef.current) {
      evtSourceRef.current.close()
      evtSourceRef.current = null
    }
    setLoading(false)
  }, [])

  const handleAsk = useCallback(async (token: string) => {
    if (!query.trim() || loading) return
    setLoading(true)
    setToast(null)
    setResult(null)
    setProgressSteps([])

    const clientId = crypto.randomUUID()
    const evtSource = new EventSource(`${API_BASE}/api/retrieval/events/${clientId}`)
    evtSourceRef.current = evtSource
    evtSource.addEventListener('progress', (e) => {
      try {
        const evData = JSON.parse(e.data)
        setProgressSteps(prev => [...prev, evData.message])
      } catch {}
    })

    const abortController = new AbortController()
    abortControllerRef.current = abortController

    try {
      const within = withinDirectories.split(',').map(s => s.trim()).filter(Boolean)
      const excluding = excludingDirectories.split(',').map(s => s.trim()).filter(Boolean)
      const withinTagsArr = withinTags.split(',').map(s => s.trim()).filter(Boolean)
      const excludingTagsArr = excludingTags.split(',').map(s => s.trim()).filter(Boolean)
      
      const data = await api<QueryResult>('/api/retrieval/query', {
        method: 'POST',
        token,
        body: JSON.stringify({ 
          query, 
          client_id: clientId,
          within_directories: within.length > 0 ? within : undefined,
          excluding_directories: excluding.length > 0 ? excluding : undefined,
          within_tags: withinTagsArr.length > 0 ? withinTagsArr : undefined,
          excluding_tags: excludingTagsArr.length > 0 ? excludingTagsArr : undefined,
          within_tags_condition: withinTagsCondition,
        }),
        signal: abortController.signal
      })
      setResult(data)
    } catch (err) {
      console.error(err)
      if (err instanceof Error && err.name !== 'AbortError') {
        setToast({ tone: 'danger', message: err.message })
      }
    } finally {
      evtSource.close()
      if (evtSourceRef.current === evtSource) {
        evtSourceRef.current = null
      }
      setLoading(false)
    }
  }, [query, loading, withinDirectories, excludingDirectories, withinTags, excludingTags, withinTagsCondition])

  return (
    <AskContext.Provider value={{
      query, setQuery, loading, showTrace, setShowTrace, showFilters, setShowFilters,
      withinDirectories, setWithinDirectories, excludingDirectories, setExcludingDirectories,
      withinTags, setWithinTags, excludingTags, setExcludingTags, withinTagsCondition, setWithinTagsCondition,
      result, toast, setToast, progressSteps, handleAsk, stopAsk
    }}>
      {children}
    </AskContext.Provider>
  )
}

export function useAsk() {
  const context = useContext(AskContext)
  if (!context) {
    throw new Error('useAsk must be used within an AskProvider')
  }
  return context
}
