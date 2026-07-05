import {
  Database,
  Network,
  Quote,
  Search,
  Zap,
  Bot,
  CheckCircle2,
  Lock,
  FileText,
  Archive,
  Brain
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const USER_FEATURES = [
  {
    icon: FileText,
    title: 'Drop & Forget',
    desc: 'Append unstructured text or upload markdown notes. Everything is indexed automatically behind the scenes.',
  },
  {
    icon: Lock,
    title: 'Complete Privacy',
    desc: 'Fully self-hosted by default. Your personal knowledge graph never leaves your device unless you choose a public API.',
  },
  {
    icon: Network,
    title: 'Multi-Hop Reasoning',
    desc: 'Not just keyword search. The AI traverses connected concepts to answer complex questions across multiple notes.',
  },
  {
    icon: Quote,
    title: 'Instant Citations',
    desc: 'Every synthesized claim includes an inline link back to the exact note and line number it originated from.',
  },
]

export function LandingView() {
  const [demoStep, setDemoStep] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setDemoStep((s) => (s + 1) % 9)
    }, 1200)
    
    return () => {
      clearInterval(timer)
    }
  }, [])

  return (
    <div className="flex flex-col items-center justify-start w-full min-h-full py-10 font-sans relative overflow-x-hidden">
      {/* Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-accent-500/10 blur-[120px] rounded-full pointer-events-none" />

      {/* Hero Split Section */}
      <div className="w-full max-w-7xl px-4 grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center mt-10 md:mt-20 z-10">
        
        {/* Left Side: Copy */}
        <div className="flex flex-col items-start text-left">
          {/* Logo mock */}
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-primary-400 to-primary-600 p-[1px] shadow-lg mb-8">
            <div className="w-full h-full bg-[#0a0a0b] dark:bg-black rounded-2xl flex items-center justify-center liquid-glass">
               <img src="/favicon.svg" alt="UnmessIt.AI Logo" className="w-9 h-9 drop-shadow-md" />
            </div>
          </div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 mb-4"
          >
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-primary-500">Context Synthesis Engine</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl md:text-[4rem] font-extrabold tracking-tight text-foreground leading-[1.05] mb-6"
          >
            Messy notes <br/> become answers <br/> you can <span className="text-primary-500">trust.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-lg text-muted-foreground max-w-xl mb-8 font-medium leading-relaxed"
          >
            Stop digging through folders for forgotten ideas. Append messy data, ask a reasoning question, and get a synthesized answer with cited lines you can open instantly.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-wrap items-center gap-3 mb-10"
          >
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground bg-white/5 dark:bg-white/5 px-3 py-1.5 rounded-full border border-border/50 shadow-sm">
              <CheckCircle2 size={14} className="text-primary-500"/> Append-friendly indexing
            </div>
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground bg-white/5 dark:bg-white/5 px-3 py-1.5 rounded-full border border-border/50 shadow-sm">
              <CheckCircle2 size={14} className="text-primary-500"/> Source-backed reasoning
            </div>
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground bg-white/5 dark:bg-white/5 px-3 py-1.5 rounded-full border border-border/50 shadow-sm">
              <CheckCircle2 size={14} className="text-primary-500"/> Inline cited lines
            </div>
          </motion.div>
        </div>

        {/* Right Side: Demo Window */}
        <motion.div
          initial={{ opacity: 0, x: 20, scale: 0.95 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ delay: 0.4, duration: 0.8, ease: "easeOut" }}
          className="w-full relative"
        >
          <div className="liquid-glass rounded-[2rem] p-2 shadow-[0_0_80px_rgba(16,185,129,0.15)] border border-white/10 dark:border-white/5 overflow-hidden backdrop-blur-3xl">
            {/* Fake Mac titlebar */}
            <div className="flex items-center justify-between px-4 py-3 bg-white/5 border-b border-white/5">
               <div className="flex items-center gap-1.5">
                 <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                 <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                 <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
               </div>
               <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary-500 animate-pulse"></span>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-primary-500">Live Retrieval</span>
               </div>
            </div>

            <div className="bg-background/60 dark:bg-background/40 p-4 md:p-6 flex flex-col gap-6 min-h-[380px]">
              {/* Query */}
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center shrink-0 mt-1">
                  <Search size={16} className="text-primary-500" />
                </div>
                <div className="flex-1 bg-white/50 dark:bg-black/40 rounded-2xl rounded-tl-none p-4 shadow-sm border border-border/50">
                  <p className="text-sm font-medium text-foreground">Based on my wife's personality, what gift should I get?</p>
                </div>
              </div>

              {/* Pipeline Status */}
              <AnimatePresence mode="wait">
                {demoStep >= 1 && demoStep < 7 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="flex flex-wrap items-center gap-2 pl-12"
                  >
                    <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-background/50 px-2 py-1 rounded-md border border-border/50 shadow-sm">
                      <Database size={12} /> {demoStep >= 2 ? 'Lexical & Vector Found' : 'Searching Vectors...'}
                    </div>
                    {demoStep >= 2 && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-background/50 px-2 py-1 rounded-md border border-border/50 shadow-sm"
                      >
                        <Network size={12} /> {demoStep >= 3 ? 'Recall Links Traced' : 'Traversing Recall Graph...'}
                      </motion.div>
                    )}
                    {demoStep >= 3 && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-background/50 px-2 py-1 rounded-md border border-border/50 shadow-sm"
                      >
                        <Archive size={12} /> {demoStep >= 4 ? 'Context Compacted' : 'Compacting Context...'}
                      </motion.div>
                    )}
                    {demoStep >= 4 && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-background/50 px-2 py-1 rounded-md border border-border/50 shadow-sm"
                      >
                        <Zap size={12} /> {demoStep >= 5 ? 'Match Cached' : 'Caching Semantic Match...'}
                      </motion.div>
                    )}
                    {demoStep >= 5 && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-background/50 px-2 py-1 rounded-md border border-border/50 shadow-sm"
                      >
                        <Brain size={12} className="text-primary-500 animate-pulse" /> Synthesizing Answer...
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Answer */}
              <AnimatePresence>
                {demoStep >= 6 && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-4"
                  >
                    <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center shrink-0 mt-1">
                      <Bot size={16} className="text-primary-500" />
                    </div>
                    <div className="flex-1 bg-gradient-to-br from-white/60 to-white/30 dark:from-white/10 dark:to-white/5 rounded-2xl rounded-tl-none p-4 shadow-sm border border-border/50">
                      <div className="flex items-center gap-2 mb-3">
                         <span className="text-[10px] font-bold uppercase tracking-widest text-primary-500 bg-primary-500/10 px-2 py-0.5 rounded-sm">Grounded</span>
                      </div>
                      <p className="text-sm font-medium text-foreground leading-relaxed mb-3">
                        She has mentioned better coffee gear three times, and your notes say she likes practical gifts with a ritual around them. Best bet: a burr grinder plus a small tasting set.
                      </p>
                      <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-border/50">
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-primary-600 dark:text-primary-400 bg-primary-500/10 px-2 py-1 rounded border border-primary-500/20 cursor-pointer hover:bg-primary-500/20 transition-colors shadow-sm">
                          <Quote size={10} /> wife_preferences.md (Lines 12-18)
                        </span>
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-primary-600 dark:text-primary-400 bg-primary-500/10 px-2 py-1 rounded border border-primary-500/20 cursor-pointer hover:bg-primary-500/20 transition-colors shadow-sm">
                          <Quote size={10} /> coffee_shop_chat.txt
                        </span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Deep Engineering Section */}
      <div className="w-full max-w-7xl px-4 mt-24 z-10 mb-20 flex flex-col gap-24">
        
        {/* Durability Split */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center"
        >
          {/* Graphic Side */}
          <div className="order-2 md:order-1 liquid-glass rounded-2xl p-0 border border-border/50 shadow-sm relative overflow-hidden flex flex-col h-[320px]">
             {/* Terminal Header */}
             <div className="bg-background/80 px-4 py-3 border-b border-white/5 flex items-center justify-between z-10">
               <div className="flex items-center gap-2">
                 <Database size={14} className="text-violet-500" />
                 <span className="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-wider">Worker Node 1</span>
               </div>
               <div className="flex items-center gap-2">
                 <span className="text-[10px] font-mono text-muted-foreground">sys.log</span>
                 <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>
               </div>
             </div>
             
             {/* Terminal Body Split */}
             <div className="flex-1 flex w-full relative z-0">
               {/* Left: Logs */}
               <div className="flex-1 p-4 font-mono text-[10px] sm:text-xs flex flex-col gap-3 border-r border-white/5 relative overflow-hidden bg-black/60 dark:bg-black/40">
                 <div className="text-emerald-400/50">[10:42:01] INFO  Starting Job queue...</div>
                 <div className="text-emerald-400/70">[10:42:02] SQL   Outbox {'>'} IngestTask</div>
                 <div className="text-blue-400/90">[10:42:02] REDIS Dispatching to Worker-1</div>
                 
                 <AnimatePresence>
                   {demoStep >= 2 && (
                     <motion.div initial={{opacity:0, x:-10}} animate={{opacity:1, x:0}} className="text-emerald-400">
                       [10:42:03] GRAPH Checkpoint saved: <span className="text-white font-bold bg-white/10 px-1 rounded">source_chunks</span>
                     </motion.div>
                   )}
                   {demoStep >= 5 && (
                     <motion.div initial={{opacity:0, x:-10}} animate={{opacity:1, x:0}} className="text-red-400 bg-red-500/20 px-2 py-0.5 -mx-2 rounded font-bold border-l-2 border-red-500">
                       [10:42:04] ERROR API Timeout: LLM unreachable
                     </motion.div>
                   )}
                   {demoStep >= 7 && (
                     <motion.div initial={{opacity:0, x:-10}} animate={{opacity:1, x:0}} className="text-violet-400 mt-2">
                       [10:42:05] SYSTEM Resuming from checkpoint...
                     </motion.div>
                   )}
                 </AnimatePresence>
               </div>
               
               {/* Right: State Inspector */}
               <div className="w-[140px] md:w-[180px] bg-background/40 p-4 font-mono text-[10px] flex flex-col gap-4 relative">
                 <div className="text-muted-foreground uppercase tracking-widest border-b border-white/5 pb-2 font-bold">State</div>
                 
                 <div className="flex flex-col gap-1.5">
                   <span className="text-foreground/40">status:</span>
                   {demoStep < 5 ? (
                     <span className="text-emerald-400 font-bold bg-emerald-500/10 w-fit px-1.5 rounded">running</span>
                   ) : demoStep < 7 ? (
                     <span className="text-red-400 font-bold bg-red-500/10 w-fit px-1.5 rounded animate-pulse">suspended</span>
                   ) : (
                     <span className="text-violet-400 font-bold bg-violet-500/10 w-fit px-1.5 rounded">resuming</span>
                   )}
                 </div>
                 
                 <div className="flex flex-col gap-1.5">
                   <span className="text-foreground/40">checkpoint:</span>
                   <AnimatePresence mode="wait">
                     <motion.div
                       key={demoStep < 2 ? "none" : "source"}
                       initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                       className="text-emerald-300"
                     >
                       {demoStep < 2 ? "{}" : "{ chunks: [...] }"}
                     </motion.div>
                   </AnimatePresence>
                 </div>
                 
                 <AnimatePresence>
                   {demoStep >= 5 && demoStep < 7 && (
                     <motion.div
                       initial={{ scale: 0.8, opacity: 0, y: 10 }}
                       animate={{ scale: 1, opacity: 1, y: 0 }}
                       exit={{ scale: 0.8, opacity: 0, y: 10 }}
                       className="absolute bottom-4 right-4 left-4 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 px-3 py-2 rounded flex items-center justify-center gap-2 backdrop-blur-md font-bold shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                     >
                       <Lock size={14} /> Data Safe
                     </motion.div>
                   )}
                 </AnimatePresence>
               </div>
             </div>
          </div>
          {/* Text Side */}
          <div className="order-1 md:order-2 flex flex-col items-start text-left">
            <div className="flex items-center gap-2 text-violet-500 mb-3">
              <Database size={18} />
              <span className="text-xs font-bold uppercase tracking-widest">Durable Execution</span>
            </div>
            <h3 className="text-3xl font-bold tracking-tight text-foreground mb-4">Jobs pause. They never fail.</h3>
            <p className="text-base font-medium text-muted-foreground leading-relaxed">
              We wrap database inserts and event emissions in an atomic SQLite <strong>Transactional Outbox</strong>. Background jobs are dispatched via <strong>Redis Streams</strong> with strict idempotency checks and deterministic <strong>LangGraph</strong> checkpoints. If an API times out mid-job, it resumes exactly where it left off.
            </p>
          </div>
        </motion.div>

        {/* Caching Split */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center"
        >
          {/* Text Side */}
          <div className="flex flex-col items-start text-left">
            <div className="flex items-center gap-2 text-emerald-500 mb-3">
              <Zap size={18} />
              <span className="text-xs font-bold uppercase tracking-widest">LLM-Verified Caching</span>
            </div>
            <h3 className="text-3xl font-bold tracking-tight text-foreground mb-4">Skip the expensive steps.</h3>
            <p className="text-base font-medium text-muted-foreground leading-relaxed">
              Full synthesis requires massive context windows for retrieval, graph traversal, and compaction. By utilizing Semantic Vector Caches, we can bypass these entirely. A tiny 12-token <strong>LLM Verifier</strong> confirms intent alignment and instantly returns the cached answer, saving you thousands of tokens per query.
            </p>
          </div>
          {/* Graphic Side */}
          <div className="liquid-glass rounded-2xl p-6 border border-border/50 shadow-sm relative overflow-hidden flex items-center justify-center min-h-[420px]">
             
             {/* Flowchart Container */}
             <div className="relative w-full max-w-sm h-[360px]">
                
                {/* SVG Connecting Lines */}
                <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {/* Query to Lookup */}
                  <path d="M 50 10 L 50 25" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
                  
                  {/* Lookup to Miss (Left) */}
                  <path d="M 50 35 C 50 45, 20 45, 20 60" fill="none" stroke="rgba(239,68,68,0.2)" strokeWidth="0.5" strokeDasharray="1,1" />
                  
                  {/* Lookup to Match (Right) */}
                  <path d="M 50 35 C 50 45, 80 45, 80 60" fill="none" stroke="rgba(16,185,129,0.3)" strokeWidth="0.5" />
                  
                  {/* Miss to Response */}
                  <path d="M 20 70 C 20 85, 50 85, 50 95" fill="none" stroke="rgba(239,68,68,0.2)" strokeWidth="0.5" strokeDasharray="1,1" />
                  
                  {/* Match to Response */}
                  <path d="M 80 70 C 80 85, 50 85, 50 95" fill="none" stroke="rgba(16,185,129,0.3)" strokeWidth="0.5" />
                </svg>

                {/* Animated Data Packet along the Match Path */}
                <motion.div 
                  className="absolute w-3 h-3 bg-emerald-500 rounded-full shadow-[0_0_15px_rgba(16,185,129,1)] z-10 -ml-1.5 -mt-1.5"
                  animate={{
                    left: ["50%", "50%", "80%", "50%"],
                    top: ["10%", "25%", "60%", "95%"],
                    opacity: [0, 1, 1, 0]
                  }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear", times: [0, 0.2, 0.6, 1] }}
                />

                {/* Nodes */}
                
                {/* 1. Incoming Query */}
                <div className="absolute top-[10%] left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                  <div className="bg-background/90 border border-white/10 px-3 py-1.5 rounded-lg text-[10px] font-bold text-foreground shadow-lg flex items-center gap-1.5 whitespace-nowrap">
                    Incoming Query
                  </div>
                </div>

                {/* 2. Cache Lookup */}
                <div className="absolute top-[25%] left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                  <div className="bg-background/90 border border-primary-500/30 px-3 py-1.5 rounded-lg text-[10px] font-bold text-primary-500 shadow-lg flex flex-col items-center">
                    <Search size={12} className="mb-0.5" />
                    Cache Lookup
                  </div>
                </div>

                {/* 3. Miss (Left) */}
                <div className="absolute top-[60%] left-[20%] -translate-x-1/2 -translate-y-1/2 z-20 opacity-40">
                  <div className="bg-background/90 border border-red-500/30 p-2 rounded-lg text-center shadow-lg w-[120px]">
                    <div className="text-[8px] font-bold text-red-500 uppercase tracking-widest mb-1">Miss</div>
                    <div className="text-[9px] text-foreground font-bold uppercase mb-1.5">Full Synthesis</div>
                    <div className="flex flex-col gap-1 mb-2 text-[7.5px] md:text-[8px] font-mono text-left bg-black/40 p-1.5 rounded border border-white/5">
                      <div className="flex items-center gap-1 text-red-300/80"><span className="text-red-500 font-bold">1.</span> Vector Retrieve</div>
                      <div className="flex items-center gap-1 text-red-300/80"><span className="text-red-500 font-bold">2.</span> Graph Traversal</div>
                      <div className="flex items-center gap-1 text-red-300/80"><span className="text-red-500 font-bold">3.</span> Context Compact</div>
                      <div className="flex items-center gap-1 text-red-300/80"><span className="text-red-500 font-bold">4.</span> LLM Generation</div>
                    </div>
                    <div className="text-[8px] font-bold text-red-400 bg-red-500/10 rounded py-0.5 border border-red-500/20">Cost: 5,000+ tkns</div>
                  </div>
                </div>

                {/* 4. Match (Right) */}
                <div className="absolute top-[60%] left-[80%] -translate-x-1/2 -translate-y-1/2 z-20">
                  <div className="bg-background/90 border border-emerald-500/30 p-2 rounded-lg text-center shadow-lg w-[110px]">
                    <div className="text-[8px] font-bold text-emerald-500 uppercase tracking-widest mb-1">Match</div>
                    <div className="text-[9px] text-foreground font-bold uppercase">LLM Verifier</div>
                    <div className="text-[8px] text-emerald-400 font-mono mt-1 bg-emerald-500/10 px-1 rounded inline-block">12 tkns</div>
                  </div>
                </div>

                {/* 5. Cache Hit / Response */}
                <div className="absolute top-[95%] left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                  <div className="bg-emerald-500/10 border border-emerald-500/50 px-4 py-2 rounded-lg text-center shadow-[0_0_20px_rgba(16,185,129,0.15)] flex flex-col items-center">
                    <div className="text-[9px] font-bold text-emerald-500 uppercase tracking-widest mb-1 flex items-center gap-1"><Zap size={10}/> Cache Hit</div>
                    <div className="text-[10px] text-emerald-400 font-bold uppercase">Instant Response</div>
                  </div>
                </div>

             </div>
          </div>
        </motion.div>
      </div>

      {/* User Facing Features Grid */}
      <div className="w-full max-w-7xl px-4 mb-32 z-10">
        <div className="mb-12">
          <p className="text-sm font-bold uppercase tracking-widest text-primary-500 mb-2 text-center">Built In</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4 text-center">Everything you need.</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {USER_FEATURES.map((feature, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              className="liquid-glass p-6 md:p-8 rounded-[2rem] flex flex-col gap-4 border border-border/50 hover:border-border/80 transition-colors shadow-lg"
            >
              <div className="w-12 h-12 rounded-2xl bg-primary-500/10 flex items-center justify-center text-primary-500 mb-2">
                <feature.icon size={24} />
              </div>
              <h3 className="text-lg font-bold tracking-tight text-foreground">{feature.title}</h3>
              <p className="text-sm font-medium text-muted-foreground leading-relaxed">
                {feature.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
