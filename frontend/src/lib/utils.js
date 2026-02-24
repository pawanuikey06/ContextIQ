/** Format seconds to mm:ss */
export function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Format duration in seconds to human string */
export function formatDuration(seconds) {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return `${h}h ${rm}m`;
}

/** Get speaker color class index */
export function speakerColorIndex(speaker, speakerList) {
  const idx = speakerList.indexOf(speaker);
  return idx >= 0 ? idx % 6 : 0;
}

/** Speaker dot colors */
export const SPEAKER_COLORS = [
  '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4',
];

/** Truncate meeting ID for display */
export function shortId(id) {
  return id ? id.substring(0, 8) + '...' : '';
}
