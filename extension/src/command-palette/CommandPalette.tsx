/* ── CommandPalette — Floating CMD+K overlay (QA-focused) ── */

import { useState, useEffect, useCallback, useRef } from "react";
import { TaskInput } from "./TaskInput";
import { QuickActions } from "./QuickActions";
import { Spinner } from "@/components/Spinner";
import type { AgentEvent } from "@/types/events";
import type { ExtensionMessage } from "@/types/messages";

type PaletteStatus = "idle" | "submitting" | "running" | "done" | "error";

interface ContextSummary {
  url: string;
  title: string;
  issueCount: number;
  consoleErrors: number;
  a11yIssues: number;
  brokenImages: number;
  formCount: number;
  linkCount: number;
}

export function CommandPalette() {
  const [visible, setVisible] = useState(false);
  const [status, setStatus] = useState<PaletteStatus>("idle");
  const [statusText, setStatusText] = useState("");
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [stepCount, setStepCount] = useState(0);
  const [contextSummary, setContextSummary] = useState<ContextSummary | null>(null);
  const [showContext, setShowContext] = useState(true);
  const backdropRef = useRef<HTMLDivElement>(null);

  // Fetch tab context when palette becomes visible
  useEffect(() => {
    if (!visible) return;

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) return;

      chrome.tabs.sendMessage(tabId, { type: "GET_TAB_CONTEXT" }, (response) => {
        if (chrome.runtime.lastError || !response?.context) return;
        const ctx = response.context;
        const issueCount =
          (ctx.consoleErrors?.length || 0) +
          (ctx.a11yIssues?.length || 0) +
          (ctx.brokenImages?.length || 0);

        setContextSummary({
          url: ctx.url || "",
          title: ctx.title || "",
          issueCount,
          consoleErrors: ctx.consoleErrors?.length || 0,
          a11yIssues: ctx.a11yIssues?.length || 0,
          brokenImages: ctx.brokenImages?.length || 0,
          formCount: ctx.formCount || 0,
          linkCount: ctx.linkCount || 0,
        });
      });
    });
  }, [visible]);

  // Listen for toggle messages from service worker
  useEffect(() => {
    const listener = (message: ExtensionMessage) => {
      if (message.type === "TOGGLE_PALETTE") {
        setVisible((v) => !v);
      } else if (message.type === "TASK_CREATED") {
        setCurrentTaskId(message.taskId);
        setStatus("running");
        setStatusText("Agent is starting...");
        setStepCount(0);
      } else if (message.type === "TASK_EVENT") {
        handleEvent(message.event);
      }
    };

    chrome.runtime.onMessage.addListener(listener);
    return () => chrome.runtime.onMessage.removeListener(listener);
  }, []);

  // Close on Escape
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && visible) {
        setVisible(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [visible]);

  const handleEvent = useCallback((event: AgentEvent) => {
    switch (event.type) {
      case "status":
        setStatusText(`Status: ${event.status}`);
        break;
      case "step":
        setStepCount((c) => c + 1);
        setStatusText(`Step ${event.data.step_number}: ${event.data.action}`);
        break;
      case "done":
        setStatus("done");
        setStatusText(
          event.data.final_result
            ? event.data.final_result.slice(0, 120)
            : "Task completed",
        );
        // Auto-hide after a few seconds
        setTimeout(() => {
          setVisible(false);
          resetState();
        }, 5000);
        break;
      case "error":
        setStatus("error");
        setStatusText(event.message);
        break;
    }
  }, []);

  const resetState = () => {
    setStatus("idle");
    setStatusText("");
    setCurrentTaskId(null);
    setStepCount(0);
    setContextSummary(null);
  };

  const handleSubmit = async (task: string) => {
    setStatus("submitting");
    setStatusText("Submitting task...");

    // Send to service worker
    chrome.runtime.sendMessage({ type: "SUBMIT_TASK", task });
  };

  const handleClickOutside = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) {
      setVisible(false);
    }
  };

  if (!visible) return null;

  return (
    <div
      ref={backdropRef}
      onClick={handleClickOutside}
      className="fixed inset-0 z-[2147483647] flex items-start justify-center pt-[20vh] bg-black/40 backdrop-blur-sm"
      style={{ fontFamily: "'Inter', system-ui, -apple-system, sans-serif" }}
    >
      <div
        className="
          w-full max-w-lg mx-4
          bg-surface border border-border rounded-2xl
          shadow-2xl shadow-black/50
          overflow-hidden
          animate-in fade-in-0 zoom-in-95 duration-150
        "
      >
        {/* Header */}
        <div className="px-4 pt-4 pb-2">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-6 w-6 rounded-lg bg-brand-600 flex items-center justify-center">
              <span className="text-white text-xs font-bold">QA</span>
            </div>
            <span className="text-text-secondary text-xs font-medium">
              QA Testing Agent
            </span>
            <span className="ml-auto text-text-muted text-xs">⌘K</span>
          </div>

          <TaskInput
            onSubmit={handleSubmit}
            disabled={status === "submitting" || status === "running"}
          />

          {/* QA Context Summary */}
          {status === "idle" && contextSummary && showContext && (
            <div className="mt-2 p-2.5 rounded-lg bg-surface-lighter border border-border text-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-medium text-text-primary">Page Context</span>
                <button
                  onClick={() => setShowContext(false)}
                  className="text-text-muted hover:text-text-primary text-[10px]"
                >
                  Hide
                </button>
              </div>
              <p className="text-text-secondary truncate mb-1" title={contextSummary.url}>
                {contextSummary.title || contextSummary.url}
              </p>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-text-muted">
                {contextSummary.consoleErrors > 0 && (
                  <span className="text-error">
                    {contextSummary.consoleErrors} error{contextSummary.consoleErrors !== 1 ? "s" : ""}
                  </span>
                )}
                {contextSummary.a11yIssues > 0 && (
                  <span className="text-warning">
                    {contextSummary.a11yIssues} a11y issue{contextSummary.a11yIssues !== 1 ? "s" : ""}
                  </span>
                )}
                {contextSummary.brokenImages > 0 && (
                  <span className="text-error">
                    {contextSummary.brokenImages} broken img{contextSummary.brokenImages !== 1 ? "s" : ""}
                  </span>
                )}
                <span>{contextSummary.formCount} form{contextSummary.formCount !== 1 ? "s" : ""}</span>
                <span>{contextSummary.linkCount} link{contextSummary.linkCount !== 1 ? "s" : ""}</span>
              </div>
              {contextSummary.issueCount === 0 && (
                <p className="text-success mt-0.5">No issues detected at a glance</p>
              )}
            </div>
          )}

          {status === "idle" && !showContext && contextSummary && (
            <button
              onClick={() => setShowContext(true)}
              className="mt-1 text-[10px] text-text-muted hover:text-text-primary"
            >
              Show page context
            </button>
          )}

          {status === "idle" && <QuickActions onSelect={handleSubmit} />}
        </div>

        {/* Status area */}
        {status !== "idle" && (
          <div className="px-4 py-3 border-t border-border">
            <div className="flex items-center gap-2">
              {(status === "submitting" || status === "running") && (
                <Spinner size="sm" />
              )}
              {status === "done" && (
                <span className="text-success text-sm">✓</span>
              )}
              {status === "error" && (
                <span className="text-error text-sm">✗</span>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary truncate">
                  {statusText}
                </p>
                {status === "running" && stepCount > 0 && (
                  <p className="text-xs text-text-muted mt-0.5">
                    {stepCount} step{stepCount !== 1 ? "s" : ""} completed
                  </p>
                )}
              </div>
              {currentTaskId && status === "running" && (
                <button
                  onClick={() => {
                    chrome.runtime.sendMessage({ type: "OPEN_SIDEPANEL" });
                  }}
                  className="text-xs text-brand-400 hover:text-brand-300 shrink-0"
                >
                  View details →
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
