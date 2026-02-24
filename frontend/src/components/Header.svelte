<script>
    import { Video, MessageSquare, Target, Home } from "lucide-svelte";
    import { location } from "svelte-spa-router";
    import Logo from "./Logo.svelte";

    const navItems = [
        { path: "/", label: "Home", icon: Home },
        { path: "/meetings", label: "Meetings", icon: Video },
        { path: "/actions", label: "Action Items", icon: Target },
        { path: "/chat", label: "AI Chat", icon: MessageSquare },
    ];

    $: loc = $location;
</script>

<header class="bg-[#052e1c] sticky top-0 z-50 border-b border-emerald-900/30">
    <div class="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
        <!-- Logo -->
        <a
            href="#/"
            class="flex items-center gap-2.5 hover:opacity-90 transition-opacity no-underline"
        >
            <Logo size={26} className="text-emerald-400" />
            <span class="font-extrabold text-lg tracking-tight">
                <span class="text-white">Context</span><span
                    class="text-emerald-400">IQ</span
                >
            </span>
        </a>

        <!-- Nav -->
        <nav class="flex items-center gap-1">
            {#each navItems as item}
                {@const active =
                    item.path === "/"
                        ? loc === "/"
                        : item.path === "/meetings"
                          ? loc.startsWith("/meetings")
                          : loc === item.path}
                <a
                    href="#{item.path}"
                    class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 no-underline
                        {active
                        ? 'bg-emerald-500/20 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.15)]'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'}"
                >
                    <svelte:component this={item.icon} size={16} />
                    {item.label}
                </a>
            {/each}
        </nav>

        <!-- Avatar -->
        <div
            class="h-8 w-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white text-sm font-bold shadow-md"
        >
            P
        </div>
    </div>
</header>
