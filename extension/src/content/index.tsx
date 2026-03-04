/* ── Content Script — Injects command palette via Shadow DOM ── */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CommandPalette } from "@/command-palette/CommandPalette";
import { extractTabContext } from "@/content/context-extractor";
import { highlightElement, clearHighlights } from "@/content/highlight-overlay";
import type { ExtensionMessage } from "@/types/messages";

// Inline CSS for Shadow DOM (Tailwind will be compiled into this)
import cssText from "@/globals.css?inline";

function init() {
  // Avoid double-injection
  if (document.getElementById("browser-agent-root")) return;

  // Create host element
  const host = document.createElement("div");
  host.id = "browser-agent-root";
  host.style.cssText = "all: initial; position: fixed; z-index: 2147483647; top: 0; left: 0;";
  document.body.appendChild(host);

  // Attach Shadow DOM for style isolation
  const shadow = host.attachShadow({ mode: "open" });

  // Inject styles into shadow root
  const style = document.createElement("style");
  style.textContent = cssText;
  shadow.appendChild(style);

  // Create React mount point
  const mountPoint = document.createElement("div");
  mountPoint.id = "browser-agent-app";
  shadow.appendChild(mountPoint);

  // Mount React app
  createRoot(mountPoint).render(
    <StrictMode>
      <CommandPalette />
    </StrictMode>,
  );

  // ── Message listeners for context extraction & highlight ──
  chrome.runtime.onMessage.addListener(
    (message: ExtensionMessage, _sender, sendResponse) => {
      switch (message.type) {
        case "GET_TAB_CONTEXT": {
          const context = extractTabContext();
          sendResponse({ type: "TAB_CONTEXT_RESPONSE", context });
          break;
        }

        case "HIGHLIGHT_ELEMENT": {
          highlightElement({
            selector: message.selector,
            label: message.label,
            action: message.action,
            duration: message.duration,
          });
          sendResponse({ ok: true });
          break;
        }

        case "CLEAR_HIGHLIGHTS": {
          clearHighlights();
          sendResponse({ ok: true });
          break;
        }
      }

      // Return true to indicate we may send an async response
      return true;
    },
  );
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
