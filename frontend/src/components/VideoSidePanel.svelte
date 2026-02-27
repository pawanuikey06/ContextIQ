<script>
    import { X } from "lucide-svelte";
    import { api } from "../lib/api.js";
    import { shortId, formatTime } from "../lib/utils.js";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";

    /** @type {string} Meeting ID whose video to play */
    export let meetingId;
    /** @type {number} Seek time in seconds */
    export let startTime = 0;

    const dispatch = createEventDispatcher();

    let videoElement = null;
    let prevMeetingId = null;
    let prevStartTime = null;

    onMount(() => {
        if (videoElement) {
            videoElement.src = api.video(meetingId);
            prevMeetingId = meetingId;
            prevStartTime = startTime;
        }
    });

    // Called when video metadata is ready — seek to target time
    function handleLoadedMetadata() {
        if (videoElement && startTime > 0) {
            videoElement.currentTime = startTime;
        }
    }

    // Watch for prop changes after initial mount
    export function seekTo(newMeetingId, newStartTime) {
        if (!videoElement) return;

        if (newMeetingId !== prevMeetingId) {
            // Different meeting — change source
            prevMeetingId = newMeetingId;
            prevStartTime = newStartTime;
            videoElement.src = api.video(newMeetingId);
            // loadedmetadata will fire and handle seeking
        } else if (newStartTime !== prevStartTime) {
            // Same meeting, different time — just seek
            prevStartTime = newStartTime;
            videoElement.currentTime = newStartTime;
        }
    }

    function close() {
        if (videoElement) {
            videoElement.pause();
        }
        dispatch("close");
    }

    onDestroy(() => {
        if (videoElement) {
            videoElement.pause();
        }
    });
</script>

<div
    class="w-[400px] border-l border-surface-200/60 bg-white flex flex-col flex-shrink-0"
>
    <!-- Panel Header -->
    <div
        class="px-4 py-3 border-b border-surface-200/60 flex items-center justify-between"
    >
        <div>
            <p class="text-sm font-semibold text-txt-primary">Video Playback</p>
            <p class="text-[11px] text-txt-faint">
                Meeting {shortId(meetingId)}
            </p>
        </div>
        <button
            class="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-surface-100 transition-colors text-txt-muted hover:text-txt-primary"
            on:click={close}
            title="Close video"
        >
            <X size={16} />
        </button>
    </div>

    <!-- Video Player -->
    <div class="flex-1 flex flex-col p-3 overflow-hidden">
        <div class="rounded-xl overflow-hidden bg-black shadow-lg">
            <video
                bind:this={videoElement}
                controls
                preload="auto"
                class="w-full"
                on:loadedmetadata={handleLoadedMetadata}
            >
                <track kind="captions" />
            </video>
        </div>
        <p class="text-[11px] text-txt-faint mt-2 text-center">
            Seeked to {formatTime(startTime)}
        </p>
    </div>
</div>
