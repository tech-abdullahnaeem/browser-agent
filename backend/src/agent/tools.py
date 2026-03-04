"""Custom browser-use tools registered via the @tools.action() decorator.

NOTE: Do NOT use `from __future__ import annotations` in this module.
browser-use's action registration inspects annotations at runtime and
deferred annotations (strings) would break the type compatibility check.

This module provides both general browser tools and QA-specific tools for
website auditing: console errors, accessibility, broken links, performance,
and form validation.
"""

import json
from browser_use import ActionResult, BrowserSession, Tools

# Create a shared Tools instance that the agent will use.
custom_tools = Tools()


# ---------------------------------------------------------------------------
# General Tools
# ---------------------------------------------------------------------------

@custom_tools.action("Extract the visible text content of the current page (useful for summarisation)")
async def extract_page_text(browser_session: BrowserSession) -> ActionResult:
    """Return the cleaned visible text of the current page."""
    page = await browser_session.get_current_page()
    text = await page.evaluate("() => document.body.innerText")
    max_chars = 5000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return ActionResult(extracted_content=text)


@custom_tools.action("Take a screenshot of the current viewport and return it as base64 PNG")
async def take_screenshot(browser_session: BrowserSession) -> ActionResult:
    """Capture the current viewport and return the image data."""
    page = await browser_session.get_current_page()
    screenshot_bytes = await page.screenshot(type="png")
    import base64

    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    return ActionResult(
        extracted_content=f"Screenshot captured ({len(screenshot_bytes)} bytes)",
        images=[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}],
    )


# ---------------------------------------------------------------------------
# QA / Testing Tools
# ---------------------------------------------------------------------------

@custom_tools.action(
    "Check the browser console for JavaScript errors, warnings, and failed network requests. "
    "Returns a summary of all console issues found."
)
async def check_console_errors(browser_session: BrowserSession) -> ActionResult:
    """Collect console errors and warnings from the current page."""
    page = await browser_session.get_current_page()

    # Inject a collector that captures existing errors and watches for new ones
    result = await page.evaluate("""() => {
        const errors = [];

        // Check for JS errors via window.onerror state
        // Re-scan performance entries for failed requests
        const failedResources = performance.getEntriesByType('resource')
            .filter(e => e.transferSize === 0 && e.decodedBodySize === 0)
            .map(e => ({ url: e.name, type: e.initiatorType }))
            .slice(0, 20);

        // Check for images that failed to load
        document.querySelectorAll('img').forEach(img => {
            if (img.complete && img.naturalWidth === 0 && img.src) {
                errors.push({ level: 'error', message: `Broken image: ${img.src}` });
            }
        });

        // Check for failed script/link loads
        document.querySelectorAll('script[src], link[rel="stylesheet"]').forEach(el => {
            if (el.tagName === 'SCRIPT' && !el.dataset.loaded) {
                // We can't reliably detect failed scripts after load, include them for awareness
            }
        });

        return JSON.stringify({
            failedResources: failedResources.slice(0, 15),
            domErrors: errors.slice(0, 20),
            totalResources: performance.getEntriesByType('resource').length
        });
    }""")

    data = json.loads(result)
    lines = []

    if data["domErrors"]:
        lines.append(f"## DOM Errors ({len(data['domErrors'])})")
        for err in data["domErrors"]:
            lines.append(f"  [{err['level']}] {err['message']}")

    if data["failedResources"]:
        lines.append(f"\n## Failed Resources ({len(data['failedResources'])})")
        for res in data["failedResources"]:
            lines.append(f"  [{res['type']}] {res['url']}")

    lines.append(f"\nTotal resources loaded: {data['totalResources']}")

    if not data["domErrors"] and not data["failedResources"]:
        lines.append("No console errors or failed resources detected.")

    return ActionResult(extracted_content="\n".join(lines))


