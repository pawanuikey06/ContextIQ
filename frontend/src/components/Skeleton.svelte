<!-- Animated shimmer skeleton pill. Use via width/height/rounded props or class override. -->
<script>
    export let width = "100%";
    export let height = "1rem";
    export let rounded = "rounded-lg";
    export let className = "";
</script>

<div
    class="animate-pulse bg-gradient-to-r from-gray-100 via-gray-200 to-gray-100 bg-[length:200%_100%] {rounded} {className}"
    style="width:{width};height:{height}"
    aria-hidden="true"
></div>

<style>
    div {
        animation: shimmer 1.6s ease-in-out infinite;
        background-size: 200% 100%;
    }
    @keyframes shimmer {
        0% {
            background-position: 200% center;
        }
        100% {
            background-position: -200% center;
        }
    }
</style>
