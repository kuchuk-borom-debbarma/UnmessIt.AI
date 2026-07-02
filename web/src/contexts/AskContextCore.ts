import { createContext } from 'react'

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

type ProgressStep = {
  message: string
  depth: number
  ref: string
  parent_ref?: string
  details?: Record<string, unknown>
}

export interface AskContextType {
  query: string
  setQuery: (q: string) => void
  loading: boolean
  showTrace: boolean
  setShowTrace: (s: boolean) => void
  showFilters: boolean
  setShowFilters: (s: boolean) => void
  terminalOpen: boolean
  setTerminalOpen: (o: boolean) => void
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
  progressSteps: ProgressStep[]
  handleAsk: (token: string) => void
  stopAsk: () => void
}

export const AskContext = createContext<AskContextType | null>(null)
export type { QueryResult, SourceChunk, Toast, ProgressStep }
