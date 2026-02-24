<script>
    import { onMount } from "svelte";
    import {
        Send,
        Loader2,
        Trash2,
        Database,
        ChevronDown,
        Sparkles,
        Bot,
        User,
    } from "lucide-svelte";
    import { api, get, post } from "../lib/api.js";
    import { shortId, formatTime } from "../lib/utils.js";

    let sessionId = crypto.randomUUID();
    let messages = [];
    let input = "";
    let sending = false;
    let chatContainer;

    let indexedMeetings = [];
    let selectedMeetings = [];
    let indexingAll = false;

    const quickPrompts = [
        "Summarize all my meetings",
        "What action items were discussed?",
        "What did each speaker talk about?",
        "What were the key decisions made?",
    ];

    onMount(async () => {
        await loadIndexedMeetings();
    });

    async function loadIndexedMeetings() {
        try {
            const res = await get(api.chat.meetings);
            indexedMeetings = res.indexed_meetings || [];
            selectedMeetings = [...indexedMeetings];
        } catch {
            indexedMeetings = [];
        }
    }

    async function indexAllMeetings() {
        indexingAll = true;
        try {
            // Get all meetings
            const allRes = await get(api.meetings);
            const allMeetings = (allRes.meetings || []).map((m) => m.id);
            // Get already indexed
            const idxRes = await get(api.chat.meetings);
            const alreadyIndexed = new Set(idxRes.indexed_meetings || []);
            // Index only un-indexed meetings
            for (const mid of allMeetings) {
                if (!alreadyIndexed.has(mid)) {
                    await post(api.chat.index(mid), null, 30000);
                }
            }
            await loadIndexedMeetings();
        } catch (err) {
            console.error("Index failed:", err);
        }
        indexingAll = false;
    }

    function newChat() {
        messages = [];
        sessionId = crypto.randomUUID();
        try {
            post(api.chat.clear(sessionId));
        } catch {}
    }

    function toggleMeeting(mid) {
        if (selectedMeetings.includes(mid)) {
            selectedMeetings = selectedMeetings.filter((m) => m !== mid);
        } else {
            selectedMeetings = [...selectedMeetings, mid];
        }
    }

    async function sendMessage(text = null) {
        const question = text || input.trim();
        if (!question || sending) return;

        input = "";
        messages = [...messages, { role: "user", content: question }];
        sending = true;

        setTimeout(() => {
            if (chatContainer)
                chatContainer.scrollTop = chatContainer.scrollHeight;
        }, 50);

        try {
            const payload = { question, session_id: sessionId };
            if (selectedMeetings.length > 0) {
                payload.meeting_ids = selectedMeetings;
            }

            const response = await fetch(api.chat.ask, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) throw new Error(await response.text());

            let fullAnswer = [];
            let citations = [];
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            messages = [
                ...messages,
                { role: "assistant", content: "", citations: [] },
            ];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n");

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    try {
                        const event = JSON.parse(line.slice(6));
                        if (event.type === "token") {
                            fullAnswer.push(event.content);
                            messages[messages.length - 1].content =
                                fullAnswer.join("");
                            messages = [...messages];
                        } else if (event.type === "citations") {
                            citations = event.content || [];
                        } else if (event.type === "done") {
                            break;
                        } else if (event.type === "error") {
                            fullAnswer.push(`\n\nError: ${event.content}`);
                        }
                    } catch {}
                }

                if (chatContainer)
                    chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            messages[messages.length - 1].content =
                fullAnswer.join("") || "Sorry, I couldn't find an answer.";
            messages[messages.length - 1].citations = citations;
            messages = [...messages];
        } catch (err) {
            messages = [
                ...messages,
                {
                    role: "assistant",
                    content: `Error: ${err.message}. Make sure the backend is running.`,
                    citations: [],
                },
            ];
        }

        sending = false;
        setTimeout(() => {
            if (chatContainer)
                chatContainer.scrollTop = chatContainer.scrollHeight;
        }, 50);
    }

    function handleKeydown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }
</script>

