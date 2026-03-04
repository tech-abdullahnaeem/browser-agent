/* ── WebSocket client for real-time agent event streaming ── */

import type { AgentEvent } from "@/types/events";

const DEFAULT_WS_BASE = "ws://localhost:8000";

export type EventCallback = (event: AgentEvent) => void;
export type ConnectionCallback = (connected: boolean) => void;

export class AgentWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string | null = null;
  private onEvent: EventCallback | null = null;
  private onConnection: ConnectionCallback | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private attempt = 0;
  private maxRetries = 5;
  private baseUrl: string;
  private _disposed = false;

  constructor(baseUrl: string = DEFAULT_WS_BASE) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /** Connect to the WebSocket for a specific task */
  connect(
    taskId: string,
    onEvent: EventCallback,
    onConnection?: ConnectionCallback,
  ): void {
    this.disconnect();
    this._disposed = false;
    this.taskId = taskId;
    this.onEvent = onEvent;
    this.onConnection = onConnection ?? null;
    this.attempt = 0;
    this._connect();
  }

  /** Disconnect and clean up */
  disconnect(): void {
    this._disposed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null; // prevent reconnect
      this.ws.close();
      this.ws = null;
    }
    this.onConnection?.(false);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private _connect(): void {
    if (this._disposed || !this.taskId) return;

    const url = `${this.baseUrl}/ws/${this.taskId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.attempt = 0;
      this.onConnection?.(true);
      this._startHeartbeat();
    };

    this.ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data as string) as AgentEvent;
        if (data.type === "pong") return; // Skip pong
        this.onEvent?.(data);

        // Auto-close on terminal events
        if (data.type === "done" || data.type === "error") {
          this.disconnect();
        }
      } catch {
        console.warn("[AgentWS] Failed to parse message:", evt.data);
      }
    };

    this.ws.onerror = (err) => {
      console.error("[AgentWS] Error:", err);
    };

    this.ws.onclose = () => {
      this.onConnection?.(false);
      this._stopHeartbeat();
      this._scheduleReconnect();
    };
  }

  private _scheduleReconnect(): void {
    if (this._disposed || this.attempt >= this.maxRetries) return;
    this.attempt++;
    const delay = Math.min(1000 * 2 ** this.attempt, 30000);
    this.reconnectTimer = setTimeout(() => this._connect(), delay);
  }

  private _startHeartbeat(): void {
    this._stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 30_000);
  }

  private _stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}
