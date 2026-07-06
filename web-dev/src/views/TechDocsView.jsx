import React, { useState, useEffect, useRef } from 'react';

const SECTIONS = [
  { id: 'overview',   label: 'System Overview',     icon: '◈' },
  { id: 'ingestion',  label: 'Ingestion Pipeline',  icon: '⟶' },
  { id: 'chunking',   label: 'Text Chunking',       icon: '⊞' },
  { id: 'recall',     label: 'Recall Graph',        icon: '⟲' },
  { id: 'query',      label: 'Query Pipeline',      icon: '◎' },
  { id: 'breakdown',  label: 'Query Breakdown',     icon: '⊕' },
  { id: 'search',     label: 'Evidence Search',     icon: '⊘' },
  { id: 'caching',    label: 'Multi-Layer Caching', icon: '▣' },
  { id: 'durability', label: 'Durable Job System',  icon: '⬡' },
  { id: 'eda',        label: 'Event-Driven System', icon: '⇌' },
  { id: 'sse',        label: 'SSE Progress Stream', icon: '↺' },
  { id: 'embedding',  label: 'Embedding System',    icon: '⟡' },
  { id: 'storage',    label: 'Storage Layer',       icon: '⊗' },
  { id: 'settings',   label: 'Settings & Presets',  icon: '⚙' },
];

const T = {
  bg: '#0f1115',
  panel: 'rgba(25,28,35,0.7)',
  border: 'rgba(255,255,255,0.08)',
  borderStrong: 'rgba(99,102,241,0.35)',
  primary: '#6366f1',
  primaryDim: 'rgba(99,102,241,0.15)',
  purple: '#a855f7',
  green: '#22c55e',
  greenDim: 'rgba(34,197,94,0.12)',
  amber: '#f59e0b',
  amberDim: 'rgba(245,158,11,0.12)',
  red: '#ef4444',
  cyan: '#22d3ee',
  cyanDim: 'rgba(34,211,238,0.12)',
  t1: '#f8fafc',
  t2: '#94a3b8',
  t3: '#64748b',
  code: 'rgba(8,10,18,0.95)',
  grad: 'linear-gradient(135deg,#a855f7,#6366f1)',
};

const H1 = ({ children, accent }) => (
  <h2 style={{
    fontSize: 26, fontWeight: 800, color: T.t1, margin: '0 0 8px',
    background: accent ? T.grad : undefined,
    WebkitBackgroundClip: accent ? 'text' : undefined,
    WebkitTextFillColor: accent ? 'transparent' : undefined,
  }}>{children}</h2>
);

