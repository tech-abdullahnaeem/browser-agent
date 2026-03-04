/* ── Service Worker — Background script for WebSocket mgmt & message routing ── */

import type { ExtensionMessage } from "@/types/messages";
import type { AgentEvent } from "@/types/events";

// ── Config ──
const DEFAULT_BACKEND = "http://localhost:8000";
const WS_BACKEND = "ws://localhost:8000";

let backendUrl = DEFAULT_BACKEND;
let wsBaseUrl = WS_BACKEND;

// Load backend URL from storage
chrome.storage.local.get("backend_url", (result) => {
  if (result.backend_url) {
    backendUrl = result.backend_url;
    wsBaseUrl = result.backend_url.replace(/^http/, "ws");
  }
});

// ── Active WebSocket connections ──
const activeConnections = new Map<string, WebSocket>();

// ── Command handler: CMD+K ──
chrome.commands.onCommand.addListener((command) => {
  if (command === "toggle-palette") {
    sendToActiveTab({ type: "TOGGLE_PALETTE" });
  }
});

// ── Side panel setup ──
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false }).catch(() => {
  // Fallback for older Chrome versions
});

// ── Message routing ──
chrome.runtime.onMessage.addListener(
  (message: ExtensionMessage, _sender, _sendResponse) => {
    switch (message.type) {
      case "SUBMIT_TASK":
        handleSubmitTask(message.task);
        break;

      case "OPEN_SIDEPANEL":
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0]?.id) {
            chrome.sidePanel.open({ tabId: tabs[0].id }).catch(console.error);
          }
        });
        break;

      case "TOGGLE_PALETTE":
        sendToActiveTab({ type: "TOGGLE_PALETTE" });
        break;

      case "HITL_RESPONSE":
        handleHITLResponse(message.taskId, message.actionId, message.approved);
        break;
    }
  },
);

// ── Query active tab for QA context ──
function getTabContext(): Promise<string | null> {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) {
        resolve(null);
        return;
      }

      chrome.tabs.sendMessage(tabId, { type: "GET_TAB_CONTEXT" }, (response) => {
        if (chrome.runtime.lastError || !response?.context) {
          resolve(null);
          return;
        }

        // Build a concise QA context string for the backend
        const ctx = response.context;
        const parts: string[] = [
          `URL: ${ctx.url}`,
          `Title: ${ctx.title}`,
          `Viewport: ${ctx.viewport?.width}x${ctx.viewport?.height}`,
        ];

        if (ctx.description) {
          parts.push(`Description: ${ctx.description}`);
        }

        // QA-relevant summary
        if (ctx.consoleErrors?.length > 0) {
          parts.push(`\nConsole Errors (${ctx.consoleErrors.length}):`);
          ctx.consoleErrors.slice(0, 5).forEach((e: string) => parts.push(`  - ${e}`));
        }

        if (ctx.a11yIssues?.length > 0) {
          parts.push(`\nAccessibility Issues (${ctx.a11yIssues.length}):`);
          ctx.a11yIssues.slice(0, 10).forEach((issue: { severity: string; type: string; message: string }) => {
            parts.push(`  [${issue.severity}] ${issue.type}: ${issue.message}`);
          });
        }

        if (ctx.brokenImages?.length > 0) {
          parts.push(`\nBroken Images (${ctx.brokenImages.length}):`);
          ctx.brokenImages.slice(0, 5).forEach((img: { src: string }) => parts.push(`  - ${img.src}`));
        }

        if (ctx.imagesWithoutAlt?.length > 0) {
          parts.push(`\nImages Without Alt Text: ${ctx.imagesWithoutAlt.length}`);
        }

        parts.push(`\nPage Stats: ${ctx.linkCount} links, ${ctx.formCount} forms, ${ctx.imageCount} images`);
        parts.push(`DOM Nodes: ${ctx.performance?.domNodes || "unknown"}`);

        if (ctx.performance?.loadComplete) {
          parts.push(`Load Time: ${ctx.performance.loadComplete}ms`);
        }

        if (ctx.headings?.length > 0) {
          parts.push(`\nHeadings:`);
          ctx.headings.slice(0, 10).forEach((h: string) => parts.push(`  ${h}`));
        }

        if (ctx.visibleText) {
          parts.push(`\nPage Content (excerpt): ${ctx.visibleText.slice(0, 1500)}`);
        }

        resolve(parts.join("\n"));
      });
    });
  });
}

