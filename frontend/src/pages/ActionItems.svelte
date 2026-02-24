<script>
    import { onMount } from "svelte";
    import { push } from "svelte-spa-router";
    import {
        CheckCircle,
        CheckCircle2,
        AlertCircle,
        Flag,
        ExternalLink,
        User,
        Calendar,
        Lightbulb,
        RotateCcw,
        Loader2,
        Sparkles,
        Zap,
        Pencil,
        Save,
        X,
        ChevronDown,
        Shield,
        ShieldCheck,
    } from "lucide-svelte";
    import { api, get, post, put } from "../lib/api.js";
    import { shortId } from "../lib/utils.js";
    import { toasts } from "../lib/toast.js";
    import Skeleton from "../components/Skeleton.svelte";

    let meetings = [];
    let selectedMeeting = null;
    let actionData = null;
    let loading = true;
    let extracting = false;
    let saving = false;
    let forceRegen = false;
    let approved = false;
    let dirty = false;

    let totalActions = 0;
    let totalDecisions = 0;
    let highPriority = 0;

    // Editing state
    let editingIndex = -1;
    let editDraft = {};

    const statusOptions = ["To Do", "In Progress", "In Review", "Done"];
    const priorityOptions = ["High", "Medium", "Low"];
    const statusColors = {
        "To Do": "bg-gray-100 text-gray-600 border-gray-200",
        "In Progress": "bg-blue-50 text-blue-700 border-blue-200",
        "In Review": "bg-amber-50 text-amber-700 border-amber-200",
        Done: "bg-emerald-50 text-emerald-700 border-emerald-200",
    };
    const priorityConfig = {
        high: {
            label: "High",
            dot: "bg-red-500",
            color: "text-red-700 bg-red-50 border-red-200/60",
        },
        medium: {
            label: "Medium",
            dot: "bg-amber-500",
            color: "text-amber-700 bg-amber-50 border-amber-200/60",
        },
        low: {
            label: "Low",
            dot: "bg-emerald-500",
            color: "text-emerald-700 bg-emerald-50 border-emerald-200/60",
        },
    };

    /** Convert AI-detected date strings to YYYY-MM-DD for date input */
    function parseDeadlineToISO(dateStr) {
        if (!dateStr) return "";
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
        const d = new Date(dateStr);
        if (!isNaN(d.getTime())) {
            return d.toISOString().split("T")[0];
        }
        return "";
    }

    /** Format ISO date for display */
    function formatDeadlineDisplay(dateStr) {
        if (!dateStr) return "";
        const d = new Date(
            dateStr + (dateStr.includes("T") ? "" : "T00:00:00"),
        );
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    }
    onMount(async () => {
        await loadMeetings();
    });

    async function loadMeetings() {
        loading = true;
        try {
            const res = await get(api.meetings);
            meetings = (res.meetings || []).map((m) => ({
                id: m.id,
                title: m.title,
            }));
            if (meetings.length > 0) {
                selectedMeeting = meetings[0].id;
                await loadActionItems(selectedMeeting);
            }
        } catch {
            meetings = [];
        }
        loading = false;
    }

    async function loadActionItems(meetingId) {
        try {
            const items = await post(api.actionItems(meetingId));
            actionData = items;
            // Ensure each item has status field
            (actionData.action_items || []).forEach((item) => {
                if (!item.status) item.status = "To Do";
                if (!item.jira_id) item.jira_id = "";
            });
            approved = actionData.approved || false;
            dirty = false;
            updateStats();
        } catch {
            actionData = null;
        }
    }

    async function extractActions() {
        if (!selectedMeeting) return;
        extracting = true;
        try {
            const url = forceRegen
                ? `${api.actionItems(selectedMeeting)}?force=true`
                : api.actionItems(selectedMeeting);
            actionData = await post(url, null, 120000);
            (actionData.action_items || []).forEach((item) => {
                if (!item.status) item.status = "To Do";
                if (!item.jira_id) item.jira_id = "";
            });
            approved = false;
            dirty = false;
            updateStats();
        } catch (err) {
            toasts.error("Extraction failed: " + err.message);
        }
        extracting = false;
    }

    async function saveAll() {
        if (!selectedMeeting || !actionData) return;
        saving = true;
        try {
            const payload = { ...actionData, approved };
            await put(api.actionItems(selectedMeeting), payload);
            dirty = false;
        } catch (err) {
            toasts.error("Save failed: " + err.message);
        }
        saving = false;
    }

    async function approveAll() {
        approved = true;
        dirty = true;
        await saveAll();
    }

    function updateStats() {
        if (!actionData) return;
        const items = actionData.action_items || [];
        totalActions = items.length;
        totalDecisions = (actionData.decisions || []).length;
        highPriority = items.filter(
            (i) => i.priority?.toLowerCase() === "high",
        ).length;
    }

    async function onMeetingChange(e) {
        selectedMeeting = e.target.value;
        actionData = null;
        editingIndex = -1;
        await loadActionItems(selectedMeeting);
    }

    function getPriority(p) {
        return priorityConfig[p?.toLowerCase()] || priorityConfig.low;
    }

    function startEdit(idx) {
        const item = actionData.action_items[idx];
        editDraft = { ...item, deadline: parseDeadlineToISO(item.deadline) };
        editingIndex = idx;
    }

    function cancelEdit() {
        editingIndex = -1;
        editDraft = {};
    }

    function saveEdit() {
        if (editingIndex < 0) return;
        actionData.action_items[editingIndex] = { ...editDraft };
        actionData = actionData; // trigger reactivity
        editingIndex = -1;
        editDraft = {};
        dirty = true;
        updateStats();
    }

    function updateItemStatus(idx, status) {
        actionData.action_items[idx].status = status;
        actionData = actionData;
        dirty = true;
    }

    function getStatusColor(s) {
        return statusColors[s] || statusColors["To Do"];
    }
