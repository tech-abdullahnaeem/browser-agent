/* ── ConfirmDialog — HITL confirmation dialog for destructive actions ── */

import { useEffect, useState, useCallback } from "react";
import { Button } from "./Button";

export interface HITLRequest {
  task_id: string;
  action_id: string;
  action_description: string;
  url: string | null;
  element_text: string | null;
  timeout_seconds: number;
}

interface ConfirmDialogProps {
  request: HITLRequest;
  onRespond: (actionId: string, approved: boolean) => void;
}

export function ConfirmDialog({ request, onRespond }: ConfirmDialogProps) {
  const [remaining, setRemaining] = useState(request.timeout_seconds);
  const [responded, setResponded] = useState(false);

  // Countdown timer — auto-deny on expiry
  useEffect(() => {
    if (responded) return;

    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onRespond(request.action_id, false);
          setResponded(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [request.action_id, onRespond, responded]);

  const handleAllow = useCallback(() => {
    if (responded) return;
    setResponded(true);
    onRespond(request.action_id, true);
  }, [request.action_id, onRespond, responded]);

  const handleDeny = useCallback(() => {
    if (responded) return;
    setResponded(true);
    onRespond(request.action_id, false);
  }, [request.action_id, onRespond, responded]);

  if (responded) return null;

  const urgency =
    remaining <= 10 ? "text-error" : remaining <= 20 ? "text-warning" : "text-text-muted";

  return (
    <div className="mx-4 my-3 p-4 rounded-lg border-2 border-warning/60 bg-warning/5 animate-pulse-slow">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">⚠️</span>
        <h3 className="text-sm font-semibold text-text-primary">
          Confirmation Required
        </h3>
        <span className={`text-xs font-mono ml-auto ${urgency}`}>
          {remaining}s
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-text-primary mb-2">
        The agent wants to perform a potentially destructive action:
      </p>
      <div className="px-3 py-2 bg-surface rounded-md border border-border mb-2">
        <p className="text-sm font-medium text-text-primary">
          {request.action_description}
        </p>
      </div>

      {/* Context */}
      {request.url && (
        <p className="text-xs text-text-secondary mb-1">
          <span className="font-medium">URL:</span> {request.url}
        </p>
      )}
      {request.element_text && (
        <p className="text-xs text-text-secondary mb-1">
          <span className="font-medium">Element:</span> {request.element_text}
        </p>
      )}

      {/* Progress bar */}
      <div className="mt-3 mb-3 h-1 w-full bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-warning transition-all duration-1000 ease-linear rounded-full"
          style={{
            width: `${(remaining / request.timeout_seconds) * 100}%`,
          }}
        />
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Button variant="primary" size="sm" onClick={handleAllow} className="flex-1">
          ✓ Allow
        </Button>
        <Button variant="danger" size="sm" onClick={handleDeny} className="flex-1">
          ✗ Deny
        </Button>
      </div>

      <p className="text-[10px] text-text-muted mt-2 text-center">
        Auto-denies in {remaining}s if no response
      </p>
    </div>
  );
}