const H2 = ({ children }) => (
  <h3 style={{ fontSize: 18, fontWeight: 700, color: T.t1, margin: '32px 0 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
    <span style={{ width: 3, height: 20, background: T.grad, borderRadius: 4, display: 'inline-block', flexShrink: 0 }} />
    {children}
  </h3>
);

const H3 = ({ children }) => (
  <h4 style={{ fontSize: 13, fontWeight: 700, margin: '20px 0 8px', textTransform: 'uppercase', letterSpacing: '0.08em', color: T.t2 }}>{children}</h4>
);

const P = ({ children }) => <p style={{ color: T.t2, fontSize: 14, lineHeight: 1.85, marginBottom: 14 }}>{children}</p>;
const Lead = ({ children }) => <p style={{ color: '#cbd5e1', fontSize: 15, lineHeight: 1.9, marginBottom: 18 }}>{children}</p>;

const Code = ({ code, lang }) => (
  <pre style={{ background: T.code, border: `1px solid ${T.borderStrong}`, borderRadius: 10, padding: '14px 18px', overflowX: 'auto', fontSize: 12.5, lineHeight: 1.75, color: '#e2e8f0', fontFamily: '"Fira Code","Cascadia Code","Consolas",monospace', marginBottom: 18, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
    {lang && <div style={{ color: T.t3, fontSize: 10, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>{lang}</div>}
    {code}
  </pre>
);

const Callout = ({ type = 'info', title, children }) => {
  const map = { info: [T.primary, T.primaryDim, '◈'], warn: [T.amber, T.amberDim, '⚠'], success: [T.green, T.greenDim, '✓'], key: [T.cyan, T.cyanDim, '◎'] };
  const [color, bg, icon] = map[type] || map.info;
  return (
    <div style={{ border: `1px solid ${color}33`, borderLeft: `3px solid ${color}`, background: bg, borderRadius: 10, padding: '12px 16px', marginBottom: 16, display: 'flex', gap: 12 }}>
      <span style={{ color, fontSize: 16, flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <div>
        {title && <div style={{ color, fontSize: 12, fontWeight: 700, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{title}</div>}
        <div style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.75 }}>{children}</div>
      </div>
    </div>
  );
};

const Badge = ({ children, color = T.primary }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', padding: '2px 8px', borderRadius: 6, background: `${color}22`, color, fontSize: 11, fontWeight: 600, fontFamily: 'monospace', border: `1px solid ${color}33`, marginRight: 4 }}>{children}</span>
);

const Table = ({ headers, rows }) => (
  <div style={{ overflowX: 'auto', marginBottom: 20 }}>
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr style={{ borderBottom: `1px solid ${T.borderStrong}` }}>
          {headers.map(h => <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: T.primary, fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} style={{ borderBottom: `1px solid rgba(255,255,255,0.04)`, background: i % 2 === 0 ? 'rgba(255,255,255,0.015)' : 'transparent' }}>
            {row.map((cell, j) => <td key={j} style={{ padding: '8px 12px', color: j === 0 ? '#e2e8f0' : j === 1 ? T.green : T.t2, fontFamily: j <= 1 ? 'monospace' : 'inherit', fontSize: j <= 1 ? 12 : 13 }}>{cell}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const ArrowDefs = () => (
  <defs>
    <marker id="ah"   markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill={T.primary} /></marker>
    <marker id="ah-a" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill={T.amber} /></marker>
    <marker id="ah-g" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill={T.green} /></marker>
    <marker id="ah-c" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill={T.cyan} /></marker>
    <marker id="ah-r" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill={T.red} /></marker>
    <marker id="ah-p" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill={T.purple} /></marker>
  </defs>
);

const Box = ({ x, y, w = 150, h = 44, label, sub, fill = '#1e293b', stroke = T.primary, fs = 12 }) => (
  <g>
    <rect x={x} y={y} width={w} height={h} rx={8} fill={fill} stroke={stroke} strokeWidth="1.5" />
    <text x={x + w / 2} y={y + (sub ? h / 2 - 5 : h / 2 + 4)} textAnchor="middle" fill={T.t1} fontSize={fs} fontFamily="Inter,sans-serif" fontWeight="600">{label}</text>
    {sub && <text x={x + w / 2} y={y + h / 2 + 10} textAnchor="middle" fill={T.t2} fontSize={10} fontFamily="Inter,sans-serif">{sub}</text>}
  </g>
);

const Diamond = ({ x, y, w = 120, h = 44, label }) => {
  const cx = x + w / 2, cy = y + h / 2;
  return (
    <g>
      <polygon points={`${cx},${y} ${x + w},${cy} ${cx},${y + h} ${x},${cy}`} fill="#1e293b" stroke={T.amber} strokeWidth="1.5" />
      <text x={cx} y={cy + 4} textAnchor="middle" fill={T.t1} fontSize={10} fontFamily="Inter,sans-serif" fontWeight="600">{label}</text>
    </g>
  );
};

const L = ({ x, y, children, color = T.t2, fs = 10 }) => (
  <text x={x} y={y} textAnchor="middle" fill={color} fontSize={fs} fontFamily="Inter,sans-serif">{children}</text>
);

const DiagramWrap = ({ title, height = 300, vb, children }) => (
  <div style={{ background: 'rgba(10,14,25,0.92)', border: `1px solid ${T.borderStrong}`, borderRadius: 14, padding: '20px 18px', marginBottom: 28 }}>
    {title && <div style={{ fontSize: 11, color: T.primary, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 16, paddingBottom: 10, borderBottom: `1px solid rgba(99,102,241,0.15)` }}>◈ {title}</div>}
    <div style={{ overflowX: 'auto' }}>
      <svg width="100%" height={height} viewBox={vb || `0 0 800 ${height}`} style={{ minWidth: 560, display: 'block' }}>
        <ArrowDefs />
        {children}
      </svg>
    </div>
  </div>
);

function SectionOverview() {
  return (
    <div>
      <H1 accent>System Overview</H1>
      <Lead>UnmessIt.AI is a personal AI memory system. It ingests free-form journal entries, extracts structured knowledge, and answers questions with precise cited evidence. Every component is designed for correctness, durability, and low-latency.</Lead>

      <DiagramWrap title="High-Level System Architecture" height={320}>
        <Box x={10}  y={138} w={120} h={44} label="Web Client"     sub="React + Vite"        stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={195} y={58}  w={130} h={44} label="FastAPI"         sub="HTTP + SSE"          stroke={T.primary} />
        <Box x={195} y={138} w={130} h={44} label="Ingest API"      sub="/notes → jobs"       stroke={T.green}  fill="rgba(34,197,94,0.08)" />
        <Box x={195} y={218} w={130} h={44} label="Query API"       sub="/query → stream"     stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <Box x={390} y={58}  w={145} h={44} label="Durable Ingest"  sub="LangGraph stages"    stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={390} y={138} w={145} h={44} label="RAG Service"     sub="evidence + answer"   stroke={T.primary} />
        <Box x={390} y={218} w={145} h={44} label="Event Bus"       sub="Redis Streams"       stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={600} y={58}  w={140} h={44} label="SQLite"          sub="jobs · chunks · recall" stroke={T.t3} />
        <Box x={600} y={138} w={140} h={44} label="ChromaDB"        sub="vectors · sem cache" stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <Box x={600} y={218} w={140} h={44} label="Redis"           sub="cache · SSE · streams" stroke={T.red}  fill="rgba(239,68,68,0.08)" />
        <path d="M 130 150 Q 162 80 193 80" stroke={T.cyan} strokeWidth="1.5" fill="none" markerEnd="url(#ah-c)" />
        <line x1={130} y1={160} x2={193} y2={160} stroke={T.cyan} strokeWidth="1.5" markerEnd="url(#ah-c)" />
        <path d="M 130 170 Q 162 240 193 240" stroke={T.cyan} strokeWidth="1.5" fill="none" markerEnd="url(#ah-c)" />
        <line x1={325} y1={80}  x2={388} y2={80}  stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={325} y1={160} x2={388} y2={160} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={325} y1={240} x2={388} y2={240} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={535} y1={80}  x2={598} y2={80}  stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={535} y1={160} x2={598} y2={160} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={535} y1={240} x2={598} y2={240} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <path d="M 195 68 Q 158 26 130 144" stroke={T.cyan} strokeWidth="1.2" fill="none" strokeDasharray="5,3" />
        <L x={160} y={22} color={T.t3}>SSE stream back</L>
      </DiagramWrap>

      <H2>Core Design Principles</H2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 14, marginBottom: 24 }}>
        {[
          { icon: '⬡', title: 'Durability First',       color: T.amber,   desc: 'Every ingest job persists to SQLite with per-unit checkpoints. A crash mid-ingest resumes from the last completed checkpoint — no work is lost.' },
          { icon: '▣', title: 'Multi-Layer Caching',    color: T.cyan,    desc: 'Exact hash → semantic vector → LRU memory → Redis. Query results are reused aggressively to cut LLM cost.' },
          { icon: '⟲', title: 'Recall Expansion',       color: T.green,   desc: 'Named entities extracted into a knowledge graph. At query time, subjects expand the evidence window beyond raw vector similarity.' },
          { icon: '⊕', title: 'Query Decomposition',    color: T.purple,  desc: 'Complex queries are broken into focused sub-queries by an LLM. Each sub-query runs independent parallel evidence searches.' },
          { icon: '◎', title: 'Multi-Tenant Isolation', color: T.primary, desc: 'Every DB query, vector collection, and cache key is namespaced by user_id. No data bleeds between users at any layer.' },
          { icon: '⇌', title: 'Event-Driven Reactions', color: T.red,     desc: 'Note lifecycle events publish to a Redis Stream. RAG listeners react asynchronously to keep all derived data in sync.' },
        ].map(({ icon, title, color, desc }) => (
          <div key={title} style={{ background: T.panel, border: `1px solid ${T.border}`, borderTop: `2px solid ${color}`, borderRadius: 10, padding: '16px 16px 14px' }}>
            <div style={{ color, fontSize: 20, marginBottom: 8 }}>{icon}</div>
            <div style={{ color: T.t1, fontSize: 13, fontWeight: 700, marginBottom: 6 }}>{title}</div>
            <div style={{ color: T.t2, fontSize: 12.5, lineHeight: 1.7 }}>{desc}</div>
          </div>
        ))}
      </div>

      <H2>Technology Stack</H2>
      <Table
        headers={['Layer', 'Technology', 'Role']}
        rows={[
          ['HTTP Server',     'FastAPI + uvicorn',               'Async HTTP, SSE streaming, routing'],
          ['AI Orchestration','LangGraph (StateGraph)',           'Ingest stages + retrieval graph as typed state machines'],
          ['LLM Client',      'LangChain (langchain_json)',       'JSON-mode LLM calls with caching and rate limiting'],
          ['Vector Store',    'ChromaDB',                        'Semantic similarity search and semantic cache collections'],
          ['Relational Store','SQLite (WAL mode)',                'Notes, chunks, recall keys, ingest jobs, event outbox'],
          ['Cache / Pub-Sub', 'Redis',                           'Retrieval cache, embedding cache, SSE fanout, event streams'],
          ['Embedding Cache', 'Memory LRU + Redis (30d TTL)',    'In-process LRU + Redis-backed for embedding vectors'],
          ['Event Bus',       'Redis Streams + SQLite outbox',   'Reliable at-least-once event delivery across processes'],
          ['Frontend',        'React + Vite + react-router',     'SPA with ingest, explorer, query, and docs views'],
        ]}
      />
    </div>
  );
}

function SectionIngestion() {
  return (
    <div>
      <H1 accent>Ingestion Pipeline</H1>
      <Lead>When a note is created or updated, UnmessIt.AI runs a multi-stage durable ingestion pipeline. The pipeline transforms raw text into searchable evidence with LLM summaries, recall links, and vector embeddings. Every stage is checkpointed so it resumes from exactly where it left off after any failure.</Lead>

      <DiagramWrap title="Ingestion Entry Points" height={200}>
        <Box x={10}  y={78}  w={140} h={44} label="API POST /notes"          sub="HTTP route"            stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={10}  y={138} w={140} h={44} label="note.created event"       sub="Redis Stream listener" stroke={T.green}  fill="rgba(34,197,94,0.08)" />
        <Box x={220} y={108} w={140} h={44} label="DurableIngest"            sub=".submit()"             stroke={T.primary} />
        <Box x={430} y={78}  w={160} h={44} label="raw_inputs.save_or_reuse" sub="SQLite idempotency"    stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={430} y={138} w={160} h={44} label="repository.create_or_reuse" sub="ingest_jobs table"  stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={660} y={108} w={130} h={44} label="DurableScheduler"         sub="asyncio task"          stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <line x1={150} y1={100} x2={218} y2={120} stroke={T.cyan}    strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={150} y1={160} x2={218} y2={138} stroke={T.green}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={360} y1={118} x2={428} y2={100} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={360} y1={128} x2={428} y2={150} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={590} y1={100} x2={658} y2={118} stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={590} y1={160} x2={658} y2={138} stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah)" />
      </DiagramWrap>

      <H2>Idempotent Submission</H2>
      <P>Before any processing, raw text is hashed as <Badge color={T.amber}>SHA-256(user_id + "\0" + text)</Badge>. The system checks if a job for that exact hash already exists: if aborted it requeues, if waiting-retry it resumes, if complete or running the existing job is returned. Resubmitting the same note text is always a database-level no-op.</P>
      <Callout type="key" title="Idempotency Key">The content hash is the idempotency key for the entire ingest system. Duplicate text from any source — API, event listener, or manual retry — always resolves to a single ingest job.</Callout>

      <DiagramWrap title="Full Ingest LangGraph — Stage Sequence" height={360} vb="0 0 800 360">
        <Box x={10}  y={158} w={95}  h={44} label="START"         stroke={T.green}   fill="rgba(34,197,94,0.12)" />
        <Box x={140} y={158} w={130} h={44} label="load_raw_input" sub="resolve + checkpoint"   stroke={T.primary} />
        <Diamond x={315} y={148} w={100} h={64} label="corrupt?" />
        <Box x={460} y={40}  w={130} h={44} label="abort"          sub="delete chunks + fail"   stroke={T.red}    fill="rgba(239,68,68,0.08)" />
        <Box x={460} y={158} w={130} h={44} label="source_chunks"  sub="draft + assemble + save" stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={460} y={270} w={130} h={44} label="recall"         sub="build recall links"     stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <Box x={630} y={158} w={130} h={44} label="recall_vectors" sub="embed recall keys"      stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={630} y={270} w={130} h={44} label="source_vectors" sub="embed source chunks"    stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={630} y={40}  w={130} h={44} label="complete"       sub="persist final counts"   stroke={T.green}  fill="rgba(34,197,94,0.08)" />
        <Box x={630} y={316} w={130} h={44} label="END"            stroke={T.t3}  fill="#1e293b" />
        <line x1={105} y1={180} x2={138} y2={180} stroke={T.green}   strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <line x1={270} y1={180} x2={313} y2={180} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={365} y1={155} x2={458} y2={62}  stroke={T.red}    strokeWidth="1.5" markerEnd="url(#ah-r)" />
        <L x={398} y={95} color={T.red}>yes</L>
        <line x1={415} y1={180} x2={458} y2={180} stroke={T.amber}  strokeWidth="1.5" markerEnd="url(#ah-a)" />
        <L x={434} y={174} color={T.t3}>no</L>
        <line x1={590} y1={292} x2={628} y2={292} stroke={T.purple} strokeWidth="1.5" markerEnd="url(#ah-c)" />
        <line x1={590} y1={180} x2={628} y2={180} stroke={T.amber}  strokeWidth="1.5" markerEnd="url(#ah-c)" />
        <line x1={695} y1={270} x2={695} y2={204} stroke={T.cyan}   strokeWidth="1.5" markerEnd="url(#ah-c)" strokeDasharray="5,3" />
        <line x1={695} y1={158} x2={695} y2={84}  stroke={T.cyan}   strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <line x1={695} y1={314} x2={695} y2={330} stroke={T.t3}     strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={590} y1={62}  x2={628} y2={62}  stroke={T.red}    strokeWidth="1.5" markerEnd="url(#ah-g)" />
      </DiagramWrap>

      <H2>Stages In Depth</H2>
      <H3>Stage 1 — load_raw_input</H3>
      <P>Loads raw text from the <Badge>raw_inputs</Badge> SQLite table and resolves <Badge>directory_path</Badge> from the note's parent directory. Writes a checkpoint so a crash before the next stage is detectable on resume.</P>
      <H3>Stage 2 — source_chunks (INGEST_PARALLELISM = 3)</H3>
      <P>Text is windowed into overlapping chunks. Each window gets a deterministic unit key: <Badge color={T.amber}>SHA-256(raw_input_id + start + end + text)</Badge>. The runner checks completed checkpoints and skips already-saved chunks. Pending chunks are processed <Badge color={T.purple}>3 at a time</Badge> via asyncio.Semaphore. Each task runs <strong>SourceChunkDrafts</strong> (LLM summary) then <strong>SourceChunkAssembler</strong> (metadata assembly) then saves to SQLite.</P>
      <H3>Stage 3 — recall</H3>
      <P>For each source chunk, the <strong>RecallIndex</strong> LLM chain extracts named entities and writes <Badge>recall_keys</Badge> + <Badge>recall_links</Badge> to SQLite. Chunks that already have recall links are detected and marked as reuse — no duplicate LLM calls.</P>
      <H3>Stage 4 — recall_vectors</H3>
      <P>All recall keys linked to this job's chunks are retrieved. Missing vector embeddings are computed in batches (configurable <Badge color={T.cyan}>embedding_batch_size</Badge>) and stored in ChromaDB for fast fuzzy recall-key lookup during queries.</P>
      <H3>Stage 5 — source_vectors</H3>
      <P>Same batch-embedding logic for source chunks themselves. Each chunk's full text is embedded and stored in ChromaDB, enabling the primary vector similarity search during retrieval.</P>
      <Callout type="warn" title="Retry Backoff">On any unit failure, <code>repository.schedule_retry()</code> sets <code>next_run_at</code> with exponential backoff (configurable via <code>ingest_retry_backoff_seconds</code>). The scheduler sleeps until that time then re-runs the full LangGraph — which skips all completed checkpoints and only retries the failed unit.</Callout>
    </div>
  );
}

function SectionChunking() {
  return (
    <div>
      <H1 accent>Text Chunking</H1>
      <Lead>Raw journal text is split into overlapping windows before any LLM processing. The windowing strategy preserves context across chunk boundaries so evidence is never cut off mid-thought.</Lead>
      <DiagramWrap title="Overlapping Sliding Window Strategy" height={190} vb="0 0 800 190">
        <rect x={20} y={25} width={760} height={30} rx={6} fill="rgba(99,102,241,0.1)" stroke={T.border} strokeWidth="1" />
        <L x={400} y={46} fs={12} color={T.t2}>Raw Text (e.g. 2800 characters)</L>
        <rect x={20}  y={82} width={300} height={26} rx={6} fill="rgba(99,102,241,0.2)"   stroke={T.primary} strokeWidth="1.5" />
        <L x={170} y={100} color={T.t1} fs={11}>Window 1 (chunk_size = 1000)</L>
        <rect x={220} y={118} width={300} height={26} rx={6} fill="rgba(168,85,247,0.18)"  stroke={T.purple}  strokeWidth="1.5" />
        <L x={370} y={137} color={T.t1} fs={11}>Window 2 (overlap = 200)</L>
        <rect x={420} y={82} width={300} height={26} rx={6} fill="rgba(34,211,238,0.15)"  stroke={T.cyan}    strokeWidth="1.5" />
        <L x={570} y={100} color={T.t1} fs={11}>Window 3</L>
        <rect x={220} y={80} width={100} height={68} rx={4} fill="rgba(245,158,11,0.06)" stroke={T.amber} strokeWidth="1" strokeDasharray="4,3" />
        <L x={270} y={165} color={T.amber} fs={10}>overlap zone</L>
        <rect x={420} y={80} width={100} height={68} rx={4} fill="rgba(245,158,11,0.06)" stroke={T.amber} strokeWidth="1" strokeDasharray="4,3" />
        <L x={470} y={165} color={T.amber} fs={10}>overlap zone</L>
      </DiagramWrap>
      <Table headers={['Setting','Default','Description']} rows={[
        ['chunk_size','1000 chars','Maximum characters per source window'],
        ['chunk_overlap','200 chars','Characters shared between adjacent windows to preserve context'],
        ['embedding_batch_size','100','Chunks sent to embedding API in a single batch call'],
      ]} />
      <H2>Source Window Keying</H2>
      <P>Each window gets a unit key: <Badge color={T.amber}>SHA-256(raw_input_id + ":" + start + ":" + end + ":" + SHA-256(text))</Badge>. This key is the checkpoint key (so ingest skips already-processed windows) and also derives the stable chunk ID, making saves idempotent even if the process crashes before the checkpoint is written.</P>
      <H2>Draft → Assembly → Save</H2>
      <P>Two LLM sub-chains run sequentially per window:</P>
      <ol style={{ color: T.t2, fontSize: 14, lineHeight: 2.1, paddingLeft: 20 }}>
        <li><strong style={{ color: T.t1 }}>SourceChunkDrafts</strong> — LLM writes a compact summary of the chunk: main topics, key facts, and entities mentioned. Stored alongside full text.</li>
        <li><strong style={{ color: T.t1 }}>SourceChunkAssembler</strong> — combines raw text window, summary, and metadata (raw_input_id, user_id, directory_path, processing_settings, llm_rotation_preset) into the final <Badge>SourceChunk</Badge> saved to SQLite.</li>
      </ol>
      <Callout type="success" title="Why Store Full Text + Summary?">Full chunk text is the verbatim evidence given to the LLM during query answering. The summary is a semantic search hook — condensed meaning improves embedding quality and retrieval accuracy.</Callout>
    </div>
  );
}

function SectionRecall() {
  return (
    <div>
      <H1 accent>Recall Graph</H1>
      <Lead>After source chunks are saved, a knowledge graph is built by extracting named entities from the text and linking them to the chunks they appear in. This recall graph lets the query pipeline expand evidence beyond raw vector similarity — finding chunks connected to a topic even when the exact wording differs.</Lead>
      <DiagramWrap title="Recall Graph Structure" height={280} vb="0 0 800 280">
        <Box x={10}  y={50}  w={160} h={44} label="Source Chunk A" sub="text + summary" stroke={T.primary} />
        <Box x={10}  y={120} w={160} h={44} label="Source Chunk B" sub="text + summary" stroke={T.primary} />
        <Box x={10}  y={190} w={160} h={44} label="Source Chunk C" sub="text + summary" stroke={T.primary} />
        <Box x={310} y={30}  w={130} h={36} label="recall_key: Alice"    sub="type=person" stroke={T.green}  fill="rgba(34,197,94,0.08)"   fs={11} />
        <Box x={310} y={98}  w={130} h={36} label="recall_key: Project X" sub="type=topic" stroke={T.amber}  fill="rgba(245,158,11,0.08)"  fs={11} />
        <Box x={310} y={166} w={130} h={36} label="recall_key: Meeting"  sub="type=event" stroke={T.purple} fill="rgba(168,85,247,0.08)"  fs={11} />
        <Box x={310} y={234} w={130} h={36} label="recall_key: London"   sub="type=place" stroke={T.cyan}   fill="rgba(34,211,238,0.08)"  fs={11} />
        <Box x={560} y={108} w={170} h={44} label="recall_key_vectors" sub="ChromaDB collection" stroke={T.t3} fill="rgba(100,116,139,0.1)" />
        <line x1={170} y1={72}  x2={308} y2={48}  stroke={T.green}  strokeWidth="1.2" markerEnd="url(#ah)" />
        <line x1={170} y1={72}  x2={308} y2={116} stroke={T.amber}  strokeWidth="1.2" markerEnd="url(#ah)" />
        <line x1={170} y1={142} x2={308} y2={116} stroke={T.amber}  strokeWidth="1.2" markerEnd="url(#ah)" />
        <line x1={170} y1={142} x2={308} y2={184} stroke={T.purple} strokeWidth="1.2" markerEnd="url(#ah)" />
        <line x1={170} y1={212} x2={308} y2={184} stroke={T.purple} strokeWidth="1.2" markerEnd="url(#ah)" />
        <line x1={170} y1={212} x2={308} y2={252} stroke={T.cyan}   strokeWidth="1.2" markerEnd="url(#ah)" />
        <line x1={440} y1={116} x2={558} y2={130} stroke={T.green}  strokeWidth="1.2" strokeDasharray="4,3" markerEnd="url(#ah-g)" />
        <line x1={440} y1={184} x2={558} y2={148} stroke={T.purple} strokeWidth="1.2" strokeDasharray="4,3" markerEnd="url(#ah-g)" />
        <L x={498} y={102} color={T.t3}>embedded</L>
      </DiagramWrap>
      <H2>How Recall Works</H2>
      <P>For each source chunk, the LLM runs the <strong>RecallIndex</strong> chain. It returns structured JSON with <Badge>recall_keys</Badge> (canonical name + type: person, place, event, topic) and <Badge>recall_links</Badge> (edges connecting each key to each chunk, with relationship description). Keys and links are saved to SQLite. Keys are also embedded into ChromaDB for vector-searchable lookup during query time.</P>
      <H2>Recall Expansion During Query</H2>
      <P>When a user asks a question, the <strong>SubjectsNode</strong> in the retrieval LangGraph extracts implied subjects from the query (e.g. "What did Alice say about the project?" → subjects: ["Alice", "project"]). These subjects are looked up against recall keys via vector similarity. Matched recall keys expand the evidence set by pulling all source chunks linked to those keys, even if those chunks weren't hit by primary vector search.</P>
      <Callout type="key" title="Why Recall Matters">Pure vector search finds semantically similar text. Recall expansion finds factually related text — chunks mentioning the same entity with completely different wording. Critical for person-centric queries like "What do I know about Bob?" or "When did Carol last visit?".</Callout>
      <Table headers={['Table','Columns','Purpose']} rows={[
        ['recall_keys',        'id, user_id, name, type, metadata',                     'Canonical named entities extracted from notes'],
        ['recall_links',       'recall_key_id, source_chunk_id, user_id, description',  'Graph edges connecting entities to evidence chunks'],
        ['recall_key_vectors', 'ChromaDB collection per user_id',                       'Vector embeddings of recall key names for fuzzy lookup'],
      ]} />
    </div>
  );
}

function SectionQuery() {
  return (
    <div>
      <H1 accent>Query Pipeline</H1>
      <Lead>When a user asks a question, the query pipeline runs a staged process: cache lookup → evidence retrieval → LLM verification → answer generation. The entire pipeline emits real-time SSE progress events so the frontend shows detailed step-by-step status.</Lead>
      <DiagramWrap title="Top-Level Query Flow" height={380} vb="0 0 800 380">
        <Box x={10}  y={168} w={90}  h={36} label="User Query"          stroke={T.cyan}   fill="rgba(34,211,238,0.08)" fs={11} />
        <Diamond x={140} y={155} w={100} h={64} label="Exact cache?" />
        <Diamond x={295} y={155} w={110} h={64} label="Semantic cache?" />
        <Box x={450} y={28}  w={130} h={36} label="Cache HIT"           sub="return instantly"    stroke={T.green}  fill="rgba(34,197,94,0.1)"  fs={11} />
        <Box x={450} y={155} w={130} h={36} label="QueryEvidenceChain"  sub="breakdown + search"  stroke={T.primary} fs={11} />
        <Box x={450} y={230} w={130} h={36} label="QueryVerifierChain"  sub="on/off-topic filter" stroke={T.amber}  fill="rgba(245,158,11,0.08)" fs={11} />
        <Diamond x={450} y={290} w={120} h={60} label="needs_retry?" />
        <Box x={295} y={303} w={120} h={36} label="Retry Evidence"      sub="re-run with retry_q" stroke={T.purple} fill="rgba(168,85,247,0.08)" fs={11} />
        <Box x={620} y={230} w={130} h={36} label="QueryAnswerChain"    sub="cite + synthesize"   stroke={T.green}  fill="rgba(34,197,94,0.1)"  fs={11} />
        <Box x={620} y={155} w={130} h={36} label="Write caches"        sub="exact + semantic"    stroke={T.t3}     fill="rgba(100,116,139,0.08)" fs={10} />
        <Box x={620} y={310} w={130} h={36} label="SSE Response"        sub="QueryResult to client" stroke={T.cyan} fill="rgba(34,211,238,0.08)" fs={11} />
        <line x1={100} y1={186} x2={138} y2={186} stroke={T.cyan}    strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={240} y1={186} x2={293} y2={186} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={240} y1={166} x2={448} y2={46}  stroke={T.green}   strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <line x1={405} y1={186} x2={448} y2={173} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <L x={426} y={168} color={T.t3} fs={9}>miss</L>
        <line x1={515} y1={191} x2={515} y2={228} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={515} y1={266} x2={515} y2={288} stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={450} y1={320} x2={415} y2={321} stroke={T.purple}  strokeWidth="1.5" markerEnd="url(#ah-a)" />
        <L x={432} y={314} color={T.amber} fs={9}>yes</L>
        <path d="M 355 321 Q 330 265 448 248" stroke={T.purple} strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ah)" />
        <line x1={580} y1={248} x2={618} y2={248} stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <L x={596} y={242} color={T.t3} fs={9}>no</L>
        <line x1={685} y1={230} x2={685} y2={193} stroke={T.green}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={685} y1={266} x2={685} y2={308} stroke={T.green}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={355} y1={165} x2={448} y2={46}  stroke={T.green}   strokeWidth="1.5" strokeDasharray="4,3" markerEnd="url(#ah-g)" />
      </DiagramWrap>
      <H2>Cache Hierarchy at Query Time</H2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
        <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16 }}>
          <div style={{ color: T.green, fontWeight: 700, fontSize: 13, marginBottom: 8 }}>1. Exact Cache (~1ms)</div>
          <div style={{ color: T.t2, fontSize: 13, lineHeight: 1.75 }}>Key = <code style={{ color: T.cyan, fontSize: 12 }}>SHA-256(query + user_id + llm_settings + filters_sig)</code>. Hit returns the full QueryResult immediately — zero LLM calls, zero vector search.</div>
        </div>
        <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16 }}>
          <div style={{ color: T.purple, fontWeight: 700, fontSize: 13, marginBottom: 8 }}>2. Semantic Cache (~50ms)</div>
          <div style={{ color: T.t2, fontSize: 13, lineHeight: 1.75 }}>Query text is embedded and searched against a per-user ChromaDB collection (<Badge color={T.purple}>threshold=0.85</Badge>). If a similar past query is found, the LLM verifier checks whether the old answer still applies before returning it.</div>
        </div>
      </div>
      <H2>Filter Namespace Isolation</H2>
      <P>Queries with directory or tag filters get a separate cache namespace: <Badge color={T.amber}>SHA-256[:16] of the sorted filter set</Badge>. Filtered and unfiltered queries never share cache entries.</P>
      <H2>LLM Metrics Tracking</H2>
      <P>Every LLM call accumulates token counts via the <Badge>async_report</Badge> callback. The final <Badge>QueryResult</Badge> includes <Badge color={T.cyan}>llm_saved_metrics</Badge> with total prompt tokens, completion tokens, and LLM call count for full observability.</P>
    </div>
  );
}

function SectionBreakdown() {
  return (
    <div>
      <H1 accent>Query Breakdown</H1>
      <Lead>Complex questions are decomposed into focused sub-queries by an LLM before any evidence search begins. Each sub-query targets a single aspect of the question. This dramatically improves recall for multi-faceted questions while simple questions pass through with no overhead.</Lead>
      <DiagramWrap title="LangGraph Retrieval Graph — 3-Node Pipeline" height={150} vb="0 0 800 150">
        <Box x={10}  y={53} w={80}  h={44} label="START"          stroke={T.green}  fill="rgba(34,197,94,0.1)" />
        <Box x={160} y={53} w={150} h={44} label="breakdown_node" sub="LLM: decompose query"  stroke={T.primary} />
        <Box x={390} y={53} w={150} h={44} label="subjects_node"  sub="LLM: extract subjects" stroke={T.purple}  fill="rgba(168,85,247,0.08)" />
        <Box x={620} y={53} w={130} h={44} label="search_node"    sub="parallel evidence"     stroke={T.amber}   fill="rgba(245,158,11,0.08)" />
        <line x1={90}  y1={75} x2={158} y2={75} stroke={T.green}   strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <line x1={310} y1={75} x2={388} y2={75} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={540} y1={75} x2={618} y2={75} stroke={T.purple}  strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={750} y1={75} x2={790} y2={75} stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah-a)" />
        <L x={795} y={78} color={T.t3} fs={9}>END</L>
      </DiagramWrap>
      <H2>Breakdown Node</H2>
      <P>The LLM is prompted to produce up to <Badge color={T.primary}>MAX_SUB_QUERIES = 6</Badge> focused questions. The original query is always first so simple questions run with exactly one search pass — no extra LLM latency. On any LLM failure, the node falls back to <code>[query]</code> so retrieval always runs.</P>
      <Code lang="example" code={`Query: "What were Alice's concerns about Project X and how did they affect the timeline?"\n\nSub-queries produced:\n  1. (original) "What were Alice's concerns about Project X and how did they affect the timeline?"\n  2. "What concerns did Alice raise about Project X?"\n  3. "How did Alice's concerns affect the project timeline?"\n  4. "What was the timeline or schedule for Project X?"`} />
      <H2>Caching for Breakdown</H2>
      <P>The breakdown result is cached. The key includes query text, user_id, and full system+human prompt (so a prompt change invalidates it). Asking the same question again skips the breakdown LLM call entirely.</P>
      <H2>Subject Extraction Node</H2>
      <P>Runs after breakdown. Extracts <em>implied subjects</em> — entities the query is about, even if described rather than named (e.g. "the tall manager" may match recall_key "Bob" if notes describe Bob as tall). These subjects feed directly into the search node for recall key lookup.</P>
      <H2>Special Query Expansion</H2>
      <P>Before vector search, the search node detects query type and expands the sub-query with semantic synonyms:</P>
      <Table headers={['Trigger Words','Expansion Terms Added','Use Case']} rows={[
        ['appearance, trait, detail, feature, body, look', 'attribute, physical, feature, property, mark, height, build…', 'Attribute/description queries'],
        ['compare, versus, similar, difference, contrast',  'contrast, parallel, context, background, outcome, decision…',  'Comparison queries'],
        ['why, cause, reason, changed, evolved, impact',    'evidence, sequence, before, after, because, cause, effect…',   'Causal/reasoning queries'],
      ]} />
    </div>
  );
}

function SectionSearch() {
  return (
    <div>
      <H1 accent>Evidence Search</H1>
      <Lead>For each sub-query, three parallel search strategies run concurrently: vector similarity on source chunks, vector similarity on recall keys (expanded to linked chunks), and a direct recall graph lookup by subject name. Results are merged, deduplicated, re-ranked via Reciprocal Rank Fusion, and context-packed.</Lead>
      <DiagramWrap title="Per-Sub-Query Evidence Search (asyncio.gather)" height={270} vb="0 0 800 270">
        <Box x={10}  y={113} w={130} h={44} label="sub_query"            sub="one of N queries"         stroke={T.primary} />
        <Box x={220} y={35}  w={160} h={44} label="Vector Search"        sub="source_chunk_vectors"     stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={220} y={113} w={160} h={44} label="Recall Key Vectors"   sub="recall_key_vectors→chunks" stroke={T.green}  fill="rgba(34,197,94,0.08)" />
        <Box x={220} y={191} w={160} h={44} label="Subject Recall Lookup" sub="name match→linked chunks" stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <Box x={470} y={113} w={130} h={44} label="Merge + Dedupe"       sub="by source_chunk_id"       stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={640} y={73}  w={145} h={44} label="Reciprocal Rank Fusion" sub="score = Σ 1/(k+rank)"  stroke={T.primary} />
        <Box x={640} y={153} w={145} h={44} label="Context Packing"      sub="≤12 chunks, ≤6000 chars"  stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <path d="M 140 135 Q 178 57 218 57"   stroke={T.cyan}   strokeWidth="1.5" fill="none" markerEnd="url(#ah-c)" />
        <line x1={140} y1={135} x2={218} y2={135} stroke={T.green}  strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <path d="M 140 135 Q 178 213 218 213" stroke={T.purple} strokeWidth="1.5" fill="none" markerEnd="url(#ah-p)" />
        <line x1={380} y1={57}  x2={468} y2={125} stroke={T.cyan}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={380} y1={135} x2={468} y2={135} stroke={T.green}  strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={380} y1={213} x2={468} y2={145} stroke={T.purple} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={600} y1={135} x2={638} y2={95}  stroke={T.amber}  strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={600} y1={135} x2={638} y2={175} stroke={T.amber}  strokeWidth="1.5" markerEnd="url(#ah)" />
      </DiagramWrap>
      <H2>Evidence Cache (Sub-Query Level)</H2>
      <P>Before any vector search, the search node checks a Redis evidence cache keyed on: query + sub_queries + subjects + user_id + ChromaDB index version + embedding settings + filter signature. The index_version increments on every chunk add/delete, ensuring new notes always invalidate stale evidence caches.</P>
      <H2>Vector Search — source_chunk_vectors</H2>
      <P>Sub-query text is embedded (with cache) and searched against the per-user ChromaDB source chunk collection using cosine similarity. ChromaDB metadata filters apply <Badge>directory_path</Badge> and <Badge>tags</Badge> restrictions at the vector store layer.</P>
      <H2>Recall Key Vector Search</H2>
      <P>The same embedding searches the recall_key_vectors ChromaDB collection. Matched recall keys are expanded: all source chunks linked to those keys via <Badge>recall_links</Badge> are loaded from SQLite and added to the evidence pool — finding chunks related by entity even if the text wording is completely different.</P>
      <H2>Subject Recall Lookup</H2>
      <P>Subjects extracted by the subjects_node are matched against recall key names using exact + fuzzy name matching in SQLite. This handles cases where the entity name is clearly stated in the query (e.g. "Alice") and pulls all linked chunks regardless of vector similarity.</P>
      <H2>Reciprocal Rank Fusion (RRF)</H2>
      <P>All results from all strategies and sub-queries are combined. Each chunk's RRF score = <code style={{ color: T.cyan }}>Σ 1 / (k + rank)</code> across all result lists (k=60). Chunks appearing high in multiple lists are naturally boosted. Chunks appearing only in one list are not penalised.</P>
      <H2>Context Packing</H2>
      <P>Top <Badge color={T.primary}>MAX_EVIDENCE_CHUNKS = 12</Badge> chunks are selected. Per chunk: up to <Badge>MAX_SNIPPETS_PER_CHUNK = 3</Badge> excerpts of <Badge>MAX_SNIPPET_CHARS = 420 chars</Badge> each are extracted by sub-query relevance. If total context exceeds <Badge color={T.amber}>9000 chars</Badge>, an LLM context compactor reduces it to <Badge color={T.amber}>≤4500 chars</Badge>.</P>
      <Table headers={['Constant','Value','Purpose']} rows={[
        ['MAX_EVIDENCE_CHUNKS','12','Max source chunks passed to verifier + answer chain'],
        ['MAX_SNIPPETS_PER_CHUNK','3','Max excerpts extracted per chunk for LLM context'],
        ['MAX_SNIPPET_CHARS','420','Max chars per excerpt snippet'],
        ['_CONTEXT_CHARS_PER_PASS','6000','Soft limit before context engineering'],
        ['_LLM_CONTEXT_MIN_RAW_CHARS','9000','Minimum raw chars that trigger LLM compaction'],
        ['_LLM_CONTEXT_MAX_PACKED_CHARS','4500','Target max chars after LLM context compaction'],
      ]} />
    </div>
  );
}

function SectionCaching() {
  return (
    <div>
      <H1 accent>Multi-Layer Caching</H1>
      <Lead>UnmessIt.AI runs five distinct cache layers, each with different scope, key strategy, and storage backend. Together they ensure repeated or similar queries return near-instantly while identical computations are never run twice.</Lead>
      <DiagramWrap title="Full Cache Stack — All 5 Layers" height={340} vb="0 0 800 340">
        <Box x={10}  y={148} w={80}  h={44} label="Query"              stroke={T.cyan}   fill="rgba(34,211,238,0.08)" fs={11} />
        <Box x={140} y={30}  w={170} h={44} label="L1: Exact Cache"    sub="memory LRU + Redis, ~1ms"   stroke={T.green}  fill="rgba(34,197,94,0.1)" />
        <Box x={140} y={100} w={170} h={44} label="L2: Semantic Cache" sub="ChromaDB + Redis, ~50ms"    stroke={T.purple} fill="rgba(168,85,247,0.1)" />
        <Box x={140} y={170} w={170} h={44} label="L3: Evidence Cache" sub="sub-query level, Redis"     stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={140} y={240} w={170} h={44} label="L4: Embedding Cache" sub="per-text, memory+Redis 30d" stroke={T.cyan}  fill="rgba(34,211,238,0.08)" />
        <Box x={140} y={310} w={170} h={44} label="L5: LLM Result Cache" sub="verifier/answer, Redis"   stroke={T.primary} />
        <Box x={390} y={30}  w={80} h={36} label="HIT → return" stroke={T.green} fill="rgba(34,197,94,0.08)" fs={10} />
        <Box x={390} y={100} w={80} h={36} label="HIT → return" stroke={T.green} fill="rgba(34,197,94,0.08)" fs={10} />
        <Box x={390} y={170} w={80} h={36} label="HIT → skip"   stroke={T.green} fill="rgba(34,197,94,0.08)" fs={10} />
        <Box x={390} y={240} w={80} h={36} label="HIT → skip"   stroke={T.green} fill="rgba(34,197,94,0.08)" fs={10} />
        <Box x={390} y={310} w={80} h={36} label="HIT → skip"   stroke={T.green} fill="rgba(34,197,94,0.08)" fs={10} />
        <path d="M 90 170 Q 115 52 138 52"   stroke={T.cyan} strokeWidth="1.4" fill="none" markerEnd="url(#ah)" />
        <path d="M 90 170 Q 115 122 138 122" stroke={T.cyan} strokeWidth="1.4" fill="none" markerEnd="url(#ah)" />
        <line x1={90} y1={170} x2={138} y2={192} stroke={T.cyan} strokeWidth="1.4" markerEnd="url(#ah)" />
        <path d="M 90 170 Q 115 262 138 262" stroke={T.cyan} strokeWidth="1.4" fill="none" markerEnd="url(#ah)" />
        <path d="M 90 170 Q 115 332 138 332" stroke={T.cyan} strokeWidth="1.4" fill="none" markerEnd="url(#ah)" />
        <line x1={310} y1={52}  x2={388} y2={48}  stroke={T.green} strokeWidth="1.3" markerEnd="url(#ah-g)" />
        <line x1={310} y1={122} x2={388} y2={118} stroke={T.green} strokeWidth="1.3" markerEnd="url(#ah-g)" />
        <line x1={310} y1={192} x2={388} y2={188} stroke={T.green} strokeWidth="1.3" markerEnd="url(#ah-g)" />
        <line x1={310} y1={262} x2={388} y2={258} stroke={T.green} strokeWidth="1.3" markerEnd="url(#ah-g)" />
        <line x1={310} y1={332} x2={388} y2={328} stroke={T.green} strokeWidth="1.3" markerEnd="url(#ah-g)" />
        <Box x={540} y={148} w={150} h={44} label="Full Retrieval" sub="evidence+verify+answer" stroke={T.primary} />
        <line x1={470} y1={112} x2={538} y2={162} stroke={T.red} strokeWidth="1" strokeDasharray="4,3" />
        <line x1={470} y1={188} x2={538} y2={168} stroke={T.red} strokeWidth="1" strokeDasharray="4,3" />
        <L x={503} y={144} color={T.red} fs={9}>miss ↓</L>
      </DiagramWrap>
      <H2>L1 — Exact Query Cache</H2>
      <P>Key: <code style={{ color: T.cyan }}>SHA-256(query + user_id + llm_settings_signature + filters_signature)</code>. Checked first in in-process <strong>MemoryJsonCache</strong> (LRU, 1000 items), then Redis (24h TTL). Hit returns the complete QueryResult before any embedding or LLM work. LLM settings signature includes model, provider, temperature, and max_tokens — changing any field correctly invalidates cached answers.</P>
      <H2>L2 — Semantic Query Cache</H2>
      <P>Query text is embedded and searched in a per-user ChromaDB collection (<Badge color={T.purple}>threshold=0.85</Badge>). Top-5 past queries checked. Full QueryResult payloads live in Redis (7-day TTL) separately from ChromaDB embeddings. For distance below epsilon <Badge>0.02</Badge>, treated as identical (no verifier call). For genuinely similar-but-different queries, <strong>SemanticCacheVerifierChain</strong> runs an LLM check before returning cached result.</P>
      <H2>L3 — Evidence Search Cache</H2>
      <P>Entire evidence search result (all sub-query hits, merged + context-packed) is cached in Redis. Key includes query, sub-queries, subjects, user_id, ChromaDB <Badge>index_version</Badge>, embedding settings, and filters. The index_version increments on every chunk add/delete, so new notes always invalidate this cache.</P>
      <H2>L4 — Embedding Cache</H2>
      <P>Every embedding API call checks in-process <strong>MemoryEmbeddingCache</strong> (LRU, 10,000 items) then Redis (30-day TTL). Key = <code style={{ color: T.cyan }}>SHA-256(provider + model + base_url + text)</code>. Changing embedding model or provider invalidates all cached vectors for that config.</P>
      <H2>L5 — LLM Result Cache</H2>
      <P>Individual LLM calls (verifier, answer, breakdown) are cached keyed on full system prompt + human prompt + LLM settings. Same question with same evidence set returns the same answer instantly from Redis — no model call.</P>
      <H2>Cache Cleanup Crons</H2>
      <Table headers={['Cron Task','Interval','What It Evicts']} rows={[
        ['_embedding_memory_cron','~10 min (±10% jitter)','Embedding vectors older than 1h from in-process LRU'],
        ['_retrieval_memory_cron','~10 min (±10% jitter)','JSON results older than 1h from in-process LRU'],
        ['_chroma_semantic_cron', '~1 hour (±10% jitter)','Stale ChromaDB semantic cache collections (>24h)'],
      ]} />
      <Callout type="info">±10% jitter on all cron intervals prevents cleanup tasks from running simultaneously on multi-process deployments, reducing I/O spikes.</Callout>
    </div>
  );
}

function SectionDurability() {
  return (
    <div>
      <H1 accent>Durable Job System</H1>
      <Lead>Every ingest operation is represented as a durable job persisted in SQLite. Jobs survive server crashes, support per-unit checkpoints, implement exponential backoff retry, and can be paused, resumed, or aborted via the API. No text is ever silently lost.</Lead>
      <H2>Job State Machine</H2>
      <DiagramWrap title="Ingest Job Status Transitions" height={180} vb="0 0 800 180">
        <Box x={10}  y={68} w={90}  h={44} label="queued"       stroke={T.t3} />
        <Box x={175} y={68} w={100} h={44} label="running"      stroke={T.primary} />
        <Box x={355} y={20} w={100} h={44} label="complete"     stroke={T.green}  fill="rgba(34,197,94,0.08)" />
        <Box x={355} y={120} w={110} h={44} label="waiting_retry" stroke={T.amber} fill="rgba(245,158,11,0.08)" />
        <Box x={540} y={120} w={100} h={44} label="failed"      stroke={T.red}    fill="rgba(239,68,68,0.08)" />
        <Box x={540} y={20}  w={100} h={44} label="aborted"     stroke={T.t3}     fill="rgba(100,116,139,0.06)" />
        <Box x={355} y={68}  w={100} h={44} label="paused"      stroke={T.t3} />
        <line x1={100} y1={90} x2={173} y2={90} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={275} y1={76} x2={353} y2={42}  stroke={T.green} strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <line x1={275} y1={104} x2={353} y2={142} stroke={T.amber} strokeWidth="1.5" markerEnd="url(#ah-a)" />
        <line x1={275} y1={90} x2={353} y2={90}  stroke={T.t3}   strokeWidth="1.2" strokeDasharray="4,3" markerEnd="url(#ah)" />
        <line x1={465} y1={142} x2={538} y2={142} stroke={T.red}  strokeWidth="1.5" markerEnd="url(#ah-r)" />
        <path d="M 460 130 Q 500 90 538 40" stroke={T.t3} strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ah)" />
        <path d="M 465 138 Q 290 200 175 106" stroke={T.amber} strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ah)" />
        <L x={320} y={210} color={T.amber} fs={9}>backoff delay → resume</L>
      </DiagramWrap>
      <H2>Checkpoint System</H2>
      <P>Within each stage, every unit of work (one source chunk, one recall link, one embedding batch) creates a checkpoint row in SQLite: <Badge>running</Badge> → <Badge color={T.green}>complete</Badge> or <Badge color={T.red}>failed</Badge>. On resume, the runner queries all checkpoints and skips units already marked <Badge color={T.green}>complete</Badge>. A job that processed 8/10 chunks before crashing resumes at chunk 9.</P>
      <Table headers={['Checkpoint Status','Meaning','On Resume']} rows={[
        ['running',  'Unit was in progress when crash occurred', 'Retried — may be partially complete'],
        ['complete', 'Unit finished successfully',               'Skipped entirely'],
        ['failed',   'Unit threw an error',                     'Job in waiting_retry; unit retried on resume'],
      ]} />
      <H2>Retry Backoff</H2>
      <P>On unit failure, <Badge>repository.schedule_retry()</Badge> sets <Badge>next_run_at</Badge> to now + backoff seconds. Schedule configurable per-preset via <Badge color={T.amber}>ingest_retry_backoff_seconds</Badge> (e.g. [30, 60, 120, 300, 600]). After <Badge color={T.red}>RETRY_LIMIT</Badge> attempts the job transitions to <Badge color={T.red}>failed</Badge> permanently.</P>
      <H2>DurableScheduler — asyncio Task Management</H2>
      <P>Maintains a <Badge>_running: set[str]</Badge> of active job IDs. Before scheduling, checks this set to prevent duplicate concurrent runs. Each task is named <code style={{ color: T.cyan }}>ingest-{'{job_id[:8]}'}</code> for observability in asyncio task dumps.</P>
      <Code lang="python" code={`# Scheduler run loop — handles retry delay, survives failures\nasync def _run_loop(self, job_id: str) -> None:\n    while True:\n        job = await asyncio.to_thread(repository.get, job_id)\n        if job["status"] in {COMPLETE, FAILED, ABORTED, PAUSED}:\n            return\n        if job["status"] == STATUS_WAITING_RETRY:\n            delay = _delay_seconds(job["next_run_at"])\n            if delay > 0:\n                await asyncio.sleep(delay)   # sleep until backoff expires\n        await self.runner.run_once(job_id)   # re-run LangGraph from checkpoints`} />
      <H2>Startup Resume</H2>
      <P>On server startup, <Badge>RagServiceImpl.resume_pending_jobs()</Badge> queries all jobs in <Badge>queued</Badge>, <Badge>running</Badge>, or <Badge>waiting_retry</Badge> state with a due <Badge>next_run_at</Badge> and schedules them. No job is permanently stuck if the server was killed mid-processing.</P>
    </div>
  );
}

function SectionEDA() {
  return (
    <div>
      <H1 accent>Event-Driven Architecture</H1>
      <Lead>UnmessIt.AI uses an event-driven model for note lifecycle management. Note operations publish domain events to a reliable event bus. RAG listeners subscribe and asynchronously keep all derived data in sync — no polling, no tight coupling.</Lead>
      <DiagramWrap title="Event Bus — Outbox → Redis Stream → Consumers" height={270} vb="0 0 800 270">
        <Box x={10}  y={113} w={130} h={44} label="Note Service"    sub="create/update/move…"   stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={205} y={113} w={130} h={44} label="event_outbox"    sub="SQLite (at-least-once)" stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={400} y={60}  w={140} h={44} label="_dispatch_loop"  sub="reads outbox → xadd"   stroke={T.primary} />
        <Box x={400} y={113} w={140} h={44} label="Redis Stream"    sub="unmessit:events"        stroke={T.red}    fill="rgba(239,68,68,0.08)" />
        <Box x={400} y={166} w={140} h={44} label="_consume_loop"   sub="xreadgroup → dispatch"  stroke={T.primary} />
        <Box x={610} y={30}  w={170} h={34} label="_on_note_created"     sub="→ submit_ingest_job"      stroke={T.green}  fill="rgba(34,197,94,0.08)"  fs={11} />
        <Box x={610} y={74}  w={170} h={34} label="_on_note_updated"     sub="→ re-submit ingest"       stroke={T.green}  fill="rgba(34,197,94,0.08)"  fs={11} />
        <Box x={610} y={118} w={170} h={34} label="_on_note_moved"       sub="→ update directory_path"  stroke={T.amber}  fill="rgba(245,158,11,0.08)" fs={11} />
        <Box x={610} y={162} w={170} h={34} label="_on_note_deleted"     sub="→ delete vectors+chunks"  stroke={T.red}    fill="rgba(239,68,68,0.08)"  fs={11} />
        <Box x={610} y={206} w={170} h={34} label="_on_note_restored"    sub="→ re-index vectors"       stroke={T.purple} fill="rgba(168,85,247,0.08)" fs={11} />
        <Box x={610} y={250} w={170} h={34} label="_on_note_tags_changed" sub="→ delete + re-index"     stroke={T.t3}     fill="rgba(100,116,139,0.08)" fs={11} />
        <line x1={140} y1={135} x2={203} y2={135} stroke={T.cyan}    strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={335} y1={135} x2={398} y2={82}  stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={335} y1={135} x2={398} y2={135} stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={540} y1={82}  x2={608} y2={47}  stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={540} y1={82}  x2={608} y2={91}  stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={540} y1={183} x2={608} y2={135} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={540} y1={183} x2={608} y2={179} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={540} y1={183} x2={608} y2={223} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={540} y1={183} x2={608} y2={267} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
      </DiagramWrap>
      <H2>Transactional Outbox Pattern</H2>
      <P>Events are never published directly to Redis. They are written to an <Badge>event_outbox</Badge> SQLite table in the same transaction as the note mutation. If the server crashes between the DB write and the Redis publish, the event is not lost — the <Badge>_dispatch_loop</Badge> will pick it up on next start.</P>
      <H2>Redis Stream Consumer Group</H2>
      <P>The <Badge>_dispatch_loop</Badge> reads pending outbox events and writes to the Redis Stream (<code style={{ color: T.cyan }}>unmessit:events</code>) via <Badge>xadd</Badge>. The <Badge>_consume_loop</Badge> reads via <Badge>xreadgroup</Badge> with 5-second block. Messages are acknowledged (<Badge>xack</Badge>) after successful dispatch. Stale unacknowledged messages older than 60s are claimed via <Badge>xautoclaim</Badge> and reprocessed.</P>
      <H2>Note Event Handlers</H2>
      <Table headers={['Event','Handler','What It Does']} rows={[
        ['note.created',      '_on_note_created',      'Submits a new durable ingest job for the note text'],
        ['note.updated',      '_on_note_updated',      'Re-submits ingest — idempotent if text unchanged (same hash)'],
        ['note.moved',        '_on_note_moved',        'Resolves new directory_path; updates SQLite + ChromaDB metadata — no re-embedding'],
        ['note.hard_deleted', '_on_note_hard_deleted', 'Deletes chunk vectors from ChromaDB + hard-deletes raw_inputs'],
        ['note.soft_deleted', '_on_note_soft_deleted', 'Soft-deletes raw_inputs; removes vectors from ChromaDB'],
        ['note.restored',     '_on_note_restored',     'Restores raw_inputs + re-indexes chunk vectors in ChromaDB'],
        ['note.tags_changed', '_on_note_tags_changed', 'Deletes then re-indexes chunk vectors to update ChromaDB tag metadata'],
      ]} />
      <Callout type="warn" title="Tags Changed → Re-index, Not Re-embed">When tags change, vectors are deleted and re-indexed but the embedding API is NOT called. ChromaDB can re-index documents with updated metadata without new embeddings, making tag changes fast and cheap.</Callout>
      <H2>In-Memory Fallback</H2>
      <P>If Redis is unavailable (<Badge>get_redis() is None</Badge>), the event bus falls back to an in-process <strong>MemoryEventBus</strong> — a dict of topic → handlers with synchronous in-process dispatch. The system degrades gracefully to single-process mode without Redis rather than failing entirely.</P>
    </div>
  );
}

function SectionSSE() {
  return (
    <div>
      <H1 accent>SSE Progress Streaming</H1>
      <Lead>Every long-running operation emits real-time progress events over Server-Sent Events (SSE). The SSE system uses a dual-backend architecture: in-process pub/sub for single-server deployments, and Redis Pub/Sub fanout for multi-process deployments behind a load balancer.</Lead>
      <DiagramWrap title="SSE Architecture — In-Process vs Redis Fanout" height={260} vb="0 0 800 260">
        <Box x={10}  y={108} w={120} h={44} label="Browser"            sub="EventSource connection"    stroke={T.cyan}   fill="rgba(34,211,238,0.08)" />
        <Box x={200} y={108} w={140} h={44} label="GET /query/stream"  sub="SSE endpoint"              stroke={T.primary} />
        <Box x={410} y={50}  w={160} h={44} label="RedisSseService"    sub="Redis Pub/Sub fanout"      stroke={T.red}    fill="rgba(239,68,68,0.08)" />
        <Box x={410} y={170} w={160} h={44} label="MemorySseService"   sub="In-process asyncio queue"  stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <Box x={410} y={108} w={160} h={44} label="unmessit:sse:{topic}" sub="Redis channel"           stroke={T.red}    fill="rgba(239,68,68,0.06)" />
        <Box x={640} y={108} w={150} h={44} label="ProgressReporter"   sub="async_report() calls"      stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <line x1={130} y1={130} x2={198} y2={130} stroke={T.cyan}    strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={340} y1={130} x2={408} y2={72}  stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={340} y1={130} x2={408} y2={192} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={638} y1={130} x2={572} y2={72}  stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={638} y1={130} x2={572} y2={192} stroke={T.amber}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <L x={410} y={248} color={T.t3} fs={10}>Redis if available; falls back to in-process queue</L>
      </DiagramWrap>
      <H2>Topic Scoping</H2>
      <P>Each SSE connection subscribes to a user-specific topic. In a multi-server setup, the browser may connect to Server A while the query runs on Server B. Server B publishes to Redis channel <code style={{ color: T.cyan }}>unmessit:sse:{'{topic}'}</code>. Server A's background listener (<Badge>psubscribe("unmessit:sse:*")</Badge>) receives it and delivers it to its local MemorySseService queue, which the SSE generator reads.</P>
      <H2>Connection Presence Tracking</H2>
      <P>Each SSE connection writes a presence record to Redis (<Badge color={T.cyan}>unmessit:sse:connections:{'{connection_id}'}</Badge>) with a 30-second TTL, refreshed every 10 seconds by a background task. This tells the system which topics have live subscribers.</P>
      <H2>Hierarchical Progress Events</H2>
      <P>Each progress event carries <Badge>ref</Badge> (unique identifier) and <Badge>parent_ref</Badge> (parent identifier). The frontend uses these to build a collapsible progress tree. Depth counter: 0=top-level query, 1=sub-query evidence or verification, 2=cache hits, 3+=internal LLM provider events.</P>
      <Code lang="progress event shape" code={`{\n  "message": "Drafting summary",\n  "ref":        "source_chunks:unit_abc:draft",\n  "parent_ref": "source_chunks:unit_abc",\n  "depth": 3,\n  "details": { "preset_name": "GPT-4o" }\n}`} />
      <H2>Reporter Stack (Thread/Task-Local)</H2>
      <P>The <Badge>set_progress_reporters()</Badge> / <Badge>reset_progress_reporters()</Badge> pattern maintains a thread-local stack of reporter tokens. Each LLM sub-chain or ingest unit pushes its own reporter so nested operations emit progress events correctly scoped to the right parent — enabling the UI to show exactly where time is spent.</P>
    </div>
  );
}

function SectionEmbedding() {
  return (
    <div>
      <H1 accent>Embedding System</H1>
      <Lead>Embeddings are numerical representations of text that power all vector similarity searches. UnmessIt.AI uses a provider-agnostic embedding pipeline with two-tier caching (in-process LRU + Redis) so each unique text string is only ever embedded once per model.</Lead>
      <DiagramWrap title="Embedding Cache Hit/Miss Flow" height={185} vb="0 0 800 185">
        <Box x={10}  y={70} w={120} h={44} label="text to embed"    sub="chunk/query/recall key"    stroke={T.t3} />
        <Diamond x={185} y={58} w={100} h={64} label="In-memory LRU?" />
        <Diamond x={355} y={58} w={100} h={64} label="Redis cache?" />
        <Box x={520} y={70} w={130} h={44} label="Embedding API"    sub="OpenAI/Ollama/custom"      stroke={T.primary} />
        <Box x={680} y={70} w={110} h={44} label="write both caches" sub="LRU + Redis 30d"           stroke={T.green}  fill="rgba(34,197,94,0.08)" />
        <line x1={130} y1={92} x2={183} y2={90} stroke={T.t3}   strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={285} y1={90} x2={353} y2={90} stroke={T.red}  strokeWidth="1.5" markerEnd="url(#ah-r)" />
        <L x={320} y={84} color={T.red} fs={9}>miss</L>
        <line x1={455} y1={90} x2={518} y2={92} stroke={T.red}  strokeWidth="1.5" markerEnd="url(#ah-r)" />
        <L x={486} y={84} color={T.red} fs={9}>miss</L>
        <line x1={650} y1={92} x2={678} y2={92} stroke={T.green} strokeWidth="1.5" markerEnd="url(#ah-g)" />
        <path d="M 285 78 Q 440 30 678 30 Q 710 30 710 68" stroke={T.green} strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ah-g)" />
        <path d="M 455 78 Q 560 30 678 30" stroke={T.green} strokeWidth="1.2" fill="none" strokeDasharray="4,3" />
        <L x={480} y={20} color={T.green} fs={9}>hit → return vector</L>
      </DiagramWrap>
      <Table headers={['Cache Layer','Backend','Capacity','TTL']} rows={[
        ['MemoryEmbeddingCache', 'In-process OrderedDict (LRU)', '10,000 items', '1h (cron cleanup)'],
        ['RedisEmbeddingCache',  'Redis string (JSON-encoded vector)', 'Unlimited', '30 days'],
      ]} />
      <H2>Cache Key</H2>
      <P>Embedding cache key: <code style={{ color: T.cyan }}>SHA-256(provider + "|" + model + "|" + base_url + "|" + text)</code>. Changing the embedding model or provider invalidates all cached vectors for that configuration.</P>
      <H2>Rate Limiting</H2>
      <P>If <Badge>embedding_rate_limit_per_minute</Badge> is set in the preset, a token-bucket rate limiter wraps all embedding API calls. This prevents hitting provider rate limits during large batch ingests.</P>
      <H2>Provider Agnosticism</H2>
      <P>Any provider with an OpenAI-compatible embeddings endpoint works by setting <Badge>embedding_provider</Badge>, <Badge>embedding_model</Badge>, and <Badge>embedding_base_url</Badge> in the preset. Supports OpenAI, Azure OpenAI, Ollama (local), and any compatible provider.</P>
    </div>
  );
}

