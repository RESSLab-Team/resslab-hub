/**
 * Shared UI-interaction state.
 *
 * `isBrushDragging` is true while the user is dragging any distribution-brush
 * handle. Dragging one brush cross-filters the whole dashboard, so *every* chart
 * reads this flag to freeze its value axis during the drag — the bars move
 * against a fixed scale (showing how much the data varies) and the axes rescale
 * only once, on pointer-up.
 */
import { ref } from 'vue'

export const isBrushDragging = ref(false)
