import { useState, useRef, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import { api, API_BASE } from '../lib/api'
import { AskContext } from './AskContextCore'
import type { ProgressStep, QueryResult, Toast } from './AskContextCore'

const MAX_PROGRESS_STEPS = 200

export function AskProvider({ children }: { children: ReactNode }) {
  const [query, setQuery] = useState(() => sessionStorage.getItem('ask_query') || '')
  const [loading, setLoading] = useState(false)
  const [showTrace, setShowTrace] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [terminalOpen, setTerminalOpen] = useState(false)
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
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>(() => {
    try {
      const saved = sessionStorage.getItem('ask_progress')
      const parsed = saved ? JSON.parse(saved) : []
      return Array.isArray(parsed) ? parsed.map(normalizeProgressStep) : []
    } catch { return [] }
  })

  // Buffer for batching SSE events — avoids one setState per SSE message
  const pendingStepsRef = useRef<ProgressStep[]>([])
  const flushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const flushPending = useCallback(() => {
    if (pendingStepsRef.current.length === 0) return
    const batch = pendingStepsRef.current.splice(0)
    setProgressSteps(prev => [...prev, ...batch].slice(-MAX_PROGRESS_STEPS))
  }, [])

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
    if (flushTimerRef.current) clearTimeout(flushTimerRef.current)
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (evtSourceRef.current) {
      evtSourceRef.current.close()
      evtSourceRef.current = null
    }
    flushPending()
    setLoading(false)
  }, [flushPending])

  const handleAsk = useCallback(async (token: string) => {
    if (!query.trim() || loading) return
    setLoading(true)
    setToast(null)
    setResult(null)
    setProgressSteps([])
    setTerminalOpen(true)
    pendingStepsRef.current = []

    const clientId = crypto.randomUUID()
    const evtSource = new EventSource(`${API_BASE}/api/v1/retrieval/events/${clientId}`)
    evtSourceRef.current = evtSource

    evtSource.addEventListener('progress', (e) => {
      try {
        const evData = JSON.parse(e.data)
        pendingStepsRef.current.push(normalizeProgressStep(evData, pendingStepsRef.current.length))
        // Debounce: flush at most every 120ms to batch rapid events into one render
        if (!flushTimerRef.current) {
          flushTimerRef.current = setTimeout(() => {
            flushTimerRef.current = null
            flushPending()
          }, 120)
        }
      } catch (err) {
        console.error('Failed to parse retrieval progress event:', err)
      }
    })

    const abortController = new AbortController()
    abortControllerRef.current = abortController

    try {
      const within = withinDirectories.split(',').map(s => s.trim()).filter(Boolean)
      const excluding = excludingDirectories.split(',').map(s => s.trim()).filter(Boolean)
      const withinTagsArr = tagIds(withinTags)
      const excludingTagsArr = tagIds(excludingTags)
      
      const data = await api<QueryResult>('/api/v1/retrieval/query', {
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
      // Collapse terminal once result arrives; user can expand it
      setTerminalOpen(false)
    } catch (err) {
      console.error(err)
      if (err instanceof Error && err.name !== 'AbortError') {
        setToast({ tone: 'danger', message: err.message })
      }
    } finally {
      if (flushTimerRef.current) {
        clearTimeout(flushTimerRef.current)
        flushTimerRef.current = null
      }
      flushPending()
      evtSource.close()
      if (evtSourceRef.current === evtSource) evtSourceRef.current = null
      setLoading(false)
    }
  }, [query, loading, withinDirectories, excludingDirectories, withinTags, excludingTags, withinTagsCondition, flushPending])

  return (
    <AskContext.Provider value={{
      query, setQuery, loading, showTrace, setShowTrace, showFilters, setShowFilters,
      terminalOpen, setTerminalOpen,
      withinDirectories, setWithinDirectories, excludingDirectories, setExcludingDirectories,
      withinTags, setWithinTags, excludingTags, setExcludingTags, withinTagsCondition, setWithinTagsCondition,
      result, toast, setToast, progressSteps, handleAsk, stopAsk
    }}>
      {children}
    </AskContext.Provider>
  )
}

function tagIds(value: string) {
  return value.split(',').map(item => item.trim().split('|')[0]).filter(Boolean)
}

function normalizeProgressStep(value: unknown, index = 0): ProgressStep {
  if (typeof value === 'string') {
    return { message: value, depth: 0, ref: `legacy:${index}` }
  }
  const item = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const details = item.details && typeof item.details === 'object' && !Array.isArray(item.details)
    ? item.details as Record<string, unknown>
    : undefined
  return {
    message: typeof item.message === 'string' ? item.message : 'Progress update',
    depth: Math.max(Number(item.depth) || 0, 0),
    ref: typeof item.ref === 'string' ? item.ref : `progress:${Date.now()}:${index}`,
    parent_ref: typeof item.parent_ref === 'string' ? item.parent_ref : undefined,
    details: details && Object.keys(details).length > 0 ? details : undefined,
  }
}
