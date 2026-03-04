/* ── Highlight Overlay — Visually highlights elements the agent interacts with ──
 *
 * When the QA agent identifies an element (e.g. a broken image, a button without
 * accessible name, a form field with validation error), this overlay draws a
 * pulsing outline around it with a tooltip explaining the issue.
 */

export interface HighlightOptions {
  selector: string;
  label?: string;
  color?: string;        // CSS color, default: '#3B82F6' (blue-500)
  duration?: number;      // ms, 0 = indefinite, default: 4000
  action?: "click" | "type" | "inspect" | "error" | "warning" | "info";
}

const OVERLAY_CLASS = "ba-highlight-overlay";
const TOOLTIP_CLASS = "ba-highlight-tooltip";

// Map action types to colors
const ACTION_COLORS: Record<string, string> = {
  click: "#3B82F6",    // blue
  type: "#8B5CF6",     // purple
  inspect: "#06B6D4",  // cyan
  error: "#EF4444",    // red
  warning: "#F59E0B",  // amber
  info: "#3B82F6",     // blue
};

/** Inject the highlight CSS once */
let styleInjected = false;
function ensureStyles(): void {
  if (styleInjected) return;
  styleInjected = true;

  const style = document.createElement("style");
  style.textContent = `
    .${OVERLAY_CLASS} {
      position: absolute;
      pointer-events: none;
      z-index: 2147483646;
      border: 2px solid var(--ba-hl-color, #3B82F6);
      border-radius: 4px;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
      animation: ba-pulse 1.5s ease-in-out infinite;
      transition: opacity 0.3s ease;
    }

    .${TOOLTIP_CLASS} {
      position: absolute;
      z-index: 2147483647;
      pointer-events: none;
      background: var(--ba-hl-color, #3B82F6);
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 11px;
      font-weight: 500;
      line-height: 1.2;
      padding: 3px 8px;
      border-radius: 4px;
      white-space: nowrap;
      max-width: 300px;
      overflow: hidden;
      text-overflow: ellipsis;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      transition: opacity 0.3s ease;
    }

    @keyframes ba-pulse {
      0%, 100% { opacity: 1; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25); }
      50%      { opacity: 0.7; box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.1); }
    }
  `;
  document.head.appendChild(style);
}

// Track active highlights so we can clear them
const activeHighlights: HTMLElement[] = [];

/** Highlight an element on the page */
export function highlightElement(options: HighlightOptions): void {
  ensureStyles();

  const { selector, label, duration = 4000, action } = options;
  const color = options.color || (action ? ACTION_COLORS[action] : undefined) || "#3B82F6";

  let target: Element | null = null;
  try {
    target = document.querySelector(selector);
  } catch {
    console.warn(`[BA Highlight] Invalid selector: ${selector}`);
    return;
  }

  if (!target) {
    console.warn(`[BA Highlight] Element not found: ${selector}`);
    return;
  }

  const rect = target.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return;

  // ── Overlay box ──
  const overlay = document.createElement("div");
  overlay.className = OVERLAY_CLASS;
  overlay.style.setProperty("--ba-hl-color", color);
  overlay.style.borderColor = color;
  overlay.style.top = `${window.scrollY + rect.top - 2}px`;
  overlay.style.left = `${window.scrollX + rect.left - 2}px`;
  overlay.style.width = `${rect.width + 4}px`;
  overlay.style.height = `${rect.height + 4}px`;
  document.body.appendChild(overlay);
  activeHighlights.push(overlay);

  // ── Tooltip label ──
  if (label) {
    const tooltip = document.createElement("div");
    tooltip.className = TOOLTIP_CLASS;
    tooltip.style.setProperty("--ba-hl-color", color);
    tooltip.style.backgroundColor = color;
    tooltip.textContent = label;

    // Position above the element; if too high, put below
    const tooltipTop = window.scrollY + rect.top - 24;
    if (tooltipTop < window.scrollY + 4) {
      tooltip.style.top = `${window.scrollY + rect.bottom + 4}px`;
    } else {
      tooltip.style.top = `${tooltipTop}px`;
    }
    tooltip.style.left = `${window.scrollX + rect.left}px`;
    document.body.appendChild(tooltip);
    activeHighlights.push(tooltip);
  }

  // Scroll element into view
  target.scrollIntoView({ behavior: "smooth", block: "nearest" });

  // Auto-remove
  if (duration > 0) {
    setTimeout(() => {
      removeHighlight(overlay);
    }, duration);
  }
}

/** Remove a specific highlight element */
function removeHighlight(el: HTMLElement): void {
  el.style.opacity = "0";
  setTimeout(() => {
    el.remove();
    const idx = activeHighlights.indexOf(el);
    if (idx >= 0) activeHighlights.splice(idx, 1);
  }, 300);
}

/** Clear all active highlights */
export function clearHighlights(): void {
  // Also query and remove by class in case references were lost
  document
    .querySelectorAll(`.${OVERLAY_CLASS}, .${TOOLTIP_CLASS}`)
    .forEach((el) => el.remove());

  activeHighlights.length = 0;
}
