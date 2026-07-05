import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

// Layout
import { AppShell } from './components/layout/AppShell'

// Views
import { AuthScreen } from './components/auth/AuthScreen'
import { NotesView } from './components/views/NotesView'
import { AskView } from './components/views/AskView'
import { JobsView } from './components/views/JobsView'
import { SettingsView } from './components/views/SettingsView'
import { LandingView } from './components/views/LandingView'
import { NoteDetailView } from './components/views/NoteDetailView'
import { NoteInsightsView } from './components/views/NoteInsightsView'
import { TrashView } from './components/views/TrashView'

// Contexts
import { AskProvider } from './contexts/AskContext'

const tokenKey = 'unmessit.token'

function RequireAuth({ token, children }: { token: string | null; children: ReactNode }) {
  if (!token) return <Navigate to="/login" replace />
  return children
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(tokenKey))

  const saveToken = (next: string | null) => {
    if (next) localStorage.setItem(tokenKey, next)
    else localStorage.removeItem(tokenKey)
    setToken(next)
  }

  useEffect(() => {
    const handleLogout = () => saveToken(null)
    window.addEventListener('unmessit:logout', handleLogout as EventListener)
    return () => window.removeEventListener('unmessit:logout', handleLogout as EventListener)
  }, [])

  return (
    <Routes>
      <Route
        path="/login"
        element={token ? <Navigate to="/notes" replace /> : <AuthScreen initialMode="signin" onAuthSuccess={saveToken} />}
      />
      <Route
        path="/signup"
        element={token ? <Navigate to="/notes" replace /> : <AuthScreen initialMode="signup" onAuthSuccess={saveToken} />}
      />
      <Route element={<AskProvider><AppShell token={token} onLogout={() => saveToken(null)} /></AskProvider>}>
        <Route path="/" element={<LandingView />} />
        <Route
          path="/notes"
          element={<RequireAuth token={token}><NotesView token={token ?? ''} /></RequireAuth>}
        />
        <Route
          path="/trash"
          element={<RequireAuth token={token}><TrashView token={token ?? ''} /></RequireAuth>}
        />
        <Route
          path="/notes/:id"
          element={<RequireAuth token={token}><NoteDetailView token={token ?? ''} /></RequireAuth>}
        />
        <Route
          path="/ask"
          element={<RequireAuth token={token}><AskView token={token ?? ''} /></RequireAuth>}
        />
        <Route
          path="/notes/:id/insights"
          element={<RequireAuth token={token}><NoteInsightsView token={token ?? ''} /></RequireAuth>}
        />
        <Route
          path="/jobs"
          element={<RequireAuth token={token}><JobsView token={token ?? ''} /></RequireAuth>}
        />
        <Route
          path="/settings"
          element={<RequireAuth token={token}><SettingsView token={token ?? ''} /></RequireAuth>}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App
