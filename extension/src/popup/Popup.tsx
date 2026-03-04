/* ── Popup — Minimal popup that redirects to the side panel ── */

import { Button } from "@/components/Button";

export function Popup() {
  const openSidePanel = async () => {
    try {
      // Open side panel from popup context
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id) {
        await chrome.sidePanel.open({ tabId: tab.id });
      }
    } catch (err) {
      console.error("Failed to open side panel:", err);
    }
    window.close();
  };

  const openPalette = () => {
    chrome.runtime.sendMessage({ type: "TOGGLE_PALETTE" });
    window.close();
  };

  return (
    <div className="w-64 bg-surface text-text-primary p-4 space-y-3">
      <div className="flex items-center gap-2">
        <div className="h-7 w-7 rounded-lg bg-brand-600 flex items-center justify-center">
          <span className="text-white text-sm font-bold">B</span>
        </div>
        <div>
          <h1 className="text-sm font-semibold">Browser Agent</h1>
          <p className="text-xs text-text-muted">AI browser automation</p>
        </div>
      </div>

      <div className="space-y-2">
        <Button onClick={openPalette} className="w-full" size="md">
          ⌘K Command Palette
        </Button>
        <Button
          onClick={openSidePanel}
          variant="secondary"
          className="w-full"
          size="md"
        >
          Open Side Panel
        </Button>
      </div>

      <p className="text-xs text-text-muted text-center">
        Tip: Press ⌘K on any page to quick-start
      </p>
    </div>
  );
}
