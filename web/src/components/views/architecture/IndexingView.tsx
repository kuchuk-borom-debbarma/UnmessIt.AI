import { motion } from 'framer-motion'
import { Database, FileText, Cpu, Combine, Fingerprint, ShieldCheck, ArrowDown, FileCheck2, Network, Code2, Server, Activity } from 'lucide-react'

export function IndexingView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-32"
    >
      
      {/* Prologue / Overview */}
      <section id="overview" className="scroll-mt-32">
        <h1 className="text-5xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white via-white to-primary-500/50">
          The Architecture Novel
        </h1>
        <p className="text-xl text-muted-foreground leading-relaxed font-light mb-12">
          A progressive, exhaustive deep dive into the engineering of an unstructured knowledge engine.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <div className="bg-white/5 p-6 rounded-2xl border border-white/5 shadow-lg relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-500/5 to-transparent pointer-events-none" />
            <h3 className="text-2xl font-bold text-white mb-4">What is UnmessIt.AI?</h3>
            <p className="text-muted-foreground leading-relaxed">
              UnmessIt.AI is an advanced Retrieval-Augmented Generation (RAG) platform designed to turn chaotic, unstructured human notes into a unified knowledge graph. It allows users to dump messy thoughts and query them with absolute precision, backing up every generated answer with strict, verifiable source citations.
            </p>
          </div>
          
          <div className="bg-white/5 p-6 rounded-2xl border border-white/5 shadow-lg relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-bl from-accent-500/5 to-transparent pointer-events-none" />
            <h3 className="text-2xl font-bold text-white mb-4">System Overview</h3>
            <p className="text-muted-foreground leading-relaxed">
              The architecture avoids the idempotency nightmares of rigid Graph Databases by using <strong>Source Chunks</strong> as the absolute authority, enriched by deterministic <strong>Recall Keys</strong>. The system comprises a durable ingestion pipeline backed by Redis Streams, a multi-layer deterministic query engine, and real-time SSE observability.
            </p>
          </div>
        </div>
      </section>

      {/* Ch 1: Ingestion */}
      <section id="ingestion" className="scroll-mt-32">
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-sm font-bold uppercase tracking-wider mb-4">
            <Database size={14} /> Chapter 1
          </div>
          <h2 className="text-4xl font-bold tracking-tight mb-4 text-white">The Indexing Engine</h2>
          <p className="text-lg text-muted-foreground">The engine translates raw human notes into structured, retrievable vectors and entities.</p>
        </div>
      
      {/* Level 1: Core Concept */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 text-lg border border-primary-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">L1</span>
            The Core Concept
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
            At its most basic level, indexing is about chopping up a document and asking an LLM to explain what each piece means. Standard RAG (Naive RAG) chops documents into isolated paragraphs. If paragraph A has the setup and paragraph B has the punchline, Naive RAG cannot connect them. Conversely, Graph RAG forces unstructured text into rigid nodes and edges, leading to idempotency nightmares. 
            <br/><br/>
            UnmessIt.AI relies on <strong>Source Chunks</strong> as the absolute authority, enriched by <strong>Recall Keys</strong>. The chunks become semantically connected without the crushing overhead of a rigid graph database.
          </p>
        </div>

        {/* Visual Flow: Level 1 */}
        <div className="liquid-glass rounded-3xl p-8 border border-white/5 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-primary-500/5 via-transparent to-transparent pointer-events-none" />
          
          <div className="flex flex-col items-center gap-6 relative z-10">
            <motion.div initial={{ y: -20, opacity: 0 }} whileInView={{ y: 0, opacity: 1 }} className="flex flex-col items-center">
              <div className="bg-white/10 p-6 rounded-2xl border border-white/10 shadow-lg text-center w-64">
                <FileText className="text-white mx-auto mb-3" size={32} />
                <h4 className="text-lg font-bold text-white">Raw Human Note</h4>
              </div>
              <div className="h-10 w-px bg-white/20 my-2" />
              <div className="bg-primary-500/20 text-primary-300 font-mono text-xs px-4 py-2 rounded-full border border-primary-500/30">
                Split into Source Chunks
              </div>
              <div className="h-10 w-px bg-white/20 my-2 relative">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full border-t border-white/20 w-64" />
              </div>
            </motion.div>

            <div className="flex gap-16">
              {[1, 2].map((chunk) => (
                <motion.div key={chunk} initial={{ y: 20, opacity: 0 }} whileInView={{ y: 0, opacity: 1 }} transition={{ delay: chunk * 0.2 }} className="flex flex-col items-center">
                  <div className="h-6 w-px bg-white/20" />
                  <div className="bg-white/5 p-6 rounded-2xl border border-white/10 shadow-lg text-center w-56 mb-6">
                    <Database className="text-primary-400 mx-auto mb-3" size={24} />
                    <h4 className="text-md font-bold text-white">Source Chunk {chunk}</h4>
                  </div>
                  
                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <Cpu className="text-muted-foreground mb-2" size={16} />
                      <div className="h-8 w-px bg-white/20 border-dashed" />
                      <div className="bg-white/5 p-3 rounded-xl border border-white/5 text-center mt-2 w-28">
                        <span className="text-xs text-white">LLM Summary</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-center">
                      <Cpu className="text-muted-foreground mb-2" size={16} />
                      <div className="h-8 w-px bg-white/20 border-dashed" />
                      <div className="bg-white/5 p-3 rounded-xl border border-white/5 text-center mt-2 w-28">
                        <span className="text-xs text-white">Recall Keys</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Level 2: Idempotency, Splitting & Caching */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 text-lg border border-primary-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">L2</span>
            Idempotency, Splitting & Exact Caching
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
            If a user fixes a single typo in a 10,000-word document, we cannot afford to pay OpenAI to re-summarize the 9,999 words that didn't change. 
            First, we split text cleanly. By default, <code>SourceWindowChain</code> splits at <code>2600</code> characters, but it intelligently seeks out double newlines (<code>\n\n</code>) to ensure paragraphs (and therefore complete ideas) are not severed in half.
            <br/><br/>
            We then introduce strict hashing and Exact Caching for every chunk. We hash the chunk text plus the LLM Signature.
          </p>
        </div>

        <div className="liquid-glass rounded-3xl p-8 border border-white/5 relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary-900/20 via-transparent to-transparent pointer-events-none" />
          
          <div className="flex flex-col md:flex-row items-center justify-center gap-8 relative z-10">
            <div className="bg-white/5 p-6 rounded-2xl border border-white/10 w-64 text-center">
               <FileText className="text-white mx-auto mb-2" />
               <div className="text-sm font-bold text-white mb-2">Raw Note</div>
               <div className="text-xs text-muted-foreground p-2 bg-black/40 rounded-lg">Compute content_hash (SHA-256)</div>
            </div>

            <ArrowDown className="text-white/20 md:-rotate-90" size={32} />

            <div className="bg-white/5 p-6 rounded-2xl border border-white/10 w-64 text-center relative">
               <div className="absolute -top-3 -right-3 bg-primary-500 text-white text-[10px] font-bold px-2 py-1 rounded-full shadow-lg">SEEK \n\n</div>
               <SplitIcon />
               <div className="text-sm font-bold text-white mt-4 mb-2">Split into Chunks</div>
               <div className="text-xs text-muted-foreground p-2 bg-black/40 rounded-lg">Hash(Chunk Text + LLM Sig)</div>
            </div>

            <ArrowDown className="text-white/20 md:-rotate-90" size={32} />

            <div className="flex flex-col gap-4">
              <div className="bg-primary-500/10 border border-primary-500/30 p-4 rounded-xl flex items-center gap-4 w-72">
                <Fingerprint className="text-primary-400" size={24} />
                <div>
                  <div className="text-sm font-bold text-white">✅ Cache HIT (1ms)</div>
                  <div className="text-xs text-primary-200/70">Return Cached Summaries</div>
                </div>
              </div>
              <div className="bg-orange-500/10 border border-orange-500/30 p-4 rounded-xl flex items-center gap-4 w-72">
                <Cpu className="text-orange-400" size={24} />
                <div>
                  <div className="text-sm font-bold text-white">❌ Cache MISS</div>
                  <div className="text-xs text-orange-200/70">LLM Extracts → Save to Cache</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Level 3: Deduplication */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 text-lg border border-primary-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">L3</span>
            The 4-Layer Deduplication Guard
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
            When the LLM hallucinates slightly different entities (e.g., "Python 3" and "Python"), we must prevent graph sprawl. The <code>RecallNormalizerChain</code> handles this strict deduplication. The Normalizer caps aliases at 10 items, strictly enforces string length limits, and if an exact match is ambiguous, it falls back to the normalized name match to ensure safe merging.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white/5 p-8 rounded-3xl border border-white/10 relative overflow-hidden group hover:border-primary-500/40 hover:bg-white/10 transition-all duration-500 shadow-lg">
            <div className="absolute -right-4 -top-4 text-9xl text-white/[0.02] font-black pointer-events-none group-hover:text-primary-500/[0.05] transition-colors">1</div>
            <SearchIcon className="text-primary-500 mb-6 drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]" size={36} />
            <h4 className="text-2xl font-bold text-white mb-4 leading-snug">Pre-prompt Candidate Retrieval</h4>
            <p className="text-base text-muted-foreground leading-relaxed mb-4">
              We cannot load thousands of existing entities into the LLM context. Instead, the <code>RecallCandidateChain</code> first extracts <code>salient_entities</code> from the Source Chunks. We then perform a concurrent <strong>SQLite FTS lookup</strong> (exact keyword) and a <strong>Chroma Vector Search</strong> (semantic meaning) for those specific entities. The resulting candidates are merged and injected into the LLM system prompt: <span className="text-primary-300">"Only extract these specific entities if they match..."</span>
            </p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-white/5 p-8 rounded-3xl border border-white/10 relative overflow-hidden group hover:border-primary-500/40 hover:bg-white/10 transition-all duration-500 shadow-lg">
            <div className="absolute -right-4 -top-4 text-9xl text-white/[0.02] font-black pointer-events-none group-hover:text-primary-500/[0.05] transition-colors">2</div>
            <Combine className="text-primary-500 mb-6 drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]" size={36} />
            <h4 className="text-2xl font-bold text-white mb-4 leading-snug">In-Memory Batch Merge</h4>
            <p className="text-base text-muted-foreground leading-relaxed mb-4">Even with prompting, an LLM might return "Python 3" and "Python" in the same exact extraction array. The <code>RecallNormalizerChain</code> performs an immediate in-memory pass (using string normalization, casing, and basic distance) to merge duplicates from the <strong>same job</strong> before they ever reach the database.</p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-white/5 p-8 rounded-3xl border border-white/10 relative overflow-hidden group hover:border-primary-500/40 hover:bg-white/10 transition-all duration-500 shadow-lg">
            <div className="absolute -right-4 -top-4 text-9xl text-white/[0.02] font-black pointer-events-none group-hover:text-primary-500/[0.05] transition-colors">3</div>
            <Database className="text-primary-500 mb-6 drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]" size={36} />
            <h4 className="text-2xl font-bold text-white mb-4 leading-snug">Exact-Match Repository Lookup</h4>
            <p className="text-base text-muted-foreground leading-relaxed mb-4">When a normalized entity is about to be saved, we perform an explicit <code>WHERE canonical_name = ?</code> lookup in SQLite. If "Javascript" already exists, we do not create a new vector. We simply append the new Source Chunk ID to the lineage of the existing "Javascript" graph node.</p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="bg-white/5 p-8 rounded-3xl border border-white/10 relative overflow-hidden group hover:border-primary-500/40 hover:bg-white/10 transition-all duration-500 shadow-lg">
            <div className="absolute -right-4 -top-4 text-9xl text-white/[0.02] font-black pointer-events-none group-hover:text-primary-500/[0.05] transition-colors">4</div>
            <ShieldCheck className="text-primary-500 mb-6 drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]" size={36} />
            <h4 className="text-2xl font-bold text-white mb-4 leading-snug">SQLite Unique Constraints</h4>
            <p className="text-base text-muted-foreground leading-relaxed mb-4">The absolute final line of defense against race conditions. If two separate background jobs process two different documents at the exact same millisecond and both try to create "Rust", the database schema enforces <code>UNIQUE(canonical_name, user_id)</code>, throwing an <code>IntegrityError</code> that forces one worker to retry and merge.</p>
          </motion.div>

        </div>
      </div>

      {/* Level 4: LangGraph */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 text-lg border border-primary-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">L4</span>
            The Code Reality (Durable LangGraph)
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
            Because indexing takes time and APIs fail, the entire sequence is wrapped in a durable LangGraph state machine. Each step acts as a deterministic checkpoint. Here is the exact Python implementation from <code>server/src/services/rag/private/durability/runner.py</code> showing how this graph is constructed in memory:
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 liquid-glass rounded-3xl p-6 border border-white/10 font-mono text-sm text-primary-300/90 overflow-x-auto shadow-2xl relative">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-500 to-accent-500" />
            <pre className="leading-loose" dangerouslySetInnerHTML={{ __html: `
<span class="text-purple-400">def</span> <span class="text-blue-400">_build_graph</span>(self):
    <span class="text-slate-500">"""Build the fixed durable ingest workflow once per runner."""</span>
    graph = StateGraph(IngestGraphState)
    
    <span class="text-slate-500"># 1. Register Nodes</span>
    graph.add_node(<span class="text-emerald-400">"load_raw_input"</span>, self._load_raw_input)
    graph.add_node(<span class="text-emerald-400">"source_chunks"</span>, self._source_chunk_node)
    graph.add_node(<span class="text-emerald-400">"recall"</span>, self._recall_node)
    graph.add_node(<span class="text-emerald-400">"recall_vectors"</span>, self._recall_vector_node)
    graph.add_node(<span class="text-emerald-400">"source_vectors"</span>, self._source_vector_node)
    graph.add_node(<span class="text-emerald-400">"complete"</span>, self._complete_node)
    graph.add_node(<span class="text-emerald-400">"abort"</span>, self._abort_node)
    
    <span class="text-slate-500"># 2. Wire Edges</span>
    graph.add_edge(START, <span class="text-emerald-400">"load_raw_input"</span>)
    graph.add_conditional_edges(
        <span class="text-emerald-400">"load_raw_input"</span>, 
        self._after_load_raw_input, 
        {"abort": <span class="text-emerald-400">"abort"</span>, "continue": <span class="text-emerald-400">"source_chunks"</span>}
    )
    graph.add_edge(<span class="text-emerald-400">"source_chunks"</span>, <span class="text-emerald-400">"recall"</span>)
    graph.add_edge(<span class="text-emerald-400">"recall"</span>, <span class="text-emerald-400">"recall_vectors"</span>)
    graph.add_edge(<span class="text-emerald-400">"recall_vectors"</span>, <span class="text-emerald-400">"source_vectors"</span>)
    graph.add_edge(<span class="text-emerald-400">"source_vectors"</span>, <span class="text-emerald-400">"complete"</span>)
    
    graph.add_edge(<span class="text-emerald-400">"complete"</span>, END)
    graph.add_edge(<span class="text-emerald-400">"abort"</span>, END)
    <span class="text-purple-400">return</span> graph.compile()
            ` }} />
          </div>
          
          <div className="lg:col-span-5 flex flex-col gap-3 relative">
            <div className="absolute left-6 top-6 bottom-6 w-0.5 bg-white/10" />
            {[
              { id: 'START', label: 'DurableIngestRunner', icon: Code2 },
              { id: 'load_raw_input', label: 'Fetch from SQLite', icon: Database },
              { id: 'source_chunks', label: 'Split & Hash', icon: SplitIcon },
              { id: 'recall', label: 'Cache/LLM & Dedupe', icon: Brain },
              { id: 'recall_vectors', label: 'Embed Keys to Chroma', icon: Network },
              { id: 'source_vectors', label: 'Embed Chunks & Lineage', icon: Network },
              { id: 'complete', label: 'Mark Done & Fire SSE', icon: Server }
            ].map((node, i) => (
              <motion.div 
                key={node.id}
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-6 relative z-10"
              >
                <div className="w-12 h-12 rounded-full bg-[#0a0a0b] border-[3px] border-primary-500/30 flex items-center justify-center text-primary-400 shrink-0 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                  <node.icon size={18} />
                </div>
                <div className="flex-1 bg-white/5 p-4 rounded-xl border border-white/10 text-white group hover:bg-white/10 transition-colors">
                  <div className="font-mono text-sm text-primary-300 mb-1">node: {node.id}</div>
                  <div className="text-xs text-muted-foreground">{node.label}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Level 5: The Full Integrated Picture */}
      <div className="space-y-8">
        <div>
          <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
            <span className="w-10 h-10 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 text-lg border border-primary-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">L5</span>
            The Full Integrated Picture
          </h3>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
            Now that we have explained every component piece-by-piece, here is the brutal reality of the absolute, end-to-end Indexing flow integrating the DB, the LangGraph, the Checkpoints, the Embedding, the Cache, and the SSE fanout.
          </p>
        </div>

        <div className="w-full bg-[#050505] rounded-3xl border border-white/10 p-8 overflow-x-auto shadow-2xl">
           <div className="min-w-[900px] flex flex-col gap-6 font-mono text-xs">
              
              {/* Request Phase */}
              <div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/10">
                 <div className="bg-blue-500 text-white px-3 py-1 rounded font-bold">POST /notes/</div>
                 <ArrowDown className="-rotate-90 text-white/40" size={16} />
                 <div className="text-white">Save note to SQLite → Write event_outbox ('note.created')</div>
                 <ArrowDown className="-rotate-90 text-white/40" size={16} />
                 <div className="bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded border border-emerald-500/30">Return 200 OK to User</div>
              </div>

              {/* Background Phase */}
              <div className="pl-12 flex flex-col gap-4 border-l-2 border-dashed border-white/20 ml-6 py-4">
                 
                 <div className="flex items-center gap-4">
                   <div className="bg-purple-500/20 text-purple-300 px-3 py-2 rounded-lg border border-purple-500/30 font-bold flex items-center gap-2">
                     <Server size={14} /> Redis Streams Listener consumes event
                   </div>
                   <ArrowDown className="-rotate-90 text-white/40" size={16} />
                   <div className="text-muted-foreground">submit_ingest_job(job_id=note_id)</div>
                 </div>

                 <div className="bg-white/5 p-6 rounded-2xl border border-white/10 mt-4 relative">
                   <div className="absolute -left-[35px] top-8 w-8 border-t-2 border-dashed border-white/20" />
                   <div className="text-primary-400 font-bold text-sm mb-4">Background Ingest Job Starts (LangGraph workflow)</div>
                   
                   <div className="space-y-4">
                     <div className="flex items-center gap-4 bg-black/40 p-3 rounded-lg border border-white/5">
                        <Database size={14} className="text-blue-400" />
                        <span className="text-white">Hash text → content_hash | Save/reuse raw_input row</span>
                        <span className="ml-auto bg-blue-500/20 text-blue-300 px-2 py-1 rounded text-[10px]">Checkpoint: raw_input</span>
                     </div>
                     
                     <div className="flex items-center gap-4 bg-black/40 p-3 rounded-lg border border-white/5">
                        <SplitIcon />
                        <span className="text-white">Split raw_input into source windows | Save as source_chunks</span>
                        <span className="ml-auto bg-blue-500/20 text-blue-300 px-2 py-1 rounded text-[10px]">Checkpoint: source_piece</span>
                     </div>

                     <div className="border border-primary-500/30 rounded-xl p-4 bg-primary-500/5">
                        <div className="text-primary-300 font-bold mb-4 flex items-center gap-2">
                          <RefreshCw size={14} /> Loop over each source_chunk
                        </div>
                        
                        <div className="flex flex-col gap-3 pl-6 border-l border-primary-500/20">
                           <div className="flex items-center gap-4">
                             <div className="bg-orange-500/20 text-orange-300 px-2 py-1 rounded border border-orange-500/30 text-[10px]">Exact Cache: SourceChunkDraftChain</div>
                             <span className="text-white/60">Key: SHA256(text) + llm_sig</span>
                           </div>
                           
                           <div className="flex items-center gap-4">
                              <span className="text-emerald-400 font-bold">✅ HIT</span>
                              <span className="text-white/40">OR</span>
                              <span className="text-red-400 font-bold">❌ MISS → LLM generates neutral summary</span>
                           </div>

                           <div className="flex items-center gap-4 mt-2">
                             <div className="bg-orange-500/20 text-orange-300 px-2 py-1 rounded border border-orange-500/30 text-[10px]">Exact Cache: RecallDraftChain</div>
                             <span className="text-white/60">Key: SHA256(text) + llm_sig</span>
                           </div>

                           <div className="flex items-center gap-4">
                              <span className="text-emerald-400 font-bold">✅ HIT</span>
                              <span className="text-white/40">OR</span>
                              <span className="text-red-400 font-bold">❌ MISS → LLM Extracts Recall Keys</span>
                           </div>

                           <div className="flex items-center gap-4 mt-2">
                             <span className="text-white">Deduplicate (4 layers) | Save/update recall_keys</span>
                             <span className="ml-auto bg-blue-500/20 text-blue-300 px-2 py-1 rounded text-[10px]">Checkpoint: recall_chunk</span>
                           </div>
                        </div>
                     </div>

                     <div className="flex items-center gap-4 bg-black/40 p-3 rounded-lg border border-white/5">
                        <Network size={14} className="text-pink-400" />
                        <span className="text-white">Embed source_chunks & recall_keys | Upsert to ChromaDB</span>
                        <span className="ml-auto bg-blue-500/20 text-blue-300 px-2 py-1 rounded text-[10px]">Checkpoint: source_vector / recall_key_vector</span>
                     </div>

                     <div className="flex items-center gap-4 bg-black/40 p-3 rounded-lg border border-white/5">
                        <FileCheck2 size={14} className="text-emerald-400" />
                        <span className="text-white">Lineage Materialization (Parse note directory path)</span>
                     </div>
                     
                     <div className="flex items-center gap-4 bg-black/40 p-3 rounded-lg border border-white/5">
                        <Activity size={14} className="text-purple-400" />
                        <span className="text-white">Publish ingest_job.changed to SSE</span>
                        <span className="ml-auto bg-emerald-500/20 text-emerald-300 px-2 py-1 rounded text-[10px] font-bold">Mark Job Complete</span>
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

function SearchIcon(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
    </svg>
  )
}

function SplitIcon(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white mx-auto mb-2">
      <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><line x1="12" x2="12" y1="3" y2="21"/>
    </svg>
  )
}

function Brain(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/><path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/><path d="M3.477 10.896a4 4 0 0 1 .585-.396"/><path d="M19.938 10.5a4 4 0 0 1 .585.396"/><path d="M6 18a4 4 0 0 1-1.967-.516"/><path d="M19.967 17.484A4 4 0 0 1 18 18"/>
    </svg>
  )
}

function RefreshCw(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
    </svg>
  )
}