// ── Task submission handler ──
async function handleSubmitTask(task: string) {
  try {
    // Gather tab context before submitting
    const context = await getTabContext();

    // POST to backend
    const body: { task: string; context?: string } = { task };
    if (context) {
      body.context = context;
    }

    const resp = await fetch(`${backendUrl}/api/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      throw new Error(`API error: ${resp.status}`);
    }

    const data = (await resp.json()) as { task_id: string; status: string };
    const taskId = data.task_id;

    // Notify content script + sidepanel
    broadcastMessage({ type: "TASK_CREATED", taskId });

    // Open WebSocket for live updates
    connectWebSocket(taskId);
  } catch (err) {
    console.error("[SW] Failed to submit task:", err);
  }
}

// ── WebSocket management ──
function connectWebSocket(taskId: string) {
  // Close existing connection for this task if any
  const existing = activeConnections.get(taskId);
  if (existing) {
    existing.close();
  }

  const url = `${wsBaseUrl}/ws/${taskId}`;
  const ws = new WebSocket(url);
  activeConnections.set(taskId, ws);

  ws.onmessage = (evt) => {
    try {
      const event = JSON.parse(evt.data as string) as AgentEvent;
      if (event.type === "pong") return;

      // Forward to all extension contexts
      broadcastMessage({ type: "TASK_EVENT", taskId, event });

      // Forward highlight events to the active tab's content script
      if (event.type === "highlight") {
        sendToActiveTab({
          type: "HIGHLIGHT_ELEMENT",
          selector: event.selector,
          label: event.label,
          action: event.action,
          duration: event.duration,
        });
      }

      // Forward HITL confirmation requests to the sidepanel
      if (event.type === "hitl_request") {
        broadcastMessage({
          type: "HITL_REQUEST",
          taskId,
          actionId: event.action_id,
          actionDescription: event.action_description,
          url: event.url,
          elementText: event.element_text,
          timeoutSeconds: event.timeout_seconds,
        });
      }

      // Clean up on terminal events
      if (event.type === "done" || event.type === "error") {
        // Clear highlights when task finishes
        sendToActiveTab({ type: "CLEAR_HIGHLIGHTS" });
        ws.close();
        activeConnections.delete(taskId);
      }
    } catch {
      console.warn("[SW] Failed to parse WS message:", evt.data);
    }
  };

  ws.onerror = (err) => {
    console.error("[SW] WebSocket error:", err);
  };

  ws.onclose = () => {
    activeConnections.delete(taskId);
  };

  // Heartbeat every 30s
  const heartbeat = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
    } else {
      clearInterval(heartbeat);
    }
  }, 30_000);
}

// ── HITL response — send user decision back to backend via WS ──
function handleHITLResponse(taskId: string, actionId: string, approved: boolean) {
  const ws = activeConnections.get(taskId);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(
      JSON.stringify({
        type: "hitl_response",
        data: { action_id: actionId, approved },
      }),
    );
  } else {
    console.warn("[SW] No active WS for HITL response, taskId:", taskId);
  }
}

// ── Helpers ──

/** Send a message to the active tab's content script */
function sendToActiveTab(message: ExtensionMessage) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]?.id) {
      chrome.tabs.sendMessage(tabs[0].id, message).catch(() => {
        // Content script may not be loaded yet
      });
    }
  });
}

/** Broadcast message to all extension contexts (content scripts, popup, sidepanel) */
function broadcastMessage(message: ExtensionMessage) {
  // Send to all tabs (content scripts)
  chrome.tabs.query({}, (tabs) => {
    for (const tab of tabs) {
      if (tab.id) {
        chrome.tabs.sendMessage(tab.id, message).catch(() => {});
      }
    }
  });

  // Send to extension pages (popup, sidepanel) via runtime
  chrome.runtime.sendMessage(message).catch(() => {
    // No receivers - that's OK
  });
}
