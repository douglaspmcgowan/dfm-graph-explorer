<!-- model: gpt-5.4 -->

# DFM Graph Explorer Review

## 1. Critical bugs / correctness issues

- **Undated frames pass the temporal filter as year `0`, so temporal mode can overcount/show frames with unknown dates** — 🟡 important — `index.html:2377-2379`.  
  Fix: in temporal mode, treat `null`/NaN `post_year` as excluded by default, or add an explicit “include undated” toggle.

- **Any frame with an unexpected/blank `se_site` becomes permanently filtered out in Levels 2–3** — 🟡 important — `index.html:1266-1280, 1437-1438, 2388-2393`.  
  Fix: derive site pills from data at load time and include an `unknown/other` bucket instead of hard-coding only 5 sites.

- **Possible exporter/schema mismatch for author reputation may silently show `rep 0` in the UI** — 🟡 important — `export_graph.py:279-281`.  
  Fix: verify whether the source node attr is `reputation` vs `author_reputation`, and add an export-time assertion/sample check.

- **Absolute machine-specific paths make the exporter non-reproducible and easy to run against the wrong files** — 🟡 important — `export_graph.py:16-21`.  
  Fix: move paths to CLI args or env vars and default to repo-relative inputs/outputs.

- **Regression risk: topic/frame navigation history is route-only, not filter-aware, so “Back” can land in a visually different state than the user left** — 🟢 nice-to-have — `index.html:1945-2013`.  
  Fix: either include filter state in history snapshots or make Back explicitly route-only in the UI copy.

---

## 2. Accessibility

- **Search results are not keyboard-navigable as a real combobox/listbox** — 🔴 critical — `index.html:1180-1189, 2052-2100, 2290-2306`.  
  Fix: add arrow-key navigation, `aria-expanded`, `aria-controls`, `aria-activedescendant`, and a highlighted active option.

- **Connected-frame cards nest a real `<button>` inside a `role="button"` card, which is problematic for screen readers and keyboard users** — 🟡 important — `index.html:2558-2561, 2586-2607`.  
  Fix: make the card a normal container with a dedicated link/button, or keep the card clickable and move “Why?” outside it.

- **Tooltip content shown on focus is not programmatically associated with the focused node** — 🟡 important — `index.html:1222, 2770-2777`.  
  Fix: connect focused nodes to tooltip text with `aria-describedby`, or expose the same metadata in an always-readable side panel region.

- **Whole-page `aria-live="polite"` on the main content will announce large rerenders too often** — 🟡 important — `index.html:1212, 1472-1495`.  
  Fix: remove `aria-live` from the main region and use a small dedicated live region for status changes only.

- **Several small-text UI elements likely miss contrast targets on the dark surface** — 🟡 important — `index.html:20-21, 184-195, 335-344, 416-421, 1049-1061`.  
  Fix: bump `--fg-faint`/`--fg-muted` contrast for 11–12px text, especially legend, breadcrumb, subtle notes, and graph caption.

- **Search results have no explicit “no results” state for screen readers** — 🟢 nice-to-have — `index.html:2052-2100`.  
  Fix: render a live “No matches” option/text instead of collapsing the popup silently.

---

## 3. Performance

- **Level 2 rescans the entire semantic-edge array on every filter change/render** — 🟡 important — `index.html:1656-1662`.  
  Fix: pre-index edges by topic once in `buildIndices()` and filter only that topic’s edge list.

- **Level 3 recomputes ego links by scanning all semantic edges, despite already having per-frame adjacency** — 🟡 important — `index.html:1801-1808, 1828-1838`.  
  Fix: derive ego links from `semanticEdgesByFrame`/neighbor adjacency instead of filtering `data.semantic_edges` globally.

- **Per-tick work writes all node positions into global state and updates all DOM attrs every tick** — 🟡 important — `index.html:2828-2851`.  
  Fix: persist positions on drag/end or simulation-end, not every tick; keep per-tick DOM work as lean as possible.

- **Level-1 link distance recomputes `maxW` and a scale inside the callback for every edge** — 🟢 nice-to-have — `index.html:1610-1614`.  
  Fix: precompute `maxW` and the scale once before calling `drawForceGraph()`.

- **Full rerender tears down and rebuilds chrome + panel + SVG on every slider/input/resize change** — 🟡 important — `index.html:1472-1495, 2167-2239, 2665-2862`.  
  Fix: separate graph updates from control/panel updates, and preserve SVG/zoom where possible.

