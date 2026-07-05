import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { FloatingDock } from './FloatingDock'
import { useVersionCheck } from '../../lib/useVersionCheck'
import { ReleaseHistoryModal } from '../ui/ReleaseHistoryModal'
import { ExternalLink, RefreshCw, AlertTriangle, ChevronRight, ServerOff, Sun, Moon, Settings } from 'lucide-react'
import { ConfigProvider } from '../../lib/context/ConfigContext'
import { useConfig } from '../../lib/context/useConfig'
import { useTheme } from '../../lib/context/useTheme'
import { useEffect, useState } from 'react'
import { API_BASE } from '../../lib/api'

const REPOSITORY_URL = 'https://github.com/kuchuk-borom-debbarma/UnmessIt.AI'

function GlobalConnectionBanner() {
  const [isOffline, setIsOffline] = useState(false)

  useEffect(() => {
    let mounted = true
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(3000) })
        if (mounted) setIsOffline(!res.ok)
      } catch {
        if (mounted) setIsOffline(true)
      }
    }
    
    checkHealth()
    const interval = setInterval(checkHealth, 5000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div className="bg-red-500 text-white px-4 py-2 shadow-lg font-space pointer-events-auto">
      <div className="flex items-center justify-center gap-3">
        <ServerOff size={18} />
        <span className="font-bold tracking-tight">Server Disconnected</span>
        <span className="text-white/80 text-sm hidden sm:block ml-2">UnmessIt.AI cannot reach the backend. Please check your connection or start the server.</span>
      </div>
    </div>
  )
}

function GlobalWarningBanner() {
  const { hasActivePreset, loading } = useConfig()
  
  if (loading || hasActivePreset !== false) return null
  
  return (
    <div className="bg-accent-500/10 border-b border-accent-500/20 px-4 py-2 flex items-center justify-between backdrop-blur-xl pointer-events-auto">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-lg bg-accent-500/10 flex items-center justify-center text-accent-500 border border-accent-500/20">
          <AlertTriangle size={18} />
        </div>
        <div>
          <h3 className="text-sm font-bold text-accent-500 tracking-tight">Missing AI Configuration</h3>
          <p className="text-xs font-medium text-accent-500/80 hidden sm:block">Create one AI config preset before using UnmessIt.AI.</p>
        </div>
      </div>
      <NavLink to="/settings" className="premium-btn premium-btn-primary h-9 px-4">
        Setup Now <ChevronRight size={16} className="ml-2" />
      </NavLink>
    </div>
  )
}

function GlobalUpdateBanner({ updateAvailable, versionInfo }: { updateAvailable: boolean; versionInfo: ReturnType<typeof useVersionCheck>['versionInfo'] }) {
  if (!updateAvailable || !versionInfo) return null

  return (
    <div className="bg-primary-500/10 border-b border-primary-500/20 px-4 py-2 flex items-center justify-between backdrop-blur-xl pointer-events-auto">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-lg bg-primary-500/10 flex items-center justify-center text-primary-500 border border-primary-500/20">
          <RefreshCw size={18} />
        </div>
        <div>
          <h3 className="text-sm font-bold text-primary-500 tracking-tight">Update Available (v{versionInfo.version})</h3>
          <p className="text-xs font-medium text-primary-500/80 hidden sm:block">A new version of UnmessIt.AI is available.</p>
        </div>
      </div>
      <a href={REPOSITORY_URL} target="_blank" rel="noreferrer" className="premium-btn premium-btn-primary h-9 px-4">
        View on GitHub <ExternalLink size={16} className="ml-2" />
      </a>
    </div>
  )
}

export function AppShell({ token, onLogout }: { token: string | null; onLogout: () => void }) {
  const [showChangelog, setShowChangelog] = useState(false)
  const { updateAvailable, versionInfo, currentVersion } = useVersionCheck()
  const location = useLocation()
  const { theme, setTheme } = useTheme()
  const isLanding = location.pathname === '/'

  return (
    <ConfigProvider token={token}>
      {token && (
        <div className="fixed top-0 inset-x-0 z-[60] pointer-events-none">
          <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-3 md:px-8 pointer-events-auto">
            <div className="flex items-center gap-2">
              <NavLink
                to="/"
                className="liquid-glass inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-all hover:scale-105 active:scale-95 hover:text-foreground"
                title="UnmessIt.AI Home"
              >
                <img src="/favicon.svg" alt="UnmessIt.AI Logo" className="w-5 h-5" />
              </NavLink>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="liquid-glass inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-all hover:text-foreground active:scale-95"
                title="Toggle Theme"
              >
                {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
              </button>
              {token && !isLanding && (
                <NavLink
                  to="/settings"
                  className="liquid-glass inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-all hover:text-foreground active:scale-95"
                  title="Settings"
                >
                  <Settings size={20} />
                </NavLink>
              )}
              <button
                className="liquid-glass inline-flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-bold text-muted-foreground transition-all hover:text-foreground active:scale-95 ml-2"
                onClick={() => setShowChangelog(true)}
              >
                v{currentVersion}
                <span className="hidden text-xs font-semibold text-primary-400 sm:inline">Release history</span>
              </button>
            </div>
          </div>
          <GlobalConnectionBanner />
          <GlobalWarningBanner />
          <GlobalUpdateBanner updateAvailable={updateAvailable} versionInfo={versionInfo} />
        </div>
      )}

      <main className="relative flex-1 flex flex-col min-h-screen w-full max-w-[1600px] mx-auto px-4 md:px-8 pb-28 pt-20 md:pt-24">
        <div className="flex-1 flex flex-col">
          <Outlet />
        </div>
      </main>

      {!isLanding && <FloatingDock token={token} onLogout={onLogout} />}
      
      <ReleaseHistoryModal 
        isOpen={showChangelog} 
        onClose={() => setShowChangelog(false)} 
        versionInfo={versionInfo} 
        currentVersion={currentVersion} 
        updateAvailable={updateAvailable}
      />
    </ConfigProvider>
  )
}