<div class="flex h-[calc(100vh-56px)]">
    <!-- Sidebar -->
    <aside
        class="w-60 border-r border-surface-200/60 bg-white flex flex-col flex-shrink-0"
    >
        <div class="p-4 border-b border-surface-200/60">
            <p class="section-label flex items-center gap-1.5">
                <Database size={11} class="text-brand-600" />
                Knowledge Base
            </p>
        </div>

        <div class="flex-1 overflow-y-auto p-3 space-y-0.5">
            {#if indexedMeetings.length === 0}
                <p class="text-[11px] text-txt-faint p-2">
                    No meetings indexed yet.
                </p>
            {:else}
                {#each indexedMeetings as mid}
                    <label
                        class="flex items-center gap-2.5 px-2.5 py-2 rounded-xl hover:bg-surface-50 cursor-pointer transition-colors"
                    >
                        <input
                            type="checkbox"
                            checked={selectedMeetings.includes(mid)}
                            on:change={() => toggleMeeting(mid)}
                            class="rounded accent-brand-600"
                        />
                        <span class="text-xs text-txt-muted truncate"
                            >{shortId(mid)}</span
                        >
                    </label>
                {/each}
            {/if}
        </div>

        <div class="p-3 border-t border-surface-200/60 space-y-1.5">
            <button
                class="btn-primary w-full text-xs justify-center !py-2 !rounded-xl"
                on:click={indexAllMeetings}
                disabled={indexingAll}
            >
                {#if indexingAll}
                    <Loader2 size={12} class="animate-spin" /> Indexing…
                {:else}
                    <Database size={12} /> Index All
                {/if}
            </button>
            <button
                class="btn-secondary w-full text-xs justify-center !py-2 !rounded-xl"
                on:click={newChat}
            >
                <Trash2 size={12} /> New Chat
            </button>
        </div>
    </aside>

    <!-- Main Area -->
    <div class="flex-1 flex flex-col bg-surface-50">
        <!-- Chat Header -->
        <div class="px-6 py-3.5 border-b border-surface-200/60 bg-white">
            <h1 class="text-base font-semibold text-txt-primary">AI Chat</h1>
            <p class="text-[11px] text-txt-faint">
                Ask questions across all your meetings
            </p>
        </div>

        <!-- Messages -->
        <div class="flex-1 overflow-y-auto px-6 py-6" bind:this={chatContainer}>
            {#if messages.length === 0}
                <div class="max-w-xl mx-auto mt-20 text-center">
                    <div
                        class="w-12 h-12 mx-auto rounded-2xl bg-brand-100 flex items-center justify-center mb-4"
                    >
                        <Sparkles size={22} class="text-brand-600" />
                    </div>
                    <h2 class="text-base font-semibold text-txt-primary mb-1">
                        What would you like to know?
                    </h2>
                    <p class="text-sm text-txt-faint mb-6">
                        Ask about your meeting transcripts
                    </p>
                    <div class="grid grid-cols-2 gap-2 max-w-md mx-auto">
                        {#each quickPrompts as prompt}
                            <button
                                class="card text-left text-[13px] text-txt-secondary hover:border-brand-300 hover:shadow-md transition-all !p-3.5"
                                on:click={() => sendMessage(prompt)}
                            >
                                {prompt}
                            </button>
                        {/each}
                    </div>
                </div>
            {:else}
                <div class="max-w-2xl mx-auto space-y-4">
                    {#each messages as msg}
                        {#if msg.role === "user"}
                            <div class="flex justify-end gap-2.5">
                                <div
                                    class="bg-brand-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md max-w-md text-sm shadow-sm"
                                >
                                    {msg.content}
                                </div>
                                <div
                                    class="w-8 h-8 rounded-full bg-emerald-700 flex items-center justify-center flex-shrink-0 mt-1 shadow-sm"
                                >
                                    <User size={14} class="text-white" />
                                </div>
                            </div>
                        {:else}
                            <div class="flex justify-start gap-2.5">
                                <div
                                    class="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center flex-shrink-0 mt-1 shadow-sm"
                                >
                                    <Bot size={14} class="text-emerald-400" />
                                </div>
                                <div class="card max-w-lg !shadow-sm">
                                    <p
                                        class="text-sm text-txt-secondary leading-relaxed whitespace-pre-wrap"
                                    >
                                        {msg.content}
                                    </p>
                                    {#if msg.citations?.length}
                                        <details
                                            class="mt-3 pt-3 border-t border-surface-200/60"
                                        >
                                            <summary
                                                class="text-[11px] text-txt-faint cursor-pointer flex items-center gap-1 select-none"
                                            >
                                                <ChevronDown size={11} />
                                                Sources ({msg.citations.length})
                                            </summary>
                                            <div class="mt-2 space-y-1.5">
                                                {#each msg.citations as c}
                                                    <div
                                                        class="text-[11px] text-txt-faint bg-surface-50 rounded-lg p-2.5"
                                                    >
                                                        <span
                                                            class="font-medium text-txt-muted"
                                                            >{c.speaker}</span
                                                        >
                                                        <span class="mx-1"
                                                            >·</span
                                                        >
                                                        <span class="font-mono"
                                                            >{formatTime(
                                                                c.start,
                                                            )}</span
                                                        >
                                                        <span class="mx-1"
                                                            >·</span
                                                        >
                                                        <span
                                                            >Meeting {shortId(
                                                                c.meeting_id,
                                                            )}</span
                                                        >
                                                        <p
                                                            class="mt-1 text-txt-secondary italic"
                                                        >
                                                            "{c.excerpt}"
                                                        </p>
                                                    </div>
                                                {/each}
                                            </div>
                                        </details>
                                    {/if}
                                </div>
                            </div>
                        {/if}
                    {/each}

                    {#if sending}
                        <div class="flex justify-start">
                            <div class="card !py-3 !px-4">
                                <Loader2
                                    size={16}
                                    class="text-brand-600 animate-spin"
                                />
                            </div>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>

        <!-- Input -->
        <div class="px-6 py-3.5 border-t border-surface-200/60 bg-white">
            <div class="max-w-2xl mx-auto flex items-center gap-2.5">
                <input
                    type="text"
                    class="input flex-1"
                    placeholder="Ask about your meetings…"
                    bind:value={input}
                    on:keydown={handleKeydown}
                    disabled={sending}
                />
                <button
                    class="btn-primary !px-3 !py-2.5"
                    on:click={() => sendMessage()}
                    disabled={sending || !input.trim()}
                >
                    <Send size={16} />
                </button>
            </div>
        </div>
    </div>
</div>
