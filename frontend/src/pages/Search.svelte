<script>
    import { onMount } from "svelte";
    import { push } from "svelte-spa-router";
    import {
        Search,
        Loader2,
        FileText,
        Clock,
        Users,
        ArrowUpRight,
        X,
    } from "lucide-svelte";
    import { api, get } from "../lib/api.js";
    import { formatTime } from "../lib/utils.js";

    let query = "";
    let results = [];
    let searching = false;
    let searched = false;
    let searchTimeout = null;

    function debounceSearch() {
        clearTimeout(searchTimeout);
        if (query.trim().length < 2) {
            results = [];
            searched = false;
            return;
        }
        searchTimeout = setTimeout(doSearch, 350);
    }

    async function doSearch() {
        if (query.trim().length < 2) return;
        searching = true;
        searched = true;
        try {
            const res = await get(api.search(query.trim()));
            results = res.results || [];
        } catch {
            results = [];
        }
        searching = false;
    }

    function clearSearch() {
        query = "";
        results = [];
        searched = false;
    }

    function openMeeting(id) {
        push(`/meetings/${id}`);
    }

    function highlightText(text, query) {
        if (!query || !text) return text;
        const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        return text.replace(
            new RegExp(`(${escaped})`, "gi"),
            '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>',
        );
    }
</script>

<div class="max-w-4xl mx-auto px-6 py-10">
    <!-- Header -->
    <div class="mb-8">
        <p
            class="text-emerald-600 text-xs font-bold uppercase tracking-[0.15em] mb-1"
        >
            Search
        </p>
        <h1 class="text-2xl font-extrabold text-gray-900">Search Meetings</h1>
        <p class="text-sm text-gray-400 mt-1">
            Search across all transcripts, speaker names, and titles
        </p>
    </div>

    <!-- Search Input -->
    <div class="relative mb-8">
        <div
            class="absolute inset-y-0 left-4 flex items-center pointer-events-none"
        >
            {#if searching}
                <Loader2 size={18} class="text-emerald-500 animate-spin" />
            {:else}
                <Search size={18} class="text-gray-400" />
            {/if}
        </div>
        <input
            type="text"
            bind:value={query}
            on:input={debounceSearch}
            on:keydown={(e) => e.key === "Enter" && doSearch()}
            placeholder="Search by keyword, speaker, or topic..."
            class="w-full pl-12 pr-12 py-4 bg-white border border-gray-200 rounded-2xl text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
        />
        {#if query}
            <button
                class="absolute inset-y-0 right-4 flex items-center text-gray-400 hover:text-gray-600"
                on:click={clearSearch}
            >
                <X size={16} />
            </button>
        {/if}
    </div>

    <!-- Results -->
    {#if searching}
        <div class="flex items-center justify-center py-20 text-gray-400">
            <Loader2 size={24} class="animate-spin mr-3" />
            Searching transcripts...
        </div>
    {:else if searched && results.length === 0}
        <div class="text-center py-20">
            <div
                class="w-14 h-14 mx-auto rounded-2xl bg-gray-50 flex items-center justify-center mb-4"
            >
                <Search size={24} class="text-gray-300" />
            </div>
            <p class="font-semibold text-gray-700">No results found</p>
            <p class="text-sm text-gray-400 mt-1">
                Try a different keyword or check spelling
            </p>
        </div>
    {:else if results.length > 0}
        <div class="space-y-3">
            <p class="text-xs text-gray-400 font-medium mb-4">
                Found <span class="font-bold text-gray-700"
                    >{results.length}</span
                >
                meeting{results.length !== 1 ? "s" : ""} matching "<span
                    class="text-emerald-600">{query}</span
                >"
            </p>
            {#each results as result}
                <button
                    class="w-full text-left bg-white border border-gray-100 rounded-2xl p-5 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group"
                    on:click={() => openMeeting(result.id)}
                >
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex-1 min-w-0 pr-4">
                            <h3
                                class="font-bold text-gray-900 text-sm group-hover:text-emerald-600 transition-colors truncate"
                            >
                                {result.title}
                            </h3>
                            <div class="flex items-center gap-3 mt-1">
                                {#if result.date}
                                    <span
                                        class="text-[11px] text-gray-400 flex items-center gap-1"
                                    >
                                        <Clock size={10} />
                                        {result.date}
                                    </span>
                                {/if}
                                <span
                                    class="text-[11px] text-gray-400 flex items-center gap-1"
                                >
                                    <Users size={10} />
                                    {result.speaker_count} speaker{result.speaker_count !==
                                    1
                                        ? "s"
                                        : ""}
                                </span>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 flex-shrink-0">
                            <span
                                class="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full"
                            >
                                {result.score} match{result.score !== 1
                                    ? "es"
                                    : ""}
                            </span>
                            <ArrowUpRight
                                size={14}
                                class="text-gray-300 group-hover:text-emerald-500 transition-colors"
                            />
                        </div>
                    </div>

                    <!-- Snippets -->
                    {#if result.snippets?.length}
                        <div class="space-y-2">
                            {#each result.snippets as snippet}
                                <div
                                    class="bg-gray-50 rounded-lg px-3 py-2 text-[12px] text-gray-600 border-l-2 border-emerald-300"
                                >
                                    <span
                                        class="font-semibold text-emerald-600 mr-2"
                                        >{snippet.speaker}</span
                                    >
                                    <span
                                        class="font-mono text-[10px] text-gray-400 mr-2"
                                        >{formatTime(snippet.start)}</span
                                    >
                                    <!-- svelte-ignore a11y-missing-attribute -->
                                    {@html highlightText(
                                        snippet.snippet,
                                        query,
                                    )}
                                </div>
                            {/each}
                        </div>
                    {/if}
                </button>
            {/each}
        </div>
    {:else if !searching && !searched}
        <div class="text-center py-20 text-gray-400">
            <Search size={40} class="mx-auto mb-4 opacity-30" />
            <p class="text-sm">Start typing to search across all meetings</p>
        </div>
    {/if}
</div>