function SectionStorage() {
  return (
    <div>
      <H1 accent>Storage Layer</H1>
      <Lead>UnmessIt.AI uses three complementary storage systems: SQLite for durable relational data (notes, chunks, jobs, recall), ChromaDB for vector embeddings and semantic cache, and Redis for high-speed ephemeral cache and pub/sub.</Lead>
      <DiagramWrap title="Storage Topology" height={250} vb="0 0 800 250">
        <Box x={10}  y={103} w={130} h={44} label="Application"    sub="FastAPI + RAG"         stroke={T.primary} />
        <Box x={230} y={30}  w={160} h={44} label="SQLite (WAL mode)" sub="structured + durable" stroke={T.amber}  fill="rgba(245,158,11,0.08)" />
        <Box x={470} y={30}  w={160} h={44} label="ChromaDB"       sub="vector similarity"     stroke={T.purple} fill="rgba(168,85,247,0.08)" />
        <Box x={660} y={103} w={120} h={44} label="Redis"          sub="cache + pub/sub"       stroke={T.red}    fill="rgba(239,68,68,0.08)" />
        <rect x={222} y={88}  width={178} height={154} rx={8} fill="rgba(245,158,11,0.03)" stroke={T.amber}  strokeWidth="1" strokeDasharray="4,3" />
        <L x={311} y={106} color={T.amber} fs={9}>SQLite Tables</L>
        <L x={311} y={120} color={T.t3} fs={9}>notes · directories · tags</L>
        <L x={311} y={133} color={T.t3} fs={9}>raw_inputs · source_chunks</L>
        <L x={311} y={146} color={T.t3} fs={9}>recall_keys · recall_links</L>
        <L x={311} y={159} color={T.t3} fs={9}>ingest_jobs · checkpoints</L>
        <L x={311} y={172} color={T.t3} fs={9}>event_outbox · ai_presets</L>
        <L x={311} y={185} color={T.t3} fs={9}>retrieval_index_version</L>
        <L x={311} y={198} color={T.t3} fs={9}>embedding_batch_queue</L>
        <rect x={462} y={88}  width={178} height={120} rx={8} fill="rgba(168,85,247,0.03)" stroke={T.purple} strokeWidth="1" strokeDasharray="4,3" />
        <L x={551} y={106} color={T.purple} fs={9}>Collections (per user_id)</L>
        <L x={551} y={120} color={T.t3} fs={9}>source_chunk_vectors</L>
        <L x={551} y={133} color={T.t3} fs={9}>recall_key_vectors</L>
        <L x={551} y={146} color={T.t3} fs={9}>semantic_cache:query_result</L>
        <L x={551} y={159} color={T.t3} fs={9}>semantic_cache:evidence-*</L>
        <L x={660} y={165} color={T.t3} fs={9}>retrieval cache (24h)</L>
        <L x={660} y={178} color={T.t3} fs={9}>embedding cache (30d)</L>
        <L x={660} y={191} color={T.t3} fs={9}>SSE channels</L>
        <L x={660} y={204} color={T.t3} fs={9}>event streams</L>
        <line x1={140} y1={115} x2={228} y2={52}  stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={140} y1={125} x2={228} y2={162} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={140} y1={125} x2={468} y2={52}  stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={140} y1={125} x2={468} y2={162} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
        <line x1={140} y1={125} x2={658} y2={125} stroke={T.primary} strokeWidth="1.5" markerEnd="url(#ah)" />
      </DiagramWrap>
      <H2>SQLite — WAL Mode</H2>
      <P>Runs in Write-Ahead Logging (WAL) mode allowing concurrent reads while a write is in progress. Critical because the async server may read ingest job status while another coroutine updates it. All access goes through <Badge>get_connection()</Badge> which returns the thread-local WAL-mode connection.</P>
      <H2>ChromaDB Collections</H2>
      <P>Collections are namespaced per user. Source chunk vectors and recall key vectors each have their own collection. Semantic cache collections are further namespaced by operation (<Badge color={T.purple}>query_result</Badge>, <Badge color={T.purple}>evidence-search-v1</Badge>). Version suffixes in collection names enable schema migrations by changing the suffix to invalidate all old data.</P>
      <H2>Redis Key Patterns</H2>
      <Table headers={['Key Pattern','Content','TTL']} rows={[
        ['unmessit:retrieval:{namespace}:{hash}',    'Full QueryResult JSON',             '24 hours'],
        ['unmessit:semantic_cache:{user_id}:{id}',   'Full QueryResult JSON (sem cache)', '7 days'],
        ['unmessit:embedding:{hash}',                'Embedding vector (JSON array)',     '30 days'],
        ['unmessit:sse:{topic}',                     'Pub/Sub channel (no stored data)',  'N/A'],
        ['unmessit:sse:connections:{conn_id}',       'Connection presence record',        '30s (refreshed)'],
        ['unmessit:events',                          'Redis Stream (event bus)',           'No TTL (consumer-group managed)'],
      ]} />
      <H2>Retrieval Index Version</H2>
      <P>A <Badge>retrieval_index_version</Badge> counter in SQLite increments each time a source chunk vector is added or deleted. The evidence cache key includes this version, so any new note immediately invalidates all evidence caches for that user — search results always reflect the latest indexed data.</P>
    </div>
  );
}