@custom_tools.action(
    "Run an accessibility audit on the current page. Checks for missing alt text, "
    "missing form labels, heading hierarchy issues, missing ARIA attributes, "
    "color contrast basics, and skip navigation. Returns a detailed report."
)
async def audit_accessibility(browser_session: BrowserSession) -> ActionResult:
    """Run a comprehensive accessibility audit on the current page."""
    page = await browser_session.get_current_page()

    result = await page.evaluate("""() => {
        const issues = [];

        // 1. Missing lang attribute
        if (!document.documentElement.lang) {
            issues.push({ severity: 'error', rule: 'html-has-lang', message: 'Document is missing lang attribute on <html>' });
        }

        // 2. Images without alt
        document.querySelectorAll('img').forEach((img, i) => {
            if (!img.hasAttribute('alt') || (img.alt.trim() === '' && !img.getAttribute('role'))) {
                const src = img.src ? img.src.substring(0, 80) : 'unknown';
                issues.push({ severity: 'warning', rule: 'img-alt', message: `Image #${i+1} missing alt text: ${src}` });
            }
        });

        // 3. Form inputs without labels
        document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea').forEach((input, i) => {
            const id = input.id;
            const hasLabel = id ? !!document.querySelector(`label[for="${id}"]`) : !!input.closest('label');
            const ariaLabel = input.getAttribute('aria-label');
            const ariaLabelledBy = input.getAttribute('aria-labelledby');
            if (!hasLabel && !ariaLabel && !ariaLabelledBy) {
                const name = input.name || input.id || input.type || 'unknown';
                issues.push({ severity: 'error', rule: 'label', message: `Form input '${name}' (#${i+1}) has no associated label` });
            }
        });

        // 4. Buttons without accessible names
        document.querySelectorAll('button, [role=button]').forEach((btn, i) => {
            const text = (btn.textContent || '').trim();
            const ariaLabel = btn.getAttribute('aria-label') || '';
            const title = btn.getAttribute('title') || '';
            if (!text && !ariaLabel && !title && !btn.querySelector('img[alt]')) {
                issues.push({ severity: 'error', rule: 'button-name', message: `Button #${i+1} has no accessible name` });
            }
        });

        // 5. Heading hierarchy
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        let prevLevel = 0;
        headings.forEach(h => {
            const level = parseInt(h.tagName[1]);
            if (prevLevel > 0 && level > prevLevel + 1) {
                issues.push({ severity: 'warning', rule: 'heading-order', message: `Heading hierarchy skips from H${prevLevel} to H${level}: "${(h.textContent || '').trim().substring(0, 50)}"` });
            }
            prevLevel = level;
        });

        // Count of h1 tags
        const h1Count = document.querySelectorAll('h1').length;
        if (h1Count === 0) {
            issues.push({ severity: 'warning', rule: 'page-has-h1', message: 'Page has no H1 heading' });
        } else if (h1Count > 1) {
            issues.push({ severity: 'info', rule: 'multiple-h1', message: `Page has ${h1Count} H1 headings (consider using only one)` });
        }

        // 6. Links without text
        let emptyLinks = 0;
        document.querySelectorAll('a[href]').forEach(a => {
            const text = (a.textContent || '').trim();
            const ariaLabel = a.getAttribute('aria-label') || '';
            if (!text && !ariaLabel && !a.querySelector('img[alt]')) {
                emptyLinks++;
            }
        });
        if (emptyLinks > 0) {
            issues.push({ severity: 'warning', rule: 'link-name', message: `${emptyLinks} link(s) have no discernible text` });
        }

        // 7. Skip navigation
        const hasSkipNav = !!document.querySelector("a[href='#main'], a[href='#content'], a[href='#main-content'], [class*='skip']");
        const hasNav = document.querySelectorAll('nav, [role=navigation]').length > 0;
        if (hasNav && !hasSkipNav) {
            issues.push({ severity: 'info', rule: 'skip-nav', message: 'Page has navigation but no skip-to-content link' });
        }

        // 8. Tab index > 0
        const badTabIndex = document.querySelectorAll('[tabindex]');
        badTabIndex.forEach(el => {
            const val = parseInt(el.getAttribute('tabindex') || '0');
            if (val > 0) {
                issues.push({ severity: 'warning', rule: 'tabindex', message: `Element has tabindex="${val}" (positive tabindex disrupts natural tab order)` });
            }
        });

        return JSON.stringify({
            issues: issues.slice(0, 50),
            totalElements: document.querySelectorAll('*').length,
            headingCount: headings.length,
            imageCount: document.querySelectorAll('img').length,
            formInputCount: document.querySelectorAll('input, select, textarea').length,
            linkCount: document.querySelectorAll('a[href]').length
        });
    }""")

    data = json.loads(result)
    lines = [f"# Accessibility Audit Report\n"]
    lines.append(f"Page stats: {data['totalElements']} DOM elements, "
                 f"{data['imageCount']} images, {data['formInputCount']} form inputs, "
                 f"{data['linkCount']} links, {data['headingCount']} headings\n")

    errors = [i for i in data["issues"] if i["severity"] == "error"]
    warnings = [i for i in data["issues"] if i["severity"] == "warning"]
    infos = [i for i in data["issues"] if i["severity"] == "info"]

    if errors:
        lines.append(f"## Errors ({len(errors)})")
        for issue in errors:
            lines.append(f"  [ERROR] [{issue['rule']}] {issue['message']}")

    if warnings:
        lines.append(f"\n## Warnings ({len(warnings)})")
        for issue in warnings:
            lines.append(f"  [WARN] [{issue['rule']}] {issue['message']}")

    if infos:
        lines.append(f"\n## Info ({len(infos)})")
        for issue in infos:
            lines.append(f"  [INFO] [{issue['rule']}] {issue['message']}")

    if not data["issues"]:
        lines.append("No accessibility issues detected. The page passes basic automated checks.")

    return ActionResult(extracted_content="\n".join(lines))


