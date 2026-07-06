import { motion } from 'framer-motion'
import { Zap, BrainCircuit, Search, ArrowRight, Check, X, Server, Database, MemoryStick, ArrowDown, Activity, FastForward, ShieldAlert } from 'lucide-react'

export function CachingView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-[1200px] mx-auto space-y-32 pb-32"
    >
      <section id="caching" className="scroll-mt-32">
        <div className="mb-12 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm font-bold uppercase tracking-wider mb-4">
            <Zap size={14} /> Caching Architecture
          </div>
          <h2 className="text-5xl font-bold tracking-tight mb-6 text-white">The Multi-Tier Cache Engine</h2>
          <p className="text-xl text-muted-foreground max-w-4xl mx-auto leading-relaxed">
            Full retrieval and LLM synthesis is expensive. To bypass it, we utilize a massive, highly optimized 3-tier caching waterfall. We combine blazing-fast in-memory LRUs with hybrid Vector+Redis storage and LLM-powered verification loops.
          </p>
        </div>

        {/* Narrative Section: The 3 Tiers */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 mb-20">
           
           <div className="bg-white/5 border border-white/10 rounded-2xl p-6 shadow-xl relative overflow-hidden group hover:border-yellow-500/30 transition-colors">
             <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <FastForward size={100} />
             </div>
             <div className="w-12 h-12 bg-blue-500/20 border border-blue-500/30 rounded-xl flex items-center justify-center text-blue-400 mb-4">
                <MemoryStick size={20} />
             </div>
             <h3 className="text-lg font-bold text-white mb-2">L1: Memory LRU (Exact)</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               The fastest layer. A synchronized, in-process <code>OrderedDict</code> LRU cache capped at 1000 items. Exact hash matches are served instantly in microseconds, completely bypassing the network.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-2xl p-6 shadow-xl relative overflow-hidden group hover:border-yellow-500/30 transition-colors">
             <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Server size={100} />
             </div>
             <div className="w-12 h-12 bg-purple-500/20 border border-purple-500/30 rounded-xl flex items-center justify-center text-purple-400 mb-4">
                <Database size={20} />
             </div>
             <h3 className="text-lg font-bold text-white mb-2">L2: Redis (Exact)</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               If L1 misses, we fall back to a distributed Redis cache using a SHA-256 digest of the query. If hit, the massive JSON payload is returned over the network and automatically promoted back to the L1 Memory Cache.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-2xl p-6 shadow-xl relative overflow-hidden group hover:border-yellow-500/30 transition-colors">
             <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <BrainCircuit size={100} />
             </div>
             <div className="w-12 h-12 bg-yellow-500/20 border border-yellow-500/30 rounded-xl flex items-center justify-center text-yellow-400 mb-4">
                <Search size={20} />
             </div>
             <h3 className="text-lg font-bold text-white mb-2">L3: Chroma+Redis (Semantic)</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               If no exact match exists, we embed the query. ChromaDB executes a vector similarity search. To keep ChromaDB lean and fast, it only stores the vectors and a <code>redis_key</code> pointer. The actual payload is fetched from Redis.
             </p>
           </div>
        </div>

        {/* Deep Dive Granular Timeline */}
        <div className="w-full bg-[#050505] rounded-3xl border border-white/10 p-8 overflow-x-auto shadow-2xl mt-12">
           <div className="min-w-[1000px] flex flex-col gap-6 font-mono text-xs">
              
              <div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/10">
                 <div className="bg-blue-500 text-white px-3 py-1 rounded font-bold">Query Execution</div>
                 <ArrowDown className="-rotate-90 text-white/40" size={16} />
                 <div className="text-white">"What is the Event-Driven Architecture?"</div>
              </div>

              <div className="pl-12 flex flex-col gap-4 border-l-2 border-dashed border-white/20 ml-6 py-4">
                 
                 {/* L1 Cache */}
                 <div className="border border-blue-500/30 rounded-xl p-4 bg-blue-500/5">
                    <div className="text-blue-300 font-bold mb-4 flex items-center gap-2">
                      <MemoryStick size={14} /> 1. L1 In-Memory LRU Cache Check (Exact)
                    </div>
                    <div className="flex flex-col gap-3 pl-6 border-l border-blue-500/20">
                       <div className="flex items-center gap-4">
                          <span className="text-emerald-400 font-bold flex items-center gap-1"><Check size={14}/> HIT</span>
                          <ArrowDown className="-rotate-90 text-white/40" size={16} />
                          <span className="text-white">Returns immediately (&lt; 1ms). Graph stops.</span>
                       </div>
                       <div className="flex items-center gap-4 mt-2 opacity-70">
                          <span className="text-red-400 font-bold flex items-center gap-1"><X size={14}/> MISS</span>
                          <ArrowDown className="-rotate-90 text-white/40" size={16} />
                          <span className="text-white">Proceed to L2</span>
                       </div>
                    </div>
                 </div>

                 {/* L2 Cache */}
                 <div className="border border-purple-500/30 rounded-xl p-4 bg-purple-500/5 mt-4">
                    <div className="text-purple-300 font-bold mb-4 flex items-center gap-2">
                      <Database size={14} /> 2. L2 Redis Distributed Cache Check (Exact)
                    </div>
                    <div className="flex flex-col gap-3 pl-6 border-l border-purple-500/20">
                       <div className="flex items-center gap-4">
                          <span className="text-emerald-400 font-bold flex items-center gap-1"><Check size={14}/> HIT</span>
                          <ArrowDown className="-rotate-90 text-white/40" size={16} />
                          <span className="text-white">Fetch JSON from Redis. <strong className="text-blue-400">Promote payload to L1 Memory Cache.</strong> Graph stops.</span>
                       </div>
                       <div className="flex items-center gap-4 mt-2 opacity-70">
                          <span className="text-red-400 font-bold flex items-center gap-1"><X size={14}/> MISS</span>
                          <ArrowDown className="-rotate-90 text-white/40" size={16} />
                          <span className="text-white">Proceed to L3 Semantic Cache</span>
                       </div>
                    </div>
                 </div>

                 {/* L3 Cache - Chroma Search */}
                 <div className="border border-yellow-500/30 rounded-xl p-4 bg-yellow-500/5 mt-4">
                    <div className="text-yellow-300 font-bold mb-4 flex items-center gap-2">
                      <BrainCircuit size={14} /> 3. L3 ChromaDB Vector Search (Semantic)
                    </div>
                    
                    <div className="flex items-center gap-4 bg-black/40 p-3 rounded-lg border border-white/5 mb-4">
                       <Activity size={14} className="text-emerald-400" />
                       <span className="text-white">Embed User Query → Query ChromaDB (n_results=5)</span>
                    </div>

                    <div className="flex flex-col gap-6 pl-6 border-l border-yellow-500/20">
                       
                       <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-4">
                             <span className="bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 px-2 py-1 rounded text-[10px] font-bold">Distance &lt; 0.02</span>
                             <span className="text-white font-bold">Exact Semantic Match</span>
                          </div>
                          <div className="text-muted-foreground pl-2 border-l-2 border-white/10 ml-1 py-1">
                             The vectors are nearly identical. 
                             <div className="flex items-center gap-2 mt-2 text-white bg-black/40 p-2 rounded">
                                <Search size={14} className="text-yellow-400" />
                                Extract `redis_key` from Chroma metadata → Fetch Payload from Redis. (Cache Hit)
                             </div>
                          </div>
                       </div>

                       <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-4">
                             <span className="bg-yellow-500/20 border border-yellow-500/40 text-yellow-400 px-2 py-1 rounded text-[10px] font-bold">Distance &lt; 0.05</span>
                             <span className="text-white font-bold">Soft Match (LLM Verification Required)</span>
                          </div>
                          <div className="text-muted-foreground pl-2 border-l-2 border-white/10 ml-1 py-1">
                             The questions are similar, but nuances might differ. We cannot blindly trust it.
                             <div className="flex items-center gap-2 mt-2 text-white bg-red-500/10 border border-red-500/20 p-2 rounded">
                                <ShieldAlert size={14} className="text-red-400" />
                                Invoke `SemanticSubQueryVerifierChain` Guardrail.
                             </div>
                          </div>
                       </div>

                       <div className="flex flex-col gap-2 opacity-70">
                          <div className="flex items-center gap-4">
                             <span className="bg-red-500/20 border border-red-500/40 text-red-400 px-2 py-1 rounded text-[10px] font-bold">Distance &gt; 0.05</span>
                             <span className="text-white font-bold">Cache Miss</span>
                          </div>
                          <div className="text-muted-foreground pl-2 border-l-2 border-white/10 ml-1 py-1">
                             No relevant cache found. We fall back to the full Query Engineering & Traversal Pipeline.
                          </div>
                       </div>

                    </div>
                 </div>

              </div>
           </div>
        </div>

        {/* The Verifier Flow */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-400 text-lg border border-yellow-500/30 shadow-[0_0_15px_rgba(234,179,8,0.2)]">4</span>
              The Semantic Verifier Guardrail
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              If the ChromaDB distance falls in the "Soft Match" zone (between <code>0.02</code> and <code>0.05</code>), we invoke the <code>SemanticSubQueryVerifierChain</code> to ask a fast LLM if the cached answer strictly satisfies the new question.
            </p>
          </div>

          <div className="bg-white/5 rounded-3xl p-8 border border-white/10 shadow-2xl relative overflow-hidden flex flex-col md:flex-row gap-8 items-center">
             <div className="flex-1 bg-black/40 p-6 rounded-2xl border border-white/10 w-full relative shadow-inner">
                <BrainCircuit className="text-yellow-500 absolute top-4 right-4 opacity-20" size={48} />
                <div className="text-xs font-mono text-yellow-400/80 mb-2 uppercase tracking-widest">System Prompt</div>
                <div className="text-sm text-white leading-relaxed font-mono">
                  You are a cache verifier. Determine if the PREVIOUS ANSWER fully and completely answers the NEW QUESTION. If there is ANY nuance missing, output "VALID: FALSE".
                </div>
                <div className="mt-4 pt-4 border-t border-white/10 flex flex-col gap-3">
                   <div className="bg-white/5 border border-white/10 p-3 rounded-lg text-xs text-white font-mono shadow-md">
                     <span className="text-muted-foreground mr-2">NEW Q:</span> "Does the SSE service use websockets?"
                   </div>
                   <div className="bg-white/5 border border-white/10 p-3 rounded-lg text-xs text-white font-mono shadow-md">
                     <span className="text-muted-foreground mr-2">PREV A:</span> "The SSE service uses Redis Pub/Sub and Server-Sent Events."
                   </div>
                </div>
             </div>

             <ArrowRight className="text-yellow-500/50 hidden md:block" size={32} />

             <div className="flex-1 flex flex-col gap-4 w-full">
                <motion.div initial={{ opacity: 0, x: 20 }} whileInView={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="bg-emerald-500/10 border border-emerald-500/30 p-5 rounded-2xl shadow-lg">
                  <div className="text-emerald-400 font-bold mb-2 flex items-center gap-2"><Check size={18} /> VALID: TRUE</div>
                  <div className="text-emerald-200/70 text-sm leading-relaxed">The LLM confirms the answer fits. We extract the <code>redis_key</code> from Chroma and fetch the payload. <strong className="text-emerald-400">Cache Hit!</strong></div>
                </motion.div>
                <motion.div initial={{ opacity: 0, x: 20 }} whileInView={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="bg-red-500/10 border border-red-500/30 p-5 rounded-2xl shadow-lg mt-2">
                  <div className="text-red-400 font-bold mb-2 flex items-center gap-2"><X size={18} /> VALID: FALSE</div>
                  <div className="text-red-200/70 text-sm leading-relaxed">The nuance is different. The cache is discarded. We proceed to the full Retrieval Pipeline. <strong className="text-red-400">Cache Miss.</strong></div>
                </motion.div>
             </div>
          </div>
        </div>

        {/* Cross-Query Evidence Recycling */}
        <div className="space-y-8 mt-24">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-sm font-bold uppercase tracking-wider mb-4">
              <Activity size={14} /> Sub-Query Architecture
            </div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              Cross-Query Evidence Recycling
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              Caching isn't just evaluated at the global query level. Our system caches evidence at the <strong>sub-query</strong> level. This creates a "Lego-block" architecture where complex, multi-part questions can instantly recycle evidence gathered by completely independent past queries.
            </p>
          </div>

          <div className="bg-white/5 rounded-3xl p-8 border border-white/10 shadow-2xl relative overflow-hidden flex flex-col gap-8">
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Query 1 */}
                <div className="bg-black/40 border border-white/10 rounded-2xl p-6 relative overflow-hidden">
                   <div className="absolute top-0 right-0 p-4 opacity-5">
                      <Database size={64} />
                   </div>
                   <div className="text-xs font-mono text-cyan-400/80 mb-2 uppercase tracking-widest">Query 1 (Independent)</div>
                   <div className="text-white font-bold mb-4">"tell me about food"</div>
                   <div className="space-y-3">
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                         <Search size={14} className="text-red-400" /> Global Cache Miss
                      </div>
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                         <Activity size={14} className="text-yellow-400" /> Heavy search runs
                      </div>
                      <div className="flex items-center gap-3 text-sm font-mono text-emerald-400 bg-emerald-500/10 p-2 rounded border border-emerald-500/20">
                         <Check size={14} /> Evidence Cached for [food]
                      </div>
                   </div>
                </div>

                {/* Query 2 */}
                <div className="bg-black/40 border border-white/10 rounded-2xl p-6 relative overflow-hidden">
                   <div className="absolute top-0 right-0 p-4 opacity-5">
                      <Database size={64} />
                   </div>
                   <div className="text-xs font-mono text-cyan-400/80 mb-2 uppercase tracking-widest">Query 2 (Independent)</div>
                   <div className="text-white font-bold mb-4">"tell me about amy"</div>
                   <div className="space-y-3">
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                         <Search size={14} className="text-red-400" /> Global Cache Miss
                      </div>
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                         <Activity size={14} className="text-yellow-400" /> Heavy search runs
                      </div>
                      <div className="flex items-center gap-3 text-sm font-mono text-emerald-400 bg-emerald-500/10 p-2 rounded border border-emerald-500/20">
                         <Check size={14} /> Evidence Cached for [amy]
                      </div>
                   </div>
                </div>

                {/* Query 3 */}
                <div className="bg-cyan-500/5 border border-cyan-500/30 rounded-2xl p-6 relative overflow-hidden ring-1 ring-cyan-500/20 shadow-[0_0_30px_rgba(6,182,212,0.1)]">
                   <div className="absolute top-0 right-0 p-4 opacity-10">
                      <Zap size={64} className="text-cyan-400" />
                   </div>
                   <div className="text-xs font-mono text-cyan-400 font-bold mb-2 uppercase tracking-widest flex items-center gap-2">
                     <FastForward size={14} /> Query 3 (Combined)
                   </div>
                   <div className="text-white font-bold mb-4">"tell me about amy and food"</div>
                   <div className="space-y-3">
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                         <Search size={14} className="text-red-400" /> Global Cache Miss
                      </div>
                      <div className="flex items-center gap-3 text-sm text-white bg-black/40 p-2 rounded border border-white/10">
                         <BrainCircuit size={14} className="text-purple-400" /> LLM Breakdown: [amy], [food]
                      </div>
                      <div className="flex items-center gap-3 text-sm font-mono text-emerald-400 bg-emerald-500/10 p-2 rounded border border-emerald-500/20">
                         <Zap size={14} /> Sub-Query Cache HIT! (Zero Search Latency)
                      </div>
                   </div>
                </div>

             </div>

             <div className="bg-black/60 border border-white/10 rounded-xl p-5 text-sm text-muted-foreground flex gap-4 items-start">
               <ShieldAlert className="text-cyan-400 shrink-0 mt-0.5" size={18} />
               <p>
                 Because <code>_search.py</code> executes and caches searches concurrently for each decomposed sub-query, <strong>Query 3 bypasses the Vector DB entirely</strong>. It instantly loads the evidence packed independently by Query 1 and Query 2, proving O(1) latency for complex combined questions.
               </p>
             </div>
          </div>
        </div>

      </section>
    </motion.div>
  )
}
