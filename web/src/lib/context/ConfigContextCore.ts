import { createContext } from 'react'

export type ConfigContextType = {
  hasActivePreset: boolean | null
  loading: boolean
  checkConfig: () => Promise<void>
}

export const ConfigContext = createContext<ConfigContextType | undefined>(undefined)
