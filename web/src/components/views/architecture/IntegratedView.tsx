import { motion } from 'framer-motion'
import { Combine, Database, Network, Server, BrainCircuit, MonitorSmartphone, RefreshCw, Box, Lock, Activity, Clock, CheckCircle2 } from 'lucide-react'

export function IntegratedView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto space-y-16 pb-32"
    >
      <section id="integrated" className="scroll-mt-32">
        <div className="mb-12 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-bold uppercase tracking-wider mb-4">
            <Combine size={14} /> The Grand Finale
          </div>
          <h2 className="text-5xl font-bold tracking-tight mb-6 text-white">The Unified Architecture</h2>
          <p className="text-xl text-muted-foreground max-w-4xl mx-auto leading-relaxed">
            This is how all subsystems operate together in the wild. A highly durable, event-driven architecture that bridges strict structured graphs with dynamic, unstructured language generation.
          </p>
        </div>

        {/* Narrative Section: The Symphony of Subsystems */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-16 mb-20">
           
           <div className="bg-white/5 border border-white/10 rounded-3xl p-8 shadow-xl hover:bg-white/10 transition-colors">
             <div className="w-14 h-14 bg-blue-500/20 border border-blue-500/30 rounded-2xl flex items-center justify-center text-blue-400 mb-6">
                <Box size={24} />
             </div>
             <h3 className="text-xl font-bold text-white mb-3">API & Transactional Outbox</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               The FastAPI layer receives requests but avoids heavy blocking logic. Instead, it strictly utilizes the <strong>Transactional Outbox Pattern</strong>—writing business data (like a new note) and an event record into SQLite in a single transaction, guaranteeing data consistency without external dependencies.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-3xl p-8 shadow-xl hover:bg-white/10 transition-colors">
             <div className="w-14 h-14 bg-purple-500/20 border border-purple-500/30 rounded-2xl flex items-center justify-center text-purple-400 mb-6">
                <Server size={24} />
             </div>
             <h3 className="text-xl font-bold text-white mb-3">Event Dispatch & Redis</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               A relentless background dispatcher polls the SQLite Outbox and safely relays pending events to <strong>Redis Streams</strong>. Redis serves as the durable queue, fanning out events via Consumer Groups to isolated Python worker nodes capable of scaling horizontally.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-3xl p-8 shadow-xl hover:bg-white/10 transition-colors">
             <div className="w-14 h-14 bg-red-500/20 border border-red-500/30 rounded-2xl flex items-center justify-center text-red-400 mb-6">
                <Lock size={24} />
             </div>
             <h3 className="text-xl font-bold text-white mb-3">Workers & Idempotency</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               Workers consume the Redis stream, but before executing, they acquire <strong>Idempotency Locks</strong> using unique constraints in the <code>event_handler_runs</code> table. This ensures network retries or crashes never result in duplicate processing.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-3xl p-8 shadow-xl hover:bg-white/10 transition-colors">
             <div className="w-14 h-14 bg-emerald-500/20 border border-emerald-500/30 rounded-2xl flex items-center justify-center text-emerald-400 mb-6">
                <Activity size={24} />
             </div>
             <h3 className="text-xl font-bold text-white mb-3">LangGraph State Machine</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               Once a worker acquires a lock, it delegates the heavy lifting to LangGraph workflows. These durable state machines orchestrate semantic splitting, LLM-based entity extraction, and massive vector embeddings while recovering gracefully from failures.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-3xl p-8 shadow-xl hover:bg-white/10 transition-colors">
             <div className="w-14 h-14 bg-pink-500/20 border border-pink-500/30 rounded-2xl flex items-center justify-center text-pink-400 mb-6">
                <Database size={24} />
             </div>
             <h3 className="text-xl font-bold text-white mb-3">The Multi-Tier Storage</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               Extracted knowledge is distributed efficiently: Vector embeddings sink into <strong>ChromaDB</strong> for semantic similarity, while exact lexical text and explicit knowledge graph edges are committed to <strong>SQLite FTS</strong>. 
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-3xl p-8 shadow-xl hover:bg-white/10 transition-colors">
             <div className="w-14 h-14 bg-orange-500/20 border border-orange-500/30 rounded-2xl flex items-center justify-center text-orange-400 mb-6">
                <BrainCircuit size={24} />
             </div>
             <h3 className="text-xl font-bold text-white mb-3">The Query Engine</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               The read-path is an explosive orchestration of Query Engineering (decomposing questions), semantic caching, and a massive 3-Prong Parallel Traversal (Vector + Lexical + Graph) powered by <code>asyncio.gather</code>, before a final LLM synthesizes the verified answer.
             </p>
           </div>
        </div>

        {/* The Massive Integrated Terminal Trace */}
        <div className="space-y-6">
          <h3 className="text-3xl font-bold text-white flex items-center gap-4">
             <Activity className="text-emerald-400" size={32} />
             End-to-End System Trace
          </h3>
          <p className="text-lg text-muted-foreground max-w-4xl">
            This terminal view visualizes exactly how data flows across process boundaries, from a user clicking "Save Note" all the way through the background ingestion pipeline, and finally out to a real-time SSE listener.
          </p>

          <div className="bg-[#050505] rounded-3xl border border-white/10 overflow-hidden shadow-2xl mt-8">
            {/* Terminal Header */}
            <div className="bg-black/60 border-b border-white/10 px-6 py-4 flex items-center justify-between backdrop-blur-xl">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-red-500/50"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500/50"></div>
                <div className="w-3 h-3 rounded-full bg-emerald-500/50"></div>
              </div>
              <div className="font-mono text-xs text-white/40 uppercase tracking-widest flex items-center gap-2">
                <Clock size={12} /> Live Trace: Note Creation → Indexing → Notification
              </div>
            </div>

            {/* Terminal Body */}
            <div className="p-8 overflow-x-auto">
              <div className="min-w-[1000px] flex flex-col font-mono text-sm leading-relaxed">
                
                {/* Process 1: HTTP API */}
                <div className="mb-8">
                  <div className="flex items-center gap-3 text-blue-400 font-bold bg-blue-500/10 px-4 py-2 rounded-lg border border-blue-500/20 w-fit mb-4">
                    <MonitorSmartphone size={16} /> [Process 1] FastAPI Server (Thread A)
                  </div>
                  
                  <div className="pl-6 border-l-2 border-blue-500/20 space-y-3">
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.001</span>
                      <span className="text-emerald-400">INFO</span>
                      <span className="text-white">Received POST /notes/</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.005</span>
                      <span className="text-blue-400">SQL </span>
                      <span className="text-slate-300">BEGIN TRANSACTION</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.006</span>
                      <span className="text-blue-400">SQL </span>
                      <span className="text-slate-300">INSERT INTO notes (id, text) VALUES ('note_123', '...')</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.007</span>
                      <span className="text-blue-400">SQL </span>
                      <span className="text-slate-300">INSERT INTO event_outbox (topic, payload) VALUES ('note.created', '{"{"}id: "note_123"{"}"}')</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.008</span>
                      <span className="text-blue-400">SQL </span>
                      <span className="text-slate-300">COMMIT TRANSACTION</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.010</span>
                      <span className="text-emerald-400">INFO</span>
                      <span className="text-white">Returned HTTP 200 OK to Client. (API Request Complete)</span>
                    </div>
                  </div>
                </div>

                {/* Process 2: Background Dispatcher */}
                <div className="mb-8">
                  <div className="flex items-center gap-3 text-purple-400 font-bold bg-purple-500/10 px-4 py-2 rounded-lg border border-purple-500/20 w-fit mb-4">
                    <Server size={16} /> [Process 2] Background Sweeper Task (Asyncio loop)
                  </div>
                  
                  <div className="pl-6 border-l-2 border-purple-500/20 space-y-3">
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.500</span>
                      <span className="text-purple-400">POLL</span>
                      <span className="text-slate-300">SELECT * FROM event_outbox WHERE status = 'pending'</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.505</span>
                      <span className="text-purple-400">REDIS</span>
                      <span className="text-white font-bold">XADD unmessit:events * topic note.created payload '{"{"}id: "note_123"{"}"}'</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.510</span>
                      <span className="text-blue-400">SQL </span>
                      <span className="text-slate-300">UPDATE event_outbox SET status = 'published' WHERE id = 1</span>
                    </div>
                  </div>
                </div>

                {/* Process 3: Worker Node */}
                <div className="mb-8">
                  <div className="flex items-center gap-3 text-orange-400 font-bold bg-orange-500/10 px-4 py-2 rounded-lg border border-orange-500/20 w-fit mb-4">
                    <Box size={16} /> [Process 3] Isolated Worker Node (redis_stream.py)
                  </div>
                  
                  <div className="pl-6 border-l-2 border-orange-500/20 space-y-3">
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.515</span>
                      <span className="text-orange-400">REDIS</span>
                      <span className="text-white font-bold">XREADGROUP GROUP ingest_workers consumer_1 STREAMS unmessit:events &gt;</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:01.518</span>
                      <span className="text-orange-400">LOCK</span>
                      <span className="text-slate-300">INSERT INTO event_handler_runs (handler, event_id) → <span className="text-emerald-400 font-bold">SUCCESS (Acquired Lock)</span></span>
                    </div>
                    
                    {/* Nested LangGraph */}
                    <div className="mt-4 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-2 text-emerald-500/20"><Network size={40} /></div>
                      <div className="text-emerald-400 font-bold mb-3">LANGGRAPH: DurableIngestRunner.run()</div>
                      <div className="space-y-2 pl-4 border-l border-emerald-500/30">
                        <div className="flex items-center gap-3"><CheckCircle2 size={12} className="text-emerald-500"/> <span className="text-slate-300">node:load_raw_input (checkpoint saved)</span></div>
                        <div className="flex items-center gap-3"><CheckCircle2 size={12} className="text-emerald-500"/> <span className="text-slate-300">node:source_chunks (split into 3 chunks, checkpoint saved)</span></div>
                        <div className="flex items-center gap-3"><RefreshCw size={12} className="text-indigo-400 animate-spin"/> <span className="text-white">node:recall (LLM Extracting subjects...)</span></div>
                        <div className="flex items-center gap-3 mt-4"><CheckCircle2 size={12} className="text-emerald-500"/> <span className="text-slate-300">node:recall (Deduplicated 4 keys, checkpoint saved)</span></div>
                        <div className="flex items-center gap-3"><CheckCircle2 size={12} className="text-emerald-500"/> <span className="text-slate-300">node:source_vectors (Embeddings sent to ChromaDB)</span></div>
                        <div className="flex items-center gap-3"><CheckCircle2 size={12} className="text-emerald-500"/> <span className="text-slate-300">node:complete</span></div>
                      </div>
                    </div>

                    <div className="flex gap-4 mt-4">
                      <span className="text-white/30">10:00:15.200</span>
                      <span className="text-orange-400">REDIS</span>
                      <span className="text-white font-bold">PUBLISH unmessit:sse:instance:node-1 '{"{"}topic: "ingest.complete"{"}"}'</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:15.205</span>
                      <span className="text-orange-400">REDIS</span>
                      <span className="text-white font-bold">XACK unmessit:events ingest_workers 1720230000000-0</span>
                    </div>
                  </div>
                </div>

                {/* Process 4: SSE Gateway */}
                <div className="mb-4">
                  <div className="flex items-center gap-3 text-pink-400 font-bold bg-pink-500/10 px-4 py-2 rounded-lg border border-pink-500/20 w-fit mb-4">
                    <Activity size={16} /> [Process 4] Target API Server (SSE Gateway)
                  </div>
                  
                  <div className="pl-6 border-l-2 border-pink-500/20 space-y-3">
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:15.207</span>
                      <span className="text-pink-400">REDIS</span>
                      <span className="text-slate-300">Received message on subscription <span className="text-white">unmessit:sse:instance:node-1</span></span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-white/30">10:00:15.210</span>
                      <span className="text-pink-400">HTTP </span>
                      <span className="text-white font-bold">Sent SSE packet to active Client connection</span>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>

      </section>
    </motion.div>
  )
}
