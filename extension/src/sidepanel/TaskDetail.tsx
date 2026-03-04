/* ── TaskDetail — Live step-by-step task status view ── */

import { useEffect, useState, useCallback } from "react";
import { getTask } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { StatusBadge } from "./StatusBadge";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/Button";
import { ConfirmDialog, type HITLRequest } from "@/components/ConfirmDialog";
import type { TaskResult, TaskStatus } from "@/types/task";
import type { StepEventData, HITLRequestEvent } from "@/types/events";

interface TaskDetailProps {
  taskId: string;
  onBack: () => void;
}

export function TaskDetail({ taskId, onBack }: TaskDetailProps) {
  const [task, setTask] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [liveSteps, setLiveSteps] = useState<StepEventData[]>([]);
  const [liveStatus, setLiveStatus] = useState<TaskStatus | null>(null);
  const [finalResult, setFinalResult] = useState<string | null>(null);
  const [hitlRequest, setHitlRequest] = useState<HITLRequest | null>(null);
  const { events, connect } = useWebSocket();

  // Fetch task details
  useEffect(() => {
    let cancelled = false;
    getTask(taskId)
      .then((data) => {
        if (!cancelled) {
          setTask(data);
          // If task is running, connect WS for live updates
          if (data.status === "running" || data.status === "pending") {
            connect(taskId);
          }
        }
      })
      .catch(console.error)
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [taskId, connect]);

  // Process WS events
  useEffect(() => {
    for (const event of events) {
      switch (event.type) {
        case "status":
          setLiveStatus(event.status as TaskStatus);
          break;
        case "step":
          setLiveSteps((prev) => [...prev, event.data]);
          break;
        case "done":
          setLiveStatus(event.data.status as TaskStatus);
          setFinalResult(event.data.final_result);
          setHitlRequest(null);
          break;
        case "error":
          setLiveStatus("failed");
          setHitlRequest(null);
          break;
        case "hitl_request": {
          const hr = event as HITLRequestEvent;
          setHitlRequest({
            task_id: hr.task_id,
            action_id: hr.action_id,
            action_description: hr.action_description,
            url: hr.url,
            element_text: hr.element_text,
            timeout_seconds: hr.timeout_seconds,
          });
          break;
        }
      }
    }
  }, [events]);

  // Listen for HITL_REQUEST forwarded from service worker
  useEffect(() => {
    const handler = (message: { type: string; taskId?: string; actionId?: string; actionDescription?: string; url?: string | null; elementText?: string | null; timeoutSeconds?: number }) => {
      if (message.type === "HITL_REQUEST" && message.taskId === taskId) {
        setHitlRequest({
          task_id: message.taskId,
          action_id: message.actionId!,
          action_description: message.actionDescription!,
          url: message.url ?? null,
          element_text: message.elementText ?? null,
          timeout_seconds: message.timeoutSeconds ?? 60,
        });
      }
    };
    chrome.runtime.onMessage.addListener(handler);
    return () => chrome.runtime.onMessage.removeListener(handler);
  }, [taskId]);

  // Send HITL response back via service worker
  const handleHITLRespond = useCallback(
    (actionId: string, approved: boolean) => {
      chrome.runtime.sendMessage({
        type: "HITL_RESPONSE",
        taskId,
        actionId,
        approved,
      });
      setHitlRequest(null);
    },
    [taskId],
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-error text-sm">Task not found</p>
        <Button variant="ghost" size="sm" onClick={onBack} className="mt-2">
          ← Back
        </Button>
      </div>
    );
  }

  const status = liveStatus ?? task.status;
  const isRunning = status === "running" || status === "pending";
  const displaySteps = liveSteps.length > 0
    ? liveSteps
    : task.steps.map((s) => ({
        step_number: s.step_number,
        action: s.action,
        element: s.element,
        reasoning: s.reasoning,
        thinking: s.thinking,
        success: s.success,
        error: s.error,
      }));
  const result = finalResult ?? task.final_result;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={onBack}
            className="text-text-muted hover:text-text-primary text-sm"
          >
            ←
          </button>
          <StatusBadge status={status} />
          {task.duration_seconds != null && (
            <span className="text-xs text-text-muted ml-auto">
              {task.duration_seconds.toFixed(1)}s
            </span>
          )}
        </div>
        <p className="text-sm text-text-primary">{task.task}</p>
      </div>

      {/* HITL Confirmation Dialog */}
      {hitlRequest && (
        <ConfirmDialog request={hitlRequest} onRespond={handleHITLRespond} />
      )}

      {/* Steps */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {displaySteps.map((step) => (
          <div
            key={step.step_number}
            className="p-3 bg-surface-light rounded-lg border border-border"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-text-muted">
                #{step.step_number}
              </span>
              <span className="text-sm text-text-primary font-medium">
                {step.action}
              </span>
              {step.success === true && (
                <span className="text-success text-xs ml-auto">✓</span>
              )}
              {step.success === false && (
                <span className="text-error text-xs ml-auto">✗</span>
              )}
            </div>
            {step.element && (
              <p className="text-xs text-text-secondary truncate">
                → {step.element}
              </p>
            )}
            {step.reasoning && (
              <p className="text-xs text-text-muted mt-1">{step.reasoning}</p>
            )}
            {step.error && (
              <p className="text-xs text-error mt-1">{step.error}</p>
            )}
          </div>
        ))}

        {isRunning && (
          <div className="flex items-center gap-2 py-2 text-text-muted">
            <Spinner size="sm" />
            <span className="text-xs">Agent is working...</span>
          </div>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className="px-4 py-3 border-t border-border shrink-0 bg-surface-light">
          <p className="text-xs text-text-muted mb-1">Result</p>
          <p className="text-sm text-text-primary">{result}</p>
        </div>
      )}

      {task.error && !result && (
        <div className="px-4 py-3 border-t border-error/30 shrink-0 bg-error/5">
          <p className="text-xs text-error mb-1">Error</p>
          <p className="text-sm text-error">{task.error}</p>
        </div>
      )}
    </div>
  );
}
