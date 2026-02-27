<script>
    import { onMount } from "svelte";
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
        ArrowUpRight,
        Send,
        Mail,
        Copy,
        Check,
        Plus,
        Trash2,
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
    let activeSection = null;

    // Jira integration
    let jiraConfigured = false;
    let pushingJira = new Set();
    let syncingJira = false;
    let jiraPushResult = null;

    // Follow-up email state
    let showEmailModal = false;
    let generatingEmail = false;
    let sendingEmail = false;
    let emailData = null;
    let emailSubject = "";
    let emailBody = "";
    let emailRecipients = [""];
    let emailCopied = false;
    let emailSent = false;

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
        // Check Jira config
        try {
            const jStatus = await get(api.jiraStatus);
            jiraConfigured = jStatus.configured || false;
        } catch {
            jiraConfigured = false;
        }
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
        const savedIdx = editingIndex;
        editingIndex = -1;
        editDraft = {};
        dirty = true;
        updateStats();
        // Auto-push to Jira if linked
        updateJiraIfLinked(savedIdx);
    }

    function updateItemStatus(idx, status) {
        actionData.action_items[idx].status = status;
        actionData = actionData;
        dirty = true;
        // Auto-push status to Jira if linked
        updateJiraIfLinked(idx);
    }

    async function updateJiraIfLinked(idx) {
        if (!jiraConfigured || !selectedMeeting) return;
        const item = actionData.action_items[idx];
        if (!item?.jira_id) return;
        try {
            // Save first so backend has latest data
            await saveAll();
            const result = await put(api.jiraUpdate(selectedMeeting), {
                index: idx,
            });
            if (result.success && result.updated_fields?.length > 0) {
                toasts.success(
                    `${item.jira_id} updated: ${result.updated_fields.join(", ")}`,
                );
            }
        } catch (err) {
            toasts.error(`Jira update failed: ${err.message}`);
        }
    }

    function getStatusColor(s) {
        return statusColors[s] || statusColors["To Do"];
    }

    async function pushToJira(indices = null) {
        if (!selectedMeeting || !actionData) return;
        const trackIds = indices || actionData.action_items.map((_, i) => i);
        trackIds.forEach((i) => pushingJira.add(i));
        pushingJira = pushingJira; // trigger reactivity
        jiraPushResult = null;
        try {
            const result = await post(api.jiraPush(selectedMeeting), {
                indices,
            });
            jiraPushResult = result;
            if (result.created > 0) {
                toasts.success(
                    `Created ${result.created} Jira ticket${result.created > 1 ? "s" : ""}!`,
                );
                // Reload to get updated jira_id fields
                await loadActionItems(selectedMeeting);
            }
            if (result.failed > 0) {
                toasts.error(
                    `${result.failed} ticket${result.failed > 1 ? "s" : ""} failed to create.`,
                );
            }
        } catch (err) {
            toasts.error("Jira push failed: " + err.message);
        }
        trackIds.forEach((i) => pushingJira.delete(i));
        pushingJira = pushingJira; // trigger reactivity
    }

    async function pushSingleToJira(idx) {
        await pushToJira([idx]);
    }

    async function syncFromJira() {
        if (!selectedMeeting || !actionData) return;
        syncingJira = true;
        try {
            const result = await post(api.jiraSync(selectedMeeting));
            if (result.changes?.length > 0) {
                const msgs = result.changes.map(
                    (c) => `${c.key}: ${c.changes.join(", ")}`,
                );
                toasts.success(`Synced! ${msgs.join(" | ")}`);
            } else {
                toasts.success("All up to date — no changes from Jira.");
            }
            await loadActionItems(selectedMeeting);
        } catch (err) {
            toasts.error("Jira sync failed: " + err.message);
        }
        syncingJira = false;
    }

    // ── Follow-up Email Functions ──
    async function openEmailModal() {
        showEmailModal = true;
        emailSent = false;
        emailCopied = false;
        generatingEmail = true;
        try {
            const result = await post(
                api.followupEmail(selectedMeeting),
                null,
                120000,
            );
            emailData = result;
            emailSubject = result.subject || "";
            emailBody = result.body || "";
            emailRecipients = result.recipients_suggested?.length
                ? [...result.recipients_suggested]
                : [""];
        } catch (err) {
            toasts.error("Failed to generate email: " + err.message);
            showEmailModal = false;
        }
        generatingEmail = false;
    }

    function closeEmailModal() {
        showEmailModal = false;
        emailData = null;
        emailSent = false;
    }

    function addRecipient() {
        emailRecipients = [...emailRecipients, ""];
    }

    function removeRecipient(idx) {
        emailRecipients = emailRecipients.filter((_, i) => i !== idx);
        if (emailRecipients.length === 0) emailRecipients = [""];
    }

    async function sendFollowupEmail() {
        const validRecipients = emailRecipients.filter(
            (r) => r.trim() && r.includes("@"),
        );
        if (validRecipients.length === 0) {
            toasts.error("Please enter at least one valid email address.");
            return;
        }
        sendingEmail = true;
        try {
            const result = await post(
                api.followupEmailSend(selectedMeeting),
                {
                    recipients: validRecipients,
                    subject: emailSubject,
                    body: emailBody,
                },
                30000,
            );
            if (result.success) {
                emailSent = true;
                toasts.success(result.message || "Email sent successfully!");
            } else {
                toasts.error(result.message || "Failed to send email.");
            }
        } catch (err) {
            toasts.error("Send failed: " + err.message);
        }
        sendingEmail = false;
    }

    function copyEmailToClipboard() {
        const text = `Subject: ${emailSubject}\n\n${emailBody}`;
        navigator.clipboard.writeText(text).then(() => {
            emailCopied = true;
            toasts.success("Email copied to clipboard!");
            setTimeout(() => (emailCopied = false), 2000);
        });
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
            {#if jiraConfigured && actionData?.action_items?.some((i) => i.jira_id)}
                <button
                    class="bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium px-4 py-2 rounded-xl transition-all inline-flex items-center gap-2 text-sm border border-blue-200"
                    on:click={syncFromJira}
                    disabled={syncingJira}
                >
                    {#if syncingJira}
                        <Loader2 size={14} class="animate-spin" />
                        Syncing…
                    {:else}
                        <RotateCcw size={14} />
                        Sync from Jira
                    {/if}
                </button>
            {/if}
            {#if actionData}
                <button
                    class="bg-violet-600 hover:bg-violet-700 text-white font-medium px-4 py-2 rounded-xl transition-all inline-flex items-center gap-2 text-sm shadow-sm"
                    on:click={openEmailModal}
                    disabled={generatingEmail}
                >
                    {#if generatingEmail}
                        <Loader2 size={14} class="animate-spin" />
                        Generating…
                    {:else}
                        <Mail size={14} />
                        Follow-up Email
                    {/if}
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

        <!-- Section cards grid -->
        {@const sections = [
            {
                id: "actions",
                label: "Action Items",
                icon: CheckCircle,
                color: "text-blue-600",
                bg: "bg-blue-50",
                border: "border-blue-100",
                count: actionData.action_items?.length || 0,
                desc: "Tasks, assignments, and deadlines extracted from the meeting.",
            },
            {
                id: "decisions",
                label: "Decisions Made",
                icon: ShieldCheck,
                color: "text-emerald-600",
                bg: "bg-emerald-50",
                border: "border-emerald-100",
                count: actionData.decisions?.length || 0,
                desc: "Key decisions and resolutions agreed upon during discussion.",
            },
            {
                id: "takeaways",
                label: "Key Takeaways",
                icon: Lightbulb,
                color: "text-amber-600",
                bg: "bg-amber-50",
                border: "border-amber-100",
                count: actionData.key_takeaways?.length || 0,
                desc: "Important insights and highlights from the meeting.",
            },
            {
                id: "followups",
                label: "Follow-ups",
                icon: RotateCcw,
                color: "text-purple-600",
                bg: "bg-purple-50",
                border: "border-purple-100",
                count: actionData.follow_ups?.length || 0,
                desc: "Pending follow-up items that need attention.",
            },
            {
                id: "risks",
                label: "Risks Identified",
                icon: AlertCircle,
                color: "text-red-600",
                bg: "bg-red-50",
                border: "border-red-100",
                count: actionData.risks_identified?.length || 0,
                desc: "Potential risks and blockers mentioned in the meeting.",
            },
        ]}

        {#if !activeSection}
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {#each sections as sec}
                    {#if sec.count > 0}
                        <button
                            class="bg-white rounded-2xl border {sec.border} shadow-sm p-6 text-left hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group"
                            on:click={() => (activeSection = sec.id)}
                        >
                            <div
                                class="w-10 h-10 rounded-xl {sec.bg} flex items-center justify-center mb-4"
                            >
                                <svelte:component
                                    this={sec.icon}
                                    size={20}
                                    class={sec.color}
                                />
                            </div>
                            <h3
                                class="text-sm font-bold text-gray-900 mb-1 flex items-center gap-2"
                            >
                                {sec.label}
                                <span
                                    class="text-[10px] font-semibold {sec.color} {sec.bg} px-2 py-0.5 rounded-full"
                                    >{sec.count}</span
                                >
                            </h3>
                            <p
                                class="text-xs text-gray-400 mb-3 leading-relaxed"
                            >
                                {sec.desc}
                            </p>
                            <span
                                class="text-xs font-semibold {sec.color} group-hover:underline inline-flex items-center gap-1"
                            >
                                Explore <ArrowUpRight size={12} />
                            </span>
                        </button>
                    {/if}
                {/each}
            </div>
        {:else}
            <!-- Back button -->
            <button
                class="inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 mb-6 transition-colors"
                on:click={() => (activeSection = null)}
            >
                <ChevronDown size={14} class="rotate-90" /> Back to overview
            </button>

            <!-- ACTION ITEMS SECTION -->
            {#if activeSection === "actions" && actionData.action_items?.length}
                <div>
                    <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center gap-2">
                            <div
                                class="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center"
                            >
                                <CheckCircle size={16} class="text-blue-600" />
                            </div>
                            <h3 class="text-sm font-bold text-gray-900">
                                Action Items
                            </h3>
                        </div>
                    </div>

                    <!-- Progress bar -->
                    {#if totalActions > 0}
                        {@const doneCount = (
                            actionData?.action_items || []
                        ).filter((i) => i.status === "Done").length}
                        {@const pct = Math.round(
                            (doneCount / totalActions) * 100,
                        )}
                        <div class="mb-6">
                            <div class="flex items-center justify-between mb-2">
                                <span
                                    class="text-xs font-semibold text-gray-500"
                                    >Completion</span
                                >
                                <span class="text-xs font-bold text-emerald-600"
                                    >{doneCount}/{totalActions} done ({pct}%)</span
                                >
                            </div>
                            <div
                                class="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden"
                            >
                                <div
                                    class="bg-gradient-to-r from-emerald-400 to-emerald-600 h-full rounded-full transition-all duration-500"
                                    style="width: {pct}%"
                                ></div>
                            </div>
                        </div>
                    {/if}

                    <div class="space-y-3">
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
                                                bind:value={
                                                    editDraft.assigned_to
                                                }
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
                                                {#each priorityOptions as pr}<option
                                                        value={pr}>{pr}</option
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
                                                {#each statusOptions as st}<option
                                                        value={st}>{st}</option
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
                                <!-- Card view -->
                                <div
                                    class="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 group overflow-hidden"
                                >
                                    <div class="flex">
                                        <div
                                            class="w-1.5 flex-shrink-0 rounded-l-2xl {p.dot}"
                                        ></div>
                                        <div class="flex-1 p-5">
                                            <div
                                                class="flex items-start justify-between gap-3 mb-3"
                                            >
                                                <div
                                                    class="flex items-start gap-3 flex-1 min-w-0"
                                                >
                                                    <div
                                                        class="w-8 h-8 rounded-xl {p.color.split(
                                                            ' ',
                                                        )[1]} flex items-center justify-center flex-shrink-0 mt-0.5"
                                                    >
                                                        <CheckCircle
                                                            size={15}
                                                            class={p.color.split(
                                                                " ",
                                                            )[0]}
                                                        />
                                                    </div>
                                                    <div class="min-w-0">
                                                        <p
                                                            class="text-sm font-semibold text-gray-900 leading-snug"
                                                        >
                                                            {item.task ||
                                                                "Untitled"}
                                                        </p>
                                                        {#if item.deadline}
                                                            <span
                                                                class="inline-flex items-center gap-1 text-[10px] text-gray-400 mt-1"
                                                            >
                                                                <Calendar
                                                                    size={10}
                                                                />
                                                                {formatDeadlineDisplay(
                                                                    item.deadline,
                                                                )}
                                                            </span>
                                                        {/if}
                                                    </div>
                                                </div>
                                                <button
                                                    on:click={() =>
                                                        startEdit(idx)}
                                                    class="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-emerald-600 p-1.5 rounded-lg hover:bg-emerald-50"
                                                >
                                                    <Pencil size={13} />
                                                </button>
                                                {#if jiraConfigured && !item.jira_id}
                                                    <button
                                                        on:click={() =>
                                                            pushSingleToJira(
                                                                idx,
                                                            )}
                                                        disabled={pushingJira.has(
                                                            idx,
                                                        )}
                                                        class="text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200/60 font-semibold px-2.5 py-1 rounded-lg text-[10px] inline-flex items-center gap-1 transition-colors"
                                                        title="Create Jira ticket for this item"
                                                    >
                                                        {#if pushingJira.has(idx)}
                                                            <Loader2
                                                                size={10}
                                                                class="animate-spin"
                                                            />
                                                        {:else}
                                                            <Send size={10} />
                                                        {/if}
                                                        Push to Jira
                                                    </button>
                                                {/if}
                                                {#if item.jira_id}
                                                    <a
                                                        href="https://pawanuikey690.atlassian.net/browse/{item.jira_id}"
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        class="text-[10px] font-mono text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200/60 px-2 py-1 rounded-lg inline-flex items-center gap-1 transition-colors no-underline"
                                                    >
                                                        <ExternalLink
                                                            size={10}
                                                        />
                                                        {item.jira_id}
                                                    </a>
                                                {/if}
                                            </div>
                                            <div
                                                class="flex flex-wrap items-center gap-2"
                                            >
                                                <span
                                                    class="inline-flex items-center gap-1.5 text-[11px] text-gray-500 bg-gray-50 px-2.5 py-1 rounded-lg"
                                                >
                                                    <User
                                                        size={11}
                                                        class="text-gray-400"
                                                    />
                                                    {item.assigned_to ||
                                                        "Unassigned"}
                                                </span>
                                                <span
                                                    class="text-[10px] font-semibold px-2.5 py-1 rounded-lg border {p.color}"
                                                    >{p.label}</span
                                                >
                                                <select
                                                    value={item.status ||
                                                        "To Do"}
                                                    on:change={(e) =>
                                                        updateItemStatus(
                                                            idx,
                                                            /** @type {HTMLSelectElement} */ (
                                                                e.target
                                                            ).value,
                                                        )}
                                                    class="text-[10px] font-semibold px-2.5 py-1 rounded-lg border appearance-none cursor-pointer {getStatusColor(
                                                        item.status,
                                                    )}"
                                                >
                                                    {#each statusOptions as s}<option
                                                            value={s}
                                                            >{s}</option
                                                        >{/each}
                                                </select>
                                                {#if item.jira_id}
                                                    <span
                                                        class="text-[10px] font-mono text-blue-600 bg-blue-50 px-2 py-1 rounded-lg"
                                                        >{item.jira_id}</span
                                                    >
                                                {/if}
                                                {#if item.category}
                                                    <span
                                                        class="text-[10px] font-medium text-violet-600 bg-violet-50 px-2 py-1 rounded-lg capitalize"
                                                    >
                                                        {item.category}
                                                    </span>
                                                {/if}
                                            </div>
                                            {#if item.context}
                                                <p
                                                    class="text-[11px] text-gray-400 mt-2 leading-relaxed"
                                                >
                                                    <span
                                                        class="font-medium text-gray-500"
                                                        >Context:</span
                                                    >
                                                    {item.context}
                                                </p>
                                            {/if}
                                            {#if item.success_criteria}
                                                <p
                                                    class="text-[11px] text-emerald-500 mt-1"
                                                >
                                                    <span class="font-medium"
                                                        >✓ Success:</span
                                                    >
                                                    {item.success_criteria}
                                                </p>
                                            {/if}
                                            {#if item.dependencies?.length}
                                                <div
                                                    class="flex flex-wrap gap-1 mt-1.5"
                                                >
                                                    {#each item.dependencies as dep}
                                                        <span
                                                            class="text-[9px] font-mono text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded"
                                                            >↗ {dep}</span
                                                        >
                                                    {/each}
                                                </div>
                                            {/if}
                                        </div>
                                    </div>
                                </div>
                            {/if}
                        {/each}
                    </div>
                </div>
            {/if}

            <!-- DECISIONS SECTION -->
            {#if activeSection === "decisions" && actionData.decisions?.length}
                <div>
                    <div class="flex items-center gap-2 mb-4">
                        <div
                            class="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center"
                        >
                            <ShieldCheck size={16} class="text-emerald-600" />
                        </div>
                        <h3 class="text-sm font-bold text-gray-900">
                            Decisions Made
                        </h3>
                    </div>
                    <div class="grid md:grid-cols-2 gap-3">
                        {#each actionData.decisions as d}
                            <div
                                class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-all"
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
                                    {#if d.impact}
                                        <p>
                                            <span
                                                class="font-medium text-emerald-500"
                                                >Impact:</span
                                            >
                                            {d.impact}
                                        </p>
                                    {/if}
                                    {#if d.alternatives_considered}
                                        <p>
                                            <span
                                                class="font-medium text-gray-500"
                                                >Alternatives:</span
                                            >
                                            {d.alternatives_considered}
                                        </p>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            <!-- KEY TAKEAWAYS SECTION -->
            {#if activeSection === "takeaways" && actionData.key_takeaways?.length}
                <div>
                    <div class="flex items-center gap-2 mb-4">
                        <div
                            class="w-8 h-8 rounded-xl bg-amber-50 flex items-center justify-center"
                        >
                            <Lightbulb size={16} class="text-amber-600" />
                        </div>
                        <h3 class="text-sm font-bold text-gray-900">
                            Key Takeaways
                        </h3>
                    </div>
                    <div
                        class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
                    >
                        <ul class="space-y-3">
                            {#each actionData.key_takeaways as t}
                                <li
                                    class="text-sm text-gray-600 flex items-start gap-2"
                                >
                                    <span class="text-amber-500 mt-1 text-[8px]"
                                        >●</span
                                    >
                                    <div class="flex-1">
                                        <span
                                            >{typeof t === "string"
                                                ? t
                                                : t.takeaway || t}</span
                                        >
                                        {#if typeof t === "object" && t.category}
                                            <span
                                                class="ml-2 text-[9px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded capitalize"
                                                >{t.category}</span
                                            >
                                        {/if}
                                        {#if typeof t === "object" && t.importance}
                                            <span
                                                class="ml-1 text-[9px] font-semibold {t.importance ===
                                                'high'
                                                    ? 'text-red-600 bg-red-50'
                                                    : t.importance === 'medium'
                                                      ? 'text-amber-600 bg-amber-50'
                                                      : 'text-gray-500 bg-gray-50'} px-1.5 py-0.5 rounded"
                                                >{t.importance}</span
                                            >
                                        {/if}
                                    </div>
                                </li>
                            {/each}
                        </ul>
                    </div>
                </div>
            {/if}

            <!-- FOLLOW-UPS SECTION -->
            {#if activeSection === "followups" && actionData.follow_ups?.length}
                <div>
                    <div class="flex items-center gap-2 mb-4">
                        <div
                            class="w-8 h-8 rounded-xl bg-purple-50 flex items-center justify-center"
                        >
                            <RotateCcw size={16} class="text-purple-600" />
                        </div>
                        <h3 class="text-sm font-bold text-gray-900">
                            Follow-ups
                        </h3>
                    </div>
                    <div
                        class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
                    >
                        <ul class="space-y-3">
                            {#each actionData.follow_ups as f}
                                <li
                                    class="text-sm text-gray-600 flex items-start gap-2"
                                >
                                    <span
                                        class="text-purple-500 mt-1 text-[8px]"
                                        >●</span
                                    >
                                    <div class="flex-1">
                                        <span
                                            >{typeof f === "string"
                                                ? f
                                                : f.item || f}</span
                                        >
                                        {#if typeof f === "object" && f.owner}
                                            <span
                                                class="ml-2 text-[9px] font-semibold text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded"
                                                >👤 {f.owner}</span
                                            >
                                        {/if}
                                        {#if typeof f === "object" && f.urgency}
                                            <span
                                                class="ml-1 text-[9px] font-semibold {f.urgency ===
                                                'immediate'
                                                    ? 'text-red-600 bg-red-50'
                                                    : f.urgency === 'this-week'
                                                      ? 'text-amber-600 bg-amber-50'
                                                      : 'text-gray-500 bg-gray-50'} px-1.5 py-0.5 rounded"
                                                >{f.urgency}</span
                                            >
                                        {/if}
                                        {#if typeof f === "object" && f.context}
                                            <p
                                                class="text-[11px] text-gray-400 mt-0.5"
                                            >
                                                {f.context}
                                            </p>
                                        {/if}
                                    </div>
                                </li>
                            {/each}
                        </ul>
                    </div>
                </div>
            {/if}

            <!-- RISKS SECTION -->
            {#if activeSection === "risks" && actionData.risks_identified?.length}
                <div>
                    <div class="flex items-center gap-2 mb-4">
                        <div
                            class="w-8 h-8 rounded-xl bg-red-50 flex items-center justify-center"
                        >
                            <AlertCircle size={16} class="text-red-600" />
                        </div>
                        <h3 class="text-sm font-bold text-gray-900">
                            Risks Identified
                        </h3>
                    </div>
                    <div class="grid md:grid-cols-2 gap-3">
                        {#each actionData.risks_identified as r}
                            <div
                                class="bg-white rounded-2xl border border-red-100 shadow-sm p-5 hover:shadow-md transition-all"
                            >
                                <p
                                    class="text-sm font-semibold text-gray-900 flex items-start gap-2"
                                >
                                    <AlertCircle
                                        size={14}
                                        class="text-red-500 mt-0.5 flex-shrink-0"
                                    />
                                    {r.risk || r}
                                </p>
                                <div
                                    class="text-[11px] text-gray-400 mt-2 ml-5 space-y-0.5"
                                >
                                    {#if r.impact}
                                        <p>
                                            <span
                                                class="font-medium text-gray-500"
                                                >Impact:</span
                                            >
                                            <span
                                                class="font-semibold {r.impact ===
                                                'high'
                                                    ? 'text-red-600'
                                                    : r.impact === 'medium'
                                                      ? 'text-amber-600'
                                                      : 'text-gray-500'}"
                                                >{r.impact}</span
                                            >
                                        </p>
                                    {/if}
                                    {#if r.mitigation}
                                        <p>
                                            <span
                                                class="font-medium text-emerald-500"
                                                >Mitigation:</span
                                            >
                                            {r.mitigation}
                                        </p>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}
        {/if}
    {/if}
</div>

<!-- ═══════════ FOLLOW-UP EMAIL MODAL ═══════════ -->
{#if showEmailModal}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
        class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        on:click|self={closeEmailModal}
    >
        <div
            class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
        >
            <!-- Modal Header -->
            <div
                class="flex items-center justify-between px-6 py-4 border-b border-gray-100"
            >
                <div class="flex items-center gap-3">
                    <div
                        class="w-10 h-10 rounded-xl bg-violet-100 flex items-center justify-center"
                    >
                        <Mail size={20} class="text-violet-600" />
                    </div>
                    <div>
                        <h2 class="text-lg font-bold text-gray-900">
                            Follow-up Email
                        </h2>
                        <p class="text-xs text-gray-400">
                            AI-generated • Review and send
                        </p>
                    </div>
                </div>
                <button
                    on:click={closeEmailModal}
                    class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                >
                    <X size={18} class="text-gray-400" />
                </button>
            </div>

            {#if generatingEmail}
                <div class="flex-1 flex items-center justify-center py-20">
                    <div class="text-center">
                        <Loader2
                            size={32}
                            class="animate-spin text-violet-500 mx-auto mb-3"
                        />
                        <p class="text-sm font-medium text-gray-600">
                            Generating follow-up email...
                        </p>
                        <p class="text-xs text-gray-400 mt-1">
                            Analyzing meeting summary & action items
                        </p>
                    </div>
                </div>
            {:else if emailSent}
                <div class="flex-1 flex items-center justify-center py-20">
                    <div class="text-center">
                        <div
                            class="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4"
                        >
                            <Check size={32} class="text-emerald-600" />
                        </div>
                        <h3 class="text-lg font-bold text-gray-900 mb-1">
                            Email Sent!
                        </h3>
                        <p class="text-sm text-gray-500">
                            Follow-up email sent to {emailRecipients.filter(
                                (r) => r.includes("@"),
                            ).length} recipient(s)
                        </p>
                        <button
                            on:click={closeEmailModal}
                            class="mt-6 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-6 py-2.5 rounded-xl text-sm transition-colors"
                            >Done</button
                        >
                    </div>
                </div>
            {:else}
                <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
                    <!-- Recipients -->
                    <div>
                        <label
                            class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-2"
                            >Recipients</label
                        >
                        {#each emailRecipients as recipient, idx}
                            <div class="flex items-center gap-2 mb-2">
                                <input
                                    type="email"
                                    bind:value={emailRecipients[idx]}
                                    placeholder="email@example.com"
                                    class="flex-1 px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all"
                                />
                                {#if emailRecipients.length > 1}
                                    <button
                                        on:click={() => removeRecipient(idx)}
                                        class="p-2 hover:bg-red-50 rounded-lg transition-colors"
                                    >
                                        <Trash2
                                            size={14}
                                            class="text-red-400"
                                        />
                                    </button>
                                {/if}
                            </div>
                        {/each}
                        <button
                            on:click={addRecipient}
                            class="text-xs font-medium text-violet-600 hover:text-violet-700 inline-flex items-center gap-1 mt-1 transition-colors"
                        >
                            <Plus size={12} /> Add recipient
                        </button>
                    </div>

                    <!-- Subject -->
                    <div>
                        <label
                            class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-2"
                            >Subject</label
                        >
                        <input
                            type="text"
                            bind:value={emailSubject}
                            class="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all font-medium"
                        />
                    </div>

                    <!-- Body -->
                    <div>
                        <label
                            class="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-2"
                            >Email Body</label
                        >
                        <textarea
                            bind:value={emailBody}
                            rows="14"
                            class="w-full px-3.5 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all leading-relaxed resize-none font-mono"
                        ></textarea>
                    </div>
                </div>

                <!-- Modal Footer -->
                <div
                    class="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50/50"
                >
                    <button
                        on:click={copyEmailToClipboard}
                        class="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-700 px-3 py-2 hover:bg-gray-100 rounded-xl transition-all"
                    >
                        {#if emailCopied}
                            <Check size={14} class="text-emerald-500" /> Copied!
                        {:else}
                            <Copy size={14} /> Copy to clipboard
                        {/if}
                    </button>
                    <div class="flex items-center gap-3">
                        <button
                            on:click={closeEmailModal}
                            class="text-sm font-medium text-gray-500 hover:text-gray-700 px-4 py-2.5 hover:bg-gray-100 rounded-xl transition-all"
                            >Cancel</button
                        >
                        <button
                            on:click={sendFollowupEmail}
                            disabled={sendingEmail}
                            class="bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300 text-white font-medium px-5 py-2.5 rounded-xl text-sm inline-flex items-center gap-2 transition-all shadow-sm"
                        >
                            {#if sendingEmail}
                                <Loader2 size={14} class="animate-spin" /> Sending…
                            {:else}
                                <Send size={14} /> Send Email
                            {/if}
                        </button>
                    </div>
                </div>
            {/if}
        </div>
    </div>
{/if}
