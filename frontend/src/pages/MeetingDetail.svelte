<script>
    import { onMount, afterUpdate, tick } from "svelte";
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
        Hash,
        ArrowUpRight,
        ClipboardList,
        FileText,
        BarChart3,
        Activity,
        Tag,
        Layers,
        UserCheck,
        Share2,
        ExternalLink,
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
    import Skeleton from "../components/Skeleton.svelte";
    import SpeakerAudioPlayer from "../components/SpeakerAudioPlayer.svelte";
    import {
        Chart,
        DoughnutController,
        ArcElement,
        Tooltip,
        Legend,
    } from "chart.js";
    Chart.register(DoughnutController, ArcElement, Tooltip, Legend);

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

    // Email modal
    let showEmailModal = false;
    let emailInput = "";
    let sendingEmail = false;

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

    // Speaker Analytics
    let speakerAnalyticsData = null;
    let loadingSpeakerAnalytics = false;

    // Keyword Cloud
    let keywordsData = null;
    let loadingKeywords = false;

    // Topic Segmentation
    let topicsData = null;
    let loadingTopics = false;

    // Speaker Report Cards
    let speakerReportData = null;
    let loadingSpeakerReport = false;

    // Publish / Integrations
    let pushingNotion = false;
    let pushingConfluence = false;
    let notionResult = null;
    let confluenceResult = null;

    // Full Report PDF
    let generatingReport = false;
    let reportReady = false;
    let reportResult = null;
    let showReportEmailModal = false;
    let reportEmailInput = "";
    let sendingReportEmail = false;

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
        {
            id: "keywords",
            label: "Keyword Cloud",
            icon: Tag,
            color: "text-orange-600",
            bg: "bg-orange-50",
            border: "border-orange-100",
            desc: "Top keywords and terms discussed most frequently in the meeting.",
        },
        {
            id: "topics",
            label: "Topics",
            icon: Layers,
            color: "text-indigo-600",
            bg: "bg-indigo-50",
            border: "border-indigo-100",
            desc: "Topic segmentation — what was discussed when during the meeting.",
        },
        {
            id: "publish",
            label: "Publish",
            icon: Share2,
            color: "text-pink-600",
            bg: "bg-pink-50",
            border: "border-pink-100",
            desc: "Push meeting data to Notion or Confluence.",
        },
        {
            id: "fullReport",
            label: "Full Report",
            icon: Download,
            color: "text-cyan-600",
            bg: "bg-cyan-50",
            border: "border-cyan-100",
            desc: "Generate comprehensive PDF report with all meeting insights.",
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
        const recipients = emailInput
            .split(/[,;\s]+/)
            .map((e) => e.trim())
            .filter((e) => e.length > 0);

        if (recipients.length === 0) {
            toasts.error("Please enter at least one email address.");
            return;
        }

        // Basic email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const invalid = recipients.filter((e) => !emailRegex.test(e));
        if (invalid.length > 0) {
            toasts.error("Invalid email(s): " + invalid.join(", "));
            return;
        }

        sendingEmail = true;
        try {
            const res = await post(api.publish(meetingId), {
                meeting_title: autoTitle || `Meeting ${shortId(meetingId)}`,
                email_recipients: recipients,
            });
            if (res.email?.success) {
                toasts.success(
                    "Email sent successfully to " + recipients.join(", ") + "!",
                );
                showEmailModal = false;
                emailInput = "";
            } else {
                toasts.error(
                    "Email failed: " + (res.email?.message || "Unknown error"),
                );
            }
        } catch (err) {
            toasts.error("Email failed: " + err.message);
        }
        sendingEmail = false;
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

    // Speaker talk-time data (computed from segments)
    let talkTimeChart = null;
    let talkTimeCanvas;

    $: speakerTalkTime = (() => {
        const times = {};
        segments.forEach((seg) => {
            const spk = seg.speaker || "UNKNOWN";
            if (!times[spk]) times[spk] = 0;
            times[spk] += seg.end - seg.start;
        });
        const total = Object.values(times).reduce((a, b) => a + b, 0) || 1;
        // Reference smap to re-trigger when speaker names change
        const _smap = smap;
        return Object.entries(times)
            .sort((a, b) => b[1] - a[1])
            .map(([speaker, duration]) => ({
                speaker,
                duration,
                percent: Math.round((duration / total) * 100),
                label: displayName(speaker),
            }));
    })();

    async function renderTalkTimeChart() {
        if (!talkTimeCanvas || speakerTalkTime.length === 0) return;
        await tick();
        if (talkTimeChart) talkTimeChart.destroy();
        const colors = speakerTalkTime.map((s) => getColor(s.speaker));
        talkTimeChart = new Chart(talkTimeCanvas, {
            type: "doughnut",
            data: {
                labels: speakerTalkTime.map((s) => s.label),
                datasets: [
                    {
                        data: speakerTalkTime.map((s) => s.duration),
                        backgroundColor: colors,
                        borderColor: "#fff",
                        borderWidth: 3,
                        hoverBorderWidth: 0,
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: "65%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#1e293b",
                        titleFont: { size: 13, weight: "bold" },
                        bodyFont: { size: 12 },
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => {
                                const s = speakerTalkTime[ctx.dataIndex];
                                const mins = Math.floor(s.duration / 60);
                                const secs = Math.round(s.duration % 60);
                                return ` ${s.percent}% (${mins}m ${secs}s)`;
                            },
                        },
                    },
                },
            },
        });
    }

    // Re-render chart when Speaker tab is active (re-renders on smap changes too)
    afterUpdate(() => {
        if (activeTab === "speaker" && talkTimeCanvas) {
            renderTalkTimeChart();
        }
    });
</script>

