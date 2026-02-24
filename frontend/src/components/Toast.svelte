<script>
    import { toasts } from "../lib/toast.js";
    import {
        X,
        CheckCircle,
        AlertCircle,
        Info,
        AlertTriangle,
    } from "lucide-svelte";

    const icons = {
        success: CheckCircle,
        error: AlertCircle,
        info: Info,
        warning: AlertTriangle,
    };

    const colors = {
        success: "bg-emerald-50 border-emerald-200 text-emerald-800",
        error: "bg-red-50 border-red-200 text-red-800",
        info: "bg-blue-50 border-blue-200 text-blue-800",
        warning: "bg-amber-50 border-amber-200 text-amber-800",
    };

    const iconColors = {
        success: "text-emerald-500",
        error: "text-red-500",
        info: "text-blue-500",
        warning: "text-amber-500",
    };
</script>

<div class="fixed top-20 right-4 z-[100] flex flex-col gap-2 max-w-sm">
    {#each $toasts as toast (toast.id)}
        <div
            class="flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-sm animate-slide-in {colors[
                toast.type
            ] || colors.info}"
            role="alert"
        >
            <svelte:component
                this={icons[toast.type] || icons.info}
                size={18}
                class={iconColors[toast.type] || iconColors.info}
            />
            <p class="text-sm font-medium flex-1">{toast.message}</p>
            <button
                class="opacity-50 hover:opacity-100 transition-opacity flex-shrink-0"
                on:click={() => toasts.remove(toast.id)}
            >
                <X size={14} />
            </button>
        </div>
    {/each}
</div>

<style>
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(100%) scale(0.95);
        }
        to {
            opacity: 1;
            transform: translateX(0) scale(1);
        }
    }

    :global(.animate-slide-in) {
        animation: slideIn 0.3s ease-out;
    }
</style>
