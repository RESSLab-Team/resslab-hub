/**
 * Stroke icons for the contribution screens.
 *
 * The pipeline design is built on stroked outlines (as is ToolSelect's chevron),
 * while `v-icon` renders filled Material paths — mixing them reads as two
 * different icon sets on the same page. Only the glyphs these screens use are
 * defined here.
 */
export const CP_ICON_PATHS = {
  arrowLeft: 'M19 12H5M12 19l-7-7 7-7',
  arrowRight: 'M5 12h14M12 5l7 7-7 7',
  chevronRight: 'M9 18l6-6-6-6',
  chevronDown: 'M6 9l6 6 6-6',
  check: 'M20 6L9 17l-5-5',
  close: 'M18 6L6 18M6 6l12 12',
  alert:
    'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01',
  info: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 16v-4M12 8h.01',
  upload: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12',
  lock: 'M19 11H5v11h14V11zM7 11V7a5 5 0 0110 0v4',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  layers: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  send: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z',
  save: 'M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2zM17 21v-8H7v8M7 3v5h8'
} as const

export type CpIconName = keyof typeof CP_ICON_PATHS
