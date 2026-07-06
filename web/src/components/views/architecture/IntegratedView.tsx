import { motion } from 'framer-motion'
import { Combine, ArrowRight } from 'lucide-react'

export function IntegratedView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-[1200px] mx-auto space-y-16 pb-32"
    >
      <section id="integrated" className="scroll-mt-32">
        <div className="mb-12 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-bold uppercase tracking-wider mb-4">
            <Combine size={14} /> The Grand Finale
          </div>
          <h2 className="text-5xl font-bold tracking-tight mb-6 text-white">The Full Integrated Engine</h2>
          <p className="text-xl text-muted-foreground max-w-4xl mx-auto leading-relaxed">
            This is how all the subsystems operate together in the wild. A highly durable, heavily cached, event-driven architecture that bridges structured graphs with unstructured language generation.
          </p>
        </div>

        <div className="bg-white/5 rounded-3xl p-8 lg:p-12 border border-white/10 shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-purple-500/5 to-emerald-500/5 pointer-events-none" />
          
          <div className="flex flex-col lg:flex-row gap-8 lg:gap-12 items-stretch relative z-10">
            {/* Ingestion Column */}
            <div className="flex-1 bg-black/40 rounded-2xl p-8 border border-white/5 flex flex-col gap-6 relative shadow-xl">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-600 to-indigo-400 rounded-t-2xl" />
              <div className="text-indigo-400 font-black uppercase tracking-widest text-lg mb-2 text-center border-b border-indigo-500/20 pb-4">1. Ingestion & Durability</div>
              
              <div className="bg-indigo-500/10 border border-indigo-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="text-indigo-100 font-bold text-lg">User Uploads Document</span>
              </div>
              <ArrowRight className="text-indigo-500/50 rotate-90 mx-auto" size={24} />
              
              <div className="bg-indigo-500/10 border border-indigo-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="font-bold text-indigo-100 text-lg">Transactional Outbox</span><br/>
                <span className="text-sm text-indigo-300/70 mt-2 block">Writes to SQLite & Redis Stream</span>
              </div>
              <ArrowRight className="text-indigo-500/50 rotate-90 mx-auto" size={24} />
              
              <div className="bg-indigo-500/10 border border-indigo-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="font-bold text-indigo-100 text-lg">Durable LangGraph</span><br/>
                <span className="text-sm text-indigo-300/70 mt-2 block">Splits, Hashes, LLM Extracts</span>
              </div>
              <ArrowRight className="text-indigo-500/50 rotate-90 mx-auto" size={24} />
              
              <div className="bg-indigo-500/10 border border-indigo-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="font-bold text-indigo-100 text-lg">Exact Caches & 4-Layer Dedupe</span><br/>
                <span className="text-sm text-indigo-300/70 mt-2 block">Saves Chunks & Canonical Keys</span>
              </div>
            </div>

            {/* Storage Core */}
            <div className="flex-1 bg-black/40 rounded-2xl p-8 border border-white/5 flex flex-col justify-center items-center gap-8 relative shadow-xl">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-t-2xl" />
              <div className="text-emerald-400 font-black uppercase tracking-widest text-lg mb-2 text-center border-b border-emerald-500/20 pb-4 w-full">2. The Core State</div>
              
              <div className="w-full bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-xl text-center shadow-md">
                <div className="text-emerald-300 font-black text-xl mb-2">ChromaDB</div>
                <div className="text-sm text-emerald-200/70">Dense Vector Embeddings</div>
              </div>
              
              <div className="w-full flex justify-between items-center px-12">
                 <ArrowRight className="text-emerald-500/50 -rotate-90" size={32} />
                 <ArrowRight className="text-emerald-500/50 rotate-90" size={32} />
              </div>

              <div className="w-full bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-xl text-center shadow-md">
                <div className="text-emerald-300 font-black text-xl mb-2">SQLite FTS & Knowledge Graph</div>
                <div className="text-sm text-emerald-200/70">Source Chunks ⟷ Recall Keys</div>
              </div>
              
              <div className="w-full bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-xl text-center mt-8 border-dashed shadow-md">
                <div className="text-emerald-300 font-black text-xl mb-2">Redis Pub/Sub</div>
                <div className="text-sm text-emerald-200/70">Live SSE UI Updates</div>
              </div>
            </div>

            {/* Querying Column */}
            <div className="flex-1 bg-black/40 rounded-2xl p-8 border border-white/5 flex flex-col gap-6 justify-end relative shadow-xl">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-orange-600 to-orange-400 rounded-t-2xl" />
              <div className="text-orange-400 font-black uppercase tracking-widest text-lg mb-2 text-center border-b border-orange-500/20 pb-4">3. Query & Generation</div>
              
              <div className="bg-orange-500/10 border border-orange-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="font-bold text-orange-100 text-lg">Top-Level Caches</span><br/>
                <span className="text-sm text-orange-300/70 mt-2 block">1ms Hit or LLM Verifier</span>
              </div>
              <ArrowRight className="text-orange-500/50 -rotate-90 mx-auto" size={24} />
              
              <div className="bg-orange-500/10 border border-orange-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="font-bold text-orange-100 text-lg">Parallel 3-Prong Traversal</span><br/>
                <span className="text-sm text-orange-300/70 mt-2 block">Vector + Lexical + Graph Edge</span>
              </div>
              <ArrowRight className="text-orange-500/50 -rotate-90 mx-auto" size={24} />
              
              <div className="bg-orange-500/10 border border-orange-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="font-bold text-orange-100 text-lg">Context Compaction</span><br/>
                <span className="text-sm text-orange-300/70 mt-2 block">Aggressively prunes noise</span>
              </div>
              <ArrowRight className="text-orange-500/50 -rotate-90 mx-auto" size={24} />
              
              <div className="bg-orange-500/10 border border-orange-500/20 p-5 rounded-xl text-center shadow-md">
                <span className="font-bold text-orange-100 text-xl">Final Cited Answer</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </motion.div>
  )
}