function SectionSettings() {
  return (
    <div>
      <H1 accent>Settings & LLM Presets</H1>
      <Lead>All LLM and embedding settings are managed through named presets stored in SQLite. A preset bundles the LLM provider, model, API key, temperature, embedding settings, chunk size, and retry schedule. The active preset is resolved per-user and per-stage at runtime.</Lead>
      <H2>Preset Fields</H2>
      <Table headers={['Field','Type / Default','Description']} rows={[
        ['llm_provider',               'string / openai',                     'LLM provider (openai, ollama, azure, etc.)'],
        ['llm_model',                  'string / gpt-4o',                     'Model name (gpt-4o, llama3, claude-3-5-sonnet, etc.)'],
        ['llm_base_url',               'string? / null',                      'Custom base URL for non-OpenAI providers or local models'],
        ['llm_api_key',                'string / empty',                      'API key stored in SQLite preset (not env)'],
        ['llm_temperature',            'float / 0.0',                         'Sampling temperature for all LLM calls'],
        ['llm_max_tokens',             'int? / null',                         'Max response tokens (optional hard limit)'],
        ['llm_rate_limit_per_minute',  'int / 0',                             'Token bucket RPM rate limit (0 = unlimited)'],
        ['embedding_provider',         'string / openai',                     'Embedding provider (openai, ollama, etc.)'],
        ['embedding_model',            'string / text-embedding-3-small',     'Embedding model name'],
        ['embedding_batch_size',       'int / 100',                           'Chunks per embedding API batch call'],
        ['chunk_size',                 'int / 1000',                          'Max chars per source window'],
        ['chunk_overlap',              'int / 200',                           'Overlap chars between adjacent windows'],
        ['ingest_retry_backoff_seconds','list[int]',                          'Backoff schedule for ingest unit retries (e.g. [30,60,120])'],
      ]} />
      <H2>LLM Rotation</H2>
      <P>Multiple presets can be active simultaneously. <Badge>get_user_llm_setting_candidates()</Badge> returns an ordered list of active presets for a given stage. This enables cost optimization (fast cheap model for breakdown, powerful model for answer generation) and automatic fallback if one provider is down.</P>
      <H2>Processing Snapshot</H2>
      <P>When a chunk or recall key is saved, the current <Badge>processing_settings</Badge> and <Badge>llm_rotation_preset</Badge> are stored as metadata on the record. This creates an audit trail of exactly which model and settings produced each piece of derived data, enabling full reproducibility and debugging.</P>
      <H2>Docker URL Rewriting</H2>
      <P><Badge>_docker_reachable_url()</Badge> rewrites <code>localhost</code> to <code>host.docker.internal</code> when running inside Docker. This allows Ollama or other local model servers on the host to be reached from the containerized server without manual URL configuration.</P>
      <Callout type="key" title="Cache Invalidation on Settings Change">The LLM settings signature (provider, model, base_url, temperature, max_tokens) is baked into every cache key. Changing any field invalidates all cached LLM results automatically — you will never get an answer from the wrong model due to stale cache.</Callout>
    </div>
  );
}

