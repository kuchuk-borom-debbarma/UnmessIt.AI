import { motion } from 'framer-motion'
import { FileText, Network, Waypoints, BrainCircuit, ArrowRight } from 'lucide-react'

export function OverviewView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-32"
    >
      <section id="overview" className="scroll-mt-32">
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm font-bold uppercase tracking-wider mb-4">
            <BrainCircuit size={14} /> The Core Concept
          </div>
          <h2 className="text-4xl font-bold tracking-tight mb-4 text-white">How UnmessIt Really Works</h2>
          <p className="text-lg text-muted-foreground max-w-4xl leading-relaxed">
            UnmessIt isn't just a standard vector database where you embed whole documents and do simple similarity searches. 
            Standard RAG (Retrieval-Augmented Generation) fails on complex reasoning because it loses the relationship between ideas. 
            UnmessIt solves this by building a highly interconnected <strong>Knowledge Graph</strong> on top of chunked text.
          </p>
        </div>

        <div className="space-y-16">
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 text-sm border border-indigo-500/30">1</span>
                Chunking with Overlaps
              </h3>
              <p className="text-muted-foreground leading-relaxed mb-6">
                When you upload a document, we don't just shove it into a database. The <code>SourceWindowChain</code> meticulously splits the text into smaller, manageable pieces (Source Chunks) governed by a strict character limit. 
                Crucially, these chunks <strong>overlap</strong>. If Chunk 1 ends at character 2600, Chunk 2 might start at character 2400. This ensures that an idea spanning across a boundary isn't abruptly severed, preserving context.
              </p>
            </div>
            <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl relative overflow-hidden flex flex-col gap-4">
              <div className="absolute top-0 right-0 p-4 opacity-10"><FileText size={64} /></div>
              <div className="bg-indigo-500/20 border border-indigo-500/30 p-4 rounded-xl text-indigo-200 text-sm relative z-10 w-[80%]">
                "...the project relies on Redis for fast caching..."
              </div>
              <div className="bg-indigo-500/20 border border-indigo-500/30 p-4 rounded-xl text-indigo-200 text-sm relative z-10 w-[80%] self-end -mt-6 backdrop-blur-md">
                "...Redis for fast caching, and uses Pub/Sub for SSE..."
              </div>
              <div className="text-center text-xs text-indigo-400 font-mono mt-2">overlap = 200 chars</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div className="order-2 md:order-1 bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl relative overflow-hidden h-64 flex items-center justify-center">
               <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary-900/20 via-transparent to-transparent pointer-events-none" />
               <div className="relative z-10 text-center">
                 <div className="bg-primary-500/20 border border-primary-500/30 text-primary-300 px-6 py-3 rounded-full font-bold shadow-[0_0_20px_rgba(16,185,129,0.3)] mb-4 inline-flex items-center gap-2">
                   <Network size={18} /> Recall Key (Entity)
                 </div>
                 <div className="flex justify-center gap-8">
                   <ArrowRight className="text-white/20 rotate-90" />
                   <ArrowRight className="text-white/20 rotate-90" />
                 </div>
                 <div className="flex gap-4 mt-4">
                   <div className="bg-white/10 border border-white/20 text-white/70 px-4 py-2 rounded-lg text-sm">Source Chunk 1</div>
                   <div className="bg-white/10 border border-white/20 text-white/70 px-4 py-2 rounded-lg text-sm">Source Chunk 42</div>
                 </div>
               </div>
            </div>
            <div className="order-1 md:order-2">
              <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 text-sm border border-primary-500/30">2</span>
                Recall Keys & Links
              </h3>
              <p className="text-muted-foreground leading-relaxed">
                We feed each Source Chunk to an LLM, but we do NOT ask for a generic "Summary". 
                Instead, we force the LLM to extract highly specific nouns, concepts, and subjects. These become <strong>Recall Keys</strong> (nodes). 
                We then create <strong>Recall Links</strong> (edges) connecting the Recall Key back to the original Source Chunk. 
                If the entity "PostgreSQL" is mentioned in Chunk 1 and Chunk 42, a single "PostgreSQL" Recall Key acts as a central bridge connecting those disparate parts of the document.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 text-sm border border-purple-500/30">3</span>
                Graph Navigation (Querying)
              </h3>
              <p className="text-muted-foreground leading-relaxed">
                When you ask a question, we don't just blind-search the chunks. We decompose your question and search for the specific <strong>Recall Keys</strong> first. 
                Because the Recall Keys are interconnected hubs, finding the right Key instantly gives us direct, hard-linked pointers to every relevant Source Chunk that mentioned it, scattered across thousands of documents. 
                This graph traversal allows for incredible accuracy and prevents the LLM from hallucinating answers based on loosely-related semantic noise.
              </p>
            </div>
            <div className="bg-white/5 p-8 rounded-3xl border border-white/10 shadow-xl relative overflow-hidden flex flex-col items-center justify-center h-64 gap-6">
              <div className="absolute top-0 right-0 p-4 opacity-10"><Waypoints size={64} /></div>
              
              <div className="flex items-center gap-4 w-full">
                <div className="bg-black/50 border border-purple-500/30 text-purple-300 p-3 rounded-lg text-sm flex-1 text-center font-bold">Query: "How is caching handled?"</div>
              </div>
              <ArrowRight className="text-white/20 rotate-90" />
              <div className="flex items-center gap-4 w-full">
                <div className="bg-primary-500/20 border border-primary-500/30 text-primary-300 p-3 rounded-full text-sm flex-1 text-center font-bold">Key: "Redis"</div>
                <div className="bg-primary-500/20 border border-primary-500/30 text-primary-300 p-3 rounded-full text-sm flex-1 text-center font-bold">Key: "LRU Cache"</div>
              </div>
            </div>
          </div>

        </div>
      </section>
    </motion.div>
  )
}
