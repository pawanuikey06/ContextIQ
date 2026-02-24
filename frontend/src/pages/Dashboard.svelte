<script>
    import { onMount } from "svelte";
    import { push } from "svelte-spa-router";
    import {
        Upload,
        Folder,
        Users,
        Clock,
        ChevronRight,
        Loader2,
        ArrowUpRight,
        Search,
        X,
    } from "lucide-svelte";
    import { api, get, post } from "../lib/api.js";
    import { formatTime, shortId } from "../lib/utils.js";
    import { toasts } from "../lib/toast.js";
    import Skeleton from "../components/Skeleton.svelte";

    let meetings = [];
    let loading = true;
    let uploading = false;
    let processing = false;
    let uploadProgress = "";
    let totalMeetings = 0;
    let totalSpeakers = 0;
    let totalDuration = 0;
    let totalDurationFormatted = "0:00";
    let fileInput;
    let searchQuery = "";

    $: filteredMeetings = searchQuery.trim()
        ? meetings.filter((m) =>
              m.title?.toLowerCase().includes(searchQuery.trim().toLowerCase()),
          )
        : meetings;

    onMount(async () => {
        await Promise.all([loadMeetings(), loadStats()]);
    });

    async function loadStats() {
        try {
            const stats = await get(api.stats);
            totalMeetings = stats.total_meetings || 0;
            totalSpeakers = stats.total_speakers || 0;
            totalDuration = stats.total_duration_seconds || 0;
            totalDurationFormatted = stats.total_duration_formatted || "0:00";
        } catch {
            // Fall back to meeting list stats
        }
    }

    async function loadMeetings() {
        loading = true;
        try {
            const res = await get(api.meetings);
            meetings = res.meetings || [];
            // Use meeting list as fallback if stats API fails
            if (!totalMeetings) {
                totalMeetings = meetings.length;
                totalSpeakers = meetings.reduce(
                    (sum, m) => sum + m.speakers,
                    0,
                );
                totalDuration = meetings.reduce(
                    (sum, m) => sum + m.duration,
                    0,
                );
            }
        } catch {
            meetings = [];
        }
        loading = false;
    }

    async function handleUpload() {
        fileInput.click();
    }

    async function onFileSelected(e) {
        const file = e.target.files[0];
        if (!file) return;

        uploading = true;
        uploadProgress = "Uploading video & extracting audio...";
        toasts.info(`Uploading ${file.name}...`);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const uploadRes = await fetch(`${api.upload}`, {
                method: "POST",
                body: formData,
            });
            const uploadData = await uploadRes.json();
            if (!uploadRes.ok) {
                throw new Error(
                    uploadData.detail || `Upload failed (${uploadRes.status})`,
                );
            }
            const meetingId = uploadData.meeting_id;
            if (!meetingId) {
                throw new Error("Server did not return a meeting ID");
            }

            uploadProgress =
                "Transcribing & diarizing (this may take a few minutes)...";
            processing = true;
            toasts.info("Transcribing & diarizing...");
            await post(api.transcribe(meetingId), null, 600000);

            uploadProgress = "Indexing for AI search...";
            try {
                await post(`${api.base}/chat/index/${meetingId}`);
            } catch {}

            uploadProgress = "Complete!";
            toasts.success("Meeting processed successfully! 🎉");
            await Promise.all([loadMeetings(), loadStats()]);
            uploading = false;
            processing = false;
        } catch (err) {
            uploadProgress = `Error: ${err.message}`;
            toasts.error(`Upload failed: ${err.message}`);
            uploading = false;
            processing = false;
        }
    }

    function openMeeting(id) {
        push(`/meetings/${id}`);
    }

    function getGreeting() {
        const hour = new Date().getHours();
        if (hour < 12) return "Good morning";
        if (hour < 17) return "Good afternoon";
        return "Good evening";
    }

    function statusBadge(status) {
        const map = {
            published: { label: "Published", cls: "badge-success" },
            summarized: { label: "Summarized", cls: "badge-blue" },
            transcribed: { label: "Transcribed", cls: "badge-warning" },
        };
        return map[status] || { label: "Uploaded", cls: "badge-warning" };
    }
</script>

