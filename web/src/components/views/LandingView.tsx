import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  Database,
  FileText,
  FolderTree,
  GitBranch,
  Link2,
  MousePointerClick,
  Network,
  PlusCircle,
  Quote,
  RefreshCw,
  Search,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { useEffect, useState } from 'react'

/* ─── Feature Cards ───────────────────────────────────────────────── */
const featureCards = [
  {
    icon: PlusCircle,
    label: 'Append-Aware Memory',
    body: 'Add or edit notes without babysitting the index. New chunks, vectors, tags, and folder paths sync into retrieval.',
  },
  {
    icon: Network,
    label: 'Multi-Hop Reasoning',
    body: 'By traversing your cross-linked notes, the engine pieces together facts scattered across multiple documents.',
  },
  {
    icon: Quote,
    label: 'Inline Citations',
    body: 'Answers can carry source chips in the paragraph itself, with cited text available before you leave the answer.',
  },
  {
    icon: FolderTree,
    label: 'Flexible Organisation',
    body: 'Structure your knowledge your way using unlimited nested directories and flexible tags.',
  },
  {
    icon: Activity,
    label: 'Transparent Indexing',
    body: 'Track the indexing progress of every note. See exactly when jobs are queued, running, or failed.',
  },
]

/* ─── Hero demo ───────────────────────────────────────────────────── */
const heroQuery = "Based on my wife's personality, what gift should I get?"
const heroAnswer =
  'She has mentioned better coffee gear three times, and your notes say she likes practical gifts with a ritual around them. Best bet: a burr grinder plus a small tasting set.'

const heroSteps = [
  { label: 'Search', detail: 'vector + text', icon: Search },
  { label: 'Recall', detail: 'linked notes', icon: Network },
  { label: 'Reason', detail: 'rank evidence', icon: Brain },
  { label: 'Cite', detail: 'exact spans', icon: Quote },
]

const heroSources = [
  { file: 'wife_preferences.md', detail: 'lines 12-18', icon: FileText },
  { file: 'coffee_shop_chat.txt', detail: 'lines 41-44', icon: Quote },
  { file: '#gift_task', detail: 'recall link', icon: Link2 },
]

const heroMetrics = [
  { label: 'tokens saved', value: '42%', icon: Zap },
  { label: 'recall links', value: '7', icon: Link2 },
  { label: 'source chunks', value: '3', icon: Database },
]

const flowCards = [
  {
    icon: PlusCircle,
    label: 'Append data',
    body: 'Drop in new notes or edits. Source chunks and metadata update without a full rebuild.',
  },
  {
    icon: Brain,
    label: 'Ask a reasoning question',
    body: 'Hybrid search gathers exact terms, semantic matches, and recall-linked context.',
  },
  {
    icon: MousePointerClick,
    label: 'Open the cited line',
    body: 'Inline source chips preview the quote, then jump straight into the note highlight.',
  },
]