const SECTION_COMPONENTS = {
  overview: SectionOverview, ingestion: SectionIngestion, chunking: SectionChunking,
  recall: SectionRecall, query: SectionQuery, breakdown: SectionBreakdown,
  search: SectionSearch, caching: SectionCaching, durability: SectionDurability,
  eda: SectionEDA, sse: SectionSSE, embedding: SectionEmbedding,
  storage: SectionStorage, settings: SectionSettings,
};

export default function TechDocsView() {
  const [active, setActive] = useState('overview');
  const [search, setSearch] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const contentRef = useRef(null);

  const SectionComponent = SECTION_COMPONENTS[active] || SectionOverview;
  const filtered = search ? SECTIONS.filter(s => s.label.toLowerCase().includes(search.toLowerCase())) : SECTIONS;

  useEffect(() => { if (contentRef.current) contentRef.current.scrollTop = 0; }, [active]);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', fontFamily: "'Inter',sans-serif", background: T.bg }}>
      <aside style={{ width: sidebarOpen ? 256 : 0, minWidth: sidebarOpen ? 256 : 0, height: '100%', background: 'rgba(13,15,20,0.98)', borderRight: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden', transition: 'width 0.25s ease,min-width 0.25s ease', flexShrink: 0 }}>
        <div style={{ padding: '20px 14px 12px', borderBottom: `1px solid ${T.border}` }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: T.t3, textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 10 }}>Technical Docs</div>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search sections…" style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '7px 12px', color: T.t1, fontSize: 12, outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </div>
        <nav style={{ flex: 1, overflowY: 'auto', padding: '8px 6px' }}>
          {filtered.map(sec => (
            <button key={sec.id} onClick={() => setActive(sec.id)} style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '8px 10px', borderRadius: 8, background: active === sec.id ? 'rgba(99,102,241,0.15)' : 'transparent', border: active === sec.id ? `1px solid ${T.borderStrong}` : '1px solid transparent', color: active === sec.id ? T.primary : T.t2, fontSize: 12.5, fontWeight: active === sec.id ? 600 : 500, cursor: 'pointer', textAlign: 'left', marginBottom: 2, transition: 'all 0.15s ease', fontFamily: 'inherit' }}>
              <span style={{ fontSize: 13, opacity: 0.75 }}>{sec.icon}</span>
              {sec.label}
            </button>
          ))}
        </nav>
        <div style={{ padding: '10px 14px', borderTop: `1px solid ${T.border}` }}>
          <div style={{ fontSize: 11, color: T.t3 }}><span style={{ color: T.green }}>●</span> UnmessIt.AI · {SECTIONS.length} sections</div>
        </div>
      </aside>

      <main ref={contentRef} style={{ flex: 1, overflowY: 'auto', background: T.bg }}>
        <div style={{ position: 'sticky', top: 0, zIndex: 20, background: 'rgba(15,17,21,0.95)', backdropFilter: 'blur(12px)', borderBottom: `1px solid ${T.border}`, padding: '11px 28px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <button onClick={() => setSidebarOpen(o => !o)} style={{ background: 'transparent', border: 'none', color: T.t2, cursor: 'pointer', fontSize: 18, padding: '2px 6px', borderRadius: 6 }} title="Toggle sidebar">☰</button>
          <div style={{ color: T.t3, fontSize: 12 }}>
            <span>Technical Docs</span>
            <span style={{ margin: '0 6px' }}>›</span>
            <span style={{ color: T.primary, fontWeight: 600 }}>{SECTIONS.find(s => s.id === active)?.label}</span>
          </div>
        </div>
        <div style={{ padding: '40px 44px', maxWidth: 900, margin: '0 auto' }}>
          <SectionComponent />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 48, paddingTop: 24, borderTop: `1px solid ${T.border}` }}>
            {(() => {
              const idx = SECTIONS.findIndex(s => s.id === active);
              const prev = SECTIONS[idx - 1];
              const next = SECTIONS[idx + 1];
              return (
                <>
                  {prev ? <button onClick={() => setActive(prev.id)} style={{ background: 'rgba(25,28,35,0.7)', border: `1px solid ${T.border}`, borderRadius: 10, padding: '10px 18px', color: T.t2, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' }}>← {prev.label}</button> : <div />}
                  {next ? <button onClick={() => setActive(next.id)} style={{ background: 'rgba(99,102,241,0.15)', border: `1px solid ${T.borderStrong}`, borderRadius: 10, padding: '10px 18px', color: T.primary, fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>{next.label} →</button> : <div />}
                </>
              );
            })()}
          </div>
        </div>
      </main>
    </div>
  );
}