- **`fetch(..., { cache: "no-store" })` disables browser/CDN caching for the largest asset** — 🟡 important — `index.html:1328`.  
  Fix: remove `no-store` in production and use hashed filenames or versioned URLs for cache busting.

---

## 4. Code smell / maintainability

- **Global mutable state mixes routing, filters, layout memory, and simulation handles in one object** — 🟡 important — `index.html:1433-1447`.  
  Fix: split into `routeState`, `filterState`, and `graphState`, with small transition helpers.

- **Filter logic is duplicated and already diverging (`passesFrameFilters`, `passesLevelFiltersExceptSelected`, ad-hoc checks in Level 3)** — 🟡 important — `index.html:1801-1808, 2388-2404`.  
  Fix: centralize one predicate with flags like `{ includeSelected, applyTemporal }`.

- **Force/layout constants are scattered magic numbers** — 🟢 nice-to-have — e.g. `index.html:1512-1514, 1609-1618, 1753-1761, 2817-2824, 2830-2833`.  
  Fix: collect per-level physics/layout settings into named config objects.

- **Large HTML template strings dominate rendering, making behavior and ARIA wiring brittle** — 🟡 important — e.g. `index.html:1533-1598, 1682-1742, 2546-2584`.  
  Fix: factor repeated UI chunks into small renderer helpers or DOM-builder functions.

- **Exporter and UI both hard-code taxonomy/site assumptions that should come from data** — 🟢 nice-to-have — `export_graph.py:211-221`, `index.html:1233-1280`.  
  Fix: emit frame/site vocab metadata from the exporter and let the UI render from that metadata.

---

## 5. UX gaps

- **No one-click “Reset filters” affordance, so empty states are easy to hit and tedious to recover from** — 🟡 important — `index.html:1780-1786, 2167-2239`.  
  Fix: add a reset/restore-defaults button whenever any filter deviates from default.

- **Zoom/pan state is lost on rerender, which is disorienting during exploration** — 🟡 important — `index.html:1466-1469, 2684-2707`.  
  Fix: preserve zoom transform across rerenders, or update the existing SVG instead of rebuilding it.

- **Search gives no visible “no matches” feedback and no way to step through multiple results from keyboard** — 🟡 important — `index.html:2052-2100, 2290-2306`.  
  Fix: show a no-results row plus arrow-key selection/Enter-to-open behavior.

- **Filters don’t show counts, so users can’t tell which pill will zero out the graph** — 🟢 nice-to-have — `index.html:2190-2239`.  
  Fix: show per-pill counts (or disable/count-zero states) based on the current topic/filter context.

- **No deep-linking/permalink to a topic/frame view** — 🟡 important — route logic around `index.html:1945-2013`.  
  Fix: mirror route + filters into URL hash/query params so researchers can bookmark/share a view.

- **“Why?” reasoning is hidden with minimal state indication** — 🟢 nice-to-have — `index.html:2561, 2586-2594`.  
  Fix: toggle button text/`aria-expanded` and keep the expanded state visible.

---

## 6. Deployment / data-split advice

- **Yes: split the data** — 🟡 important — current 8.1 MB monolith is okay over Brotli/gzip, but transfer is only half the problem; JSON parse + indexing still blocks first meaningful interaction.  
  Fix: ship a tiny Level-1 manifest (`topics + topic adjacency + counts + year range`), then lazy-load per-topic bundles and a compact search index.

- **Keep Level 1 self-contained and cheap** — 🟡 important — it only needs supernodes, aggregated topic edges, and metadata, not every quote/main point.  
  Fix: move full frame records into per-topic JSON; optionally keep Level-3 quote text only in the topic bundle.

- **Don’t split into many eager requests** — 🟡 important — 39 topic files is fine only if fetched on demand; fetching them all up front just trades one bottleneck for another.  
  Fix: load `topics.json` first, fetch `topic_<id>.json` only on open, and optionally prefetch the last/next topic.

- **Vercel compression helps bytes, not parse cost; remove `no-store` once files are versioned** — 🟡 important — `index.html:1328`.  
  Fix: use immutable/hashes for split bundles and let Vercel/browser cache them aggressively.

- **Make the search index intentionally skinny** — 🟡 important — don’t duplicate full `source_quote`/`main_point` text unless ranking quality truly needs it.  
  Fix: store only ids + short searchable fields/tokens/snippets, and open the real topic/frame data lazily.

- **Exporter paths/config should be deployment-safe before you split** — 🟡 important — `export_graph.py:16-21, 327-329`.  
  Fix: parameterize input/output paths now, so producing `topics.json`, `search_index.json`, and topic bundles is repeatable across machines/CI.