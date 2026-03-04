/* ── useTabContext — React hook to request page context from content script ── */

import { useState, useEffect } from "react";
import type { TabContext } from "@/content/context-extractor";

interface UseTabContextReturn {
  context: TabContext | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Sends a GET_TAB_CONTEXT message to the active tab's content script
 * and returns QA-oriented page context.
 */
export function useTabContext(autoFetch = true): UseTabContextReturn {
  const [context, setContext] = useState<TabContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    setLoading(true);
    setError(null);

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) {
        setError("No active tab");
        setLoading(false);
        return;
      }

      chrome.tabs.sendMessage(tabId, { type: "GET_TAB_CONTEXT" }, (response) => {
        setLoading(false);
        if (chrome.runtime.lastError) {
          setError(chrome.runtime.lastError.message || "Failed to get context");
          return;
        }
        if (response?.type === "TAB_CONTEXT_RESPONSE" && response.context) {
          setContext(response.context as TabContext);
        } else {
          setError("Invalid context response");
        }
      });
    });
  };

  useEffect(() => {
    if (autoFetch) {
      refresh();
    }
  }, [autoFetch]);

  return { context, loading, error, refresh };
}
