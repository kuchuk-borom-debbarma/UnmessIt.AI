import { useState } from 'react'
import { ArrowRight, Bot, CheckCircle2, GitBranch, LogIn, RefreshCw, Search, UserPlus } from 'lucide-react'
import { authApi } from '../../lib/api'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils'

type AuthMode = 'signin' | 'signup'
type Toast = { tone: 'success' | 'danger'; message: string }

function ToastMessage({ toast }: { toast: Toast }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn(
        'absolute -top-16 left-0 right-0 px-4 py-3 rounded-xl text-sm font-bold text-center shadow-2xl backdrop-blur-md border',
        toast.tone === 'success'
          ? 'bg-primary-500/10 text-primary-500 border-primary-500/20'
          : 'bg-red-500/10 text-red-500 border-red-500/20',
      )}
    >
      {toast.message}
    </motion.div>
  )
}

const differentiators = [
  {
    icon: RefreshCw,
    label: 'Volatile-safe ingest',
    body: 'New notes flow in continuously. Jobs checkpoint and resume — no full rebuilds.',
  },
  {
    icon: GitBranch,
    label: 'Broad multi-hop search',
    body: 'Vector + lexical + recall link expansion reaches context scattered across many notes.',
  },
  {
    icon: CheckCircle2,
    label: 'Cited answers',
    body: 'Every response carries exact source spans, file references, and a retrieval trace.',
  },
]

export function AuthScreen({
  initialMode = 'signin',
  onAuthSuccess,
}: {
  initialMode?: AuthMode
  onAuthSuccess: (token: string) => void
}) {
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setToast(null)

    try {
      const res =
        mode === 'signin'
          ? await authApi.signIn(username, password)
          : await authApi.signUp(username, password)

      if (res.token) {
        onAuthSuccess(res.token)
      } else {
        setToast({ tone: 'success', message: res.message || 'Success' })
        if (mode === 'signup') setMode('signin')
      }
    } catch (err: any) {
      setToast({ tone: 'danger', message: err.message || 'Authentication failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="bg-noise" />
      <div className="auth-grid">

        {/* Left — story panel */}
        <motion.div
          className="auth-story"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="auth-brand">
            <img src="/favicon.svg" alt="" />
            <span>UnmessIt.AI</span>
          </div>

          <h1>Messy notes become answers you can trust.</h1>
          <p>
            Write in plain text. The system indexes, links, and retrieves — so your questions get cited, grounded answers instead of guesses.
          </p>

          <div className="auth-diff-grid">
            {differentiators.map((d) => (
              <div key={d.label} className="auth-diff-card">
                <div className="auth-diff-icon">
                  <d.icon size={16} />
                </div>
                <div>
                  <strong>{d.label}</strong>
                  <span>{d.body}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="auth-demo-bar">
            <div className="auth-demo-query">
              <Search size={15} />
              <span>What did I promise to follow up on?</span>
            </div>
            <div className="auth-demo-answer">
              <Bot size={15} />
              <span>Built from 4 linked notes · 2 source chunks · 1 task thread</span>
            </div>
          </div>
        </motion.div>

        {/* Right — form */}
        <motion.div
          className="auth-card-wrap"
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.07 }}
        >
          <div className="relative">
            <AnimatePresence>
              {toast && <ToastMessage toast={toast} />}
            </AnimatePresence>

            <form onSubmit={handleSubmit} className="auth-card">
              <div className="auth-card-heading">
                <div>
                  {mode === 'signin' ? <LogIn size={20} /> : <UserPlus size={20} />}
                </div>
                <h2>{mode === 'signin' ? 'Welcome back' : 'Start your workspace'}</h2>
                <p>
                  {mode === 'signin'
                    ? 'Pick up where your notes, chunks, and source links left off.'
                    : 'Create a workspace where notes stay searchable and cited.'}
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    required
                    className="premium-input h-12 text-base"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    className="premium-input h-12 text-base"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="premium-btn premium-btn-primary w-full h-13 text-base mt-6 flex items-center justify-center gap-2"
              >
                {mode === 'signin' ? <LogIn size={18} /> : <UserPlus size={18} />}
                {loading ? 'Authenticating…' : mode === 'signin' ? 'Sign In' : 'Sign Up'}
                {!loading && <ArrowRight size={16} />}
              </button>

              <div className="text-center mt-5">
                <button
                  type="button"
                  onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}
                  className="text-sm font-medium text-muted-foreground hover:text-primary-400 transition-colors"
                >
                  {mode === 'signin'
                    ? "Don't have an account? Sign up"
                    : 'Already have an account? Sign in'}
                </button>
              </div>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