<div class="max-w-5xl mx-auto px-6 py-10">
    <!-- Welcome -->
    <div class="flex items-end justify-between mb-10">
        <div>
            <p
                class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-1"
            >
                Dashboard
            </p>
            <h1 class="text-2xl font-extrabold text-gray-900">
                {getGreeting()}, Pawan
            </h1>
        </div>

        <input
            type="file"
            accept="video/*,audio/*"
            bind:this={fileInput}
            on:change={onFileSelected}
            class="hidden"
        />
        <button
            class="btn-primary"
            on:click={handleUpload}
            disabled={uploading}
        >
            {#if uploading}
                <Loader2 size={16} class="animate-spin" />
                {#if processing}Processing…{:else}Uploading…{/if}
            {:else}
                <Upload size={16} /> Upload Meeting
            {/if}
        </button>
    </div>

    <!-- Progress Banner -->
    {#if uploading}
        <div
            class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 mb-8 flex items-center gap-3"
        >
            <div
                class="w-8 h-8 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0"
            >
                <Loader2 size={16} class="text-emerald-600 animate-spin" />
            </div>
            <span class="text-sm text-emerald-800 font-medium"
                >{uploadProgress}</span
            >
        </div>
    {/if}

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <div
            class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-4 shadow-sm hover:shadow-md transition-shadow"
        >
            <div
                class="w-11 h-11 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0"
            >
                <Folder size={20} class="text-emerald-600" />
            </div>
            <div>
                <div class="text-2xl font-extrabold text-gray-900">
                    {totalMeetings}
                </div>
                <div
                    class="text-[11px] text-gray-400 uppercase tracking-wider font-semibold"
                >
                    Meetings
                </div>
            </div>
        </div>
        <div
            class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-4 shadow-sm hover:shadow-md transition-shadow"
        >
            <div
                class="w-11 h-11 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0"
            >
                <Users size={20} class="text-blue-600" />
            </div>
            <div>
                <div class="text-2xl font-extrabold text-gray-900">
                    {totalSpeakers}
                </div>
                <div
                    class="text-[11px] text-gray-400 uppercase tracking-wider font-semibold"
                >
                    Speakers
                </div>
            </div>
        </div>
        <div
            class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-4 shadow-sm hover:shadow-md transition-shadow"
        >
            <div
                class="w-11 h-11 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0"
            >
                <Clock size={20} class="text-amber-600" />
            </div>
            <div>
                <div class="text-2xl font-extrabold text-gray-900">
                    {totalDurationFormatted}
                </div>
                <div
                    class="text-[11px] text-gray-400 uppercase tracking-wider font-semibold"
                >
                    Total Duration
                </div>
            </div>
        </div>
    </div>

    <!-- Meetings Table -->
    <div>
        <!-- Header + Search -->
        <div class="flex items-center justify-between mb-4 gap-3">
            <p
                class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] whitespace-nowrap"
            >
                Recent Meetings
                {#if searchQuery.trim() && !loading}
                    <span class="text-gray-400 font-normal normal-case ml-1"
                        >— {filteredMeetings.length} result{filteredMeetings.length !==
                        1
                            ? "s"
                            : ""}</span
                    >
                {/if}
            </p>
            <div class="relative max-w-xs w-full">
                <div
                    class="absolute inset-y-0 left-3 flex items-center pointer-events-none"
                >
                    <Search size={14} class="text-gray-400" />
                </div>
                <input
                    type="text"
                    bind:value={searchQuery}
                    placeholder="Search meetings…"
                    class="w-full pl-9 pr-8 py-2 text-sm bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400/30 focus:border-emerald-400 transition-all"
                />
                {#if searchQuery}
                    <button
                        class="absolute inset-y-0 right-2.5 flex items-center text-gray-400 hover:text-gray-600"
                        on:click={() => (searchQuery = "")}
                    >
                        <X size={13} />
                    </button>
                {/if}
            </div>
        </div>

        {#if loading}
            <!-- Skeleton rows -->
            <div
                class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden"
            >
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Meeting</th><th>Speakers</th><th>Duration</th
                            ><th>Status</th><th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each Array(3) as _}
                            <tr style="cursor:default">
                                <td>
                                    <Skeleton
                                        height="0.85rem"
                                        width="60%"
                                        className="mb-1.5"
                                    />
                                    <Skeleton height="0.65rem" width="35%" />
                                </td>
                                <td
                                    ><Skeleton
                                        height="0.8rem"
                                        width="2rem"
                                    /></td
                                >
                                <td
                                    ><Skeleton
                                        height="0.8rem"
                                        width="3rem"
                                    /></td
                                >
                                <td
                                    ><Skeleton
                                        height="1.4rem"
                                        width="5rem"
                                        rounded="rounded-full"
                                    /></td
                                >
                                <td></td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {:else if meetings.length === 0}
            <div
                class="bg-white rounded-2xl border border-gray-100 shadow-sm text-center py-16"
            >
                <div
                    class="w-14 h-14 mx-auto rounded-2xl bg-gray-50 flex items-center justify-center mb-4"
                >
                    <Folder size={24} class="text-gray-300" />
                </div>
                <p class="text-gray-700 font-semibold mb-1">No meetings yet</p>
                <p class="text-xs text-gray-400 mb-5">
                    Upload a video or audio file to get started.
                </p>
                <button class="btn-primary text-sm" on:click={handleUpload}>
                    <Upload size={14} /> Upload Meeting
                </button>
            </div>
        {:else if filteredMeetings.length === 0 && searchQuery.trim()}
            <div
                class="bg-white rounded-2xl border border-gray-100 shadow-sm text-center py-16"
            >
                <div
                    class="w-14 h-14 mx-auto rounded-2xl bg-gray-50 flex items-center justify-center mb-4"
                >
                    <Search size={24} class="text-gray-300" />
                </div>
                <p class="text-gray-700 font-semibold mb-1">No matches found</p>
                <p class="text-xs text-gray-400">
                    No meetings match "{searchQuery}"
                </p>
                <button
                    class="mt-4 text-xs text-emerald-600 hover:underline"
                    on:click={() => (searchQuery = "")}>Clear search</button
                >
            </div>
        {:else}
            <div
                class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden"
            >
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Meeting</th>
                            <th>Speakers</th>
                            <th>Duration</th>
                            <th>Status</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each filteredMeetings as meeting}
                            {@const badge = statusBadge(meeting.status)}
                            <tr on:click={() => openMeeting(meeting.id)}>
                                <td>
                                    <div
                                        class="font-semibold text-sm text-gray-900"
                                    >
                                        {meeting.title}
                                    </div>
                                    <div
                                        class="text-[11px] text-gray-400 mt-0.5"
                                    >
                                        {meeting.date || shortId(meeting.id)}
                                    </div>
                                </td>
                                <td class="text-sm text-gray-500"
                                    >{meeting.speakers}</td
                                >
                                <td class="text-sm text-gray-500 font-mono"
                                    >{formatTime(meeting.duration)}</td
                                >
                                <td>
                                    <span class={badge.cls}>{badge.label}</span>
                                </td>
                                <td class="text-right">
                                    <ArrowUpRight
                                        size={14}
                                        class="text-gray-300"
                                    />
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>
