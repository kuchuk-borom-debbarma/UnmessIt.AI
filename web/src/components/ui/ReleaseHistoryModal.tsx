import { ExternalLink, X, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import type { VersionInfo } from '../../lib/useVersionCheck'

type ReleaseHistoryModalProps = {
  isOpen: boolean
  onClose: () => void
  versionInfo: VersionInfo | null
  currentVersion: string
  updateAvailable?: boolean
}

const REPOSITORY_URL = 'https://github.com/kuchuk-borom-debbarma/UnmessIt.AI'

export function ReleaseHistoryModal({ isOpen, onClose, versionInfo, currentVersion, updateAvailable = false }: ReleaseHistoryModalProps) {
  if (!isOpen || !versionInfo) return null
  const history = versionInfo.history?.length ? versionInfo.history : [{ version: versionInfo.version, changelog: versionInfo.changelog }]

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-md"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <motion.div
          role="dialog"
          aria-modal="true"
          className="max-h-[88vh] w-full max-w-3xl flex flex-col rounded-lg border border-border bg-card p-0 shadow-2xl overflow-hidden"
          initial={{ opacity: 0, y: 18, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 18, scale: 0.98 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border/60 bg-input/20 px-6 py-4">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Sparkles size={18} className="text-primary-400" />
                Release History
                <span className="rounded-full bg-primary-500/15 px-2 py-0.5 text-xs font-bold text-primary-400">
                  New: v{versionInfo.version}
                </span>
              </h2>
              <p className="text-xs font-medium text-muted-foreground mt-1">
                You are currently on version {currentVersion}
              </p>
            </div>
            <button className="icon-btn" onClick={onClose} aria-label="Close modal">
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="mb-5 flex flex-wrap gap-2">
              {history.map((release) => (
                <span key={release.version} className="rounded-lg border border-border bg-input px-3 py-1 text-xs font-bold text-muted-foreground">
                  v{release.version}
                </span>
              ))}
            </div>
            <div className="space-y-8">
              {history.map((release) => (
                <section key={release.version} className="border-b border-border/50 pb-6 last:border-b-0 last:pb-0">
                  <div className="prose prose-invert prose-p:leading-relaxed prose-pre:bg-zinc-900 max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                    >
                      {release.changelog}
                    </ReactMarkdown>
                  </div>
                </section>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-border/60 bg-input/20 px-6 py-4">
            <p className="text-xs text-muted-foreground font-medium">
              {updateAvailable ? 'Open the repository to update your install.' : 'You are viewing the bundled release history.'}
            </p>
            <div className="flex gap-3">
              <button className="premium-btn premium-btn-secondary h-10 px-4" onClick={onClose}>
                Close
              </button>
              {updateAvailable && (
                <a className="premium-btn premium-btn-primary h-10 px-4 gap-2" href={REPOSITORY_URL} target="_blank" rel="noreferrer">
                  <ExternalLink size={16} /> View on GitHub
                </a>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
