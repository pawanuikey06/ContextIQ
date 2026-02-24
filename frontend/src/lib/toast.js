import { writable } from 'svelte/store';

function createToastStore() {
    const { subscribe, update } = writable([]);
    let id = 0;

    function add(type, message, duration = 4000) {
        const toast = { id: ++id, type, message };
        update(toasts => [...toasts, toast]);
        setTimeout(() => remove(toast.id), duration);
        return toast.id;
    }

    function remove(toastId) {
        update(toasts => toasts.filter(t => t.id !== toastId));
    }

    return {
        subscribe,
        success: (msg) => add('success', msg),
        error: (msg) => add('error', msg, 6000),
        info: (msg) => add('info', msg),
        warning: (msg) => add('warning', msg, 5000),
        remove,
    };
}

export const toasts = createToastStore();
