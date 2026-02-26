import { writable } from 'svelte/store';

// Currently loaded meeting transcript data
export const meetingData = writable(null);

// Summary data
export const summaryData = writable(null);

// Speaker name mapping
export const speakerMap = writable({});

// Summary approval state
export const summaryApproved = writable(false);

// Action items data
export const actionItemsData = writable(null);

// ── Upload / Processing pipeline state (persists across navigation) ──
export const uploadState = writable({
  uploading: false,
  processing: false,
  progress: '',
  meetingId: null,
});
