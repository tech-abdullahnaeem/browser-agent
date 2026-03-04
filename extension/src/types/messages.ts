/* ── Messages exchanged between service worker, content script, and UI ── */

import type { TabContext } from "@/content/context-extractor";

export interface TogglePaletteMessage {
  type: "TOGGLE_PALETTE";
}

export interface SubmitTaskMessage {
  type: "SUBMIT_TASK";
  task: string;
}

export interface TaskCreatedMessage {
  type: "TASK_CREATED";
  taskId: string;
}

export interface TaskEventMessage {
  type: "TASK_EVENT";
  taskId: string;
  event: import("./events").AgentEvent;
}

export interface OpenSidePanelMessage {
  type: "OPEN_SIDEPANEL";
}

// ── Phase 4: Context & Highlight messages ──

export interface GetTabContextMessage {
  type: "GET_TAB_CONTEXT";
}

export interface TabContextResponseMessage {
  type: "TAB_CONTEXT_RESPONSE";
  context: TabContext;
}

export interface HighlightElementMessage {
  type: "HIGHLIGHT_ELEMENT";
  selector: string;
  label?: string;
  action?: "click" | "type" | "inspect" | "error" | "warning" | "info";
  duration?: number;
}

export interface ClearHighlightsMessage {
  type: "CLEAR_HIGHLIGHTS";
}

// ── Phase 6: HITL confirmation messages ──

export interface HITLRequestMessage {
  type: "HITL_REQUEST";
  taskId: string;
  actionId: string;
  actionDescription: string;
  url: string | null;
  elementText: string | null;
  timeoutSeconds: number;
}

export interface HITLResponseMessage {
  type: "HITL_RESPONSE";
  taskId: string;
  actionId: string;
  approved: boolean;
}

export type ExtensionMessage =
  | TogglePaletteMessage
  | SubmitTaskMessage
  | TaskCreatedMessage
  | TaskEventMessage
  | OpenSidePanelMessage
  | GetTabContextMessage
  | TabContextResponseMessage
  | HighlightElementMessage
  | ClearHighlightsMessage
  | HITLRequestMessage
  | HITLResponseMessage;
