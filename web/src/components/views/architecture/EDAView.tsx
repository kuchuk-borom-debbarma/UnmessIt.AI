import { motion } from 'framer-motion'
import { GitBranch, Box, ArrowRight, Mail, Webhook, Zap, Database, Activity, Radio, Lock, Repeat, ShieldAlert } from 'lucide-react'

export function EDAView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-32 pb-32"
    >
      <section id="eda" className="scroll-mt-32">
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-sm font-bold uppercase tracking-wider mb-4">
            <GitBranch size={14} /> Event-Driven Architecture
          </div>
          <h2 className="text-4xl font-bold tracking-tight mb-4 text-white">Durable Event-Driven Design</h2>
          <p className="text-lg text-muted-foreground max-w-4xl leading-relaxed">
            UnmessIt relies on a loosely coupled architecture driven by domain events. This ensures that core domain logic remains clean, isolated, and completely durable against infrastructural failures or server crashes using a strict Transactional Outbox pattern paired with Redis Streams.
          </p>
        </div>

        {/* Stage 1: Core Concept */}
        <div className="space-y-8 mt-16">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400 text-lg border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.2)]">1</span>
              Decoupling Effects
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              When a user signs up or creates a note, we need to trigger downstream effects like updating analytics, indexing vectors, or sending emails. Instead of bloating the core service, the service simply mutates its own state, emits a domain event (e.g. <code>note.created</code>), and finishes immediately.
            </p>
          </div>

          <div className="liquid-glass rounded-3xl p-8 border border-white/5 relative overflow-hidden shadow-2xl">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-900/10 via-transparent to-transparent pointer-events-none" />
            
            <div className="relative z-10 flex flex-col md:flex-row items-center gap-8 justify-center">
               <div className="bg-white/5 border border-white/10 p-6 rounded-2xl flex flex-col items-center shadow-xl">
                  <Box className="text-white mb-2" size={32} />
                  <div className="font-bold text-white mb-4">Core Domain</div>
                  <div className="bg-black/50 p-3 rounded-xl font-mono text-xs border border-white/5 text-cyan-300">
                    user = repository.create(...)<br/>
                    emit('user.created', user.id)
                  </div>
               </div>

               <ArrowRight className="text-cyan-500/50 hidden md:block" size={32} />

               <div className="flex flex-col gap-4">
                  <motion.div initial={{ x: 20, opacity: 0 }} whileInView={{ x: 0, opacity: 1 }} transition={{ delay: 0.1 }} className="flex items-center gap-4 bg-emerald-500/10 border border-emerald-500/30 p-4 rounded-xl shadow-lg">
                    <Mail className="text-emerald-400" />
                    <div>
                      <div className="text-sm font-bold text-white">Email Service</div>
                      <div className="text-xs text-emerald-200/70 mt-1">Listens to 'user.created' → Sends Welcome Email</div>
                    </div>
                  </motion.div>
                  
                  <motion.div initial={{ x: 20, opacity: 0 }} whileInView={{ x: 0, opacity: 1 }} transition={{ delay: 0.2 }} className="flex items-center gap-4 bg-purple-500/10 border border-purple-500/30 p-4 rounded-xl shadow-lg">
                    <Webhook className="text-purple-400" />
                    <div>
                      <div className="text-sm font-bold text-white">Analytics Service</div>
                      <div className="text-xs text-purple-200/70 mt-1">Listens to 'user.created' → Updates Mixpanel</div>
                    </div>
                  </motion.div>

                  <motion.div initial={{ x: 20, opacity: 0 }} whileInView={{ x: 0, opacity: 1 }} transition={{ delay: 0.3 }} className="flex items-center gap-4 bg-blue-500/10 border border-blue-500/30 p-4 rounded-xl shadow-lg">
                    <Zap className="text-blue-400" />
                    <div>
                      <div className="text-sm font-bold text-white">Billing Service</div>
                      <div className="text-xs text-blue-200/70 mt-1">Listens to 'user.created' → Syncs with Stripe</div>
                    </div>
                  </motion.div>
               </div>
            </div>
          </div>
        </div>

        {/* Stage 2: Transactional Outbox */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 text-lg border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]">2</span>
              The Transactional Outbox
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              We never write directly to Redis when saving a domain entity. If the Redis write fails after the SQLite write succeeds, the event is lost forever (dual-write problem). Instead, we use a single SQLite Transaction to save the entity AND write the event to the <code>event_outbox</code> table.
            </p>
          </div>

          <div className="liquid-glass rounded-3xl p-8 border border-white/5 relative overflow-hidden shadow-2xl">
            <div className="flex flex-col md:flex-row items-center gap-8 relative z-10">
               <div className="flex-1 bg-white/5 p-8 rounded-2xl border border-white/10 w-full shadow-xl">
                 <div className="flex items-center gap-2 mb-6 text-primary-400 font-bold text-lg">
                   <Database size={22} /> SQLite Atomic Transaction
                 </div>
                 <div className="space-y-4 font-mono text-sm">
                    <div className="bg-black/50 p-4 rounded-xl border border-white/5 text-white/80 shadow-inner">
                      BEGIN TRANSACTION;
                    </div>
                    <div className="bg-black/50 p-4 rounded-xl border border-white/5 text-blue-300 ml-6 shadow-inner">
                      INSERT INTO notes (id, text) VALUES (...);
                    </div>
                    <div className="bg-black/50 p-4 rounded-xl border border-white/5 text-accent-300 ml-6 relative shadow-inner">
                      <div className="absolute -left-7 top-1/2 -translate-y-1/2 text-white/30 font-sans text-xs font-bold">AND</div>
                      INSERT INTO event_outbox (topic, payload) VALUES ('note.created', ...);
                    </div>
                    <div className="bg-black/50 p-4 rounded-xl border border-white/5 text-emerald-400 font-bold shadow-inner">
                      COMMIT;
                    </div>
                 </div>
               </div>
            </div>
          </div>
        </div>

        {/* Stage 3: Dispatcher & Redis Streams */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 text-lg border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.2)]">3</span>
              Dispatcher & Redis Streams
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              A background sweeper continuously polls the <code>event_outbox</code> table for pending events. When it finds them, it safely pushes them into a Redis Stream (<code>unmessit:events</code>) via <code>XADD</code>. Once the Redis append is successful, the SQLite outbox row is marked published. This guarantees at-least-once delivery to the message broker.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div className="bg-white/5 border border-white/10 p-8 rounded-3xl shadow-xl flex flex-col justify-center h-full group hover:border-white/20 transition-all">
                <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500/20 text-blue-400 mb-6 group-hover:scale-110 transition-transform">
                   <Activity size={32} />
                </div>
                <h4 className="text-2xl font-bold text-white mb-3">Background Dispatcher</h4>
                <p className="text-blue-200/70 text-sm leading-relaxed mb-6">
                   An isolated <code>asyncio.Task</code> that polls SQLite batches. Resilient to Redis connection drops and network blips.
                </p>
                <div className="font-mono text-xs bg-black/50 p-4 rounded-xl border border-white/5 text-blue-300">
                   SELECT * FROM event_outbox<br/>WHERE status = 'pending' LIMIT 100;
                </div>
             </div>
             
             <div className="bg-white/5 border border-white/10 p-8 rounded-3xl shadow-xl flex flex-col justify-center h-full group hover:border-white/20 transition-all">
                <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-purple-500/20 text-purple-400 mb-6 group-hover:scale-110 transition-transform">
                   <Radio size={32} />
                </div>
                <h4 className="text-2xl font-bold text-white mb-3">Redis Stream Broadcast</h4>
                <p className="text-purple-200/70 text-sm leading-relaxed mb-6">
                   Using Redis <code>XADD</code> to broadcast the event to the cluster. The event is now highly available and durably enqueued in memory.
                </p>
                <div className="font-mono text-xs bg-black/50 p-4 rounded-xl border border-white/5 text-purple-300">
                   XADD unmessit:events * topic note.created payload ...
                </div>
             </div>
          </div>
        </div>

        {/* Stage 4: Consumer Groups & Idempotency Locks */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">4</span>
              Consumer Groups & Idempotency Locks
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              Worker nodes consume the Redis Stream using <code>XREADGROUP</code>. Because we use "at-least-once" delivery, it's entirely possible a worker crashes mid-job and the job is reclaimed by another worker. To prevent catastrophic double-processing, we rely on strict SQLite idempotency locks for each handler execution.
            </p>
          </div>

          <div className="liquid-glass rounded-3xl p-8 lg:p-12 border border-white/5 relative overflow-hidden shadow-2xl flex flex-col lg:flex-row gap-12 items-center">
             
             <div className="flex-1 flex flex-col gap-6 w-full relative z-10">
                <div className="bg-emerald-500/10 border border-emerald-500/30 p-6 rounded-2xl text-center shadow-lg">
                  <div className="text-emerald-400 font-bold mb-2 font-mono text-lg flex items-center justify-center gap-2">
                    <Zap size={18}/> XREADGROUP
                  </div>
                  <div className="text-emerald-200/70 text-sm">Worker pulls Event #123 from Stream</div>
                </div>
                
                <div className="flex justify-center"><ArrowRight className="text-white/20 rotate-90" size={32} /></div>
                
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl relative overflow-hidden shadow-lg">
                   <div className="absolute top-0 right-0 p-4"><Lock className="text-white/20" size={24} /></div>
                   <div className="font-mono text-xs text-blue-300 mb-3 px-2 py-1 bg-blue-500/10 rounded inline-block">SQLite: event_handler_runs</div>
                   <div className="text-white text-base font-bold mb-2">Attempt to INSERT (event_id, handler_name)</div>
                   <div className="text-sm text-muted-foreground leading-relaxed">This table has a strict UNIQUE constraint mapping the exact event ID to the specific handler function name.</div>
                </div>
             </div>

             <div className="flex-1 flex flex-col gap-6 w-full lg:border-l lg:border-white/10 lg:pl-12 relative z-10">
                <motion.div initial={{ opacity: 0, x: 20 }} whileInView={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="bg-green-500/10 border border-green-500/30 p-6 rounded-2xl shadow-lg relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-3 opacity-20"><Zap size={40} className="text-green-400" /></div>
                  <div className="text-green-400 font-bold mb-2 text-lg">SUCCESS (First Run)</div>
                  <div className="text-green-200/70 text-sm leading-relaxed">The lock is acquired. The worker executes the downstream logic (e.g. LangGraph ingestion). Upon completion, it commits `HANDLER_COMPLETE` and sends an `XACK` to Redis.</div>
                </motion.div>
                
                <motion.div initial={{ opacity: 0, x: 20 }} whileInView={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="bg-orange-500/10 border border-orange-500/30 p-6 rounded-2xl shadow-lg relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-3 opacity-20"><Repeat size={40} className="text-orange-400" /></div>
                  <div className="text-orange-400 font-bold mb-2 text-lg flex items-center gap-2">IntegrityError (Duplicate)</div>
                  <div className="text-orange-200/70 text-sm leading-relaxed">Another worker already started this handler! The insert fails. We immediately abort, optionally `XACK` the message if it was completed globally, and avoid data duplication.</div>
                </motion.div>
             </div>
          </div>
        </div>

        {/* Stage 5: Recovery and XAUTOCLAIM */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center text-red-400 text-lg border border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">5</span>
              Stalled Jobs & XAUTOCLAIM
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              If an API timeout occurs, or the server machine crashes unexpectedly, jobs will be stuck in the Pending Entries List (PEL). To guarantee forward progress, the system uses <code>XAUTOCLAIM</code>.
            </p>
          </div>

          <div className="bg-white/5 border border-white/10 p-8 rounded-3xl flex flex-col md:flex-row items-center gap-8 shadow-xl">
             <div className="w-20 h-20 shrink-0 rounded-full bg-red-500/20 flex items-center justify-center text-red-400 shadow-[0_0_20px_rgba(239,68,68,0.2)]">
               <ShieldAlert size={36} />
             </div>
             <div>
                <h4 className="text-xl font-bold text-white mb-2">Automated Reclamation</h4>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  During the consumer loop, workers constantly execute <code>XAUTOCLAIM</code> looking for un-ACKed messages older than 60,000ms. If found, ownership is transferred to the new worker, which attempts the idempotency lock logic again. Jobs pause, but they never fail permanently.
                </p>
             </div>
          </div>
        </div>

      </section>
    </motion.div>
  )
}
