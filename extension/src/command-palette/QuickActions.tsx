/* ── QuickActions — QA-focused suggested action buttons ── */

interface QuickActionsProps {
  onSelect: (task: string) => void;
}

const QA_SUGGESTIONS = [
  {
    label: "� Full site audit",
    task: "Run a complete end-to-end QA audit of this website. First, crawl and map the entire site to discover all pages and interactive elements. Then visit EVERY page and test it: check that pages load correctly, all links work, all buttons are functional, all forms validate properly, images load, and there are no console errors. Test interactions like a real user would — click buttons, fill forms, navigate between pages. Finally compile a comprehensive report with all issues found, organized by severity.",
  },
  {
    label: "🗺️ Map & explore all pages",
    task: "Discover and map all pages on this website. Use crawl_and_map_site to find every internal page, navigation link, form, and interactive element. Then navigate to each discovered page and verify it loads correctly with no errors. Report a summary of all pages found and their status.",
  },
  {
    label: "🖱️ Test all interactions",
    task: "Test every interactive element on this website like a real user. Navigate through all pages and for each page: click every button, test every form (with valid AND invalid data), toggle every dropdown, open every modal, switch every tab. Report which elements work correctly and which are broken or non-functional.",
  },
  {
    label: "📝 Test all forms & inputs",
    task: "Find and test every form across all pages of this website. For each form: submit with empty required fields (verify error messages), submit with invalid data (wrong email format, short passwords), submit with valid data (verify success). Check that all form fields have proper labels, validation messages are clear, and autocomplete attributes are set.",
  },
  {
    label: "🔍 Accessibility & console check",
    task: "Run accessibility and console error checks across ALL pages of this website. Navigate to every page and on each one: audit accessibility (alt text, labels, headings, ARIA), check console for JavaScript errors, and check for broken links. Compile a comprehensive report covering every page.",
  },
  {
    label: "⚡ Performance & SEO audit",
    task: "Analyze performance and SEO across all pages of this website. Navigate to each page and check: load times, DOM complexity, resource sizes, meta tags, heading structure, and mobile-friendliness. Report optimization opportunities for each page.",
  },
];

export function QuickActions({ onSelect }: QuickActionsProps) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {QA_SUGGESTIONS.map((s) => (
        <button
          key={s.label}
          onClick={() => onSelect(s.task)}
          className="
            px-2.5 py-1 text-xs rounded-lg
            bg-surface-lighter border border-border
            text-text-secondary hover:text-text-primary
            hover:bg-border hover:border-text-muted
            transition-colors
          "
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