<!-- ───────────────────────────────── SKELETON LOADING ──────────────────────── -->
{#if loading}
    <!-- Skeleton Header Bar -->
    <div
        class="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-surface-200/60"
    >
        <div
            class="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between"
        >
            <div class="flex items-center gap-4">
                <Skeleton width="32px" height="32px" rounded="rounded-lg" />
                <div class="space-y-2">
                    <Skeleton
                        width="220px"
                        height="18px"
                        rounded="rounded-md"
                    />
                    <Skeleton
                        width="140px"
                        height="12px"
                        rounded="rounded-md"
                    />
                </div>
            </div>
            <div class="flex items-center gap-2">
                <Skeleton width="90px" height="28px" rounded="rounded-lg" />
                <Skeleton width="90px" height="28px" rounded="rounded-lg" />
            </div>
        </div>
    </div>

    <!-- Skeleton Tab Bar -->
    <div class="max-w-6xl mx-auto px-6 pt-4">
        <div class="flex gap-2 mb-6 overflow-x-auto pb-1">
            {#each Array(6) as _}
                <Skeleton
                    width="110px"
                    height="52px"
                    rounded="rounded-xl"
                    className="flex-shrink-0"
                />
            {/each}
        </div>

        <!-- Skeleton Chat Messages -->
        <div class="max-w-3xl space-y-3">
            {#each [100, 85, 92, 70, 95] as pct, i}
                <div
                    class="bg-white rounded-xl border border-surface-200/60 shadow-sm p-4 flex gap-3.5"
                >
                    <Skeleton
                        width="36px"
                        height="36px"
                        rounded="rounded-full"
                        className="flex-shrink-0"
                    />
                    <div class="flex-1 space-y-2.5">
                        <div class="flex items-center gap-2">
                            <Skeleton
                                width="{60 + i * 20}px"
                                height="14px"
                                rounded="rounded-md"
                            />
                            <Skeleton
                                width="70px"
                                height="12px"
                                rounded="rounded"
                            />
                        </div>
                        <Skeleton
                            width="{pct}%"
                            height="12px"
                            rounded="rounded"
                        />
                        <Skeleton
                            width="{pct - 20}%"
                            height="12px"
                            rounded="rounded"
                        />
                        {#if i % 2 === 0}
                            <Skeleton
                                width="{pct - 35}%"
                                height="12px"
                                rounded="rounded"
                            />
                        {/if}
                    </div>
                </div>
            {/each}
        </div>
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
                            <div class="mb-1">
                                <SpeakerAudioPlayer
                                    {meetingId}
                                    speakerId={spk}
                                />
                            </div>
                            <span
                                class="absolute left-2.5 bottom-[10px] w-2 h-2 rounded-full"
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
            <!-- Segment count -->
            <div class="flex items-center justify-between mb-4">
                <p
                    class="text-[11px] font-semibold text-txt-faint uppercase tracking-[0.15em]"
                >
                    {segments.length} segments
                </p>
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
            <!-- Talk-Time Chart -->
            {#if speakerTalkTime.length > 0}
                <div
                    class="bg-white rounded-2xl border border-surface-200 shadow-sm p-6 mb-6"
                >
                    <span
                        class="text-[10px] font-bold text-blue-600 uppercase tracking-[0.15em] block mb-4"
                        >Speaker Talk-Time Analysis</span
                    >
                    <div class="flex flex-col md:flex-row items-center gap-8">
                        <!-- Doughnut Chart -->
                        <div class="relative w-52 h-52 flex-shrink-0">
                            <canvas
                                bind:this={talkTimeCanvas}
                                width="208"
                                height="208"
                            ></canvas>
                            <div
                                class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
                            >
                                <span
                                    class="text-2xl font-extrabold text-txt-primary"
                                    >{speakerTalkTime.length}</span
                                >
                                <span
                                    class="text-[10px] text-txt-faint uppercase tracking-wider"
                                    >Speakers</span
                                >
                            </div>
                        </div>
                        <!-- Speaker Bars -->
                        <div class="flex-1 w-full space-y-3">
                            {#each speakerTalkTime as s}
                                <div>
                                    <div
                                        class="flex items-center justify-between mb-1"
                                    >
                                        <div class="flex items-center gap-2">
                                            <div
                                                class="w-3 h-3 rounded-full"
                                                style="background-color: {getColor(
                                                    s.speaker,
                                                )}"
                                            ></div>
                                            <span
                                                class="text-sm font-semibold text-txt-primary"
                                                >{s.label}</span
                                            >
                                        </div>
                                        <span
                                            class="text-xs text-txt-faint font-mono"
                                            >{s.percent}% · {Math.floor(
                                                s.duration / 60,
                                            )}m {Math.round(
                                                s.duration % 60,
                                            )}s</span
                                        >
                                    </div>
                                    <div
                                        class="w-full bg-surface-100 rounded-full h-2.5 overflow-hidden"
                                    >
                                        <div
                                            class="h-full rounded-full transition-all duration-700 ease-out"
                                            style="width: {s.percent}%; background-color: {getColor(
                                                s.speaker,
                                            )}"
                                        ></div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </div>
                </div>
            {/if}

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
                                on:click={() => (showEmailModal = true)}
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

                    <!-- Email Recipients Modal -->
                    {#if showEmailModal}
                        <!-- svelte-ignore a11y-click-events-have-key-events -->
                        <div
                            class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
                            on:click|self={() => (showEmailModal = false)}
                        >
                            <div
                                class="bg-white rounded-2xl shadow-2xl border border-surface-200 w-full max-w-md mx-4 overflow-hidden"
                            >
                                <!-- Header -->
                                <div
                                    class="px-6 pt-5 pb-3 border-b border-surface-100"
                                >
                                    <div class="flex items-center gap-3">
                                        <div
                                            class="w-9 h-9 rounded-xl bg-brand-100 flex items-center justify-center"
                                        >
                                            <Mail
                                                size={18}
                                                class="text-brand-600"
                                            />
                                        </div>
                                        <div>
                                            <h3
                                                class="text-base font-semibold text-txt-primary"
                                            >
                                                Send Summary via Email
                                            </h3>
                                            <p class="text-xs text-txt-faint">
                                                Enter recipient email addresses
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <!-- Body -->
                                <div class="px-6 py-4">
                                    <label class="block">
                                        <span
                                            class="text-[11px] font-semibold text-txt-faint uppercase tracking-wider"
                                            >Recipients</span
                                        >
                                        <textarea
                                            class="w-full mt-1.5 h-20 text-sm text-txt-secondary bg-surface-50 border border-surface-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 resize-none"
                                            placeholder="Enter email addresses separated by commas, e.g.&#10;john@example.com, jane@example.com"
                                            bind:value={emailInput}
                                        ></textarea>
                                    </label>
                                    <p
                                        class="text-[11px] text-txt-faint mt-1.5"
                                    >
                                        Separate multiple emails with commas
                                    </p>
                                </div>

                                <!-- Footer -->
                                <div
                                    class="px-6 pb-5 flex items-center justify-end gap-2"
                                >
                                    <button
                                        class="btn-secondary text-sm"
                                        on:click={() =>
                                            (showEmailModal = false)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        class="btn-primary text-sm"
                                        on:click={sendEmail}
                                        disabled={sendingEmail ||
                                            !emailInput.trim()}
                                    >
                                        {#if sendingEmail}
                                            <Loader2
                                                size={14}
                                                class="animate-spin"
                                            /> Sending…
                                        {:else}
                                            <Mail size={14} /> Send Email
                                        {/if}
                                    </button>
                                </div>
                            </div>
                        </div>
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
                            Extract functional requirements, user stories,
                            risks, and constraints discussed in this meeting.
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
                    <!-- Summary Banner -->
                    {#if reqData.summary}
                        <div
                            class="mb-6 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl p-4 border border-emerald-200/60"
                        >
                            <span
                                class="text-[10px] font-bold text-emerald-700 uppercase tracking-[0.15em] block mb-1"
                                >Overview</span
                            >
                            <p class="text-sm text-emerald-900">
                                {reqData.summary}
                            </p>
                        </div>
                    {/if}

                    <!-- Functional Requirements -->
                    {#if reqData.functional_requirements?.length}
                        <div class="mb-6">
                            <div class="flex items-center gap-2 mb-3">
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em]"
                                    >Functional Requirements</span
                                >
                                <span
                                    class="text-[10px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full"
                                    >{reqData.functional_requirements
                                        .length}</span
                                >
                            </div>
                            <div class="space-y-3">
                                {#each reqData.functional_requirements as req}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60 hover:border-emerald-300/60 transition-colors"
                                    >
                                        <div
                                            class="flex items-start justify-between gap-3"
                                        >
                                            <div
                                                class="flex items-center gap-2"
                                            >
                                                <span
                                                    class="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded"
                                                    >{req.id}</span
                                                >
                                                <span
                                                    class="text-sm font-semibold text-txt-primary"
                                                    >{req.title}</span
                                                >
                                            </div>
                                            <div
                                                class="flex items-center gap-1.5 shrink-0"
                                            >
                                                <span
                                                    class="text-[10px] font-semibold px-2 py-0.5 rounded-full border
                                                    {req.priority ===
                                                    'must-have'
                                                        ? 'text-red-700 bg-red-50 border-red-200'
                                                        : req.priority ===
                                                            'should-have'
                                                          ? 'text-amber-700 bg-amber-50 border-amber-200'
                                                          : 'text-emerald-700 bg-emerald-50 border-emerald-200'}"
                                                    >{req.priority}</span
                                                >
                                                {#if req.status}
                                                    <span
                                                        class="text-[10px] font-medium px-2 py-0.5 rounded-full
                                                        {req.status === 'agreed'
                                                            ? 'text-green-700 bg-green-50'
                                                            : req.status ===
                                                                'needs-discussion'
                                                              ? 'text-orange-700 bg-orange-50'
                                                              : 'text-slate-600 bg-slate-50'}"
                                                        >{req.status}</span
                                                    >
                                                {/if}
                                            </div>
                                        </div>
                                        <p
                                            class="text-xs text-txt-secondary mt-2 leading-relaxed"
                                        >
                                            {req.description}
                                        </p>

                                        <!-- Acceptance Criteria -->
                                        {#if req.acceptance_criteria?.length}
                                            <div
                                                class="mt-3 bg-white rounded-lg p-3 border border-surface-200/40"
                                            >
                                                <span
                                                    class="text-[9px] font-bold text-slate-500 uppercase tracking-[0.15em] block mb-1.5"
                                                    >Acceptance Criteria</span
                                                >
                                                <ul class="space-y-1">
                                                    {#each req.acceptance_criteria as ac}
                                                        <li
                                                            class="text-[11px] text-txt-secondary flex items-start gap-2"
                                                        >
                                                            <span
                                                                class="text-emerald-500 mt-0.5"
                                                                >✓</span
                                                            >
                                                            {ac}
                                                        </li>
                                                    {/each}
                                                </ul>
                                            </div>
                                        {/if}

                                        <!-- Meta row -->
                                        <div
                                            class="flex flex-wrap items-center gap-3 mt-3 pt-2 border-t border-surface-200/40"
                                        >
                                            {#if req.raised_by}
                                                <span
                                                    class="text-[10px] text-txt-faint"
                                                    >👤 {req.raised_by}</span
                                                >
                                            {/if}
                                            {#if req.dependencies?.length}
                                                <span
                                                    class="text-[10px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full"
                                                    >🔗 Depends on: {req.dependencies.join(
                                                        ", ",
                                                    )}</span
                                                >
                                            {/if}
                                            {#if req.risk}
                                                <span
                                                    class="text-[10px] text-red-600 bg-red-50 px-2 py-0.5 rounded-full"
                                                    >⚠️ {req.risk}</span
                                                >
                                            {/if}
                                        </div>

                                        <!-- Implementation Notes -->
                                        {#if req.implementation_notes}
                                            <p
                                                class="text-[10px] text-indigo-600 bg-indigo-50 rounded-md px-3 py-1.5 mt-2"
                                            >
                                                💡 {req.implementation_notes}
                                            </p>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Non-Functional Requirements -->
                    {#if reqData.non_functional_requirements?.length}
                        <div class="mb-6">
                            <div class="flex items-center gap-2 mb-3">
                                <span
                                    class="text-[10px] font-bold text-purple-600 uppercase tracking-[0.15em]"
                                    >Non-Functional Requirements</span
                                >
                                <span
                                    class="text-[10px] font-medium text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full"
                                    >{reqData.non_functional_requirements
                                        .length}</span
                                >
                            </div>
                            <div class="grid md:grid-cols-2 gap-3">
                                {#each reqData.non_functional_requirements as nfr}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60 hover:border-purple-300/60 transition-colors"
                                    >
                                        <div
                                            class="flex items-start justify-between gap-2 mb-1.5"
                                        >
                                            <div>
                                                <span
                                                    class="text-[10px] font-mono text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded mr-2"
                                                    >{nfr.id}</span
                                                >
                                                <span
                                                    class="text-sm font-semibold text-txt-primary"
                                                    >{nfr.title}</span
                                                >
                                            </div>
                                            <span
                                                class="text-[10px] text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full shrink-0"
                                                >{nfr.category}</span
                                            >
                                        </div>
                                        <p
                                            class="text-xs text-txt-secondary mt-1.5 leading-relaxed"
                                        >
                                            {nfr.description}
                                        </p>
                                        {#if nfr.measurable_criteria}
                                            <p
                                                class="text-[10px] text-emerald-700 bg-emerald-50 rounded px-2 py-1 mt-2"
                                            >
                                                📏 {nfr.measurable_criteria}
                                            </p>
                                        {/if}
                                        {#if nfr.impact}
                                            <p
                                                class="text-[10px] text-red-600 mt-1.5"
                                            >
                                                ⚠️ Impact: {nfr.impact}
                                            </p>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- User Stories -->
                    {#if reqData.user_stories?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-blue-600 uppercase tracking-[0.15em] block mb-3"
                                >User Stories</span
                            >
                            <div class="space-y-2">
                                {#each reqData.user_stories as story}
                                    <div
                                        class="bg-blue-50/50 rounded-xl p-4 border border-blue-100"
                                    >
                                        <p
                                            class="text-sm text-blue-900 italic font-medium"
                                        >
                                            "{typeof story === "string"
                                                ? story
                                                : story.story}"
                                        </p>
                                        {#if story.acceptance_criteria?.length}
                                            <div
                                                class="mt-2 pt-2 border-t border-blue-100"
                                            >
                                                <span
                                                    class="text-[9px] font-bold text-blue-500 uppercase tracking-[0.15em] block mb-1"
                                                    >Acceptance Criteria</span
                                                >
                                                {#each story.acceptance_criteria as ac}
                                                    <p
                                                        class="text-[11px] text-blue-700 flex items-start gap-1.5"
                                                    >
                                                        <span
                                                            class="text-blue-400"
                                                            >✓</span
                                                        >
                                                        {ac}
                                                    </p>
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Risks -->
                    {#if reqData.risks?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-red-600 uppercase tracking-[0.15em] block mb-3"
                                >Risk Assessment</span
                            >
                            <div class="space-y-2">
                                {#each reqData.risks as risk}
                                    <div
                                        class="bg-red-50/50 rounded-xl p-4 border border-red-100"
                                    >
                                        <div
                                            class="flex items-start justify-between gap-3"
                                        >
                                            <p
                                                class="text-sm text-txt-primary font-medium"
                                            >
                                                {risk.risk}
                                            </p>
                                            <div class="flex gap-1.5 shrink-0">
                                                <span
                                                    class="text-[9px] font-semibold px-2 py-0.5 rounded-full
                                                    {risk.likelihood === 'high'
                                                        ? 'text-red-700 bg-red-100'
                                                        : risk.likelihood ===
                                                            'medium'
                                                          ? 'text-amber-700 bg-amber-100'
                                                          : 'text-green-700 bg-green-100'}"
                                                >
                                                    L: {risk.likelihood}
                                                </span>
                                                <span
                                                    class="text-[9px] font-semibold px-2 py-0.5 rounded-full
                                                    {risk.impact === 'high'
                                                        ? 'text-red-700 bg-red-100'
                                                        : risk.impact ===
                                                            'medium'
                                                          ? 'text-amber-700 bg-amber-100'
                                                          : 'text-green-700 bg-green-100'}"
                                                >
                                                    I: {risk.impact}
                                                </span>
                                            </div>
                                        </div>
                                        {#if risk.mitigation}
                                            <p
                                                class="text-[11px] text-emerald-700 mt-1.5"
                                            >
                                                🛡️ Mitigation: {risk.mitigation}
                                            </p>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Constraints, Assumptions, Open Questions grid -->
                    <div class="grid md:grid-cols-3 gap-4">
                        {#if reqData.constraints?.length}
                            <div
                                class="bg-amber-50/50 rounded-xl p-4 border border-amber-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-amber-600 uppercase tracking-[0.15em] block mb-2"
                                    >Constraints</span
                                >
                                <ul class="space-y-2">
                                    {#each reqData.constraints as c}
                                        <li class="text-xs text-txt-secondary">
                                            <div class="flex items-start gap-2">
                                                <span
                                                    class="text-amber-500 mt-0.5 text-[8px]"
                                                    >●</span
                                                >
                                                <div>
                                                    <p>
                                                        {typeof c === "string"
                                                            ? c
                                                            : c.constraint}
                                                    </p>
                                                    {#if c.type}<span
                                                            class="text-[9px] text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded mt-1 inline-block"
                                                            >{c.type}</span
                                                        >{/if}
                                                </div>
                                            </div>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                        {#if reqData.assumptions?.length}
                            <div
                                class="bg-indigo-50/50 rounded-xl p-4 border border-indigo-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-indigo-600 uppercase tracking-[0.15em] block mb-2"
                                    >Assumptions</span
                                >
                                <ul class="space-y-1.5">
                                    {#each reqData.assumptions as a}
                                        <li
                                            class="text-xs text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-indigo-400 mt-0.5 text-[8px]"
                                                >●</span
                                            >
                                            {a}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                        {#if reqData.open_questions?.length}
                            <div
                                class="bg-sky-50/50 rounded-xl p-4 border border-sky-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-sky-600 uppercase tracking-[0.15em] block mb-2"
                                    >Open Questions</span
                                >
                                <ul class="space-y-2">
                                    {#each reqData.open_questions as q}
                                        <li class="text-xs text-txt-secondary">
                                            <p class="font-medium">
                                                {typeof q === "string"
                                                    ? q
                                                    : q.question}
                                            </p>
                                            {#if q.raised_by}
                                                <p
                                                    class="text-[10px] text-txt-faint mt-0.5"
                                                >
                                                    Asked by: {q.raised_by}
                                                </p>
                                            {/if}
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
                            Generate comprehensive meeting minutes with
                            technical details, decisions, and stakeholder
                            impact.
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
                            Click "Generate Docs" to create comprehensive
                            meeting minutes.
                        </p>
                        <p class="text-xs text-txt-faint mt-1">
                            This is optional — use for meetings that need formal
                            documentation.
                        </p>
                    </div>
                {:else}
                    <!-- Executive Summary -->
                    {#if docData.executive_summary}
                        <div
                            class="mb-6 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl p-5 border border-emerald-200/60"
                        >
                            <span
                                class="text-[10px] font-bold text-emerald-700 uppercase tracking-[0.15em] block mb-2"
                                >Executive Summary</span
                            >
                            <p class="text-sm text-emerald-900 leading-relaxed">
                                {docData.executive_summary}
                            </p>
                        </div>
                    {/if}

                    <!-- Attendees + Objective row -->
                    <div class="grid md:grid-cols-2 gap-4 mb-6">
                        {#if docData.attendees?.length}
                            <div
                                class="bg-surface-50 rounded-xl p-4 border border-surface-200/60"
                            >
                                <span
                                    class="text-[10px] font-bold text-blue-600 uppercase tracking-[0.15em] block mb-2"
                                    >Attendees</span
                                >
                                <div class="space-y-1.5">
                                    {#each docData.attendees as person}
                                        <div class="flex items-center gap-2">
                                            <div
                                                class="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-[10px] font-bold text-blue-700"
                                            >
                                                {(person.name || "?")
                                                    .charAt(0)
                                                    .toUpperCase()}
                                            </div>
                                            <div>
                                                <span
                                                    class="text-sm font-medium text-txt-primary"
                                                    >{person.name}</span
                                                >
                                                {#if person.role}
                                                    <span
                                                        class="text-[10px] text-txt-faint ml-1.5"
                                                        >— {person.role}</span
                                                    >
                                                {/if}
                                            </div>
                                        </div>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                        {#if docData.objective}
                            <div
                                class="bg-emerald-50/50 rounded-xl p-4 border border-emerald-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-1.5"
                                    >Meeting Objective</span
                                >
                                <p
                                    class="text-sm text-txt-primary leading-relaxed"
                                >
                                    {docData.objective}
                                </p>
                            </div>
                        {/if}
                    </div>

                    <!-- Topics Discussed -->
                    {#if docData.topics_discussed?.length}
                        <div class="mb-6">
                            <div class="flex items-center gap-2 mb-3">
                                <span
                                    class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em]"
                                    >Topics Discussed</span
                                >
                                <span
                                    class="text-[10px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full"
                                    >{docData.topics_discussed.length}</span
                                >
                            </div>
                            <div class="space-y-3">
                                {#each docData.topics_discussed as topic, i}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60 hover:border-emerald-300/60 transition-colors"
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
                                            class="text-xs text-txt-secondary mt-2 leading-relaxed"
                                        >
                                            {topic.summary}
                                        </p>

                                        {#if topic.key_points?.length}
                                            <div class="mt-2 ml-1">
                                                {#each topic.key_points as kp}
                                                    <p
                                                        class="text-[11px] text-txt-secondary flex items-start gap-2 mt-1"
                                                    >
                                                        <span
                                                            class="text-emerald-400 mt-0.5"
                                                            >•</span
                                                        >
                                                        {kp}
                                                    </p>
                                                {/each}
                                            </div>
                                        {/if}

                                        <div
                                            class="flex flex-wrap items-center gap-3 mt-2 pt-2 border-t border-surface-200/40"
                                        >
                                            {#if topic.speakers_involved?.length}
                                                <span
                                                    class="text-[10px] text-txt-faint"
                                                    >👥 {topic.speakers_involved.join(
                                                        ", ",
                                                    )}</span
                                                >
                                            {/if}
                                            {#if topic.outcome}
                                                <span
                                                    class="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full"
                                                    >✅ {topic.outcome}</span
                                                >
                                            {/if}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Technical Details -->
                    {#if docData.technical_details?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-indigo-600 uppercase tracking-[0.15em] block mb-3"
                                >Technical Details</span
                            >
                            <div class="space-y-3">
                                {#each docData.technical_details as tech}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60 hover:border-indigo-300/60 transition-colors"
                                    >
                                        <p
                                            class="text-sm font-semibold text-txt-primary"
                                        >
                                            {tech.area}
                                        </p>
                                        <p
                                            class="text-xs text-txt-secondary mt-1.5 leading-relaxed"
                                        >
                                            {tech.details}
                                        </p>
                                        {#if tech.implementation_approach}
                                            <p
                                                class="text-[10px] text-indigo-700 bg-indigo-50 rounded-md px-3 py-1.5 mt-2"
                                            >
                                                🔧 {tech.implementation_approach}
                                            </p>
                                        {/if}
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
                                class="text-[10px] font-bold text-violet-600 uppercase tracking-[0.15em] block mb-3"
                                >Decisions & Rationale</span
                            >
                            <div class="space-y-3">
                                {#each docData.decisions_and_rationale as d}
                                    <div
                                        class="bg-surface-50 rounded-xl p-4 border border-surface-200/60 hover:border-violet-300/60 transition-colors"
                                    >
                                        <p
                                            class="text-sm font-semibold text-txt-primary"
                                        >
                                            {d.decision}
                                        </p>
                                        <p
                                            class="text-xs text-txt-secondary mt-1.5 leading-relaxed"
                                        >
                                            <span
                                                class="font-medium text-txt-muted"
                                                >Why:</span
                                            >
                                            {d.rationale || "Not specified"}
                                        </p>
                                        {#if d.alternatives_discussed}
                                            <p
                                                class="text-xs text-txt-faint mt-1"
                                            >
                                                <span class="font-medium"
                                                    >Alternatives:</span
                                                >
                                                {d.alternatives_discussed}
                                            </p>
                                        {/if}
                                        <div
                                            class="flex flex-wrap items-center gap-3 mt-2 pt-2 border-t border-surface-200/40"
                                        >
                                            {#if d.decided_by}
                                                <span
                                                    class="text-[10px] text-txt-faint"
                                                    >👤 {d.decided_by}</span
                                                >
                                            {/if}
                                            {#if d.impact}
                                                <span
                                                    class="text-[10px] text-violet-700 bg-violet-50 px-2 py-0.5 rounded-full"
                                                    >📊 {d.impact}</span
                                                >
                                            {/if}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Agreements & Disagreements -->
                    <div class="grid md:grid-cols-2 gap-4 mb-6">
                        {#if docData.agreements?.length}
                            <div
                                class="bg-green-50/50 rounded-xl p-4 border border-green-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-green-600 uppercase tracking-[0.15em] block mb-2"
                                    >✅ Agreements</span
                                >
                                <ul class="space-y-1.5">
                                    {#each docData.agreements as a}
                                        <li
                                            class="text-xs text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-green-500 mt-0.5 text-[8px]"
                                                >●</span
                                            >
                                            {a}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                        {#if docData.disagreements?.length}
                            <div
                                class="bg-orange-50/50 rounded-xl p-4 border border-orange-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-orange-600 uppercase tracking-[0.15em] block mb-2"
                                    >⚡ Disagreements</span
                                >
                                <ul class="space-y-2">
                                    {#each docData.disagreements as dis}
                                        <li class="text-xs text-txt-secondary">
                                            <p class="font-medium">
                                                {dis.topic}
                                            </p>
                                            {#if dis.parties?.length}
                                                <p
                                                    class="text-[10px] text-txt-faint mt-0.5"
                                                >
                                                    Between: {dis.parties.join(
                                                        " vs ",
                                                    )}
                                                </p>
                                            {/if}
                                            {#if dis.resolution}
                                                <p
                                                    class="text-[10px] text-green-700 mt-0.5"
                                                >
                                                    Resolution: {dis.resolution}
                                                </p>
                                            {/if}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    </div>

                    <!-- Next Steps -->
                    {#if docData.next_steps?.length}
                        <div class="mb-6">
                            <span
                                class="text-[10px] font-bold text-emerald-600 uppercase tracking-[0.15em] block mb-3"
                                >Next Steps</span
                            >
                            <div class="space-y-2">
                                {#each docData.next_steps as step}
                                    <div
                                        class="bg-surface-50 rounded-lg p-3 border border-surface-200/60 flex items-start justify-between gap-3"
                                    >
                                        <div class="flex items-start gap-2">
                                            <span
                                                class="text-emerald-500 mt-0.5 text-[8px]"
                                                >●</span
                                            >
                                            <p
                                                class="text-sm text-txt-secondary"
                                            >
                                                {typeof step === "string"
                                                    ? step
                                                    : step.action}
                                            </p>
                                        </div>
                                        {#if step.owner || step.deadline}
                                            <div
                                                class="flex items-center gap-2 shrink-0"
                                            >
                                                {#if step.owner}
                                                    <span
                                                        class="text-[10px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full"
                                                        >{step.owner}</span
                                                    >
                                                {/if}
                                                {#if step.deadline}
                                                    <span
                                                        class="text-[10px] text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full"
                                                        >{step.deadline}</span
                                                    >
                                                {/if}
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Stakeholder Impact + Parking Lot + Glossary -->
                    <div class="grid md:grid-cols-3 gap-4">
                        {#if docData.stakeholder_impact?.length}
                            <div
                                class="bg-purple-50/50 rounded-xl p-4 border border-purple-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-purple-600 uppercase tracking-[0.15em] block mb-2"
                                    >Stakeholder Impact</span
                                >
                                <ul class="space-y-2">
                                    {#each docData.stakeholder_impact as si}
                                        <li class="text-xs text-txt-secondary">
                                            <p
                                                class="font-medium text-purple-800"
                                            >
                                                {si.stakeholder}
                                            </p>
                                            <p
                                                class="text-[11px] text-txt-faint mt-0.5"
                                            >
                                                {si.impact}
                                            </p>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                        {#if docData.parking_lot?.length}
                            <div
                                class="bg-amber-50/50 rounded-xl p-4 border border-amber-100"
                            >
                                <span
                                    class="text-[10px] font-bold text-amber-600 uppercase tracking-[0.15em] block mb-2"
                                    >Parking Lot</span
                                >
                                <ul class="space-y-1.5">
                                    {#each docData.parking_lot as item}
                                        <li
                                            class="text-xs text-txt-secondary flex items-start gap-2"
                                        >
                                            <span
                                                class="text-amber-500 mt-0.5 text-[8px]"
                                                >●</span
                                            >
                                            {item}
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                        {#if docData.glossary?.length}
                            <div
                                class="bg-slate-50/50 rounded-xl p-4 border border-slate-200"
                            >
                                <span
                                    class="text-[10px] font-bold text-slate-600 uppercase tracking-[0.15em] block mb-2"
                                    >Glossary</span
                                >
                                <dl class="space-y-1.5">
                                    {#each docData.glossary as g}
                                        <div>
                                            <dt
                                                class="text-xs font-semibold text-txt-primary"
                                            >
                                                {g.term}
                                            </dt>
                                            <dd
                                                class="text-[11px] text-txt-faint"
                                            >
                                                {g.definition}
                                            </dd>
                                        </div>
                                    {/each}
                                </dl>
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

        <!-- ─── Quick Stats (computed from transcript) ─── -->
        {#if activeTab === "speaker" && segments.length > 0}
            {@const totalDur =
                segments.length > 0
                    ? Math.max(...segments.map((s) => s.end))
                    : 0}
            {@const totalWords = segments.reduce(
                (sum, s) => sum + s.text.split(/\s+/).filter((w) => w).length,
                0,
            )}
            <div class="grid grid-cols-3 gap-3 mt-6">
                <div
                    class="bg-white border border-surface-200 rounded-xl p-4 text-center"
                >
                    <span class="text-2xl font-extrabold text-cyan-600"
                        >{Object.keys(speakers).length}</span
                    >
                    <p
                        class="text-[10px] text-txt-faint uppercase tracking-wider mt-1"
                    >
                        Speakers
                    </p>
                </div>
                <div
                    class="bg-white border border-surface-200 rounded-xl p-4 text-center"
                >
                    <span class="text-2xl font-extrabold text-blue-600"
                        >{Math.floor(totalDur / 60)}m {Math.round(
                            totalDur % 60,
                        )}s</span
                    >
                    <p
                        class="text-[10px] text-txt-faint uppercase tracking-wider mt-1"
                    >
                        Total Duration
                    </p>
                </div>
                <div
                    class="bg-white border border-surface-200 rounded-xl p-4 text-center"
                >
                    <span class="text-2xl font-extrabold text-purple-600"
                        >{totalWords.toLocaleString()}</span
                    >
                    <p
                        class="text-[10px] text-txt-faint uppercase tracking-wider mt-1"
                    >
                        Total Words
                    </p>
                </div>
            </div>
        {/if}

        <!-- ─── Speaker Report Cards (merged into Speaker Analysis tab) ─── -->
        {#if activeTab === "speaker"}
            <div class="max-w-5xl space-y-6 mt-8">
                <hr class="border-surface-200" />
                <div class="flex items-center justify-between">
                    <p
                        class="text-[11px] font-semibold text-txt-faint uppercase tracking-[0.15em]"
                    >
                        Speaker Report Cards
                    </p>
                    <button
                        class="btn-secondary text-sm"
                        on:click={async () => {
                            loadingSpeakerReport = true;
                            try {
                                speakerReportData = await get(
                                    api.speakerReport(meetingId),
                                );
                            } catch (e) {
                                toasts.error("Failed to load speaker report");
                            } finally {
                                loadingSpeakerReport = false;
                            }
                        }}
                        disabled={loadingSpeakerReport}
                    >
                        {#if loadingSpeakerReport}
                            <Loader2 size={14} class="animate-spin" /> Loading…
                        {:else}
                            <UserCheck size={14} />
                            {speakerReportData
                                ? "Refresh"
                                : "Generate Report Cards"}
                        {/if}
                    </button>
                </div>

                {#if !speakerReportData}
                    <div
                        class="bg-white border border-surface-200 rounded-2xl p-10 text-center"
                    >
                        <div
                            class="w-12 h-12 mx-auto rounded-xl bg-teal-100 flex items-center justify-center mb-4"
                        >
                            <UserCheck size={22} class="text-teal-600" />
                        </div>
                        <h3
                            class="text-base font-semibold text-txt-primary mb-1"
                        >
                            Speaker Report Cards
                        </h3>
                        <p class="text-sm text-txt-muted max-w-sm mx-auto">
                            Click "Generate Report Cards" to see comprehensive
                            per-speaker scorecards with role classification,
                            sentiment, and more.
                        </p>
                    </div>
                {:else}
                    <!-- Card Grid -->
                    <div
                        class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5"
                    >
                        {#each speakerReportData.speakers as s, i}
                            {@const roleColors = {
                                "Decision Maker": {
                                    bg: "bg-amber-50",
                                    text: "text-amber-700",
                                    border: "border-amber-200",
                                    icon: "🎯",
                                },
                                Presenter: {
                                    bg: "bg-blue-50",
                                    text: "text-blue-700",
                                    border: "border-blue-200",
                                    icon: "🎤",
                                },
                                Challenger: {
                                    bg: "bg-purple-50",
                                    text: "text-purple-700",
                                    border: "border-purple-200",
                                    icon: "❓",
                                },
                                Doer: {
                                    bg: "bg-emerald-50",
                                    text: "text-emerald-700",
                                    border: "border-emerald-200",
                                    icon: "✅",
                                },
                                Observer: {
                                    bg: "bg-slate-50",
                                    text: "text-slate-600",
                                    border: "border-slate-200",
                                    icon: "👂",
                                },
                                Contributor: {
                                    bg: "bg-cyan-50",
                                    text: "text-cyan-700",
                                    border: "border-cyan-200",
                                    icon: "💬",
                                },
                            }}
                            {@const rc =
                                roleColors[s.role] || roleColors["Contributor"]}
                            {@const sentColor =
                                s.sentiment.dominant === "positive"
                                    ? "#10b981"
                                    : s.sentiment.dominant === "negative"
                                      ? "#ef4444"
                                      : "#64748b"}
                            {@const sentEmoji =
                                s.sentiment.dominant === "positive"
                                    ? "😊"
                                    : s.sentiment.dominant === "negative"
                                      ? "😟"
                                      : "😐"}
                            <div
                                class="bg-white border border-surface-200 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow"
                            >
                                <!-- Header -->
                                <div
                                    class="p-4 pb-3 border-b border-surface-100"
                                >
                                    <div class="flex items-center gap-3">
                                        <div
                                            class="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold"
                                            style="background-color: {getColor(
                                                s.speaker_id,
                                            )}"
                                        >
                                            {s.display_name
                                                .charAt(0)
                                                .toUpperCase()}
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <h4
                                                class="text-sm font-bold text-txt-primary truncate"
                                            >
                                                {s.display_name}
                                            </h4>
                                            <span
                                                class="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border {rc.bg} {rc.text} {rc.border}"
                                            >
                                                {rc.icon}
                                                {s.role}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <!-- Stats Grid -->
                                <div class="p-4 space-y-3">
                                    <!-- Talk Time -->
                                    <div>
                                        <div
                                            class="flex justify-between text-[11px] mb-1"
                                        >
                                            <span
                                                class="text-txt-faint font-medium"
                                                >🎤 Talk Time</span
                                            >
                                            <span
                                                class="font-bold text-txt-primary"
                                                >{s.talk_time_percent}%</span
                                            >
                                        </div>
                                        <div
                                            class="w-full bg-surface-100 rounded-full h-2"
                                        >
                                            <div
                                                class="h-full rounded-full transition-all duration-500"
                                                style="width: {s.talk_time_percent}%; background-color: {getColor(
                                                    s.speaker_id,
                                                )}"
                                            ></div>
                                        </div>
                                        <span class="text-[9px] text-txt-faint"
                                            >{Math.floor(
                                                s.talk_time_seconds / 60,
                                            )}m {Math.round(
                                                s.talk_time_seconds % 60,
                                            )}s · {s.words_per_minute} WPM</span
                                        >
                                    </div>

                                    <!-- Key Metrics Row -->
                                    <div class="grid grid-cols-3 gap-2">
                                        <div
                                            class="bg-surface-50 rounded-lg p-2 text-center"
                                        >
                                            <span
                                                class="text-lg font-extrabold text-blue-600"
                                                >{s.word_count}</span
                                            >
                                            <p
                                                class="text-[9px] text-txt-faint uppercase"
                                            >
                                                Words
                                            </p>
                                        </div>
                                        <div
                                            class="bg-surface-50 rounded-lg p-2 text-center"
                                        >
                                            <span
                                                class="text-lg font-extrabold text-purple-600"
                                                >{s.questions_asked}</span
                                            >
                                            <p
                                                class="text-[9px] text-txt-faint uppercase"
                                            >
                                                Questions
                                            </p>
                                        </div>
                                        <div
                                            class="bg-surface-50 rounded-lg p-2 text-center"
                                        >
                                            <span
                                                class="text-lg font-extrabold text-amber-600"
                                                >{s.interruptions}</span
                                            >
                                            <p
                                                class="text-[9px] text-txt-faint uppercase"
                                            >
                                                Interrupts
                                            </p>
                                        </div>
                                    </div>

                                    <!-- Action Items & Decisions -->
                                    <div class="grid grid-cols-2 gap-2">
                                        <div
                                            class="bg-emerald-50/50 rounded-lg p-2 border border-emerald-100"
                                        >
                                            <span
                                                class="text-[10px] text-emerald-700 font-semibold"
                                                >📋 Action Items</span
                                            >
                                            <p
                                                class="text-lg font-extrabold text-emerald-600"
                                            >
                                                {s.action_items_assigned}
                                            </p>
                                        </div>
                                        <div
                                            class="bg-amber-50/50 rounded-lg p-2 border border-amber-100"
                                        >
                                            <span
                                                class="text-[10px] text-amber-700 font-semibold"
                                                >⚡ Decisions</span
                                            >
                                            <p
                                                class="text-lg font-extrabold text-amber-600"
                                            >
                                                {s.decisions_attributed}
                                            </p>
                                        </div>
                                    </div>

                                    <!-- Sentiment -->
                                    <div class="flex items-center gap-2">
                                        <span class="text-sm">{sentEmoji}</span>
                                        <div class="flex-1">
                                            <span
                                                class="text-[10px] font-semibold capitalize"
                                                style="color: {sentColor}"
                                                >{s.sentiment.dominant}</span
                                            >
                                            <div
                                                class="flex gap-0.5 mt-1 h-1.5 rounded-full overflow-hidden bg-surface-100"
                                            >
                                                {#if s.sentiment.positive + s.sentiment.negative + s.sentiment.neutral > 0}
                                                    <div
                                                        class="bg-emerald-400 h-full"
                                                        style="width: {(s
                                                            .sentiment
                                                            .positive /
                                                            (s.sentiment
                                                                .positive +
                                                                s.sentiment
                                                                    .negative +
                                                                s.sentiment
                                                                    .neutral)) *
                                                            100}%"
                                                    ></div>
                                                    <div
                                                        class="bg-slate-300 h-full"
                                                        style="width: {(s
                                                            .sentiment.neutral /
                                                            (s.sentiment
                                                                .positive +
                                                                s.sentiment
                                                                    .negative +
                                                                s.sentiment
                                                                    .neutral)) *
                                                            100}%"
                                                    ></div>
                                                    <div
                                                        class="bg-red-400 h-full"
                                                        style="width: {(s
                                                            .sentiment
                                                            .negative /
                                                            (s.sentiment
                                                                .positive +
                                                                s.sentiment
                                                                    .negative +
                                                                s.sentiment
                                                                    .neutral)) *
                                                            100}%"
                                                    ></div>
                                                {/if}
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Topics -->
                                    {#if s.topics.length > 0}
                                        <div>
                                            <span
                                                class="text-[10px] text-txt-faint font-medium"
                                                >🏷️ Topics</span
                                            >
                                            <div
                                                class="flex flex-wrap gap-1 mt-1"
                                            >
                                                {#each s.topics.slice(0, 3) as topic}
                                                    <span
                                                        class="text-[9px] px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded-full border border-indigo-100 truncate max-w-[120px]"
                                                        >{topic}</span
                                                    >
                                                {/each}
                                                {#if s.topics.length > 3}
                                                    <span
                                                        class="text-[9px] px-1.5 py-0.5 bg-surface-100 text-txt-faint rounded-full"
                                                        >+{s.topics.length -
                                                            3}</span
                                                    >
                                                {/if}
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- ═══════════════════ KEYWORD CLOUD VIEW ═══════════════════ -->
        {#if activeTab === "keywords"}
            <div class="max-w-4xl space-y-6">
                <!-- Load Button -->
                <div class="flex items-center justify-between">
                    <p
                        class="text-[11px] font-semibold text-txt-faint uppercase tracking-[0.15em]"
                    >
                        Keyword Cloud
                    </p>
                    <button
                        class="btn-secondary text-sm"
                        on:click={async () => {
                            loadingKeywords = true;
                            try {
                                keywordsData = await get(
                                    api.keywords(meetingId),
                                );
                            } catch (e) {
                                toasts.error("Failed to load keywords");
                            } finally {
                                loadingKeywords = false;
                            }
                        }}
                        disabled={loadingKeywords}
                    >
                        {#if loadingKeywords}
                            <Loader2 size={14} class="animate-spin" /> Loading…
                        {:else}
                            <Tag size={14} />
                            {keywordsData ? "Refresh" : "Extract Keywords"}
                        {/if}
                    </button>
                </div>

                {#if !keywordsData}
                    <div
                        class="bg-white border border-surface-200 rounded-2xl p-10 text-center"
                    >
                        <div
                            class="w-12 h-12 mx-auto rounded-xl bg-orange-100 flex items-center justify-center mb-4"
                        >
                            <Tag size={22} class="text-orange-600" />
                        </div>
                        <h3
                            class="text-base font-semibold text-txt-primary mb-1"
                        >
                            Keyword Cloud
                        </h3>
                        <p class="text-sm text-txt-muted max-w-sm mx-auto">
                            Click "Extract Keywords" to see the most frequently
                            discussed terms in this meeting.
                        </p>
                    </div>
                {:else}
                    <!-- Stats Row -->
                    <div class="flex items-center gap-4">
                        <div
                            class="bg-white border border-surface-200 rounded-xl px-4 py-3 flex items-center gap-2"
                        >
                            <span class="text-lg font-extrabold text-orange-600"
                                >{keywordsData.total_unique_words}</span
                            >
                            <span
                                class="text-[11px] text-txt-faint uppercase tracking-wider"
                                >Unique Words</span
                            >
                        </div>
                        <div
                            class="bg-white border border-surface-200 rounded-xl px-4 py-3 flex items-center gap-2"
                        >
                            <span class="text-lg font-extrabold text-blue-600"
                                >{keywordsData.keywords.length}</span
                            >
                            <span
                                class="text-[11px] text-txt-faint uppercase tracking-wider"
                                >Top Keywords</span
                            >
                        </div>
                    </div>

                    <!-- Word Cloud -->
                    <div
                        class="bg-white border border-surface-200 rounded-2xl p-8"
                    >
                        <div
                            class="flex flex-wrap items-center justify-center gap-3"
                        >
                            {#each keywordsData.keywords as kw, i}
                                {@const hue = (i * 37) % 360}
                                {@const size = 12 + Math.round(kw.weight * 24)}
                                <span
                                    class="inline-block font-bold cursor-default transition-transform hover:scale-125 hover:-translate-y-1"
                                    style="font-size: {size}px; color: hsl({hue}, 70%, 45%); opacity: {0.5 +
                                        kw.weight * 0.5};"
                                    title="{kw.word}: {kw.count} occurrences"
                                >
                                    {kw.word}
                                </span>
                            {/each}
                        </div>
                    </div>

                    <!-- Top Keywords Bar Chart -->
                    <div
                        class="bg-white border border-surface-200 rounded-2xl p-6"
                    >
                        <span
                            class="text-[10px] font-bold text-orange-600 uppercase tracking-[0.15em] block mb-4"
                            >Top 15 Keywords by Frequency</span
                        >
                        <div class="space-y-2">
                            {#each keywordsData.keywords.slice(0, 15) as kw, i}
                                {@const hue = (i * 37) % 360}
                                <div class="flex items-center gap-3">
                                    <span
                                        class="w-24 text-[12px] font-semibold text-txt-primary text-right truncate"
                                        >{kw.word}</span
                                    >
                                    <div
                                        class="flex-1 bg-surface-100 rounded-full h-5 overflow-hidden"
                                    >
                                        <div
                                            class="h-full rounded-full flex items-center px-2 transition-all duration-500"
                                            style="width: {Math.max(
                                                kw.weight * 100,
                                                8,
                                            )}%; background-color: hsl({hue}, 70%, 50%);"
                                        >
                                            <span
                                                class="text-[10px] font-bold text-white"
                                                >{kw.count}</span
                                            >
                                        </div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        {/if}

        <!-- ══════════════ TOPICS TAB ══════════════ -->
        {#if activeTab === "topics"}
            <div class="max-w-4xl space-y-6">
                <!-- Load Button -->
                <div class="flex items-center justify-between">
                    <p
                        class="text-[11px] font-semibold text-txt-faint uppercase tracking-[0.15em]"
                    >
                        Topic Segmentation
                    </p>
                    <button
                        class="btn-secondary text-sm"
                        on:click={async () => {
                            loadingTopics = true;
                            try {
                                topicsData = await post(
                                    api.topics(meetingId),
                                    null,
                                    120000,
                                );
                            } catch (e) {
                                toasts.error("Failed to extract topics");
                            } finally {
                                loadingTopics = false;
                            }
                        }}
                        disabled={loadingTopics}
                    >
                        {#if loadingTopics}
                            <Loader2 size={14} class="animate-spin" /> Analyzing…
                        {:else}
                            <Layers size={14} />
                            {topicsData ? "Refresh" : "Extract Topics"}
                        {/if}
                    </button>
                </div>

                {#if !topicsData}
                    <div
                        class="bg-surface-50 border border-surface-200/60 rounded-2xl p-10 text-center"
                    >
                        <Layers
                            size={40}
                            class="mx-auto text-indigo-300 mb-3"
                        />
                        <p class="text-txt-secondary">
                            Click <strong>Extract Topics</strong> to identify what
                            was discussed when.
                        </p>
                    </div>
                {:else}
                    <!-- Stats Bar -->
                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-indigo-50 rounded-xl p-4 text-center">
                            <span class="text-2xl font-bold text-indigo-600"
                                >{topicsData.topic_count}</span
                            >
                            <p class="text-xs text-indigo-500 mt-1">
                                Topics Identified
                            </p>
                        </div>
                        <div class="bg-purple-50 rounded-xl p-4 text-center">
                            <span class="text-2xl font-bold text-purple-600"
                                >{formatDuration(
                                    segments.length > 0
                                        ? segments[segments.length - 1].end
                                        : 0,
                                )}</span
                            >
                            <p class="text-xs text-purple-500 mt-1">
                                Total Duration
                            </p>
                        </div>
                    </div>

                    <!-- Topic Timeline -->
                    <div class="relative">
                        <!-- Vertical line -->
                        <div
                            class="absolute left-6 top-0 bottom-0 w-0.5 bg-indigo-200"
                        ></div>

                        {#each topicsData.topics as topic, i}
                            {@const colors = [
                                "bg-indigo-500",
                                "bg-purple-500",
                                "bg-blue-500",
                                "bg-emerald-500",
                                "bg-amber-500",
                                "bg-rose-500",
                                "bg-cyan-500",
                                "bg-teal-500",
                            ]}
                            <div class="relative flex gap-4 pb-6">
                                <!-- Circle marker -->
                                <div
                                    class="relative z-10 flex-shrink-0 w-12 h-12 rounded-full {colors[
                                        i % colors.length
                                    ]} flex items-center justify-center text-white font-bold text-lg shadow-lg"
                                >
                                    {i + 1}
                                </div>

                                <!-- Topic Card -->
                                <div
                                    class="flex-1 bg-white border border-surface-200/60 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow"
                                >
                                    <div class="mb-2">
                                        <h3
                                            class="font-semibold text-txt-primary text-base"
                                        >
                                            {topic.title}
                                        </h3>
                                    </div>
                                    <p
                                        class="text-sm text-txt-secondary leading-relaxed mb-3"
                                    >
                                        {topic.summary}
                                    </p>
                                    {#if topic.speakers && topic.speakers.length > 0}
                                        <div class="flex flex-wrap gap-1.5">
                                            {#each topic.speakers as spk}
                                                <span
                                                    class="text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600"
                                                >
                                                    {displayName(spk)}
                                                </span>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- ═══════════════════ PUBLISH TAB ═══════════════════ -->
        {#if activeTab === "publish"}
            <div class="max-w-3xl space-y-6">
                <div>
                    <h2 class="text-lg font-bold text-txt-primary mb-1">
                        Publish Meeting
                    </h2>
                    <p class="text-sm text-txt-faint">
                        Push this meeting's data to external platforms.
                    </p>
                </div>

                <!-- Notion Card -->
                <div
                    class="bg-white rounded-2xl border border-surface-200 shadow-sm overflow-hidden"
                >
                    <div
                        class="bg-gradient-to-r from-gray-900 to-gray-800 px-6 py-4"
                    >
                        <div class="flex items-center gap-3">
                            <div
                                class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center"
                            >
                                <span class="text-xl">📝</span>
                            </div>
                            <div>
                                <h3 class="text-white font-bold text-base">
                                    Notion
                                </h3>
                                <p class="text-gray-400 text-xs">
                                    Create a rich Notion page with all meeting
                                    data
                                </p>
                            </div>
                        </div>
                    </div>
                    <div class="px-6 py-5">
                        <div class="text-xs text-txt-faint mb-4 space-y-1">
                            <p>
                                📋 Summary (EN + Hindi) · 👥 Speaker summaries ·
                                ✅ Action items
                            </p>
                            <p>
                                🏷️ Topics · 📊 Sentiment analysis · 👤 Speaker
                                list
                            </p>
                        </div>
                        {#if notionResult?.success}
                            <div
                                class="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 mb-4"
                            >
                                <Check size={16} class="text-emerald-600" />
                                <div class="flex-1">
                                    <span
                                        class="text-sm font-medium text-emerald-800"
                                        >Published to Notion</span
                                    >
                                    {#if notionResult.page_url}
                                        <a
                                            href={notionResult.page_url}
                                            target="_blank"
                                            rel="noopener"
                                            class="text-xs text-emerald-600 hover:underline flex items-center gap-1 mt-0.5"
                                        >
                                            Open page <ExternalLink size={11} />
                                        </a>
                                    {/if}
                                </div>
                            </div>
                        {/if}
                        <button
                            class="btn-primary text-sm w-full justify-center"
                            on:click={async () => {
                                pushingNotion = true;
                                notionResult = null;
                                try {
                                    notionResult = await post(
                                        api.notionPush(meetingId),
                                    );
                                    toasts.success("Published to Notion!");
                                } catch (err) {
                                    toasts.error(
                                        "Notion push failed: " + err.message,
                                    );
                                }
                                pushingNotion = false;
                            }}
                            disabled={pushingNotion}
                        >
                            {#if pushingNotion}
                                <Loader2 size={15} class="animate-spin" /> Pushing
                                to Notion…
                            {:else}
                                <Share2 size={15} /> Push to Notion
                            {/if}
                        </button>
                    </div>
                </div>

                <!-- Confluence Card -->
                <div
                    class="bg-white rounded-2xl border border-surface-200 shadow-sm overflow-hidden"
                >
                    <div
                        class="bg-gradient-to-r from-blue-700 to-blue-600 px-6 py-4"
                    >
                        <div class="flex items-center gap-3">
                            <div
                                class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center"
                            >
                                <span class="text-xl">🏢</span>
                            </div>
                            <div>
                                <h3 class="text-white font-bold text-base">
                                    Confluence
                                </h3>
                                <p class="text-blue-200 text-xs">
                                    Create a wiki page with Jira ticket links
                                </p>
                            </div>
                        </div>
                    </div>
                    <div class="px-6 py-5">
                        <div class="text-xs text-txt-faint mb-4 space-y-1">
                            <p>
                                📋 Summary · 👥 Speaker summaries · ✅ Action
                                items table
                            </p>
                            <p>
                                🏷️ Topics · 📊 Sentiment · 🔗 Linked Jira
                                tickets
                            </p>
                        </div>
                        {#if confluenceResult?.success}
                            <div
                                class="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 mb-4"
                            >
                                <Check size={16} class="text-blue-600" />
                                <div class="flex-1">
                                    <span
                                        class="text-sm font-medium text-blue-800"
                                        >Published to Confluence</span
                                    >
                                    {#if confluenceResult.page_url}
                                        <a
                                            href={confluenceResult.page_url}
                                            target="_blank"
                                            rel="noopener"
                                            class="text-xs text-blue-600 hover:underline flex items-center gap-1 mt-0.5"
                                        >
                                            Open page <ExternalLink size={11} />
                                        </a>
                                    {/if}
                                </div>
                            </div>
                        {/if}
                        <button
                            class="btn-primary text-sm w-full justify-center"
                            on:click={async () => {
                                pushingConfluence = true;
                                confluenceResult = null;
                                try {
                                    confluenceResult = await post(
                                        api.confluencePush(meetingId),
                                    );
                                    toasts.success("Published to Confluence!");
                                } catch (err) {
                                    toasts.error(
                                        "Confluence push failed: " +
                                            err.message,
                                    );
                                }
                                pushingConfluence = false;
                            }}
                            disabled={pushingConfluence}
                        >
                            {#if pushingConfluence}
                                <Loader2 size={15} class="animate-spin" /> Pushing
                                to Confluence…
                            {:else}
                                <Share2 size={15} /> Push to Confluence
                            {/if}
                        </button>
                    </div>
                </div>
            </div>
        {/if}

        <!-- ─── Full Report Tab ─── -->
        {#if activeTab === "fullReport"}
            <div class="max-w-3xl space-y-6">
                <div>
                    <h2 class="text-lg font-bold text-txt-primary mb-1">
                        Full Meeting Report
                    </h2>
                    <p class="text-sm text-txt-faint">
                        Generate a comprehensive PDF with all meeting insights.
                        Missing sections are auto-generated.
                    </p>
                </div>

                <!-- Report Content Card -->
                <div
                    class="bg-white rounded-2xl border border-surface-200 shadow-sm overflow-hidden"
                >
                    <div
                        class="bg-gradient-to-r from-cyan-600 to-blue-700 px-6 py-4"
                    >
                        <div class="flex items-center gap-3">
                            <div
                                class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center"
                            >
                                <FileText size={20} class="text-white" />
                            </div>
                            <div>
                                <h3 class="text-white font-bold text-base">
                                    Comprehensive Report PDF
                                </h3>
                                <p class="text-cyan-100 text-xs">
                                    All 7 sections auto-generated from your
                                    meeting
                                </p>
                            </div>
                        </div>
                    </div>

                    <div class="px-6 py-5 space-y-4">
                        <!-- Sections included -->
                        <div
                            class="grid grid-cols-2 gap-2 text-xs text-txt-faint"
                        >
                            <span>📝 Meeting Summary</span>
                            <span>👥 Speaker Contributions</span>
                            <span>✅ Action Items</span>
                            <span>🏛️ Key Decisions</span>
                            <span>📋 Requirements</span>
                            <span>🎯 Meeting Objective</span>
                            <span class="col-span-2">📌 Next Steps</span>
                        </div>

                        {#if reportResult}
                            <div
                                class="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3"
                            >
                                <div class="flex items-center gap-2">
                                    <Check size={16} class="text-emerald-600" />
                                    <span
                                        class="text-sm font-semibold text-emerald-800"
                                        >Report Ready</span
                                    >
                                </div>
                                {#if reportResult.generated_sections?.length > 0}
                                    <p class="text-xs text-emerald-700 mt-1">
                                        Auto-generated: {reportResult.generated_sections.join(
                                            ", ",
                                        )}
                                    </p>
                                {:else}
                                    <p class="text-xs text-emerald-700 mt-1">
                                        All sections loaded from cache.
                                    </p>
                                {/if}
                            </div>
                        {/if}

                        <!-- Action buttons -->
                        <div class="flex gap-3">
                            {#if !reportReady}
                                <!-- Generate Button -->
                                <button
                                    class="btn-primary text-sm flex-1 justify-center"
                                    on:click={async () => {
                                        generatingReport = true;
                                        reportResult = null;
                                        try {
                                            reportResult = await post(
                                                api.fullReportGenerate(
                                                    meetingId,
                                                ),
                                                {},
                                                300000,
                                            );
                                            reportReady = true;
                                            toasts.success(
                                                "Full report generated!",
                                            );
                                        } catch (err) {
                                            toasts.error(
                                                "Report generation failed: " +
                                                    err.message,
                                            );
                                        }
                                        generatingReport = false;
                                    }}
                                    disabled={generatingReport}
                                >
                                    {#if generatingReport}
                                        <Loader2
                                            size={15}
                                            class="animate-spin"
                                        /> Generating Report…
                                    {:else}
                                        <Sparkles size={15} /> Generate Report
                                    {/if}
                                </button>
                            {:else}
                                <!-- Download Button -->
                                <a
                                    href={api.fullReport(meetingId)}
                                    target="_blank"
                                    class="btn-primary text-sm flex-1 justify-center inline-flex items-center gap-2"
                                >
                                    <Download size={15} /> Download PDF
                                </a>

                                <!-- Email Button -->
                                <button
                                    class="btn-secondary text-sm flex-1 justify-center"
                                    on:click={() => {
                                        showReportEmailModal = true;
                                    }}
                                >
                                    <Mail size={15} /> Send Email
                                </button>
                            {/if}
                        </div>

                        {#if reportReady}
                            <button
                                class="text-xs text-txt-faint hover:text-txt-muted underline"
                                on:click={async () => {
                                    generatingReport = true;
                                    reportResult = null;
                                    reportReady = false;
                                    try {
                                        reportResult = await post(
                                            api.fullReportGenerate(meetingId),
                                            {},
                                            300000,
                                        );
                                        reportReady = true;
                                        toasts.success("Report regenerated!");
                                    } catch (err) {
                                        toasts.error(
                                            "Regeneration failed: " +
                                                err.message,
                                        );
                                    }
                                    generatingReport = false;
                                }}
                                disabled={generatingReport}
                            >
                                {#if generatingReport}
                                    Regenerating…
                                {:else}
                                    ↻ Regenerate
                                {/if}
                            </button>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- Email Modal -->
            {#if showReportEmailModal}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                    class="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center"
                    on:click|self={() => {
                        showReportEmailModal = false;
                    }}
                >
                    <div
                        class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4"
                    >
                        <h3 class="text-lg font-bold text-txt-primary">
                            Send Full Report
                        </h3>
                        <p class="text-sm text-txt-faint">
                            Enter recipient email addresses, separated by
                            commas.
                        </p>
                        <input
                            type="text"
                            bind:value={reportEmailInput}
                            placeholder="email@example.com, another@team.com"
                            class="w-full border border-surface-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-400"
                        />
                        <div class="flex justify-end gap-3">
                            <button
                                class="btn-secondary text-sm"
                                on:click={() => {
                                    showReportEmailModal = false;
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                class="btn-primary text-sm"
                                on:click={async () => {
                                    const recipients = reportEmailInput
                                        .split(",")
                                        .map((e) => e.trim())
                                        .filter((e) => e.length > 0);
                                    if (recipients.length === 0) {
                                        toasts.error(
                                            "Please enter at least one email.",
                                        );
                                        return;
                                    }
                                    sendingReportEmail = true;
                                    try {
                                        await post(
                                            api.fullReportEmail(meetingId),
                                            { recipients },
                                        );
                                        toasts.success(
                                            `Report sent to ${recipients.join(", ")}`,
                                        );
                                        showReportEmailModal = false;
                                        reportEmailInput = "";
                                    } catch (err) {
                                        toasts.error(
                                            "Email failed: " + err.message,
                                        );
                                    }
                                    sendingReportEmail = false;
                                }}
                                disabled={sendingReportEmail}
                            >
                                {#if sendingReportEmail}
                                    <Loader2 size={14} class="animate-spin" /> Sending…
                                {:else}
                                    <Mail size={14} /> Send
                                {/if}
                            </button>
                        </div>
                    </div>
                </div>
            {/if}
        {/if}
    </div>
{/if}
