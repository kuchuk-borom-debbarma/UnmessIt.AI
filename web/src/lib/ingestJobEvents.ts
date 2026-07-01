import { useEffect, useRef } from 'react'
import { API_BASE } from './api'

export type JobStatus = 'queued' | 'running' | 'waiting_retry' | 'complete' | 'failed' | 'aborted' | 'paused'

export type JobEvent = { job: { id: string; status: JobStatus } }

export type JobProgressEvent = {
  job_id: string
  status: JobStatus
  stage: string
  message: string
  depth?: number
  ref?: string
  parent_ref?: string
}

export type ProgressLine = {
  ref: string
  message: string
  depth: number
  stage: string
  parent_ref?: string
}

export type ProgressByJob = Record<string, ProgressLine[]>
type IngestJobHandlers = {
  onJob?: (event: JobEvent) => void
  onProgress?: (event: JobProgressEvent) => void
  onError?: (error: unknown) => void
}

const MAX_PROGRESS_LINES = 100

export function applyProgressEvent(current: ProgressByJob, event: JobProgressEvent): ProgressByJob {
  const line = normalizeProgressLine(event)
  const existing = current[event.job_id] ?? []
  const index = existing.findIndex(item => item.ref === line.ref)
  const next = index >= 0
    ? existing.map((item, itemIndex) => itemIndex === index ? line : item)
    : [...existing, line]
  return { ...current, [event.job_id]: next.slice(-MAX_PROGRESS_LINES) }
}

export function normalizeProgressLine(event: JobProgressEvent): ProgressLine {
  return {
    ref: event.ref || fallbackRef(event.message),
    message: event.message,
    depth: Math.max(0, Number(event.depth) || 0),
    stage: event.stage,
    parent_ref: event.parent_ref,
  }
}

export function useIngestJobEvents(
  token: string,
  handlers: IngestJobHandlers,
) {
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    const controller = new AbortController()
    let retryTimer: number | undefined
    const connect = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/advanced/ingest_jobs/events`, {
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
          for (const block of events) handleBlock(block, handlersRef.current)
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          handlersRef.current.onError?.(error)
          retryTimer = window.setTimeout(connect, 5000)
        }
      }
    }
    void connect()
    return () => {
      controller.abort()
      if (retryTimer) clearTimeout(retryTimer)
    }
  }, [token])
}

function handleBlock(block: string, handlers: IngestJobHandlers) {
  const event = block.split('\n').find(line => line.startsWith('event: '))?.slice(7)
  const rawData = block.split('\n').find(line => line.startsWith('data: '))?.slice(6)
  if (!rawData) return
  if (event === 'job') handlers.onJob?.(JSON.parse(rawData) as JobEvent)
  if (event === 'job_progress') handlers.onProgress?.(JSON.parse(rawData) as JobProgressEvent)
}

function fallbackRef(message: string) {
  let hash = 0
  for (let index = 0; index < message.length; index += 1) {
    hash = ((hash << 5) - hash + message.charCodeAt(index)) | 0
  }
  return `message:${Math.abs(hash)}`
}
