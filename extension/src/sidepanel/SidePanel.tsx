/* ── SidePanel — Main sidebar component ── */

import { useState, useEffect, useCallback } from "react";
import { TaskList } from "./TaskList";
import { TaskDetail } from "./TaskDetail";
import { Button } from "@/components/Button";
import { healthCheck } from "@/lib/api";
import type { ExtensionMessage } from "@/types/messages";

export function SidePanel() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Check backend connectivity
  useEffect(() => {
    healthCheck().then(setBackendOnline);
    const interval = setInterval(() => {
      healthCheck().then(setBackendOnline);
    }, 15_000);
    return () => clearInterval(interval);
  }, []);

  // Listen for task-created events to auto-navigate
  useEffect(() => {
    const listener = (message: ExtensionMessage) => {
      if (message.type === "TASK_CREATED") {
        setSelectedTaskId(message.taskId);
        setRefreshTrigger((c) => c + 1);
      }
    };
    chrome.runtime.onMessage.addListener(listener);
    return () => chrome.runtime.onMessage.removeListener(listener);
  }, []);

  const handleNewTask = useCallback(() => {
    // Tell service worker to open the command palette in the content script
    chrome.runtime.sendMessage({ type: "TOGGLE_PALETTE" } satisfies ExtensionMessage);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-surface text-text-primary">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-lg bg-brand-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold">B</span>
          </div>
          <h1 className="text-sm font-semibold">Browser Agent</h1>
        </div>
        <div className="flex items-center gap-2">
          {/* Connectivity indicator */}
          <span
            className={`h-2 w-2 rounded-full ${
              backendOnline === null
                ? "bg-text-muted"
                : backendOnline
                  ? "bg-success"
                  : "bg-error"
            }`}
            title={
              backendOnline === null
                ? "Checking..."
                : backendOnline
                  ? "Backend connected"
                  : "Backend offline"
            }
          />
          <Button size="sm" onClick={handleNewTask}>
            + New Task
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {selectedTaskId ? (
          <TaskDetail
            taskId={selectedTaskId}
            onBack={() => {
              setSelectedTaskId(null);
              setRefreshTrigger((c) => c + 1);
            }}
          />
        ) : (
          <div className="h-full overflow-y-auto">
            <TaskList
              onSelect={setSelectedTaskId}
              refreshTrigger={refreshTrigger}
            />
          </div>
        )}
      </div>

      {/* Backend offline warning */}
      {backendOnline === false && (
        <div className="px-4 py-2 bg-error/10 border-t border-error/30 shrink-0">
          <p className="text-xs text-error">
            Backend offline — start the server at localhost:8000
          </p>
        </div>
      )}
    </div>
  );
}
