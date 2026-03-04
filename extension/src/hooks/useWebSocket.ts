/* ── useWebSocket — React hook for real-time agent event streaming ── */

import { useCallback, useEffect, useRef, useState } from "react";
import { AgentWebSocket } from "@/lib/ws";
import type { AgentEvent } from "@/types/events";

interface UseWebSocketReturn {
  events: AgentEvent[];
  isConnected: boolean;
  error: string | null;
  connect: (taskId: string) => void;
  disconnect: () => void;
}

export function useWebSocket(wsBaseUrl = "ws://localhost:8000"): UseWebSocketReturn {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<AgentWebSocket | null>(null);

  // Create WS client once
  useEffect(() => {
    wsRef.current = new AgentWebSocket(wsBaseUrl);
    return () => {
      wsRef.current?.disconnect();
    };
  }, [wsBaseUrl]);

  const connect = useCallback((taskId: string) => {
    setEvents([]);
    setError(null);

    wsRef.current?.connect(
      taskId,
      (event) => {
        setEvents((prev) => [...prev, event]);
        if (event.type === "error") {
          setError((event as { message: string }).message);
        }
      },
      (connected) => {
        setIsConnected(connected);
      },
    );
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
  }, []);

  return { events, isConnected, error, connect, disconnect };
}
