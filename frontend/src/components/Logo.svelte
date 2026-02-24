<script>
    export let size = 24;
    export let className = "";
</script>

<!-- ContextIQ Logo: Stylized nodes/connections representing meeting intelligence -->
<svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    class={className}
>
    <!-- Outer ring -->
    <circle
        cx="16"
        cy="16"
        r="14"
        stroke="currentColor"
        stroke-width="1.5"
        opacity="0.3"
    />

    <!-- Central hexagon shape -->
    <path
        d="M16 4 L26 10 L26 22 L16 28 L6 22 L6 10 Z"
        stroke="currentColor"
        stroke-width="1.5"
        fill="none"
        opacity="0.6"
    />

    <!-- Inner connections -->
    <line
        x1="16"
        y1="4"
        x2="16"
        y2="28"
        stroke="currentColor"
        stroke-width="1"
        opacity="0.3"
    />
    <line
        x1="6"
        y1="10"
        x2="26"
        y2="22"
        stroke="currentColor"
        stroke-width="1"
        opacity="0.3"
    />
    <line
        x1="26"
        y1="10"
        x2="6"
        y2="22"
        stroke="currentColor"
        stroke-width="1"
        opacity="0.3"
    />

    <!-- Node dots -->
    <circle cx="16" cy="4" r="2.5" fill="currentColor" />
    <circle cx="26" cy="10" r="2.5" fill="currentColor" />
    <circle cx="26" cy="22" r="2.5" fill="currentColor" />
    <circle cx="16" cy="28" r="2.5" fill="currentColor" />
    <circle cx="6" cy="22" r="2.5" fill="currentColor" />
    <circle cx="6" cy="10" r="2.5" fill="currentColor" />

    <!-- Center pulse dot -->
    <circle cx="16" cy="16" r="3.5" fill="currentColor" opacity="0.9" />
    <circle
        cx="16"
        cy="16"
        r="5.5"
        stroke="currentColor"
        stroke-width="1"
        opacity="0.4"
    />
</svg>
