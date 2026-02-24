<script>
    import { onMount } from "svelte";
    import { push } from "svelte-spa-router";
    import {
        ChevronLeft,
        Users,
        Clock,
        Loader2,
        Sparkles,
        Download,
        Mail,
        MessageSquare,
        RefreshCw,
        Check,
        Edit3,
        Play,
        Hash,
        ArrowUpRight,
        ClipboardList,
        FileText,
        BarChart3,
    } from "lucide-svelte";
    import { toasts } from "../lib/toast.js";
    import { api, get, post } from "../lib/api.js";
    import {
        meetingData,
        summaryData,
        speakerMap,
        summaryApproved,
    } from "../lib/stores.js";
    import {
        formatTime,
        formatDuration,
        SPEAKER_COLORS,
        shortId,
    } from "../lib/utils.js";

    export let params = {};

    let meetingId = "";
    let data = null;
    let segments = [];
    let speakers = {};
    let speakerList = [];
    let loading = true;
    let activeTab = null;
    let autoTitle = "";

    // Summary
    let summary = null;
    let generatingSummary = false;
    let editedEn = "";
    let editedHi = "";
    let approved = false;
    let rewritePrompt = "";
    let showRewriteBox = false;

    // Speaker mapping
    let smap = {};
    let renameInputs = {};
    let showSpeakerPanel = false;

    // Requirements (optional)
    let reqData = null;
    let extractingReqs = false;

    // Documentation (optional)
    let docData = null;
    let generatingDocs = false;

    // Sentiment (optional)
    let sentimentData = null;
    let analyzingSentiment = false;

    const tabs = [
        {
            id: "chat",
            label: "Chat View",
            icon: MessageSquare,
            color: "text-blue-600",
            bg: "bg-blue-50",
            border: "border-blue-100",
            desc: "Full conversation transcript with speaker-identified chat bubbles.",
        },
        {
            id: "speaker",
            label: "Speaker Analysis",
            icon: Users,
            color: "text-emerald-600",
            bg: "bg-emerald-50",
            border: "border-emerald-100",
            desc: "View contributions grouped by each participant with talk-time stats.",
        },
        {
            id: "timeline",
            label: "Timeline",
            icon: Clock,
            color: "text-amber-600",
            bg: "bg-amber-50",
            border: "border-amber-100",
            desc: "Chronological segment timeline with timestamps and speaker flow.",
        },
        {
            id: "summary",
            label: "AI Summary",
            icon: Sparkles,
            color: "text-purple-600",
            bg: "bg-purple-50",
            border: "border-purple-100",
            desc: "AI-generated meeting summary with approve, edit, and share options.",
        },
        {
            id: "requirements",
            label: "Requirements",
            icon: ClipboardList,
            color: "text-rose-600",
            bg: "bg-rose-50",
            border: "border-rose-100",
            desc: "Extract functional requirements, user stories, and constraints.",
        },
        {
            id: "docs",
            label: "Documentation",
            icon: FileText,
            color: "text-teal-600",
            bg: "bg-teal-50",
            border: "border-teal-100",
            desc: "Generate formal meeting minutes with decisions and next steps.",
        },
        {
            id: "sentiment",
            label: "Sentiment Analysis",
            icon: BarChart3,
            color: "text-pink-600",
            bg: "bg-pink-50",
            border: "border-pink-100",
            desc: "Analyze emotional tone and mood shifts throughout the meeting.",
        },
    ];

    onMount(async () => {
        meetingId = params.id;
        await loadMeeting();
    });

    async function loadMeeting() {
        loading = true;
        try {
            const stored = $meetingData;
            if (stored && stored.meeting_id === meetingId) {
                data = stored;
            } else {
                data = await get(api.meeting(meetingId));
                meetingData.set(data);
            }

            segments = data.segments || [];
            speakers = data.speakers || {};
            speakerList = Object.keys(speakers);

            try {
                const meta = await get(
                    `${api.base}/meeting/${meetingId}/metadata`,
                );
                autoTitle = meta.auto_title || meta.title || "";
            } catch {}

            try {
                const mapRes = await get(api.speakerMap(meetingId));
                smap = mapRes.speaker_map || {};
                speakerMap.set(smap);
            } catch {
                smap = {};
            }

            speakerList.forEach((s) => {
                renameInputs[s] = smap[s] || "";
            });

            if ($summaryData) {
                summary = $summaryData;
                editedEn = summary.overall_summary_en || "";
                editedHi = summary.overall_summary_hi || "";
                approved = $summaryApproved;
            }
        } catch (err) {
            console.error("Failed to load meeting:", err);
        }
        loading = false;
    }

    function displayName(spkId) {
        return smap[spkId] || spkId;
    }

    function getColor(spkId) {
        const idx = speakerList.indexOf(spkId);
        return SPEAKER_COLORS[idx >= 0 ? idx % 6 : 0];
    }

    async function applyNames() {
        const newMap = {};
        for (const [key, val] of Object.entries(renameInputs)) {
            if (val.trim()) newMap[key] = val.trim();
        }
        smap = newMap;
        speakerMap.set(smap);
        showSpeakerPanel = false;
        try {
            await post(api.speakerMap(meetingId), { speaker_map: newMap });
        } catch {}
    }

    async function resetNames() {
        smap = {};
        speakerMap.set({});
        renameInputs = {};
        speakerList.forEach((s) => {
            renameInputs[s] = "";
        });
        try {
            await post(api.speakerMap(meetingId), { speaker_map: {} });
        } catch {}
    }

    async function generateSummary(force = false) {
        generatingSummary = true;
        try {
            if (Object.keys(smap).length > 0) {
                await post(api.speakerMap(meetingId), { speaker_map: smap });
            }
            const shouldForce = force || !!rewritePrompt.trim();
            let url = shouldForce
                ? `${api.summarize(meetingId)}?force=true`
                : api.summarize(meetingId);
            if (rewritePrompt.trim()) {
                url += `&extra_prompt=${encodeURIComponent(rewritePrompt.trim())}`;
            }
            const res = await post(url, null, 300000);
            summary = res;
            summaryData.set(res);
            editedEn = res.overall_summary_en || "";
            editedHi = res.overall_summary_hi || "";
            approved = false;
            summaryApproved.set(false);
            // Close rewrite box & clear prompt after generation
            showRewriteBox = false;
            rewritePrompt = "";
        } catch (err) {
            toasts.error("Summary generation failed: " + err.message);
        }
        generatingSummary = false;
    }

    function approveSummary() {
        summary.overall_summary_en = editedEn;
        summary.overall_summary_hi = editedHi;
        summaryData.set(summary);
        approved = true;
        summaryApproved.set(true);
    }

    async function downloadPdf() {
        try {
            await post(api.publish(meetingId), {
                meeting_title: autoTitle || `Meeting ${shortId(meetingId)}`,
            });
            const res = await fetch(api.publishPdf(meetingId));
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "Meeting_Summary.pdf";
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            toasts.error("PDF download failed: " + err.message);
        }
    }

    async function sendEmail() {
        try {
            const res = await post(api.publish(meetingId), {
                meeting_title: autoTitle || `Meeting ${shortId(meetingId)}`,
                email_recipients: ["pawanuikey690@gmail.com"],
            });
            if (res.email?.success) {
                toasts.success("Email sent successfully!");
            } else {
                toasts.error(
                    "Email failed: " + (res.email?.message || "Unknown error"),
                );
            }
        } catch (err) {
            toasts.error("Email failed: " + err.message);
        }
    }

    async function sendToTeams() {
        try {
            const res = await post(api.publish(meetingId), {
                meeting_title: autoTitle || `Meeting ${shortId(meetingId)}`,
            });
            if (res.teams?.success) {
                toasts.success("Sent to Teams!");
            } else {
                toasts.error(
                    "Teams failed: " + (res.teams?.message || "Unknown error"),
                );
            }
        } catch (err) {
            toasts.error("Teams failed: " + err.message);
        }
    }

    async function extractRequirements(force = false) {
        extractingReqs = true;
        try {
            const url = force
                ? `${api.requirements(meetingId)}?force=true`
                : api.requirements(meetingId);
            reqData = await post(url, null, 120000);
            toasts.success("Requirements extracted!");
        } catch (err) {
            toasts.error("Requirements extraction failed: " + err.message);
        }
        extractingReqs = false;
    }

    async function generateDocumentation(force = false) {
        generatingDocs = true;
        try {
            const url = force
                ? `${api.documentation(meetingId)}?force=true`
                : api.documentation(meetingId);
            docData = await post(url, null, 120000);
            toasts.success("Documentation generated!");
        } catch (err) {
            toasts.error("Documentation generation failed: " + err.message);
        }
        generatingDocs = false;
    }

    async function analyzeSentiment(force = false) {
        analyzingSentiment = true;
        try {
            const url = force
                ? `${api.sentiment(meetingId)}?force=true`
                : api.sentiment(meetingId);
            sentimentData = await post(url, null, 120000);
            toasts.success("Sentiment analysis complete!");
        } catch (err) {
            toasts.error("Sentiment analysis failed: " + err.message);
        }
        analyzingSentiment = false;
    }

    function sentimentColor(sentiment) {
        const map = {
            positive: "#10b981",
            negative: "#ef4444",
            neutral: "#94a3b8",
        };
        return map[sentiment] || map.neutral;
    }

    function sentimentEmoji(sentiment) {
        const map = {
            positive: "😊",
            negative: "😟",
            neutral: "😐",
        };
        return map[sentiment] || "😐";
    }

    $: totalDur =
        segments.length > 0 ? Math.max(...segments.map((s) => s.end)) : 0;
