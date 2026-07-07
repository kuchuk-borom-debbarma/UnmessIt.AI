import { motion } from 'framer-motion'
import { Radio, HeartPulse, Laptop, Server, Waves, Activity, Zap, ShieldCheck, Database, ArrowRight, ArrowDown } from 'lucide-react'

export function SSEView() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-[1200px] mx-auto space-y-32 pb-32"
    >
      <section id="sse" className="scroll-mt-32">
        <div className="mb-12 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm font-bold uppercase tracking-wider mb-4">
            <Radio size={14} /> SSE & Streaming
          </div>
          <h2 className="text-5xl font-bold tracking-tight mb-6 text-white">Scalable SSE Routing</h2>
          <p className="text-xl text-muted-foreground max-w-4xl mx-auto leading-relaxed">
            In a horizontally scaled environment with hundreds of API nodes, global Pub/Sub fanout is an O(N) bottleneck. Instead, we use Redis Sorted Sets to track exact client locations and achieve O(K) <strong>Targeted Instance Routing</strong>.
          </p>
        </div>

        {/* Narrative Section: The 3 Stages of Routing */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 mb-20">
           
           <div className="bg-white/5 border border-white/10 rounded-2xl p-6 shadow-xl relative overflow-hidden group hover:border-rose-500/30 transition-colors">
             <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Laptop size={100} />
             </div>
             <div className="w-12 h-12 bg-blue-500/20 border border-blue-500/30 rounded-xl flex items-center justify-center text-blue-400 mb-4">
                <HeartPulse size={20} />
             </div>
             <h3 className="text-lg font-bold text-white mb-2">1. Topic ZSET Tracking</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               When a client connects to a topic, the API server writes its <code>instance_id</code> into a Redis Sorted Set (ZSET) for that topic, using the current timestamp as the score for TTL expiration.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-2xl p-6 shadow-xl relative overflow-hidden group hover:border-rose-500/30 transition-colors">
             <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Server size={100} />
             </div>
             <div className="w-12 h-12 bg-purple-500/20 border border-purple-500/30 rounded-xl flex items-center justify-center text-purple-400 mb-4">
                <Radio size={20} />
             </div>
             <h3 className="text-lg font-bold text-white mb-2">2. Dedicated Listening</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               Unlike naive Pub/Sub where every node listens to a global wildcard, our API servers subscribe <strong>only</strong> to their own dedicated <code>instance_id</code> channel. This reduces network noise to zero for idle nodes.
             </p>
           </div>

           <div className="bg-white/5 border border-white/10 rounded-2xl p-6 shadow-xl relative overflow-hidden group hover:border-rose-500/30 transition-colors">
             <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Waves size={100} />
             </div>
             <div className="w-12 h-12 bg-rose-500/20 border border-rose-500/30 rounded-xl flex items-center justify-center text-rose-400 mb-4">
                <Zap size={20} />
             </div>
             <h3 className="text-lg font-bold text-white mb-2">3. Smart Routing</h3>
             <p className="text-sm text-muted-foreground leading-relaxed">
               When a background worker emits an event, it queries the ZSET to find exactly which instances have active clients. It then publishes the event strictly to those specific instance channels.
             </p>
           </div>
        </div>

        {/* Deep Dive Granular Timeline */}
        <div className="w-full bg-[#050505] rounded-3xl border border-white/10 p-8 overflow-x-auto shadow-2xl mt-12">
           <div className="min-w-[1000px] flex flex-col gap-6 font-mono text-xs">
              
              <div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/10">
                 <div className="bg-rose-500 text-white px-3 py-1 rounded font-bold shadow-[0_0_15px_rgba(244,63,94,0.3)]">Background Worker</div>
                 <ArrowDown className="-rotate-90 text-white/40" size={16} />
                 <div className="text-white">Needs to emit progress event for `topic: query_123`</div>
              </div>

              <div className="pl-12 flex flex-col gap-4 border-l-2 border-dashed border-white/20 ml-6 py-4">
                 
                 {/* ZSET Query */}
                 <div className="border border-purple-500/30 rounded-xl p-4 bg-purple-500/5">
                    <div className="text-purple-300 font-bold mb-4 flex items-center gap-2">
                      <Database size={14} /> 1. Query Topic ZSET
                    </div>
                    <div className="flex flex-col gap-3 pl-6 border-l border-purple-500/20">
                       <div className="flex items-center gap-4">
                          <span className="text-white font-bold bg-black/50 px-2 py-1 rounded border border-white/10">ZRANGEBYSCORE</span>
                          <ArrowDown className="-rotate-90 text-white/40" size={16} />
                          <span className="text-white">Fetch all active `instance_id`s with score &gt; (NOW - TTL)</span>
                       </div>
                       <div className="flex items-center gap-4 mt-2">
                          <span className="text-emerald-400 font-bold flex items-center gap-1"><ShieldCheck size={14}/> Returned</span>
                          <ArrowDown className="-rotate-90 text-white/40" size={16} />
                          <span className="text-white">["api-node-alpha", "api-node-delta"]</span>
                       </div>
                    </div>
                 </div>

                 {/* Targeted Publish */}
                 <div className="border border-blue-500/30 rounded-xl p-4 bg-blue-500/5 mt-4">
                    <div className="text-blue-300 font-bold mb-4 flex items-center gap-2">
                      <Waves size={14} /> 2. Targeted Instance Publishing
                    </div>
                    
                    <div className="flex flex-col gap-4 pl-6 border-l border-blue-500/20">
                       
                       <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-4">
                             <span className="bg-blue-500/20 border border-blue-500/40 text-blue-400 px-2 py-1 rounded text-[10px] font-bold">PUBLISH</span>
                             <span className="text-white font-bold">unmessit:sse:instance:api-node-alpha</span>
                          </div>
                          <div className="text-muted-foreground pl-2 border-l-2 border-white/10 ml-1 py-1 flex items-center gap-2">
                             <ArrowRight size={14} className="text-blue-400" />
                             Delivered to Node Alpha. Node Alpha forwards to local client.
                          </div>
                       </div>

                       <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-4">
                             <span className="bg-blue-500/20 border border-blue-500/40 text-blue-400 px-2 py-1 rounded text-[10px] font-bold">PUBLISH</span>
                             <span className="text-white font-bold">unmessit:sse:instance:api-node-delta</span>
                          </div>
                          <div className="text-muted-foreground pl-2 border-l-2 border-white/10 ml-1 py-1 flex items-center gap-2">
                             <ArrowRight size={14} className="text-blue-400" />
                             Delivered to Node Delta. Node Delta forwards to local client.
                          </div>
                       </div>

                       <div className="flex flex-col gap-2 opacity-50">
                          <div className="flex items-center gap-4">
                             <span className="bg-white/5 border border-white/10 text-white/40 px-2 py-1 rounded text-[10px] font-bold">IGNORED</span>
                             <span className="text-white font-bold">api-node-beta, api-node-gamma, etc.</span>
                          </div>
                          <div className="text-muted-foreground pl-2 border-l-2 border-white/10 ml-1 py-1">
                             Other 998 nodes receive zero network traffic for this event. O(K) scaling achieved.
                          </div>
                       </div>

                    </div>
                 </div>

              </div>
           </div>
        </div>

        {/* The Heartbeat TTL */}
        <div className="space-y-8 mt-24">
          <div>
            <h3 className="text-3xl font-bold text-white flex items-center gap-4 mb-6">
              <span className="w-10 h-10 rounded-full bg-rose-500/20 flex items-center justify-center text-rose-400 text-lg border border-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.2)]">4</span>
              The 30s ZSET Heartbeat
            </h3>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-4xl">
              Because SSE connections are process-local, if the user closes their laptop or the API server crashes, the connection dies without firing a clean disconnect event. We implement a Continuous Heartbeat to purge dead nodes from the ZSET.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div className="bg-white/5 border border-white/10 p-8 rounded-3xl shadow-xl hover:border-rose-500/30 transition-colors">
                <div className="flex items-center gap-3 mb-6">
                   <HeartPulse className="text-rose-400" size={28} />
                   <h4 className="text-xl font-bold text-white">Continuous ZADD</h4>
                </div>
                <p className="text-muted-foreground mb-6 text-sm leading-relaxed">
                   While the SSE stream is open, the API server runs an async background task that updates the ZSET score every 10 seconds:
                </p>
                <div className="bg-black/50 p-4 rounded-xl font-mono text-xs text-rose-200/70 border border-white/5 space-y-2 shadow-inner">
                   <div>ZADD unmessit:sse:topics:query_123</div>
                   <div>{"{ api-node-alpha: 1718294400 }"}</div>
                </div>
             </div>

             <div className="bg-white/5 border border-white/10 p-8 rounded-3xl shadow-xl hover:border-rose-500/30 transition-colors">
                <div className="flex items-center gap-3 mb-6">
                   <Activity className="text-rose-400" size={28} />
                   <h4 className="text-xl font-bold text-white">ZREMRANGEBYSCORE</h4>
                </div>
                <p className="text-muted-foreground mb-6 text-sm leading-relaxed">
                   When the publisher queries the ZSET, it first aggressively prunes any instances whose score (timestamp) is older than 30 seconds.
                </p>
                <div className="bg-black/50 p-4 rounded-xl font-mono text-xs text-rose-200/70 border border-white/5 space-y-2 shadow-inner">
                   <div>ZREMRANGEBYSCORE</div>
                   <div>unmessit:sse:topics:query_123</div>
                   <div>-inf (NOW - 30s)</div>
                </div>
             </div>
          </div>
        </div>

      </section>
    </motion.div>
  )
}
