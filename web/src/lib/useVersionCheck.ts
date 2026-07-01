import { useState, useEffect } from 'react'

export type VersionInfo = {
  version: string
  changelog: string
}

// Ensure proper semver comparison (e.g. 1.0.1 > 1.0.0)
function isNewerVersion(current: string, latest: string): boolean {
  const currentParts = current.replace(/^v/, '').split('.').map(Number)
  const latestParts = latest.replace(/^v/, '').split('.').map(Number)
  
  for (let i = 0; i < Math.max(currentParts.length, latestParts.length); i++) {
    const c = currentParts[i] || 0
    const l = latestParts[i] || 0
    if (l > c) return true
    if (c > l) return false
  }
  return false
}

export function useVersionCheck() {
  const [updateAvailable, setUpdateAvailable] = useState(false)
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null)

  useEffect(() => {
    let mounted = true

    const checkForUpdate = async () => {
      try {
        // Append timestamp to bypass caching
        const res = await fetch(`/version.json?t=${new Date().getTime()}`)
        if (!res.ok) return

        const data = await res.json() as VersionInfo
        if (!data || !data.version) return

        const currentVersion = import.meta.env.VITE_APP_VERSION || '0.0.0'
        
        if (mounted) {
          setVersionInfo(data)
          if (isNewerVersion(currentVersion, data.version)) {
            setUpdateAvailable(true)
          }
        }
      } catch (err) {
        console.error('Failed to check for updates', err)
      }
    }

    checkForUpdate()
    
    // Check every hour
    const interval = setInterval(checkForUpdate, 60 * 60 * 1000)
    
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  return { updateAvailable, versionInfo, currentVersion: import.meta.env.VITE_APP_VERSION || '0.0.0' }
}
