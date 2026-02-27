<script>
    import { onMount } from "svelte";
    import { Volume2, VolumeX, Loader2 } from "lucide-svelte";
    import { api } from "../lib/api.js";

    /** @type {string} Meeting ID */
    export let meetingId;
    /** @type {string} Speaker ID (e.g. SPEAKER_00_m1) */
    export let speakerId;

    let playing = false;
    let loading = false;
    let audioEl = null;
    let clipAvailable = null; // null = checking, true/false = known
    let errorMsg = "";

    onMount(async () => {
        // Check if clip exists via HEAD request
        try {
            const res = await fetch(api.speakerClip(meetingId, speakerId), {
                method: "HEAD",
            });
            clipAvailable = res.ok;
        } catch {
            clipAvailable = false;
        }
    });

    async function togglePlay() {
        if (!audioEl || !clipAvailable) return;

        if (playing) {
            audioEl.pause();
            audioEl.currentTime = 0;
            playing = false;
        } else {
            loading = true;
            errorMsg = "";
            try {
                audioEl.src = api.speakerClip(meetingId, speakerId);
                await audioEl.play();
                playing = true;
            } catch (err) {
                errorMsg = "Playback failed";
                console.warn("Playback failed for", speakerId, err);
            }
            loading = false;
        }
    }

    function handleEnded() {
        playing = false;
    }
</script>

{#if clipAvailable === null}
    <span
        class="inline-flex items-center gap-1 px-2 py-1 text-[10px] text-txt-faint"
    >
        <Loader2 size={10} class="animate-spin" /> Checking…
    </span>
{:else if clipAvailable}
    <button
        class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all duration-200 {playing
            ? 'bg-brand-100 text-brand-700 ring-1 ring-brand-300'
            : 'bg-surface-100 text-txt-muted hover:bg-brand-50 hover:text-brand-600'}"
        on:click={togglePlay}
        title={playing ? "Stop" : "Play speaker voice sample"}
    >
        {#if loading}
            <Loader2 size={10} class="animate-spin" />
        {:else}
            <Volume2 size={10} />
        {/if}
        {playing ? "Playing…" : "▶ Listen"}
    </button>
    {#if errorMsg}
        <span class="text-[9px] text-red-500 ml-1">{errorMsg}</span>
    {/if}
{:else}
    <span
        class="inline-flex items-center gap-1 px-2 py-1 text-[10px] text-txt-faint opacity-50"
    >
        <VolumeX size={10} /> No clip
    </span>
{/if}

<audio bind:this={audioEl} on:ended={handleEnded} preload="none" class="hidden">
    <track kind="captions" />
</audio>
