/* ── Context Extractor — Extracts QA-relevant page context ──
 *
 * This module is designed for a quality-testing agent. It gathers not just
 * basic page info, but also QA signals: console errors, accessibility issues,
 * broken images, form validation states, meta/SEO data, and performance metrics.
 */

export interface FormFieldInfo {
  name: string;
  type: string;
  value: string;
  placeholder: string;
  required: boolean;
  validationMessage: string;
  ariaLabel: string | null;
  id: string;
  hasLabel: boolean;
}

export interface LinkInfo {
  href: string;
  text: string;
  isExternal: boolean;
  target: string;
}

export interface ImageInfo {
  src: string;
  alt: string;
  naturalWidth: number;
  naturalHeight: number;
  isBroken: boolean;
  hasAlt: boolean;
}

export interface A11yIssue {
  type: string;
  selector: string;
  message: string;
  severity: "error" | "warning" | "info";
}

export interface PerformanceMetrics {
  domContentLoaded: number;
  loadComplete: number;
  domNodes: number;
  jsHeapUsedMB: number | null;
}

export interface TabContext {
  // ── Basic page info ──
  url: string;
  title: string;
  description: string;
  viewport: { width: number; height: number };

  // ── Content ──
  visibleText: string;
  selectedText: string;
  headings: string[];

  // ── QA: Forms ──
  formFields: FormFieldInfo[];
  formCount: number;

  // ── QA: Links ──
  linkCount: number;
  externalLinkCount: number;
  linksWithoutText: number;

  // ── QA: Images ──
  imageCount: number;
  brokenImages: ImageInfo[];
  imagesWithoutAlt: ImageInfo[];

  // ── QA: Console errors (collected by content script) ──
  consoleErrors: string[];

  // ── QA: Accessibility ──
  a11yIssues: A11yIssue[];

  // ── QA: SEO / Meta ──
  metaTags: Record<string, string>;
  hasCanonical: boolean;
  hasViewportMeta: boolean;
  lang: string;
  charset: string;

  // ── QA: Performance ──
  performance: PerformanceMetrics;

  // ── Timestamp ──
  extractedAt: string;
}

// ── Console error collector (runs as early as possible) ──
const collectedConsoleErrors: string[] = [];
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  if (collectedConsoleErrors.length < 50) {
    collectedConsoleErrors.push(args.map(String).join(" ").slice(0, 300));
  }
  originalConsoleError.apply(console, args);
};

// Also capture unhandled errors
window.addEventListener("error", (event) => {
  if (collectedConsoleErrors.length < 50) {
    const msg = `[JS Error] ${event.message} at ${event.filename}:${event.lineno}`;
    collectedConsoleErrors.push(msg.slice(0, 300));
  }
});

window.addEventListener("unhandledrejection", (event) => {
  if (collectedConsoleErrors.length < 50) {
    const msg = `[Unhandled Promise] ${String(event.reason).slice(0, 250)}`;
    collectedConsoleErrors.push(msg);
  }
});


