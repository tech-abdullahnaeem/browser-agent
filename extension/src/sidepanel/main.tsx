import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { SidePanel } from "./SidePanel";
import { loadBaseUrl } from "@/lib/api";
import "@/globals.css";

loadBaseUrl().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <SidePanel />
    </StrictMode>,
  );
});