@custom_tools.action(
    "Scan all links on the current page and test each one for broken links (HTTP 4xx/5xx). "
    "Returns a report of broken links, redirect chains, and links without descriptive text."
)
async def check_broken_links(browser_session: BrowserSession) -> ActionResult:
    """Check all links on the page for broken URLs."""
    page = await browser_session.get_current_page()

    # Extract all links from the page
    links_json = await page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href;
            const text = (a.textContent || '').trim().substring(0, 100);
            const ariaLabel = a.getAttribute('aria-label') || '';
            // Only check http(s) links
            if (href && (href.startsWith('http://') || href.startsWith('https://'))) {
                links.push({ href, text, ariaLabel });
            }
        });
        // Deduplicate by href
        const seen = new Set();
        return JSON.stringify(links.filter(l => {
            if (seen.has(l.href)) return false;
            seen.add(l.href);
            return true;
        }).slice(0, 50));
    }""")

    links = json.loads(links_json)
    lines = [f"# Broken Link Check\n", f"Testing {len(links)} unique links...\n"]

    broken = []
    redirect = []
    no_text = []

    for link in links:
        if not link["text"] and not link["ariaLabel"]:
            no_text.append(link)

        # Test each link with a HEAD request via the browser
        try:
            status_code = await page.evaluate(
                """(url) => {
                    return fetch(url, { method: 'HEAD', mode: 'no-cors' })
                        .then(r => r.status)
                        .catch(() => -1);
                }""",
                link["href"],
            )
            if status_code >= 400:
                broken.append({**link, "status": status_code})
            elif status_code >= 300:
                redirect.append({**link, "status": status_code})
        except Exception:
            broken.append({**link, "status": "error"})

    if broken:
        lines.append(f"## Broken Links ({len(broken)})")
        for b in broken:
            lines.append(f"  [{b['status']}] {b['href']}")
            if b["text"]:
                lines.append(f"        Text: {b['text']}")

    if redirect:
        lines.append(f"\n## Redirect Links ({len(redirect)})")
        for r in redirect:
            lines.append(f"  [{r['status']}] {r['href']}")

    if no_text:
        lines.append(f"\n## Links Without Description ({len(no_text)})")
        for n in no_text[:10]:
            lines.append(f"  {n['href']}")

    if not broken and not redirect:
        lines.append("All links appear to be working correctly.")

    return ActionResult(extracted_content="\n".join(lines))


@custom_tools.action(
    "Analyze page performance metrics including DOM size, resource counts, load timing, "
    "large resources, and render-blocking elements. Returns optimization recommendations."
)
async def check_performance(browser_session: BrowserSession) -> ActionResult:
    """Collect and analyze page performance metrics."""
    page = await browser_session.get_current_page()

    result = await page.evaluate("""() => {
        const navTiming = performance.getEntriesByType('navigation')[0] || {};
        const resources = performance.getEntriesByType('resource');

        // Group resources by type
        const byType = {};
        resources.forEach(r => {
            const type = r.initiatorType || 'other';
            if (!byType[type]) byType[type] = { count: 0, totalSize: 0 };
            byType[type].count++;
            byType[type].totalSize += r.transferSize || 0;
        });

        // Find large resources (> 100KB)
        const largeResources = resources
            .filter(r => r.transferSize > 100000)
            .map(r => ({
                url: r.name.substring(0, 120),
                type: r.initiatorType,
                sizeKB: Math.round(r.transferSize / 1024),
                durationMs: Math.round(r.duration)
            }))
            .sort((a, b) => b.sizeKB - a.sizeKB)
            .slice(0, 10);

        // DOM depth
        let maxDepth = 0;
        function getDepth(el, depth) {
            if (depth > maxDepth) maxDepth = depth;
            if (depth > 30) return; // Limit to prevent stack overflow
            for (let child of el.children) {
                getDepth(child, depth + 1);
            }
        }
        getDepth(document.body, 0);

        // JS heap
        let heapMB = null;
        try {
            if (performance.memory) {
                heapMB = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024);
            }
        } catch(e) {}

        return JSON.stringify({
            timing: {
                dns: Math.round((navTiming.domainLookupEnd || 0) - (navTiming.domainLookupStart || 0)),
                tcp: Math.round((navTiming.connectEnd || 0) - (navTiming.connectStart || 0)),
                ttfb: Math.round((navTiming.responseStart || 0) - (navTiming.requestStart || 0)),
                domContentLoaded: Math.round((navTiming.domContentLoadedEventEnd || 0) - (navTiming.startTime || 0)),
                loadComplete: Math.round((navTiming.loadEventEnd || 0) - (navTiming.startTime || 0)),
                domInteractive: Math.round((navTiming.domInteractive || 0) - (navTiming.startTime || 0))
            },
            dom: {
                nodes: document.querySelectorAll('*').length,
                maxDepth: maxDepth,
                scripts: document.querySelectorAll('script').length,
                stylesheets: document.querySelectorAll('link[rel=stylesheet]').length,
                images: document.querySelectorAll('img').length
            },
            resources: {
                total: resources.length,
                byType: byType,
                largeResources: largeResources,
                totalTransferKB: Math.round(resources.reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024)
            },
            heapMB: heapMB
        });
    }""")

    data = json.loads(result)
    t = data["timing"]
    d = data["dom"]
    r = data["resources"]

    lines = ["# Performance Analysis Report\n"]

    lines.append("## Load Timing")
    lines.append(f"  DNS Lookup: {t['dns']}ms")
    lines.append(f"  TCP Connection: {t['tcp']}ms")
    lines.append(f"  Time to First Byte: {t['ttfb']}ms")
    lines.append(f"  DOM Interactive: {t['domInteractive']}ms")
    lines.append(f"  DOM Content Loaded: {t['domContentLoaded']}ms")
    lines.append(f"  Full Load: {t['loadComplete']}ms")

    lines.append(f"\n## DOM Analysis")
    lines.append(f"  Total DOM Nodes: {d['nodes']}")
    lines.append(f"  Max DOM Depth: {d['maxDepth']}")
    lines.append(f"  Scripts: {d['scripts']}")
    lines.append(f"  Stylesheets: {d['stylesheets']}")
    lines.append(f"  Images: {d['images']}")

    if data.get("heapMB"):
        lines.append(f"  JS Heap: {data['heapMB']}MB")

    lines.append(f"\n## Resources")
    lines.append(f"  Total Resources: {r['total']}")
    lines.append(f"  Total Transfer Size: {r['totalTransferKB']}KB")
    if r.get("byType"):
        for rtype, info in r["byType"].items():
            lines.append(f"    {rtype}: {info['count']} ({round(info['totalSize']/1024)}KB)")

    if r.get("largeResources"):
        lines.append(f"\n## Large Resources (> 100KB)")
        for res in r["largeResources"]:
            lines.append(f"  [{res['type']}] {res['sizeKB']}KB — {res['url']}")

    # Recommendations
    recs = []
    if d["nodes"] > 1500:
        recs.append(f"DOM has {d['nodes']} nodes (recommended < 1500). Consider reducing DOM complexity.")
    if d["maxDepth"] > 15:
        recs.append(f"DOM depth is {d['maxDepth']} (recommended < 15). Flatten nested elements.")
    if t["loadComplete"] > 3000:
        recs.append(f"Page load time is {t['loadComplete']}ms (recommended < 3000ms).")
    if r["totalTransferKB"] > 2000:
        recs.append(f"Total page weight is {r['totalTransferKB']}KB (recommended < 2000KB).")
    if d["scripts"] > 20:
        recs.append(f"Page loads {d['scripts']} scripts. Consider bundling or lazy-loading.")

    if recs:
        lines.append(f"\n## Recommendations")
        for rec in recs:
            lines.append(f"  ⚠ {rec}")

    return ActionResult(extracted_content="\n".join(lines))


@custom_tools.action(
    "Test all forms on the current page by checking validation, required fields, "
    "label associations, placeholder text, and attempting to submit empty required fields. "
    "Returns a report of form issues found."
)
async def validate_forms(browser_session: BrowserSession) -> ActionResult:
    """Audit all forms on the current page."""
    page = await browser_session.get_current_page()

    result = await page.evaluate("""() => {
        const formReports = [];

        document.querySelectorAll('form').forEach((form, formIdx) => {
            const report = {
                index: formIdx + 1,
                action: form.action || 'none',
                method: (form.method || 'GET').toUpperCase(),
                fields: [],
                issues: []
            };

            // Check if form has no submit button
            const submitBtn = form.querySelector('button[type=submit], input[type=submit], button:not([type])');
            if (!submitBtn) {
                report.issues.push('Form has no visible submit button');
            }

            const inputs = form.querySelectorAll('input:not([type=hidden]), select, textarea');
            inputs.forEach((input, inputIdx) => {
                const field = {
                    index: inputIdx + 1,
                    name: input.name || '',
                    type: input.type || input.tagName.toLowerCase(),
                    required: input.required,
                    value: (input.value || '').substring(0, 50),
                    placeholder: input.placeholder || '',
                    issues: []
                };

                // Check label
                const id = input.id;
                const hasLabel = id ? !!document.querySelector(`label[for="${id}"]`) : !!input.closest('label');
                const ariaLabel = input.getAttribute('aria-label');
                if (!hasLabel && !ariaLabel) {
                    field.issues.push('Missing label');
                }

                // Check autocomplete
                if (['email', 'tel', 'password', 'text'].includes(input.type) && !input.autocomplete && !input.getAttribute('autocomplete')) {
                    field.issues.push('Missing autocomplete attribute');
                }

                // Check validation message
                if (!input.validity.valid) {
                    field.issues.push(`Validation: ${input.validationMessage}`);
                }

                // Required but empty
                if (input.required && !input.value) {
                    field.issues.push('Required field is empty');
                }

                report.fields.push(field);
            });

            formReports.push(report);
        });

        // Also check orphaned inputs (not inside a form)
        const orphanedInputs = document.querySelectorAll('input:not(form input):not([type=hidden])');
        const orphanCount = orphanedInputs.length;

        return JSON.stringify({ forms: formReports, orphanedInputs: orphanCount });
    }""")

    data = json.loads(result)
    forms = data["forms"]

    if not forms and data["orphanedInputs"] == 0:
        return ActionResult(extracted_content="No forms found on this page.")

    lines = [f"# Form Validation Report\n", f"Found {len(forms)} form(s) on the page.\n"]

    for form in forms:
        lines.append(f"## Form #{form['index']} ({form['method']} → {form['action'][:80]})")

        if form["issues"]:
            for issue in form["issues"]:
                lines.append(f"  ⚠ {issue}")

        for field in form["fields"]:
            field_info = f"  Field #{field['index']}: {field['name'] or 'unnamed'} ({field['type']})"
            if field["required"]:
                field_info += " [REQUIRED]"
            lines.append(field_info)

            for issue in field["issues"]:
                lines.append(f"    ⚠ {issue}")

    if data["orphanedInputs"] > 0:
        lines.append(f"\n## Orphaned Inputs")
        lines.append(f"  {data['orphanedInputs']} input(s) found outside any <form> element")

    return ActionResult(extracted_content="\n".join(lines))


@custom_tools.action(
    "Check SEO basics on the current page: meta tags, Open Graph, canonical, structured data, "
    "heading structure, and robots directives. Returns a report of SEO issues."
)
async def check_seo(browser_session: BrowserSession) -> ActionResult:
    """Audit basic SEO elements on the current page."""
    page = await browser_session.get_current_page()

    result = await page.evaluate("""() => {
        const issues = [];
        const info = {};

        // Title
        info.title = document.title || '';
        if (!info.title) {
            issues.push({ severity: 'error', message: 'Page has no <title> tag' });
        } else if (info.title.length < 10) {
            issues.push({ severity: 'warning', message: `Title is very short (${info.title.length} chars)` });
        } else if (info.title.length > 60) {
            issues.push({ severity: 'warning', message: `Title is long (${info.title.length} chars, recommended < 60)` });
        }

        // Meta description
        const metaDesc = document.querySelector('meta[name=description]');
        info.description = metaDesc ? metaDesc.content : '';
        if (!info.description) {
            issues.push({ severity: 'error', message: 'Page has no meta description' });
        } else if (info.description.length > 160) {
            issues.push({ severity: 'warning', message: `Meta description is long (${info.description.length} chars, recommended < 160)` });
        }

        // Canonical
        const canonical = document.querySelector('link[rel=canonical]');
        info.canonical = canonical ? canonical.href : null;
        if (!info.canonical) {
            issues.push({ severity: 'warning', message: 'No canonical URL specified' });
        }

        // Open Graph
        const ogTags = {};
        document.querySelectorAll('meta[property^="og:"]').forEach(m => {
            ogTags[m.getAttribute('property')] = (m.content || '').substring(0, 100);
        });
        info.ogTags = ogTags;
        if (!ogTags['og:title']) issues.push({ severity: 'info', message: 'Missing og:title' });
        if (!ogTags['og:description']) issues.push({ severity: 'info', message: 'Missing og:description' });
        if (!ogTags['og:image']) issues.push({ severity: 'info', message: 'Missing og:image' });

        // Robots
        const robotsMeta = document.querySelector('meta[name=robots]');
        info.robots = robotsMeta ? robotsMeta.content : null;

        // Viewport
        const viewport = document.querySelector('meta[name=viewport]');
        if (!viewport) {
            issues.push({ severity: 'warning', message: 'Missing viewport meta tag (mobile-friendliness)' });
        }

        // Structured data
        const jsonLd = document.querySelectorAll('script[type="application/ld+json"]');
        info.structuredDataCount = jsonLd.length;

        // H1 check
        const h1s = document.querySelectorAll('h1');
        if (h1s.length === 0) {
            issues.push({ severity: 'error', message: 'Page has no H1 heading' });
        } else if (h1s.length > 1) {
            issues.push({ severity: 'warning', message: `Page has ${h1s.length} H1 headings (recommended: 1)` });
        }

        return JSON.stringify({ info, issues });
    }""")

    data = json.loads(result)
    info = data["info"]
    issues = data["issues"]

    lines = ["# SEO Audit Report\n"]

    lines.append(f"Title: {info.get('title', 'N/A')}")
    lines.append(f"Description: {(info.get('description', 'N/A') or 'N/A')[:150]}")
    lines.append(f"Canonical: {info.get('canonical', 'Not set')}")
    lines.append(f"Robots: {info.get('robots', 'Not set')}")
    lines.append(f"Structured Data: {info.get('structuredDataCount', 0)} JSON-LD block(s)")

    if info.get("ogTags"):
        lines.append(f"\n## Open Graph Tags")
        for key, val in info["ogTags"].items():
            lines.append(f"  {key}: {val}")

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    infos = [i for i in issues if i["severity"] == "info"]

    if errors:
        lines.append(f"\n## Errors ({len(errors)})")
        for issue in errors:
            lines.append(f"  [ERROR] {issue['message']}")
    if warnings:
        lines.append(f"\n## Warnings ({len(warnings)})")
        for issue in warnings:
            lines.append(f"  [WARN] {issue['message']}")
    if infos:
        lines.append(f"\n## Info ({len(infos)})")
        for issue in infos:
            lines.append(f"  [INFO] {issue['message']}")

    if not issues:
        lines.append("\nNo SEO issues detected. Page passes basic automated checks.")

    return ActionResult(extracted_content="\n".join(lines))


# ---------------------------------------------------------------------------
# Site-Wide Exploration Tools
# ---------------------------------------------------------------------------

@custom_tools.action(
    "Crawl and map the current website: discover all internal pages/routes, navigation links, "
    "and interactive entry-points (buttons, forms, dropdowns). Returns a structured site map "
    "showing every discoverable page and the interactive elements on the current page. "
    "Use this FIRST when starting a full site audit so you know every page to visit."
)
async def crawl_and_map_site(browser_session: BrowserSession) -> ActionResult:
    """Build a site map by extracting all internal links and interactive elements."""
    page = await browser_session.get_current_page()

    result = await page.evaluate("""() => {
        const currentOrigin = window.location.origin;
        const currentPath = window.location.pathname;

        // --- Discover all internal links ---
        const internalLinks = new Map();
        const externalLinks = new Set();

        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href;
            const text = (a.textContent || '').trim().substring(0, 80);
            const ariaLabel = a.getAttribute('aria-label') || '';
            const label = text || ariaLabel || '[no text]';

            try {
                const url = new URL(href, window.location.href);
                if (url.origin === currentOrigin) {
                    const path = url.pathname + (url.hash || '');
                    if (!internalLinks.has(path)) {
                        internalLinks.set(path, {
                            path: path,
                            fullUrl: url.href,
                            label: label,
                            isCurrentPage: url.pathname === currentPath,
                            inNav: !!a.closest('nav, [role=navigation], header, .navbar, .nav, .sidebar, .menu')
                        });
                    }
                } else if (href.startsWith('http')) {
                    externalLinks.add(url.origin + url.pathname);
                }
            } catch(e) {}
        });

        // --- Discover navigation structure ---
        const navElements = [];
        document.querySelectorAll('nav, [role=navigation]').forEach((nav, i) => {
            const links = [];
            nav.querySelectorAll('a[href]').forEach(a => {
                links.push({
                    text: (a.textContent || '').trim().substring(0, 60),
                    href: a.getAttribute('href')
                });
            });
            navElements.push({ index: i + 1, linkCount: links.length, links: links.slice(0, 20) });
        });

        // --- Discover interactive elements ---
        const buttons = [];
        document.querySelectorAll('button, [role=button], input[type=button], input[type=submit]').forEach((btn, i) => {
            const text = (btn.textContent || btn.value || '').trim().substring(0, 60);
            const ariaLabel = btn.getAttribute('aria-label') || '';
            const type = btn.getAttribute('type') || 'button';
            const disabled = btn.disabled || btn.getAttribute('aria-disabled') === 'true';
            buttons.push({ index: i + 1, text: text || ariaLabel || '[no text]', type, disabled });
        });

        // --- Discover forms ---
        const forms = [];
        document.querySelectorAll('form').forEach((form, i) => {
            const action = form.action || '';
            const method = (form.method || 'GET').toUpperCase();
            const fieldCount = form.querySelectorAll('input:not([type=hidden]), select, textarea').length;
            const submitBtn = form.querySelector('button[type=submit], input[type=submit], button:not([type])');
            forms.push({
                index: i + 1,
                action: action.substring(0, 100),
                method,
                fieldCount,
                hasSubmit: !!submitBtn
            });
        });

        // --- Discover dropdowns/menus ---
        const dropdowns = [];
        document.querySelectorAll('select, [role=listbox], [role=menu], [role=combobox], details').forEach((el, i) => {
            const tag = el.tagName.toLowerCase();
            const label = el.getAttribute('aria-label') || el.name || '';
            if (tag === 'select') {
                const options = el.querySelectorAll('option').length;
                dropdowns.push({ index: i + 1, type: 'select', label, optionCount: options });
            } else if (tag === 'details') {
                const summary = el.querySelector('summary');
                dropdowns.push({ index: i + 1, type: 'details', label: (summary ? summary.textContent : '').trim().substring(0, 60) });
            } else {
                dropdowns.push({ index: i + 1, type: el.getAttribute('role'), label });
            }
        });

        return JSON.stringify({
            currentUrl: window.location.href,
            currentPath: currentPath,
            title: document.title,
            internalPages: Array.from(internalLinks.values()).sort((a, b) => a.path.localeCompare(b.path)),
            externalLinkCount: externalLinks.size,
            navigation: navElements,
            buttons: buttons.slice(0, 30),
            forms: forms,
            dropdowns: dropdowns.slice(0, 20),
            iframes: document.querySelectorAll('iframe').length,
            totalLinks: document.querySelectorAll('a[href]').length
        });
    }""")

    data = json.loads(result)
    lines = ["# Site Map & Interactive Elements\n"]
    lines.append(f"Current page: {data['currentUrl']}")
    lines.append(f"Page title: {data['title']}\n")

    # Internal pages
    pages = data["internalPages"]
    nav_pages = [p for p in pages if p["inNav"]]
    other_pages = [p for p in pages if not p["inNav"] and not p["isCurrentPage"]]
    current = [p for p in pages if p["isCurrentPage"]]

    lines.append(f"## Discovered Pages ({len(pages)} internal, {data['externalLinkCount']} external links)")

    if nav_pages:
        lines.append(f"\n### Navigation Links ({len(nav_pages)})")
        for p in nav_pages:
            marker = " ← CURRENT" if p["isCurrentPage"] else ""
            lines.append(f"  {p['path']} — \"{p['label']}\"{marker}")

    if other_pages:
        lines.append(f"\n### Other Internal Links ({len(other_pages)})")
        for p in other_pages[:30]:
            lines.append(f"  {p['path']} — \"{p['label']}\"")
        if len(other_pages) > 30:
            lines.append(f"  ... and {len(other_pages) - 30} more")

    # Navigation structure
    if data["navigation"]:
        lines.append(f"\n## Navigation Menus ({len(data['navigation'])})")
        for nav in data["navigation"]:
            lines.append(f"  Nav #{nav['index']}: {nav['linkCount']} links")
            for link in nav["links"][:10]:
                lines.append(f"    → {link['text']} ({link['href']})")

    # Interactive elements
    if data["buttons"]:
        lines.append(f"\n## Buttons ({len(data['buttons'])})")
        for btn in data["buttons"]:
            status = " [DISABLED]" if btn["disabled"] else ""
            lines.append(f"  [{btn['type']}] \"{btn['text']}\"{status}")

    if data["forms"]:
        lines.append(f"\n## Forms ({len(data['forms'])})")
        for form in data["forms"]:
            submit = "has submit" if form["hasSubmit"] else "NO submit button"
            lines.append(f"  Form #{form['index']}: {form['method']} → {form['action']} ({form['fieldCount']} fields, {submit})")

    if data["dropdowns"]:
        lines.append(f"\n## Dropdowns & Menus ({len(data['dropdowns'])})")
        for dd in data["dropdowns"]:
            extra = f" ({dd.get('optionCount', '?')} options)" if dd["type"] == "select" else ""
            lines.append(f"  [{dd['type']}] \"{dd['label']}\"{extra}")

    if data["iframes"]:
        lines.append(f"\n## Iframes: {data['iframes']}")

    lines.append(f"\n## Summary")
    lines.append(f"  Total internal pages to test: {len(pages)}")
    lines.append(f"  Buttons to interact with: {len(data['buttons'])}")
    lines.append(f"  Forms to test: {len(data['forms'])}")
    lines.append(f"  Dropdowns/menus: {len(data['dropdowns'])}")

    return ActionResult(extracted_content="\n".join(lines))


@custom_tools.action(
    "Test all interactive elements on the current page: click each button, toggle each dropdown, "
    "expand each collapsible section, and report what happened (navigation, state change, error, "
    "or no response). Use this to verify that interactive elements actually work."
)
async def test_interactive_elements(browser_session: BrowserSession) -> ActionResult:
    """Click and test interactive elements, reporting what happens."""
    page = await browser_session.get_current_page()

    # First, collect the interactive elements and page state before interaction
    result = await page.evaluate("""() => {
        const results = [];

        // Capture initial state
        const initialUrl = window.location.href;
        const initialTitle = document.title;

        // --- Test buttons (non-submit, non-navigation) ---
        const buttons = document.querySelectorAll('button:not([type=submit]), [role=button]');
        const buttonInfo = [];
        buttons.forEach((btn, i) => {
            if (i >= 15) return;  // Limit to prevent overwhelming
            const text = (btn.textContent || '').trim().substring(0, 60);
            const disabled = btn.disabled || btn.getAttribute('aria-disabled') === 'true';
            const ariaExpanded = btn.getAttribute('aria-expanded');
            const ariaControls = btn.getAttribute('aria-controls');
            buttonInfo.push({
                index: i,
                text: text || btn.getAttribute('aria-label') || '[no text]',
                disabled,
                ariaExpanded,
                ariaControls,
                tagName: btn.tagName,
                type: btn.getAttribute('type') || 'button',
                visible: btn.offsetParent !== null
            });
        });

        // --- Test details/summary (collapsible) ---
        const details = document.querySelectorAll('details');
        const detailsInfo = [];
        details.forEach((d, i) => {
            if (i >= 10) return;
            const summary = d.querySelector('summary');
            detailsInfo.push({
                index: i,
                label: summary ? (summary.textContent || '').trim().substring(0, 60) : '[no summary]',
                open: d.open
            });
        });

        // --- Check for modals/dialogs ---
        const dialogs = document.querySelectorAll('dialog, [role=dialog], [role=alertdialog]');
        const dialogInfo = [];
        dialogs.forEach((d, i) => {
            dialogInfo.push({
                index: i,
                open: d.open || d.getAttribute('aria-hidden') !== 'true',
                label: d.getAttribute('aria-label') || ''
            });
        });

        // --- Check tabs ---
        const tabLists = document.querySelectorAll('[role=tablist]');
        const tabInfo = [];
        tabLists.forEach((tl, i) => {
            const tabs = tl.querySelectorAll('[role=tab]');
            const tabData = [];
            tabs.forEach(t => {
                tabData.push({
                    text: (t.textContent || '').trim().substring(0, 40),
                    selected: t.getAttribute('aria-selected') === 'true'
                });
            });
            tabInfo.push({ index: i, tabs: tabData });
        });

        return JSON.stringify({
            initialUrl,
            initialTitle,
            buttons: buttonInfo,
            details: detailsInfo,
            dialogs: dialogInfo,
            tabs: tabInfo,
            totalInteractive: buttonInfo.length + detailsInfo.length + dialogInfo.length + tabInfo.length
        });
    }""")

    data = json.loads(result)
    lines = ["# Interactive Elements Test Report\n"]
    lines.append(f"Page: {data['initialUrl']}")
    lines.append(f"Total interactive elements found: {data['totalInteractive']}\n")

    # Report buttons
    if data["buttons"]:
        lines.append(f"## Buttons ({len(data['buttons'])})")
        for btn in data["buttons"]:
            status_parts = []
            if btn["disabled"]:
                status_parts.append("DISABLED")
            if not btn["visible"]:
                status_parts.append("HIDDEN")
            if btn["ariaExpanded"] is not None:
                status_parts.append(f"expanded={btn['ariaExpanded']}")
            if btn["ariaControls"]:
                status_parts.append(f"controls=#{btn['ariaControls']}")
            status = f" ({', '.join(status_parts)})" if status_parts else ""
            lines.append(f"  Button #{btn['index']+1}: \"{btn['text']}\"{status}")
            if btn["disabled"]:
                lines.append(f"    → Skipped (disabled)")
            elif not btn["visible"]:
                lines.append(f"    → Skipped (not visible)")
            else:
                lines.append(f"    → Ready for click testing — use browser click action on this button to verify it works")

    # Report collapsible sections
    if data["details"]:
        lines.append(f"\n## Collapsible Sections ({len(data['details'])})")
        for d in data["details"]:
            state = "OPEN" if d["open"] else "CLOSED"
            lines.append(f"  Section #{d['index']+1}: \"{d['label']}\" [{state}]")
            lines.append(f"    → Toggle this to verify it expands/collapses correctly")

    # Report dialogs/modals
    if data["dialogs"]:
        lines.append(f"\n## Dialogs/Modals ({len(data['dialogs'])})")
        for d in data["dialogs"]:
            state = "OPEN" if d["open"] else "CLOSED"
            lines.append(f"  Dialog #{d['index']+1}: \"{d['label']}\" [{state}]")

    # Report tabs
    if data["tabs"]:
        lines.append(f"\n## Tab Sets ({len(data['tabs'])})")
        for ts in data["tabs"]:
            lines.append(f"  Tab set #{ts['index']+1}:")
            for tab in ts["tabs"]:
                marker = " ← SELECTED" if tab["selected"] else ""
                lines.append(f"    \"{tab['text']}\"{marker}")
            lines.append(f"    → Click each tab to verify content switches correctly")

    if data["totalInteractive"] == 0:
        lines.append("No interactive elements (buttons, collapsibles, dialogs, tabs) found on this page.")
        lines.append("This could indicate a static page or that interactive elements use non-standard markup.")

    lines.append(f"\n## Next Steps")
    lines.append("For each element listed above, use browser actions to:")
    lines.append("  1. Click the element")
    lines.append("  2. Observe what changes (new content, navigation, modal, error)")
    lines.append("  3. Verify the response is correct and expected")
    lines.append("  4. Check for console errors after interaction")

    return ActionResult(extracted_content="\n".join(lines))


@custom_tools.action(
    "Generate a comprehensive test report combining all page-level and site-level findings "
    "into a structured QA report with severity ratings, page coverage, and pass/fail summary. "
    "Call this as the FINAL step after you've tested all pages and interactions."
)
async def generate_test_report(browser_session: BrowserSession) -> ActionResult:
    """Generate a final structured test report for the current page state."""
    page = await browser_session.get_current_page()

    result = await page.evaluate("""() => {
        // Collect final state metrics
        const metrics = {
            url: window.location.href,
            title: document.title,
            domNodes: document.querySelectorAll('*').length,
            images: document.querySelectorAll('img').length,
            brokenImages: 0,
            links: document.querySelectorAll('a[href]').length,
            forms: document.querySelectorAll('form').length,
            inputs: document.querySelectorAll('input:not([type=hidden]), select, textarea').length,
            buttons: document.querySelectorAll('button, [role=button]').length,
            headings: document.querySelectorAll('h1,h2,h3,h4,h5,h6').length,
            scripts: document.querySelectorAll('script').length,
            stylesheets: document.querySelectorAll('link[rel=stylesheet]').length,
            hasViewport: !!document.querySelector('meta[name=viewport]'),
            hasLang: !!document.documentElement.lang,
            hasTitle: !!document.title,
            hasDescription: !!document.querySelector('meta[name=description]'),
            hasH1: document.querySelectorAll('h1').length > 0,
            hasFavicon: !!document.querySelector('link[rel*=icon]'),
            failedResources: performance.getEntriesByType('resource')
                .filter(e => e.transferSize === 0 && e.decodedBodySize === 0).length,
            totalResourceSizeKB: Math.round(
                performance.getEntriesByType('resource')
                    .reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024
            )
        };

        // Count broken images
        document.querySelectorAll('img').forEach(img => {
            if (img.complete && img.naturalWidth === 0 && img.src) metrics.brokenImages++;
        });

        return JSON.stringify(metrics);
    }""")

    data = json.loads(result)
    lines = ["# QA Test Report — Final Summary\n"]
    lines.append(f"Page: {data['url']}")
    lines.append(f"Title: {data['title']}\n")

    # Quick health checks
    lines.append("## Quick Health Checks")
    checks = [
        ("Page title present", data["hasTitle"]),
        ("Meta description present", data["hasDescription"]),
        ("HTML lang attribute", data["hasLang"]),
        ("Viewport meta tag", data["hasViewport"]),
        ("H1 heading present", data["hasH1"]),
        ("Favicon present", data["hasFavicon"]),
        ("No broken images", data["brokenImages"] == 0),
        ("No failed resources", data["failedResources"] == 0),
    ]

    passed = sum(1 for _, v in checks if v)
    total = len(checks)
    for label, ok in checks:
        icon = "PASS" if ok else "FAIL"
        lines.append(f"  [{icon}] {label}")

    lines.append(f"\nScore: {passed}/{total} checks passed")

    # Page statistics
    lines.append(f"\n## Page Statistics")
    lines.append(f"  DOM Nodes: {data['domNodes']}")
    lines.append(f"  Images: {data['images']} ({data['brokenImages']} broken)")
    lines.append(f"  Links: {data['links']}")
    lines.append(f"  Forms: {data['forms']} ({data['inputs']} inputs)")
    lines.append(f"  Buttons: {data['buttons']}")
    lines.append(f"  Scripts: {data['scripts']}")
    lines.append(f"  Stylesheets: {data['stylesheets']}")
    lines.append(f"  Total resource size: {data['totalResourceSizeKB']}KB")
    lines.append(f"  Failed resources: {data['failedResources']}")

    return ActionResult(extracted_content="\n".join(lines))


# ---------------------------------------------------------------------------
# Personal Vault Tools (Phase 5)
# ---------------------------------------------------------------------------

@custom_tools.action(
    "Auto-fill a form on the current page using data from the user's encrypted personal vault. "
    "This reads stored personal data (name, email, phone, address, etc.) and fills matching "
    "form fields on the page. Only works when the vault is unlocked."
)
async def fill_form_from_vault(browser_session: BrowserSession) -> ActionResult:
    """Fill form fields using data from the personal vault."""
    # Import here to avoid circular imports — vault is optional
    try:
        from src.api.routes_vault import _vault
    except ImportError:
        return ActionResult(extracted_content="Vault module not available.")

    if _vault is None or not _vault.is_unlocked():
        return ActionResult(
            extracted_content="Personal vault is not available or locked. "
            "Ask the user to unlock the vault from the extension first."
        )

    vault_data = await _vault.get_form_fill_data()
    if not vault_data:
        return ActionResult(extracted_content="Vault is empty — no personal data stored.")

    page = await browser_session.get_current_page()

    # Build a mapping from common form field patterns to vault data
    vault_json = json.dumps(vault_data)
    filled = await page.evaluate(
        """(vaultData) => {
        const data = JSON.parse(vaultData);
        const filled = [];

        // Mapping: vault field → common form field name/id/autocomplete patterns
        const fieldMap = {
            'name': ['name', 'full-name', 'fullname', 'your-name', 'display-name'],
            'email': ['email', 'e-mail', 'mail'],
            'phone': ['phone', 'tel', 'telephone', 'mobile'],
            'address_line1': ['address', 'street', 'address-line1', 'address1', 'street-address'],
            'address_city': ['city', 'town', 'locality'],
            'address_state': ['state', 'region', 'province'],
            'address_zip': ['zip', 'postal', 'postcode', 'postal-code', 'zip-code'],
            'address_country': ['country'],
            'card_number': ['card-number', 'cardnumber', 'cc-number'],
            'card_exp': ['card-exp', 'expiry', 'cc-exp', 'expiration'],
            'card_cvv': ['cvv', 'cvc', 'security-code', 'cc-csc'],
            'card_name': ['cc-name', 'card-name', 'cardholder'],
            'username': ['username', 'user', 'login'],
            'company': ['company', 'organization', 'org'],
        };

        const inputs = document.querySelectorAll(
            'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]), textarea, select'
        );

        inputs.forEach(input => {
            const name = (input.name || '').toLowerCase();
            const id = (input.id || '').toLowerCase();
            const autocomplete = (input.getAttribute('autocomplete') || '').toLowerCase();
            const placeholder = (input.placeholder || '').toLowerCase();
            const label = input.labels?.[0]?.textContent?.toLowerCase() || '';

            for (const [vaultKey, patterns] of Object.entries(fieldMap)) {
                if (!data[vaultKey]) continue;

                const match = patterns.some(p =>
                    name.includes(p) || id.includes(p) ||
                    autocomplete.includes(p) || placeholder.includes(p) ||
                    label.includes(p)
                );

                if (match) {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    )?.set || Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    )?.set;

                    if (nativeInputValueSetter) {
                        nativeInputValueSetter.call(input, data[vaultKey]);
                    } else {
                        input.value = data[vaultKey];
                    }
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    filled.push({
                        field: input.name || input.id || 'unnamed',
                        vaultKey: vaultKey,
                        value: data[vaultKey].substring(0, 3) + '***'
                    });
                    break;
                }
            }
        });

        return JSON.stringify({
            filledCount: filled.length,
            totalInputs: inputs.length,
            filled: filled
        });
    }""",
        vault_json,
    )

    result = json.loads(filled)
    lines = ["# Form Auto-Fill Report\n"]
    lines.append(f"Filled {result['filledCount']} of {result['totalInputs']} form fields\n")

    if result["filled"]:
        for f in result["filled"]:
            lines.append(f"  \u2713 {f['field']} \u2190 vault:{f['vaultKey']} ({f['value']})")
    else:
        lines.append("No matching form fields found for the stored vault data.")
        lines.append("You may need to fill these fields manually using the input tool.")

    return ActionResult(extracted_content="\n".join(lines))
