/* ── WebSocket event types mirroring backend AgentEvent models ── */

export type EventType = "status" | "step" | "plan" | "screenshot" | "done" | "error" | "pong" | "highlight" | "hitl_request";

export interface BaseEvent {
  type: EventType;
  task_id: string;
  timestamp: string;
}

export interface StatusEvent extends BaseEvent {
  type: "status";
  status: string;
}

export interface StepEventData {
  step_number: number;
  action: string;
  element?: string | null;
  reasoning?: string | null;
  thinking?: string | null;
  success?: boolean | null;
  error?: string | null;
}

export interface StepEvent extends BaseEvent {
  type: "step";
  data: StepEventData;
}

export interface PlanEvent extends BaseEvent {
  type: "plan";
  plan: string;
}

export interface ScreenshotEvent extends BaseEvent {
  type: "screenshot";
  data: string; // base64
  step_number: number;
}

export interface DoneEventData {
  status: string;
  final_result: string | null;
  error: string | null;
  total_steps: number;
  duration_seconds: number;
}

export interface DoneEvent extends BaseEvent {
  type: "done";
  data: DoneEventData;
}

export interface ErrorEvent extends BaseEvent {
  type: "error";
  message: string;
}

export interface PongEvent extends BaseEvent {
  type: "pong";
}

export interface HighlightEvent extends BaseEvent {
  type: "highlight";
  selector: string;
  label?: string;
  action?: "click" | "type" | "inspect" | "error" | "warning" | "info";
  duration?: number;
}

export interface HITLRequestEvent extends BaseEvent {
  type: "hitl_request";
  action_id: string;
  action_description: string;
  url: string | null;
  element_text: string | null;
  timeout_seconds: number;
}

export type AgentEvent =
  | StatusEvent
  | StepEvent
  | PlanEvent
  | ScreenshotEvent
  | DoneEvent
  | ErrorEvent
  | PongEvent
  | HighlightEvent
  | HITLRequestEvent;
