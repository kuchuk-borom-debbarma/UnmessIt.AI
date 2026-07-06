import { motion } from 'framer-motion'
import { SearchIcon, Network, Zap, ArrowRight, Waypoints, Shrink, ShieldCheck, MonitorSmartphone, Database, BrainCircuit, Activity, RefreshCw } from 'lucide-react'

export function QueryingView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-32 pb-32"
    >
      <section id="query-engine" className="scroll-mt-32">
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 border border-accent-500/20 text-accent-400 text-sm font-bold uppercase tracking-wider mb-4">
            <SearchIcon size={14} /> Chapter 2
          </div>
          <h2 className="text-4xl font-bold tracking-tight mb-4 text-white">The Query Engine</h2>
          <p className="text-lg text-muted-foreground max-w-4xl leading-relaxed">
            Retrieval must be highly accurate, fast, and prevent hallucinations. It does this by building up defensive layers of Exact Caching, Semantic Verification, Deterministic Expansion, Parallel Traversal, and strict Validation.
          </p>
        </div>

        {/* Stage 1: Top-Level Exact & Semantic Cache */}
        <div className="space-y-8 mt-16">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">1</span>
              Top-Level Exact & Semantic Caches
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
              Before executing <em>any</em> expensive logic, we check the Top-Level Exact Cache (1ms hit). If that misses, we check the Semantic Cache. If the query distance is &lt; 0.02, it's an instant hit. If it's between 0.02 and 0.05, an LLM Verifier checks if the cached payload is safe to reuse.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl flex flex-col items-center">
              <div className="bg-black/50 p-4 rounded-xl border border-accent-500/30 text-accent-300 w-full text-center shadow-lg font-bold">
                "How do you deploy Postgres?"
              </div>
              <ArrowRight className="text-white/20 rotate-90 my-2" />
              <div className="grid grid-cols-2 gap-4 w-full">
                <div className="bg-emerald-500/10 border border-emerald-500/30 p-3 rounded-lg text-emerald-400 text-sm text-center">
                  Distance: 0.01<br/>(Exact: "How to deploy postgres")
                </div>
                <div className="bg-orange-500/10 border border-orange-500/30 p-3 rounded-lg text-orange-400 text-sm text-center">
                  Distance: 0.04<br/>(Near: "Postgres deployment guide")
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 w-full mt-2">
                 <div className="text-center"><ArrowRight className="text-white/20 rotate-90 mx-auto" /></div>
                 <div className="text-center"><ArrowRight className="text-white/20 rotate-90 mx-auto" /></div>
              </div>
              <div className="grid grid-cols-2 gap-4 w-full mt-2">
                <div className="bg-emerald-500/20 border border-emerald-500/40 p-3 rounded-lg text-emerald-300 text-sm font-bold flex items-center justify-center gap-2">
                  <Zap size={16} /> Instant Hit
                </div>
                <div className="bg-orange-500/20 border border-orange-500/40 p-3 rounded-lg text-orange-300 text-sm font-bold flex items-center justify-center gap-2">
                  <ShieldCheck size={16} /> Verifier LLM Check
                </div>
              </div>
            </div>
            
            <div className="liquid-glass rounded-3xl p-6 border border-white/10 font-mono text-sm text-accent-200/90 overflow-x-auto shadow-2xl relative h-full flex flex-col justify-center">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent-500 to-orange-500" />
              <pre className="leading-loose" dangerouslySetInnerHTML={{ __html: `
<span class="text-purple-400">if</span> distance &lt; _EXACT_MATCH_EPSILON:
    is_safe = <span class="text-orange-400">True</span>
<span class="text-purple-400">else</span>:
    <span class="text-slate-500"># Fast LLM call to verify context safety</span>
    verifier = SemanticSubQueryVerifierChain()
    is_safe = <span class="text-purple-400">await</span> verifier.run(...)

<span class="text-purple-400">if</span> is_safe:
    <span class="text-purple-400">return</span> cached_payload
              ` }} />
            </div>
          </div>
        </div>

        {/* Stage 2: Breakdown & Extraction */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">2</span>
              Query Breakdown, Expansion & Subject Extraction
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-6">
              If all caches miss, we decompose the user's query into up to 6 distinct sub-queries.
              We then run a deterministic fan-out, checking for Attribute, Comparison, and Reasoning triggers to inject explicit terms (e.g., adding "parallels", "differences").
            </p>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              Finally, we run an LLM Subject Extraction to identify named entities (e.g. translating "that guy with the car" into explicit noun targets) to anchor our exact-match lexical searches.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-center shadow-xl flex flex-col items-center">
              <BrainCircuit className="w-10 h-10 text-indigo-400 mb-4" />
              <h4 className="font-bold text-white mb-2">1. Decompose</h4>
              <p className="text-sm text-indigo-200/70">Break complex questions into singular, atomic sub-queries.</p>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-center shadow-xl flex flex-col items-center">
              <Waypoints className="w-10 h-10 text-emerald-400 mb-4" />
              <h4 className="font-bold text-white mb-2">2. Deterministic Expand</h4>
              <p className="text-sm text-emerald-200/70">Inject hidden lexical keywords like "compare", "causes", "features".</p>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-center shadow-xl flex flex-col items-center">
              <SearchIcon className="w-10 h-10 text-orange-400 mb-4" />
              <h4 className="font-bold text-white mb-2">3. Extract Subjects</h4>
              <p className="text-sm text-orange-200/70">Isolate exact nouns to prepare for SQLite FTS queries.</p>
            </div>
          </div>
        </div>

        {/* Stage 3: Batch Evidence Cache */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">3</span>
              Batch Evidence Exact Cache
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-6">
              We now have an exact array of sub-queries and subjects. Before running the database searches, we hash this entire array and check the Batch Evidence Exact Cache. If another user recently ran these exact same atomic searches, we instantly retrieve the Chunks and skip all Vector/Lexical IO.
            </p>
          </div>
        </div>

        {/* Stage 4: Parallel Traversal */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">4</span>
              Parallel 3-Prong Traversal
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
              If the Batch Evidence cache misses, we execute a concurrent per-sub-query scatter-gather. We fire 3 simultaneous searches in <code>_search.py</code> using <code>asyncio.gather</code>.
            </p>
          </div>

          <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl relative overflow-hidden">
             <div className="flex flex-col gap-6">
               <div className="flex items-center gap-4 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
                 <div className="p-3 bg-blue-500/20 rounded-lg text-blue-400"><Network size={24}/></div>
                 <div>
                   <div className="font-bold text-white text-lg">1. Vector Search (Chroma)</div>
                   <div className="text-sm text-blue-200/70 mt-1">Finds chunks by semantic distance (topic meaning).</div>
                 </div>
               </div>
               <div className="flex items-center gap-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                 <div className="p-3 bg-emerald-500/20 rounded-lg text-emerald-400"><Database size={24}/></div>
                 <div>
                   <div className="font-bold text-white text-lg">2. Lexical Search (SQLite FTS)</div>
                   <div className="text-sm text-emerald-200/70 mt-1">Finds chunks by exact keyword and extracted subject matches.</div>
                 </div>
               </div>
               <div className="flex items-center gap-4 p-4 rounded-xl bg-purple-500/10 border border-purple-500/20">
                 <div className="p-3 bg-purple-500/20 rounded-lg text-purple-400"><Waypoints size={24}/></div>
                 <div>
                   <div className="font-bold text-white text-lg">3. Graph Traversal (Recall Links)</div>
                   <div className="text-sm text-purple-200/70 mt-1">Queries FTS and Vector DBs to find Recall Keys (nodes), then traverses Recall Links (edges) to pull connected Source Chunks.</div>
                 </div>
               </div>
             </div>
             <div className="mt-8 text-center bg-white/5 py-4 rounded-xl border border-white/10">
               <div className="text-white font-bold mb-2">Merge, Dedupe & Score</div>
               <div className="text-sm text-muted-foreground px-4">Chunks discovered via multiple independent paths receive a massive ranking boost. The top 12 chunks are selected.</div>
             </div>
          </div>
        </div>

        {/* Stage 5: Context Compaction */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">5</span>
              Context Engineering & Compaction
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
              If the merged chunks exceed 9,000 characters, we aggressively prune irrelevant sentences. The <code>_pack_context</code> function uses a Compactor LLM chain.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl flex flex-col justify-center">
               <div className="flex items-center justify-between mb-4">
                 <span className="text-white font-bold">Raw Source Chunks</span>
                 <span className="text-xs font-mono bg-white/10 px-2 py-1 rounded text-white/60">~12,000 chars</span>
               </div>
               <div className="bg-black/50 p-4 rounded-xl border border-red-500/30 text-red-200/70 text-sm line-through">
                 ...the weather was nice that day. We discussed the new project...
               </div>
               <div className="bg-black/50 p-4 rounded-xl border border-emerald-500/30 text-emerald-300 text-sm font-bold mt-2">
                 The API server must be deployed using Docker with port 8080 exposed.
               </div>
               <div className="bg-black/50 p-4 rounded-xl border border-red-500/30 text-red-200/70 text-sm line-through mt-2">
                 ...we also ordered pizza for the team...
               </div>
            </div>
            
            <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl flex flex-col justify-center items-center text-center group hover:bg-white/10 transition-colors cursor-default relative overflow-hidden h-full">
               <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent-500 to-accent-300" />
               <Shrink className="w-16 h-16 text-accent-400 mb-6 group-hover:scale-110 transition-transform" />
               <h4 className="text-2xl font-bold text-white mb-2">Compacted Context</h4>
               <p className="text-accent-200/70 mb-4 text-sm max-w-xs mx-auto">
                 Filters down to max 4500 chars containing exact relevant sentences only.
               </p>
               <div className="bg-accent-500/20 text-accent-300 px-4 py-2 rounded-full font-mono text-xs border border-accent-500/30">
                 _context_compactor_cache_key
               </div>
               <p className="text-xs text-muted-foreground mt-4">
                 Compacted snippets are independently cached. We never compact the same chunk twice.
               </p>
            </div>
          </div>
        </div>

        {/* Stage 6: LLM Evidence Verifier & 2nd Pass Search */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">6</span>
              LLM Evidence Verifier & 2nd Pass Search
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-6">
              The compacted chunks are passed to the <code>LLM Evidence Verifier</code>. This strict guardrail drops any remaining off-topic chunks.
              Crucially, if the Verifier determines that the remaining chunks are insufficient to answer the query, it triggers a <strong>2nd Pass Search</strong> with a highly focused re-query, retrieving fresh chunks to fill the gap.
            </p>
          </div>
        </div>

        {/* Stage 7: Answer Generation & Citations */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">7</span>
              Answer Generation & Strict Citation Parsing
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-6">
              The finalized, verified context is injected into the Answer Generation prompt. The <code>_answer_system_prompt</code> enforces strict synthesis rules (e.g., "Preserve exact actor/patient relationships", "Answer the supported part first and briefly name what is missing").
            </p>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-8">
              The LLM is instructed to embed <code>[cite](source_chunk_id)</code> markers inline. The <code>_normalize_answer_result</code> function aggressively strips out hallucinated citations, validates IDs against retrieved chunks, and caps the total citations to 6. We then cache this final JSON.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
            <div className="lg:col-span-7 liquid-glass rounded-3xl p-6 border border-white/10 font-mono text-sm text-accent-200/90 overflow-x-auto shadow-2xl relative scrollbar-hide">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent-500 to-purple-500" />
              <pre className="leading-loose whitespace-pre" dangerouslySetInnerHTML={{ __html: `
<span class="text-purple-400">def</span> <span class="text-blue-400">_normalize_answer_result</span>(data, chunks):
    answer = str(data.get(<span class="text-emerald-400">"answer"</span>)).strip()
    valid_ids = {chunk[<span class="text-emerald-400">"id"</span>] <span class="text-purple-400">for</span> chunk <span class="text-purple-400">in</span> chunks}
    
    <span class="text-slate-500"># Extract modern [cite](id) markdown markers</span>
    marker_ids = []
    <span class="text-purple-400">for</span> match <span class="text-purple-400">in</span> re.finditer(<span class="text-emerald-400">r'\\[([^\\]]+)\\]\\(([^)\\s]+)\\)'</span>, answer):
        <span class="text-purple-400">if</span> <span class="text-emerald-400">"cite"</span> <span class="text-purple-400">in</span> match.group(1).lower() <span class="text-purple-400">or</span> match.group(2) <span class="text-purple-400">in</span> valid_ids:
            marker_ids.append(match.group(2))
            
    <span class="text-slate-500"># Strip hallucinated citations not found in context</span>
    marker_ids = [m <span class="text-purple-400">for</span> m <span class="text-purple-400">in</span> marker_ids <span class="text-purple-400">if</span> m <span class="text-purple-400">in</span> valid_ids]
    
    <span class="text-slate-500"># Cap max citations and sanitize the final markdown</span>
    data_ids = [str(i) <span class="text-purple-400">for</span> i <span class="text-purple-400">in</span> data.get(<span class="text-emerald-400">"citation_ids"</span>, []) <span class="text-purple-400">if</span> str(i) <span class="text-purple-400">in</span> valid_ids]
    citation_ids = list(dict.fromkeys([*data_ids, *marker_ids]))[:6]
    
    answer = _sanitize_answer_citations(answer, set(citation_ids))
    
    <span class="text-purple-400">return</span> {<span class="text-emerald-400">"answer"</span>: answer, <span class="text-emerald-400">"citation_ids"</span>: citation_ids}
              ` }} />
            </div>
            
            <div className="lg:col-span-5 liquid-glass rounded-3xl p-8 border border-white/10 shadow-xl flex flex-col justify-center relative overflow-hidden group hover:border-indigo-500/40 transition-colors">
               <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-purple-500" />
               <div className="flex justify-between items-center mb-6">
                 <div className="text-white font-bold flex items-center gap-2"><MonitorSmartphone size={18} className="text-indigo-400"/> UI Rendering</div>
                 <div className="bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full font-mono text-xs border border-indigo-500/30">React Component</div>
               </div>
               <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-6 text-indigo-100 leading-relaxed shadow-inner text-[15px]">
                 Redis Streams are used for durable background job queues <sup className="bg-indigo-500 text-white px-2 py-0.5 rounded text-[11px] font-bold cursor-pointer shadow-[0_0_10px_rgba(99,102,241,0.5)] hover:bg-indigo-400 transition-colors">1</sup>, ensuring that even if the API server crashes, the task is resumed.
               </div>
               <div className="mt-6 text-center text-indigo-300/70 text-sm font-medium">
                 The raw <code>[cite](id)</code> markdown is translated into interactive superscript elements linking to the Source Chunks.
               </div>
            </div>
          </div>
        </div>

        {/* Stage 8: SSE Trace Reality */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">8</span>
              SSE Trace Compilation
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-6">
              Throughout this entire LangGraph execution, the backend emits <code>retrieval_trace.ui</code> events over Server-Sent Events (SSE). 
              The frontend catches these real-time streams to render exactly which caches hit, how many LLM tokens were saved, and the sub-millisecond execution times for every step.
            </p>
          </div>
          
          <div className="bg-white/5 border border-white/10 rounded-3xl p-8 flex flex-col md:flex-row items-center gap-8 shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent pointer-events-none" />
            <div className="p-6 bg-black/40 rounded-2xl border border-white/5 shadow-inner flex-1 w-full relative z-10">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-white font-bold"><Activity size={16} className="text-emerald-400"/> Live Trace Stream</div>
                <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span><span className="text-xs text-muted-foreground font-mono">Connected</span></div>
              </div>
              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between items-center text-slate-300"><span className="flex items-center gap-2"><RefreshCw size={12} className="animate-spin text-blue-400" /> Searching Vector DB...</span> <span>42ms</span></div>
                <div className="flex justify-between items-center text-slate-400"><span className="flex items-center gap-2 text-emerald-400">✓ Context Compactor Cache Hit</span> <span>1ms</span></div>
                <div className="flex justify-between items-center text-slate-400"><span className="flex items-center gap-2 text-emerald-400">✓ Evidence Verifier Completed</span> <span>845ms</span></div>
                <div className="flex justify-between items-center text-slate-300"><span className="flex items-center gap-2"><RefreshCw size={12} className="animate-spin text-purple-400" /> Generating Answer...</span> <span>In Progress</span></div>
              </div>
            </div>
            <div className="flex-1 text-center md:text-left z-10">
              <h4 className="text-2xl font-bold text-white mb-3">Transparent Engine</h4>
              <p className="text-muted-foreground text-sm leading-relaxed max-w-sm mx-auto md:mx-0">
                The user is never left waiting in the dark. Every single decision, cache hit, and parallel search is streamed directly to the UI, proving the engine's complexity and speed in real-time.
              </p>
            </div>
          </div>
        </div>

        {/* Stage 9: The Complete Flow */}
        <div className="space-y-8 mt-32 border-t border-white/10 pt-16">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-lg border border-accent-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]">9</span>
              The Complete Query Execution Flow
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl mb-12">
              This is the literal execution path from <code>server/src/services/rag/private/chains/query/__init__.py</code>. It brings all of the caches, verifiers, and parallel searches together into a single, cohesive timeline.
            </p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-3xl p-8 lg:p-12 shadow-2xl relative overflow-hidden">
             <div className="absolute top-0 right-0 p-8 opacity-5">
               <Network size={200} />
             </div>
             
             <div className="relative z-10 max-w-4xl mx-auto">
                <div className="flex flex-col relative">
                  
                  {/* Vertical Line */}
                  <div className="absolute left-[27px] top-4 bottom-4 w-0.5 bg-gradient-to-b from-accent-500 via-orange-500 to-indigo-500 opacity-30" />

                  <div className="flex flex-col gap-6">
                    {/* Step 1 */}
                    <div className="flex items-start gap-6">
                       <div className="w-14 h-14 shrink-0 rounded-2xl bg-black/50 border border-white/10 flex items-center justify-center z-10 shadow-lg">
                          <Activity className="text-accent-400" />
                       </div>
                       <div className="bg-black/40 border border-white/5 rounded-2xl p-5 flex-1 relative mt-1">
                          <div className="absolute -left-2 top-6 w-2 h-0.5 bg-white/20" />
                          <div className="flex items-center gap-4 mb-2">
                            <span className="text-white font-bold text-lg">Receive QueryInput</span>
                            <span className="bg-accent-500/20 text-accent-300 px-2 py-0.5 rounded text-[10px] font-mono border border-accent-500/30">SSE stream started</span>
                          </div>
                          <div className="text-sm text-muted-foreground">The API accepts the query and begins streaming <code>retrieval_trace.ui</code> events.</div>
                       </div>
                    </div>

                    {/* Step 2 */}
                    <div className="flex items-start gap-6">
                       <div className="w-14 h-14 shrink-0 rounded-2xl bg-black/50 border border-emerald-500/30 flex items-center justify-center z-10 shadow-lg shadow-emerald-500/10">
                          <Zap className="text-emerald-400" />
                       </div>
                       <div className="bg-black/40 border border-white/5 rounded-2xl p-5 flex-1 relative mt-1">
                          <div className="absolute -left-2 top-6 w-2 h-0.5 bg-white/20" />
                          <div className="flex items-center gap-4 mb-3">
                            <span className="text-white font-bold text-lg">Top-Level Caches</span>
                            <span className="bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded text-[10px] font-mono border border-emerald-500/30">1ms Hit</span>
                          </div>
                          <div className="flex flex-col gap-2 pl-4 border-l border-emerald-500/20 text-sm font-mono mt-2">
                             <div className="text-white/70">1. Exact Cache Check (SHA256)</div>
                             <div className="text-white/70">2. Semantic Cache Check (Distance &lt; 0.02)</div>
                             <div className="text-white/70">3. Semantic Verifier (Distance &lt; 0.05)</div>
                          </div>
                       </div>
                    </div>

                    {/* Step 3 */}
                    <div className="flex items-start gap-6">
                       <div className="w-14 h-14 shrink-0 rounded-2xl bg-black/50 border border-white/10 flex items-center justify-center z-10 shadow-lg">
                          <BrainCircuit className="text-indigo-400" />
                       </div>
                       <div className="bg-black/40 border border-white/5 rounded-2xl p-5 flex-1 relative mt-1">
                          <div className="absolute -left-2 top-6 w-2 h-0.5 bg-white/20" />
                          <div className="flex items-center gap-4 mb-2">
                            <span className="text-white font-bold text-lg">Query Engineering Pipeline</span>
                            <span className="bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded text-[10px] font-mono border border-indigo-500/30">LLM + Logic</span>
                          </div>
                          <div className="flex gap-4 mt-4">
                            <div className="bg-indigo-500/10 border border-indigo-500/20 p-2 rounded flex-1 text-center text-xs text-indigo-200">Decompose</div>
                            <div className="bg-indigo-500/10 border border-indigo-500/20 p-2 rounded flex-1 text-center text-xs text-indigo-200">Fan-Out</div>
                            <div className="bg-indigo-500/10 border border-indigo-500/20 p-2 rounded flex-1 text-center text-xs text-indigo-200">Extract Nouns</div>
                          </div>
                       </div>
                    </div>

                    {/* Step 4 */}
                    <div className="flex items-start gap-6">
                       <div className="w-14 h-14 shrink-0 rounded-2xl bg-black/50 border border-white/10 flex items-center justify-center z-10 shadow-lg">
                          <SearchIcon className="text-orange-400" />
                       </div>
                       <div className="bg-black/40 border border-white/5 rounded-2xl p-5 flex-1 relative mt-1">
                          <div className="absolute -left-2 top-6 w-2 h-0.5 bg-white/20" />
                          <div className="flex items-center gap-4 mb-2">
                            <span className="text-white font-bold text-lg">Parallel 3-Prong Traversal</span>
                            <span className="bg-orange-500/20 text-orange-300 px-2 py-0.5 rounded text-[10px] font-mono border border-orange-500/30">asyncio.gather</span>
                          </div>
                          <div className="text-sm text-muted-foreground mb-3">Checks the Batch Evidence Cache first. On miss, searches concurrently:</div>
                          <div className="flex flex-col gap-2 pl-4 border-l border-orange-500/20 text-sm font-mono">
                             <div className="text-white/80 flex items-center gap-2"><Database size={12} className="text-blue-400" /> Vector DB (Semantic)</div>
                             <div className="text-white/80 flex items-center gap-2"><Database size={12} className="text-emerald-400" /> SQLite FTS (Lexical)</div>
                             <div className="text-white/80 flex items-center gap-2"><Network size={12} className="text-purple-400" /> Recall Graph Traversal (Edges)</div>
                          </div>
                          <div className="mt-4 bg-orange-500/10 border border-orange-500/30 p-2 rounded text-xs text-orange-200 text-center font-bold">
                             Merge & Dedupe (Massive boost for multi-path discoveries)
                          </div>
                       </div>
                    </div>

                    {/* Step 5 */}
                    <div className="flex items-start gap-6">
                       <div className="w-14 h-14 shrink-0 rounded-2xl bg-black/50 border border-white/10 flex items-center justify-center z-10 shadow-lg">
                          <Shrink className="text-pink-400" />
                       </div>
                       <div className="bg-black/40 border border-white/5 rounded-2xl p-5 flex-1 relative mt-1">
                          <div className="absolute -left-2 top-6 w-2 h-0.5 bg-white/20" />
                          <div className="flex items-center gap-4 mb-2">
                            <span className="text-white font-bold text-lg">Context Compaction</span>
                          </div>
                          <div className="text-sm text-muted-foreground">Compresses up to 12,000 chars of source chunks down to 4,500 chars containing only highly relevant sentences.</div>
                       </div>
                    </div>

                    {/* Step 6 */}
                    <div className="flex items-start gap-6">
                       <div className="w-14 h-14 shrink-0 rounded-2xl bg-black/50 border border-white/10 flex items-center justify-center z-10 shadow-lg">
                          <ShieldCheck className="text-red-400" />
                       </div>
                       <div className="bg-black/40 border border-white/5 rounded-2xl p-5 flex-1 relative mt-1">
                          <div className="absolute -left-2 top-6 w-2 h-0.5 bg-white/20" />
                          <div className="flex items-center gap-4 mb-2">
                            <span className="text-white font-bold text-lg">Evidence Verifier</span>
                            <span className="bg-red-500/20 text-red-300 px-2 py-0.5 rounded text-[10px] font-mono border border-red-500/30">Guardrail</span>
                          </div>
                          <div className="text-sm text-muted-foreground">Drops off-topic chunks. If context is insufficient, automatically triggers a highly focused <strong>2nd Pass Search</strong>.</div>
                       </div>
                    </div>

                    {/* Step 7 */}
                    <div className="flex items-start gap-6">
                       <div className="w-14 h-14 shrink-0 rounded-2xl bg-gradient-to-br from-accent-500 to-orange-500 border border-white/20 flex items-center justify-center z-10 shadow-[0_0_20px_rgba(239,68,68,0.3)]">
                          <MonitorSmartphone className="text-white" />
                       </div>
                       <div className="bg-black/40 border border-white/5 rounded-2xl p-5 flex-1 relative mt-1 shadow-xl">
                          <div className="absolute -left-2 top-6 w-2 h-0.5 bg-white/20" />
                          <div className="flex items-center gap-4 mb-2">
                            <span className="text-white font-bold text-lg">Answer Generation</span>
                          </div>
                          <div className="text-sm text-muted-foreground mb-3">The final LLM synthesizes the verified chunks, embedding <code>[cite](id)</code> inline.</div>
                          <div className="bg-black/50 border border-white/5 p-3 rounded-lg flex items-center gap-3">
                             <RefreshCw className="text-accent-400 animate-spin" size={16} />
                             <span className="text-sm text-white font-mono">_normalize_answer_result(data, chunks)</span>
                          </div>
                          <div className="text-xs text-accent-300 mt-2">Strips hallucinated citations, validates IDs, and caches the final JSON payload.</div>
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