</script>

<div class="max-w-5xl mx-auto px-6 py-10">
    <!-- Header -->
    <div class="flex items-end justify-between mb-10">
        <div>
            <p
                class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-1"
            >
                Action Items
            </p>
            <h1 class="text-2xl font-extrabold text-gray-900">
                Tasks & Decisions
            </h1>
        </div>
        <div class="flex items-center gap-2">
            {#if dirty}
                <button
                    class="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-xl transition-all inline-flex items-center gap-2 text-sm shadow-sm"
                    on:click={saveAll}
                    disabled={saving}
                >
                    {#if saving}<Loader2
                            size={14}
                            class="animate-spin"
                        />{:else}<Save size={14} />{/if}
                    Save Changes
                </button>
            {/if}
            {#if actionData && !approved}
                <button
                    class="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-medium px-4 py-2 rounded-xl transition-all inline-flex items-center gap-2 text-sm border border-emerald-200"
                    on:click={approveAll}
                >
                    <ShieldCheck size={14} /> Approve All
                </button>
            {/if}
        </div>
    </div>

    <!-- Approval Banner -->
    {#if approved}
        <div
            class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 mb-6 flex items-center gap-3"
        >
            <div
                class="w-8 h-8 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0"
            >
                <ShieldCheck size={16} class="text-emerald-600" />
            </div>
            <div>
                <p class="text-sm font-semibold text-emerald-800">
                    Approved — Human Verified
                </p>
                <p class="text-xs text-emerald-600">
                    Action items have been reviewed and approved for
                    distribution.
                </p>
            </div>
        </div>
    {/if}

    <!-- Controls -->
    <div
        class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-8"
    >
        <div class="flex-1 w-full sm:w-auto">
            <p
                class="text-emerald-600 text-[10px] font-bold uppercase tracking-[0.15em] mb-1.5"
            >
                Select Meeting
            </p>
            <select
                class="w-full px-3.5 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition-all"
                on:change={onMeetingChange}
            >
                {#each meetings as m}
                    <option value={m.id}>{m.title || shortId(m.id)}</option>
                {/each}
            </select>
        </div>

        <div class="flex items-center gap-3 flex-shrink-0">
            <label
                class="flex items-center gap-2 text-sm text-gray-500 cursor-pointer select-none"
            >
                <input
                    type="checkbox"
                    bind:checked={forceRegen}
                    class="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                Regenerate
            </label>
            <button
                class="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2.5 rounded-xl transition-all inline-flex items-center gap-2 text-sm shadow-sm"
                on:click={extractActions}
                disabled={extracting || !selectedMeeting}
            >
                {#if extracting}
                    <Loader2 size={14} class="animate-spin" /> Extracting…
                {:else}
                    <Zap size={14} /> Extract
                {/if}
            </button>
        </div>
    </div>

    {#if loading}
        <!-- Skeleton stats -->
        <div class="grid grid-cols-3 gap-4 mb-8">
            {#each Array(3) as _}
                <div
                    class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-4 shadow-sm"
                >
                    <Skeleton
                        width="2.75rem"
                        height="2.75rem"
                        rounded="rounded-xl"
                    />
                    <div class="flex-1">
                        <Skeleton
                            height="1.6rem"
                            width="3rem"
                            className="mb-1.5"
                        />
                        <Skeleton height="0.65rem" width="5rem" />
                    </div>
                </div>
            {/each}
        </div>
        <!-- Skeleton rows -->
        <div
            class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden"
        >
            {#each Array(4) as _}
                <div
                    class="flex items-center gap-4 px-5 py-4 border-b border-gray-50"
                >
                    <Skeleton
                        width="100%"
                        height="0.85rem"
                        className="flex-1"
                    />
                    <Skeleton
                        width="4rem"
                        height="1.5rem"
                        rounded="rounded-full"
                    />
                    <Skeleton width="3rem" height="0.8rem" />
                </div>
            {/each}
        </div>
    {:else if !actionData}
        <div
            class="bg-white rounded-2xl border border-gray-100 shadow-sm text-center py-20"
        >
            <div
                class="w-14 h-14 mx-auto rounded-2xl bg-emerald-50 flex items-center justify-center mb-4"
            >
                <Zap size={24} class="text-emerald-600" />
            </div>
            <h3 class="font-bold text-gray-900 mb-1">No action items yet</h3>
            <p class="text-sm text-gray-400">
                Click "Extract" to analyze this meeting.
            </p>
        </div>
    {:else}
        <!-- Stats -->
        <div class="grid grid-cols-3 gap-4 mb-8">
            <div
                class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-4 shadow-sm"
            >
                <div
                    class="w-11 h-11 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0"
                >
                    <CheckCircle size={20} class="text-blue-600" />
                </div>
                <div>
                    <div class="text-2xl font-extrabold text-gray-900">
                        {totalActions}
                    </div>
                    <div
                        class="text-[11px] text-gray-400 uppercase tracking-wider font-semibold"
                    >
                        Action Items
                    </div>
                </div>
            </div>
            <div
                class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-4 shadow-sm"
            >
                <div
                    class="w-11 h-11 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0"
                >
                    <Lightbulb size={20} class="text-emerald-600" />
                </div>
                <div>
                    <div class="text-2xl font-extrabold text-gray-900">
                        {totalDecisions}
                    </div>
                    <div
                        class="text-[11px] text-gray-400 uppercase tracking-wider font-semibold"
                    >
                        Decisions
                    </div>
                </div>
            </div>
            <div
                class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-4 shadow-sm"
            >
                <div
                    class="w-11 h-11 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0"
                >
                    <Flag size={20} class="text-red-600" />
                </div>
                <div>
                    <div class="text-2xl font-extrabold text-gray-900">
                        {highPriority}
                    </div>
                    <div
                        class="text-[11px] text-gray-400 uppercase tracking-wider font-semibold"
                    >
                        High Priority
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Items (Jira-style) -->
        {#if actionData.action_items?.length}
            <div class="mb-8">
                <div class="flex items-center justify-between mb-4">
                    <p
                        class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em]"
                    >
                        Action Items
                    </p>
                </div>

                <!-- Table header -->
                <div
                    class="hidden md:grid md:grid-cols-12 gap-3 px-5 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-wider"
                >
                    <div class="col-span-4">Task</div>
                    <div class="col-span-2">Assignee</div>
                    <div class="col-span-2">Priority</div>
                    <div class="col-span-2">Status</div>
                    <div class="col-span-1">Jira ID</div>
                    <div class="col-span-1"></div>
                </div>

                <div class="space-y-2">
                    {#each actionData.action_items as item, idx}
                        {@const p = getPriority(item.priority)}

                        {#if editingIndex === idx}
                            <!-- Edit mode -->
                            <div
                                class="bg-white rounded-2xl border-2 border-emerald-200 shadow-lg p-5 space-y-4"
                            >
                                <div>
                                    <span
                                        class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1"
                                        >Task</span
                                    >
                                    <input
                                        type="text"
                                        bind:value={editDraft.task}
                                        class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                                    />
                                </div>
                                <div
                                    class="grid grid-cols-2 md:grid-cols-4 gap-3"
                                >
                                    <div>
                                        <span
                                            class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1"
                                            >Assignee</span
                                        >
                                        <input
                                            type="text"
                                            bind:value={editDraft.assigned_to}
                                            class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                                        />
                                    </div>
                                    <div>
                                        <span
                                            class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1"
                                            >Priority</span
                                        >
                                        <select
                                            bind:value={editDraft.priority}
                                            class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                                        >
                                            {#each priorityOptions as opt}<option
                                                    value={opt}>{opt}</option
                                                >{/each}
                                        </select>
                                    </div>
                                    <div>
                                        <span
                                            class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1"
                                            >Status</span
                                        >
                                        <select
                                            bind:value={editDraft.status}
                                            class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                                        >
                                            {#each statusOptions as opt}<option
                                                    value={opt}>{opt}</option
                                                >{/each}
                                        </select>
                                    </div>
                                    <div>
                                        <span
                                            class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1"
                                            >Jira ID</span
                                        >
                                        <input
                                            type="text"
                                            bind:value={editDraft.jira_id}
                                            placeholder="PROJ-123"
                                            class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <span
                                        class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1"
                                        >Deadline</span
                                    >
                                    <input
                                        type="date"
                                        bind:value={editDraft.deadline}
                                        class="w-full max-w-xs px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                                    />
                                </div>
                                <div class="flex gap-2 pt-1">
                                    <button
                                        on:click={saveEdit}
                                        class="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-lg text-sm inline-flex items-center gap-1.5 transition-colors"
                                    >
                                        <Save size={13} /> Save
                                    </button>
                                    <button
                                        on:click={cancelEdit}
                                        class="bg-gray-100 hover:bg-gray-200 text-gray-600 font-medium px-4 py-2 rounded-lg text-sm inline-flex items-center gap-1.5 transition-colors"
                                    >
                                        <X size={13} /> Cancel
                                    </button>
                                </div>
                            </div>
                        {:else}
                            <!-- View mode (Jira row) -->
                            <div
                                class="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 md:p-5 hover:shadow-md transition-shadow group"
                            >
                                <div
                                    class="md:grid md:grid-cols-12 gap-3 items-center"
                                >
                                    <!-- Task -->
                                    <div
                                        class="col-span-4 flex items-start gap-3 mb-2 md:mb-0"
                                    >
                                        <div
                                            class="w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 {p.dot}"
                                        ></div>
                                        <p
                                            class="text-sm font-semibold text-gray-900 leading-snug"
                                        >
                                            {item.task || "Untitled"}
                                        </p>
                                    </div>
                                    <!-- Assignee -->
                                    <div
                                        class="col-span-2 flex items-center gap-1.5 mb-2 md:mb-0"
                                    >
                                        <div
                                            class="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0"
                                        >
                                            <User
                                                size={11}
                                                class="text-gray-400"
                                            />
                                        </div>
                                        <span
                                            class="text-xs text-gray-600 truncate"
                                            >{item.assigned_to ||
                                                "Unassigned"}</span
                                        >
                                    </div>
                                    <!-- Priority -->
                                    <div class="col-span-2 mb-2 md:mb-0">
                                        <span
                                            class="text-[10px] font-semibold px-2.5 py-1 rounded-full border {p.color}"
                                            >{p.label}</span
                                        >
                                    </div>
                                    <!-- Status -->
                                    <div class="col-span-2 mb-2 md:mb-0">
                                        <select
                                            value={item.status || "To Do"}
                                            on:change={(e) =>
                                                updateItemStatus(
                                                    idx,
                                                    /** @type {HTMLSelectElement} */ (
                                                        e.target
                                                    ).value,
                                                )}
                                            class="text-[11px] font-semibold px-2.5 py-1 rounded-full border appearance-none cursor-pointer {getStatusColor(
                                                item.status,
                                            )}"
                                        >
                                            {#each statusOptions as s}<option
                                                    value={s}>{s}</option
                                                >{/each}
                                        </select>
                                    </div>
                                    <!-- Jira ID -->
                                    <div class="col-span-1 mb-2 md:mb-0">
                                        {#if item.jira_id}
                                            <span
                                                class="text-[11px] font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded"
                                                >{item.jira_id}</span
                                            >
                                        {:else}
                                            <span
                                                class="text-[10px] text-gray-300"
                                                >—</span
                                            >
                                        {/if}
                                    </div>
                                    <!-- Edit button -->
                                    <div class="col-span-1 flex justify-end">
                                        <button
                                            on:click={() => startEdit(idx)}
                                            class="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-emerald-600 p-1.5 rounded-lg hover:bg-emerald-50"
                                        >
                                            <Pencil size={13} />
                                        </button>
                                    </div>
                                </div>
                                <!-- Deadline row -->
                                {#if item.deadline}
                                    <div
                                        class="mt-2 ml-5 flex items-center gap-1.5 text-[11px] text-gray-400"
                                    >
                                        <Calendar size={10} />
                                        {formatDeadlineDisplay(item.deadline)}
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    {/each}
                </div>
            </div>
        {/if}

        <!-- Decisions -->
        {#if actionData.decisions?.length}
            <div class="mb-8">
                <p
                    class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-4"
                >
                    Decisions Made
                </p>
                <div class="grid md:grid-cols-2 gap-3">
                    {#each actionData.decisions as d}
                        <div
                            class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
                        >
                            <p
                                class="text-sm font-semibold text-gray-900 flex items-start gap-2"
                            >
                                <CheckCircle2
                                    size={14}
                                    class="text-emerald-600 mt-0.5 flex-shrink-0"
                                />
                                {d.decision || "N/A"}
                            </p>
                            <div
                                class="text-[11px] text-gray-400 mt-2 ml-5 space-y-0.5"
                            >
                                <p>
                                    <span class="font-medium text-gray-500"
                                        >By:</span
                                    >
                                    {d.made_by || "Unknown"}
                                </p>
                                <p>
                                    <span class="font-medium text-gray-500"
                                        >Context:</span
                                    >
                                    {d.context || "N/A"}
                                </p>
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}

        <!-- Key Takeaways + Follow-ups -->
        <div class="grid md:grid-cols-2 gap-4 mb-8">
            {#if actionData.key_takeaways?.length}
                <div
                    class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
                >
                    <p
                        class="text-emerald-600 text-[10px] font-bold uppercase tracking-[0.15em] mb-3 flex items-center gap-1.5"
                    >
                        <Lightbulb size={12} class="text-amber-500" /> Key Takeaways
                    </p>
                    <ul class="space-y-2">
                        {#each actionData.key_takeaways as t}
                            <li
                                class="text-sm text-gray-600 flex items-start gap-2"
                            >
                                <span class="text-emerald-500 mt-1 text-[8px]"
                                    >●</span
                                >
                                {t}
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}
            {#if actionData.follow_ups?.length}
                <div
                    class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
                >
                    <p
                        class="text-emerald-600 text-[10px] font-bold uppercase tracking-[0.15em] mb-3 flex items-center gap-1.5"
                    >
                        <RotateCcw size={12} class="text-blue-500" /> Follow-ups
                    </p>
                    <ul class="space-y-2">
                        {#each actionData.follow_ups as f}
                            <li
                                class="text-sm text-gray-600 flex items-start gap-2"
                            >
                                <span class="text-blue-500 mt-1 text-[8px]"
                                    >●</span
                                >
                                {f}
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}
        </div>
    {/if}
</div>