/** Extract comprehensive QA-oriented page context */
export function extractTabContext(): TabContext {
  const url = window.location.href;
  const title = (document.title || "").slice(0, 200);

  // ── Meta tags ──
  const metaTags: Record<string, string> = {};
  document.querySelectorAll("meta").forEach((meta) => {
    const name = meta.getAttribute("name") || meta.getAttribute("property") || "";
    const content = meta.getAttribute("content") || "";
    if (name && content) {
      metaTags[name] = content.slice(0, 500);
    }
  });

  const description = metaTags["description"] || metaTags["og:description"] || "";
  const hasCanonical = !!document.querySelector("link[rel='canonical']");
  const hasViewportMeta = !!document.querySelector("meta[name='viewport']");
  const lang = document.documentElement.lang || "";
  const charset =
    document.characterSet ||
    document.querySelector("meta[charset]")?.getAttribute("charset") ||
    "";

  // ── Visible text ──
  const visibleText = (document.body?.innerText || "").slice(0, 3000);
  const selectedText = (window.getSelection()?.toString() || "").slice(0, 1000);

  // ── Headings ──
  const headings: string[] = [];
  document.querySelectorAll("h1, h2, h3").forEach((h) => {
    const text = (h.textContent || "").trim();
    if (text && headings.length < 30) {
      headings.push(`${h.tagName}: ${text.slice(0, 120)}`);
    }
  });

  // ── Forms & Fields ──
  const forms = document.querySelectorAll("form");
  const formFields: FormFieldInfo[] = [];
  const inputSelector = "input:not([type='hidden']), select, textarea";

  document.querySelectorAll(inputSelector).forEach((el) => {
    if (formFields.length >= 30) return;
    const input = el as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
    const id = input.id || "";
    const hasLabel = id
      ? !!document.querySelector(`label[for='${CSS.escape(id)}']`)
      : !!input.closest("label");

    formFields.push({
      name: input.name || "",
      type: input instanceof HTMLSelectElement ? "select" : (input as HTMLInputElement).type || "text",
      value: input.value?.slice(0, 100) || "",
      placeholder: (input as HTMLInputElement).placeholder || "",
      required: input.required,
      validationMessage: input.validationMessage?.slice(0, 200) || "",
      ariaLabel: input.getAttribute("aria-label"),
      id,
      hasLabel,
    });
  });

  // ── Links ──
  const allLinks = document.querySelectorAll("a[href]");
  let externalLinkCount = 0;
  let linksWithoutText = 0;

  allLinks.forEach((a) => {
    const anchor = a as HTMLAnchorElement;
    const text = (anchor.textContent || "").trim();
    const ariaLabel = anchor.getAttribute("aria-label") || "";
    if (!text && !ariaLabel && !anchor.querySelector("img")) {
      linksWithoutText++;
    }
    try {
      if (anchor.hostname && anchor.hostname !== window.location.hostname) {
        externalLinkCount++;
      }
    } catch { /* invalid URL */ }
  });

  // ── Images ──
  const allImages = document.querySelectorAll("img");
  const brokenImages: ImageInfo[] = [];
  const imagesWithoutAlt: ImageInfo[] = [];

  allImages.forEach((img) => {
    const info: ImageInfo = {
      src: (img.src || "").slice(0, 200),
      alt: (img.alt || "").slice(0, 150),
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      isBroken: img.complete && img.naturalWidth === 0,
      hasAlt: img.hasAttribute("alt") && img.alt.trim().length > 0,
    };

    if (info.isBroken && brokenImages.length < 20) {
      brokenImages.push(info);
    }
    if (!info.hasAlt && imagesWithoutAlt.length < 20) {
      imagesWithoutAlt.push(info);
    }
  });

  // ── Accessibility quick checks ──
  const a11yIssues: A11yIssue[] = [];

  // Missing lang attribute
  if (!lang) {
    a11yIssues.push({
      type: "missing-lang",
      selector: "html",
      message: "Document is missing lang attribute",
      severity: "error",
    });
  }

  // Buttons / interactive elements without accessible names
  document.querySelectorAll("button, [role='button']").forEach((btn) => {
    const text = (btn.textContent || "").trim();
    const ariaLabel = btn.getAttribute("aria-label") || "";
    const ariaLabelledBy = btn.getAttribute("aria-labelledby") || "";
    const title = btn.getAttribute("title") || "";
    if (!text && !ariaLabel && !ariaLabelledBy && !title) {
      if (a11yIssues.length < 50) {
        a11yIssues.push({
          type: "button-no-name",
          selector: getSelector(btn),
          message: "Button has no accessible name",
          severity: "error",
        });
      }
    }
  });

  // Form inputs without labels
  formFields.forEach((field) => {
    if (!field.hasLabel && !field.ariaLabel && field.type !== "submit" && field.type !== "button") {
      if (a11yIssues.length < 50) {
        a11yIssues.push({
          type: "input-no-label",
          selector: field.id ? `#${field.id}` : `input[name='${field.name}']`,
          message: `Form input '${field.name || field.id || field.type}' has no associated label`,
          severity: "error",
        });
      }
    }
  });

  // Images without alt text
  imagesWithoutAlt.forEach((img) => {
    if (a11yIssues.length < 50) {
      a11yIssues.push({
        type: "img-no-alt",
        selector: `img[src='${CSS.escape(img.src.slice(0, 100))}']`,
        message: "Image is missing alt text",
        severity: "warning",
      });
    }
  });

  // Links without discernible text
  if (linksWithoutText > 0) {
    a11yIssues.push({
      type: "link-no-text",
      selector: "a",
      message: `${linksWithoutText} link(s) have no discernible text`,
      severity: "warning",
    });
  }

  // Missing skip navigation
  const hasSkipNav = !!document.querySelector(
    "a[href='#main'], a[href='#content'], [class*='skip']",
  );
  if (!hasSkipNav && document.querySelectorAll("nav, [role='navigation']").length > 0) {
    a11yIssues.push({
      type: "no-skip-nav",
      selector: "body",
      message: "Page has navigation but no skip-to-content link",
      severity: "info",
    });
  }

  // Check heading hierarchy
  let lastLevel = 0;
  let headingOrderBroken = false;
  document.querySelectorAll("h1, h2, h3, h4, h5, h6").forEach((h) => {
    const level = parseInt(h.tagName[1]!, 10);
    if (level > lastLevel + 1 && lastLevel > 0 && !headingOrderBroken) {
      headingOrderBroken = true;
      a11yIssues.push({
        type: "heading-skip",
        selector: getSelector(h),
        message: `Heading hierarchy skips from H${lastLevel} to H${level}`,
        severity: "warning",
      });
    }
    lastLevel = level;
  });

  // ── Performance ──
  const navTiming = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
  const perfMetrics: PerformanceMetrics = {
    domContentLoaded: navTiming ? Math.round(navTiming.domContentLoadedEventEnd - navTiming.startTime) : 0,
    loadComplete: navTiming ? Math.round(navTiming.loadEventEnd - navTiming.startTime) : 0,
    domNodes: document.querySelectorAll("*").length,
    jsHeapUsedMB: null,
  };

  // JS heap if available (Chrome only)
  try {
    const mem = (performance as unknown as { memory?: { usedJSHeapSize: number } }).memory;
    if (mem) {
      perfMetrics.jsHeapUsedMB = Math.round(mem.usedJSHeapSize / 1024 / 1024);
    }
  } catch { /* not available */ }

  return {
    url,
    title,
    description: description.slice(0, 500),
    viewport: { width: window.innerWidth, height: window.innerHeight },
    visibleText,
    selectedText,
    headings,
    formFields,
    formCount: forms.length,
    linkCount: allLinks.length,
    externalLinkCount,
    linksWithoutText,
    imageCount: allImages.length,
    brokenImages,
    imagesWithoutAlt,
    consoleErrors: [...collectedConsoleErrors],
    a11yIssues,
    metaTags,
    hasCanonical,
    hasViewportMeta,
    lang,
    charset,
    performance: perfMetrics,
    extractedAt: new Date().toISOString(),
  };
}

/** Build a concise CSS selector for an element (best-effort) */
function getSelector(el: Element): string {
  if (el.id) return `#${el.id}`;
  const tag = el.tagName.toLowerCase();
  const cls = el.className && typeof el.className === "string"
    ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".")
    : "";
  return `${tag}${cls}`.slice(0, 100);
}