</script>

<!-- ───────────────────────────────── LOADING ──────────────────────────── -->
{#if loading}
    <div class="flex flex-col items-center justify-center py-32 gap-3">
        <div
            class="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center"
        >
            <Loader2 size={20} class="text-brand-600 animate-spin" />
        </div>
        <span class="text-sm text-txt-muted">Loading meeting…</span>
    </div>
{:else if !data}
    <div class="max-w-md mx-auto px-6 py-24 text-center">
        <div
            class="w-14 h-14 mx-auto rounded-2xl bg-surface-100 flex items-center justify-center mb-4"
        >
            <Hash size={24} class="text-txt-faint" />
        </div>
        <h2 class="text-lg font-semibold text-txt-primary mb-1">
            Meeting not found
        </h2>
        <p class="text-sm text-txt-muted mb-6">
            This meeting ID doesn't exist or has been removed.
        </p>
        <a href="#/meetings" class="btn-primary text-sm no-underline"
            >← Back to Meetings</a
        >
    </div>
{:else}
    <!-- ─────────────────────── STICKY HEADER BAR ─────────────────────── -->
    <div
        class="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-surface-200/60"
    >
        <div class="max-w-6xl mx-auto px-6">
            <!-- Row 1: Breadcrumb + Actions -->
            <div class="flex items-center justify-between py-3">
                <a
                    href="#/meetings"
                    class="inline-flex items-center gap-1 text-xs text-txt-faint hover:text-brand-600 transition-colors no-underline"
                >
                    <ChevronLeft size={14} />
                    Meetings
                </a>

                <button
                    class="text-xs text-txt-faint hover:text-brand-600 transition-colors flex items-center gap-1.5"
                    on:click={() => (showSpeakerPanel = !showSpeakerPanel)}
                >
                    <Edit3 size={12} />
                    Rename
                </button>
            </div>

            <!-- Row 2: Title + Meta -->
            <div class="pb-3">
                <h1
                    class="text-lg font-semibold text-txt-primary leading-tight"
                >
                    {autoTitle || `Meeting ${shortId(meetingId)}`}
                </h1>
                <div class="flex items-center gap-3 mt-1.5">
                    <span
                        class="inline-flex items-center gap-1 text-[11px] text-txt-faint"
                    >
                        <Users size={11} />
                        {speakerList.length}
                    </span>
                    <span
                        class="inline-flex items-center gap-1 text-[11px] text-txt-faint"
                    >
                        <Hash size={11} />
                        {segments.length} segs
                    </span>
                    <span
                        class="inline-flex items-center gap-1 text-[11px] text-txt-faint"
                    >
                        <Clock size={11} />
                        {formatTime(totalDur)}
                    </span>
                    <span
                        class="inline-block w-1.5 h-1.5 rounded-full bg-brand-500"
                    ></span>
                    <span class="text-[11px] text-brand-700 font-medium"
                        >Completed</span
                    >
                </div>
            </div>

            <!-- Tab Cards or Back Button -->
            {#if !activeTab}
                <div class="pb-4">
                    <p
                        class="text-[11px] font-semibold text-txt-faint uppercase tracking-[0.15em] mb-3"
                    >
                        Explore
                    </p>
                </div>
            {:else}
                <div class="pb-3 flex items-center justify-between">
                    <button
                        class="flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium transition-colors"
                        on:click={() => (activeTab = null)}
                    >
                        <ChevronLeft size={16} /> Back to overview
                    </button>
                    <a
                        href={api.fullReport(meetingId)}
                        target="_blank"
                        class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-1.5 rounded-lg transition-colors"
                    >
                        <Download size={13} /> Full Report PDF
                    </a>
                </div>
            {/if}
        </div>
    </div>

    <!-- ──────────── SPEAKER RENAME PANEL (slides down) ──────────── -->
    {#if showSpeakerPanel}
        <div class="bg-surface-50 border-b border-surface-200">
            <div class="max-w-6xl mx-auto px-6 py-4">
                <p
                    class="text-[11px] text-txt-faint uppercase tracking-wider mb-3"
                >
                    Speaker Names
                </p>
                <div
                    class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2"
                >
                    {#each speakerList as spk}
                        <div class="relative">
                            <span
                                class="absolute left-2.5 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full"
                                style="background-color: {getColor(spk)}"
                            ></span>
                            <input
                                type="text"
                                class="w-full pl-7 pr-3 py-2 text-sm bg-white border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600"
                                placeholder={spk}
                                bind:value={renameInputs[spk]}
                            />
                        </div>
                    {/each}
                </div>
                <div class="flex gap-2 mt-3">
                    <button
                        class="bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium px-3.5 py-1.5 rounded-lg transition-colors"
                        on:click={applyNames}>Apply</button
                    >
                    <button
                        class="text-xs text-txt-muted hover:text-txt-primary px-3 py-1.5 transition-colors"
                        on:click={resetNames}>Reset</button
                    >
                </div>
            </div>
        </div>
    {/if}

    <!-- ───────────────────── CARD GRID (when no tab selected) ───────────────────── -->
    {#if !activeTab}
        <div class="max-w-6xl mx-auto px-6 py-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {#each tabs as tab}
                    <button
                        class="group text-left bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 cursor-pointer overflow-hidden relative"
                        on:click={() => (activeTab = tab.id)}
                    >
                        <!-- Gradient accent on top -->
                        <div
                            class="absolute top-0 left-0 right-0 h-1 {tab.bg} opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                        ></div>

                        <!-- Icon -->
                        <div
                            class="w-11 h-11 rounded-xl {tab.bg} border {tab.border} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300"
                        >
                            <svelte:component
                                this={tab.icon}
                                size={20}
                                class={tab.color}
                            />
                        </div>

                        <!-- Title -->
                        <h3
                            class="text-[15px] font-bold text-txt-primary mb-1.5 group-hover:{tab.color} transition-colors"
                        >
                            {tab.label}
                        </h3>

                        <!-- Description -->
                        <p
                            class="text-[12px] text-txt-secondary leading-relaxed mb-4"
                        >
                            {tab.desc}
                        </p>

                        <!-- CTA -->
                        <span
                            class="inline-flex items-center gap-1 text-[12px] font-semibold {tab.color} group-hover:gap-2 transition-all duration-200"
                        >
                            Explore <ArrowUpRight size={13} />
                        </span>
                    </button>
                {/each}
            </div>
        </div>
    {/if}

    <!-- ───────────────────── TAB CONTENT ───────────────────── -->
    <div class="max-w-6xl mx-auto px-6 py-6">
        <!-- ═══════════════════ CHAT VIEW ═══════════════════ -->
        {#if activeTab === "chat"}
            <!-- Subtitle Export Bar -->
            <div class="flex items-center justify-between mb-4">
                <p
                    class="text-[11px] font-semibold text-txt-faint uppercase tracking-[0.15em]"
                >
                    {segments.length} segments
                </p>
                <div class="flex items-center gap-2">
                    <span class="text-[11px] text-txt-faint">Download:</span>
                    <a
                        href={api.subtitleSrt(meetingId)}
                        download
                        class="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-lg transition-colors"
                    >
                        <Download size={11} /> SRT
                    </a>
                    <a
                        href={api.subtitleVtt(meetingId)}
                        download
                        class="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-600 hover:text-purple-700 bg-purple-50 hover:bg-purple-100 px-2.5 py-1 rounded-lg transition-colors"
                    >
                        <Download size={11} /> VTT
                    </a>
                </div>
            </div>
            <div class="max-w-3xl space-y-3">
                {#each segments as seg, i}
                    {@const prevSpeaker =
                        i > 0 ? segments[i - 1].speaker : null}
                    {@const isNewSpeaker = seg.speaker !== prevSpeaker}

                    {#if isNewSpeaker}
                        <div
                            class="group bg-white rounded-xl border border-surface-200/60 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer overflow-hidden"
                        >
                            <div class="flex gap-3.5 p-4">
                                <!-- Speaker color bar -->
                                <div
                                    class="w-1 rounded-full flex-shrink-0 -my-1 -ml-1"
                                    style="background-color: {getColor(
                                        seg.speaker,
                                    )}"
                                ></div>

                                <!-- Avatar -->
                                <div
                                    class="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 text-white text-[11px] font-bold shadow-sm"
                                    style="background-color: {getColor(
                                        seg.speaker,
                                    )}"
                                >
                                    {displayName(seg.speaker)
                                        .charAt(0)
                                        .toUpperCase()}
                                </div>

                                <div class="flex-1 min-w-0">
                                    <!-- Speaker name & time -->
                                    <div class="flex items-center gap-2 mb-1.5">
                                        <span
                                            class="text-[13px] font-semibold"
                                            style="color: {getColor(
                                                seg.speaker,
                                            )}"
                                        >
                                            {displayName(seg.speaker)}
                                        </span>
                                        <span
                                            class="text-[10px] text-txt-faint font-mono bg-surface-50 px-1.5 py-0.5 rounded"
                                        >
                                            {formatTime(seg.start)} – {formatTime(
                                                seg.end,
                                            )}
                                        </span>
                                    </div>
                                    <!-- Text content -->
                                    <p
                                        class="text-[13px] text-txt-secondary leading-relaxed"
                                    >
                                        {seg.text}
                                    </p>

                                    <!-- Collect consecutive segments from same speaker -->
                                    {#each segments.slice(i + 1) as nextSeg, j}
                                        {#if nextSeg.speaker === seg.speaker && (j === 0 || segments[i + j]?.speaker === seg.speaker)}
                                            <p
                                                class="text-[13px] text-txt-secondary leading-relaxed mt-1.5"
                                            >
                                                {nextSeg.text}
                                            </p>
                                        {/if}
                                    {/each}
                                </div>
                            </div>
                        </div>
                    {/if}
                {/each}
            </div>

            <!-- ═══════════════════ SPEAKER VIEW ═══════════════════ -->
        {:else if activeTab === "speaker"}
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {#each Object.entries(speakers) as [spkId, segs]}
                    <div
                        class="bg-white border border-surface-200 rounded-xl overflow-hidden"
                    >
                        <div
                            class="flex items-center gap-3 px-4 py-3 border-b border-surface-100"
                        >
                            <div
                                class="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold"
                                style="background-color: {getColor(spkId)}"
                            >
                                {displayName(spkId).charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <span
                                    class="text-sm font-semibold text-txt-primary"
                                    >{displayName(spkId)}</span
                                >
                                <span class="text-[11px] text-txt-faint ml-2"
                                    >{segs.length} segments</span
                                >
                            </div>
                        </div>
                        <div
                            class="divide-y divide-surface-100 max-h-72 overflow-y-auto"
                        >
                            {#each segs as s}
                                <div
                                    class="px-4 py-2.5 hover:bg-surface-50 transition-colors"
                                >
                                    <span
                                        class="text-[10px] font-mono text-txt-faint"
                                        >{formatTime(s.start)} – {formatTime(
                                            s.end,
                                        )}</span
                                    >
                                    <p
                                        class="text-[13px] text-txt-secondary mt-0.5 leading-relaxed"
                                    >
                                        {s.text}
                                    </p>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/each}
            </div>

            <!-- ═══════════════════ TIMELINE VIEW ═══════════════════ -->
        {:else if activeTab === "timeline"}
            <div
                class="bg-white border border-surface-200 rounded-xl overflow-hidden"
            >
                <table class="w-full">
                    <thead>
                        <tr
                            class="border-b border-surface-200 bg-surface-50/60"
                        >
                            <th
                                class="text-left px-4 py-2.5 text-[10px] font-semibold text-txt-faint uppercase tracking-wider w-20"
                                >Time</th
                            >
                            <th
                                class="text-left px-4 py-2.5 text-[10px] font-semibold text-txt-faint uppercase tracking-wider w-32"
                                >Speaker</th
                            >
                            <th
                                class="text-left px-4 py-2.5 text-[10px] font-semibold text-txt-faint uppercase tracking-wider"
                                >Content</th
                            >
                        </tr>
                    </thead>
                    <tbody>
                        {#each segments as seg}
                            <tr
                                class="border-b border-surface-100 last:border-0 hover:bg-surface-50/40 transition-colors"
                            >
                                <td
                                    class="px-4 py-2.5 text-[11px] text-txt-faint font-mono align-top"
                                    >{formatTime(seg.start)} – {formatTime(
                                        seg.end,
                                    )}</td
                                >
                                <td class="px-4 py-2.5 align-top">
                                    <span
                                        class="inline-flex items-center gap-1.5"
                                    >
                                        <span
                                            class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                                            style="background-color: {getColor(
                                                seg.speaker,
                                            )}"
                                        ></span>
                                        <span
                                            class="text-[13px] text-txt-primary font-medium"
                                            >{displayName(seg.speaker)}</span
                                        >
                                    </span>
                                </td>
                                <td
                                    class="px-4 py-2.5 text-[13px] text-txt-secondary leading-relaxed"
                                    >{seg.text}</td
                                >
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            <!-- ═══════════════════ SUMMARY VIEW ═══════════════════ -->
        {:else if activeTab === "summary"}
            <div class="max-w-4xl space-y-6">
                <!-- Generate CTA -->
                {#if !summary}
                    <div
                        class="bg-white border border-surface-200 rounded-2xl p-10 text-center"
                    >
                        <div
                            class="w-12 h-12 mx-auto rounded-xl bg-brand-100 flex items-center justify-center mb-4"
                        >
                            <Sparkles size={22} class="text-brand-600" />
                        </div>
                        <h3
                            class="text-base font-semibold text-txt-primary mb-1"
                        >
                            Generate AI Summary
                        </h3>
                        <p class="text-sm text-txt-muted mb-5 max-w-sm mx-auto">
                            Create speaker-wise and overall summaries powered by
                            AI.
                        </p>
                        <button
                            class="btn-primary"
                            on:click={() => generateSummary(false)}
                            disabled={generatingSummary}
                        >
                            {#if generatingSummary}
                                <Loader2 size={16} class="animate-spin" /> Generating…
                            {:else}
                                <Sparkles size={16} /> Generate Summary
                            {/if}
                        </button>
                    </div>
                {:else}
                    <!-- Speaker Summaries -->
                    {#if summary.speaker_summaries_en}
                        <div>
                            <h3
                                class="text-[11px] font-semibold text-txt-faint uppercase tracking-wider mb-3"
                            >
                                Speaker Summaries
                            </h3>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {#each Object.entries(summary.speaker_summaries_en) as [spk, text]}
                                    <div
                                        class="bg-white border border-surface-200 rounded-xl p-4"
                                    >
                                        <div
                                            class="flex items-center gap-2 mb-2"
                                        >
                                            <span
                                                class="w-2 h-2 rounded-full"
                                                style="background-color: {getColor(
                                                    spk,
                                                )}"
                                            ></span>
                                            <span
                                                class="text-[13px] font-semibold text-txt-primary"
                                                >{displayName(spk)}</span
                                            >
                                        </div>
                                        <p
                                            class="text-[13px] text-txt-secondary leading-relaxed"
                                        >
                                            {text}
                                        </p>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Overall Summary — Editable -->
                    <div>
                        <h3
                            class="text-[11px] font-semibold text-txt-faint uppercase tracking-wider mb-3"
                        >
                            Overall Summary
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div
                                class="bg-white border border-surface-200 rounded-xl p-4"
                            >
                                <span
                                    class="text-[10px] font-semibold text-txt-faint uppercase tracking-wider"
                                    >English</span
                                >
                                <textarea
                                    class="w-full mt-2 h-32 text-[13px] text-txt-secondary leading-relaxed bg-transparent border-0 p-0 focus:outline-none resize-none"
                                    bind:value={editedEn}
                                ></textarea>
                            </div>
                            <div
                                class="bg-white border border-surface-200 rounded-xl p-4 border-l-2 border-l-orange-400"
                            >
                                <span
                                    class="text-[10px] font-semibold text-txt-faint uppercase tracking-wider"
                                    >हिंदी</span
                                >
                                <textarea
                                    class="w-full mt-2 h-32 text-[13px] text-txt-secondary leading-relaxed bg-transparent border-0 p-0 focus:outline-none resize-none"
                                    bind:value={editedHi}
                                ></textarea>
                            </div>
                        </div>
                    </div>

                    <!-- Action Bar -->
                    <div class="flex flex-wrap items-center gap-2">
                        <button
                            class="btn-primary text-sm"
                            on:click={approveSummary}
                        >
                            <Check size={14} /> Approve
                        </button>
                        <button
                            class="btn-secondary text-sm"
                            on:click={() => (showRewriteBox = !showRewriteBox)}
                        >
                            <RefreshCw size={14} /> Rewrite
                        </button>

                        {#if approved}
                            <span class="mx-1 text-surface-300">|</span>
                            <button
                                class="btn-secondary text-sm"
                                on:click={downloadPdf}
                            >
                                <Download size={14} /> PDF
                            </button>
                            <button
                                class="btn-secondary text-sm"
                                on:click={sendEmail}
                            >
                                <Mail size={14} /> Email
                            </button>
                            <button
                                class="btn-secondary text-sm"
                                on:click={sendToTeams}
                            >
                                <MessageSquare size={14} /> Teams
                            </button>
                        {/if}
                    </div>

                    <!-- Rewrite Box -->
                    {#if showRewriteBox}
                        <div
                            class="bg-white border border-brand-200 rounded-xl p-4 flex gap-3 items-end"
                        >
                            <div class="flex-1">
                                <span
                                    class="text-[10px] font-semibold text-txt-faint uppercase tracking-wider"
                                    >Custom instructions</span
                                >
                                <textarea
                                    class="w-full mt-1.5 h-16 text-sm text-txt-secondary bg-surface-50 border border-surface-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 resize-none"
                                    placeholder="e.g. Make it more concise, Focus on decisions, Use bullet points…"
                                    bind:value={rewritePrompt}
                                ></textarea>
                            </div>
                            <button
                                class="btn-primary text-sm flex-shrink-0 self-end mb-0.5"
                                on:click={() => generateSummary(true)}
                                disabled={generatingSummary}
                            >
                                {#if generatingSummary}
                                    <Loader2 size={14} class="animate-spin" /> Rewriting…
                                {:else}
                                    <Sparkles size={14} /> Rewrite
                                {/if}
                            </button>
                        </div>
                    {/if}

                    {#if !approved}
                        <p class="text-xs text-txt-faint italic">
                            Review and approve the summary to unlock sharing
                            options.
                        </p>
                    {/if}
                {/if}
            </div>
        {/if}

        <!-- =================== REQUIREMENTS TAB (Optional) =================== -->
        {#if activeTab === "requirements"}
            <div
                class="bg-white rounded-2xl shadow-sm border border-surface-200 p-6"
            >
                <div class="flex items-center justify-between mb-5">
                    <div>
                        <span
                            class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-0.5"
                            >Requirements</span
                        >
                        <p class="text-xs text-txt-faint">
                            Extract functional requirements, user stories, and
                            constraints discussed in this meeting.
                        </p>
                    </div>
                    <button
                        class="btn-primary text-sm"
                        on:click={() => extractRequirements(!reqData)}
                        disabled={extractingReqs}
                    >
                        {#if extractingReqs}
                            <Loader2 size={14} class="animate-spin" /> Extracting…
                        {:else}
                            <Sparkles size={14} />
                            {reqData ? "Regenerate" : "Extract Requirements"}
                        {/if}
                    </button>
                </div>

                {#if !reqData}
                    <div class="text-center py-16">
                        <div
                            class="w-14 h-14 mx-auto rounded-2xl bg-emerald-50 flex items-center justify-center mb-4"
                        >
                            <Sparkles size={24} class="text-emerald-600" />
                        </div>
                        <h3 class="font-bold text-txt-primary mb-1">
                            No requirements extracted
                        </h3>
                        <p class="text-sm text-txt-faint">
                            Click "Extract Requirements" to analyze this meeting
                            for requirements.
                        </p>
                        <p class="text-xs text-txt-faint mt-1">
                            This is optional — use only for
                            requirement-gathering meetings.
                        </p>
                    </div>
                {:else}
                    <!-- Functional Requirements -->
                    {#if reqData.functional_requirements?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-3"
                                >Functional Requirements</span
                            >
                            <div class="space-y-2">
                                {#each reqData.functional_requirements as req}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60"
                                    >
                                        <div
                                            class="flex items-start justify-between gap-3"
                                        >
                                            <div>
                                                <span
                                                    class="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded mr-2"
                                                    >{req.id}</span
                                                >
                                                <span
                                                    class="text-sm font-semibold text-txt-primary"
                                                    >{req.title}</span
                                                >
                                            </div>
                                            <span
                                                class="text-[10px] font-semibold px-2 py-0.5 rounded-full border
                                                {req.priority === 'must-have'
                                                    ? 'text-red-700 bg-red-50 border-red-200'
                                                    : req.priority ===
                                                        'should-have'
                                                      ? 'text-amber-700 bg-amber-50 border-amber-200'
                                                      : 'text-emerald-700 bg-emerald-50 border-emerald-200'}"
                                                >{req.priority}</span
                                            >
                                        </div>
                                        <p
                                            class="text-xs text-txt-secondary mt-1.5"
                                        >
                                            {req.description}
                                        </p>
                                        <p
                                            class="text-[10px] text-txt-faint mt-1"
                                        >
                                            Raised by: {req.raised_by ||
                                                "Unknown"}
                                        </p>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Non-Functional Requirements -->
                    {#if reqData.non_functional_requirements?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-3"
                                >Non-Functional Requirements</span
                            >
                            <div class="grid md:grid-cols-2 gap-2">
                                {#each reqData.non_functional_requirements as nfr}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60"
                                    >
                                        <span
                                            class="text-[10px] font-mono text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded mr-2"
                                            >{nfr.id}</span
                                        >
                                        <span
                                            class="text-sm font-semibold text-txt-primary"
                                            >{nfr.title}</span
                                        >
                                        <p
                                            class="text-xs text-txt-secondary mt-1.5"
                                        >
                                            {nfr.description}
                                        </p>
                                        <span
                                            class="text-[10px] text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full mt-1.5 inline-block"
                                            >{nfr.category}</span
                                        >
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- User Stories -->
                    {#if reqData.user_stories?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-3"
                                >User Stories</span
                            >
                            <div class="space-y-1.5">
                                {#each reqData.user_stories as story}
                                    <div
                                        class="bg-blue-50/50 rounded-lg p-3 border border-blue-100 text-sm text-blue-900 italic"
                                    >
                                        "{story}"
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Constraints & Open Questions -->
                    <div class="grid md:grid-cols-2 gap-4">
                        {#if reqData.constraints?.length}
                            <div>
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-2"
                                    >Constraints</span
                                >
                                <ul class="space-y-1">
                                    {#each reqData.constraints as c}
                                        <li
                                            class="text-sm text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-amber-500 mt-1 text-[8px]"
                                                >●</span
                                            >
                                            {c}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                        {#if reqData.open_questions?.length}
                            <div>
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-2"
                                    >Open Questions</span
                                >
                                <ul class="space-y-1">
                                    {#each reqData.open_questions as q}
                                        <li
                                            class="text-sm text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-blue-500 mt-1 text-[8px]"
                                                >●</span
                                            >
                                            {q}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- =================== DOCUMENTATION TAB (Optional) =================== -->
        {#if activeTab === "docs"}
            <div
                class="bg-white rounded-2xl shadow-sm border border-surface-200 p-6"
            >
                <div class="flex items-center justify-between mb-5">
                    <div>
                        <span
                            class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-0.5"
                            >Documentation</span
                        >
                        <p class="text-xs text-txt-faint">
                            Generate structured meeting minutes and technical
                            documentation.
                        </p>
                    </div>
                    <button
                        class="btn-primary text-sm"
                        on:click={() => generateDocumentation(!docData)}
                        disabled={generatingDocs}
                    >
                        {#if generatingDocs}
                            <Loader2 size={14} class="animate-spin" /> Generating…
                        {:else}
                            <Sparkles size={14} />
                            {docData ? "Regenerate" : "Generate Docs"}
                        {/if}
                    </button>
                </div>

                {#if !docData}
                    <div class="text-center py-16">
                        <div
                            class="w-14 h-14 mx-auto rounded-2xl bg-emerald-50 flex items-center justify-center mb-4"
                        >
                            <Sparkles size={24} class="text-emerald-600" />
                        </div>
                        <h3 class="font-bold text-txt-primary mb-1">
                            No documentation generated
                        </h3>
                        <p class="text-sm text-txt-faint">
                            Click "Generate Docs" to create meeting minutes.
                        </p>
                        <p class="text-xs text-txt-faint mt-1">
                            This is optional — use for meetings that need formal
                            documentation.
                        </p>
                    </div>
                {:else}
                    <!-- Objective -->
                    {#if docData.objective}
                        <div
                            class="mb-6 bg-emerald-50/50 rounded-xl p-4 border border-emerald-100"
                        >
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-1"
                                >Meeting Objective</span
                            >
                            <p class="text-sm text-txt-primary">
                                {docData.objective}
                            </p>
                        </div>
                    {/if}

                    <!-- Topics Discussed -->
                    {#if docData.topics_discussed?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-3"
                                >Topics Discussed</span
                            >
                            <div class="space-y-3">
                                {#each docData.topics_discussed as topic, i}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60"
                                    >
                                        <p
                                            class="text-sm font-semibold text-txt-primary flex items-center gap-2"
                                        >
                                            <span
                                                class="text-[10px] font-mono text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded"
                                                >{i + 1}</span
                                            >
                                            {topic.topic}
                                        </p>
                                        <p
                                            class="text-xs text-txt-secondary mt-1.5"
                                        >
                                            {topic.summary}
                                        </p>
                                        {#if topic.speakers_involved?.length}
                                            <p
                                                class="text-[10px] text-txt-faint mt-1"
                                            >
                                                Speakers: {topic.speakers_involved.join(
                                                    ", ",
                                                )}
                                            </p>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Technical Details -->
                    {#if docData.technical_details?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-3"
                                >Technical Details</span
                            >
                            <div class="space-y-2">
                                {#each docData.technical_details as tech}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60"
                                    >
                                        <p
                                            class="text-sm font-semibold text-txt-primary"
                                        >
                                            {tech.area}
                                        </p>
                                        <p
                                            class="text-xs text-txt-secondary mt-1"
                                        >
                                            {tech.details}
                                        </p>
                                        {#if tech.tools_mentioned?.length}
                                            <div
                                                class="flex flex-wrap gap-1 mt-2"
                                            >
                                                {#each tech.tools_mentioned as tool}
                                                    <span
                                                        class="text-[10px] font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full"
                                                        >{tool}</span
                                                    >
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Decisions & Rationale -->
                    {#if docData.decisions_and_rationale?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-3"
                                >Decisions & Rationale</span
                            >
                            <div class="space-y-2">
                                {#each docData.decisions_and_rationale as d}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60"
                                    >
                                        <p
                                            class="text-sm font-semibold text-txt-primary"
                                        >
                                            {d.decision}
                                        </p>
                                        <p
                                            class="text-xs text-txt-secondary mt-1"
                                        >
                                            <span
                                                class="font-medium text-txt-muted"
                                                >Why:</span
                                            >
                                            {d.rationale || "Not specified"}
                                        </p>
                                        {#if d.alternatives_discussed}
                                            <p
                                                class="text-xs text-txt-faint mt-0.5"
                                            >
                                                <span class="font-medium"
                                                    >Alternatives:</span
                                                >
                                                {d.alternatives_discussed}
                                            </p>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Next Steps & Parking Lot -->
                    <div class="grid md:grid-cols-2 gap-4">
                        {#if docData.next_steps?.length}
                            <div>
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-2"
                                    >Next Steps</span
                                >
                                <ul class="space-y-1">
                                    {#each docData.next_steps as step}
                                        <li
                                            class="text-sm text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-emerald-500 mt-1 text-[8px]"
                                                >●</span
                                            >
                                            {step}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                        {#if docData.parking_lot?.length}
                            <div>
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-2"
                                    >Parking Lot</span
                                >
                                <ul class="space-y-1">
                                    {#each docData.parking_lot as item}
                                        <li
                                            class="text-sm text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-amber-500 mt-1 text-[8px]"
                                                >●</span
                                            >
                                            {item}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- ═══════════════════ SENTIMENT ═══════════════════ -->
        {#if activeTab === "sentiment"}
            <div
                class="bg-white rounded-2xl shadow-sm border border-surface-200 p-6"
            >
                <div class="flex items-center justify-between mb-5">
                    <div>
                        <span
                            class="text-[10px] font-bold text-pink-600 uppercase tracking-[0.15em] block mb-0.5"
                            >Sentiment Analysis</span
                        >
                        <p class="text-xs text-txt-faint">
                            Analyze emotional tone and mood shifts across the
                            meeting.
                        </p>
                    </div>
                    <button
                        class="btn-primary text-sm"
                        on:click={() => analyzeSentiment(!sentimentData)}
                        disabled={analyzingSentiment}
                    >
                        {#if analyzingSentiment}
                            <Loader2 size={14} class="animate-spin" /> Analyzing…
                        {:else}
                            <BarChart3 size={14} />
                            {sentimentData ? "Re-analyze" : "Analyze Sentiment"}
                        {/if}
                    </button>
                </div>

                {#if !sentimentData}
                    <div class="text-center py-16">
                        <div
                            class="w-14 h-14 mx-auto rounded-2xl bg-pink-50 flex items-center justify-center mb-4"
                        >
                            <BarChart3 size={24} class="text-pink-600" />
                        </div>
                        <h3 class="font-bold text-txt-primary mb-1">
                            No sentiment analysis yet
                        </h3>
                        <p class="text-sm text-txt-faint">
                            Click "Analyze Sentiment" to detect emotional tone.
                        </p>
                        <p class="text-xs text-txt-faint mt-1">
                            This is optional — use to understand meeting
                            dynamics.
                        </p>
                    </div>
                {:else}
                    <!-- Overall Mood -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div
                            class="bg-surface-50 rounded-xl p-4 border border-surface-200 text-center"
                        >
                            <div class="text-3xl mb-2">
                                {sentimentEmoji(
                                    sentimentData.overall_sentiment,
                                )}
                            </div>
                            <div
                                class="text-[10px] font-bold uppercase tracking-wider text-txt-faint mb-1"
                            >
                                Overall Mood
                            </div>
                            <span
                                class="inline-block px-3 py-1 rounded-full text-sm font-semibold capitalize"
                                style="background-color: {sentimentColor(
                                    sentimentData.overall_sentiment,
                                )}20; color: {sentimentColor(
                                    sentimentData.overall_sentiment,
                                )}"
                            >
                                {sentimentData.overall_sentiment}
                            </span>
                        </div>
                        <div
                            class="bg-surface-50 rounded-xl p-4 border border-surface-200 text-center"
                        >
                            <div
                                class="text-3xl font-bold mb-2"
                                style="color: {sentimentColor(
                                    sentimentData.overall_sentiment,
                                )}"
                            >
                                {(sentimentData.overall_score || 0).toFixed(2)}
                            </div>
                            <div
                                class="text-[10px] font-bold uppercase tracking-wider text-txt-faint mb-1"
                            >
                                Score
                            </div>
                            <div class="text-xs text-txt-faint">
                                -1.0 (negative) to +1.0 (positive)
                            </div>
                        </div>
                        <div
                            class="bg-surface-50 rounded-xl p-4 border border-surface-200"
                        >
                            <div
                                class="text-[10px] font-bold uppercase tracking-wider text-txt-faint mb-2"
                            >
                                Breakdown
                            </div>
                            <div class="space-y-2">
                                <div class="flex items-center gap-2">
                                    <div
                                        class="w-2 h-2 rounded-full bg-emerald-500"
                                    ></div>
                                    <span
                                        class="text-xs text-txt-secondary flex-1"
                                        >Positive</span
                                    >
                                    <span
                                        class="text-xs font-mono font-semibold text-emerald-600"
                                        >{sentimentData.segments.filter(
                                            (s) => s.sentiment === "positive",
                                        ).length} ({Math.round(
                                            (sentimentData.segments.filter(
                                                (s) =>
                                                    s.sentiment === "positive",
                                            ).length /
                                                (sentimentData.segments
                                                    .length || 1)) *
                                                100,
                                        )}%)</span
                                    >
                                </div>
                                <div class="flex items-center gap-2">
                                    <div
                                        class="w-2 h-2 rounded-full bg-red-500"
                                    ></div>
                                    <span
                                        class="text-xs text-txt-secondary flex-1"
                                        >Negative</span
                                    >
                                    <span
                                        class="text-xs font-mono font-semibold text-red-600"
                                        >{sentimentData.segments.filter(
                                            (s) => s.sentiment === "negative",
                                        ).length} ({Math.round(
                                            (sentimentData.segments.filter(
                                                (s) =>
                                                    s.sentiment === "negative",
                                            ).length /
                                                (sentimentData.segments
                                                    .length || 1)) *
                                                100,
                                        )}%)</span
                                    >
                                </div>
                                <div class="flex items-center gap-2">
                                    <div
                                        class="w-2 h-2 rounded-full bg-slate-400"
                                    ></div>
                                    <span
                                        class="text-xs text-txt-secondary flex-1"
                                        >Neutral</span
                                    >
                                    <span
                                        class="text-xs font-mono font-semibold text-slate-600"
                                        >{sentimentData.segments.filter(
                                            (s) => s.sentiment === "neutral",
                                        ).length} ({Math.round(
                                            (sentimentData.segments.filter(
                                                (s) =>
                                                    s.sentiment === "neutral",
                                            ).length /
                                                (sentimentData.segments
                                                    .length || 1)) *
                                                100,
                                        )}%)</span
                                    >
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Mood Summary -->
                    {#if sentimentData.mood_summary}
                        <div
                            class="bg-pink-50/50 rounded-xl p-4 border border-pink-100 mb-6"
                        >
                            <span
                                class="text-[10px] font-bold text-pink-600 uppercase tracking-[0.15em] block mb-1"
                                >Mood Summary</span
                            >
                            <p class="text-sm text-txt-secondary">
                                {sentimentData.mood_summary}
                            </p>
                        </div>
                    {/if}

                    <!-- Sentiment Timeline Bar Chart -->
                    <div class="mb-6">
                        <span
                            class="text-[10px] font-bold text-pink-600 uppercase tracking-[0.15em] block mb-3"
                            >Sentiment Timeline</span
                        >
                        <div
                            class="bg-surface-50 rounded-xl p-4 border border-surface-200"
                        >
                            <div class="flex items-end gap-px h-24">
                                {#each sentimentData.segments as seg}
                                    {@const normalizedHeight = Math.max(
                                        10,
                                        Math.abs(seg.score) * 100,
                                    )}
                                    <div
                                        class="flex-1 rounded-t-sm transition-all duration-200 hover:opacity-80 cursor-pointer relative group"
                                        style="height: {normalizedHeight}%; background-color: {sentimentColor(
                                            seg.sentiment,
                                        )}; min-width: 2px;"
                                        title="{displayName(
                                            seg.speaker,
                                        )}: {seg.emotion} ({seg.score > 0
                                            ? '+'
                                            : ''}{seg.score})"
                                    >
                                        <div
                                            class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-gray-900 text-white text-[10px] rounded px-2 py-1 whitespace-nowrap z-10"
                                        >
                                            {displayName(seg.speaker)}: {seg.emotion}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                            <div class="flex justify-between mt-2">
                                <span class="text-[10px] text-txt-faint"
                                    >Start</span
                                >
                                <span class="text-[10px] text-txt-faint"
                                    >End</span
                                >
                            </div>
                        </div>
                    </div>

                    <!-- Highlights -->
                    {#if sentimentData.highlights}
                        <div class="grid md:grid-cols-2 gap-4 mb-6">
                            <div
                                class="bg-emerald-50/50 rounded-xl p-4 border border-emerald-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-2"
                                    >😊 Most Positive Moment</span
                                >
                                <p class="text-sm text-txt-secondary italic">
                                    "{sentimentData.highlights.most_positive ||
                                        "N/A"}"
                                </p>
                            </div>
                            <div
                                class="bg-red-50/50 rounded-xl p-4 border border-red-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-red-600 uppercase tracking-[0.15em] block mb-2"
                                    >😟 Most Negative Moment</span
                                >
                                <p class="text-sm text-txt-secondary italic">
                                    "{sentimentData.highlights.most_negative ||
                                        "N/A"}"
                                </p>
                            </div>
                        </div>
                        {#if sentimentData.highlights.turning_points?.length}
                            <div
                                class="bg-amber-50/50 rounded-xl p-4 border border-amber-100 mb-6"
                            >
                                <span
                                    class="text-[10px] font-bold text-amber-600 uppercase tracking-[0.15em] block mb-2"
                                    >⚡ Turning Points</span
                                >
                                <ul class="space-y-1">
                                    {#each sentimentData.highlights.turning_points as tp}
                                        <li
                                            class="text-sm text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-amber-500 mt-1 text-[8px]"
                                                >●</span
                                            >
                                            {tp}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    {/if}

                    <!-- Segment Details -->
                    <div>
                        <span
                            class="text-[10px] font-bold text-pink-600 uppercase tracking-[0.15em] block mb-3"
                            >Segment Details</span
                        >
                        <div class="space-y-1.5 max-h-96 overflow-y-auto">
                            {#each sentimentData.segments as seg}
                                <div
                                    class="flex items-center gap-3 p-2.5 rounded-lg hover:bg-surface-50 transition-colors"
                                >
                                    <div
                                        class="w-2 h-2 rounded-full flex-shrink-0"
                                        style="background-color: {sentimentColor(
                                            seg.sentiment,
                                        )}"
                                    ></div>
                                    <span
                                        class="text-[11px] font-mono text-txt-faint w-20 flex-shrink-0"
                                        >{formatTime(seg.start)} – {formatTime(
                                            seg.end,
                                        )}</span
                                    >
                                    <span
                                        class="text-[12px] font-semibold text-txt-primary w-28 flex-shrink-0 truncate"
                                        >{displayName(seg.speaker)}</span
                                    >
                                    <p
                                        class="text-[12px] text-txt-secondary flex-1 truncate"
                                    >
                                        {seg.text}
                                    </p>
                                    <span
                                        class="text-[10px] font-medium px-2 py-0.5 rounded-full capitalize flex-shrink-0"
                                        style="background-color: {sentimentColor(
                                            seg.sentiment,
                                        )}15; color: {sentimentColor(
                                            seg.sentiment,
                                        )}"
                                    >
                                        {seg.emotion}
                                    </span>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        {/if}
    </div>
{/if}