/* ─── Component ───────────────────────────────────────────────────── */
export function LandingView() {
  const [demoTick, setDemoTick] = useState(0)

  const [termTick, setTermTick] = useState(0)
  const [pipeTick, setPipeTick] = useState(0)

  const queryChars = Math.min(heroQuery.length, Math.max(0, demoTick - 4))
  const retrievalTick = demoTick - heroQuery.length - 12
  const activeStep =
    retrievalTick < 0 ? -1 : Math.min(heroSteps.length - 1, Math.floor(retrievalTick / 12))
  const answerChars = Math.max(0, Math.min(heroAnswer.length, (demoTick - heroQuery.length - 62) * 4))
  const typedQuery = heroQuery.slice(0, queryChars)
  const typedAnswer = heroAnswer.slice(0, answerChars)
  const showSources = demoTick > heroQuery.length + 48
  const showMetrics = demoTick > heroQuery.length + 72

  useEffect(() => {
    const id = window.setInterval(() => setDemoTick((t) => (t + 1) % 190), 75)
    const termId = window.setInterval(() => setTermTick((t) => (t + 1) % 150), 100)
    const pipeId = window.setInterval(() => setPipeTick((t) => (t + 1) % 100), 100)
    return () => {
      window.clearInterval(id)
      window.clearInterval(termId)
      window.clearInterval(pipeId)
    }
  }, [])

  return (
    <div className="landing-page">
      {/* ── Hero ── */}
      <section className="landing-hero">
        <div className="landing-hero-copy">
          <div className="brand-mark" aria-hidden="true">
            <img src="/favicon.svg" alt="" />
          </div>
          <p className="eyebrow">Personal RAG AI</p>
          <h1>
            Messy notes become answers you can <span>trust.</span>
          </h1>
          <p className="hero-subcopy">
            Stop digging through folders for forgotten ideas. Append messy data, ask a reasoning question, and get a synthesized answer with cited lines you can open instantly.
          </p>
          <div className="hero-pills">
            <span><PlusCircle size={14} /> Append-friendly indexing</span>
            <span><Brain size={14} /> Source-grounded reasoning</span>
            <span><Quote size={14} /> Inline cited lines</span>
          </div>
        </div>

        <div className="answer-demo product-demo" aria-label="Animated retrieval answer demo">
          <div className="demo-window-bar">
            <span className="demo-window-dots" aria-hidden="true">
              <i /><i /><i />
            </span>
            <span className="demo-live-status">Live retrieval</span>
          </div>

          <div className="demo-query">
            <Search size={20} />
            <span>
              {typedQuery}
              <b className="typing-caret" aria-hidden="true" />
            </span>
          </div>

          <div className="demo-step-row" aria-label="Retrieval progress">
            {heroSteps.map((step, i) => (
              <div
                key={step.label}
                className={`demo-step ${i === activeStep ? 'active' : ''} ${i < activeStep ? 'done' : ''}`}
              >
                <step.icon size={16} />
                <span>{step.label}</span>
                <small>{step.detail}</small>
              </div>
            ))}
          </div>

          <div className="demo-answer">
            <div>
              <Bot size={18} />
              <strong>Answer</strong>
              <span>grounded</span>
            </div>
            <p>{typedAnswer || 'Reading notes, recall links, and exact source spans…'}</p>
            <div className={`demo-inline-cites ${showSources ? 'show' : ''}`} aria-label="Inline citation preview">
              <button type="button">Source 1: lines 12-18</button>
              <button type="button">Source 2: lines 41-44</button>
            </div>
          </div>

          <div className={`evidence-row source-strip ${showSources ? 'show' : ''}`}>
            {heroSources.map((s) => (
              <span key={s.file}>
                <s.icon size={15} />
                <strong>{s.file}</strong>
                <small>{s.detail}</small>
              </span>
            ))}
          </div>

          <div className={`metric-strip ${showMetrics ? 'show' : ''}`}>
            {heroMetrics.map((m) => (
              <span key={m.label}>
                <m.icon size={15} />
                <strong>{m.value}</strong>
                {m.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="rag-flow-strip" aria-label="RAG demo flow">
        {flowCards.map((item) => (
          <article key={item.label}>
            <div><item.icon size={18} /></div>
            <strong>{item.label}</strong>
            <span>{item.body}</span>
          </article>
        ))}
      </section>

      {/* ── Highlight 1: Engine ── */}
      <section className="showcase-split">
        <div className="showcase-text">
          <div className="showcase-kicker accent-sky">
            <Network size={16} />
            Data & Retrieval Engine
          </div>
          <h2>Changing notes still retrieve cleanly.</h2>
          <p className="showcase-sub">
            Static RAG gets stale when notes are appended, edited, moved, or tagged. This engine keeps chunks, vectors, lexical search, and recall links aligned as your knowledge base changes.
          </p>
          
          <div className="showcase-features">
            <div className="sc-feat-card">
              <Database size={18} className="text-sky-400" />
              <strong>Continuous Indexing</strong>
              <span>Raw text flows in; chunks, vectors, and folder metadata are managed separately. No stale states or full rebuilds.</span>
            </div>
            <div className="sc-feat-card">
              <GitBranch size={18} className="text-sky-400" />
              <strong>Hybrid Recall Search</strong>
              <span>Lexical + vector search casts a wide net, then recall links pull in scattered context for synthesis.</span>
            </div>
          </div>
        </div>

        <div className="showcase-graphic accent-sky product-demo">
          <div className="demo-window-bar">
            <span className="demo-window-dots"><i/><i/><i/></span>
            <span className="demo-live-status text-sky-400">Pipeline Flow</span>
          </div>
          
          <div className="pipeline-visual">
            <svg viewBox="0 0 400 300" className="pipeline-svg" aria-hidden="true">
               <path className="pipe-glow sky" d="M 50 150 C 150 50, 250 50, 350 150" fill="none" />
               <path className="pipe-glow sky" d="M 50 150 C 150 250, 250 250, 350 150" fill="none" />
               <path className="pipe-line" d="M 50 150 L 350 150" fill="none" />
            </svg>
            
            <div className={`node left transition-all duration-500 ${pipeTick < 25 ? 'scale-110 shadow-[0_0_20px_rgba(56,189,248,0.4)]' : 'opacity-60'}`}>
               <FileText size={20} />
               <span>Raw Notes</span>
            </div>
            
            <div className={`node center transition-all duration-500 ${pipeTick >= 25 && pipeTick < 70 ? 'scale-110' : 'opacity-60'}`}>
               <Brain size={24} className="text-sky-400" />
               <div className={`orbit sky ${pipeTick >= 25 && pipeTick < 70 ? 'fast' : ''}`}></div>
               <div className={`orbit sky delayed ${pipeTick >= 25 && pipeTick < 70 ? 'fast' : ''}`}></div>
            </div>
            
            <div className={`node right transition-all duration-500 ${pipeTick >= 70 ? 'scale-110 shadow-[0_0_20px_rgba(56,189,248,0.4)]' : 'opacity-60'}`}>
               <CheckCircle2 size={20} className="text-sky-400" />
               <span>Grounded Context</span>
            </div>
            
            <div className={`floating-tag t1 transition-opacity duration-300 ${pipeTick >= 25 && pipeTick < 70 ? 'opacity-100' : 'opacity-20'}`}>Vectors</div>
            <div className={`floating-tag t2 transition-opacity duration-300 ${pipeTick >= 25 && pipeTick < 70 ? 'opacity-100' : 'opacity-20'}`}>Lexical</div>
            <div className={`floating-tag t3 transition-opacity duration-300 ${pipeTick >= 25 && pipeTick < 70 ? 'opacity-100' : 'opacity-20'}`}>Recall Links</div>
          </div>
        </div>
      </section>

      {/* ── Highlight 2: Durability ── */}
      <section className="showcase-split reverse">
        <div className="showcase-text">
          <div className="showcase-kicker accent-violet">
            <ShieldCheck size={16} />
            Durable Execution
          </div>
          <h2>Jobs pause. They never fail.</h2>
          <p className="showcase-sub">
            AI APIs drop connections and timeout. Instead of crashing halfway and leaving a corrupted index, long-running jobs are checkpointed in SQLite.
          </p>
          
          <div className="showcase-features">
            <div className="sc-feat-card">
              <RefreshCw size={18} className="text-violet-400" />
              <strong>Chunk-level Checkpoints</strong>
              <span>State is persisted at every step. If a model call fails, the system waits and resumes precisely where it left off.</span>
            </div>
            <div className="sc-feat-card">
              <Activity size={18} className="text-violet-400" />
              <strong>Complete Auditability</strong>
              <span>Because jobs are tracked in a database, you can inspect progress, replay failures, and trace the exact lineage of an answer.</span>
            </div>
          </div>
        </div>

        <div className="showcase-graphic accent-violet product-demo">
           <div className="demo-window-bar">
            <span className="demo-window-dots"><i/><i/><i/></span>
            <span className="demo-live-status text-violet-400">Job State</span>
          </div>
          
          <div className="terminal-ui">
             <div className={`term-line success transition-opacity duration-300 ${termTick >= 0 ? 'opacity-100' : 'opacity-0'}`}>
               <CheckCircle2 size={14}/>
               <span>Chunk 142 ... Processed</span>
             </div>
             <div className={`term-line success transition-opacity duration-300 ${termTick >= 20 ? 'opacity-100' : 'opacity-0'}`}>
               <CheckCircle2 size={14}/>
               <span>Chunk 143 ... Processed</span>
             </div>
             <div className={`term-line error transition-opacity duration-300 ${termTick >= 40 ? 'opacity-100' : 'opacity-0'}`}>
               <RefreshCw size={14} className={termTick >= 40 && termTick < 80 ? "animate-spin" : ""} />
               <span>Chunk 144 ... API Timeout (Waiting 5s)</span>
             </div>
             <div className={`term-line pending mt-4 transition-opacity duration-300 ${termTick >= 80 ? 'opacity-100' : 'opacity-0'}`}>
               <span>... Checkpoint saved to SQLite.</span>
             </div>
             <div className={`term-line pending transition-opacity duration-300 ${termTick >= 110 ? 'opacity-100' : 'opacity-0'}`}>
               <span>... Ready to resume at Chunk 144.</span>
             </div>
          </div>
        </div>
      </section>

      {/* ── Feature Cards ── */}
      <section className="feat-section">
        <p className="eyebrow" style={{ textAlign: 'center' }}>Built in</p>
        <h2 className="feat-heading">Everything the system needs.</h2>
        <div className="feat-grid">
          {featureCards.map((f) => (
            <article key={f.label} className="feat-card">
              <div className="feat-icon">
                <f.icon size={18} />
              </div>
              <h3>{f.label}</h3>
              <p>{f.body}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
