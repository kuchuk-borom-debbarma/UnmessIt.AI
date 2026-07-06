import { motion } from 'framer-motion'
import { Database, CheckCircle2, ArrowDown, Server, ArrowRight, Box, ActivitySquare, Activity, Timer, Shield } from 'lucide-react'

export function SupportingSystemsView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-32"
    >
      <section id="supporting-systems" className="scroll-mt-32">
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-bold uppercase tracking-wider mb-4">
            <Server size={14} /> Chapter 3
          </div>
          <h2 className="text-4xl font-bold tracking-tight mb-4 text-white">Supporting Systems</h2>
          <p className="text-lg text-muted-foreground">The unseen infrastructure that makes the engine durable, scalable, and responsive.</p>
        </div>
      
      {/* SubSystem 1: Transactional Outbox */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 text-lg border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]">S1</span>
            The Transactional Outbox
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
            The worst bug in a distributed system is saving a record to the database but failing to send the "start processing" message to the background worker (e.g., if the server crashes in that split second). The <strong>Transactional Outbox pattern</strong> solves this. We insert the Note AND the Message into SQLite in the exact same database transaction.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          <div className="liquid-glass p-8 rounded-3xl border border-white/10 shadow-xl font-mono text-sm text-blue-200/80 overflow-x-auto">
            <pre dangerouslySetInnerHTML={{ __html: `
<span class="text-purple-400">async def</span> <span class="text-blue-400">create_note_with_events</span>(db: AsyncSession, note_data: dict):
    <span class="text-slate-500"># Both operations are part of the same transaction</span>
    
    <span class="text-slate-500"># 1. Insert the Note</span>
    note = Note(**note_data)
    db.add(note)
    
    <span class="text-slate-500"># 2. Insert the Outbox Event</span>
    event = EventOutbox(
        event_type=<span class="text-emerald-400">"note.created"</span>,
        payload={"note_id": note.id}
    )
    db.add(event)
    
    <span class="text-purple-400">await</span> db.commit() <span class="text-slate-500"># Atomic success or failure</span>
            ` }} />
          </div>
          
          <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl flex flex-col items-center">
            <div className="bg-white/10 p-4 rounded-xl border border-white/20 w-48 text-center shadow-lg relative">
              <Database className="mx-auto mb-2 text-white" />
              <div className="font-bold text-white">BEGIN TX</div>
            </div>
            
            <ArrowDown className="text-white/20 my-2" />
            
            <div className="bg-black/50 p-4 rounded-xl border border-blue-500/30 w-64">
               <div className="flex items-center gap-2 text-blue-400 text-sm mb-2"><CheckCircle2 size={16}/> Insert notes table</div>
               <div className="flex items-center gap-2 text-blue-400 text-sm"><CheckCircle2 size={16}/> Insert event_outbox table</div>
            </div>
            
            <ArrowDown className="text-white/20 my-2" />

            <div className="bg-emerald-500/20 p-4 rounded-xl border border-emerald-500/30 w-48 text-center shadow-[0_0_15px_rgba(16,185,129,0.2)]">
              <div className="font-bold text-emerald-400">COMMIT TX</div>
            </div>
          </div>
        </div>
      </div>

      {/* SubSystem 2: Redis Streams */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 text-lg border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]">S2</span>
            Redis Streams & Consumer Groups
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
            A background poller reads the <code>event_outbox</code> table and pushes the events to a <strong>Redis Stream</strong>. 
            Unlike basic queues, Redis Streams use <strong>Consumer Groups</strong>. This means if you have 5 worker servers, Redis guarantees that each event is only given to ONE worker.
          </p>
        </div>

        <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl overflow-hidden relative">
          <div className="flex flex-col md:flex-row items-center gap-8 justify-center">
            
            <div className="bg-black p-6 rounded-2xl border border-blue-500/30 text-center w-64 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
              <Box className="text-blue-400 mx-auto mb-2" size={32} />
              <div className="text-white font-bold text-lg">Redis Stream</div>
              <div className="text-blue-300 text-xs mt-1">unmessit:events:stream</div>
              
              <div className="flex flex-col gap-2 mt-4">
                <div className="bg-blue-500/20 text-white text-xs py-1 rounded">Event 1: note.created</div>
                <div className="bg-blue-500/20 text-white text-xs py-1 rounded">Event 2: chunk.indexed</div>
              </div>
            </div>

            <div className="flex md:flex-col gap-4 text-white/20">
               <ArrowRight className="hidden md:block" />
               <ArrowRight className="hidden md:block" />
            </div>

            <div className="flex flex-col gap-4 border-l-2 border-dashed border-white/20 pl-8 relative">
               <div className="absolute -left-3 top-1/2 -translate-y-1/2 bg-black text-white/50 text-xs px-2 py-1 rounded rotate-[-90deg]">Consumer Group</div>
               
               <div className="bg-white/10 p-4 rounded-xl border border-white/20 flex items-center gap-4 w-64">
                 <Server className="text-emerald-400" />
                 <div>
                   <div className="text-white font-bold text-sm">Worker A</div>
                   <div className="text-emerald-400 text-xs">Processing Event 1</div>
                 </div>
               </div>
               
               <div className="bg-white/10 p-4 rounded-xl border border-white/20 flex items-center gap-4 w-64">
                 <Server className="text-purple-400" />
                 <div>
                   <div className="text-white font-bold text-sm">Worker B</div>
                   <div className="text-purple-400 text-xs">Processing Event 2</div>
                 </div>
               </div>
            </div>

          </div>
        </div>
      </div>

      {/* SubSystem 3: Idempotency */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 text-lg border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]">S3</span>
            Strict Handler Idempotency
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
            Redis Streams guarantees <i>at-least-once</i> delivery. This means a worker might receive the exact same event twice (e.g., network timeout during ACK). If we process a `note.created` event twice, we will index the note twice and corrupt the graph. We block this at the SQLite database level using an <code>event_handler_runs</code> table.
          </p>
        </div>

        <div className="liquid-glass rounded-3xl p-8 border border-white/10 overflow-x-auto relative shadow-2xl">
          <pre className="font-mono text-sm text-blue-200/90 leading-loose" dangerouslySetInnerHTML={{ __html: `
<span class="text-purple-400">async def</span> <span class="text-blue-400">handle_event</span>(event_id: str, handler_name: str):
    <span class="text-slate-500"># Try to insert a record marking this event as handled by this handler</span>
    <span class="text-purple-400">try</span>:
        run = EventHandlerRun(event_id=event_id, handler=handler_name)
        db.add(run)
        <span class="text-purple-400">await</span> db.commit()
    <span class="text-purple-400">except</span> IntegrityError:
        <span class="text-slate-500"># A unique constraint violation means another worker already handled it!</span>
        logger.info(<span class="text-emerald-400">f"Event {event_id} already handled by {handler_name}. Skipping."</span>)
        <span class="text-purple-400">return</span> <span class="text-orange-400">False</span>
    
    <span class="text-slate-500"># Safe to process!</span>
    <span class="text-purple-400">await</span> execute_expensive_llm_job()
          ` }} />
        </div>
      </div>

      {/* SubSystem 4: Global Rate Limiting */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center text-orange-400 text-lg border border-orange-500/30 shadow-[0_0_15px_rgba(249,115,22,0.2)]">S4</span>
            Global Rate Limiting
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
            LLM providers enforce strict RPM (Requests Per Minute) limits. We use a thread-safe singleton <code>PerMinuteRateLimiter</code> (via <code>@lru_cache</code>) which ensures that all concurrent background ingestion workers AND synchronous user queries share the same exact token bucket, perfectly throttling traffic before the LLM SDK ever makes a network call.
          </p>
        </div>
        
        <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl overflow-hidden relative">
           <div className="flex items-center justify-center gap-8">
             <div className="flex flex-col gap-4">
                <div className="bg-blue-500/10 border border-blue-500/30 p-3 rounded-lg text-blue-300 text-sm flex items-center gap-2"><Server size={14}/> Ingestion Worker A</div>
                <div className="bg-blue-500/10 border border-blue-500/30 p-3 rounded-lg text-blue-300 text-sm flex items-center gap-2"><Server size={14}/> Ingestion Worker B</div>
                <div className="bg-accent-500/10 border border-accent-500/30 p-3 rounded-lg text-accent-300 text-sm flex items-center gap-2"><Activity size={14}/> Query Request</div>
             </div>
             
             <ArrowRight className="text-white/20" />
             
             <div className="bg-black/80 p-6 rounded-2xl border border-orange-500/50 shadow-[0_0_20px_rgba(249,115,22,0.3)] text-center relative">
               <Shield className="text-orange-400 mx-auto mb-2" size={24} />
               <div className="font-bold text-white text-sm">PerMinuteRateLimiter</div>
               <div className="text-orange-300 text-xs mt-1">Shared Singleton</div>
               <div className="mt-4 flex gap-1 justify-center">
                  <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                  <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                  <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                  <div className="w-2 h-2 rounded-full bg-white/10"></div>
               </div>
             </div>
             
             <ArrowRight className="text-white/20" />
             
             <div className="bg-emerald-500/10 border border-emerald-500/30 p-4 rounded-xl text-emerald-400 text-sm flex flex-col items-center">
                <Database size={24} className="mb-2" />
                LLM API
             </div>
           </div>
        </div>
      </div>

      {/* SubSystem 5: Caching & Cron */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">S5</span>
            L1/L2 Cache & Async Cron
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
            Cache invalidation is notoriously difficult. Instead of synchronous blocking TTL checks, UnmessIt uses a multi-tier cache: <strong>L1 Memory</strong> (Fastest, LRU limit) and <strong>L2 Redis</strong>. An asynchronous <code>cron.py</code> event loop continuously scrubs stale keys in the background without blocking the main event thread.
          </p>
        </div>
        
        <div className="liquid-glass rounded-3xl p-8 border border-white/10 shadow-2xl relative">
          <div className="absolute right-6 top-6 bg-emerald-500/10 text-emerald-400 p-3 rounded-full shadow-[0_0_15px_rgba(16,185,129,0.3)] animate-spin-slow">
            <Timer size={20} />
          </div>
          <pre className="font-mono text-sm text-emerald-200/90 leading-loose" dangerouslySetInnerHTML={{ __html: `
<span class="text-purple-400">async def</span> <span class="text-blue-400">_embedding_memory_cron</span>():
    <span class="text-purple-400">while True</span>:
        <span class="text-slate-500"># Non-blocking async sleep with jitter</span>
        <span class="text-purple-400">await</span> asyncio.sleep(MEMORY_CACHE_INTERVAL * random.uniform(0.9, 1.1))
        
        cache = get_memory_embedding_cache()
        count = cache.cleanup_stale(EMBEDDING_CACHE_TTL)
        
        <span class="text-purple-400">if</span> count &gt; 0:
            logger.info(<span class="text-emerald-400">"cron_embedding_cache_cleanup evicted=%d"</span>, count)
          ` }} />
        </div>
      </div>

      {/* SubSystem 6: SSE PubSub */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 text-lg border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.2)]">S6</span>
            SSE & Pub/Sub Broadcast
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
            If User A connects to Server 1, but their background job runs on Server 2, how does Server 2 tell Server 1 to update the UI? Server 2 broadcasts the progress event to a <strong>Redis Pub/Sub Topic</strong>. Server 1 (and all other servers) receives the broadcast, checks its local memory for the active socket, and routes the payload to the browser.
          </p>
        </div>
        
        <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl relative overflow-hidden">
           <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-purple-900/20 via-transparent to-transparent pointer-events-none" />
           
           <div className="flex flex-col items-center gap-8 relative z-10">
             <motion.div 
               animate={{ scale: [1, 1.05, 1] }} 
               transition={{ repeat: Infinity, duration: 2 }}
               className="bg-black p-4 rounded-2xl border border-purple-500/50 shadow-[0_0_30px_rgba(168,85,247,0.3)] text-center w-64 relative"
             >
               <ActivitySquare className="text-purple-400 mx-auto mb-2" size={32} />
               <div className="text-white font-bold">Redis Pub/Sub</div>
               <div className="text-purple-300 text-xs">unmessit:sse:topics:jobs</div>
               <motion.div
                 initial={{ opacity: 0, scale: 0.8 }}
                 animate={{ opacity: [0, 1, 0], scale: [0.8, 1.5, 2] }}
                 transition={{ repeat: Infinity, duration: 2, delay: 0.5 }}
                 className="absolute inset-0 border-2 border-purple-500/30 rounded-2xl"
               />
             </motion.div>

             <div className="flex gap-12 w-full justify-center">
                <div className="flex flex-col items-center gap-2">
                  <ArrowDown className="text-purple-400/50" />
                  <div className="bg-white/10 p-4 rounded-xl border border-emerald-500/30 text-center w-40 relative">
                    <Server className="text-white mx-auto mb-2" />
                    <div className="font-bold text-white text-sm">Server 1</div>
                    <div className="text-emerald-400 text-xs mt-2">Has Socket → Sends to User</div>
                  </div>
                </div>

                <div className="flex flex-col items-center gap-2">
                  <ArrowDown className="text-purple-400/50" />
                  <div className="bg-white/10 p-4 rounded-xl border border-white/20 text-center w-40 relative opacity-50">
                    <Server className="text-white mx-auto mb-2" />
                    <div className="font-bold text-white text-sm">Server 2 (Job)</div>
                    <div className="text-white/60 text-xs mt-2">No Socket → Ignores</div>
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
