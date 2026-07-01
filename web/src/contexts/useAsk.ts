import { useContext } from 'react'
import { AskContext } from './AskContextCore'

export function useAsk() {
  const context = useContext(AskContext)
  if (!context) {
    throw new Error('useAsk must be used within an AskProvider')
  }
  return context
}
