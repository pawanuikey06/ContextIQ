<script>
    import { push } from "svelte-spa-router";
    import {
        Upload,
        MessageSquare,
        Target,
        Zap,
        BarChart3,
        ArrowRight,
        Mic,
        FileText,
        CheckCircle2,
        Database,
        Brain,
        Cpu,
        Layers,
        Mail,
        FileDown,
        Users,
    } from "lucide-svelte";
    import Logo from "../components/Logo.svelte";
</script>

<div class="min-h-screen overflow-hidden">
    <!-- ═══════════════ HERO (Dark Green — Coactive style) ═══════════════ -->
    <section
        class="relative bg-gradient-to-br from-[#052e1c] via-[#064a2a] to-[#053622] overflow-hidden"
    >
        <!-- Decorative green swoosh -->
        <div class="absolute inset-0 pointer-events-none">
            <div
                class="absolute bottom-0 right-0 w-[55%] h-full bg-gradient-to-tl from-emerald-600/20 via-transparent to-transparent rounded-tl-[120px]"
            ></div>
            <div
                class="absolute top-0 right-[30%] w-[300px] h-[300px] bg-emerald-500/10 rounded-full blur-[80px]"
            ></div>
            <div
                class="absolute bottom-0 right-[10%] w-[250px] h-[250px] bg-teal-500/10 rounded-full blur-[60px]"
            ></div>
        </div>

        <div class="relative max-w-5xl mx-auto px-6 py-20 lg:py-28">
            <div class="grid lg:grid-cols-2 gap-12 items-center">
                <!-- Left: Text -->
                <div>
                    <h1
                        class="text-4xl lg:text-[3.25rem] font-extrabold leading-[1.1] mb-6 tracking-tight"
                    >
                        <span
                            class="bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent"
                            >ContextIQ</span
                        >
                        <br />
                        <span class="text-white">Meeting Intelligence</span>
                        <br />
                        <span class="text-white">Platform</span>
                    </h1>

                    <p
                        class="text-gray-300 text-[17px] leading-relaxed mb-8 max-w-md"
                    >
                        A full-stack platform for meeting intelligence —
                        purpose-built for transcription, summarization, and
                        actionable insights at scale.
                    </p>

                    <div class="flex flex-wrap gap-3">
                        <a
                            href="#/meetings"
                            class="bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-semibold px-7 py-3.5 rounded-xl transition-all flex items-center gap-2.5 shadow-lg shadow-emerald-500/20 no-underline text-[15px] hover:-translate-y-0.5"
                        >
                            <Upload size={17} /> Upload Meeting
                        </a>
                        <a
                            href="#/chat"
                            class="bg-white/10 hover:bg-white/15 text-white font-semibold px-7 py-3.5 rounded-xl transition-all flex items-center gap-2.5 border border-white/15 no-underline text-[15px] hover:-translate-y-0.5 backdrop-blur-sm"
                        >
                            <MessageSquare size={17} /> AI Chat
                        </a>
                    </div>
                </div>

                <!-- Right: Platform Diagram -->
                <div class="hidden lg:block">
                    <div
                        class="bg-white/[0.06] backdrop-blur-md border border-white/10 rounded-2xl p-6 shadow-2xl"
                    >
                        <!-- Pipeline diagram -->
                        <div class="space-y-3">
                            <!-- Top: Apps row -->
                            <div class="flex gap-2 mb-2">
                                <div
                                    class="bg-emerald-500/20 border border-emerald-500/30 rounded-lg px-3 py-1.5 flex items-center gap-1.5"
                                >
                                    <Logo
                                        size={12}
                                        className="text-emerald-400"
                                    />
                                    <span
                                        class="text-[10px] font-bold text-emerald-300 uppercase tracking-wider"
                                        >ContextIQ Platform</span
                                    >
                                </div>
                                <div
                                    class="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 flex items-center gap-1.5"
                                >
                                    <span
                                        class="text-[10px] font-medium text-gray-400 uppercase tracking-wider"
                                        >Your Meetings</span
                                    >
                                </div>
                            </div>

                            <!-- Main platform box -->
                            <div
                                class="bg-emerald-900/30 border border-emerald-500/20 rounded-xl p-4 space-y-2.5"
                            >
                                <div class="flex items-center gap-2 mb-1">
                                    <Logo
                                        size={14}
                                        className="text-emerald-400"
                                    />
                                    <span
                                        class="text-[10px] font-bold text-emerald-300 uppercase tracking-wider"
                                        >Meeting Intelligence Pipeline</span
                                    >
                                </div>

                                <!-- Internal blocks -->
                                <div class="grid grid-cols-2 gap-2">
                                    <div
                                        class="bg-white/5 rounded-lg px-3 py-2 border border-white/5"
                                    >
                                        <span
                                            class="text-[9px] font-bold text-emerald-400 uppercase tracking-wider"
                                            >Transcription</span
                                        >
                                        <p
                                            class="text-[9px] text-gray-400 mt-0.5"
                                        >
                                            WhisperX + Diarization
                                        </p>
                                    </div>
                                    <div
                                        class="bg-white/5 rounded-lg px-3 py-2 border border-white/5"
                                    >
                                        <span
                                            class="text-[9px] font-bold text-blue-400 uppercase tracking-wider"
                                            >Summarization</span
                                        >
                                        <p
                                            class="text-[9px] text-gray-400 mt-0.5"
                                        >
                                            Bilingual AI summaries
                                        </p>
                                    </div>
                                    <div
                                        class="bg-white/5 rounded-lg px-3 py-2 border border-white/5"
                                    >
                                        <span
                                            class="text-[9px] font-bold text-violet-400 uppercase tracking-wider"
                                            >RAG Chat</span
                                        >
                                        <p
                                            class="text-[9px] text-gray-400 mt-0.5"
                                        >
                                            Cross-meeting Q&A
                                        </p>
                                    </div>
                                    <div
                                        class="bg-white/5 rounded-lg px-3 py-2 border border-white/5"
                                    >
                                        <span
                                            class="text-[9px] font-bold text-amber-400 uppercase tracking-wider"
                                            >Action Items</span
                                        >
                                        <p
                                            class="text-[9px] text-gray-400 mt-0.5"
                                        >
                                            Tasks, decisions, follow-ups
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <!-- Bottom: Foundation row -->
                            <div class="flex gap-2">
                                <div
                                    class="bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex-1"
                                >
                                    <span
                                        class="text-[9px] font-bold text-gray-400 uppercase tracking-wider"
                                        >Foundation Models</span
                                    >
                                </div>
                                <div
                                    class="bg-white/5 border border-white/10 rounded-lg px-3 py-2 flex items-center gap-2"
                                >
                                    <span
                                        class="text-[10px] font-semibold text-gray-300"
                                        >Groq</span
                                    >
                                    <span class="text-[9px] text-gray-500"
                                        >·</span
                                    >
                                    <span
                                        class="text-[10px] font-semibold text-gray-300"
                                        >Llama 3.3</span
                                    >
                                    <span class="text-[9px] text-gray-500"
                                        >·</span
                                    >
                                    <span
                                        class="text-[10px] font-semibold text-gray-300"
                                        >ChromaDB</span
                                    >
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- ═══════════════ CORE CAPABILITIES ═══════════════ -->
    <section class="relative bg-white">
        <div
            class="absolute -left-14 top-20 w-[200px] h-[280px] bg-emerald-400 rounded-[50px] rotate-[25deg] opacity-[0.05] pointer-events-none"
        ></div>

        <div class="max-w-5xl mx-auto px-6 py-24">
            <div class="text-center mb-16">
                <p
                    class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-3"
                >
                    Core Capabilities
                </p>
                <h2
                    class="text-3xl md:text-[2.5rem] font-extrabold text-gray-900 leading-tight mb-4"
                >
                    Everything you need for<br />meeting intelligence
                </h2>
                <p class="text-gray-500 max-w-xl mx-auto text-[15px]">
                    From raw video to structured insights — our AI pipeline
                    handles the heavy lifting.
                </p>
            </div>

            <div class="grid md:grid-cols-3 gap-6">
                <a
                    href="#/meetings"
                    class="group rounded-2xl p-8 transition-all no-underline block bg-gradient-to-br from-emerald-50/70 to-teal-50/50 border border-emerald-100/60 hover:shadow-xl hover:shadow-emerald-100/30 hover:-translate-y-1"
                >
                    <div
                        class="w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-6 shadow-sm border border-emerald-100/50 group-hover:scale-110 transition-transform"
                    >
                        <Mic size={22} class="text-emerald-600" />
                    </div>
                    <h3 class="font-bold text-gray-900 text-lg mb-2">
                        Transcription & Diarization
                    </h3>
                    <p class="text-sm text-gray-500 leading-relaxed mb-4">
                        WhisperX-powered transcription with accurate speaker
                        identification and time-aligned segments.
                    </p>
                    <span
                        class="text-emerald-600 text-sm font-semibold flex items-center gap-1 group-hover:gap-2 transition-all"
                    >
                        Explore <ArrowRight size={14} />
                    </span>
                </a>

                <a
                    href="#/chat"
                    class="group rounded-2xl p-8 transition-all no-underline block bg-gradient-to-br from-blue-50/70 to-indigo-50/50 border border-blue-100/60 hover:shadow-xl hover:shadow-blue-100/30 hover:-translate-y-1"
                >
                    <div
                        class="w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-6 shadow-sm border border-blue-100/50 group-hover:scale-110 transition-transform"
                    >
                        <MessageSquare size={22} class="text-blue-600" />
                    </div>
                    <h3 class="font-bold text-gray-900 text-lg mb-2">
                        AI Meeting Chat
                    </h3>
                    <p class="text-sm text-gray-500 leading-relaxed mb-4">
                        RAG-powered Q&A across all meetings with streaming
                        responses and source citations.
                    </p>
                    <span
                        class="text-blue-600 text-sm font-semibold flex items-center gap-1 group-hover:gap-2 transition-all"
                    >
                        Explore <ArrowRight size={14} />
                    </span>
                </a>

                <a
                    href="#/actions"
                    class="group rounded-2xl p-8 transition-all no-underline block bg-gradient-to-br from-violet-50/70 to-purple-50/50 border border-violet-100/60 hover:shadow-xl hover:shadow-violet-100/30 hover:-translate-y-1"
                >
                    <div
                        class="w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-6 shadow-sm border border-violet-100/50 group-hover:scale-110 transition-transform"
                    >
                        <Target size={22} class="text-violet-600" />
                    </div>
                    <h3 class="font-bold text-gray-900 text-lg mb-2">
                        Action Items & Tracking
                    </h3>
                    <p class="text-sm text-gray-500 leading-relaxed mb-4">
                        AI extracts tasks, decisions, and follow-ups with
                        priority tracking.
                    </p>
                    <span
                        class="text-violet-600 text-sm font-semibold flex items-center gap-1 group-hover:gap-2 transition-all"
                    >
                        Explore <ArrowRight size={14} />
                    </span>
                </a>

                <!-- New: Sentiment Analysis -->
                <a
                    href="#/meetings"
                    class="group rounded-2xl p-8 transition-all no-underline block bg-gradient-to-br from-pink-50/70 to-rose-50/50 border border-pink-100/60 hover:shadow-xl hover:shadow-pink-100/30 hover:-translate-y-1"
                >
                    <div
                        class="w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-6 shadow-sm border border-pink-100/50 group-hover:scale-110 transition-transform"
                    >
                        <BarChart3 size={22} class="text-pink-600" />
                    </div>
                    <h3 class="font-bold text-gray-900 text-lg mb-2">
                        Sentiment Analysis
                    </h3>
                    <p class="text-sm text-gray-500 leading-relaxed mb-4">
                        LLM-powered sentiment scoring per segment — mood
                        timeline, emotion labels, and highlight detection.
                    </p>
                    <span
                        class="text-pink-600 text-sm font-semibold flex items-center gap-1 group-hover:gap-2 transition-all"
                    >
                        Explore <ArrowRight size={14} />
                    </span>
                </a>

                <!-- New: Meeting Search -->
                <a
                    href="#/search"
                    class="group rounded-2xl p-8 transition-all no-underline block bg-gradient-to-br from-sky-50/70 to-cyan-50/50 border border-sky-100/60 hover:shadow-xl hover:shadow-sky-100/30 hover:-translate-y-1"
                >
                    <div
                        class="w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-6 shadow-sm border border-sky-100/50 group-hover:scale-110 transition-transform"
                    >
                        <Zap size={22} class="text-sky-600" />
                    </div>
                    <h3 class="font-bold text-gray-900 text-lg mb-2">
                        Instant Search
                    </h3>
                    <p class="text-sm text-gray-500 leading-relaxed mb-4">
                        Keyword search across all meeting transcripts, titles,
                        and speakers with ranked contextual snippets.
                    </p>
                    <span
                        class="text-sky-600 text-sm font-semibold flex items-center gap-1 group-hover:gap-2 transition-all"
                    >
                        Search <ArrowRight size={14} />
                    </span>
                </a>

                <!-- Jira Integration -->
                <a
                    href="#/actions"
                    class="group rounded-2xl p-8 transition-all no-underline block bg-gradient-to-br from-amber-50/70 to-orange-50/50 border border-amber-100/60 hover:shadow-xl hover:shadow-amber-100/30 hover:-translate-y-1"
                >
                    <div
                        class="w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-6 shadow-sm border border-amber-100/50 group-hover:scale-110 transition-transform"
                    >
                        <Target size={22} class="text-amber-600" />
                    </div>
                    <h3 class="font-bold text-gray-900 text-lg mb-2">
                        Jira Integration
                    </h3>
                    <p class="text-sm text-gray-500 leading-relaxed mb-4">
                        Push action items to Jira as tickets with bi-directional
                        sync for status, priority, and assignee updates.
                    </p>
                    <span
                        class="text-amber-600 text-sm font-semibold flex items-center gap-1 group-hover:gap-2 transition-all"
                    >
                        Manage <ArrowRight size={14} />
                    </span>
                </a>
            </div>
        </div>
    </section>

    <!-- ═══════════════ PLATFORM ═══════════════ -->
    <section class="relative bg-gray-50/50 border-y border-gray-100">
        <div
            class="absolute -right-10 bottom-16 w-[180px] h-[240px] bg-emerald-400 rounded-[40px] -rotate-[12deg] opacity-[0.04] pointer-events-none"
        ></div>

        <div class="max-w-5xl mx-auto px-6 py-24">
            <div class="grid md:grid-cols-2 gap-16 items-center">
                <div>
                    <p
                        class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-3"
                    >
                        Platform
                    </p>
                    <h2
                        class="text-3xl font-extrabold text-gray-900 mb-6 leading-tight"
                    >
                        Intelligent Meeting
                        <span
                            class="bg-gradient-to-r from-emerald-500 to-teal-500 bg-clip-text text-transparent"
                            >Pipeline</span
                        >
                    </h2>

                    <div class="space-y-6">
                        {#each [{ title: "Automated Ingestion", desc: "Upload video files and our pipeline automatically extracts audio, transcribes with WhisperX, and identifies speakers." }, { title: "Context-Aware Analysis", desc: "Bilingual summaries (English + Hindi), speaker-wise breakdowns, with human-in-the-loop approval before publishing." }, { title: "Cross-Meeting Intelligence", desc: "RAG-powered search across all meetings with diverse retrieval for comprehensive answers with source citations." }] as item}
                            <div class="flex gap-4">
                                <div
                                    class="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0 mt-0.5"
                                >
                                    <CheckCircle2
                                        size={14}
                                        class="text-emerald-600"
                                    />
                                </div>
                                <div>
                                    <h4
                                        class="font-bold text-gray-900 text-[15px] mb-1"
                                    >
                                        {item.title}
                                    </h4>
                                    <p
                                        class="text-sm text-gray-500 leading-relaxed"
                                    >
                                        {item.desc}
                                    </p>
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>

                <!-- Architecture Diagram -->
                <div
                    class="bg-white rounded-2xl border border-gray-200 shadow-lg p-7 relative overflow-hidden"
                >
                    <div
                        class="absolute -right-4 -top-4 w-20 h-28 bg-emerald-400 rounded-[20px] rotate-12 opacity-[0.06]"
                    ></div>
                    <div class="relative space-y-3">
                        <div
                            class="bg-emerald-50 rounded-xl px-5 py-3.5 border border-emerald-100"
                        >
                            <div class="flex items-center gap-2 mb-1">
                                <Upload size={13} class="text-emerald-600" />
                                <span
                                    class="text-[11px] font-bold text-emerald-800 uppercase tracking-wider"
                                    >Input</span
                                >
                            </div>
                            <p class="text-[11px] text-emerald-600/70">
                                Video upload → FFmpeg audio extraction
                            </p>
                        </div>
                        <div class="flex justify-center">
                            <svg
                                width="10"
                                height="14"
                                viewBox="0 0 10 14"
                                fill="none"
                                ><path
                                    d="M5 0v10M1.5 7L5 10.5 8.5 7"
                                    stroke="#d1d5db"
                                    stroke-width="1.5"
                                /></svg
                            >
                        </div>
                        <div
                            class="bg-blue-50 rounded-xl px-5 py-3.5 border border-blue-100"
                        >
                            <div class="flex items-center gap-2 mb-1">
                                <Mic size={13} class="text-blue-600" />
                                <span
                                    class="text-[11px] font-bold text-blue-800 uppercase tracking-wider"
                                    >Processing</span
                                >
                            </div>
                            <p class="text-[11px] text-blue-600/70">
                                WhisperX → Speaker diarization → Alignment
                            </p>
                        </div>
                        <div class="flex justify-center">
                            <svg
                                width="10"
                                height="14"
                                viewBox="0 0 10 14"
                                fill="none"
                                ><path
                                    d="M5 0v10M1.5 7L5 10.5 8.5 7"
                                    stroke="#d1d5db"
                                    stroke-width="1.5"
                                /></svg
                            >
                        </div>
                        <div class="grid grid-cols-2 gap-2.5">
                            <div
                                class="bg-violet-50 rounded-xl px-4 py-3 border border-violet-100"
                            >
                                <div class="flex items-center gap-1.5 mb-0.5">
                                    <Brain size={11} class="text-violet-600" />
                                    <span
                                        class="text-[10px] font-bold text-violet-800 uppercase tracking-wider"
                                        >LLM</span
                                    >
                                </div>
                                <p class="text-[10px] text-violet-600/70">
                                    Groq · Llama 3.3 70B
                                </p>
                            </div>
                            <div
                                class="bg-amber-50 rounded-xl px-4 py-3 border border-amber-100"
                            >
                                <div class="flex items-center gap-1.5 mb-0.5">
                                    <Database
                                        size={11}
                                        class="text-amber-600"
                                    />
                                    <span
                                        class="text-[10px] font-bold text-amber-800 uppercase tracking-wider"
                                        >Vector DB</span
                                    >
                                </div>
                                <p class="text-[10px] text-amber-600/70">
                                    ChromaDB · Embeddings
                                </p>
                            </div>
                        </div>
                        <div class="flex justify-center">
                            <svg
                                width="10"
                                height="14"
                                viewBox="0 0 10 14"
                                fill="none"
                                ><path
                                    d="M5 0v10M1.5 7L5 10.5 8.5 7"
                                    stroke="#d1d5db"
                                    stroke-width="1.5"
                                /></svg
                            >
                        </div>
                        <div
                            class="bg-gray-900 rounded-xl px-5 py-3.5 text-white"
                        >
                            <div class="flex items-center gap-2 mb-1.5">
                                <Zap size={13} class="text-emerald-400" />
                                <span
                                    class="text-[11px] font-bold uppercase tracking-wider"
                                    >Output</span
                                >
                            </div>
                            <div class="flex flex-wrap gap-1.5">
                                {#each ["Summaries", "Actions", "PDF", "Email", "RAG Chat"] as tag}
                                    <span
                                        class="text-[10px] bg-white/10 rounded-md px-2.5 py-0.5"
                                        >{tag}</span
                                    >
                                {/each}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- ═══════════════ HOW IT WORKS ═══════════════ -->
    <section class="bg-white max-w-5xl mx-auto px-6 py-24">
        <div class="text-center mb-16">
            <p
                class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-3"
            >
                Workflow
            </p>
            <h2 class="text-3xl font-extrabold text-gray-900 mb-3">
                How it works
            </h2>
            <p class="text-gray-500 max-w-lg mx-auto text-[15px]">
                Four steps from raw video to actionable intelligence.
            </p>
        </div>

        <div class="grid md:grid-cols-4 gap-8">
            {#each [{ step: "01", title: "Upload", desc: "Drop your meeting video — audio is extracted automatically.", Icon: Upload, bg: "bg-emerald-100", tc: "text-emerald-600" }, { step: "02", title: "Transcribe", desc: "WhisperX generates speaker-separated, timestamped transcripts.", Icon: Mic, bg: "bg-blue-100", tc: "text-blue-600" }, { step: "03", title: "Analyze", desc: "AI creates bilingual summaries, action items, and decisions.", Icon: BarChart3, bg: "bg-violet-100", tc: "text-violet-600" }, { step: "04", title: "Act", desc: "Publish via PDF, email, Teams. Push tasks to Jira.", Icon: Zap, bg: "bg-amber-100", tc: "text-amber-600" }] as item}
                <div class="text-center group">
                    <div
                        class="text-[2rem] font-black text-gray-100 mb-4 group-hover:text-emerald-100 transition-colors"
                    >
                        {item.step}
                    </div>
                    <div
                        class="w-14 h-14 rounded-2xl {item.bg} flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform shadow-sm"
                    >
                        <svelte:component
                            this={item.Icon}
                            size={22}
                            class={item.tc}
                        />
                    </div>
                    <h3 class="font-bold text-gray-900 mb-1.5">{item.title}</h3>
                    <p class="text-sm text-gray-500 leading-relaxed">
                        {item.desc}
                    </p>
                </div>
            {/each}
        </div>
    </section>

    <!-- ═══════════════ PUBLISH ═══════════════ -->
    <section class="relative bg-gray-50/50 border-y border-gray-100">
        <div class="max-w-5xl mx-auto px-6 py-24">
            <div class="text-center mb-14">
                <p
                    class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-3"
                >
                    Distribution
                </p>
                <h2 class="text-3xl font-extrabold text-gray-900 mb-3">
                    Publish anywhere
                </h2>
                <p class="text-gray-500 max-w-lg mx-auto text-[15px]">
                    Share insights through the channels your team already uses.
                </p>
            </div>

            <div class="grid md:grid-cols-4 gap-4">
                {#each [{ title: "PDF Export", desc: "Download formatted meeting reports", Icon: FileDown, bg: "bg-red-50", tc: "text-red-500" }, { title: "Email", desc: "Send follow-up emails with summaries", Icon: Mail, bg: "bg-blue-50", tc: "text-blue-500" }, { title: "Teams", desc: "Post directly to Microsoft Teams channels", Icon: Users, bg: "bg-violet-50", tc: "text-violet-500" }, { title: "Jira", desc: "Push action items as tasks to Jira", Icon: Target, bg: "bg-amber-50", tc: "text-amber-500" }] as item}
                    <div
                        class="bg-white rounded-2xl border border-gray-100 p-6 text-center hover:shadow-lg hover:-translate-y-0.5 transition-all"
                    >
                        <div
                            class="w-11 h-11 rounded-xl {item.bg} flex items-center justify-center mx-auto mb-4"
                        >
                            <svelte:component
                                this={item.Icon}
                                size={20}
                                class={item.tc}
                            />
                        </div>
                        <h4 class="font-bold text-gray-900 text-sm mb-1">
                            {item.title}
                        </h4>
                        <p class="text-xs text-gray-500">{item.desc}</p>
                    </div>
                {/each}
            </div>
        </div>
    </section>

    <!-- ═══════════════ CTA ═══════════════ -->
    <section class="bg-white">
        <div class="max-w-3xl mx-auto px-6 py-20 text-center">
            <h2 class="text-3xl font-extrabold text-gray-900 mb-4">
                Ready to unlock the potential<br />in your meetings?
            </h2>
            <p class="text-gray-500 mb-8 text-[15px]">
                Start transforming meeting recordings into actionable
                intelligence today.
            </p>
            <a
                href="#/meetings"
                class="inline-flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white font-semibold px-8 py-3.5 rounded-xl transition-all shadow-lg shadow-gray-900/10 no-underline text-[15px] hover:-translate-y-0.5"
            >
                Get Started <ArrowRight size={15} />
            </a>
        </div>
    </section>

    <!-- ═══════════════ FOOTER ═══════════════ -->
    <footer class="bg-white border-t border-gray-100 py-8">
        <div class="max-w-5xl mx-auto px-6 flex items-center justify-between">
            <div class="flex items-center gap-2">
                <Logo size={20} className="text-emerald-600" />
                <span class="font-bold text-gray-900 text-sm"
                    >Context<span class="text-emerald-600">IQ</span></span
                >
            </div>
            <p class="text-xs text-gray-400">
                AI-Powered Meeting Intelligence Platform
            </p>
        </div>
    </footer>
</div>
